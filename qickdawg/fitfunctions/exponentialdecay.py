import numpy as np


def exponential_decay(x, a, t, y0):
    
    return a * np.exp(-x / t) + y0
