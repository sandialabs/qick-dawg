"""
NVConfiguration
============================
A configuration class that is passed to averager programs to
setup the pulse sequencing for qick-dawg programs
"""


from itemattribute import ItemAttribute
from ..util.intexpscale import int_exp_scale

from math import floor
import qickdawg as qd
import numpy as np


class NVConfiguration(ItemAttribute):
    '''
    A class that stores configuration used by qick-dawg programs and
    and automatically converts units to be used in qick-dawg programs

    Time  properties: properties that end in '_tus', '_tns', or '_treg'
    are converted to all three variants as soon as they are initialized

    Frequency properties: properties that end in '_fMHz', 'fGHz', and '_freg'
    are converted to all three variations as soon as they are initialized

    Phase properties: properties that end in '_pdegrees', '_preg' are converted
    to all variants as soon as they are initilized

    Parameters
    ---------
    None

    Attributes
    ----------
    soccfg
        an instance of the qick.QickConfig class

    Methods
    -------
    add_linear_sweep
        method that generates all the attributes required for exectuing a linear sweep

    add_exponential_sweep
        method that generates all the attributes required for exectuing a linear sweep
    '''

    def __init__(self):

        self.soccfg = qd.soccfg

        self.ddr4 = False
        self.mr = False
        self.n_ddr4_bins = 10

        self.rounds = 1
        self.reps = 1

    def __setattribute__(self, name, value):

        super().__setattribute__(self, name, value)

    def __setattr__(self, name, value):
        """
        Overloaded class method which handles converting properties
        related to units used by the qick-dawg program
        """

        if name.split('_')[-1] == 'tus':

            treg = self.soccfg.us2cycles(value)
            tus = self.soccfg.cycles2us(treg)

            self.__dict__[name.replace('tus', 'treg')] = treg
            self.__dict__[name] = tus
            self.__dict__[name.replace('tus', 'tns')] = tus * 1000

        elif name.split('_')[-1] == 'treg':
            tus = self.soccfg.cycles2us(value)

            self.__dict__[name] = value
            self.__dict__[name.replace('treg', 'tus')] = tus
            self.__dict__[name.replace('treg', 'tns')] = tus * 1000

        elif name.split('_')[-1] == 'tns':
            treg = self.soccfg.us2cycles(value / 1000)
            tus = self.soccfg.cycles2us(treg)

            self.__dict__[name.replace('tns', 'treg')] = treg
            self.__dict__[name.replace('tns', 'tus')] = tus
            self.__dict__[name] = tus * 1000

        elif name.split('_')[-1] == 'fMHz':
            freg = self.soccfg.freq2reg(value)
            fMHz = self.soccfg.reg2freq(freg)

            self.__dict__[name.replace('fMHz', 'freg')] = freg
            self.__dict__[name] = fMHz
            self.__dict__[name.replace('fMHz', 'fGHz')] = fMHz / 1000

        elif name.split('_')[-1] == 'fGHz':
            freg = self.soccfg.freq2reg(value * 1000)
            fMHz = self.soccfg.reg2freq(freg)

            self.__dict__[name.replace('fGHz', 'freg')] = freg
            self.__dict__[name.replace('fGHz', 'fMHz')] = fMHz
            self.__dict__[name] = fMHz / 1000

        elif name.split('_')[-1] == 'freg':
            fMHz = self.soccfg.reg2freq(value)

            self.__dict__[name] = value
            self.__dict__[name.replace('freg', 'fMHz')] = fMHz
            self.__dict__[name.replace('freg', 'fGHz')] = fMHz / 1000

        elif name.split('_')[-1] == 'pdegrees':
            preg = self.soccfg.deg2reg(value)

            self.__dict__[name] = self.soccfg.reg2deg(preg)
            self.__dict__[name.replace('pdegrees', 'preg')] = preg

        elif name.split('_')[-1] == 'preg':
            pdegrees = self.soccfg.reg2deg(value)

            self.__dict__[name.replace('preg', 'pdegrees')] = pdegrees
            self.__dict__[name] = value

        else:
            self.__dict__[name] = value

    def add_linear_sweep(self, name, unit, start, stop, delta=0, nsweep_points=0):
        """
        Configures linear sweep properites for qick-dawg program s changing parameter 'name' using 'units'
        from 'start' to 'end' either by 'delta' steps or by 'nsweep_points'

        Parameters
        -------------------------
        name
            A string which is attribute that is to be swept over, i.e. 'mw'
        unit
           A string which can be either 'fMhz', 'fGHz', 'freg', 'tus', 'tns'
           or 'treg'
        start
            float or integer which is the start value of the sweep
        stop
            float or integer which is the end value of the sweep
        delta
            float or integer which is the step size between start and end values
            (if excluded, must have nsweep_points parameter)
        nsweep_points
            number of points between start and end
            (if excluded, must have delta parameter)
        """

        assert np.sum(np.array([delta, nsweep_points]) > 0) == 1, 'Either delta and nsweep_points are required, but not both'

        assert unit in [
            'fMHz', 'fGHz', 'freg',
            'tus', 'tns', 'treg',
            'pdeg', 'preg']
        assert isinstance(nsweep_points, int)
        if 'reg' in unit:
            assert np.all([isinstance(var, int) for var in (start, stop, delta)]), \
                "reg units require int start, stop, and delta"

        self.scaling_mode = 'linear'

        if 'f' == unit[0]:
            ounit = unit
            runit = 'freg'
        elif 't' == unit[0]:
            ounit = unit
            runit = 'treg'
        elif 'p' == unit[0]:
            ounit = unit
            runit = 'preg'

        self.__setattr__(name + '_start_' + unit, start)

        if (delta != 0) & (nsweep_points == 0):

            self.__setattr__(name + '_delta_' + unit, delta)
            self.nsweep_points = int(
                floor((stop - start)
                / delta + 1))

            self.__setattr__(name + '_end_' + runit, (
                self[name + '_start_' + runit] +
                self[name + '_delta_' + runit] *
                (self.nsweep_points - 1)))

        elif (delta == 0) & (nsweep_points != 0):

            self.nsweep_points = nsweep_points
            self.__setattr__(name + '_delta_' + ounits, int(
                floor((start - stop)
                / (nsweep_points - 1))))
            self.__setattr__(name + '_end_' + runit, (
                self[name + '_start_' + runit] +
                self[name + '_delta_' + runit] *
                self.nsweep_points))

        actual_start = self[name + '_start_' + ounit]
        actual_end = self[name + '_end_' + ounit]
        actual_delta = self[name + '_delta_' + ounit]

        if np.any([actual_start != start, actual_end != stop,
                   (actual_delta != delta) & (delta != 0)]):
            print('Warning: exact sweep condition not possible\n')
            if delta == 0:
                print(f'Requested {start} to {stop} in {nsweep_points}')
            else:
                print(f'Requested {start} to {stop} by {delta}')
            print(f'Instead using {actual_start} to {actual_end} by {actual_delta} in {self.nsweep_points} steps')

    def add_unitless_linear_sweep(self, name, start, stop, delta=0, nsweep_points=0):

        for var in [start, stop, delta]:
            assert issubclass(var, int), "Unitless linear sweep requires integer start, stop, delta" 

        start_name = name + '_start'
        end_name = name + '_end'
        delta_name = name + '_delta'

        self[start_name] = start

        if (delta != 0) & (nsweep_points == 0):
            self[delta_name] = delta        
            self.nsweep_points = int(floor((stop-start)/delta + 1))
            self[end_name] = (start + delta * self.nsweep_points)

        elif (delta == 0) & (nsweep_points == 0):
            self.nsweep_points = nsweep_points
            self[delta_name] = int(floor((stop-start)/(nsweep_points - 1)))
            self[end_name] = (start + delta * self.nsweep_points)

        if (self[start_name] + self[delta_name] * self.nsweep_points) != stop:
            print('Warning: exact sweep condition not possible\n')
            if delta == 0:
                print(f'Requested {start} to {stop} in {nsweep_points}')
            else:
                print(f'Requested {start} to {stop} by {delta}')
            print(f'Instead using {start} to {self[end_name]} by {self[delta_name]} in {self.n_sweep_points}')

    def add_exponential_sweep(self, name, unit, start, stop, scaling_factor=0):
        """
        Configures exponentially scaling sweep properites for qick-dawg programs
        changing parameter 'name' using 'units' from 'start' to 'end' by
        a scaling factor

        Parameters
        -------------------------
        name
            A string which is attribute that is to be swept over, i.e. 'mw'
        unit
           A string which can be either 'fMhz', 'fGHz', 'freg', 'tus', 'tns'
           or 'treg'
        start
            float or integer which is the start value of the sweep
        stop
            float or integer which is the end value of the sweep
        scaling_factor
            string which currently is only implemented for strings
            '3/2', '5/4', '9/8', '17/16', that determines the step sizes
            between 'start' and 'stop'
        """

        self.scaling_mode = 'exponential'
        assert scaling_factor in ['17/16', '9/8', '5/4', '3/2'], 'Currently accepting only \
        scaling values 17/16, 9/8, /5/4, 3/2'

        self.scaling_factor = scaling_factor
        self.__setattr__(name + '_start_' + unit, start)
        self.__setattr__(name + '_end_' + unit, stop)

        start = self[name + '_start_treg']
        stop = self[name + '_end_treg']

        self.nsweep_points = len(int_exp_scale(start, stop, self.scaling_factor))
