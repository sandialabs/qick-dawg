'''
Counting Duration
=======================================================================
Min resolution of 200ps for steps between pulses in Rabi sequence
using fine control of waveform start address and phase.

Modified from Tommy's RabiFineRes program. See his notebook for more details on the method.
'''

import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from itemattribute import ItemAttribute
from qickdawg.util.apply_on_axis_0_n_times import apply_on_axis_0_n_times

from qickdawg.nvpulsing.nvaverageprogram import NVAveragerProgram
from qickdawg.nvpulsing.nvqicksweep import NVQickSweep
from .readout_helpers import ReadoutHelpers
import numpy as np

# NVAveragerProgram first as this class should only use the
# Use the default acquire method from NVAveragerProgram, when acquire.super() is called
class CountingDurationFineRes(NVAveragerProgram, ReadoutHelpers):
    '''
    Rabi sub-nanosecond resolution pulsing program
    '''
    required_cfg = [
        # Channels and pmods
        "mw_channel",
        "adc_channel",
        "laser_gate_pmod", # should be 0 for PMOD0_0

        # MW pulse parameters
        "mw_pi_ftsamp", # length of mw
        "mw_freg", # Microwave freq 
        "mw_nqz", # 1 at 1405 MHz
        "mw_gain", # MW Gain

        # Readout and delays
        "mw_to_laser_delay_treg", # How long do we need to delay the mw, to ensure the laser pulse is correctly timed before it
        "relax_delay_treg", # delay between laser and next MW pulse

        # Readout
        "laser_on_treg",
        "readout_reference_start_treg",
        "readout_integration_treg",
        "laser_readout_offset_treg",

        # Other
        "reps",
        "pre_init",
        "get_reference",  # Whether to acquire a reference readout with MW gain = 0
    ]

    def initialize(self):
        self.check_cfg()

        # Get mw registers
        self.declare_gen(ch=self.cfg.mw_channel, nqz=self.cfg.mw_nqz)
        self.setup_helper_registers(self.cfg.mw_channel)

        # Setup laser
        self.setup_readout()

        # Get samps per clk for later calculations
        self.samps_per_clk = self.soccfg['gens'][self.cfg.mw_channel]['samps_per_clk']
        # Configure the waveforms for fine resolution pulse steps (must be >= 3 treg units)
        self.mw_pulse_waveform_len_treg = max(int(np.ceil(self.cfg.mw_pi_ftsamp / self.samps_per_clk)), 3)
        self.mw_pulse_waveform_len_ftsamp = self.mw_pulse_waveform_len_treg * self.samps_per_clk
        # Create waveform with exact duration
        data = np.zeros(self.mw_pulse_waveform_len_ftsamp)
        data[:self.cfg.mw_pi_ftsamp] = 1
        data *= self.soccfg.get_maxv(self.cfg.mw_channel)
        self.add_envelope(ch=self.cfg.mw_channel, name="pulse", idata=data, qdata=None)
        # MW pulse register
        self.default_pulse_registers(ch=self.cfg.mw_channel,
                                     style='arb',
                                     freq=self.cfg.mw_freg,
                                     gain=self.cfg.mw_gain,
                                     waveform="pulse",
                                     phase=0)
        # Explicitly arm the pulse
        self.set_pulse_registers(ch=self.cfg.mw_channel)

        self.pre_init()

    def body(self):
        self.initialize_spin()
        self.program_pulse()
        self.readout_and_reference(self.program_pulse)

    def program_pulse(self):
        """Program the MW pulse sequence"""
        self.pulse(ch=self.cfg.mw_channel)
        self.sync_all()
    
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

        norm_factor = self.cfg.readout_integration_tns * 1e-9 * self.cfg.reps
        for key in ['signal1', 'reference1', 'signal2', 'reference2']:
            d[key + '_cts_s'] = d[key] / norm_factor

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
