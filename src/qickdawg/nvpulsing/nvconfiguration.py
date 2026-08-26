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

    Fine Time properties: properties that end in '_ftus', '_ftns', or '_ftsamp'
    are converted to all three variants as soon as they are initialized.
    A specific samples per cycle conversion factor is assumed based on generator channel 0.

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
        method that generates all the attributes required for executing a linear sweep

    add_exponential_sweep
        method that generates all the attributes required for executing an exponential sweep
    '''

    def __init__(self):

        self.soccfg = qd.soccfg

        self.ddr4 = False
        self.mr = False
        self.n_ddr4_bins = 10
        self.test = False

        self.soft_avgs = 1
        self.reps = 1

        self.edge_counting = False
        self.high_threshold = 0
        self.low_threshold = 0

        # Assumes fine-time conversion factor (samples per fabric clock cycle)
        # Based on generator channel 0
        self.ft_samps_per_clk_assumed = self.soccfg['gens'][0]['samps_per_clk']

    def __setattribute__(self, name, value):

        super().__setattribute__(self, name, value)

    def __setattr__(self, name, value):
        """
        Overloaded class method which handles converting properties
        related to units used by the qick-dawg program
        """

        # Allow bootstrap attributes to be set before conversion helpers are available.
        if (
            ('soccfg' not in self.__dict__)
            or ('ft_samps_per_clk_assumed' not in self.__dict__)
            or (name in ('soccfg', 'ft_samps_per_clk_assumed'))
        ):
            self.__dict__[name] = value
            return

        suffix = name.split('_')[-1]
        sample2us = self.soccfg.cycles2us(1) / self.ft_samps_per_clk_assumed

        # Fine Timing units added (time in sample units)
        if suffix == 'ftus':
            ftsamp = int(round(value / sample2us))
            ftus = ftsamp * sample2us

            self.__dict__[name.replace('ftus', 'ftsamp')] = ftsamp
            self.__dict__[name] = ftus
            self.__dict__[name.replace('ftus', 'ftns')] = ftus * 1000

        elif suffix == 'ftsamp':
            if not isinstance(value, (int, np.integer)):
                raise TypeError("ftsamp must be an integer number of samples")

            ftus = value * sample2us

            self.__dict__[name.replace('ftsamp', 'ftus')] = ftus
            self.__dict__[name] = int(value)
            self.__dict__[name.replace('ftsamp', 'ftns')] = ftus * 1000

        elif suffix == 'ftns':
            ftsamp = int(round((value / 1000) / sample2us))
            ftus = ftsamp * sample2us

            self.__dict__[name.replace('ftns', 'ftsamp')] = ftsamp
            self.__dict__[name.replace('ftns', 'ftus')] = ftus
            self.__dict__[name] = ftus * 1000

        elif suffix == 'tus':

            treg = self.soccfg.us2cycles(value)
            tus = self.soccfg.cycles2us(treg)

            self.__dict__[name.replace('tus', 'treg')] = treg
            self.__dict__[name] = tus
            self.__dict__[name.replace('tus', 'tns')] = tus * 1000

        elif suffix == 'treg':
            tus = self.soccfg.cycles2us(value)

            self.__dict__[name] = value
            self.__dict__[name.replace('treg', 'tus')] = tus
            self.__dict__[name.replace('treg', 'tns')] = tus * 1000

        elif suffix == 'tns':
            treg = self.soccfg.us2cycles(value / 1000)
            tus = self.soccfg.cycles2us(treg)

            self.__dict__[name.replace('tns', 'treg')] = treg
            self.__dict__[name.replace('tns', 'tus')] = tus
            self.__dict__[name] = tus * 1000

        elif suffix == 'fMHz':
            freg = self.soccfg.freq2reg(value)
            fMHz = self.soccfg.reg2freq(freg)

            self.__dict__[name.replace('fMHz', 'freg')] = freg
            self.__dict__[name] = fMHz
            self.__dict__[name.replace('fMHz', 'fGHz')] = fMHz / 1000

        elif suffix == 'fGHz':
            freg = self.soccfg.freq2reg(value * 1000)
            fMHz = self.soccfg.reg2freq(freg)

            self.__dict__[name.replace('fGHz', 'freg')] = freg
            self.__dict__[name.replace('fGHz', 'fMHz')] = fMHz
            self.__dict__[name] = fMHz / 1000

        elif suffix == 'freg':
            fMHz = self.soccfg.reg2freq(value)

            self.__dict__[name] = value
            self.__dict__[name.replace('freg', 'fMHz')] = fMHz
            self.__dict__[name.replace('freg', 'fGHz')] = fMHz / 1000

        elif suffix == 'pdegrees':
            preg = self.soccfg.deg2reg(value)

            self.__dict__[name] = self.soccfg.reg2deg(preg)
            self.__dict__[name.replace('pdegrees', 'preg')] = preg

        elif suffix == 'preg':
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
            'ftus', 'ftns', 'ftsamp',
            'pdeg', 'preg']
        assert isinstance(nsweep_points, int)
        if ('reg' in unit) or (unit == 'ftsamp'):
            assert np.all([isinstance(var, int) for var in (start, stop, delta)]), \
                "reg/ftsamp units require int start, stop, and delta"

        self.scaling_mode = 'linear'

        if unit.startswith('ft'):
            ounit = unit
            runit = 'ftsamp'
        elif 'f' == unit[0]:
            ounit = unit
            runit = 'freg'
        elif 't' == unit[0]:
            ounit = unit
            runit = 'treg'
        elif 'p' == unit[0]:
            ounit = unit
            runit = 'preg'

        self.__setattr__(name + '_start_' + unit, start)

        if (delta != 0) and (nsweep_points == 0):

            self.__setattr__(name + '_delta_' + unit, delta)
            self.nsweep_points = int(
                floor((stop - start)
                      / delta + 1))

            self.__setattr__(name + '_end_' + runit, (
                self[name + '_start_' + runit]
                + self[name + '_delta_' + runit]
                * (self.nsweep_points - 1)))

        elif (delta == 0) and (nsweep_points != 0):

            self.nsweep_points = nsweep_points
            self.__setattr__(name + '_delta_' + ounit, int(
                floor((start - stop)
                      / (nsweep_points - 1))))
            self.__setattr__(name + '_end_' + runit, (
                self[name + '_start_' + runit]
                + self[name + '_delta_' + runit]
                * self.nsweep_points))

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

        assert np.sum(np.array([delta, nsweep_points]) > 0) == 1, 'Either delta and nsweep_points are required, but not both'
        assert isinstance(start, int) and isinstance(stop, int), "Unitless linear sweep requires integer start and stop"
        assert isinstance(nsweep_points, int), "nsweep_points must be an int"
        if delta != 0:
            assert isinstance(delta, int), "Unitless linear sweep requires integer delta"

        start_name = name + '_start'
        end_name = name + '_end'
        delta_name = name + '_delta'

        self[start_name] = start

        if (delta != 0) and (nsweep_points == 0):
            self[delta_name] = delta
            self.nsweep_points = int(floor((stop - start) / delta + 1))
            self[end_name] = (start + delta * (self.nsweep_points - 1))

        elif (delta == 0) and (nsweep_points != 0):
            assert nsweep_points > 1, "nsweep_points must be > 1 when delta is not provided"
            self.nsweep_points = nsweep_points
            self[delta_name] = int(floor((stop - start) / (nsweep_points - 1)))
            self[end_name] = (start + self[delta_name] * (self.nsweep_points - 1))

        if self[end_name] != stop:
            print('Warning: exact sweep condition not possible\n')
            if delta == 0:
                print(f'Requested {start} to {stop} in {nsweep_points}')
            else:
                print(f'Requested {start} to {stop} by {delta}')
            print(f'Instead using {start} to {self[end_name]} by {self[delta_name]} in {self.nsweep_points}')

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
        assert unit in [
            'fMHz', 'fGHz', 'freg',
            'tus', 'tns', 'treg',
            'ftus', 'ftns', 'ftsamp',
            'pdeg', 'preg']
        assert scaling_factor in ['17/16', '9/8', '5/4', '3/2'], 'Currently accepting only \
        scaling values 17/16, 9/8, /5/4, 3/2'

        self.scaling_factor = scaling_factor
        self.__setattr__(name + '_start_' + unit, start)
        self.__setattr__(name + '_end_' + unit, stop)

        if unit.startswith('ft'):
            runit = 'ftsamp'
        elif 'f' == unit[0]:
            runit = 'freg'
        elif 't' == unit[0]:
            runit = 'treg'
        elif 'p' == unit[0]:
            runit = 'preg'

        start = self[name + '_start_' + runit]
        stop = self[name + '_end_' + runit]

        self.nsweep_points = len(int_exp_scale(start, stop, self.scaling_factor))
