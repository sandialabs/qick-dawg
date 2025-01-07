
from .nvaverageprogram import NVAveragerProgram
from .nvqicksweep import NVQickSweep

import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import os 


class CPMGXY8nSweep(NVAveragerProgram):
    '''
    An NVAveragerProgram class that generates and executes a sequence used
    to measure the T2 decay of a hahn echo

    Parameters
    ----------
    soccfg : `qick.QickConfig`
    cfg : `.NVConfiguration`
        instance of `.NVConfiguration` class with attributes:
        .adc_channel : int
            ADC channel for gathering data, usually 0 or 1
        .mw_channel : int
            qick channel that provides microwave excitation
            0 or 1 for RFSoC4x2
            0 to 6 for ZCU111 or ZCU216
        .mw_nqz : int
            nyquist zone for microwave generator (1 or 2)
        .mw_gain : int
            gain of micrwave channel, in register values, from 0 to 2**15-1

        .pre_init : bool
            boolian value that indicates whether to pre-pulse the laser to initialize
            the spin state

        .relax_delay_treg : int
            Time between on/off cycles and reps in register units
        .readout_length_treg : int
            Time for which the adc accumulates data in register units
        .laser_readout_offset_treg : int
            Time offset between initial laser triggering and readout start

        .laser_gate_pmod : int
            PMOD channel used to trigger laser source usually 0 to 6

    Returns
    `.HahnEchoDelaySweep`
        An instance of HahnEchoDelay sweep with compiled assembly language

    Methods
    -------
    initialize
        method that generates the assembly code that setups the adcs &  mw generators,
        and performs other one-off setps
    body
        method that generates the assembly code that exectues in the middle of each sweep
        and rep
    plot_sequence
        generates a plot labeled with self.cfg attributes or the required inputs
    time_per_rep
        returns the approximatetime for one rep to complete
    total_time
        returns the approximate total time for the entire program to complete
    '''
    required_cfg = [
        "adc_channel",
        "readout_integration_treg",
        "mw_channel",
        "mw_nqz",
        "mw_pi2_treg",
        "mw_gain",
        "scaling_mode",
        "delay_start_treg",
        "delay_end_treg",
        "nsweep_points",
        "pre_init",
        "laser_gate_pmod",
        "laser_on_treg",
        "relax_delay_treg",
        "reps",
        "readout_reference_start_treg",
        "laser_readout_offset_treg",
        "mw_readout_delay_treg"]

    def initialize(self):
        '''Method that generates the assembly code that is sets up adcs and sources.

        For HahnEchoDelaySweep this:
        1. Configures the adc to acquire points for self.cfg.readout_integration_t#
        2. Configures the microwave channel
        3. Configures the sweep parameters
        4. Initiailzes the spin state with a laser pulse
        '''
        self.check_cfg()

        self.declare_readout(ch=self.cfg.adc_channel,
                             freq=0,
                             length=self.cfg.readout_integration_treg,
                             sel="input")

        self.cfg.adcs = [self.cfg.adc_channel]

        if self.cfg.test:
            self.declare_readout(ch=self.cfg.mw_readout_channel,
                                freq=self.cfg.mw_fMHz,
                                length=self.cfg.readout_integration_treg)
            self.cfg.adcs.append(self.cfg.mw_readout_channel)

        # Get registers for mw

        self.declare_gen(ch=self.cfg.mw_channel,
                         nqz=self.cfg.mw_nqz)

        # Setup pulse defaults microwave
        self.default_pulse_registers(ch=self.cfg.mw_channel,
                                     style='const',
                                     freq=self.cfg.mw_freg,
                                     length=self.cfg.mw_pi2_treg,
                                     gain=self.cfg.mw_gain)

        self.set_pulse_registers(ch=self.cfg.mw_channel,
                                 phase=0)

        # Addd loops
        self.n_total_register = self.new_gen_reg(
            self.cfg.mw_channel,
            name='n_total',
            init_val=self.cfg.delay_start_treg)

        self.mw_time_register = self.get_gen_reg(self.cfg.mw_channel,
                                                 name='t')

        self.n_cpmg_register = self.new_gen_reg(
            self.cfg.mw_channel,
            name='ncpmg',
            init_val = 0)

        if self.cfg.scaling_mode == 'exponential':
            self.add_sweep(NVQickSweep(
                self,
                self.n_total_register,
                self.cfg.n_start,
                self.cfg.n_end,
                expts=self.cfg.nsweep_points,
                scaling_mode=self.cfg.scaling_mode,
                scaling_factor=self.cfg.scaling_factor))

        elif self.cfg.scaling_mode == 'linear':
            self.add_sweep(NVQickSweep(
                self,
                self.n_total_register,
                self.cfg.n_start,
                self.cfg.n_end,
                self.cfg.nsweep_points))
        else:
            assert 0, 'cfg.scaling_mode must be "linear" or "exponential"'

        self.synci(100)  # give processor some time to configure pulses
        if (self.cfg.ddr4 == True) or (self.cfg.mr == True):
            self.trigger(ddr4=self.cfg.ddr4, mr=self.cfg.mr, adc_trig_offset=0)
        self.synci(100)

        if self.cfg.pre_init:
            self.trigger(
                pins=[self.cfg.laser_gate_pmod],
                width=self.cfg.laser_on_treg,
                adc_trig_offset=0
            )
            self.sync_all(self.cfg.laser_on_treg + self.cfg.relax_delay_treg)

    def body(self):
        '''
        Method that generates the assembly code that is looped over or repeated.
        For CPMGXY8 this peforms four measurements at a time and does two pulse
        sequences differing only by the phase of the final pulse.  The sequences is:
        1. Set pulse phase to 0
        2. Pulse mw for pi/2
        ...
        7. Perform readout
        8. Loop over delay times
        9. Loop over reps
        10. Loop over rounds
        '''


        for i, project_phase in enumerate([0, 180]):
            self.set_pulse_registers(ch=self.cfg.mw_channel, phase=self.deg2reg(0))
            ## Pulse Sequence 1
            # first reset phase to x

            # pi/2 - x
            self.pulse(ch=self.cfg.mw_channel)
            self.sync_all()

            # unit of XY8
            self.math(self.n_cpmg_register.page,
                      self.n_cpmg_register.addr,
                      self.n_cpmg_register.addr,
                      "+",
                      self.n_total_reg.addr)
            self.label("LOOP_ncpmg{}".format(i))
            for phase in [0, 90, 0, 90, 90, 0, 90, 0]:
                #  delay
                self.sync(self.delay_register.page, self.delay_register.addr)
                # set phase
                self.set_pulse_registers(ch=self.cfg.mw_channel, phase=self.deg2reg(phase))
                # pi - pulse
                self.pulse(ch=self.cfg.mw_channel)
                self.pulse(ch=self.cfg.mw_channel)
                self.sync_all()
                # delay
                self.sync(self.delay_register.page, self.delay_register.addr)
            self.loopnz(
                self.n_cpmg_register.page,
                self.n_cpmg_register.addr,
                'LOOP_ncpmg{}'.format(i))
            # pi-2 projection pulse
            self.set_pulse_registers(ch=self.cfg.mw_channel, phase=self.deg2reg(project_phase))
            self.pulse(ch=self.cfg.mw_channel)
            self.sync_all(self.cfg.mw_readout_delay_treg)

            # Readout
            self.ttl_readout()

    def acquire(self, raw_data=False, *arg, **kwarg):

        data = super().acquire(readouts_per_experiment=4, *arg, **kwarg)

        if raw_data is False:
            data = self.analyze_pulse_sequence_results(data)

        return data
