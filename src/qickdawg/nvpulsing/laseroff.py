"""
LaserOff
=======================================================================
Makes a qick program to turn off the laser control, typically used in conjunction with the
LaserOn class
"""

import numpy as np
from .nvaverageprogram import NVAveragerProgram


def laser_off(config, reps=1, readout_integration_treg=1020):
    '''Sets laser PMOD to low

    Parameters
    ----------
    reps : int (default 1)
    readout_integration_treg (default 65535 (maximum))

    Returns
    -------
    int
        Average ADC value over time readout_integration_treg
    '''

    config.reps = reps
    config.readout_integration_treg = readout_integration_treg
    prog = LaserOff(config)

    _ = prog.acquire()
    data = prog.acquire()
    if prog.cfg.edge_counting:
        return int(data)
    else:
        data = np.mean(data)
        data /= readout_integration_treg

        return float(data)


class LaserOff(NVAveragerProgram):
    """Qickdawg program that turns the laser pmod low and laser off

    Parameters
    ----------
    cfg :
        instance of `.NVConfiguration`  with attributes
        .laser_gate_pmod
        .readout_integration_treg

    Methods
    -------
        acquire
            turns the laser off, but also acquires one data point and might be used
            as a background signal reference

    """

    def initialize(self):
        """
        Method that generates the assembly code that initializes the pulse sequence.
        For LaserOff this simply sets up the adc to integrate for self.cfg.readout_intregration_t#
        """

        # Inherited from qd.NVAveragerProgram
        self.setup_readout()

        self.synci(100)  # give processor some time to configure pulses
        if (self.cfg.ddr4 is True) or (self.cfg.mr is True):
            self.trigger(ddr4=self.cfg.ddr4, mr=self.cfg.mr, adc_trig_offset=0)
        self.synci(100)

        self.trigger(
            pins=[self.cfg.laser_gate_pmod],
            adc_trig_offset=0,
            t=0)

        self.synci(self.cfg.readout_integration_treg)

    def body(self):
        '''
        Method that generates the assembly code that is looped over or repeated.
        For LaserOff this simply sets laser_gate_pmod to the low value
        '''

        self.trigger(adcs=[self.cfg.adc_channel],
                     adc_trig_offset=0,
                     t=0)

        self.wait_all()
        self.synci(self.cfg.relax_delay_treg)
