"""
NVConfiguration
============================
A configuration class that is passed to averager programs to
setup the pulse sequencing for qick-dawg programs
"""


from ..util.itemattribute import ItemAttribute
from ..util.intexpscale import int_exp_scale

from math import floor
import qickdawg as qd


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
    adjust_rounds
        bandaid method.  An error is typically thrown when more than 1k reps are exectued too quickly
        this method divides the expereiment into several rounds of less than 1k reps.  Likely slows acuqisition

    add_linear_sweep
        method that generates all the attributes required for exectuing a linear sweep

    add_exponential_sweep
        method that generates all the attributes required for exectuing a linear sweep
    '''

    def __init__(self):

        self.soccfg = qd.soccfg

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
            self.__dict__[name.replace('freg', 'fMHz')] = fMHz / 1000

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

    def adjust_rounds(self, reads_per_rep=4):
        """
        Take the number of reps (self.reps) and the number of sweep points
        (self.n_sweep_points) to avoid time outs related to acquiring data too
        quickly

        Note: this may be fixed with a qick-patch
        """

        safe_round_points = 1e3

        if 'nsweep_points' not in self:
            self.nsweep_points = 1

        points_per_round = reads_per_rep * self.nsweep_points * self.reps

        if points_per_round > safe_round_points:
            reps = safe_round_points // (reads_per_rep * self.nsweep_points)

            self.rounds = int(self.reps // reps)
            self.reps = int(reps)

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

        self.__setattr__(name + '_start_' + unit, start)
        self.__setattr__(name + '_end_' + unit, stop)
        self.__setattr__(name + '_delta_' + unit, delta)

        self.scaling_mode = 'linear'

        if 'f' == unit[0]:
            unit = 'freg'
        elif 't' == unit[0]:
            unit = 'treg'

        if (delta != 0) & (nsweep_points == 0):

            self.nsweep_points = int(
                (self[name + '_end_' + unit]
                 - self[name + '_start_' + unit])
                / self[name + '_delta_' + unit] + 1)

        elif (delta == 0) & (nsweep_points != 0):

            self.nsweep_points = nsweep_points
            start_reg = self[name + '_start_' + unit]
            end_reg = self[name + '_end_' + unit]

            if not (end_reg - start_reg) % (nsweep_points - 1):
                self.__setattr__(name + '_delta_' + unit,
                                 (end_reg - start_reg) // (nsweep_points - 1))
            else:
                delta_reg = floor((end_reg - start_reg) / (nsweep_points - 1))
                self.__setattr__(name + '_delta_' + unit,
                                 delta_reg)
                self.__setattr__(name + '_end_' + unit,
                                 start_reg + delta_reg * (nsweep_points - 1))

        else:
            assert 0, 'Either delta and nsweep_points are required, but not both'

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
