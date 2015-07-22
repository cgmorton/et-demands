import datetime
import logging
import math
import sys

import compute_crop_gdd
import calculate_height
import grow_root
import kcb_daily
import runoff
import util

def compute_crop_et(t30, data, et_cell, crop, foo, foo_day):
    """crop et computations"""
    ##logging.debug('compute_crop_et()')

    #' determine if within a new growing period, etc.
    #' update 30 day mean air temperature (t30) and cumulative growing degree days (CGDD)
    #compute_crop_gdd()

    compute_crop_gdd.compute_crop_gdd(data, crop, foo, foo_day)
    logging.debug(
        'compute_crop_et():  jdStartCycle %s  CGDD %.6f  GDD %.6f  TMean %.6f' %
        (foo.doy_start_cycle, foo.cgdd, foo.gdd, foo_day.tmean))

    #' calculate height of vegetation.  Call was moved up to this point 12/26/07 for use in adj. Kcb and kc_max
    calculate_height.calculate_height(crop, foo)

    #' interpolate Kcb and make climate adjustment (for ETo basis)

    #If Not kcb_daily(t30):    Return False
    kcb_daily.kcb_daily(data, et_cell, crop, foo, foo_day)

    #' Jump to end if open water (crops numbers 55 through 57 are open water)

    #If crop.class_number < 55 or crop.class_number > 57:    #' <------ specific value for crop number
    ### return here if open water
    #logging.debug(type(crop.class_number), crop.class_number)
    if crop.class_number in [55,56,57]:
        return 

    #' Maximum Kc when soil is wet.  For grass reference, kc_max = 1.2 plus climatic adj.
    #' For alfalfa reference, kc_max = 1.0, with no climatic adj.
    #' kc_max is set to less than 1.0 during winter to account for effects of cold soil.

    #' ETo basis:  Switched over to this 12/2007 #' Allen and Huntington
    #' Note that u2 and rhmin were disabled when KcETr code was converted to ETr basis
    #' these have been reactivated 12/2007 by Allen, based on daily wind and TDew
    #' rhmin and u2 are computed in Climate subroutine called above

    foo.height = max(0.05, foo.height) #' m #'limit height for numerical stability
    if data.refet_type > 0:    #' edited by Allen, 6/8/09 to use kc_max from file if given
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
                (foo.height / 3) ** 0.3)
        else:
            kc_max = (
                1.2 + (0.04 * (foo_day.u2 - 2) - 0.004 * (foo_day.rhmin - 45)) *
                (foo.height / 3) ** 0.3)
        #' if yearOfCalcs < 1952:    PrintLine(lfNum, "ctcount, cropn, hcrop, crop_kc_max,RHMin,u2" & Chr(9) & getDmiDate(dailyDates(sdays - 1)) & Chr(9) & crop.class_number & ", " & cropn & Chr(9) & Hcrop & Chr(9) & crop_kc_max(ctCount) & Chr(9) & rhmin & Chr(9) & u2)

    #' if yearOfCalcs < 1952:    PrintLine(lfNum, "Initial kc_max" & Chr(9) & getDmiDate(dailyDates(sdays - 1)) & Chr(9) & kc_max)

    #' ETr basis:
    #' kc_max = 1#  #'for ETr ******************* #'commented out 12/2007

    #' assign fraction of ground covered for each of three nongrowing season cover types

    if crop.class_number == 44:    #' bare soil  #.  changed Jan. 2007 for add. crop cats.
        foo.fc = 0.0
    elif crop.class_number == 45:    #' Mulched soil, including grain stubble  #.
        foo.fc = 0.4
    elif crop.class_number == 46:    #' Dormant turf/sod (winter time)  #.
        foo.fc = 0.7 #' was 0.6

    # kc_max and foo.fc for wintertime land use (Nov-Mar)
    wscc = crop.winter_surface_cover_class

    # wscc = 1 bare, 2 mulch, 3 sod

    # Assume that winter time is constrained to Nov thru March in northern hemisphere
    if util.is_winter(data, foo_day):    
        # Bare soil
        if crop.class_number == 44:
            # Less soil heat in winter.
            if data.refet_type > 0:
                # For ETr (Allen 3/2008)
                kc_max = 0.9 
            else:
                # For ETo  (Allen 12/2007)
                kc_max = 1.1 
            foo.fc = 0.0
        # Mulched soil, including grain stubble
        elif crop.class_number == 45:
            if data.refet_type > 0:
                # For ETr (Allen 3/2008)
                kc_max = 0.85 
            else:
                # For ETo (0.85 * 1.2)  (Allen 12/2007)
                kc_max = 1.0  
            foo.fc = 0.4
        # Dormant turf/sod (winter time)
        elif crop.class_number == 46:
            if data.refet_type > 0:    
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
        if crop.class_number < 44 or crop.class_number > 46:

            if wscc == 1:    #' bare soil    #'note that these are ETr based.  Mult by 1.2 (plus adj?) for ETo base  *************
                #' foo.fc is calculated below
                if data.refet_type > 0:    #' Allen 3/08
                    kc_max = 0.9 #' for ETr
                else:
                    kc_max = 1.1 #' for ETo  #'Allen 12/2007 **********
            elif wscc == 2:    #' Mulched soil, including grain stubble
                if data.refet_type > 0:   
                    kc_max = 0.85 #' for ETr
                else:
                    kc_max = 1.0  #' for ETo (0.85 * 1.2)  #'Allen 12/2007 ************
            elif wscc == 3:    #' Dormant turf/sod (winter time)
                if data.refet_type > 0:   
                    kc_max = 0.8 #' for ETr
                else:
                    kc_max = 0.95 #' for ETo (0.8 * 1.2)  #'Allen 12/2007  **********

        #' if yearOfCalcs < 1952:    PrintLine(lfNum, "Winter kc_max" & Chr(9) & getDmiDate(dailyDates(sdays - 1)) & Chr(9) & kc_max & Chr(9) & "for wscc of " & wscc)

    #' added 2/21/08 to make sure that a winter cover class is used if during nongrowing season

    #' override Kcb assigned from KcbDaily if nongrowing season and not water
    if (not foo.in_season and
        (crop.class_number < 55 or crop.class_number > 57)):    
        logging.debug(
            'compute_crop_et(): Kcb %.6f  Kcb_wscc %s  wscc %s' % (
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

    # Use same value for both ETr or ETo bases.
    foo.kc_min = 0.1 

    # Estimate height of vegetation for estimating fraction of ground cover
    #   for evaporation and fraction of ground covered by vegetation
    if crop.class_number < 44 or crop.class_number > 46:
        if kc_max <= foo.kc_min:    
            kc_max = foo.kc_min + 0.001
        if foo.in_season:   
            if foo.kcb > foo.kc_min:   
                #' heightcalc  #'call to heightcalc was moved to top of this subroutine 12/26/07 by Allen
                foo.fc = ((foo.kcb - foo.kc_min) / (kc_max - foo.kc_min)) ** (1 + 0.5 * foo.height)
                # limit so that few > 0
                if foo.fc > 0.99:    
                    foo.fc = 0.99 
            else:
                foo.fc = 0.001
    logging.debug(
        'compute_crop_et(): kc_max %s  Kcmin %s  Kcb %s  InSeason %s' % (
        kc_max, foo.kc_min, foo.kcb, foo.in_season))


    # Estimate infiltrating precipitation
    # Yesterday's infiltration
    foo.ppt_inf_yest = foo.ppt_inf 
    foo.ppt_inf = 0.0
    foo.sro = 0.0
    if foo_day.precip > 0:   
        # Compute weighted depletion of surface from irr and precip areas
        foo.depl_surface = foo.wtirr * foo.de + (1 - foo.wtirr) * foo.dep
        runoff.runoff(foo, foo_day)
        foo.ppt_inf = foo_day.precip - foo.sro
        #if foo.sro > 0.01:   
            #' Debug.Writeline "P and SRO "; P; SRO
            #' return false
    logging.debug(
        ('compute_crop_et(): p_inf_yest %s  p_inf %.6f  SRO %s  precip %.6f') %
        (foo.ppt_inf_yest, foo.ppt_inf, foo.sro, foo_day.precip))
    logging.debug(
        ('compute_crop_et(): depl_surface %.6f  wtirr %.6f  de %.6f  dep %.6f') %
        (foo.depl_surface, foo.wtirr, foo.de, foo.dep))

    # Compare precipitation and irrigation to determine value for fw

    # At this point, irrigation depth, Irr is based on yesterday's irrigations
    # (irrig has not yet been updated)
    # Note: In Idaho CU computations, scheduling is assumed automated according to MAD
    # Following code contains capacity to specify manual and #'special' irrigations, but isn't used here

    # irr_real is a real irrigation experienced and read in
    # irr_manual is a manually specified irrigation from an array
    # irr_special is a special irrigation for leaching or germination
    irr_real = 0.0
    irr_manual = 0.0
    irr_special = 0.0

    # Update fw of irrigation if an irrigation yesterday
    if irr_real + foo.irr_auto > 0:
        foo.fwi = foo.fw_std
    elif irr_manual + irr_special > 0:   
        foo.fwi = foo.fw_spec

    #' find current water in fwi portion of ze layer

    ## [140820] changed the tests below to round(watinZe?,6) in both py/vb for consistency
    ## both versions tested values ~1e-15, which were being passed through
    ## and would happen inconsistently between py/vb versions
    watinZe = foo.tew - foo.de
    logging.debug('compute_crop_et(): TEW %.6f  De %.6f  watinZe %.6f' % (
        foo.tew, foo.de, watinZe))

    #if watinZe <= 0.:    
    if round(watinZe,6) <= 0.:    
        watinZe = 0.001
    if watinZe > foo.tew:    
        watinZe = foo.tew
    logging.debug('compute_crop_et(): TEW %.6f  De %.6f  watinZe %.6f' % (
        foo.tew, foo.de, watinZe))

    # Find current water in fwp portion of Ze layer
    # the use of 'fewp' (precip) fraction of surface
    watinZep = foo.tew - foo.dep #' follows Allen et al. 2005 (ASCE JIDE) extensions
    logging.debug('compute_crop_et(): TEW %.6f  Dep %.6f  watinZep %.6f' % (
        foo.tew, foo.dep, watinZep))
    #if watinZep <= 0.:    
    if round(watinZep,6) <= 0.:    
        watinZep = 0.001
    if watinZep > foo.tew:    
        watinZep = foo.tew
    logging.debug('compute_crop_et(): TEW %.6f  Dep %.6f  watinZep %.6f' % (
        foo.tew, foo.dep, watinZep))

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

    logging.debug(
        ('compute_crop_et(): fwi %s stn_whc %.6f  AW %.6f  TEW %.6f') %
        (foo.fwi, et_cell.stn_whc, foo.aw, foo.tew))
    logging.debug(
        ('compute_crop_et(): Dep %.6f  De %.6f  watinZe %.6f') %
        (foo.dep, foo.de, watinZe))
    logging.debug(
        ('compute_crop_et(): watinZep %.6f  fewp %s  totwatinZe %.6f') %
        (watinZep, fewp, foo.totwatinZe))

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
        dpe = foo.ppt_inf + foo.irr_simulated / foo.fwi - foo.de
    else:
        # De, irr from yesterday
        # fw changed to fwi 8/10/06
        dpe = foo.ppt_inf + foo.irr_simulated / 1 - foo.de

    if dpe < 0:
        dpe = 0.0
    # Dep from yesterday
    dpe_yest = foo.ppt_inf - foo.dep 
    if dpe_yest < 0:
        dpe_yest = 0.0

    #' Compute initial balance of Ze layer.  E and T from Ze layer
    #' will be added later.  De is depletion of Ze layer, mm
    #' Pinf is P that infiltrates
    #' This balance is here, since irr is yesterday's irrigation and
    #' it is assumed to be in morning before E and T for day have
    #' occurred.  It is assumed that P occurs earlier in morning.
    if foo.fwi > 0.0001:
        #' fw changed to fwi 8/10/06
        foo.de = foo.de - foo.ppt_inf - foo.irr_simulated / foo.fwi + dpe 
        logging.debug('compute_crop_et(): De %.6f' % (foo.de))
    else:
        #' fw changed to fwi 8/10/06
        foo.de = foo.de - foo.ppt_inf - foo.irr_simulated / 1 + dpe 
        logging.debug('compute_crop_et(): De %.6f' % (foo.de))

    if foo.de < 0:
        foo.de = 0.0
        logging.debug('compute_crop_et(): De %.6f' % (foo.de))
    if foo.de > foo.tew:
        # Use TEW rather than TEW2use to conserve De
        foo.de = foo.tew 
        logging.debug('compute_crop_et(): De %.6f' % (foo.de))

    # Update depletion of few beyond that wetted by irrigation
    foo.dep = foo.dep - foo.ppt_inf + dpe_yest
    if foo.dep < 0:    
        foo.dep = 0.0
    if foo.dep > foo.tew:    
        foo.dep = foo.tew

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

    if foo.tew3 < 0.1:    
        foo.kr2 = 0.0

    # De is depletion of evaporation layer, mm

    #' make sure De does not exceed Dr (depl. of root zone), since Dr includes De.
    #' IF De > Dr THEN De = Dr   #'this causes problems during offseason.  don't use

    # For portion of surface that has been wetted by irrigation and precipitation
    #   reduce TEW (and REW) during winter when ETr drops below 4 mm/day (FAO-56)

    tew2use = foo.tew2
    tew3use = foo.tew3 #' for stage 3 drying (cracking soils (not in Idaho))
    rew2use = foo.rew
    foo.etref_30 = max(0.1, foo.etref_30) #' mm/day  #'edited from ETr to ETref 12/26/2007
    if data.refet_type > 0:   
        etr_threshold = 4 #' for ETr basis
    else:
        etr_threshold = 5 #' for ETo basis #'added March 26, 2008 RGA

    # Use 30 day ETr, if less than 4 or 5 mm/d to reduce TEW
    if foo.etref_30 < etr_threshold:    
        tew2use = foo.tew2 * math.sqrt(foo.etref_30 / etr_threshold)
        tew3use = foo.tew3 * math.sqrt(foo.etref_30 / etr_threshold)
        if rew2use > 0.8 * tew2use:
            # Limit REW to 30% less than TEW
            # Was 0.7 until 4/16/08
            rew2use = 0.8 * tew2use 

    s = 'compute_crop_et(): TEW2 %.6f  ETref30 %.6f  etr_threshold %s'
    t = (foo.tew2, foo.etref_30, etr_threshold)
    logging.debug(s % t)

    if foo.de <= rew2use:   
        kr = 1
    else:
        if foo.de <= tew2use:   
            kr = foo.kr2 + (1 - foo.kr2) * (tew2use - foo.de) / (tew2use - rew2use)
        else:
            if tew3use > tew2use:    #' Stage 3 drying (cracking soils)
                kr = foo.kr2 * (tew3use - foo.de) / (tew3use - tew2use)
            else:
                kr = 0.0

    #' portion of surface that has been wetted by precipitation

    if foo.dep <= rew2use:   
        krp = 1
    else:
        if foo.dep <= tew2use:   
            krp = foo.kr2 + (1 - foo.kr2) * (tew2use - foo.dep) / (tew2use - rew2use)
        else:
            if tew3use > tew2use:    #' Stage 3 drying (cracking soils)
                krp = foo.kr2 * (tew3use - foo.dep) / (tew3use - tew2use)
            else:
                krp = 0.0

    #' evaporation coefficient Ke
    #' partition Ke into that from irrigation wetted and from precip wetted
    #' Kelimit = (few + fewp) * kc_max
    #' find weighting factor based on water in Ze layer in irrig. wetted and precip wetted

    #' following conditional added July 2006 for when denominator is zero

    if (few * watinZe + fewp * watinZep) > 0.0001:   
        foo.wtirr = few * watinZe / (few * watinZe + fewp * watinZep)
    else:
        foo.wtirr = few * watinZe
    foo.wtirr = min([max([foo.wtirr, 0]), 1])
    ##DEADBEEF
    ##if foo.wtirr < 0.:    
    ##    foo.wtirr = 0.
    ##if foo.wtirr > 1.:    
    ##    foo.wtirr = 1.
    logging.debug(
        ('compute_crop_et(): few %.6f  watinZe %.6f  fewp %s') %
        (few, watinZe, fewp))
    logging.debug(
        ('compute_crop_et(): watinZep %.6f  wtirr %.6f') %
        (watinZep, foo.wtirr))

    #' Ke = Kr * (kc_max - foo.kcb) #' this was generic for irr + precip
    #' IF Ke > few * kc_max THEN Ke = few * kc_max

    kei = kr * (kc_max - foo.kcb) * foo.wtirr

    # Limit to maximum rate per unit surface area

    if kei > few * kc_max:    
        kei = few * kc_max
    kep = krp * (kc_max - foo.kcb) * (1 - foo.wtirr)
    if kep > fewp * kc_max:    
        kep = fewp * kc_max
    if kei < 0:    
        kei = 0.0
    if kep < 0:    
        kep = 0.0
    ke = kei + kep

    # Transpiration coefficient for moisture stress
    taw = foo.aw * foo.zr
    if taw < 0.001:
        taw = 0.001
    # mad is set to mad_ini or mad_mid in kcb_daily sub.
    raw = foo.mad * taw / 100 

    # Remember to check reset of AD and RAW each new crop season.  #####
    # AD is allowable depletion
    if foo.dr > raw:   
        ks = (taw - foo.dr) / (taw - raw)
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
            foo.stress_event = True
        if foo.stress_event:   
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
        kc_mult = 1 - k_rad + (1 - albedo_snow) / (1 - albedo_soil) * k_rad
        # Was 0.9, reduced another 30% to account for latent heat of fusion of melting snow
        kc_mult = kc_mult * 0.7

    ke *= kc_mult
    kei *= kc_mult
    kep *= kc_mult

    # Don't reduce Kcb, since it may be held constant during nongrowing periods.
    # Make adjustment to kc_act
    kc_act = kc_mult * ks * foo.kcb + ke
    kc_pot = foo.kcb + ke
    
    #' if yearOfCalcs < 1952:    PrintLine(lfNum, "First kcbas, kcpot, kcact" & Chr(9) & getDmiDate(dailyDates(sdays - 1)) & Chr(9) & Kcb & Chr(9) & kc_pot & Chr(9) & kc_act)

    # ETref is defined (to ETo or ETr) in CropCycle sub #'Allen 12/26/2007
    foo.etc_act = kc_act * foo_day.etref
    foo.etc_pot = kc_pot * foo_day.etref
    foo.etc_bas = foo.kcb * foo_day.etref

    de_last = 0  ## Used below here

    logging.debug(
        ('compute_crop_et(): Kcmult %s  few %s  fewp %s  Kei %.6f  Kep %s') %
        (kc_mult, few, fewp, kei, kep))
    logging.debug(
        ('compute_crop_et(): Ks %s  Kr %.6f  krp %s  wtirr %.6f  De %.6f') %
        (ks, kr, krp, foo.wtirr, foo.de))
    logging.debug(
        ('compute_crop_et(): Delast %s  Dep %s  tew2use %.6f  rew2use %.6f') %
        (de_last, foo.dep, tew2use, rew2use))
    logging.debug(
        ('compute_crop_et(): ETref %.6f  RAW %.6f  Zr %s') %
        (foo_day.etref, raw, foo.zr))
    logging.debug(
        ('compute_crop_et(): Kcb %s  Kc_pot %.6f  Kc_act %.6f') %
        (foo.kcb, kc_pot, kc_act))
    logging.debug(
        ('compute_crop_et(): ETcbas %.6f  ETcpot %.6f  ETcact %.6f') %
        (foo.etc_bas, foo.etc_pot, foo.etc_act))
    logging.debug(
        ('compute_crop_et(): Dr %.6f  Pinf %.6f') %
        (foo.dr, foo.ppt_inf))

    e = ke * foo_day.etref
    ei = kei * foo_day.etref
    ep = kep * foo_day.etref

    # Begin Water balance of evaporation layer and root zone

    # Transpiration from Ze layer
    # transpiration proportioning

    ## TP ze never initialized, assume 0.0 value
    ## also used in SetupDormant(), but value set explicity...wonder if was meant to be global????
    ze = 0.0   # I added this line
    if ze < 0.0001:    
        ze = 0.0001
    if foo.zr < 0.0001:    
        foo.zr = 0.01
    kt_prop = (ze / foo.zr) ** 0.6
    if kt_prop > 1:    
        kt_prop = 1

    # Zr is root depth, m
    # Dr is depletion in root zone, mm
    # AW is available water for soil, mm/m

    # For irrigation wetted fraction
    kt_reducer_denom = 1 - foo.dr / taw
    if kt_reducer_denom < 0.001:    
        kt_reducer_denom = 0.001
    #' few added, 8/2006, that is not in Allen et al., 2005, ASCE
    kt_reducer = few * (1 - foo.de / tew2use) / kt_reducer_denom
    kt_prop = kt_prop * kt_reducer
    #' kt_reducer can be greater than 1
    kt_prop = min(kt_prop, 1)
    #' this had a few in equation as compared to Allen et al., 2005, ASCE
    tei = kc_mult * ks * foo.kcb * foo_day.etref * kt_prop

    # For precip wetted fraction beyond that irrigated
    #' fewp added, 8/2006, that is not in Allen et al., 2005, ASCE
    kt_reducer = fewp * (1 - foo.dep / tew2use) / kt_reducer_denom
    kt_prop = kt_prop * kt_reducer
    #' kt_reducer can be greater than 1
    kt_prop = min(kt_prop, 1)
    #' this had a fewp in equation as compared to Allen et al., 2005, ASCE
    tep = kc_mult * ks * foo.kcb * foo_day.etref * kt_prop

    # Setup for water balance of evaporation layer
    de_last = foo.de
    dep_last = foo.dep

    # if total profile is bone dry from a dry down, then any root
    # extraction from a rain or light watering may all come from the
    # evaporating layer.  Therefore, actCount for transpiration extraction
    # of water from Ze layer that will increase depletion of that layer

    # Available water in Zr includes water in Ze layer.  Therefore limit De.
    AvailWatinTotalZr = taw - foo.dr

    #' leave following out, for noncrop situations
    #' IF Delast + Deplast < TEW - AvailWatinTotalZr THEN
    #'   Delast = TEW - AvailWatinTotalZr #'soil is very dry
    #'  Deplast = TEW
    #' END IF

    #' finish water balance of Ze evaporation layer
    #' (Pinf, irr and DPe were subtracted or added earlier)

    foo.de = de_last + ei / few + tei
    logging.debug('compute_crop_et(): De %.6f' % (foo.de))

    # This next section modified 2/21/08 to keep a days potential E from exceeding 
    # Evaporable water available (for coarse soils).  Allen and Huntington
    if foo.de < 0:   
        foo.de = 0.0
        logging.debug('compute_crop_et(): De %.6f' % (foo.de))
    if foo.de > foo.tew:
        #' use tew here rather than tew2use to allow de to remain at tew #'''  probably not.  if Delast <= 0:    Delast = 0
        potential_e = foo.de - de_last
        if potential_e < 0.0001:    
            potential_e = 0.0001
        e_factor = 1 - (foo.de - foo.tew) / potential_e
        if e_factor < 0:    
            e_factor = 0.0
        if e_factor > 1:    
            e_factor = 1
        ei = ei * e_factor
        tei = tei * e_factor
        foo.de = de_last + ei / few + tei #' recalculate
        logging.debug('compute_crop_et(): De %.6f' % (foo.de))
        if foo.de > foo.tew + 0.2:   
            #PrintLine(lfNum, "Problem in keeping de water balance within tew.  de, tew, ei, tei, e_factor = " & Chr(9) & De & Chr(9) & TEW & Chr(9) & Ei & Chr(9) & tei & Chr(9) & e_factor)
            logging.warning(
                ('Problem in keeping De water balance within TEW.'+
                 'De, TEW, Ei, tei, e_factor = {} {} {} {} {}').format(
                     de, tew, ei, tei, e_factor))
            return

    foo.dep = dep_last + ep / fewp + tep
    if foo.dep < 0:    
        foo.dep = 0.0

    if foo.dep > foo.tew:   
        #'Dep = TEW

        potential_e = foo.dep - dep_last
        if potential_e < 0.0001:    
            potential_e = 0.0001
        e_factor = 1 - (foo.dep - foo.tew) / potential_e
        if e_factor < 0:    
            e_factor = 0.0
        if e_factor > 1:    
            e_factor = 1
        ep = ep * e_factor
        tep = tep * e_factor
        foo.dep = dep_last + ep / fewp + tep #' recalculate
        if foo.dep > foo.tew + 0.2:   
            #PrintLine(lfNum, "Problem in keeping De water balance within TEW.  De, TEW,Ei, tei,e_factor = " & Chr(9) & De & Chr(9) & TEW & Chr(9) & Ei & Chr(9) & tei & Chr(9) & e_factor)
            #if not batchFlag:    MsgBox("Problem in keeping De water balance within TEW.  De, TEW,Ei, tei,e_factor = " & Chr(9) & De & Chr(9) & TEW & Chr(9) & Ei & Chr(9) & tei & Chr(9) & e_factor)
            #Exit Function
            logging.warning(
                ('Problem in keeping De water balance within TEW.  '+
                 'De, TEW, Ei, tei, e_factor = {} {} {} {} {}').format(
                     de, tew, ei, tei, e_factor))
            return


    # Recomputed these based on corrections above if De > TEW  2/21/08
    etref_divisor = foo_day.etref
    if etref_divisor < 0.01:    
        etref_divisor = 0.01
    kei = ei / etref_divisor
    kep = ep / etref_divisor
    if kei > 1.5:    
        kei = 1.5 #' limit for when ETref is super small
    if kep > 1.5:    
        kep = 1.5
    if kei < 0:    
        kei = 0.0
    if kep < 0:    
        kep = 0.0
    ke = kei + kep
    e = ke * foo_day.etref
    if kc_mult > 1:   
        #PrintLine(lfNum, "kcmult > 1.")
        #if not batchFlag:    MsgBox("kcmult > 1.")
        #Exit Function
        logging.warning("kcmult > 1.")
        return

    if ks > 1:   
        #PrintLine(lfNum, "ks > 1.")
        #if not batchFlag:    MsgBox("ks > 1.")
        #Exit Function
        logging.warning("ks > 1.")
        return

    kc_act = kc_mult * ks * foo.kcb + ke
    foo.etc_act = kc_act * foo_day.etref
    # Note that etc_act will be checked later against Dr and TAW
    kc_pot = foo.kcb + ke

    # etref is defined (to eto or etr) in crop_cycle sub'Allen 12/26/2007

    foo.etc_pot = kc_pot * foo_day.etref
    foo.etc_bas = foo.kcb * foo_day.etref

    # Accumulate evaporation following each irrigation event.
    # Subtract evaporation from precipitation.
    # Precipitation evaporation is set to evaporation that would have occurred
    #   from precipitation in absence of irrigation, and is estimated as
    #   infiltrated P less deep percolation of P from evaporation layer for P
    #   only (if no irrigation).
    # This was moved about 40 lines down 2/21/08 to be after adjustment to Ke, E, etc. made just above here.
    foo.cummevap1 = foo.cummevap1 + ei - (foo.ppt_inf - dpe_yest)
    if foo.cummevap1 < 0:
        foo.cummevap1 = 0.0

    # Get irrigation information

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

    logging.debug(
        ('compute_crop_et(): Dr %.6f  etc_act %.6f  p_inf %.6f') %
        (foo.dr, foo.etc_act, foo.ppt_inf))
    logging.debug(
        ('compute_crop_et(): irr_real %s  irr_manual %s  irr_special %s') %
        (irr_real, irr_manual, irr_special))

    foo.dr = foo.dr + foo.etc_act - foo.ppt_inf - irr_real - irr_manual - irr_special

    # Ireal is a real irrigation experienced and read in
    # Imanual is a manually specified irrigation from an array
    # Ispecial is a special irrigation for leaching or germination

    # Determine if there is a need for an automatic irrigation
    irr_yester = foo.irr_simulated
    foo.irr_simulated = 0.0
    if foo.irr_flag:   
        doy_to_start_irr = foo.doy_start_cycle + crop.days_after_planting_irrigation
        if doy_to_start_irr > 365:
            doy_to_start_irr -= 365

        # Following code was added and changed to prevent winter irrigations of winter grain. dlk 08/15/2012
        crop_doy = foo_day.doy - foo.doy_start_cycle + 1
        if crop_doy < 1:
            crop_doy += 365
        if (crop_doy >= crop.days_after_planting_irrigation and
            foo_day.doy >= doy_to_start_irr and foo.in_season and
            foo.dr > raw and foo.kcb > 0.22):   
            # No premature end for irrigations is used for Idaho CU comps.
            # Limit irrigation to periods when Kcb > 0.22 to preclude
            #   frequent irrigation during initial periods
            foo.irr_simulated = foo.dr
            foo.irr_simulated = max(foo.irr_simulated, foo.irr_min)
            #if debugFlag and crop.class_number = 7:   
            #    PrintLine(lfNum, "Field corn irrigated- Date, Dr, RAW, Irr, DOY, JD to start Irr, Crop DOY" & Chr(9) & getDmiDate(dailyDates(sdays - 1)) & Chr(9) & Dr & Chr(9) & raw & Chr(9) & simulated_irr & Chr(9) & doy & Chr(9) & doy_to_start_irr & Chr(9) & crop_doy)

            #if debugFlag and crop.class_number = 13:   

    # Update Dr
    logging.debug(
        'compute_crop_et(): Dr %.6f  simulated_irr %s' %
        (foo.dr, foo.irr_simulated))
    foo.dr = foo.dr - foo.irr_simulated

    # Total irrigation for today
    foo.irr_auto = foo.irr_simulated
    foo.irr_simulated = foo.irr_simulated + irr_real + irr_manual + irr_special
    if foo.irr_simulated > 0:   
        # Ready cummulative evaporation since last irrig for printing
        foo.cummevap = foo.cummevap1
        foo.cummevap1 = 0.0

    # Deep percolation from root zone
    # Evaluate irrigation and precip for today and yesterday to actCount
    #   for temporary water storage above field capacity
    # Don't allow deep perc on rainy day or if yesterday rainy if excess < 20 mm
    #   unless zr < .2 m
    if ((foo.irr_simulated + irr_yester + foo.ppt_inf + foo.ppt_inf_yest) <= 0.0001 or
        foo.zr < 0.2):   
        if foo.dr < 0.0:   
            foo.dpr = -foo.dr
        else:
            foo.dpr = 0.0
    else:
        # Allow 20 mm above FC if watered today or yesterday
        if foo.dr < -20:
            foo.dpr = -20.0 - foo.dr
        else:
            foo.dpr = 0.0

    # Final update to dr (depletion of root zone)
    logging.debug('compute_crop_et(): Dr %.6f  Dpr %s' % (foo.dr, foo.dpr))
    foo.dr += foo.dpr

    # 4/16/08.  if dr > taw, assume it is because we have overshot E+T on this day.
    # 12/23/2011.  But don't do this if the stress flag is turned off!!
    # In that case, dr may be computed (incidentally) as an increasing value
    # since there is no irrigation, but no stress either
    # (i.e., wetlands, cottonwoods, etc.)  (Nuts!)
    logging.debug(
        'compute_crop_et(): Dr %.6f  TAW %.6f  Invoke_Stress %s' %
        (foo.dr, taw, crop.invoke_stress))
    if crop.invoke_stress > 0.5 and foo.dr > taw:
        # Since we overshot, then just give remaining water to etc_act
        foo.etc_act -= (foo.dr - taw)
        foo.etc_act = max(foo.etc_act, 0)

        # Calc new kc_act
        if foo_day.etref > 0.1:    
            kc_act = foo.etc_act / foo_day.etref
        # Limit depletion to total available water
        foo.dr = taw 

    # Update average Avail. Water in soil layer below current root depth
    #   and above maximum root depth.  Add gross deep percolation to it.
    # Assume a uniform soil texture.
    # First, calculate a #'gross' deep percolation that includes 10% of irrigation depth
    #   as an incidental loss
    gDPr = foo.dpr + 0.1 * foo.irr_simulated

    # This moisture can recharge a dry profile
    # from previous year and reduce need for irrigation.
    # This is realistic, but make sure it does not reduce any #'NIR'

    # Calc total water currently in layer 3.
    # aw3 is 0 first time through and calculated in next section

    # aw3 is mm/m and daw3 is mm in layer 3.
    # aw3 is layer between current root depth and max root
    daw3 = foo.aw3 * (foo.zrx - foo.zr)
    # taw3 is potential mm in layer 3
    taw3 = foo.aw * (foo.zrx - foo.zr)
    daw3 = max(daw3, 0)
    taw3 = max(taw3, 0)
    # Increase water in layer 3 for deep perc from root zone
    daw3 += gDPr
    if daw3 > taw3:   
        foo.dpr = daw3 - taw3
        # Limit to FC
        daw3 = taw3
    else:
        # No deep perc from potential rootzone for crop (layer 3)
        foo.Dpr = 0

    daw3 = max(daw3, 0)
    if foo.zrx > foo.zr:   
        # Also defined in setup_dormant.
        # Check that zrx does not get changed during ngs
        foo.aw3 = daw3 / (foo.zrx - foo.zr)
    else:
        # No layer present, thus, aw3 is meaningless
        foo.aw3 = 0

    # Note, at end of season (harvest or death), aw3 and zr need to be reset
    #   according to dr at that time and zr for dormant season.
    # This is done in setup_dormant().

    # Get setup for next time step.
    if foo.in_season:    
        grow_root.grow_root(crop, foo)
