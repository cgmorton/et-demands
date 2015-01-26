import math
import numpy as np

def aFNEs(t):
    """ Tetens (1930) equation for sat. vap pressure, kPa, (T in C)

    Args:
        t: a float or int of the temperature [C]
        
    Returns:
        A float of the saturated vapor pressure [kPa]
    """
    return 0.6108 * math.exp((17.27 * t) / (t + 237.3)) 


def aFNEsIce(t):
    """ Murray (1967) equation for sat. vap pressure over ice, kPa, (T in C)

    Args:
        t: a float or int of the temperature [C]
        
    Returns:
        A float of the saturated vapor pressure over ice [kPa]
    """
    return 0.6108 * math.exp((21.87 * t) / (t + 265.5)) 


def is_winter(data, foo_day):
    """Determine if the input day is in a winter month

    Args:
        data: ?
        day: ?
        
    Returns:
        A boolean that is True if the input day is in a winter month
    """
    if data.ctrl['CGDDMainDoy'] < 183:
        # Northern hemisphere
        if foo_day.month < 4 or foo_day.month > 10:
            return True
        else:
            return False
    else:
        # Southern hemisphere
        if foo_day.month <= 10 and foo_day.month >= 4:
            return True 
        else:
            return False

def pair_func(elevation):
    """Calculates air pressure as a function of elevation

    Args:
        elevation: NumPy array of elevations [m]

    Returns:
        NumPy array of air pressures [kPa]
    """
    return 101.3 * np.power((293.0 - 0.0065 * elevation) / 293.0, 5.26)

def ea_from_q(p, q):
    """Calculates vapor pressure from pressure and specific humidity

    Args:
        p: NumPy array of pressures [kPa]
        q: NumPy array of specific humidities [kg / kg]

    Returns:
        NumPy array of vapor pressures [kPa]
    """
    return p * q / (0.622 + 0.378 * q)

def tdew_from_ea(ea):
    """Calculates vapor pressure at a given temperature

    Args:
        temperature: NumPy array of temperatures [C]

    Returns:
        NumPy array of vapor pressures [kPa]
    """
    return (237.3 * np.log(ea / 0.6108)) / (17.27 - np.log(ea / 0.6108))

#pDEBUG = True
#fp = open('DEBUG.txt', 'w')


class Output:
    name = None

    def __init__(self, pth='tmp', DEBUG=False):
        """ """
        self.pth = pth
        self.DEBUG = DEBUG
        if DEBUG:
            self.dfp = open('%s/DEBUG.txt' % pth, 'w')
        
    def debug(self, s=''):
        """ """
        if self.DEBUG:
            self.dfp.write(s)

    def write(self, s=''):
        """ """
        self.fp.write(s)

