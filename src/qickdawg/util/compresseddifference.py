"""
compressed_difference
"""


import numpy as np


def compressed_difference(a):
    """
    Function that takes the difference between every other member of an array (a)
    and returns a new arry containing the differences

    new_array[0] = a[1] - a[0]
    new_array[1] = a[3]  - a[2]
    ...
    new_array[n] = a[2n+1] - a[2n]

    Parameters
    ----------
    a
        a 1D array of size n

    returns
        an array of size n//2 with takes the difference of every two
    """
    a = np.reshape(a, [a.shape[1] // 2, 2])
    a[:, 1] = a[:, 1] * -1

    return np.sum(a, axis=1)
