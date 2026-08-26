'''
Helper class for shared spin initialization and readout sequences
=======================================================================
Provides common spin initialization and readout methods, and acquisition/analysis methods
for Fine Timing Suite programs.
'''

import numpy as np
from itemattribute import ItemAttribute
from qickdawg.util.apply_on_axis_0_n_times import apply_on_axis_0_n_times


class ReadoutHelpers:
    """
    Mixin class that provides shared laser initialization, readout, and data analysis methods
    for Fine Resolution programs. Intended to be used with NVAveragerProgram subclasses.
    """
    
    def setup_helper_registers(self, mw_channel):
        """Setup registers and validation for readout sequence"""
        self.mw_gain_register = self.get_gen_reg(mw_channel, "gain")

        if self.cfg.laser_on_treg < self.cfg.readout_reference_start_treg + self.cfg.readout_integration_treg:
            raise ValueError(
                "Invalid readout timing: laser_on_treg must be >= "
                "readout_reference_start_treg + readout_integration_treg. "
                f"Got laser_on_treg={self.cfg.laser_on_treg}, "
                f"readout_reference_start_treg={self.cfg.readout_reference_start_treg}, "
                f"readout_integration_treg={self.cfg.readout_integration_treg}."
            )


    def pre_init(self):
        """
        Optional pre-initialization pulse. Performs the spin initialization 
        for the first cycle.
        """
        if self.cfg.pre_init:
            self.trigger(
                pins=[self.cfg.laser_gate_pmod],
                width=self.cfg.laser_on_treg, 
                adc_trig_offset=0)
            self.sync_all(self.cfg.laser_on_treg)

        self.wait_all()
        self.sync_all(self.cfg.relax_delay_treg)


    def initialize_spin(self):
        """
        Initialize the spin state. This function ensures that initialization completes
        in alignment with the start of the MW pulses.

        Optionally, laser initialization and relaxation can be moved here instead of
        occurring during the previous cycle's readout.
        """
        self.sync_all(self.cfg.mw_to_laser_delay_treg)


    def nv_readout(self):
        """
        Read out the spin state using the laser and ADC. Currently delegates to ttl_readout(),
        which performs the signal and reference readouts and applies the post-laser
        relaxation delay.
        """
        self.ttl_readout()

    def readout_and_reference(self, pulse_program_fn):
        """
        Perform the main readout, then if cfg.get_reference is True, acquires a timing-matched
        reference readout without the RF pulses.

        Parameters
        ----------
        pulse_program_fn : callable
            Function to call to program the pulse sequence for the reference measurement.
            This is typically self.program_pulses() or equivalent.
        """
        # Core readout
        self.nv_readout()
        
        # Reference readout (if configured)
        if self.cfg.get_reference:
            # Set MW gain to 0
            self.mw_gain_register.set_to(0, physical_unit=False)
            self.initialize_spin()
            pulse_program_fn()
            self.nv_readout()
            # Restore original gain
            self.mw_gain_register.set_to(self.cfg.mw_gain, physical_unit=False)


    def acquire(self, raw_data=False, sweep_param=None, *arg, **kwarg):
        """
        Generic acquire method that handles reference readouts based on config.
        
        Parameters
        ----------
        raw_data : bool
            If False, analyzes results; if True, returns raw data
        
        Returns
        -------
        Analyzed or raw data depending on raw_data flag
        """
        readouts = 4 if self.cfg.get_reference else 2

        data = super().acquire(readouts_per_experiment=readouts, *arg, **kwarg)
        if not raw_data:
            data = self.analyze_results_helper(data, sweep_param=sweep_param)
        return data

    def _add_sweep_with_conversions(self, d, sweep_param, sweep_pts):
        """Attach the provided sweep axis and NVConfiguration-style unit conversions."""
        d[sweep_param] = sweep_pts
        d.sweep_param = sweep_param

        if '_' not in sweep_param:
            return

        base, suffix = sweep_param.rsplit('_', 1)
        vals = np.asarray(sweep_pts)

        # Keep conversion behavior aligned with NVConfiguration.
        soccfg = self.cfg.soccfg

        def _reg2freq_array(reg_arr):
            return np.asarray([soccfg.reg2freq(int(r)) for r in reg_arr], dtype=float)

        def _freq2reg_array(freq_arr_mhz):
            return np.asarray([soccfg.freq2reg(float(f)) for f in freq_arr_mhz], dtype=int)

        def _cycles2us_array(cycles_arr):
            return np.asarray([soccfg.cycles2us(int(c)) for c in cycles_arr], dtype=float)

        def _us2cycles_array(us_arr):
            return np.asarray([soccfg.us2cycles(float(u)) for u in us_arr], dtype=int)

        def _reg2deg_array(reg_arr):
            return np.asarray([soccfg.reg2deg(int(r)) for r in reg_arr], dtype=float)

        def _deg2reg_array(deg_arr):
            return np.asarray([soccfg.deg2reg(float(p)) for p in deg_arr], dtype=int)

        if suffix in ('fMHz', 'fGHz', 'freg'):
            if suffix == 'fMHz':
                freg = _freq2reg_array(vals)
                fMHz = _reg2freq_array(freg)
            elif suffix == 'fGHz':
                freg = _freq2reg_array(vals * 1000.0)
                fMHz = _reg2freq_array(freg)
            else:  # freg
                freg = np.rint(vals).astype(int)
                fMHz = _reg2freq_array(freg)

            d[base + '_freg'] = freg
            d[base + '_fMHz'] = fMHz
            d[base + '_fGHz'] = fMHz / 1000.0
            return

        if suffix in ('tus', 'tns', 'treg'):
            if suffix == 'tus':
                treg = _us2cycles_array(vals)
                tus = _cycles2us_array(treg)
            elif suffix == 'tns':
                treg = _us2cycles_array(vals / 1000.0)
                tus = _cycles2us_array(treg)
            else:  # treg
                treg = np.rint(vals).astype(int)
                tus = _cycles2us_array(treg)

            d[base + '_treg'] = treg
            d[base + '_tus'] = tus
            d[base + '_tns'] = tus * 1000.0
            return

        if suffix in ('ftus', 'ftns', 'ftsamp'):
            # Prefer hardware-defined samples/clk for the configured MW channel.
            # Fall back to config assumption, then default 16.
            ft_samps_per_clk = None
            mw_channel = getattr(self.cfg, 'mw_channel', None)
            if mw_channel is not None:
                try:
                    ft_samps_per_clk = soccfg['gens'][mw_channel]['samps_per_clk']
                except Exception:
                    ft_samps_per_clk = None

            if ft_samps_per_clk is None:
                ft_samps_per_clk = getattr(self.cfg, 'ft_samps_per_clk_assumed', 16)

            sample2us = soccfg.cycles2us(1) / ft_samps_per_clk

            if suffix == 'ftus':
                ftsamp = np.rint(vals / sample2us).astype(int)
            elif suffix == 'ftns':
                ftsamp = np.rint((vals / 1000.0) / sample2us).astype(int)
            else:  # ftsamp
                ftsamp = np.rint(vals).astype(int)

            ftus = ftsamp * sample2us
            d[base + '_ftsamp'] = ftsamp
            d[base + '_ftus'] = ftus
            d[base + '_ftns'] = ftus * 1000.0
            return

        if suffix in ('pdegrees', 'pdeg', 'preg'):
            if suffix in ('pdegrees', 'pdeg'):
                preg = _deg2reg_array(vals)
                pdegrees = _reg2deg_array(preg)
            else:  # preg
                preg = np.rint(vals).astype(int)
                pdegrees = _reg2deg_array(preg)

            d[base + '_preg'] = preg
            d[base + '_pdegrees'] = pdegrees
            d[base + '_pdeg'] = pdegrees
            return

    def analyze_results_helper(self, data, sweep_param=None):
        """
        Method that takes in a 1D array of data points from self.acquire() and analyzes the
        results based on the number of reps and frequency points

        Parameters
        ----------
        data
            (1D np.array) data returned from self.acquire()

        returns
            (qickdawg.ItemAttribute instance) with attributes
            .frequencies (len(nsweep_points) np array, MHz units) - frequencies swept over
            .signal (nfrequency np.array, adc units)
                - average adc signal with MW pulse
            .reference (nfrequency np.array, adc units)
                - signal at the end of the reinitialization pulse
            .contrast (nfrequency np.array, fractional units)
                - (signal - reference) / reference
        """
        data = np.reshape(data, self.data_shape)
        
        d = ItemAttribute()

        norm_factor = self.cfg.readout_integration_tns * 1e-9 * self.cfg.reps

        # RF on readout
        d.signal1 = data[..., 0]
        d.reference1 = data[..., 1]

        if self.cfg.get_reference:
            # RF off readout
             d.signal2 = data[..., 2]
             d.reference2 = data[..., 3]

        # Average over all axes except the last (sweep param) axis
        n = len(d.signal1.shape) - 1
        
        measurement_keys = ['signal1', 'reference1']
        if self.cfg.get_reference:
            measurement_keys += ['signal2', 'reference2']

        for key in measurement_keys:
            # Sum over all reps for each measurement
            d[key] = apply_on_axis_0_n_times(d[key], np.sum, n)
            # Generate cts/s versions of each key
            d[key + '_cts_s'] = d[key] / norm_factor

        # Calculate signal/reference
        if self.cfg.get_reference:
            d.contrast = d.signal1 / d.signal2

        # Add sweep points if available.
        if hasattr(self, 'qick_sweeps') and len(self.qick_sweeps) > 0:
            pts = self.qick_sweeps[0].get_sweep_pts()
            d.sweep_pts = pts
            if sweep_param is not None:
                self._add_sweep_with_conversions(d, sweep_param, pts)
        
        return d