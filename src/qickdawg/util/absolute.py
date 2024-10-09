"""
absolute
===============================================================================

"""

import numpy as np


def absolute(a):
    '''
    A funciton that returns the quadrature sum of an array of shape
    [2, n]

    Parameters
    a
        an array of size [2, n]

    returns
        an array of size [n] such that the values are sqrt(a[0]**2 + a[1]**2)
    '''

    return np.sqrt(a[0]**2 + a[1]**2)
