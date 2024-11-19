from .readoutwindow import ReadoutWindow
import numpy as np


def check_readout(config, reps=1, readout_integration_treg=1020):
    '''
    Quick look at the readout with just the laser output on

    Parameters
    ----------
    config : `.NVConfig`
    reps : int (optional, 1)
    readout_integration_treg (option, 3)

    Returns
    -------
    int
        integrated ADC value over time readout_integration_treg
    '''

    config.pre_init = False
    config.readout_length_treg = readout_integration_treg
    config.mw_pi2_treg = 0
    config.mw_fMHz = 0
    config.laser_initialize_treg = readout_integration_treg
    config.mw_readout_delay_treg = 0
    config.laser_readout_offset_treg = 0
    config.reps = 1

    prog = ReadoutWindow(config)
    data = prog.acquire_decimated(progress=False)

    return data
