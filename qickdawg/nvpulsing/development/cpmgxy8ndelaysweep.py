from .nvaverageprogram import NVAveragerProgram
from .nvqicksweep import NVQickSweep
from ..util import ItemAttribute

import numpy as np

class CPMGXY8nDelaySweep(NVAveragerProgram):
    def initialize(self):
        """
        This is run at the beginning of each acquire or acquire_decimated command
        """

        self.declare_readout(ch=0,
                             freq=0,
                             length=self.cfg.readout_integration_treg,
                             sel="input")

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
        
        
        # Delcare laser controls
        if self.cfg.laser_control == 'aom':

            self.declare_gen(ch=self.cfg.aom_channel, nqz=1)

            self.set_pulse_registers(ch=self.cfg.aom_channel, 
                                        style='const',
                                        freq=self.cfg.aom_freg,
                                        gain=self.cfg.aom_gain,
                                        length=self.cfg.laser_on_treg,
                                        phase=0)
        elif self.cfg.laser_control == 'ttl':
            pass
        else:
            assert 0, "cfg.laser_control must be assigned to 'aom' or 'ttl'"


        # Addd loops
        self.delay_register = self.new_gen_reg(self.cfg.mw_channel,
                                               name='delay', 
                                               init_val=self.cfg.delay_start_treg)
        self.time_register = self.new_gen_reg(self.cfg.mw_channel,
                                               name='time', 
                                               init_val=0)


        if self.cfg.scaling_mode=='exponential':
            self.add_sweep(NVQickSweep(self, 
                                    self.delay_register,
                                    self.cfg.delay_start_treg, 
                                    self.cfg.delay_end_treg,
                                    expts=self.cfg.nsweep_points,
                                    scaling_mode= self.cfg.scaling_mode,
                                    scaling_factor=self.cfg.scaling_factor))

        else:
            self.add_sweep(NVQickSweep(self, 
                                    self.delay_register,
                                    self.cfg.delay_start_treg, 
                                    self.cfg.delay_end_treg,
                                    self.cfg.nsweep_points))

        self.synci(400)  # give processor some time to self.cfgure pulses

        if self.cfg.pre_init:
            self.pulse(ch=self.cfg.aom_channel)                
            self.wait_all()
            self.sync_all(self.cfg.relax_delay_treg)

            
        ##   NEWEST ADD
        self.mw_length_register = self.get_gen_reg(self.mw_channel, name='time')    

    def body(self):
        ## Pulse Sequence 1

        # pi/2 phase x 
        self.set_pulse_registers(ch=self.cfg.mw_channel, phase=self.deg2reg(0))
        self.pulse(ch=self.cfg.mw_channel)
        self.mathi(0, self.mw_length_register, self.mw_length_register, '+', self.cfg.mw_pi2_treg)
        # 1 tau delay 
        self.math(0, self.mw_length_register, self.mw_length_register, '+', self.delay_register.addr)

        for phase in [0, 90, 0, 90, 90, 0, 90, 0]:

            self.set_pulse_registers(ch=self.cfg.mw_channel, phase=self.deg2reg(phase))

            # tau delay

            self.math(0, 26, 26, '+', self.delay_register.addr)

            self.pulse(ch=self.cfg.mw_channel, t=None)

            self.mathi(0, 26, 26, '+', self.cfg.mw_pi2_treg)

            self.pulse(ch=self.cfg.mw_channel, t=None)

            self.mathi(0, 26, 26, '+', self.cfg.mw_pi2_treg)

            # tau delay

            self.math(0, 26, 26, '+', self.delay_register.addr)


        #pi/2 phase x
        self.set_pulse_registers(ch=self.cfg.mw_channel, phase=self.deg2reg(0))
        self.pulse(ch=self.cfg.mw_channel)
        self.mathi(0, 26, 26, '+', self.cfg.mw_pi2_treg)
    
        self.sync(0, 26)
        # readout
        if self.cfg.laser_control == 'aom':
            self.pulse(ch=self.cfg.aom_channel)   
        if self.cfg.laser_control == 'ttl':
            self.trigger(
                pins=[self.cfg.laser_gate_pmod],
                width=self.cfg.readout_integration_treg
                )
        t = self.cfg.laser_readout_offset_treg
        self.trigger(adcs=[0],
                    pins=[0, 1],
                    adc_trig_offset=0,
                    t = t)
        t +=  self.cfg.readout_reference_treg
        self.trigger(adcs=[0],
                    pins=[0, 1],                     
                    adc_trig_offset=0,
                    t = t)
        # Pause between pulse sequences, let aom turn off
        self.wait_all()
        self.sync_all(self.cfg.relax_delay_treg)

        ## Pulse sequence 2

        # pi/2 phase x 
        self.set_pulse_registers(ch=self.cfg.mw_channel, phase=self.deg2reg(0))
        self.pulse(ch=self.cfg.mw_channel)
        self.mathi(0, 26, 26, '+', self.cfg.mw_pi2_treg)
        # 1 tau delay 
        self.math(0, 26, 26, '+', self.delay_register.addr)

        for phase in [0, 90, 0, 90, 90, 0, 90, 0]:

            self.set_pulse_registers(ch=self.cfg.mw_channel, phase=self.deg2reg(phase))

            # tau delay

            self.math(0, 26, 26, '+', self.delay_register.addr)

            self.pulse(ch=self.cfg.mw_channel, t=None)

            self.mathi(0, 26, 26, '+', self.cfg.mw_pi2_treg)

            self.pulse(ch=self.cfg.mw_channel, t=None)

            self.mathi(0, 26, 26, '+', self.cfg.mw_pi2_treg)

            # tau delay

            self.math(0, 26, 26, '+', self.delay_register.addr)
  

        #pi/2 phase -x
        self.set_pulse_registers(ch=self.cfg.mw_channel, phase=self.deg2reg(180))
        self.pulse(ch=self.cfg.mw_channel)
        self.mathi(0, 26, 26, '+', self.cfg.mw_pi2_treg)

        self.sync(0, 26)
        # readout
        # readout
        if self.cfg.laser_control == 'aom':
            self.pulse(ch=self.cfg.aom_channel)   
        if self.cfg.laser_control == 'ttl':
            self.trigger(
                pins=[self.cfg.laser_gate_pmod],
                width=self.cfg.readout_integration_treg
                )            
        t = self.cfg.laser_readout_offset_treg
        self.trigger(adcs=[0],
                    pins=[0, 1],
                    adc_trig_offset=0,
                    t = t)
        t +=  self.cfg.readout_reference_treg
        self.trigger(adcs=[0],
                    pins=[0, 1],                     
                    adc_trig_offset=0,
                    t = t)
        # Pause between pulse sequences, let aom turn off
        self.wait_all()
        self.sync_all(self.cfg.relax_delay_treg)

    def acquire_decimated(self, soc, *arg, **kwarg):

        data = super().acquire_decimated(soc, *arg, **kwarg)

        return data[0][:, 0]
    
    def analyze_results(self, data):
        data = np.reshape(data, self.data_shape)

        d = ItemAttribute()

        if len(self.data_shape) == 2:
            d.signal1 = data[:, 0]
            d.reference1 = data[:, 1]
            if self.data_shape[-1] == 4:
                d.signal2 = data[:, 2]
                d.reference2 = data[:, 3]
        elif len(self.data_shape) == 3:
            d.signal1 = data[:, :, 0]
            d.reference1 = data[:, :, 1]
            if self.data_shape[-1] == 4:
                d.signal2 = data[:, :, 2]
                d.reference2 = data[:, :, 3]
        elif len(self.data_shape) == 4:
            d.signal1 = data[:, :, :, 0]
            d.reference1 = data[:, :, :, 1]
            if self.data_shape[-1] == 4:
                d.signal2 = data[:, :,  :, 2]
                d.reference2 = data[:, :, :, 3]

        if self.data_shape[-1]==2:
            d.contrast = ((d.signal1 - d.reference1)/d.reference1 *100) 
            for _ in range(len(d.contrast.shape) - 1):
                d.contrast = np.mean(d.contrast, axis=0)
                d.signal1 = np.mean(d.signal1, axis=0)
                d.reference1 = np.mean(d.reference1, axis=0)
        elif self.data_shape[-1]==4:
            d.contrast1 = ((d.signal1 - d.reference1)/d.reference1 *100) 
            d.contrast2 = ((d.signal2 - d.reference2)/d.reference2 *100) 
            d.contrast = d.contrast1 - d.contrast2
            for _ in range(len(d.contrast1.shape) - 1):
                d.contrast1 = np.mean(d.contrast1, axis=0)
                d.signal1 = np.mean(d.signal1, axis=0)
                d.reference1 = np.mean(d.reference1, axis=0)
                d.contrast2 = np.mean(d.contrast2, axis=0)
                d.signal2 = np.mean(d.signal2, axis=0)
                d.reference2 = np.mean(d.reference2, axis=0)
                d.contrast = np.mean(d.contrast, axis=0)

        d.x_treg = self.qick_sweeps[0].get_sweep_pts()
        d.x_tus = self.qick_sweeps[0].get_sweep_pts()*self.cycles2us(1)

        return d