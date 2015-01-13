import math

def grow_root(crop, foo, OUT):
    """Determine depth of root zone."""
                                
    # dlk - 10/31/2011 - added zero value tests        
    fractime = 0
    if crop.curve_type == 1 and crop.end_of_root_growth_fraction_time != 0.0:
        fractime = foo.n_cumgdd / crop.end_of_root_growth_fraction_time
    if crop.curve_type > 1 and crop.end_of_root_growth_fraction_time != 0.0:    
        fractime = foo.nPL_EC / crop.end_of_root_growth_fraction_time
    if fractime < 0:    
        fractime = 0
    if fractime > 1:    
        fractime = 1
    lZr = foo.zr

    # Old linear function
    #zr = initial_rooting_depth() + (maximum_rooting_depth(ctCount) - initial_rooting_depth(ctCount)) * fractime

    # Borg and Grimes (1986) sigmoidal function       
    foo.zr = (
        (0.5 + 0.5 * math.sin(3.03 * fractime - 1.47)) *
        (foo.zrx - foo.zrn) + foo.zrn)
    delta_zr = foo.zr - lZr

    # update Dr for new moisture coming in bottom of root zone
    # Dr (depletion) will increase if new portion of root zone is < FC
    if delta_zr > 0:   
        # AM3 is mean moisture of maxrootzone - Zr layer
        foo.dr += delta_zr * (foo.aw - foo.aw3)

    s = (
        '4grow_root(): zr %s  fractime %s  zrx %s  zrn %s  dr %s  '+
        'delta_zr %s  aw %s  aw3 %s  n_cumgdd %s  nPL_EC %s  '+
        'end_of_root... %s  crop_curve_type %s\n')
    t = (
        foo.zr, fractime, foo.zrx, foo.zrn, foo.dr, delta_zr, foo.aw, foo.aw3,
        foo.n_cumgdd, foo.nPL_EC, crop.end_of_root_growth_fraction_time,
        crop.curve_type) 
    OUT.debug(s % t)
                
    # Also keep zr from #'shrinking' (for example, with multiple alfalfa cycles    
    if foo.zr < lZr:    
        foo.zr = lZr
                    
    ## [140616] remove foo's, pass in zr, zrx, zrn, aw, aw3 ...  return zr,dr

    # continuity from one season to next is done elsewhere (in xxxxxxx)
