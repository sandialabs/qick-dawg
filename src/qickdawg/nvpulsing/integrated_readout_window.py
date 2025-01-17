from .nvaverageprogram import NVAveragerProgram
from .nvqicksweep import NVQickSweep

import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import os
import numpy as np
from itemattribute import ItemAttribute
from ..util import apply_on_axis_0_n_times


class IntegratedReadoutWindow(NVAveragerProgram):
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
                    "mw_pi2_treg",
                    "pre_init",
                    "laser_gate_pmod",
                    "laser_on_treg",
                    "relax_delay_treg",
                    "mw_readout_delay_treg",
                    "reps",
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

        self.setup_readout()

        # configure pulse defaults and initial parameters for microwave
        self.declare_gen(
            ch=self.cfg.mw_channel,
            nqz=self.cfg.mw_nqz)        

        self.default_pulse_registers(
            ch=self.cfg.mw_channel,
            style='const',
            freq=self.cfg.mw_freg,
            gain=self.cfg.mw_gain,
            length=self.cfg.mw_pi2_treg,
            phase=0)

        self.set_pulse_registers(ch=self.cfg.mw_channel)
                                 
        self.synci(400)  # give processor some time to configure pulses

        if self.cfg.pre_init:

            self.trigger(
                pins=[self.cfg.laser_gate_pmod],
                width=self.cfg.laser_on_treg, 
                adc_trig_offset=self.cfg.laser_readout_offset_treg)
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
        self.sync_all()
        self.synci(self.cfg.mw_readout_delay_treg)
        self.ttl_readout()

        self.synci(self.cfg.mw_pi2_treg * 2)
        self.synci(self.cfg.mw_readout_delay_treg)
        self.ttl_readout()

    def acquire(self, raw_data=False, *arg, **kwarg):

        data = super().acquire(readouts_per_experiment=4, *arg, **kwarg)

        if raw_data:
            return data

        data = np.reshape(data, self.data_shape)

        d = ItemAttribute()

        d.signal1 = data[..., 0]
        d.reference1 = data[..., 1]
        d.signal2 = data[..., 2]
        d.reference2 = data[..., 3]

        n = len(d.signal1.shape)

        if self.cfg.edge_counting is False:
            ret_type = float
            func = np.mean
        else:
            ret_type = int
            func = np.sum

        if self.cfg.edge_counting is False:
            d.contrast1 = ((d.signal1 - d.reference1) / d.reference1 * 100)
            d.contrast2 = ((d.signal2 - d.reference2) / d.reference2 * 100)
        else:
            d.contrast1 = d.signal1 - d.reference1
            d.contrast2 = d.signal2 - d.reference2

        d.contrast = d.contrast1 - d.contrast2

        d.contrast1 = apply_on_axis_0_n_times(d.contrast1.astype(ret_type), func, n)
        d.signal1 = apply_on_axis_0_n_times(d.signal1.astype(ret_type), func, n)
        d.reference1 = apply_on_axis_0_n_times(d.reference1.astype(ret_type), func, n)
        
        d.contrast2 = apply_on_axis_0_n_times(d.contrast2.astype(ret_type), func, n)
        d.signal2 = apply_on_axis_0_n_times(d.signal2.astype(ret_type), func, n)
        d.reference2 = apply_on_axis_0_n_times(d.reference2.astype(ret_type), func, n)

        d.contrast = apply_on_axis_0_n_times(d.contrast.astype(ret_type), func, n)

        return d

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
            plt.text(
                195,
                580,
                " Sweep pi/2 pulse time linearly from config.mw_start to config.mw_end in config.mw_delta sized steps",
                fontsize=12)
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

            string = f"Sweep pi/2 pulse time linearly from {int(cfg.mw_start_treg)} time register"
            string += f" to {int(cfg.mw_end_treg)} time register in steps of "
            string += f"{str(cfg.mw_delta_treg)[:4]} time register"
            plt.text(195, 580, string, fontsize=12)

            plt.text(265, 370, "readout_integration  \n       = {} ns".format(
                int(cfg.readout_integration_tns)), fontsize=14)
            plt.text(527, 370, "readout_integration  \n      = {} ns".format(
                int(cfg.readout_integration_tns)), fontsize=14)
            plt.text(190, 368, " pi/2\npulse", fontsize=14)
            plt.text(735, 370, "relax_delay \n = {} ns".format(int(cfg.relax_delay_tns)), fontsize=14)
            plt.text(235, 407, "laser_offset = {} ns".format(int(cfg.laser_readout_offset_tns)), fontsize=14)
            plt.text(430, 407, "readout_reference_start = {} us".format(
                int(cfg.readout_reference_start_tus)), fontsize=14)
            plt.title("           Rabi Oscillation Pulse Sequence", fontsize=20)
