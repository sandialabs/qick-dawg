import numpy as np

def int_exp_scale(start, end, scaling_factor):
    '''
    Function that generates a exponentially scaled array from 'start' to 
    'end' by 'scaling_factor'
    ---------------------------------------------------------------------
    Parameters
        start
            int value for the start of the array
        end
            int value for the end of the array
        scaling_factor
            str that must be '3/2', '5/4', '9/8', '17/16'
            that determines the scaling between one point in the 
            array and the next
    '''

    points = [start]
    
    numerator, denominator = scaling_factor.split('/')
    numerator = int(numerator)
    denominator = int(denominator)

    shift = int(np.log2(denominator))
    while points[-1] < end:
        x = int(points[-1])
        points.append(x + (x >> shift))

    return np.array(points)
