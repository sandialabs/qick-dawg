'''
Subnanosecond CPMG-XY Test
=======================================================================
Subnanosecond CPMG-XY Test class used to test the shape of RF envelopes.
Implements full experiment with laser initialization and readout.
'''

from ..nvpulsing.nvaverageprogram import NVAveragerProgram
from ..nvpulsing.nvqicksweep import NVQickSweep
from .readout_helpers import ReadoutHelpers

import numpy as np
from math import floor


class HahnEchoFineRes(ReadoutHelpers, NVAveragerProgram):
    '''
    An NVAveragerProgram class that generates RF gain and frequency stepping sequences.
    '''
    required_cfg = [
        # Channels and pmods
        "mw_channel",
        "adc_channel",
        "laser_gate_pmod", # should be 0 for PMOD0_0

        # MW pulse parameters
        "mw_pi2_ftsamp", # length of pi/2 pulse
        "mw_nqz", # 1 < 2.495 GHz
        "mw_freg",
        "mw_gain",

        # Delay Sweep parameters
        "tau_start_ftsamp",
        "tau_end_ftsamp",
        "nsweep_points",
        "scaling_mode",
        "scaling_factor", # Only used if scaling_mode is 'exponential'

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
        """
        Sets up the waveforms, registers and sweeps, for pi and pi/2 pulses, and delays. 
        """
        # ---------------------
        # General Config
        # ---------------------
        self.check_cfg()

        if self.cfg.mw_gain < 0:
            assert 0, 'Smallest Microwave gain must be postive'
        elif self.cfg.mw_gain > 32767: # 2**15 - 1
            assert 0, 'Largest Microwave gain exceeds maximum value'

        # Get mw registers
        self.declare_gen(ch=self.cfg.mw_channel, nqz=self.cfg.mw_nqz)
        self.setup_helper_registers(self.cfg.mw_channel)

        # Setup laser
        self.setup_readout()

        # Get samples per clock (16 with current version of QICK-DAWG)
        self.samps_per_clk = self.soccfg['gens'][self.cfg.mw_channel]['samps_per_clk']

        # ---------------------
        # Waveform Set-up
        # ---------------------
        # Waveforms must have at least a length of 3 treg
        self.pi_waveform_len_treg = \
            max(int(np.ceil((self.cfg.mw_pi2_ftsamp*2 + (self.samps_per_clk-1)) / self.samps_per_clk)), 3)
        self.half_pi_waveform_len_treg = \
            max(int(np.ceil((self.cfg.mw_pi2_ftsamp + (self.samps_per_clk-1)) / self.samps_per_clk)), 3)
        
        # Generate waveforms with each offset
        for i in range(self.samps_per_clk):
            # pi pulses
            data = np.zeros(self.pi_waveform_len_treg * 16)
            data[i: i + self.cfg.mw_pi2_ftsamp*2] = 1
            data *= self.soccfg.get_maxv(self.cfg.mw_channel)
            self.add_envelope(ch=self.cfg.mw_channel, name=f"pi_{i}", idata=data, qdata=data)

            # half pi pulses
            data = np.zeros(self.half_pi_waveform_len_treg * 16)
            data[i : i + self.cfg.mw_pi2_ftsamp] = 1
            data *= self.soccfg.get_maxv(self.cfg.mw_channel)
            self.add_envelope(ch=self.cfg.mw_channel, name=f"half_pi_{i}", idata=data, qdata=data)

        # Amount of delay in the waveforms
        self.pi_len_unused = self.pi_waveform_len_treg*16 - self.cfg.mw_pi2_ftsamp*2
        self.half_pi_len_unused = self.half_pi_waveform_len_treg*16 - self.cfg.mw_pi2_ftsamp
        
        # Register to hold the FPGA/tproc delay between pulses
        self.treg_offset_register = self.new_gen_reg(self.cfg.mw_channel,
                                                name='treg_offset',
                                                init_val=0)

        self.ftsamp_offset_register = self.new_gen_reg(self.cfg.mw_channel,
                                                    name='ftsamp_offset',
                                                    init_val=0)
        
        # Initialize pulse register defaults
        self.default_pulse_registers(ch=self.cfg.mw_channel,
                                     style='arb',
                                     freq=self.cfg.mw_freg,
                                     gain=self.cfg.mw_gain)
        
        self.tau_samples = self.new_gen_reg(self.cfg.mw_channel, "tau_samples")

        if self.cfg.scaling_mode == 'exponential':
            self.add_sweep(NVQickSweep(
                self,
                self.tau_samples,
                self.cfg.tau_start_ftsamp,
                self.cfg.tau_end_ftsamp,
                expts=self.cfg.nsweep_points,
                scaling_mode=self.cfg.scaling_mode,
                scaling_factor=self.cfg.scaling_factor))

        elif self.cfg.scaling_mode == 'linear':
            self.add_sweep(NVQickSweep(
                self,
                self.tau_samples,
                self.cfg.tau_start_ftsamp,
                self.cfg.tau_end_ftsamp,
                self.cfg.nsweep_points))
        else:
            assert 0, 'cfg.scaling_mode must be "linear" or "exponential"'
        
        # waveform address register
        self.address_register = self.get_gen_reg(self.cfg.mw_channel, name='addr')
        
        # Pre-initialization
        self.pre_init()
        

    def body(self):
        """
        The full pulse sequence: laser init -> RF pulses -> readout
        """
        self.initialize_spin() # misnomer this just delays for mw_to_laser_delay_treg
        self.program_pulses(1)
        self.signal_and_reference_readout(lambda: self.program_pulses(2))


    def program_pulses(self, iter):
        """
        1. pi: index = 0
        2. pi/2: index <= index + tau - half_pi_len_unused
        3. pi: index <= index + tau - pi_len_unused
        """
        # Pi/2 X pulse
        self.set_pulse_registers(ch=self.cfg.mw_channel, waveform="half_pi_0", phase=self.deg2reg(0))
        self.pulse(ch=self.cfg.mw_channel)
        self.sync_all()
        # pi X pulse
        self.set_pulse_registers(ch=self.cfg.mw_channel, waveform="pi_0", phase=0)
        self.set_waveform(pi_pulse=True)
        self.pulse(ch=self.cfg.mw_channel)
        self.sync_all()
        # pi/2 X pulse
        self.set_pulse_registers(ch=self.cfg.mw_channel, waveform="half_pi_0", phase=0)
        self.set_waveform(pi_pulse=False)
        self.pulse(ch=self.cfg.mw_channel)
        self.sync_all()

        # Reset for next loop
        self.ftsamp_offset_register.reset() # reset to initial value 


    def set_waveform(self, pi_pulse=True):
        """
        Configures the assembly code necessary for setting the waveform.
        """
        # Compute offset (fine and coarse)
        self.offset_computations(after_half_pi=pi_pulse)
        self.sync(self.treg_offset_register.page, self.treg_offset_register.addr) 

        # Update the address register to correspond to the correct waveform
        self.address_register.set_to(self.ftsamp_offset_register, '*', 
                                     self.pi_waveform_len_treg+self.half_pi_waveform_len_treg, physical_unit = False)
        if not pi_pulse: # pi/2 Waveforms are stored after pi waveforms
            self.address_register.set_to(self.address_register, '+', 
                                     self.pi_waveform_len_treg, physical_unit = False)


    def offset_computations(self, after_half_pi):
        # index <== index + tau
        self.math(self.ftsamp_offset_register.page, self.ftsamp_offset_register.addr, 
                  self.ftsamp_offset_register.addr, "+", self.tau_samples.addr)
        # index <== index - pi_len_unused or pi/2_len_unused based on previous pulse
        subtract_from_tau = self.half_pi_len_unused if after_half_pi else self.pi_len_unused
        self.mathi(self.ftsamp_offset_register.page, self.ftsamp_offset_register.addr, 
                    self.ftsamp_offset_register.addr, "-", subtract_from_tau)
        
        # treg_offset_register <== ftsamp_offset_register >> 4 (global offset)
        # Computes coarse delay (in tregs)
        self.bitwi(self.ftsamp_offset_register.page, self.treg_offset_register.addr, 
                   self.ftsamp_offset_register.addr, ">>", int(np.log2(self.samps_per_clk)))
        # ftsamp_offset_register <== ftsamp_offset_register & 15
        # Computes the fine delay (in samples, ie pulse offset within the waveform) 
        self.bitwi(self.ftsamp_offset_register.page, self.ftsamp_offset_register.addr, 
                   self.ftsamp_offset_register.addr, "&", (self.samps_per_clk-1))
        

    def acquire(self, raw_data=False, *arg, **kwarg):
        # self.acquire --> ReadoutHelpers.acquire --> NVAveragerProgram.acquire
        data = super().acquire(raw_data=raw_data, sweep_param='tau_ftsamp', *arg, **kwarg)
        return data


