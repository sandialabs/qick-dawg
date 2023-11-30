"""
NVQickSweep 
===========================
Class configures the qick assembly language to loop measurements over
parameters. The main difference between this an QickSweep are
1. Handling of sweeping pulse length
2. Addition of logorithm scaling
"""

from qick.averager_program import AbsQickSweep
from ..util.intexpscale import int_exp_scale

import numpy as np


class NVQickSweep(AbsQickSweep):
    """
    Class that generates the assembly language code to change parameters
    between measurements. Modified from the original QickSweep class to handle
    pulse length sweep and implement exponential scaling

    Attributes
    ----------
    prog
        instance of qick.QickProgram 
    reg
        instance of qick.QickRegister
    start
        start value of sweep in register units
    stop
        stop value of sweep in register untis
    expts
        number of experiment to be performed in the sweep
    label (default None)
        label for the sweep parametner
    scaling_mode (default 'linear')
        string which can be 'linear' or 'exponential'
    scaling_factor (defaul '')
        string which indicates factor for exponential scaling which can be
        '3/2', '5/4', '9/8', '17/16'
    mw_channel (default -1)
        microwave channl for which the sweep is implemented, used when 
        label = 'length' to find the mode parameters

    Methods
    -------
    get_sweep_pts
        returns a 1D array with the points generated for the sweep

    update
        generates the assembly code to update the sweep parameter after each
        iteration of the loop

    reset
        generates the assembly code to rset the swept parameter(s) to the initial
        value(s)

    """

    def __init__(self, prog, reg, start, stop, expts, label=None, 
                 scaling_mode='linear', scaling_factor='', mw_channel=-1):
        """
        Run when an instance of NVQickSweep is created
        """

        super().__init__(prog)
        self.reg = reg

        self.start = start
        self.stop = stop
        self.expts = expts

        step_val = (stop - start) / (expts - 1)

        self.step_val = step_val

        self.reg.init_val = start

        if label is None:
            self.label = self.reg.name
        else:
            self.label = label

        # Custom code for changing pulse lenght which requires and additional register
        # to also change the delay length

        if label == 'length':
            assert mw_channel > -1, "must define a valid mw_channel"
            self.mw_channel = mw_channel
            self.mw_mode_register = self.prog.get_gen_reg(self.mw_channel, name='mode')

        # Code for chanigng scaling option.  original had only linear, but this adds exponential
        # and checks for errors that would cause it to fail
        self.scaling_mode = scaling_mode
        self.scaling_factor = scaling_factor

        if self.scaling_mode == 'exponential':
            assert self.scaling_factor in ['17/16', '9/8', '5/4', '3/2'], \
                'Currently accepting only scaling values 17/16, 9/8, /5/4, 3/2'
            self.numerator, self.denominator = self.scaling_factor.split('/')
            self.numerator = int(self.numerator)
            self.denominator = int(self.denominator)
            self.nshift = int(np.log2(self.denominator))
            self.temp_reg = self.prog.new_gen_reg(self.reg.page)

    def get_sweep_pts(self):
        '''
        Method that returns a 1D array of points for which the main sweep parameter is swept over
        for self.scaling_mode='linear' returns self.start to self.end in self.expts points
        for self.scaling_mode = 'exponential' returns array for self.start to self.end
            with setps determined by self.scaling_factor. see qickdawg.int_exp_scale for details 
        '''

        if self.scaling_mode == 'linear':
            return np.linspace(self.start, self.stop, self.expts)
        elif self.scaling_mode == 'exponential':
            return int_exp_scale(self.start, self.stop, self.scaling_factor)

    def update(self):
        """
        Method that generates the assembly code to update the swept register value 
        for each iteration of the appropriate loop

        if self.scaling_mode=='linear' adds self.step_val to self.reg
            if self.label =='length' also changes self.mw_mode_register

        if self.scaling_mode =='exponential' creates the step value by shifting
            the bit value of the initial value by self.nshift then addds this value to 
            the initial value. i.e. for self.scaling_factor == '3/2', the bit shift
            caluclates 1/2*initial value, then adds 1/2*initial value to the inital value
            final_value = initial_value + 1/2 initial_value == 3/2*initial_value
        """
        if self.scaling_mode == 'linear':
            self.reg.set_to(self.reg, '+', self.step_val)
            if self.label == 'length':
                self.mw_mode_register.set_to(self.mw_mode_register, '+', self.step_val)

        elif self.scaling_mode == 'exponential':
            self.prog.bitwi(self.reg.page, self.temp_reg.addr, self.reg.addr, '>>', self.nshift)
            self.prog.math(self.reg.page, self.reg.addr, self.reg.addr, '+', self.temp_reg.addr)

    def reset(self):
        """
        Method that generates the assembly code for reseting the register to the inital value
        of the loop

        This is the same as qick.QickSweep.reset() with an additional condition for self.label="length"
        so that the mode register is also reset
        """

        self.reg.reset()

        if self.label == 'length':
            self.prog.set_pulse_registers(ch=self.mw_channel,
                                          length=self.start)
