'''
get_readout_window
=======================================================================
An function that acquires a timedomain readout window signal that
is composed of multiple segments due to the limited memory assigned to the
FPGA buffer.  Furhtermore, this take a readout window with and without a microwave
pulse to generate a spin contrast that can be used to calibrate the averaging time
for pulsed measurements
'''

from .readoutwindow import ReadoutWindow

import numpy as np


def get_readout_window(config, n_time_bins):
    '''
    Function that acquires two readoutwindows by combining
    n_time_bins number of window

    Parameters
    ----------
    soc : ::class:`~qick.QickSoc`
    soccfg : ::class:`~qick.QickConfig`
    config : ::class:`~qickdawg.nvpulsing.NVConfiguration
        qickdawg.NVconfiguraiton instance for required attributes
        see qickdawg.ReadoutWindow for required attributes
    n_time_bins : int
        Number of windows to combine to take the full readoutwindow

    Returns
    --------
    (np.array, np.array, qickdawg.NVAveragerProgram) a three tuple
        consisting of
        1D np.array of the readout window with microwave on
        1D np.array of the readout window wiht microwave off
        The average program instance for diagnostics
    '''
    pi2 = config.mw_pi2_tus
    laser_readout_offset_treg = config.laser_readout_offset_treg
    config.mw_pi2_tus = 0

    assert (n_time_bins * config.readout_length_treg) <= config.laser_initialize_treg, "More time bins than laser on time"

    for i in range(n_time_bins):
        prog = ReadoutWindow(config)
        if i == 0:
            laser_readout_offset_treg = config.laser_readout_offset_treg
            prog = ReadoutWindow(config)
            data_off = prog.acquire_decimated(progress=False)
            # print(i, config.laser_readout_offset_treg)
        else:
            config.laser_readout_offset_treg += 1020
            prog = ReadoutWindow(config)
            data = prog.acquire_decimated(progress=False)
            data_off = np.append(data_off, data)
            # print(i, config.laser_readout_offset_treg)

    config.laser_readout_offset_treg = laser_readout_offset_treg
    config.mw_pi2_tus = pi2

    for i in range(n_time_bins):
        prog = ReadoutWindow(config)
        if i == 0:
            laser_readout_offset_treg = config.laser_readout_offset_treg
            prog = ReadoutWindow(config)
            data_on = prog.acquire_decimated(progress=False)
            # print(i, config.laser_readout_offset_treg)
        else:
            config.laser_readout_offset_treg += 1020
            prog = ReadoutWindow(config)
            data = prog.acquire_decimated(progress=False)
            data_on = np.append(data_on, data)
            # print(i, config.laser_readout_offset_treg)

    return data_on, data_off, prog
