'''
Subnanosecond Ramsey
=======================================================================
Implements the Ramsey experiment with fine timed microwave pulse delays
to measure the dephasing time, T2*, of the NV center spin. 
'''

from ..nvpulsing.nvaverageprogram import NVAveragerProgram
from ..nvpulsing.nvqicksweep import NVQickSweep
from .readout_helpers import ReadoutHelpers

import numpy as np
from math import floor


class RamseyFineRes(ReadoutHelpers, NVAveragerProgram):
    '''
    An NVAveragerProgram class that generates RF gain and frequency stepping sequences.
    '''
    required_cfg = [
        # Hardware channels
        "mw_channel",
        "adc_channel",
        "laser_gate_pmod",        # 0 for PMOD0_0

        # MW pulse parameters
        "mw_pi2_ftsamp",          # π/2 pulse duration
        "mw_nqz",                 # 1 for f < 2.495 GHz
        "mw_freg",
        "mw_gain",

        # Delay Sweep parameters
        "tau_start_ftsamp",
        "tau_end_ftsamp",
        "scaling_mode",
        "nsweep_points",          # Only used if scaling_mode is 'linear'
        "scaling_factor",         # Only used if scaling_mode is 'exponential'

        # Timing delays
        "mw_to_laser_delay_treg", # Laser turn-on lag relative to MW
        "relax_delay_treg",       # Spin relaxation delay (post laser reinitialization)

        # Readout timing
        "laser_on_treg",
        "readout_reference_start_treg",
        "readout_integration_treg",
        "laser_readout_offset_treg",

        # Experiment control
        "reps",
        "pre_init",
        "get_reference",            # If True, collect MW-off reference readouts
    ]
    
    def initialize(self):
        """
        Sets up π/2 waveforms, FPGA registers, and the τ sweep.

        Sweep modes:
            'linear':      evenly spaced points from tau_start to tau_end.
            'exponential': logarithmically spaced points, scaled by scaling_factor.
        """
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

        # Samples per clock (16 with current version of QICK-DAWG)
        self.samps_per_clk = self.soccfg['gens'][self.cfg.mw_channel]['samps_per_clk']

        # ---------------------
        # Waveform Set-up
        # ---------------------
        # Waveforms must have at least a length of 3 treg
        self.half_pi_waveform_len_treg = \
            max(int(np.ceil((self.cfg.mw_pi2_ftsamp + (self.samps_per_clk-1)) / self.samps_per_clk)), 3)
        
        # Generate waveform with each offset
        for i in range(self.samps_per_clk):
            # π/2 pulses
            data = np.zeros(self.half_pi_waveform_len_treg * 16)
            data[i : i + self.cfg.mw_pi2_ftsamp] = 1
            data *= self.soccfg.get_maxv(self.cfg.mw_channel)
            self.add_envelope(ch=self.cfg.mw_channel, name=f"half_pi_{i}", idata=data, qdata=data)

        # Amount of delay in the waveforms
        self.half_pi_len_unused = self.half_pi_waveform_len_treg*16 - self.cfg.mw_pi2_ftsamp
        
        # ---------------------
        # FPGA Register Setup
        # ---------------------
        # delay_coarse_cycles: coarse-time inter-pulse delay (in FPGA clock cycles, treg).
        self.delay_coarse_cycles = self.new_gen_reg(self.cfg.mw_channel,
                                                name='treg_offset',
                                                init_val=0)

        # delay_fine_samples: fine-time waveform offset (in DAC samples, ftsamp).
        self.delay_fine_samples = self.new_gen_reg(self.cfg.mw_channel,
                                                    name='ftsamp_offset',
                                                    init_val=0)
        
        # Default pulse parameters — phase is overridden per-pulse by set_waveform()
        self.default_pulse_registers(ch=self.cfg.mw_channel,
                                     style='arb',
                                     freq=self.cfg.mw_freg,
                                     gain=self.cfg.mw_gain,
                                     phase=0,
                                     waveform="half_pi_0")
        
        #  τ sweep register (in ftsamp units)
        self.tau_samples = self.new_gen_reg(self.cfg.mw_channel, "tau_samples")

        if self.cfg.scaling_mode == 'exponential':
            self.add_sweep(NVQickSweep(
                self,
                self.tau_samples,
                self.cfg.tau_start_ftsamp,
                self.cfg.tau_end_ftsamp,
                expts=self.cfg.nsweep_points,
                scaling_mode=self.cfg.scaling_mode,
                scaling_factor=self.cfg.scaling_factor)
                )
        elif self.cfg.scaling_mode == 'linear':
            self.add_sweep(NVQickSweep(
                self,
                self.tau_samples,
                self.cfg.tau_start_ftsamp,
                self.cfg.tau_end_ftsamp,
                self.cfg.nsweep_points)
                )
        else:
            assert 0, 'cfg.scaling_mode must be "linear" or "exponential"'
        
        # Direct handles to the waveform address register
        self.address_register = self.get_gen_reg(self.cfg.mw_channel, name='addr')
        
        self.pre_init()
        
    def body(self):
        """
        Initialize spin → π/2_X → delay τ → π/2_X → Readout (and reference).
        """
        self.initialize_spin()
        self.program_pulses(1)
        self.readout_and_reference(self.program_pulses())

    def program_pulses(self):
        """ π/2_X → delay τ → π/2_X """
        # π/2 X pulse
        self.set_pulse_registers(ch=self.cfg.mw_channel)
        self.pulse(ch=self.cfg.mw_channel)
        self.sync_all()

        # π/2 X pulse
        self.set_waveform()
        self.pulse(ch=self.cfg.mw_channel)
        self.sync_all()

        # Reset timing offset for next iteration
        self.delay_fine_samples.reset()

    def set_waveform(self):
        """
        Configures delays and waveform address for the 2nd pulse.

        Coarse delay → sync(delay_coarse_cycles)
        Fine delay   → selects the waveform variant.
        """
        self.offset_computations()
        self.sync(self.delay_coarse_cycles.page, self.delay_coarse_cycles.addr) 

        # Resolve waveform address based on fine offset
        self.address_register.set_to(self.delay_fine_samples, '*', 
                                     self.half_pi_waveform_len_treg, physical_unit = False)

    def offset_computations(self):
        """
        Computes the delay from the end of the 1st waveform to the 2nd pulse.

        The effective delay is:
            effective_delay = τ - elapsed_waveform_deadtime

        This delay is decomposed into:
            • delay_coarse_cycles  (integer FPGA cycles, treg)
            • delay_fine_samples   (waveform offset in ftsamp)
        """
        # Step 1: Compute effective delay (fine-sample units)
        self.math(self.delay_fine_samples.page, self.delay_fine_samples.addr, 
                  self.delay_fine_samples.addr, "+", self.tau_samples.addr)
        self.mathi(self.delay_fine_samples.page, self.delay_fine_samples.addr, 
                    self.delay_fine_samples.addr, "-", self.half_pi_len_unused)

        # Step 2: extract coarse delay (integer FPGA cycles)
        # Equivalent to: // samps_per_clk
        self.bitwi(self.delay_fine_samples.page, self.delay_coarse_cycles.addr, 
                   self.delay_fine_samples.addr, ">>", int(np.log2(self.samps_per_clk)))
        
        # Step 3: retain remainder (fine waveform offset)
        # Equivalent to: % samps_per_clk
        self.bitwi(self.delay_fine_samples.page, self.delay_fine_samples.addr, 
                   self.delay_fine_samples.addr, "&", (self.samps_per_clk-1))
        
    def acquire(self, raw_data=False, *arg, **kwarg):
        """
        Delegates to ReadoutHelpers.acquire() → NVAveragerProgram.acquire(), 
        tagging the sweep axis as 'tau_ftsamp'.
        """
        data = super().acquire(raw_data=raw_data, sweep_param='tau_ftsamp', *arg, **kwarg)
        return data
