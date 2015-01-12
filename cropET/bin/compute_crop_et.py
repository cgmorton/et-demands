import math
from pprint import pprint
import sys

import compute_crop_gdd
import calculate_height
import grow_root
import kcb_daily
import runoff
import util

def compute_crop_et(t30, data, crop, et_cell, foo, foo_day, OUT):
    """crop et computations"""

    #print 'in compute_crop_et()'

    #pprint(vars(et_cell))
    #pprint(vars(crop))
    #pprint(vars(foo))

    #' determine if within a new growing period, etc.
    #' update 30 day mean air temperature (t30) and cumulative growing degree days (cumGDD)
    #compute_crop_gdd()

    s = 'compute_crop_et() for %s crop %s %s %s %s\n' %  (
        et_cell.cell_id, crop.crop_class_num, crop.name.replace(' ','_'),
        foo_day.doy, foo_day.date)
    OUT.debug(s)

    compute_crop_gdd.compute_crop_gdd(data, crop, foo, foo_day, OUT)
    s = '3compute_crop_et():a jdStartCycle %s cumgdd %s GDD %s TMean %s\n' % (
        foo.jd_start_cycle, foo.cumgdd, foo.gdd, foo_day.tmean)
    OUT.debug(s)


    #' calculate height of vegetation.  Call was moved up to this point 12/26/07 for use in adj. Kcb and kc_max
    calculate_height.calculate_height(crop, foo, OUT)

    #' interpolate Kcb and make climate adjustment (for ETo basis)

    #If Not kcb_daily(t30):    Return False
    kcb_daily.kcb_daily(data, crop, et_cell, foo, foo_day, OUT)
    #pprint(vars(crop))
    #pprint(vars(et_cell))

    #' Jump to end if open water (crops numbers 55 through 57 are open water)

    #If crop.crop_class_num < 55 or crop.crop_class_num > 57:    #' <------ specific value for crop number
    ### return here if open water
    #print type(crop.crop_class_num), crop.crop_class_num
    if crop.crop_class_num in [55,56,57]:
        return 

    #' Maximum Kc when soil is wet.  For grass reference, kc_max = 1.2 plus climatic adj.
    #' For alfalfa reference, kc_max = 1.0, with no climatic adj.
    #' kc_max is set to less than 1.0 during winter to account for effects of cold soil.

    #' ETo basis:  Switched over to this 12/2007 #' Allen and Huntington
    #' Note that u2 and rhmin were disabled when KcETr code was converted to ETr basis
    #' these have been reactivated 12/2007 by Allen, based on daily wind and TDew
    #' rhmin and u2 are computed in Climate subroutine called above

    foo.Hcrop = max(0.05, foo.Hcrop) #' m #'limit Hcrop for numerical stability
    if data.ctrl['refETType'] > 0:    #' edited by Allen, 6/8/09 to use kc_max from file if given
        if crop.crop_kc_max > 0.3:   
            kc_max = crop.crop_kc_max
        else:
            #' ETr basis
            kc_max = 1
    else:
        if crop.crop_kc_max > 0.3:   
            kc_max = (
                crop.crop_kc_max +
                (0.04 * (foo_day.u2 - 2) - 0.004 * (foo_day.rhmin - 45)) *
                (foo.Hcrop / 3) ** 0.3)
        else:
            kc_max = (
                1.2 + (0.04 * (foo_day.u2 - 2) - 0.004 * (foo_day.rhmin - 45)) *
                (foo.Hcrop / 3) ** 0.3)
        #' if yearOfCalcs < 1952:    PrintLine(lfNum, "ctcount, cropn, hcrop, crop_kc_max,RHMin,u2" & Chr(9) & getDmiDate(dailyDates(sdays - 1)) & Chr(9) & crop.crop_class_num & ", " & cropn & Chr(9) & Hcrop & Chr(9) & crop_kc_max(ctCount) & Chr(9) & rhmin & Chr(9) & u2)

    #' if yearOfCalcs < 1952:    PrintLine(lfNum, "Initial kc_max" & Chr(9) & getDmiDate(dailyDates(sdays - 1)) & Chr(9) & kc_max)

    #' ETr basis:
    #' kc_max = 1#  #'for ETr ******************* #'commented out 12/2007

    #' assign fraction of ground covered for each of three nongrowing season cover types

    if crop.crop_class_num == 44:    #' bare soil  #.  changed Jan. 2007 for add. crop cats.
        foo.fc = 0.0
    if crop.crop_class_num == 45:    #' Mulched soil, including grain stubble  #.
        foo.fc = 0.4
    if crop.crop_class_num == 46:    #' Dormant turf/sod (winter time)  #.
        foo.fc = 0.7 #' was 0.6

    # kc_max and foo.fc for wintertime land use (Nov-Mar)
    wscc = crop.winter_surface_cover_class

    # wscc = 1 bare, 2 mulch, 3 sod

    # Assume that winter time is constrained to Nov thru March in northern hemisphere
    if util.is_winter(data, foo_day):    
        # Bare soil
        if crop.crop_class_num == 44:
            # Less soil heat in winter.
            if data.ctrl['refETType'] > 0:
                # For ETr (Allen 3/2008)
                kc_max = 0.9 
            else:
                # For ETo  (Allen 12/2007)
                kc_max = 1.1 
            foo.fc = 0.0
        # Mulched soil, including grain stubble
        if crop.crop_class_num == 45:
            if data.ctrl['refETType'] > 0:
                # For ETr (Allen 3/2008)
                kc_max = 0.85 
            else:
                # For ETo (0.85 * 1.2)  (Allen 12/2007)
                kc_max = 1.0  
            foo.fc = 0.4
        # Dormant turf/sod (winter time)
        if crop.crop_class_num == 46:
            if data.ctrl['refETType'] > 0:    
                # For ETr (Allen 3/2008)
                kc_max = 0.8
            else:
                # For ETo (0.8 * 1.2)  (Allen 12/2007)
                kc_max = 0.95
            # Was 0.6
            foo.fc = 0.7 

        #' also set up kc_max for nongrowing seasons for other crops
        #' kc_max for wintertime land use (Nov-Mar)for nongrowing season crops

        # (not ground cover class)
        if crop.crop_class_num < 44 or crop.crop_class_num > 46:

            if wscc == 1:    #' bare soil    #'note that these are ETr based.  Mult by 1.2 (plus adj?) for ETo base  *************
                #' foo.fc is calculated below

                if data.ctrl['refETType'] > 0:    #' Allen 3/08
                    kc_max = 0.9 #' for ETr
                else:
                    kc_max = 1.1 #' for ETo  #'Allen 12/2007 **********
            if wscc == 2:    #' Mulched soil, including grain stubble
                if data.ctrl['refETType'] > 0:   
                    kc_max = 0.85 #' for ETr
                else:
                    kc_max = 1.0  #' for ETo (0.85 * 1.2)  #'Allen 12/2007 ************
            if wscc == 3:    #' Dormant turf/sod (winter time)
                if data.ctrl['refETType'] > 0:   
                    kc_max = 0.8 #' for ETr
                else:
                    kc_max = 0.95 #' for ETo (0.8 * 1.2)  #'Allen 12/2007  **********

        #' if yearOfCalcs < 1952:    PrintLine(lfNum, "Winter kc_max" & Chr(9) & getDmiDate(dailyDates(sdays - 1)) & Chr(9) & kc_max & Chr(9) & "for wscc of " & wscc)

    #' added 2/21/08 to make sure that a winter cover class is used if during nongrowing season

    #' override Kcb assigned from KcbDaily if nongrowing season and not water
    if (not foo.in_season and
        (crop.crop_class_num < 55 or crop.crop_class_num > 57)):    
        OUT.debug('3ComputeCropET():b0  Kcb %s  Kcb_wscc %s  wscc %s\n' % (
            foo.kcb, foo.kcb_wscc[wscc], wscc))
        foo.kcb = foo.kcb_wscc[wscc] 

    #' if yearOfCalcs < 1952:    PrintLine(lfNum, "Initial kcb" & Chr(9) & getDmiDate(dailyDates(sdays - 1)) & Chr(9) & Kcb)

    #' limit kc_max to at least Kcb + .05

    kc_max = max(kc_max, foo.kcb + 0.05)
    #' if yearOfCalcs < 1952:    PrintLine(lfNum, "Final kc_max" & Chr(9) & getDmiDate(dailyDates(sdays - 1)) & Chr(9) & kc_max)

    #' Kcmin is minimum evaporation for 0 ground cover under dry soil surface
    #' but with diffusive evaporation.
    #' Kcmin is used to estimate fraction of ground cover for crops.
    #' Set Kcmin to 0.1 for all vegetation covers (crops and natural)
    #' Kcb will be reduced for all surfaces not irrigated when stressed, even during winter.

    foo.Kcmin = 0.1 #' use same value for both ETr or ETo bases.

    #' estimate height of vegetation for estimating fraction of ground cover for evaporation
    #' and fraction of ground covered by vegetation

    if crop.crop_class_num < 44 or crop.crop_class_num > 46:    #' <------ specific value for crop number (no's changed Jan. 07)
        #'  was: if crop.crop_class_num < 39 or crop.crop_class_num > 41:
        if kc_max <= foo.Kcmin:    
            kc_max = foo.Kcmin + 0.001
        if foo.in_season:   
            if foo.kcb > foo.Kcmin:   
                #' heightcalc  #'call to heightcalc was moved to top of this subroutine 12/26/07 by Allen
                foo.fc = ((foo.kcb - foo.Kcmin) / (kc_max - foo.Kcmin)) ** (1 + 0.5 * foo.Hcrop)
                # limit so that few > 0
                if foo.fc > 0.99:    
                    foo.fc = 0.99 
            else:
                foo.fc = 0.001

    # 
    s = '3ComputeCropET():b kc_max %s  Kcmin %s  Kcb %s  InSeason %s\n' % (kc_max, foo.Kcmin, foo.kcb, foo.in_season)
    OUT.debug(s)


    # Estimate infiltrating precipitation
    # Yesterday's infiltration
    foo.Pinfyest = foo.Pinf 
    foo.Pinf = 0.0
    foo.SRO = 0.0
    if foo_day.precip > 0:   
        # Compute weighted depletion of surface from irr and precip areas
        foo.Depl_surface = foo.wtirr * foo.De + (1 - foo.wtirr) * foo.Dep
        runoff.runoff(foo, foo_day, OUT)
        foo.Pinf = foo_day.precip - foo.SRO
        #if foo.SRO > 0.01:   
            #' Debug.Writeline "P and SRO "; P; SRO
            #' return false

    s = '3ComputeCropET():c Pinfyest %s  Pinf %s  runoff().SRO %s  Precip %s  Depl_surface %s  wtirr %s  De %s  Dep %s\n'
    t = (foo.Pinfyest, foo.Pinf, foo.SRO, foo_day.precip, foo.Depl_surface, foo.wtirr, foo.De, foo.Dep)
    OUT.debug(s % t)

    # Compare precipitation and irrigation to determine value for fw

    # At this point, irrigation depth, Irr is based on yesterday's irrigations
    # (irrig has not yet been updated)
    # Note: In Idaho CU computations, scheduling is assumed automated according to MAD
    # Following code contains capacity to specify manual and #'special' irrigations, but isn't used here

    # Ireal is a real irrigation experienced and read in
    # Imanual is a manually specified irrigation from an array
    # Ispecial is a special irrigation for leaching or germination
    Ireal = 0.0
    Imanual = 0.0
    Ispecial = 0.0

    # Update fw of irrigation if an irrigation yesterday
    if Ireal + foo.Iauto > 0:
        foo.fwi = foo.fwstd
    else:
        if Imanual + Ispecial > 0:   
            foo.fwi = foo.fwspec

    #' find current water in fwi portion of Ze layer

    ## [140820] changed the tests below to round(watinZe?,6) in both py/vb for consistency
    ## both versions tested values ~1e-15, which were being passed through
    ## and would happen inconsistently between py/vb versions
    watinZe = foo.TEW - foo.De
    OUT.debug('3ComputeCropET():d0 TEW %s  De %s  watinZe %s\n' % (foo.TEW, foo.De, watinZe))

    #if watinZe <= 0.:    
    if round(watinZe,6) <= 0.:    
        watinZe = 0.001
    if watinZe > foo.TEW:    
        watinZe = foo.TEW
    OUT.debug('3ComputeCropET():d1 TEW %s  De %s  watinZe %s\n' % (foo.TEW, foo.De, watinZe))

    # Find current water in fwp portion of Ze layer
    # the use of 'fewp' (precip) fraction of surface
    watinZep = foo.TEW - foo.Dep #' follows Allen et al. 2005 (ASCE JIDE) extensions
    OUT.debug('3ComputeCropET():d0p TEW %s  Dep %s  watinZep %s\n' % (
        foo.TEW, foo.Dep, watinZep))
    #if watinZep <= 0.:    
    if round(watinZep,6) <= 0.:    
        watinZep = 0.001
    if watinZep > foo.TEW:    
        watinZep = foo.TEW
    OUT.debug('3ComputeCropET():d1p TEW %s  Dep %s  watinZep %s\n' % (
        foo.TEW, foo.Dep, watinZep))

    # Fraction of ground that is both exposed and wet
    few = 1 - foo.fc
    if few > foo.fwi:
        # Limit to fraction wetted by irrigation
        few = foo.fwi 
    if few < 0.001:
        few = 0.001

    # Fraction of ground that is exposed and wet by precip beyond irrigation
    fewp = 1 - foo.fc - few
    if fewp < 0.001:    
        fewp = 0.001

    # Was "totwatinZe = watinZe * few + watinZep * fewp" until 5/9/07
    # (corrected)
    foo.totwatinZe = (watinZe * few + watinZep * fewp) / (few + fewp)

    s = '3compute_crop_et():d fwi %s stn_whc %s  AW %s  TEW %s  Dep %s  De %s  watinZe %s  watinZep %s  fewp %s  totwatinZe %s\n'
    t = (foo.fwi, et_cell.stn_whc, foo.AW, foo.TEW, foo.Dep, foo.De, watinZe,
         watinZep, fewp, foo.totwatinZe)
    OUT.debug(s % t)

    #' TEW is total evaporable water (end of 2nd or 3rd stage)
    #' REW is readily evaporable water (end of stage 1)
    #' De is depletion of evaporation layer wetted by irrigation and exposed
    #' De is computed here each day and retained as static
    #' De should be initialized at start of each new crop
    #' in crop cycle routine
    #' Dep is depletion of evaporation layer wetted by Precip beyond irrigation

    #' setup for water balance of evaporation layer

    # Deep percolation from Ze layer (not root zone, only surface soil)
    if foo.fwi > 0.0001:   
        # De, irr from yesterday
        # fw changed to foo.fwi 8/10/06
        Dpe = foo.Pinf + foo.simulated_irr / foo.fwi - foo.De
    else:
        # De, irr from yesterday
        # fw changed to fwi 8/10/06
        Dpe = foo.Pinf + foo.simulated_irr / 1 - foo.De

    if Dpe < 0:
        Dpe = 0.0
    # Dep from yesterday
    Dpep = foo.Pinf - foo.Dep 
    if Dpep < 0:
        Dpep = 0.0

    #' Compute initial balance of Ze layer.  E and T from Ze layer
    #' will be added later.  De is depletion of Ze layer, mm
    #' Pinf is P that infiltrates
    #' This balance is here, since irr is yesterday's irrigation and
    #' it is assumed to be in morning before E and T for day have
    #' occurred.  It is assumed that P occurs earlier in morning.
    if foo.fwi > 0.0001:   
        foo.De = foo.De - foo.Pinf - foo.simulated_irr / foo.fwi + Dpe #' fw changed to fwi 8/10/06
        OUT.debug('3ComputeCropET():da De %s\n' % (foo.De))
    else:
        foo.De = foo.De - foo.Pinf - foo.simulated_irr / 1 + Dpe #' fw changed to fwi 8/10/06
        OUT.debug('3ComputeCropET():db De %s\n' % (foo.De))

    if foo.De < 0:
        foo.De = 0.0
        OUT.debug('3ComputeCropET():dc De %s\n' % (foo.De))
    if foo.De > foo.TEW:
        # Use TEW rather than TEW2use to conserve De
        foo.De = foo.TEW 
        OUT.debug('3ComputeCropET():dd De %s\n' % (foo.De))

    # Update depletion of few beyond that wetted by irrigation
    foo.Dep = foo.Dep - foo.Pinf + Dpep
    if foo.Dep < 0:    
        foo.Dep = 0.0
    if foo.Dep > foo.TEW:    
        foo.Dep = foo.TEW

    #' reducer coefficient for evaporation based on moisture left
    #' This is set up for three stage evaporation
    #' REW is depletion at end of stage 1 (energy limiting), mm
    #' TEW2 is depletion at end of stage 2 (typical soil), mm
    #' TEW3 is depletion at end of stage 3 (rare), mm
    #' Stage 3 represents a cracking soil where cracks open on drying
    #' Kr2 is value for Kr at transition from stage 2 to 3
    #'   i.e., when depletion is equal to TEW2.
    #' for example, for a cracking clay loam soil,
    #'     REW=8 mm, TEW2=50 mm, TEW3=100 mm and Kr2=0.2
    #' for a noncracking clay loam soil, REW=8 mm, TEW2=50 mm, TEW3=0, Kr2=0
    #' make sure that Kr2 is 0 if TEW3=0

    if foo.TEW3 < 0.1:    
        foo.Kr2 = 0.0

    #' De is depletion of evaporation layer, mm

    #' make sure De does not exceed Dr (depl. of root zone), since Dr includes De.
    #' IF De > Dr THEN De = Dr   #'this causes problems during offseason.  don't use

    #' for portion of surface that has been wetted by irrigation and precipitation

    #' reduce TEW (and REW) during winter when ETr drops below 4 mm/day (FAO-56)

    tew2use = foo.TEW2
    TEW3use = foo.TEW3 #' for stage 3 drying (cracking soils (not in Idaho))
    rew2use = foo.REW
    foo.ETref30 = max(0.1, foo.ETref30) #' mm/day  #'edited from ETr to ETref 12/26/2007
    if data.ctrl['refETType'] > 0:   
        ETr_threshold = 4 #' for ETr basis
    else:
        ETr_threshold = 5 #' for ETo basis #'added March 26, 2008 RGA

    if foo.ETref30 < ETr_threshold:    #' use 30 day ETr, if less than 4 or 5 mm/d to reduce TEW
        tew2use = foo.TEW2 * math.sqrt(foo.ETref30 / ETr_threshold)
        TEW3use = foo.TEW3 * math.sqrt(foo.ETref30 / ETr_threshold)
        if rew2use > 0.8 * tew2use:    
            rew2use = 0.8 * tew2use #' limit REW to 30% less than TEW    #'was 0.7 until 4/16/08

    s = '3ComputeCropET():e TEW2 %s  ETref30 %s  ETr_threshold %s\n'
    t = (foo.TEW2, foo.ETref30, ETr_threshold)
    OUT.debug(s % t)

    if foo.De <= rew2use:   
        Kr = 1
    else:
        if foo.De <= tew2use:   
            Kr = foo.Kr2 + (1 - foo.Kr2) * (tew2use - foo.De) / (tew2use - rew2use)
        else:
            if TEW3use > tew2use:    #' Stage 3 drying (cracking soils)
                Kr = foo.Kr2 * (TEW3use - foo.De) / (TEW3use - tew2use)
            else:
                Kr = 0.0

    #' portion of surface that has been wetted by precipitation

    if foo.Dep <= rew2use:   
        Krp = 1
    else:
        if foo.Dep <= tew2use:   
            Krp = foo.Kr2 + (1 - foo.Kr2) * (tew2use - foo.Dep) / (tew2use - rew2use)
        else:
            if TEW3use > tew2use:    #' Stage 3 drying (cracking soils)
                Krp = foo.Kr2 * (TEW3use - foo.Dep) / (TEW3use - tew2use)
            else:
                Krp = 0.0

    #' evaporation coefficient Ke
    #' partition Ke into that from irrigation wetted and from precip wetted
    #' Kelimit = (few + fewp) * kc_max
    #' find weighting factor based on water in Ze layer in irrig. wetted and precip wetted

    #' following conditional added July 2006 for when denominator is zero

    if (few * watinZe + fewp * watinZep) > 0.0001:   
        foo.wtirr = few * watinZe / (few * watinZe + fewp * watinZep)
    else:
        foo.wtirr = few * watinZe

    if foo.wtirr < 0.:    
        foo.wtirr = 0.
    if foo.wtirr > 1.:    
        foo.wtirr = 1.

    s = '3ComputeCropET():m few %s  watinZe %s  fewp %s  watinZep %s  wtirr %s\n'
    t = (few, watinZe, fewp, watinZep, foo.wtirr)
    OUT.debug(s % t)

    #' Ke = Kr * (kc_max - foo.kcb) #' this was generic for irr + precip
    #' IF Ke > few * kc_max THEN Ke = few * kc_max

    Kei = Kr * (kc_max - foo.kcb) * foo.wtirr

    #' limit to maximum rate per unit surface area

    if Kei > few * kc_max:    
        Kei = few * kc_max
    Kep = Krp * (kc_max - foo.kcb) * (1 - foo.wtirr)
    if Kep > fewp * kc_max:    
        Kep = fewp * kc_max
    if Kei < 0:    
        Kei = 0.0
    if Kep < 0:    
        Kep = 0.0
    ke = Kei + Kep

    #' IF Ke > Kelimit THEN Ke = Kelimit

    #' transpiration coefficient for moisture stress

    TAW = foo.AW * foo.Zr
    if TAW < 0.001:
        TAW = 0.001
    raw = foo.MAD * TAW / 100 #' MAD is set to MADini or MADmid in KcbDaily sub.

    #' remember to check reset of AD and RAW each new crop season.  #####

    #' AD is allowable depletion

    if foo.Dr > raw:   
        ks = (TAW - foo.Dr) / (TAW - raw)
    else:
        ks = 1
    if ks < 0:    
        ks = 0.0

    #' check to see if stress flag is turned off.

    if crop.invoke_stress < 1:   
        ks = 1 #' no stress if flag = 0 #'used to be irrigtypeflag=2

    if crop.invoke_stress == 1:   
        # Unrecoverable stress.  No greenup after this.
        if ks < 0.05 and foo.in_season and foo.kcb > 0.3:
            foo.stressEvent = True
        if foo.stressEvent:   
            ks = 0.0

    #' calculate Kc during snow cover

    kc_mult = 1
    if foo_day.snow_depth > 0.01:   
        # Radiation term for reducing Kc to actCount for snow albedo
        k_rad = (
            0.000000022 * foo_day.DoY ** 3 - 0.0000242 * foo_day.doy ** 2 +
            0.006 * foo_day.doy + 0.011)
        albedo_snow = 0.8
        albedo_soil = 0.25
        kc_mult = 1 - K_radiation + (1 - albedo_snow) / (1 - albedo_soil) * k_rad
        # Was 0.9, reduced another 30% to account for latent heat of fusion of melting snow
        kc_mult = kc_mult * 0.7

    ke = ke * kc_mult
    Kei = Kei * kc_mult
    Kep = Kep * kc_mult

    # Don't reduce Kcb, since it may be held constant during nongrowing periods.  Make adjustment to kc_act
    kc_act = kc_mult * ks * foo.kcb + ke
    kc_pot = foo.kcb + ke
    
    #' if yearOfCalcs < 1952:    PrintLine(lfNum, "First kcbas, kcpot, kcact" & Chr(9) & getDmiDate(dailyDates(sdays - 1)) & Chr(9) & Kcb & Chr(9) & kc_pot & Chr(9) & kc_act)

    # ETref is defined (to ETo or ETr) in CropCycle sub #'Allen 12/26/2007
    foo.etc_act = kc_act * foo_day.ETref
    foo.etc_pot = kc_pot * foo_day.ETref
    foo.etc_bas = foo.kcb * foo_day.ETref

    Delast = 0  ## Used below here

    s = '3ComputeCropET():f Kcmult %s  few %s  fewp %s  Kei %s  Kep %s  ks %s  Kr %s  Krp %s  wtirr %s  De %s  Dep %s\n'
    t = (kc_mult, few, fewp, Kei, Kep, ks, Kr, Krp, foo.wtirr, foo.De, foo.Dep)
    OUT.debug(s % t)
    s = '3ComputeCropET():g Delast %s  Dep %s  tew2use %s  rew2use %s  ETref %s  raw %s  Zr %s\n'
    t = (Delast, foo.Dep, tew2use, rew2use, foo_day.ETref, raw, foo.Zr)
    OUT.debug(s % t)
    s = '3ComputeCropET():h Kcb %s  kc_pot %s  kc_act %s  ETcbas %s  ETcpot %s  ETcact %s  Dr %s  Pinf %s\n'
    t = (foo.kcb, kc_pot, kc_act, foo.etc_bas, foo.etc_pot, foo.etc_act, foo.Dr, foo.Pinf)
    OUT.debug(s % t)

    E = ke * foo_day.ETref
    Ei = Kei * foo_day.ETref
    Ep = Kep * foo_day.ETref

    # Begin Water balance of evaporation layer and root zone

    # Transpiration from Ze layer
    # transpiration proportioning

    ## TP ze never initialized, assume 0.0 value
    ## also used in SetupDormant(), but value set explicity...wonder if was meant to be global????
    ze = 0.0   # I added this line
    if ze < 0.0001:    
        ze = 0.0001
    if foo.Zr < 0.0001:    
        foo.Zr = 0.01
    Ktprop = (ze / foo.Zr) ** 0.6
    if Ktprop > 1:    
        Ktprop = 1

    # Zr is root depth, m
    # Dr is depletion in root zone, mm
    # AW is available water for soil, mm/m

    # For irrigation wetted fraction
    KTreducerdenom = 1 - foo.Dr / TAW
    if KTreducerdenom < 0.001:    
        KTreducerdenom = 0.001
    KTreducer = few * (1 - foo.De / tew2use) / KTreducerdenom #' few added, 8/2006, that is not in Allen et al., 2005, ASCE
    Ktprop = Ktprop * KTreducer #' KTreducer can be greater than 1
    if Ktprop > 1:    
        Ktprop = 1
    Tei = kc_mult * ks * foo.kcb * foo_day.ETref * Ktprop #' this had a few in equation as compared to Allen et al., 2005, ASCE

    # For precip wetted fraction beyond that irrigated
    KTreducer = fewp * (1 - foo.Dep / tew2use) / KTreducerdenom #' fewp added, 8/2006, that is not in Allen et al., 2005, ASCE
    Ktprop = Ktprop * KTreducer #' KTreducer can be greater than 1
    if Ktprop > 1:     
        Ktprop = 1
    Tep = kc_mult * ks * foo.kcb * foo_day.ETref * Ktprop #' this had a fewp in equation as compared to Allen et al., 2005, ASCE

    # Setup for water balance of evaporation layer
    Delast = foo.De
    Deplast = foo.Dep

    # if total profile is bone dry from a dry down, then any root
    # extraction from a rain or light watering may all come from the
    # evaporating layer.  Therefore, actCount for transpiration extraction
    # of water from Ze layer that will increase depletion of that layer

    # Available water in Zr includes water in Ze layer.  Therefore limit De.
    AvailWatinTotalZr = TAW - foo.Dr

    #' leave following out, for noncrop situations
    #' IF Delast + Deplast < TEW - AvailWatinTotalZr THEN
    #'   Delast = TEW - AvailWatinTotalZr #'soil is very dry
    #'  Deplast = TEW
    #' END IF

    #' finish water balance of Ze evaporation layer
    #' (Pinf, irr and DPe were subtracted or added earlier)

    foo.De = Delast + Ei / few + Tei
    OUT.debug('3ComputeCropET():de De %s\n' % (foo.De))

    # This next section modified 2/21/08 to keep a days potential E from exceeding 
    # Evaporable water available (for coarse soils).  Allen and Huntington
    if foo.De < 0:   
        foo.De = 0.0
        OUT.debug('3ComputeCropET():df De %s\n' % (foo.De))
    if foo.De > foo.TEW:    #' use TEW here rather than TEW2use to allow De to remain at TEW #'''  probably not.  if Delast <= 0:    Delast = 0
        potentialE = foo.De - Delast
        if potentialE < 0.0001:    
            potentialE = 0.0001
        Efactor = 1 - (foo.De - foo.TEW) / potentialE
        if Efactor < 0:    
            Efactor = 0.0
        if Efactor > 1:    
            Efactor = 1
        Ei = Ei * Efactor
        Tei = Tei * Efactor
        foo.De = Delast + Ei / few + Tei #' recalculate
        OUT.debug('3ComputeCropET():dg De %s\n' % (foo.De))
        if foo.De > foo.TEW + 0.2:   
            #PrintLine(lfNum, "Problem in keeping De water balance within TEW.  De, TEW,Ei, Tei,Efactor = " & Chr(9) & De & Chr(9) & TEW & Chr(9) & Ei & Chr(9) & Tei & Chr(9) & Efactor)
            print "Problem in keeping De water balance within TEW.  De, TEW,Ei, Tei,Efactor = ", De, TEW, Ei, Tei, Efactor
            return

    foo.Dep = Deplast + Ep / fewp + Tep
    if foo.Dep < 0:    
        foo.Dep = 0.0

    if foo.Dep > foo.TEW:   
        #'Dep = TEW

        potentialE = foo.Dep - Deplast
        if potentialE < 0.0001:    
            potentialE = 0.0001
        Efactor = 1 - (foo.Dep - foo.TEW) / potentialE
        if Efactor < 0:    
            Efactor = 0.0
        if Efactor > 1:    
            Efactor = 1
        Ep = Ep * Efactor
        Tep = Tep * Efactor
        foo.Dep = Deplast + Ep / fewp + Tep #' recalculate
        if foo.Dep > foo.TEW + 0.2:   
            #PrintLine(lfNum, "Problem in keeping De water balance within TEW.  De, TEW,Ei, Tei,Efactor = " & Chr(9) & De & Chr(9) & TEW & Chr(9) & Ei & Chr(9) & Tei & Chr(9) & Efactor)
            #if not batchFlag:    MsgBox("Problem in keeping De water balance within TEW.  De, TEW,Ei, Tei,Efactor = " & Chr(9) & De & Chr(9) & TEW & Chr(9) & Ei & Chr(9) & Tei & Chr(9) & Efactor)
            #Exit Function
            print "Problem in keeping De water balance within TEW.  De, TEW,Ei, Tei,Efactor = ..."
            return


    # Recomputed these based on corrections above if De > TEW  2/21/08
    etref_divisor = foo_day.ETref
    if etref_divisor < 0.01:    
        etref_divisor = 0.01
    kei = Ei / etref_divisor
    kep = Ep / etref_divisor
    if kei > 1.5:    
        kei = 1.5 #' limit for when ETref is super small
    if kep > 1.5:    
        kep = 1.5
    if kei < 0:    
        kei = 0.0
    if kep < 0:    
        kep = 0.0
    ke = kei + kep
    E = ke * foo_day.ETref
    if kc_mult > 1:   
        #PrintLine(lfNum, "kcmult > 1.")
        #if not batchFlag:    MsgBox("kcmult > 1.")
        #Exit Function
        print "kcmult > 1."
        return

    if ks > 1:   
        #PrintLine(lfNum, "ks > 1.")
        #if not batchFlag:    MsgBox("ks > 1.")
        #Exit Function
        print "ks > 1."
        return

    kc_act = kc_mult * ks * foo.kcb + ke
    foo.etc_act = kc_act * foo_day.ETref #' note that ETcact will be checked later against Dr and TAW
    kc_pot = foo.kcb + ke

    #' ETref is defined (to ETo or ETr) in CropCycle sub'Allen 12/26/2007

    foo.etc_pot = kc_pot * foo_day.ETref
    foo.etc_bas = foo.kcb * foo_day.ETref

    #' accumulate evaporation following each irrigation event. Subtract evaporation from precipitation.
    #' Precipitation evaporation is set to evaporation that would have occurred
    #' from precipitation in absence of irrigation, and is estimated as infiltrated P less deep percolation of P from
    #' evaporation layer for P only (if no irrigation).
    #' this was moved about 40 lines down 2/21/08 to be after adjustment to Ke, E, etc. made just above here.

    foo.cummevap1 = foo.cummevap1 + Ei - (foo.Pinf - Dpep)
    if foo.cummevap1 < 0:
        foo.cummevap1 = 0.0

    #' get irrigation information

    #' this is done after computation of Ke, since it is assumed that
    #' irrigations occur in pm of day, on average.
    #' this can / should be changed (moved ahead of Ke computation) for
    #' special/manual irrigations that are known to occur in am

    #' Ireal is a real irrigation experienced and read in
    #' Imanual is a manually specified irrigation from an array
    #' Ispecial is a special irrigation for leaching or germination
    #' for now, Ireal and Imanual are place holders (zero)
    #' Ispecial is determined from crop data read in

    #' water balance for Zr root zone (includes Ze layer)
    #' Initial calculation for Dr

    s = '3ComputeCropET():i Dr %s  ETcact %s  Pinf %s  Ireal %s  Imanual %s  Ispecial %s\n'
    t = (foo.Dr, foo.etc_act, foo.Pinf, Ireal, Imanual, Ispecial)
    OUT.debug(s % t)

    foo.Dr = foo.Dr + foo.etc_act - foo.Pinf - Ireal - Imanual - Ispecial

    # Ireal is a real irrigation experienced and read in
    # Imanual is a manually specified irrigation from an array
    # Ispecial is a special irrigation for leaching or germination

    # Determine if there is a need for an automatic irrigation
    Iyester = foo.simulated_irr
    foo.simulated_irr = 0.0
    if foo.irr_flag:   
        jd_to_start_irr = foo.jd_start_cycle + crop.days_after_planting_irrigation
        if jd_to_start_irr > 365:
            jd_to_start_irr = jd_to_start_irr - 365

        #' following code was added and changed to prevent winter irrigations of winter grain. dlk 08/15/2012

        crop_doy = foo_day.doy - foo.jd_start_cycle + 1
        if crop_doy < 1:
            crop_doy = crop_doy + 365
        if (crop_doy >= crop.days_after_planting_irrigation and
            foo_day.doy >= jd_to_start_irr):   
            if foo.in_season:   
                #' if JD <= JDendIrr:    #'no premature end for irrigations is used for Idaho CU comps.

                if foo.Dr > raw:    #' AD:   
                    #' limit irrigation to periods when Kcb > 0.22 to preclude frequent irrigation during initial periods

                    if foo.kcb > 0.22:   
                        foo.simulated_irr = foo.Dr
                        foo.simulated_irr = max(foo.simulated_irr, foo.irrigMin)
                        #if debugFlag and crop.crop_class_num = 7:   
                        #    PrintLine(lfNum, "Field corn irrigated- Date, Dr, RAW, Irr, DOY, JD to start Irr, Crop DOY" & Chr(9) & getDmiDate(dailyDates(sdays - 1)) & Chr(9) & Dr & Chr(9) & raw & Chr(9) & simulated_irr & Chr(9) & doy & Chr(9) & jd_to_start_irr & Chr(9) & crop_doy)

                        #if debugFlag and crop.crop_class_num = 13:   

    # Update Dr
    OUT.debug('3compute_crop_et():j Dr %s  simulated_irr %s\n' % (foo.Dr, foo.simulated_irr))
    foo.Dr = foo.Dr - foo.simulated_irr

    # Total irrigation for today
    foo.Iauto = foo.simulated_irr
    foo.simulated_irr = foo.simulated_irr + Ireal + Imanual + Ispecial
    if foo.simulated_irr > 0:   
        # Ready cummulative evaporation since last irrig for printing
        foo.cummevap = foo.cummevap1
        foo.cummevap1 = 0.0

    # Deep percolation from root zone
    #' evaluate irrigation and precip for today and yesterday to actCount
    #' for temporary water storage above field capacity
    #' don't allow deep perc on rainy day or if yesterday rainy if excess < 20 mm
    #' unless Zr < .2 m

    if (foo.simulated_irr + Iyester + foo.Pinf + foo.Pinfyest) <= 0.0001 or foo.Zr < 0.2:   
        if foo.Dr < 0.0:   
            foo.Dpr = -foo.Dr
        else:
            foo.Dpr = 0.0
    else:
        # Allow 20 mm above FC if watered today or yesterday
        if foo.Dr < -20:
            foo.Dpr = -20.0 - foo.Dr
        else:
            foo.Dpr = 0.0

    # Final update to Dr (depletion of root zone)
    OUT.debug('3ComputeCropET():k Dr %s  Dpr %s\n' % (foo.Dr, foo.Dpr))
    foo.Dr = foo.Dr + foo.Dpr

    #' 4/16/08.  if Dr > TAW, assume it is because we have overshot E+T on this day.

    #' 12/23/2011.  But don't do this if the stress flag is turned off!!  In that case, Dr
    #' may be computed (incidentally) as an increasing value since there is no irrigation, 
    #' but no stress either (i.e., wetlands, cottonwoods, etc.)  (Nuts!)

    OUT.debug('3ComputeCropET():l Dr %s  TAW %s  Invoke_Stress %s\n' % (foo.Dr, TAW, crop.invoke_stress))
    if crop.invoke_stress > 0.5:   
        if foo.Dr > TAW:   
            foo.etc_act = foo.etc_act - (foo.Dr - TAW) #' since we overshot, then just give remaining water to ETcact
            if foo.etc_act < 0.0:    
                foo.etc_act = 0.0

            #' calc new kc_act

            if foo_day.ETref > 0.1:    
                kc_act = foo.etc_act / foo_day.ETref
            foo.Dr = TAW #' limit depletion to total available water

    #' Update average Avail. Water in soil layer below current root depth
    #' and above maximum root depth.  Add gross deep percolation to it.  Assume
    #' a uniform soil texture.
    #' First, calculate a #'gross' deep percolation that includes 10% of irrigation depth
    #' as an incidental loss

    gDPr = foo.Dpr + 0.1 * foo.simulated_irr

    #' This moisture can recharge a dry profile
    #' from previous year and reduce need for irrigation.
    #' This is realistic, but make sure it does not reduce any #'NIR'

    #' Calc total water currently in layer 3.  AW3 is 0 first time through and calculated in next section

    DAW3 = foo.AW3 * (foo.Zrx - foo.Zr) #' AW3 is mm/m and DAW3 is mm in layer 3.  AW3 is layer between current root depth and max root
    TAW3 = foo.AW * (foo.Zrx - foo.Zr) #' TAW3 is potential mm in layer 3
    if DAW3 < 0:
        DAW3 = 0.0
    if TAW3 < 0:
        TAW3 = 0.0
    DAW3 = DAW3 + gDPr #' increase water in layer 3 for deep perc from root zone
    if DAW3 > TAW3:   
        foo.Dpr = DAW3 - TAW3
        DAW3 = TAW3 #' limit to FC
    else:
        foo.Dpr = 0 #' no deep perc from potential rootzone for crop (layer 3)

    if DAW3 < 0:
        DAW3 = 0.0
    if foo.Zrx > foo.Zr:   
        foo.AW3 = DAW3 / (foo.Zrx - foo.Zr) #' also defined in SetupDormant.  Check that Zrx does not get changed during ngs
    else:
        foo.AW3 = 0 #' no layer present, thus,AW3 is meaningless

    #' note, at end of season (harvest or death, AW3 and Zr need to be reset according
    #' to Dr at that time and Zr for dormant season.  This is done in Setupdormant.

    #' get setup for next time step.
    #' grow root

    if foo.in_season:    
        grow_root.grow_root(crop, foo, OUT)

"""
End if #' for non-water bodies ---- if crop.crop_class_num < 55 or crop.crop_class_num > 57:    #' <------ specific value for crop number
Return True

#Catch ex As Exception
#    if Not batchFlag:    MsgBox(Err.Description & " occurred computing ETc for ET Cell " & ETCellCount & " and crop " & crop.crop_class_num & ", " & cropn & ".")
#    PrintLine(lfNum, Err.Description & " occurred computing ETc for ET Cell " & ETCellCount & " and crop " & crop.crop_class_num & ", " & cropn & ".")
#    Return False
#End Try
#Function
"""
