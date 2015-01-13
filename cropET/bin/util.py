import math

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

