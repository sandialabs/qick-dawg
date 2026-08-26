'''
T1 Fine-Resolution Spin Relaxation
=======================================================================
Measures T1 via π pulse followed by swept delay and readout.
Works with π pulse values that have sub-nanosecond timing resolution,
delays are limited to the tproc clock rate (treg).
'''

from itemattribute import ItemAttribute
from qickdawg.util.apply_on_axis_0_n_times import apply_on_axis_0_n_times

from ..nvpulsing.nvaverageprogram import NVAveragerProgram
from ..nvpulsing.nvqicksweep import NVQickSweep
from .readout_helpers import ReadoutHelpers
import numpy as np


class T1FineRes(ReadoutHelpers, NVAveragerProgram):
    '''
    T1 sequence with fixed MW pi pulse and swept waiting delay before readout.
    '''
    required_cfg = [
        # Channels and pmods
        "mw_channel",
        "adc_channel",
        "laser_gate_pmod",        # 0 for PMOD0_0

        # MW pulse parameters
        "mw_pi2_ftsamp",          # π/2 pulse duration
        "mw_nqz",                 # 1 for f < 2.495 GHz
        "mw_freg",
        "mw_gain",

        # Sweep parameters
        "delay_start_treg",
        "delay_end_treg",
        "scaling_mode",
        "nsweep_points",          # Only used if scaling_mode is 'linear'
        "scaling_factor",         # Only used if scaling_mode is 'exponential'


        # Readout and delays
        "mw_to_laser_delay_treg", # Laser turn-on lag relative to MW
        "relax_delay_treg",       # Spin relaxation delay (post laser reinitialization)

        # Readout
        "laser_on_treg",
        "readout_reference_start_treg",
        "readout_integration_treg",
        "laser_readout_offset_treg",

        # Other
        "reps",
        "pre_init",
        "get_reference",            # If True, collect MW-off reference readouts
    ]

    def initialize(self):
        # ---------------------
        # General Config
        # ---------------------
        self.check_cfg()

        if self.cfg.mw_gain < 0:
            assert 0, 'Smallest Microwave gain must be postive'
        elif self.cfg.mw_gain > 32767: # 2**15 - 1
            assert 0, 'Largest Microwave gain exceeds maximum value'

        self.declare_gen(ch=self.cfg.mw_channel, nqz=self.cfg.mw_nqz)
        self.setup_helper_registers(self.cfg.mw_channel)

        self.setup_readout()
        
        self.samps_per_clk = self.soccfg['gens'][self.cfg.mw_channel]['samps_per_clk']

        self.mw_pulse_waveform_len_treg = max(int(np.ceil(self.cfg.mw_pi_ftsamp / self.samps_per_clk)), 3)
        self.mw_pulse_waveform_len_ftsamp = self.mw_pulse_waveform_len_treg * self.samps_per_clk
        # Create single pi pulse waveform
        data = np.zeros(self.mw_pulse_waveform_len_ftsamp)
        data[:self.cfg.mw_pi_ftsamp] = 1
        data *= self.soccfg.get_maxv(self.cfg.mw_channel)
        self.add_envelope(ch=self.cfg.mw_channel, name="pulse", idata=data, qdata=data)
        
        # MW pulse register
        self.default_pulse_registers(ch=self.cfg.mw_channel,
                                     style='arb',
                                     freq=self.cfg.mw_freg,
                                     gain=self.cfg.mw_gain,
                                     waveform="pulse",
                                     phase=0)
        # Pulse registers can be armed immediately (no variable parameters)
        self.set_pulse_registers(ch=self.cfg.mw_channel)
        
        # Setup T1-delay sweep (time-register units).
        self.delay_register = self.new_gen_reg(self.cfg.mw_channel, "delay")

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
        else:
            assert 0, 'cfg.scaling_mode must be "linear" or "exponential"'
        
        self.pre_init()

    def body(self):
        self.initialize_spin()
        self.program_pulse()
        self.readout_and_reference(self.program_pulse)

    def program_pulse(self):
        self.pulse(ch=self.cfg.mw_channel)
        self.sync(self.delay_register.page, self.delay_register.addr)
        self.sync_all()
    
    def acquire(self, raw_data=False, *arg, **kwarg):
        # self.acquire --> ReadoutHelpers.acquire --> NVAveragerProgram.acquire
        data = super().acquire(raw_data=raw_data, sweep_param='delay_treg', *arg, **kwarg)
        return data