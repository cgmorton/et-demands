import logging

def calculate_height(crop, foo, debug_flag = False):
    """Determine height of crop based on Kc and height limits

    Args:
        crop ():
        foo ():
        debug_flag (bool): If True, write debug level comments to debug.txt

    Returns:
        None
    """
    height_prev = foo.height

    # <----- previous (2000) and with error (Kcbmin vs Kcmin)
    # height = height_min + (kc_bas - kcb_min) / (kc_bas_mid - kc_min) * (height_max - height_min)
    # kc_bas_mid is maximum kc_bas found in kc_bas table read into program

    # Following conditionals added 12/26/07 to prevent any error
    if foo.kc_bas > foo.kc_min and foo.kc_bas_mid > foo.kc_min:
        foo.height = (
            crop.height_initial + (foo.kc_bas - foo.kc_min) / (foo.kc_bas_mid - foo.kc_min) *
            (crop.height_max - crop.height_initial))
    else:
        foo.height = crop.height_initial
    foo.height = min(max(crop.height_initial, max(height_prev, foo.height)), crop.height_max)

    if debug_flag:
        logging.debug(
            ('calculate_height(): unadj_height %.6f  kc_bas %.6f  kc_min %.6f  kc_bas_mid %.6f') %
            (foo.height, foo.kc_bas, foo.kc_min, foo.kc_bas_mid))
        logging.debug(
            ('calculate_height(): height_min %.6f  height_max %.6f  height %.6f') %
            (crop.height_initial, crop.height_max, foo.height))
