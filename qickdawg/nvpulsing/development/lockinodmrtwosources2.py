from .nvqicksweep import NVQickSweep
from .nvaverageprogram import NVAveragerProgram
from ..util import ItemAttribute

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.image as mpimg

class LockinODMRTwoSources2(NVAveragerProgram):

    def initialize(self):
        """
        This is run at the beginning of each acquire or acquire_decimated command
        """
        self.declare_readout(ch=0,
                             freq=0,
                             length=self.cfg.readout_integration_treg,
                             sel="input")

        # Delcare and setup aom generator
        if self.cfg.laser_control == 'aom':
            self.declare_gen(ch=self.cfg.aom_channel, nqz=1)

            self.set_pulse_registers(ch=self.cfg.aom_channel, 
                                        style='const',
                                        freq=self.cfg.aom_freg,
                                        gain=self.cfg.aom_gain,
                                        length=self.cfg.readout_integration_treg,
                                        phase=0)
        elif self.cfg.laser_control == 'ttl':
            pass
        else:
            assert 0, "cfg.laser_control must be assigned to 'aom' or 'ttl'"

        # Get registers for mw 1
        self.declare_gen(ch=self.cfg.mw_channel, nqz=self.cfg.mw_nqz)        
        
        # Setup pulse defaults microwave
        self.default_pulse_registers(ch=self.cfg.mw_channel,
                                     style='const',
                                     gain= self.cfg.mw_gain,
                                     length=self.cfg.readout_integration_treg,
                                     phase=0)
        
        self.set_pulse_registers(ch=self.cfg.mw_channel, 
                                 freq=self.cfg.mw_start_freg
                                )


        # Get registers for mw2
        self.declare_gen(ch=self.cfg.mw2_channel, nqz=self.cfg.mw2_nqz)        
        
        # Setup pulse defaults microwave
        self.default_pulse_registers(ch=self.cfg.mw2_channel,
                                     style='const',
                                     gain= self.cfg.mw2_gain,
                                     length=self.cfg.readout_integration_treg,
                                     phase=self.cfg.mw2_phase_preg)

        self.set_pulse_registers(ch=self.cfg.mw2_channel, 
                                 freq=self.cfg.mw_start_freg
                                )

        self.mw1_frequency_register=self.get_gen_reg(self.cfg.mw_channel, "freq")   
        self.mw2_frequency_register=self.get_gen_reg(self.cfg.mw2_channel, "freq")   

        self.add_sweep(NVQickSweep(self, 
                                   self.mw1_frequency_register,
                                   self.cfg.mw_start_fMHz,
                                   self.cfg.mw_end_fMHz, 
                                   self.cfg.nsweep_points, 
                                   source2_reg=self.mw2_frequency_register))


        self.synci(400)  # give processor some time to self.cfgure pulses

        if self.cfg.pre_init:
            self.pulse(ch=self.cfg.mw_channel)
            self.pulse(ch=self.cfg.mw2_channel)
            if self.cfg.laser_control == 'aom':
                self.pulse(ch=self.cfg.aom_channel)
                self.sync_all(self.cfg.relax_delay_treg)
       
            elif self.cfg.laser_control == 'ttl':
                self.trigger(
                    pins=[self.cfg.laser_gate_pmod],
                    width=self.cfg.readout_integration_treg,
                    adc_trig_offset=0
                    )
                self.sync_all(self.cfg.readout_integration_treg+self.cfg.relax_delay_treg)

    def body(self):

        if self.cfg.laser_control=='aom':
            t0=0 
            self.pulse(ch=self.cfg.mw_channel, t=t0)
            self.pulse(ch=self.cfg.mw2_channel, t=t0)
    
            self.pulse(ch=self.cfg.aom_channel)   
            self.trigger(adcs=[0],
                         adc_trig_offset=0)

            self.wait_all()
            self.sync_all(self.cfg.relax_delay_treg)

            self.pulse(ch=self.cfg.aom_channel)   
            self.trigger(adcs=[0],
                         adc_trig_offset=0)
        
    
            self.wait_all()
            self.sync_all(self.cfg.relax_delay)


        if self.cfg.laser_control=='ttl':
            t0 = 0
            self.pulse(ch=self.cfg.mw_channel, t=t0)
            self.pulse(ch=self.cfg.mw2_channel, t=t0)

            self.trigger(adcs=[0],
                pins=[self.cfg.laser_gate_pmod],
                width=self.cfg.readout_integration_treg,
                adc_trig_offset=0,
                t=t0)
            t0 += self.cfg.readout_integration_treg            
            t0 += self.cfg.relax_delay_treg
        
            self.trigger(adcs=[0],
                pins=[self.cfg.laser_gate_pmod],
                width=self.cfg.readout_integration_treg,
                adc_trig_offset=0,
                t=t0
                )

            self.sync_all(self.cfg.relax_delay_treg)
            self.wait_all()
    
    def analyze_results(self, data):
        data = np.reshape(data, self.data_shape)
        data = data/self.cfg.readout_integration_treg

        if len(self.data_shape) == 2:
            signal = data[:, 0]
            reference = data[:, 1]
        elif len(self.data_shape) == 3:
            signal = data[:, :, 0]
            reference = data[:, :, 1]
        elif len(self.data_shape) == 4:
            signal = data[:, :, :, 0]
            reference = data[:, :, :, 1]

        odmr = (signal - reference)
        odmr_contrast = (signal - reference)/reference *100
        
        for _ in range(len(odmr.shape) - 1):
            odmr = np.mean(odmr, axis=0)
            signal = np.mean(signal, axis=0)
            reference = np.mean(reference, axis=0)
            odmr_contrast = np.mean(odmr_contrast, axis=0)
        
        d = ItemAttribute()
        d.odmr = odmr
        d.signal = signal
        d.reference = reference
        d.odmr_contrast = odmr_contrast
        
        d.frequencies = self.qick_sweeps[0].get_sweep_pts()
        
        return d
        
    def plot_sequence(self):
        plt.figure(figsize=(10,10))
        plt.axis('off')
        plt.imshow(mpimg.imread('../graphics/ODMR.jpg'))
        plt.text(240,710,"Repeat {} times".format(self.cfg.reps),fontsize=16)
        plt.text(170,465,"readout_integration = {} us".format(int(self.cfg.readout_integration_tus)),fontsize=14)
        plt.text(485,490,"relax_delay \n = {} us".format(str(self.cfg.relax_delay_tus)[:4]),fontsize=14)
        plt.text(90,520,"Sweep linearly from {} MHz to {} MHz in steps of {} MHz".format(int(self.cfg.mw_start_fMHz),int(self.cfg.mw_end_fMHz),str(self.cfg.mw_delta_fMHz)[:4]), fontsize=14)
        plt.title("      ODMR Pulse Sequence", fontsize=20)


    def time_per_rep(self):

        t = self.cfg.readout_integration_tus*2
        t += self.cfg.relax_delay_tus *2
        t *= self.cfg.nsweep_points /1e6

        return t

    def total_time(self):

        return self.time_per_rep() * self.cfg.reps