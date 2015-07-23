import logging

def calculate_height(crop, foo):
    """Determine height of crop based on Kc and height limits"""
    height_prev = foo.height

    # height = height_min + (kcb - kcb_min) / (kcb_mid - kc_min) * (height_max - height_min) <----- previous (2000) and with error (Kcbmin vs Kcmin)
    # kcb_mid is maximum kcb found in kcb table read into program

    # Followng conditionals added 12/26/07 to prevent any error
    if foo.kcb > foo.kc_min and foo.kcb_mid > foo.kc_min:
        foo.height = (
            crop.height_initial + (foo.kcb - foo.kc_min) / (foo.kcb_mid - foo.kc_min) *
            (crop.height_max - crop.height_initial))
    else:
        foo.height = crop.height_initial
    foo.height = min(max(crop.height_initial, max(height_prev, foo.height)), crop.height_max)
    
    logging.debug(
        ('calculate_height(): unadj_height %s  kcb %s  kcmin %s  kcb_mid %s') %
        (foo.height, foo.kcb, foo.kc_min, foo.kcb_mid))
    logging.debug(
        ('calculate_height(): height_min %s  height_max %s  height %s') %
        (crop.height_initial, crop.height_max, foo.height))
