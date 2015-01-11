import math
import util

def GrowRoot(crop, foo, OUT):
    """ """
    #' update root zone              
    #Private Sub GrowRoot()              
    #Dim Delta_Zr, fractime, lZr As Double
                                
    #' parameters                    
                                
    #' determine depth of root zone
                        
    #' dlk - 10/31/2011 - added zero value tests
                
    fractime = 0
    if crop.Crop_curve_type == 1 and crop.End_of_Root_growth_fraction_time != 0.0:
        fractime = foo.ncumGDD / crop.End_of_Root_growth_fraction_time
    if crop.Crop_curve_type > 1 and crop.End_of_Root_growth_fraction_time != 0.0:    
        fractime = foo.nPL_EC / crop.End_of_Root_growth_fraction_time
    if fractime < 0:    
        fractime = 0
    if fractime > 1:    
        fractime = 1
    lZr = foo.Zr

    #' old linear function
    #' Zr = Initial_rooting_depth() + (Maximum_rooting_depth(ctCount) - Initial_rooting_depth(ctCount)) * fractime
    #' Borg and Grimes (1986) sigmoidal function
            
    foo.Zr = (0.5 + 0.5 * math.sin(3.03 * fractime - 1.47)) * (foo.Zrx - foo.Zrn) + foo.Zrn
    Delta_Zr = foo.Zr - lZr

    #' update Dr for new moisture coming in bottom of root zone
    #' Dr (depletion) will increase if new portion of root zone is < FC

    if Delta_Zr > 0:   
        foo.Dr = foo.Dr + Delta_Zr * (foo.AW - foo.AW3) #' AM3 is mean moisture of maxrootzone - Zr layer

    s = '4GrowRoot(): Zr %s  fractime %s  Zrx %s  Zrn %s  Dr %s  Delta_Zr %s  AW %s  AW3 %s  ncumGDD %s  nPL_EC %s  End_of_Root... %s  Crop_curve_type %s\n'
    t = (foo.Zr, fractime, foo.Zrx, foo.Zrn, foo.Dr, Delta_Zr, foo.AW, foo.AW3, foo.ncumGDD, foo.nPL_EC, crop.End_of_Root_growth_fraction_time, crop.Crop_curve_type) 
    OUT.debug(s % t)
                
    #' also keep Zr from #'shrinking' (for example, with multiple alfalfa cycles
            
    if foo.Zr < lZr:    
        foo.Zr = lZr
                    
    ## [140616] remove foo's, pass in Zr, Zrx, Zrn, AW, AW3 ...  return Zr,Dr

    #' continuity from one season to next is done elsewhere (in xxxxxxx)
    #End Sub             


