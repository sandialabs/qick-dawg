"""
Dark Counts
===========
A NVAveragerProgram class that turns the  returns averaged number of photon counts 
for some readout time. 
"""

from .nvaverageprogram import NVAveragerProgram

import numpy as np


class DarkCounts(NVAveragerProgram):
    """
    NVAveragerProgram which simply turns on an AOM and collects PL intensity from an 
    the adc for a time defined by cfg.readout_integrat_t#

    Parameters
    ----------
    cfg
        instance of `.NVConfiguration` class with attributes
        .adc_channel : int
            0 or 1 - adc channel for collecting data
        .laser_gate_pmod : int
            typicall 0 to 6 - pmod channel to trigger the laser gating
        .relax_delay_treg : int
            delay time between acquisitions so everything syncs, typicaly 1us or less
        .readout_integration_treg : int
            PL integration time for each data point
        .reps : int
            number of repititions for collecting PL intensity data
    """

    required_cfg = [
        "adc_channel",
        "laser_gate_pmod",
        "readout_integration_treg",
        "relax_delay_treg",
        "reps"]

    def initialize(self):
        """
        Method that generates the assembly code that initializes the pulse sequence. 

        For qickdawg.PLIntensity,  this simply sets up the adc to integrate for self.cfg.readout_intregration_t#
        """

        self.check_cfg()

        self.setup_readout()

        self.synci(200)  # give processor some time to cfgure pulses

    def body(self):
        """
        Method that generates the assembly code that is looped over or repeated. 
        For qickdawg.PLIntensity this sets the PMODs to high for self.cfg.readout_integration_t#
        """
        self.trigger(
            adcs=[self.cfg.adc_channel],
            width=self.cfg.readout_integration_treg,
            t=0)

        self.wait_all()
        self.sync_all(self.cfg.relax_delay_treg)

    def acquire(self, *arg, **kwarg):
        '''
        Method that overloads the qickdawg.NVAvergerProgram.acquire() method to analyze the output
        to a single point which is the mean of the returned data points divided by
        self.cfg.readout_integration_treg

        Parameters
        ----------
        counting_return : str
            'rate' will return the average counts/s
            'totalize' will return the total counts over all reps

        Returns
        -------
        float 
            if config.edge_counting
                counting_return == 'rate', returns count rate in cts/s
                counting_return == 'totalize', returns total counts
            if not edge coutning
                returns average analog ADC level
        '''

        data = super().acquire(*arg, **kwarg)

        if self.cfg.edge_counting:
            return int(np.sum(data))
        else:
            data = np.mean(data.astype('float')) / self.cfg.readout_integration_treg
            return float(data)
