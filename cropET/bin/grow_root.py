import logging
import math

def grow_root(crop, foo):
    """Determine depth of root zone"""
                                
    # dlk - 10/31/2011 - added zero value tests        
    fractime = 0
    if crop.curve_type == 1 and crop.end_of_root_growth_fraction_time != 0.0:
        fractime = foo.n_cgdd / crop.end_of_root_growth_fraction_time
    if crop.curve_type > 1 and crop.end_of_root_growth_fraction_time != 0.0:    
        fractime = foo.n_pl_ec / crop.end_of_root_growth_fraction_time
    if fractime < 0:    
        fractime = 0
    elif fractime > 1:    
        fractime = 1
    lZr = foo.zr

    # Old linear function
    #zr = initial_rooting_depth() + (maximum_rooting_depth(ctCount) - initial_rooting_depth(ctCount)) * fractime

    # Borg and Grimes (1986) sigmoidal function       
    foo.zr = (
        (0.5 + 0.5 * math.sin(3.03 * fractime - 1.47)) *
        (foo.zr_max - foo.zr_min) + foo.zr_min)
    delta_zr = foo.zr - lZr

    # update Dr for new moisture coming in bottom of root zone
    # Dr (depletion) will increase if new portion of root zone is < FC
    if delta_zr > 0:   
        # AM3 is mean moisture of maxrootzone - Zr layer
        foo.dr += delta_zr * (foo.aw - foo.aw3)

    logging.debug(
        ('grow_root(): zr %.6f  fractime %s  zr_max %s  zr_min %s  dr %.6f') %
        (foo.zr, fractime, foo.zr_max, foo.zr_min, foo.dr))
    logging.debug(
        ('grow_root(): delta_zr %s  AW %.6f  AW3 %.6f') %
        (delta_zr, foo.aw, foo.aw3))
    logging.debug(
        'grow_root(): n_cgdd %.6f  n_pl_ec %s' % (foo.n_cgdd, foo.n_pl_ec))
    logging.debug(
        ('grow_root(): end_of_root %s  crop_curve_type %s') %
        (crop.end_of_root_growth_fraction_time, crop.curve_type))
                
    # Also keep zr from #'shrinking' (for example, with multiple alfalfa cycles    
    if foo.zr < lZr:    
        foo.zr = lZr
                    
    ## [140616] remove foo's, pass in zr, zr_max, zr_min, aw, aw3 ...  return zr,dr

    # continuity from one season to next is done elsewhere (in xxxxxxx)
