import math

def grow_root(crop, foo, OUT):
    """Determine depth of root zone    """
                                
    # dlk - 10/31/2011 - added zero value tests        
    fractime = 0
    if crop.crop_curve_type == 1 and crop.end_of_root_growth_fraction_time != 0.0:
        fractime = foo.ncumGDD / crop.end_of_root_growth_fraction_time
    if crop.crop_curve_type > 1 and crop.end_of_root_growth_fraction_time != 0.0:    
        fractime = foo.nPL_EC / crop.end_of_root_growth_fraction_time
    if fractime < 0:    
        fractime = 0
    if fractime > 1:    
        fractime = 1
    lZr = foo.Zr

    # Old linear function
    # Zr = Initial_rooting_depth() + (Maximum_rooting_depth(ctCount) - Initial_rooting_depth(ctCount)) * fractime

    # Borg and Grimes (1986) sigmoidal function       
    foo.Zr = (0.5 + 0.5 * math.sin(3.03 * fractime - 1.47)) * (foo.Zrx - foo.Zrn) + foo.Zrn
    delta_zr = foo.Zr - lZr

    # update Dr for new moisture coming in bottom of root zone
    # Dr (depletion) will increase if new portion of root zone is < FC
    if delta_zr > 0:   
        foo.Dr = foo.Dr + delta_zr * (foo.AW - foo.AW3) #' AM3 is mean moisture of maxrootzone - Zr layer

    s = '4grow_root(): Zr %s  fractime %s  Zrx %s  Zrn %s  Dr %s  delta_zr %s  AW %s  AW3 %s  ncumGDD %s  nPL_EC %s  end_of_root... %s  Crop_curve_type %s\n'
    t = (
        foo.Zr, fractime, foo.Zrx, foo.Zrn, foo.Dr, delta_zr, foo.AW, foo.AW3,
        foo.ncumGDD, foo.nPL_EC, crop.end_of_root_growth_fraction_time,
        crop.crop_curve_type) 
    OUT.debug(s % t)
                
    # Also keep Zr from #'shrinking' (for example, with multiple alfalfa cycles    
    if foo.Zr < lZr:    
        foo.Zr = lZr
                    
    ## [140616] remove foo's, pass in Zr, Zrx, Zrn, AW, AW3 ...  return Zr,Dr

    # continuity from one season to next is done elsewhere (in xxxxxxx)
