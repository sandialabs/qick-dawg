'''
RabiSweep
=======================================================================
An NVAveragerProgram class that generates and executes a measurement which takes
four measurements while sweeping the microwave output length to generate a Rabi
oscillation dataset which can be used to determine the pi and pi/2 pulse lenghts
for future measurements
'''

from .nvaverageprogram import NVAveragerProgram
from .nvqicksweep import NVQickSweep

import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import os
import numpy as np


class RabiSweep(NVAveragerProgram):
    '''
    An NVAveragerProgram class that generates and executes a sequence used
    to determine the pi (pi/2) pulse lenghts for your experimetanl configuration

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
    required_cfg = ["adc_channel",
                    "readout_integration_treg",
                    "mw_channel",
                    "mw_nqz",
                    "mw_gain",
                    "mw_freg",
                    "mw_start_treg",
                    "mw_end_treg",
                    "nsweep_points",
                    "pre_init",
                    "laser_gate_pmod",
                    "laser_on_treg",
                    "adc_trigger_offset_treg",
                    "relax_delay_treg",
                    "mw_readout_delay_treg",
                    "reps",
                    "mw_delta_treg",
                    "readout_reference_start_treg"
                    ]

    def initialize(self):
        '''
        Method that generates the assembly code that is sets up adcs and sources. 
        For RabiSweep this:
        configures the adc to acquire points for self.cfg.readout_integration_t#. 
        configures the microwave channel 
        configures the sweep parameters
        initiailzes the spin state with a laser pulse
        '''
        self.check_cfg()

        self.declare_readout(ch=self.cfg.adc_channel,
                             freq=0,
                             length=self.cfg.readout_integration_treg,
                             sel="input")

        # configure pulse defaults and initial parameters for microwave
        self.declare_gen(
            ch=self.cfg.mw_channel,
            nqz=self.cfg.mw_nqz)        

        self.default_pulse_registers(
            ch=self.cfg.mw_channel,
            style='const',
            freq=self.cfg.mw_freg,
            gain=self.cfg.mw_gain,
            phase=0)

        self.set_pulse_registers(ch=self.cfg.mw_channel,
                                 length=self.cfg.mw_start_treg)

        # configure the sweep
        self.mw_length_register = self.new_gen_reg(self.cfg.mw_channel, 
                                                   name='mw_length', 
                                                   init_val=self.cfg.mw_start_treg)

        self.add_sweep(NVQickSweep(self, 
                                   reg=self.mw_length_register, 
                                   start=self.cfg.mw_start_treg, 
                                   stop=self.cfg.mw_end_treg, 
                                   expts=self.cfg.nsweep_points,
                                   label='mw_length',
                                   mw_channel=self.cfg.mw_channel))

        self.synci(400)  # give processor some time to configure pulses

        if self.cfg.pre_init:

            self.trigger(
                pins=[self.cfg.laser_gate_pmod],
                width=self.cfg.laser_on_treg, 
                adc_trig_offset=self.cfg.adc_trigger_offset_treg)
            self.sync_all(self.cfg.laser_on_treg)

        self.wait_all()
        self.sync_all(self.cfg.relax_delay_treg)

    def body(self):
        '''
        Method that generates the assembly code that is looped over or repeated. 
        For RabiSweep this peforms four measurements at a time and does two pulse sequences:
        1. Microwave pulse followed by readout and reference emasurement
        2. No micrwave pulse followed by readout and reference 
        '''

        self.pulse(ch=self.cfg.mw_channel, t=0)
        self.sync(self.mw_length_register.page, self.mw_length_register.addr)
        self.synci(self.cfg.mw_readout_delay_treg)
        self.ttl_readout()

        self.sync(self.mw_length_register.page, self.mw_length_register.addr)
        self.synci(self.cfg.mw_readout_delay_treg)
        self.ttl_readout()

    def acquire(self, raw_data=False, *arg, **kwarg):

        data = super().acquire(readouts_per_experiment=4, *arg, **kwarg)

        if raw_data is False:
            data = self.analyze_pulse_sequence_results(data)

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
        graphics_folder = os.path.join(os.path.dirname(__file__), '../../graphics')
        image_path = os.path.join(graphics_folder, 'RABI.png')


        if cfg is None:
            plt.figure(figsize=(15, 15))
            plt.axis('off')
            plt.imshow(mpimg.imread(image_path))
            plt.text(455, 510, "config.reps", fontsize=14)
            plt.text(350, 440, "config.laser_on", fontsize=14)
            plt.text(195, 580, " Sweep pi/2 pulse time linearly from config.mw_start to config.mw_end in config.mw_delta sized steps", fontsize=12)
            plt.text(265, 355, "config.readout_integration", fontsize=14)
            plt.text(527, 355, " config.readout_integration", fontsize=14)
            plt.text(190, 368, " pi/2\npulse", fontsize=14)
            plt.text(735, 355, "config.relax_delay", fontsize=14)
            plt.text(220, 407, "config.laser_readout_offset", fontsize=14)
            plt.text(430, 407, "config.readout_reference_start", fontsize=14)
            plt.title("           Rabi Oscillation Pulse Sequence", fontsize=20)

        else:
            plt.figure(figsize=(15, 15))
            plt.axis('off')
            plt.imshow(mpimg.imread(image_path))
            plt.text(420, 510, "Repeat {} times".format(cfg.reps), fontsize=14)
            plt.text(350, 440, "laser_on_tus = {} us".format(str(cfg.laser_on_tus)[:4]), fontsize=14)
            plt.text(195, 580, " Sweep pi/2 pulse time linearly from {} time register to {} time register in steps of {} time register".format(int(cfg.mw_start_treg), int(cfg.mw_end_treg), str(cfg.mw_delta_treg)[:4]), fontsize=12)
            plt.text(265, 370, "readout_integration  \n       = {} ns".format(int(cfg.readout_integration_tns)), fontsize=14)
            plt.text(527, 370, "readout_integration  \n      = {} ns".format(int(cfg.readout_integration_tns)), fontsize=14)
            plt.text(190, 368, " pi/2\npulse", fontsize=14)
            plt.text(735, 370, "relax_delay \n = {} ns".format(int(cfg.relax_delay_tns)), fontsize=14)
            plt.text(235, 407, "laser_offset = {} ns".format(int(cfg.laser_readout_offset_tns)), fontsize=14)
            plt.text(430, 407, "readout_reference_start = {} us".format(int(cfg.readout_reference_start_tus)), fontsize=14)
            plt.title("           Rabi Oscillation Pulse Sequence", fontsize=20)
