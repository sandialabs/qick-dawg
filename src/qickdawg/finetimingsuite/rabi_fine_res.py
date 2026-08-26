'''
Rabi sub-nanosecond resolution pulsing program
=======================================================================
Performs Rabi sweep with a minimum mw pulse step size of 1 ftsamp (200ps)
'''

from qickdawg.nvpulsing.nvaverageprogram import NVAveragerProgram
from qickdawg.nvpulsing.nvqicksweep import NVQickSweep
from .readout_helpers import ReadoutHelpers
import numpy as np

class RabiFineRes(ReadoutHelpers, NVAveragerProgram):
    '''
    Rabi sub-nanosecond resolution pulsing program
    '''
    required_cfg = [      
        # Channels and pmods
        "mw_channel",
        "adc_channel",
        "laser_gate_pmod",        # 0 for PMOD0_0

        # MW pulse parameters
        "mw_nqz",                 # 1 for f < 2.495 GHz
        "mw_freg",
        "mw_gain",

        # Sweep parameters
        "mw_duration_start_ftsamp",
        "mw_duration_end_ftsamp",
        "nsweep_points",

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
        "get_reference",  # Whether to acquire a reference readout with MW gain = 0  
    ]

    def initialize(self):
        self.check_cfg()

        # Get mw registers
        self.declare_gen(ch=self.cfg.mw_channel, nqz=self.cfg.mw_nqz)
        self.setup_helper_registers(self.cfg.mw_channel)

        # Setup laser
        self.setup_readout()

        # Samples per clock (16 with current version of QICK-DAWG)
        self.samps_per_clk = self.soccfg['gens'][self.cfg.mw_channel]['samps_per_clk']

        # ---------------------
        # Waveform Set-up
        # ---------------------
        self.mw_pulse_waveform_len_treg = 4
        self.mw_pulse_waveform_len_ftsamp = self.mw_pulse_waveform_len_treg * self.samps_per_clk  # in ftsamp units
        
        for i in np.arange(0, self.mw_pulse_waveform_len_ftsamp+1, 1):
            data = np.zeros(self.mw_pulse_waveform_len_ftsamp)
            data[:i] = 1
            data *= self.soccfg.get_maxv(self.cfg.mw_channel)
            self.add_envelope(ch=self.cfg.mw_channel, name=f"pulse_{i}", idata=data, qdata=data)

        # ---------------------
        # FPGA Register Setup
        # ---------------------
        self.address_register = self.get_gen_reg(self.cfg.mw_channel, name='addr')
        
        self.default_pulse_registers(ch=self.cfg.mw_channel,
                                     style='arb',
                                     freq=self.cfg.mw_freg,
                                     gain=self.cfg.mw_gain,
                                     phase = 0)
        
        # mw duration register
        self.mw_duration_register = self.new_gen_reg(self.cfg.mw_channel,
                                                   name='mw_duration',
                                                   init_val=self.cfg.mw_duration_start_ftsamp)

        # mw coarse and fine pulse loop registers
        self.coarse_mw_register = self.new_gen_reg(self.cfg.mw_channel,
                                                   name='mw_coarse',
                                                   init_val=0)
        self.fine_mw_register = self.new_gen_reg(self.cfg.mw_channel,
                                                   name='mw_fine',
                                                   init_val=0)

        self.add_sweep(NVQickSweep(self,
                                   reg=self.mw_duration_register,
                                   start=self.cfg.mw_duration_start_ftsamp,
                                   stop=self.cfg.mw_duration_end_ftsamp,
                                   expts=self.cfg.nsweep_points))
        
        self.pre_init() # Give tproc time to get ahead

    def body(self):
        self.initialize_spin()
        self.program_pulses(1)
        self.readout_and_reference(lambda: self.program_pulses(2))

    def program_pulses(self, num):
        # set coarse and fine registers based on duration. coarse is x//64 and then multiply by 4 to get treg units
        self.bitwi(self.coarse_mw_register.page, self.coarse_mw_register.addr, self.mw_duration_register.addr, ">>", int(np.log2(self.mw_pulse_waveform_len_ftsamp)))
        self.bitwi(self.coarse_mw_register.page, self.coarse_mw_register.addr, self.coarse_mw_register.addr, "<<", int(np.log2(self.mw_pulse_waveform_len_treg)))
        self.bitwi(self.fine_mw_register.page, self.fine_mw_register.addr, self.mw_duration_register.addr, "&", self.mw_pulse_waveform_len_ftsamp - 1)
        
        # if there is no coarse part just do fine part
        self.condj(self.coarse_mw_register.page, self.coarse_mw_register.addr, "==", 0, f"JUMP_NO_COARSE_{num}")

        # since using sync all (and need to use it for accurate timing), it will always play a pulse so need to subtract onewaveform length
        self.coarse_mw_register.set_to(self.coarse_mw_register, "-", self.mw_pulse_waveform_len_treg, physical_unit=False)
        self.set_pulse_registers(ch=self.cfg.mw_channel, waveform=f"pulse_{self.mw_pulse_waveform_len_ftsamp}", mode = "periodic")
        self.pulse(ch=self.cfg.mw_channel) 
        self.sync_all()
        self.sync(self.coarse_mw_register.page, self.coarse_mw_register.addr)

        self.label(f"JUMP_NO_COARSE_{num}")
        self.set_pulse_registers(ch=self.cfg.mw_channel, waveform=f"pulse_{0}", mode = "oneshot")
        self.address_register.set_to(self.fine_mw_register, '*', self.mw_pulse_waveform_len_treg, physical_unit = False)
        self.pulse(ch=self.cfg.mw_channel)
        self.sync_all()

    def acquire(self, raw_data=False, *arg, **kwarg):
        """
        Delegates to ReadoutHelpers.acquire() → NVAveragerProgram.acquire(), 
        tagging the sweep axis as 'mw_duration_ftsamp'.
        """
        data = super().acquire(raw_data=raw_data, sweep_param='mw_duration_ftsamp', *arg, **kwarg)
        return data
