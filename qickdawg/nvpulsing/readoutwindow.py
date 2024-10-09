'''
ReadoutWindow
=======================================================================
An NVAveragerProgram class acquires time domain data for calibrating the timing
of the gating of the laser relative to triggering of the ADC.  The adc trigger is
tyipcally on order 100 register values faster than the external trigger.
'''

from .nvaverageprogram import NVAveragerProgram

import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import os


class ReadoutWindow(NVAveragerProgram):
    '''
    An NVAveragerProgram class that generates and executes a sequence used
    to calibrate the laser gating relative to the adc data accumulation. 
    This is intended to be used with the function qickdawg.get_readout_window()
    to accumulate multiple windows with (to accomodate the 1020 point limit of the
    FPGA buffer) and microwave on and off to provide contrast between spin projections

    Parameters
    ----------
    cfg
        instance of qickdawg.NVConfiguration class with attributes:
        .adc_channel (required)
            int channel which is reading data 0 or 1

        .mw_channel (required)
            qick channel that provides microwave excitation
            0 or 1 for RFSoC4x2
            0 to 6 for ZCU111 or ZCU216
        .mw_nqz (required)
            nyquist zone for microwave generator (1 or 2)
        .mw_gain (required)
            gain of micrwave channel, in register values, from 0 to 2**15-1

        .pre_init (required)
            boolian value that indicates whether to pre-pulse the laser to initialize
            the spin state

        .relax_delay_treg (required)
            int that indicates how long to delay between on/off cycles and reps
            in register units
        .readout_length_treg (required)
            int time for which the adc accumulates data
            the limit is 1020 points for the FPGA buffer
        .laser_readout_offset_treg (required)

        .laser_gate_pmod(required)
            int PMOD channel used to trigger laser source
            0 to 4
    returns
        an instances of LockinODMR class with assembly language compiled


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
        "mw_channel",
        "adc_channel",
        "mw_nqz",
        "mw_gain",
        "pre_init",
        "relax_delay_treg",
        "laser_gate_pmod",
        "readout_length_treg",
        "mw_pi2_treg",
        "mw_fMHz",
        "laser_initialize_treg",
        "mw_readout_delay_treg",
        "laser_readout_offset_treg",
        "soft_avgs"]

    def initialize(self):
        '''
        Method that generates the assembly code that configures adcs, mw, etc. 
        For ReadoutWindow this setups up the adc to acquire points for 
        self.cfg.readout_length_t#.  If the mw_pi2_t# > 0, this setups the 
        microwave channel to pulse, otherwise there is mw pulse
        '''
        self.check_cfg()

        self.declare_readout(ch=self.cfg.adc_channel,
                             freq=0,
                             length=self.cfg.readout_length_treg,
                             sel="input")

        # Setup pulse defaults microwave
        if self.cfg.mw_pi2_treg > 0:

            self.declare_gen(ch=self.cfg.mw_channel, nqz=self.cfg.mw_nqz)        
            self.default_pulse_registers(
                ch=self.cfg.mw_channel,
                style='const',
                freq=self.cfg.mw_freg,
                gain=self.cfg.mw_gain,
                length=self.cfg.mw_pi2_treg,
                phase=0)

            self.set_pulse_registers(ch=self.cfg.mw_channel)

        self.synci(400)  # give processor some time to configure pulses

    def body(self):
        '''
        Method that generates the assembly code that is looped over or repeated. 
        For Readoutwindow pre-initializes the spin state by turning just the laser on
        for self.cfg.laser_initalize_t#. After initialization, the micrwave channel is pulsed
        followed by the laser, then the adc is triggered. The laser and adc are offset by 
        self.cfg.laser_readout_offset_t#
        '''
        t = 0

        if self.cfg.pre_init:
            self.trigger(
                pins=[self.cfg.laser_gate_pmod],
                width=self.cfg.laser_initialize_treg, t=t
            )
            t += self.cfg.laser_initialize_treg           

        t += self.cfg.relax_delay_treg

        if self.cfg.mw_pi2_treg > 0:
            self.pulse(ch=self.cfg.mw_channel, t=t)
            t += self.cfg.mw_pi2_treg

        self.sync_all(self.cfg.mw_readout_delay_treg)

        if self.cfg.laser_readout_offset_treg > 3:
            self.trigger_no_off(
                pins=[self.cfg.laser_gate_pmod],
                t=t,
                adc_trig_offset=0)
            t += self.cfg.laser_readout_offset_treg

        self.trigger(
            adcs=[self.cfg.adc_channel],
            adc_trig_offset=0,
            pins=[self.cfg.laser_gate_pmod],
            t=t,
            width=self.cfg.laser_initialize_treg - self.cfg.laser_readout_offset_treg)

        t += self.cfg.laser_initialize_treg            
        t += self.cfg.relax_delay_treg

        self.synci(t)
        self.waiti(0, 0)

    def plot_sequence(cfg=None):
        '''
        Function that plots the pulse sequence generated by this program
        
        Parameters
        ----------
        cfg: `.NVConfiguration` or None(default None)
            If None, this plots the squence with configuration labels
            If a `.NVConfiguration` object is supplied, the configuraiton value are added to the plot
        '''
        graphics_folder = os.path.join(os.path.dirname(__file__), '../../graphics')
        image_path = os.path.join(graphics_folder, 'READOUT.png')
        

        if cfg is None:
            plt.figure(figsize=(10, 10))
            plt.axis('off')
            plt.imshow(mpimg.imread(image_path))
            plt.text(265, 440, "config.soft_avgs", fontsize=14)
            plt.text(205, 305, "config.readout_length_t#", fontsize=12)
            plt.text(445, 305, "config.relax_delay_t#", fontsize=14)
            plt.text(175, 220, "config.mw_pi2_t#", fontsize=14)
            plt.text(210, 340, "config.laser_initialize_t#", fontsize=14)
            plt.title("            Readout Pulse Sequence", fontsize=20)
        else:
            plt.figure(figsize=(10, 10))
            plt.axis('off')
            plt.imshow(mpimg.imread(image_path))
            plt.text(265, 440, "Repeat {} times".format(cfg.soft_avgs), fontsize=14)
            plt.text(205, 305, "readout_length = {} treg".format(int(cfg.readout_length_treg)), fontsize=12)
            plt.text(445, 305, "relax_delay = {} us".format(str(cfg.relax_delay_tus)[:4]), fontsize=14)
            plt.text(175, 220, "pi/2 pulse = {} ns".format(int(cfg.mw_pi2_tns)), fontsize=14)
            plt.text(210, 340, "laser_initialize = {} us".format(int(cfg.laser_initialize_tus)), fontsize=14)
            plt.title("            Readout Pulse Sequence", fontsize=20)
