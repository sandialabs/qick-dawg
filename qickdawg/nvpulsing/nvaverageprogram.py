"""
NVAverageProgam
==========================================================================
An abstract class for generating qick-dawg programs modified from
qick.NDAverageProgram
"""

from qick import QickProgram
from qick.qick_asm import QickRegisterManagerMixin
from qick.averager_program import AbsQickSweep
from tqdm.auto import tqdm
import qickdawg as qd

try:
    from rpyc.utils.classic import obtain
except ModuleNotFoundError:
    def obtain(i):
        return i

import numpy as np
from typing import List
from ..util.itemattribute import ItemAttribute


class NVAveragerProgram(QickRegisterManagerMixin, QickProgram):
    """
    NVAveragerProgram class, for experiments that sweep over multiple variables
    in qick-dawg ordered in reps, sweep_n,... sweep_0.

    Subclass of qick.QickRegisterManagerMixin and qick.QickProgram

    Parameters
    --------------------------------------------------------------------------
    soccfg
        an instance of QickConfig
    cfg
        an instance of NVConfiguration

    Attributes
    ----------



    Methods
    -------





    """

    def __init__(self, cfg):
        """
        Constructor for the NVAveragerProgram. Make the ND sweep asm commands.
        """
        super().__init__(qd.soccfg)
        self.cfg = cfg
        self.qick_sweeps: List[AbsQickSweep] = []
        self.expts = 1
        self.sweep_axes = []
        self.make_program()
        self.reps = cfg['reps']
        if "soft_avgs" in cfg:
            self.rounds = cfg['soft_avgs']
        if "rounds" in cfg:
            self.rounds = cfg['rounds']

    def initialize(self):
        """
        Abstract method for initializing the program. Should include the instructions that will be executed once at the
        beginning of the qick program. This is filled in by child classes to make a pulse program.
        """
        pass

    def body(self):
        """
        Abstract method for the body of the program. This is filled in by child classes to make a pulse program.
        """
        pass

    def add_sweep(self, sweep: AbsQickSweep):
        """
        Add a layer of register sweep to the qick asm program.
        The order of sweeping will follow first added first sweep.
        :param sweep:
        :return:
        """
        self.qick_sweeps.append(sweep)
        self.expts *= sweep.expts
        self.sweep_axes.append(sweep.expts)

    def make_program(self):
        """
        Method that makes the assmebly code for an N dimensional sweep pogram. The steps are as follows:
        1. run the overloaded self.initialize() method to initialize the mw and adc channels etc.
        2. asserts N <7
        3. sets the run count to 0
        4. sets and labels repitition counter
        5. Adds reset and start for each sweep, with label
        6. exectues self.body()
        7. increments rcount
        8. exectues sweep.update() for each sweep and labels the end contdition
        9. creates the stop condition for the rep loop
        10. implement self.end() method to end the assembly code
        """

        self.initialize()  # initialize only run once at the very beginning

        rcount = 13  # total run counter
        rep_count = 14  # repetition counter

        n_sweeps = len(self.qick_sweeps)
        if n_sweeps > 7:  # to be safe, only register 15-21 in page 0 can be used as sweep counters
            raise OverflowError(f"too many qick inner loops ({n_sweeps}), run out of counter registers")
        counter_regs = (np.arange(n_sweeps) + 15).tolist()  # not sure why this has to be a list (np.array doesn't work)

        self.regwi(0, rcount, 0)  # reset total run count

        # set repetition counter and tag
        self.regwi(0, rep_count, self.cfg["reps"] - 1)
        self.label("LOOP_rep")

        # add reset and start tags for each sweep
        for creg, swp in zip(counter_regs[::-1], self.qick_sweeps[::-1]):
            swp.reset()
            self.regwi(0, creg, swp.expts - 1)
            self.label(f"LOOP_{swp.label if swp.label is not None else creg}")

        # run body and total_run_counter++
        self.body()
        self.mathi(0, rcount, rcount, "+", 1)
        self.memwi(0, rcount, 1)

        # add update and stop condition for each sweep
        for creg, swp in zip(counter_regs, self.qick_sweeps):
            swp.update()
            # pass
            self.loopnz(0, creg, f"LOOP_{swp.label if swp.label is not None else creg}")

        # stop condition for repetition
        self.loopnz(0, rep_count, 'LOOP_rep')

        self.end()

    def get_expt_pts(self):
        """
        Method that returns the swept values for each sweep as a 2D array.
        """
        sweep_pts = []
        for swp in self.qick_sweeps:
            sweep_pts.append(swp.get_sweep_pts())
        return sweep_pts

    def acquire(self, reads_per_rep=1, load_pulses=True, start_src="internal", progress=False, debug=False):
        """
        Method that exectues the qick program and accumulates data from the data buffer until the proram is complete
        For NV measurements, the results are DC values and thus only have I values (rather than I and Q)

        Parameters
        ----------
        soc : QickSoc
            qick.QickSoc instance
        reads_per_rep
            int number of readout triggers in the loop body
        load_pulses
            bool: if True, load pulse envelopes
        start_src
            str: "internal" (tProc starts immediately) or "external" (each round waits for an external trigger)
        progress
            bool: if true, displays progress bar
        debug
            bool: if true, displays assembly code for tProc program

        Returns
        -------
        ndarray
            raw accumulated IQ values (int32)
            if rounds>1, only the last round is kept
            dimensions : (n_ch, n_expts*n_reps*n_reads, 2)

        ndarray
            averaged IQ values (float)
            divided by the length of the RO window, and averaged over reps and rounds
            if shot_threshold is defined, the I values will be the fraction of points over threshold
            dimensions for a simple averaging program: (n_ch, n_reads, 2)
            dimensions for a program with multiple expts/steps: (n_ch, n_reads, n_expts, 2)
        """
        self.config_all(qd.soc, load_pulses=load_pulses, start_src=start_src, debug=debug)

        n_ro = len(self.ro_chs)

        expts = self.expts
        if expts is None:
            expts = 1
        total_reps = expts * self.reps
        total_count = total_reps * reads_per_rep
        d_buf = np.zeros((n_ro, total_count, 2), dtype=np.int32)
        self.stats = []

        if 'rounds' not in self.cfg:
            self.cfg.rounds = 1

        # select which tqdm progress bar to show
        hiderounds = True
        hidereps = True
        if progress:
            if self.rounds > 1:
                hiderounds = False
            else:
                hidereps = False

        # avg_d doesn't have a specific shape here, so that it's easier for child programs to write custom _average_buf
        self.dbuf_shape = []

        if reads_per_rep > 1:
            self.dbuf_shape.append(reads_per_rep)

        for swp in self.qick_sweeps:
            self.dbuf_shape = [swp.expts] + self.dbuf_shape

        if self.cfg.reps > 1:
            self.dbuf_shape = [self.cfg.reps] + self.dbuf_shape

        if self.cfg.rounds > 1:
            self.data_shape = [self.cfg.rounds] + self.dbuf_shape
        else:
            self.data_shape = self.dbuf_shape

        for i, ir in enumerate(tqdm(range(self.rounds), disable=hiderounds)):
            # Configure and enable buffer capture.
            self.config_bufs(qd.soc, enable_avg=True, enable_buf=False)

            count = 0
            with tqdm(total=total_count, disable=hidereps) as pbar:
                qd.soc.start_readout(
                    total_reps,
                    counter_addr=self.counter_addr,
                    ch_list=list(self.ro_chs),
                    reads_per_rep=reads_per_rep)
                while count < total_count:
                    new_data = obtain(qd.soc.poll_data())
                    for d, s in new_data:
                        # print(len(new_data), count, total_count)
                        new_points = d.shape[1]
                        d_buf[:, count:count + new_points] = d
                        count += new_points
                        self.stats.append(s)
                        pbar.update(new_points)

            if i == 0:
                data = np.array(d_buf[0][:, 0])
            else:
                data = np.append(data, [np.array(d_buf[0][:, 0])])
        return data

    def acquire_decimated(self, *arg, **kwarg):
        '''
        Overloaded qick.QickProgram method that drops the Q channel of the time domain readout

        Parameters
        ----------
        soc
            qick.QickSoc instance

        Returns
        --------



        '''
        data = super().acquire_decimated(qd.soc, *arg, **kwarg)

        return data[0][:, 0]

    def trigger_no_off(self, adcs=None, pins=None, adc_trig_offset=0, t=0, rp=0, r_out=31):
        """
        Method that is a slight modificaiton of qick.QickProgram.trigger().
        This method does not turn off the PMOD pins, thus also does not require a width parameter

        Parameters
        ----------
        adcs : list of int
            List of readout channels to trigger (index in 'readouts' list) [0], [1], or [0, 1]
        pins : list of int
            List of marker pins to pulsem, i.e. PMOD channels.
            Use the pin numbers in the QickConfig printout.
        adc_trig_offset : int, optional
            Offset time at which the ADC is triggered (in tProc cycles)
        t : int, optional
            The number of tProc cycles at which the ADC trigger starts
        rp : int, optional
            Register page
        r_out : int, optional
            Register number
        """
        if adcs is None:
            adcs = []
        if pins is None:
            pins = []
        if not adcs and not pins:
            raise RuntimeError("must pulse at least one ADC or pin")

        out = 0
        for adc in adcs:
            out |= (1 << self.soccfg['readouts'][adc]['trigger_bit'])
        for pin in pins:
            out |= (1 << pin)

        t_start = t
        if adcs:
            t_start += adc_trig_offset
            # update timestamps with the end of the readout window
            for adc in adcs:
                ts = self.get_timestamp(ro_ch=adc)
                if t_start < ts:
                    print("Readout time %d appears to conflict with previous readout ending at %f?" % (t, ts))
                # convert from readout clock to tProc clock
                ro_length = self.ro_chs[adc]['length']
                ro_length *= self.soccfg['fs_proc'] / self.soccfg['readouts'][adc]['f_fabric']
                self.set_timestamp(t_start + ro_length, ro_ch=adc)

        trig_output = self.soccfg['tprocs'][0]['trig_output']

        self.regwi(rp, r_out, out, f'out = 0b{out:>016b}')
        self.seti(trig_output, rp, r_out, t_start, f'ch =0 out = ${r_out} @t = {t}')
        # self.seti(trig_output, rp, 0, t_end, f'ch =0 out = 0 @t = {t}')

    def ttl_readout(self):
        '''
        Method that generates the NV TTL readout assembly code. Pseduo code as follows:
        1. turn on laser  only at t=0
        2. turn on laser and adc at time self.cfg.laser_readout_offset
        3. turn on laser adc off at time self.cfg.laser_readout_offset+ self.cfg.readout_integration
        4. trigger readout a second time at self.cfg.readout_reference_start_treg
        5. turn readout trigger off and leave laser on for the remaining time
        6. sync tproc
        '''
        # aom only for offset between aom and laser on at t=0
        self.trigger_no_off(
            pins=[self.cfg.laser_gate_pmod],
            adc_trig_offset=0,
            t=0)

        # measure and laser trigger at laser_readout_offset
        self.trigger_no_off(
            adcs=[self.cfg.adc_channel],
            pins=[self.cfg.laser_gate_pmod],
            adc_trig_offset=0,
            t=self.cfg.laser_readout_offset_treg)

        # laser on for time between first measure and second measure
        # at time = laser_readout_offset + readout_integration
        self.trigger_no_off(
            pins=[self.cfg.laser_gate_pmod],
            adc_trig_offset=0,
            t=self.cfg.laser_readout_offset_treg + self.cfg.readout_integration_treg)

        # laser and measure second time at readout_reference_start
        self.trigger_no_off(
            adcs=[self.cfg.adc_channel],
            pins=[self.cfg.laser_gate_pmod],
            adc_trig_offset=0,
            t=self.cfg.readout_reference_start_treg)

        # just laser for the rest of the time = remaining_time
        remaining_time = (
            self.cfg.laser_on_treg
            - 2 * self.cfg.readout_integration_treg
            - self.cfg.readout_reference_start_treg
            - self.cfg.laser_readout_offset_treg)

        self.trigger(
            pins=[self.cfg.laser_gate_pmod],
            width=remaining_time,
            adc_trig_offset=0,
            t=self.cfg.readout_reference_start_treg + self.cfg.readout_integration_treg)

        self.wait_all()
        self.sync_all(self.cfg.relax_delay_treg + remaining_time)

    def analyze_pulse_sequence_results(self, data):
        """
        Method that takes in a 1D array of data points from self.acquire() and analyzes the
        results based on the number of reps, rounds, and frequency points

        Parameters
        ----------
        data
            (1D np.array) data returned from self.acquire()

        returns
            (qickdawg.ItemAttribute instance) with attributes
            .sweep_treg (len(nsweep_points) np array, reg units) - sweep lengths
            .sweep_tus (len(nsweep_points) np array, us units) - sweep lengths
            .signal1, .signal2 (nfrequency np.array, adc units)
                - average adc signal for microwave on, off
            .reference1, .reference2 (nfrequency np.array, adc units)
                - average referenceadc signal for microwave on, off
            .contrast1, contrast2 (nfrequency np.array, adc units))
                - (.signal1(2) minus .refrence1(2))/reference1(2)*100
            .contrast (nfrequency np.array, adc units)
                - .contrast1 - .contrast2
        """

        data = np.reshape(data, self.data_shape)

        d = ItemAttribute()

        if len(self.data_shape) == 2:
            d.signal1 = data[:, 0]
            d.reference1 = data[:, 1]
            if self.data_shape[-1] == 4:
                d.signal2 = data[:, 2]
                d.reference2 = data[:, 3]
        elif len(self.data_shape) == 3:
            d.signal1 = data[:, :, 0]
            d.reference1 = data[:, :, 1]
            if self.data_shape[-1] == 4:
                d.signal2 = data[:, :, 2]
                d.reference2 = data[:, :, 3]
        elif len(self.data_shape) == 4:
            d.signal1 = data[:, :, :, 0]
            d.reference1 = data[:, :, :, 1]
            if self.data_shape[-1] == 4:
                d.signal2 = data[:, :, 2]
                d.reference2 = data[:, :, 3]

        if self.data_shape[-1] == 2:
            d.contrast = ((d.signal1 - d.reference1) / d.reference1 * 100)
            for _ in range(len(d.contrast.shape) - 1):
                d.contrast = np.mean(d.contrast, axis=0)
                d.signal1 = np.mean(d.signal1, axis=0)
                d.reference1 = np.mean(d.reference1, axis=0)
        elif self.data_shape[-1] == 4:
            d.contrast1 = ((d.signal1 - d.reference1) / d.reference1 * 100)
            d.contrast2 = ((d.signal2 - d.reference2) / d.reference2 * 100)
            d.contrast = d.contrast1 - d.contrast2
            for _ in range(len(d.contrast1.shape) - 1):
                d.contrast1 = np.mean(d.contrast1, axis=0)
                d.signal1 = np.mean(d.signal1, axis=0)

                d.reference1 = np.mean(d.reference1, axis=0)
                d.contrast2 = np.mean(d.contrast2, axis=0)
                d.signal2 = np.mean(d.signal2, axis=0)
                d.reference2 = np.mean(d.reference2, axis=0)
                d.contrast = np.mean(d.contrast, axis=0)

        d.sweep_treg = self.qick_sweeps[0].get_sweep_pts()
        d.sweep_tus = self.qick_sweeps[0].get_sweep_pts() * self.cycles2us(1)

        return d

    def check_cfg(self):
        '''
        Method that checks that the configuration has all the values needed to run PL intensity and returns an
        assertion error for missing values

        '''

        missing_cfg = []

        # loop checks if each required item is in self.cfg and adds missing variables to missing_cfg
        for i in range(0, len(self.required_cfg)):
            if self.required_cfg[i] in self.cfg:
                pass
            else:
                missing_cfg.append(self.required_cfg[i])

        # assertion that values must be assigned to the missing items in self.cfg
        assert len(missing_cfg) == 0, \
            ("Missing value for {}".format(", ".join("config.{}".format(item) for item in missing_cfg)))

        if self.cfg.mw_gain > 32767:
            assert self.cfg.mw_gain < 32767, "config.mw_gain should be between 0 and 32,767"
