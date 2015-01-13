from pprint import pprint

def calculate_height(crop, foo, OUT):
    """Determine height of crop based on Kc and height limits"""
    height_min = crop.height_initial
    height_max = crop.height_maximum
    height_prev = foo.height

    #pprint(vars(crop))

    # hcrop = hmin + (kcb - kcb_min) / (kcb_mid - kc_min) * (hmax - hmin) <----- previous (2000) and with error (Kcbmin vs Kcmin)
    # kcb_mid is maximum kcb found in kcb table read into program

    # Followng conditionals added 12/26/07 to prevent any error
    if foo.kcb > foo.kc_min and foo.kcb_mid > foo.kc_min:
        foo.height = (
            height_min + (foo.kcb - foo.kc_min) / (foo.kcb_mid - foo.kc_min) *
            (height_max - height_min))
    else:
        foo.hcrop = height_min

    s = ('1calculate_height(): unadj_height %s  kcb %s  kcmin %s  '+
         'kcb_mid %s hmin %s  hmax %s\n')
    t = (foo.height, foo.kcb, foo.kc_min, foo.kcb_mid, height_min, height_max)
    OUT.debug(s % t)

    foo.height = min(max(height_min, max(height_prev, foo.height)), height_max)
    #print crop, height_min, height_max, foo.kcb, foo.kc_min, foo.kcb_mid, foo.height
