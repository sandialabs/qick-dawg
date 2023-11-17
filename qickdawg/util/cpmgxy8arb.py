import numpy as np

def cpmgxy8_arb(pi2, tau):
    '''
    returns i, q valuse for IQIQQIQI sequence with tau spacing
    pi2 and tau in ns
    '''
    pi = 2*pi2
    
    t = np.arange(0, pi2*2*8 + tau*2*8, 0.120)
    
    if len(t) > 65536:
        assert 0, "Must have fewer than 65536 points for cpmg arb sequence, you are using \
        {} points".format(len(t))
    
    i = 0*t
    q = 0*t
    
    i[np.where((t > tau) & (t <= (pi + tau)))] = 1
    q[np.where((t >= (pi + 3 * tau)) & (t <= (2 * pi + 3 * tau)))] = 1
    i[np.where((t >= (2 * pi + 5 * tau)) & (t <= (3 * pi + 5 * tau)))] = 1
    q[np.where((t >= (3 * pi + 7 * tau)) & (t <= (4 * pi + 7 * tau)))] = 1
    q[np.where((t >=  (4 * pi + 9 * tau)) & (t <= (5 * pi + 9*tau )))] = 1
    i[np.where((t >= ( 5 * pi + 11*tau)) & (t<=(6* pi + 11*tau)))] = 1
    q[np.where((t >= (6*pi + 13*tau)) & (t<=(7* pi + 13*tau)))] = 1
    i[np.where((t >= (7*pi + 15*tau)) & (t<=(8* pi + 15*tau)))] = 1
    
    return i, q

