import math


def aFNEs(T):
    #' Tetens (1930) equation for sat. vap pressure, kPa, (T in C)
    aFNEs = 0.6108 * math.exp((17.27 * T) / (T + 237.3)) 
    return aFNEs

def aFNEsIce(T):
    #' Murray (1967) equation for sat. vap pressure over ice, kPa, (T in C)
    aFNEsIce = 0.6108 * math.exp((21.87 * T) / (T + 265.5)) 
    return aFNEsIce


#    ' determine if a winter month
#    Private Function IsWinter() As Boolean
def IsWinter(data, foo_day):
        if data.ctrl['CGDDMainDoy'] < 183:
            #' northern hemisphere
            if foo_day.monthOfCalcs < 4 or foo_day.monthOfCalcs > 10:
                return True
            else:
                return False
        else:
            #' southern hemisphere

            if foo_day.monthOfCalcs <= 10 and foo_day.monthOfCalcs >= 4:
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

