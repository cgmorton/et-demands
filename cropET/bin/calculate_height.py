from pprint import pprint

def calculate_height(crop, foo, OUT):
    """Determine height of crop based on Kc and height limits"""
    hmin = crop.starting_crop_height
    hmax = crop.maximum_crop_height
    hcrop_yesterday = foo.hcrop

    #pprint(vars(crop))

    # hcrop = hmin + (kcb - kcb_min) / (kcb_mid - kc_min) * (hmax - hmin) <----- previous (2000) and with error (Kcbmin vs Kcmin)
    # kcb_mid is maximum kcb found in kcb table read into program

    # Followng conditionals added 12/26/07 to prevent any error
    if foo.kcb > foo.kc_min:
        if foo.kcb_mid > foo.kc_min:
            foo.hcrop = (
                hmin + (foo.kcb - foo.kc_min) / (foo.kcb_mid - foo.kc_min) * (hmax - hmin))
        else:
            foo.hcrop = hmin
    else:
        foo.hcrop = hmin

    s = ('1calculate_height(): unadj_hcrop %s  kcb %s  kcmin %s  kcbmid %s '+
         'hmin %s  hmax %s\n')
    t = (foo.hcrop, foo.kcb, foo.kc_min, foo.kcb_mid, hmin, hmax)
    OUT.debug(s % t)

    foo.Hcrop = min(max(hmin, max(hcrop_yesterday, foo.hcrop)), hmax)
    #print crop, hmin, hmax, foo.kcb, foo.kc_min, foo.kcbmid, foo.Hcrop
