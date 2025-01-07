from .nvqicksweep import NVQickSweep
from .nvaverageprogram import NVAveragerProgram
import numpy as np


class LockinODMRTwoSources(NVAveragerProgram):

    def initialize(self):
        """
        This is run at the beginning of each acquire or acquire_decimated command
        """
        self.declare_readout(ch=0,
                             freq=0,
                             length=self.cfg.readout_treg,
                             sel="input")

        # Get registers for mw1
        self.declare_gen(ch=self.cfg.mw1_channel, nqz=self.cfg.mw1_nqz)        

        # Setup pulse defaults microwave
        self.set_pulse_registers(ch=self.cfg.mw1_channel,
                                 style='const',
                                 freq=self.cfg.mw1_start_freg,
                                 gain=self.cfg.mw1_gain,
                                 length=self.cfg.readout_treg,
                                 phase=0)

        # Get registers for mw1
        self.declare_gen(ch=self.cfg.mw2_channel, nqz=self.cfg.mw1_nqz)        

        # Setup pulse defaults microwave
        self.set_pulse_registers(ch=self.cfg.mw2_channel,
                                 style='const',
                                 freq=self.cfg.mw2_start_freg,
                                 gain=self.cfg.mw2_gain,
                                 length=self.cfg.readout_treg,
                                 phase=self.cfg.mw2_phase_preg)

        ## Get frequency register and convert frequency values to integers
        self.mw1_frequency_register = self.get_gen_reg(self.cfg.mw1_channel, "freq")   
        self.mw2_frequency_register = self.get_gen_reg(self.cfg.mw2_channel, "freq")   

        df_points = (self.cfg.mw1_end_freg - self.cfg.mw1_start_freg) // self.cfg.mw1_delta_freg + 1

        self.add_sweep(
            NVQickSweep(
                self,
                self.mw1_frequency_register,
                self.cfg.mw1_start_freqMHz,
                self.cfg.mw1_end_freqMHz,
                df_points,
                source2=self.mw2_frequency_register))

        if self.cfg.pre_init:
            self.pulse(ch=self.cfg.mw1_channel)    
            self.pulse(ch=self.cfg.mw2_channel)    
            self.sync_all()    

        self.synci(400)  # give processor some time to configure pulses

    def body(self):
        t0 = 0

        self.pulse(ch=self.cfg.mw1_channel, t=t0)
        self.pulse(ch=self.cfg.mw2_channel, t=t0)

        self.trigger(adcs=[0],
                     adc_trig_offset=0)

        self.wait_all()
        self.sync_all(self.cfg.relax_delay_treg)

        self.trigger(adcs=[0],
                     adc_trig_offset=0)

        self.wait_all()
        self.sync_all(self.cfg.relax_delay_treg)

    def analyze_results(self, data):
        data = np.reshape(data, self.data_shape)

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
        odmr_contrast = (signal - reference) / reference * 100

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

    def acquire(self, soc, *arg, **kwarg):

        data = super().new_acquire(soc, *arg, **kwarg)

        data = self.analyze_results(data)

        return data
