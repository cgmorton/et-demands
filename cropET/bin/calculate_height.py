from pprint import pprint
import sys

import util

#    Private Sub CalculateHeight()
#        Dim Hcropyesterday As Double
def CalculateHeight(crop, foo, OUT):
    """ """
    #' determine height of crop based on Kc and height limits

    hmin = crop.Starting_Crop_height
    hmax = crop.Maximum_Crop_height
    Hcropyesterday = foo.Hcrop

    #pprint(vars(crop))
    #sys.exit()

    #' Hcrop = hmin + (Kcb - Kcbmin) / (Kcbmid - Kcmin) * (hmax - hmin) <----- previous (2000) and with error (Kcbmin vs Kcmin)
    #' Kcbmid is maximum Kcb found in Kcb table read into program
    #' followng conditionals added 12/26/07 to prevent any error

    if foo.Kcb > foo.Kcmin:
        if foo.Kcbmid > foo.Kcmin:
            foo.Hcrop = hmin + (foo.Kcb - foo.Kcmin) / (foo.Kcbmid - foo.Kcmin) * (hmax - hmin)
        else:
            foo.Hcrop = hmin
    else:
        foo.Hcrop = hmin

    s = '1CalculateHeight(): unadj_hcrop %s  kcb %s  kcmin %s  kcbmid %s hmin %s  hmax %s\n'
    t = (foo.Hcrop, foo.Kcb, foo.Kcmin, foo.Kcbmid, hmin, hmax)
    OUT.debug(s % t)

    foo.Hcrop = min(max(hmin, max(Hcropyesterday, foo.Hcrop)), hmax)

    #print crop, hmin, hmax, foo.Kcb, foo.Kcmin, foo.Kcbmid, foo.Hcrop
