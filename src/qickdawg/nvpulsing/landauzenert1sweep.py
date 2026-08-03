'''
LandauZenerT1sweep
=======================================================================
An NVAveragerProgram class acquires data for T1 decay measurement, i.e.
a Landau-Zener mw frequency ramp - delay - readout where the frequency ramp
pulse is cycled between on and off to acquire contrasted measurements

For the Landau-Zener frequency ramp, the user must set:

    config.mw_fMHz
        center frequency of the ramp in MHz
    config.df
        total frequency width of the ramp in Hz
    config.wfm_length
        ramp pulse length in register units
    config.fs
        sampling frequency used to generate the waveform in Hz
    config.mw_gain
        microwave gain
    config.pulse_style
        must be set to 'framp'

The ramp frequency range is approximately

    config.mw_fMHz - config.df/2 to config.mw_fMHz + config.df/2

where config.df is converted from Hz to MHz when comparing to config.mw_fMHz.

The ramp time is approximately

    16 * config.wfm_length / config.fs

and the ramp rate is approximately

    config.df / ramp_time
'''


from .nvaverageprogram import NVAveragerProgram
from .nvqicksweep import NVQickSweep

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import os


class LandauZenerT1sweep(NVAveragerProgram):
    '''
    An NVAveragerProgram class that generates and executes a sequence used
    to measure the T1 Decay using a Landau-Zener frequency ramp pulse

    Parameters
    -------------------------------------------------------------------
    soccfg
        instance of qick.QickConfig class
    cfg
        instance of qickdawg.NVConfiguration class with attributes:
        .adc_channel (required)
            int channel which is reading data 0 or 1

        .mw_channel (required)
            qick channel that provides microwave excitation
            0 or 1 for RFSoC4x2
            0 to 6 for ZCU111 or ZCU216
        .mw_nqz (required)
            nyquist zone for microwave generator. 1 or 2
        .mw_gain (required)
            gain of micrwave channel, in register values, from 0 to 2**15-1
        .mw_freg (required)
            microwave frequency in register values
        .mw_fMHz (required)
            center frequency of the Landau-Zener ramp in MHz

        .pulse_style (required)
            pulse style for the microwave channel, should be 'framp'
        .fs (required)
            sampling frequency used to generate the waveform, in Hz
        .df (required)
            total frequency width of the Landau-Zener ramp, in Hz
        .wfm_length (required)
            length of the arbitrary waveform in register units

        .pre_init (required)
            boolian value that indicates whether to pre-pulse the laser to initialize
            the spin state

        .relax_delay_treg (required)
            int that indicates how long to delay between on/off cycles and reps
            in register units
        .laser_readout_offset_treg (required)

        .laser_gate_pmod(required)
            int PMOD channel used to trigger laser source
            0 to 4

    Frequency Ramp Settings
    -------------------------------------------------------------------
    The frequency ramp is configured by setting:
        config.mw_fMHz
        config.df
        config.wfm_length
        config.fs
        config.mw_gain
        config.pulse_style = 'framp'

    The frequency ramp is centered at config.mw_fMHz and spans config.df.
    Therefore the ramp starts at approximately

        config.mw_fMHz - config.df / 2

    and ends at approximately

        config.mw_fMHz + config.df / 2

    where config.df is given in Hz.

    The ramp time is set by config.wfm_length and config.fs:

        ramp_time = 16 * config.wfm_length / config.fs

    The ramp rate is approximately:

        ramp_rate = config.df / ramp_time

    Methods
    -------
    initialize
        method that generates the assembly code that setups the adcs & mw generators,
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
        "mw_gain",
        "mw_freg",
        "pulse_style",
        "fs",
        "df",
        "wfm_length",
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
        '''
        Method that generates the assembly code that is sets up adcs and sources.
        For LandauZenerT1sweep this:
        1. configures the adc to acquire points for self.cfg.readout_integration_t#.
        2. configures the microwave channel
        3. configures the frequency ramp pulse
        4. configures the sweep parameters
        5. initiailzes the spin state with a laser pulse
        '''

        self.check_cfg()

        self.setup_readout()

        self.cfg.adcs = [self.cfg.adc_channel]

        if self.cfg.test:
            self.declare_readout(ch=self.cfg.mw_readout_channel,
                                 freq=self.cfg.mw_fMHz,
                                 length=self.cfg.readout_integration_treg)
            self.cfg.adcs.append(self.cfg.mw_readout_channel)

        self.declare_gen(ch=self.cfg.mw_channel, nqz=self.cfg.mw_nqz)

        if self.cfg.pulse_style == 'framp':

            # Frequency ramp settings:
            # self.cfg.mw_fMHz sets the center frequency of the ramp
            # self.cfg.df sets the total ramp width in Hz
            # self.cfg.wfm_length sets the ramp duration in register units
            # self.cfg.fs sets the sampling frequency used to generate the waveform
            # self.cfg.mw_gain sets the microwave amplitude

            wfm_length = self.cfg.wfm_length * 16
            self.cfg.mw_start_treg = self.cfg.wfm_length

            idata = np.zeros(wfm_length)
            qdata = np.zeros(wfm_length)
            t = np.arange(wfm_length) / self.cfg.fs
            T = wfm_length / self.cfg.fs

            w0 = 0
            dw = 2 * np.pi * self.cfg.df

            baseband_phase = (w0 - dw / 2) * t + (dw / 2 / T) * t**2
            real = np.cos(baseband_phase)
            imag = np.sin(baseband_phase)

            idata = real
            qdata = imag

            idata *= self.soccfg.get_maxv(self.cfg.mw_channel) - 1
            qdata *= self.soccfg.get_maxv(self.cfg.mw_channel) - 1

            self.add_envelope(ch=self.cfg.mw_channel,
                              name="measure",
                              idata=idata,
                              qdata=qdata)

            self.default_pulse_registers(
                ch=self.cfg.mw_channel,
                style='arb',
                freq=self.cfg.mw_freg,
                gain=self.cfg.mw_gain,
                phase=0)

            self.set_pulse_registers(ch=self.cfg.mw_channel,
                                     waveform='measure')

        # Add loops
        self.delay_register = self.new_gen_reg(self.cfg.mw_channel,
                                               name='delay',
                                               init_val=self.cfg.delay_start_treg)

        if self.cfg.scaling_mode == 'exponential':
            self.add_sweep(NVQickSweep(
                self,
                self.delay_register,
                self.cfg.delay_start_treg,
                self.cfg.delay_end_treg,
                expts=self.cfg.nsweep_points,
                scaling_mode=self.cfg.scaling_mode,
                scaling_factor=self.cfg.scaling_factor))

        elif self.cfg.scaling_mode == 'linear':
            self.add_sweep(NVQickSweep(
                self,
                self.delay_register,
                self.cfg.delay_start_treg,
                self.cfg.delay_end_treg,
                self.cfg.nsweep_points))

        self.synci(100)  # give processor some time to configure pulses
        if (self.cfg.ddr4 is True) or (self.cfg.mr is True):
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
        For LandauZenerT1sweep this peforms four measurements at a time and does two
        pulse sequences differing as to whether the microwave ramp is on or off.
        The sequences is:
        1. Pulse mw with frequency ramp off
        2. delay by variable delay time
        3. Perform readout
        4. Pulse mw with frequency ramp on
        5. delay by variable delay time
        6. Perform readout
        7. Loop over delay times
        8. Loop over reps
        9. Loop over rounds
        '''

        ## First pulse sequence
        ## Landau-Zener ramp off - delay - readout
        ## Nothing - just delay for the ramp time
        self.synci(self.cfg.mw_start_treg)

        # delay
        self.sync(self.delay_register.page, self.delay_register.addr)

        # readout
        self.sync_all(self.cfg.mw_readout_delay_treg)
        self.ttl_readout()

        ## Second pulse sequence
        ## Landau-Zener ramp on - delay - readout
        self.pulse(ch=self.cfg.mw_channel, t=0)
        self.synci(self.cfg.mw_start_treg)

        # delay
        self.sync(self.delay_register.page, self.delay_register.addr)

        # readout
        self.sync_all(self.cfg.mw_readout_delay_treg)
        self.ttl_readout()

    def acquire(self, raw_data=False, *arg, **kwarg):

        data = super().acquire(readouts_per_experiment=4, *arg, **kwarg)

        if raw_data is False:
            data = self.analyze_pulse_sequence(data)

        return data

    def plot_sequence(cfg=None):
        '''
        Function that plots the pulse sequence generated by this program

        Parameters
        ----------
        cfg: `.NVConfiguration` or None(default None)
            If None, this plots the squence with configuration labels
            If a `.NVConfiguration` object is supplied, the configuraiton value are added to the plot
        '''
        graphics_folder = os.path.join(os.path.dirname(__file__), 'graphics')
        image_path = os.path.join(graphics_folder, 'T1.png')

        if cfg is None:
            plt.figure(figsize=(12, 12))
            plt.axis('off')
            plt.imshow(mpimg.imread(image_path))
            plt.text(500, 700, "config.reps", fontsize=14)

            plt.text(305, 335, "delay", fontsize=10)
            plt.text(400, 385, "  config.readout_reference_start", fontsize=10)
            plt.text(220, 335, "LZ ramp", fontsize=10)

            plt.text(260, 465, "config.laser_readout_offset", fontsize=10)
            plt.text(390, 340, "config.readout_integration", fontsize=10)
            plt.text(650, 340, "config.readout_integration", fontsize=10)
            plt.text(850, 340, "config.relax_delay", fontsize=10)
            plt.text(400, 430, "config.laser_on", fontsize=10)

            string = "Sweep delay from config.delay_start to config.delay_end in "
            string += "config.nsweep_points \n"
            string += "                            with scaling given by config.scaling_mode"

            plt.text(220, 605, string, fontsize=12)
            plt.title("             Landau-Zener T1 Pulse Sequence", fontsize=20)
        else:
            plt.figure(figsize=(12, 12))
            plt.axis('off')
            plt.imshow(mpimg.imread(image_path))
            plt.text(450, 700, "Repeat {} times".format(cfg.reps), fontsize=14)
            plt.text(305, 335, "delay", fontsize=10)
            plt.text(400, 385, "  config.readout_reference_start", fontsize=10)
            plt.text(220, 335, "LZ ramp", fontsize=10)
            plt.text(240, 465, "laser_readout_offset = {} treg".format(cfg.laser_readout_offset_treg), fontsize=10)
            plt.text(390, 337, "readout_integration = {} us".format(str(cfg.readout_integration_tus)[:4]), fontsize=10)
            plt.text(650, 357, "readout_integration \n = {} us".format(
                str(cfg.readout_integration_tus)[:4]), fontsize=10)
            plt.text(850, 357, "relax_delay \n = {} us".format(str(cfg.relax_delay_tus)[:4]), fontsize=10)
            plt.text(400, 430, "laser_on = {} us".format(cfg.laser_on_tus), fontsize=12)
            plt.text(325, 605, "    Sweep delay from {} us to {} us \n                in {} {} steps".format(
                int(cfg.delay_start_tns), int(cfg.delay_end_tns), cfg.nsweep_points, cfg.scaling_mode), fontsize=12)
            plt.title("               Landau-Zener T1 Pulse Sequence", fontsize=20)