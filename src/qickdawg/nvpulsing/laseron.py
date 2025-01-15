"""
TurnLaserOn
=======================================================================
Makes a qick program to turn on the laser control without turning off
"""

import numpy as np
from .nvaverageprogram import NVAveragerProgram


def laser_on(config, reps=1, readout_integration_treg=1020):
    '''Sets laser PMOD to high without turning off

    Parameters
    ----------
    config : `.NVConfig`
        See `.LaserOn` for required attributes
    reps : int (optional, 1)
    readout_integration_treg (option, 3)

    Returns
    -------
    int
        integrated ADC value over time readout_integration_treg
    '''

    config.reps = reps
    config.readout_integration_treg = readout_integration_treg
    prog = LaserOn(config)

    _ = prog.acquire()
    data = prog.acquire()

    if prog.cfg.edge_counting:
        return int(data)
    else:
        data = np.mean(data)
        data /= readout_integration_treg
        return float(data)


class LaserOn(NVAveragerProgram):
    """
    Class which creates a qickdawg program that will turn the laser controller
    to the on state without turning the laser controller of

    Parameters
    -----------
    soccfg
        instance of qick.QickConfig class
    cfg
        instance of qickdawg.NVConfiguration class with attributes
        .adc_cannel (required)
        .laser_gate_pmod(required)

    Methods
    -------
    acquire
        returns a single datapoint which may be used the PL intensity

    """

    def initialize(self):
        """
        Method that generates the assembly code that initializes the pulse sequence.
        For LaserOn this simply sets up the adc to integrate for self.cfg.readout_intregration_t#
        """

        # Inherited from qd.NVAveragerProgram
        self.setup_readout()

        self.synci(100)  # give processor some time to configure pulses
        if (self.cfg.ddr4 is True) or (self.cfg.mr is True):
            self.trigger(ddr4=self.cfg.ddr4, mr=self.cfg.mr, adc_trig_offset=0)
        self.synci(100)

    def body(self):
        '''
        Method that generates the assembly code that is looped over or repeated.
        For LaserOn this simply sets laser_gate_pmod to the high value
        '''
        self.trigger_no_off(
            adcs=[self.cfg.adc_channel],
            pins=[self.cfg.laser_gate_pmod],
            adc_trig_offset=0)

        self.wait_all()
        self.synci(self.cfg.relax_delay_treg)
