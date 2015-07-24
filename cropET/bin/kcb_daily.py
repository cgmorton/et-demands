import datetime
import logging
import sys

import numpy as np

import open_water_evap

def kcb_daily(data, et_cell, crop, foo, foo_day):
    """Compute basal ET."""
    ##logging.debug('kcb_daily()')

    # Following two variables are used in one equation each but are never assigned a value - dlk - ?
    bcuttings = 0
    dcuttings = 0

    # Determine if inside or outside growing period
    # Procedure for deciding start and return false of season.
    curve_number = crop.curve_number

    # Determination of start of season was rearranged April 12 2009 by R.Allen
    # To correct computation error in limiting first and latest starts of season 
    #   that caused a complete loss of crop start turnon.

    # XXX Need to reset Realstart = false twice in Climate Sub.

    # Flag for estimating start of season 1 = cgdd, 2 = t30, 3 = date, 4 or 0 is on all the time
    logging.debug('kcb_daily(): Flag_for_means_to_estimate_pl_or_gu %s' % (
            crop.flag_for_means_to_estimate_pl_or_gu))
    logging.debug('kcb_daily(): Kcb %s  Kcb_yesterday %s' % (
        foo.kcb, foo.kcb_yesterday))

    #### Flag_for_means_to_estimate_pl_or_gu Case 1 #########
    #Select Case Flag_for_means_to_estimate_pl_or_gu(ctCount)
    #    Case 1
    if crop.flag_for_means_to_estimate_pl_or_gu == 1:
        # print 'in kcbDaily().CASE 1'
        #' cgdd

        # Only allow start flag to begin if < July 15 to prevent GU in fall after freezedown
        if foo_day.doy < (crop.gdd_trigger_doy  + 195):
            #' before finding date of startup using normal cgdd, determine if it is after latest
            #' allowable start by checking to see if pl or gu need to be constrained based on long term means
            #' estimate date based on long term mean:
            #' prohibit specifying start of season as long term less 40 days when it is before that date.
            
            foo_day.cgdd_0_lt[0] = foo_day.cgdd_0_lt[1]
            try:
                longterm_pl = int(np.where(np.diff(np.array(
                    foo_day.cgdd_0_lt > crop.t30_for_pl_or_gu_or_cgdd, 
                    dtype=np.int8)) > 0)[0]) + 1
            except TypeError:
                logging.error('  kcb_daily(): error finding DOY index')
                longterm_pl = 0
            ##for doy in range(1,367):
            ##    if (foo_day.cgdd_0_lt[doy] > crop.t30_for_pl_or_gu_or_cgdd and
            ##        foo_day.cgdd_0_lt[doy-1] < crop.t30_for_pl_or_gu_or_cgdd):
            ##        longterm_pl = doy
            ##        ## DEADBEEF - Stop after after a value is found?
            ##        ##break

            # Check if getting too late in season
            # Season hasn't started yet
            # was longterm_pl + 40 ----4/30/2009
            if (longterm_pl > 0 and
                foo_day.doy > (longterm_pl + 40) and
                not foo.real_start):      
                foo.doy_start_cycle = foo_day.doy 
                foo.real_start = True

            # Start of season has not yet been determined.  Look for it in normal fashion:
            if (not foo.real_start and
                foo.cgdd > crop.t30_for_pl_or_gu_or_cgdd):
                #' JH,RGA 4/13/09
                #' if cgdd > t30_for_pl_or_gu_or_cgdd(ctCount) And lcumGDD < t30_for_pl_or_gu_or_cgdd(ctCount) Then 'was until 4/13/09.  last part not needed now, with Realstart 'JH,RGA
                #' planting or GU is today

                #' This is modeled startup day, but check to see if it is too early
                #' use +/- 40 days from longterm as constraint
                if longterm_pl > 0 and foo_day.doy < (longterm_pl - 40):    
                    foo.real_start = False #' too early to start season
                    foo.doy_start_cycle = longterm_pl - 40
                    if foo.doy_start_cycle < 1:     
                        foo.doy_start_cycle += 365
                else:
                    foo.doy_start_cycle = foo_day.doy
                    foo.real_start = True

            # If season start has been found then turn parameters on
            # Look for day when DoY equals doy_start_cycle
            # Note that this requires that all days be present (no missing days)
            if foo_day.doy == foo.doy_start_cycle:    
                foo.real_start = True
                foo.stress_event = False #' reset severe stress event flag
                foo.in_season = True #' turn season on
                foo.dormant_setup_flag = True #' set set up flag positive for next end of season
                foo.setup_crop(crop) #' initialize rooting depth, etc. for crop
                foo.cycle = 1 #' first cycle for alfalfa

                # some range grasses require backing up 10 days
                # note that following logic will cause first 10 days to not be assigned to range grasses, but to winter cover
                # but this code needs to be here because process (or doy) can not go back in time
                if crop.date_of_pl_or_gu < 0.0:    
                    foo.doy_start_cycle = foo.doy_start_cycle + int(crop.date_of_pl_or_gu)
                    if foo.doy_start_cycle < 1:     
                        foo.doy_start_cycle += 365
            logging.debug(
                'kcb_daily(): InSeason %s  longterm_pl %s  doy %s  doy_start_cycle %s' %
                (foo.in_season, longterm_pl, foo_day.doy, foo.doy_start_cycle))
            logging.debug(
                'kcb_daily(): t30_for_pl_or_gu_or_cgdd %s' %
                (crop.t30_for_pl_or_gu_or_cgdd))
            logging.debug(
                'kcb_daily(): cumGDD0LT156 %.6f  cumGDD0LT155 %.6f' %
                (foo_day.cgdd_0_lt[156], foo_day.cgdd_0_lt[155]))

    #### Flag_for_means_to_estimate_pl_or_gu Case 2 ####
    elif crop.flag_for_means_to_estimate_pl_or_gu == 2:
        ## Use T30 for startup
        ## Caution - need some contraints for oscillating T30 and for late summer
        ## Use first occurrence
        if foo_day.doy < crop.gdd_trigger_doy  + 195:
            ## Only allow start flag to begin if < July 15 to prevent GU in fall after freezedown
            ##   before finding date of startup using normal T30, determine if it is after latest
            ##   allowable start by checking to see if pl or gu need to be constrained based on long term means
            ## Estimate date based on long term mean
            ## Prohibit specifying start of season as long term less
            ##   40 days when it is before that date.
            t30_lt = et_cell.climate['main_t30_lt']
            t30_lt[0] = t30_lt[1]
            try:
                longterm_pl = int(np.where(np.diff(np.array(
                    t30_lt > crop.t30_for_pl_or_gu_or_cgdd, 
                    dtype=np.int8)) > 0)[0]) + 1
            except TypeError:
                logging.error('  kcb_daily(): error finding DOY index')
                longterm_pl = 0
            ##longterm_pl = 0
            ##for jDoy in range(1,367):
            ##    if longterm_pl < 1:
            ##        ## line added 4/29/09 to keep from multiple longterm start dates.  duh.
            ##        if (t30_lt[jDoy] > crop.t30_for_pl_or_gu_or_cgdd and
            ##            t30_lt[jDoy-1] <= crop.t30_for_pl_or_gu_or_cgdd):
            ##            longterm_pl = jDoy
            logging.debug('kcb_daily(): longterm_pl %s  t30_lt(0) %s  t30_lt(1) %s' % (
                longterm_pl, t30_lt[0], t30_lt[1]))

            ## check if getting too late in season
            ##   and season hasn't started yet
            if (longterm_pl > 0 and
                foo_day.doy > longterm_pl+40 and
                not foo.real_start):
                ## longterm_pl + 40 'it is unseasonably warm (too warm).
                ## Delay start ' set to Doy on 4/29/09 (nuts)
                foo.doy_start_cycle = foo_day.doy 
                logging.debug('kcb_daily(): doy_start_cycle %s' % (
                    foo.doy_start_cycle))
                foo.real_start = True    #' Harleys Rule

            #' start of season has not yet been determined.  Look for it in normal fashion:
            if not foo.real_start:     
                if foo_day.t30 > crop.t30_for_pl_or_gu_or_cgdd:     #' 'JH,RGA 4/13/09
                    if longterm_pl > 0:    
                        if foo_day.doy < longterm_pl - 40:     #' use +/- 40 days from longterm as constraint
                            foo.real_start = False #' too early to start season
                            foo.doy_start_cycle = longterm_pl - 40
                            logging.debug('kcb_daily(): doy_start_cycle %s' % (
                                foo.doy_start_cycle))
                            if foo.doy_start_cycle < 1:     
                                foo.doy_start_cycle = foo.doy_start_cycle + 365
                                logging.debug('kcb_daily(): doy_start_cycle %s' % (
                                    foo.doy_start_cycle))
                        else:
                            foo.doy_start_cycle = foo_day.doy
                            logging.debug('kcb_daily(): doy_start_cycle %s' % (
                                foo.doy_start_cycle))
                            foo.real_start = True
                    else:
                        foo.doy_start_cycle = foo_day.doy
                        logging.debug('kcb_daily(): doy_start_cycle %s' % (
                            foo.doy_start_cycle))
                        foo.real_start = True

            ## If season start has been found then turn parameters on
            ##   look for day when DoY equals doy_start_cycle
            ## Note that this requires that all days be present (no missing days)
            if foo_day.doy == foo.doy_start_cycle:    
                foo.real_start = True
                ## Reset severe stress event flag
                foo.stress_event = False 
                ## Turn season on
                foo.in_season = True 
                ## Set setup flag positive for next end of season
                foo.dormant_setup_flag = True
                ## Initialize rooting depth, etc. for crop
                foo.setup_crop(crop)
                ## First cycle for alfalfa
                foo.cycle = 1 

                ## Some range grasses require backing up 10 days
                ## Note that following logic will cause first 10 days to not
                ##   be assigned to range grasses, but to winter cover
                ##   but this code needs to be here because process (or DoY)
                ##   can not go back in time
                if crop.date_of_pl_or_gu < 0.0:    
                    foo.doy_start_cycle = foo.doy_start_cycle + int(crop.date_of_pl_or_gu)
                    logging.debug('kcb_daily(): doy_start_cycle %s' % (
                        foo.doy_start_cycle))
                    if foo.doy_start_cycle < 1:     
                        foo.doy_start_cycle = foo.doy_start_cycle + 365
                        logging.debug('kcb_daily(): doy_start_cycle %s' % (
                            foo.doy_start_cycle))
            logging.debug(
                'kcb_daily(): doy_start_cycle %s  DoY %s  real_start %s' %
                (foo.doy_start_cycle, foo_day.doy, foo.real_start))
            logging.debug(
                'kcb_daily(): T30 %s  t30_for_pl_or_gu_or_cgdd %s  Date_of_pl_or_gu %s' %
                (foo_day.t30, crop.t30_for_pl_or_gu_or_cgdd, crop.date_of_pl_or_gu))
            logging.debug('kcb_daily(): InSeason %s' % (foo.in_season))

    #### Flag_for_means_to_estimate_pl_or_gu Case 3 ####
    elif crop.flag_for_means_to_estimate_pl_or_gu == 3:
        ## A date is used for planting or greenup
        month = int(crop.date_of_pl_or_gu)
        day = (crop.date_of_pl_or_gu - month) * 30.4
        if day < 0.5:     
            day = 15

        ## vb code (DateSerial) apparently resolves Mo=0 to 12
        if month == 0:
            month = 12
        doy = datetime.datetime(foo_day.year,month,day).timetuple().tm_yday

        ## Modified next statement to get winter grain to et and irrigate in first year of run.  dlk  08/16/2012
        if (foo_day.doy == doy or
            (foo_day.sdays == 1 and doy >= crop.gdd_trigger_doy )):    
            foo.doy_start_cycle = doy
            foo.in_season = True
            ## Reset severe stress event flag
            foo.stress_event = False
            foo.dormant_setup_flag = True
            ## Initialize rooting depth, etc. for crop
            foo.setup_crop(crop) 
        logging.debug('kcb_daily(): InSeason %s' % (foo.in_season))

    #### Flag_for_means_to_estimate_pl_or_gu Case 4 ####
    elif crop.flag_for_means_to_estimate_pl_or_gu == 4:
        foo.in_season = True
        ## Reset severe stress event flag if first
        if foo_day.doy == crop.gdd_trigger_doy :     
            foo.stress_event = False 
        foo.dormant_setup_flag = True 
        logging.debug('kcb_daily(): InSeason %s' % (foo.in_season))

    #### Case Else ####
    else:
        foo.in_season = True
        ## Reset severe stress event flag if first
        if foo_day.doy == crop.gdd_trigger_doy :     
            foo.stress_event = False
        foo.dormant_setup_flag = True
        logging.debug('kcb_daily(): InSeason %s' % (foo.in_season))
    #### END Case ####


    ## Set MAD to MADmid universally at the start.
    ## Value will be changed later.  R.Allen 12/14/2011
    foo.mad = foo.mad_mid  
    #### InSeason  ####
    if foo.in_season:     #' <------This kcb loop only conducted if inside growing season
        #' crop curve type: 1 = NcumGDD, 2 = %PL-EC, 3 = %PL-EC,daysafter, 4 = %PL-Term

        #### crop.curve_type Case 1 ####
        if crop.curve_type == 1:
            ## Normalized cumulative growing degree days
    
            if foo.doy_start_cycle == foo_day.doy:     
                foo.cgdd_at_planting = foo.cgdd
            cgdd_in_season = foo.cgdd - foo.cgdd_at_planting
            cgdd_in_season = max(0, cgdd_in_season)
            cgdd_efc = crop.cgdd_for_efc
            cgdd_term = crop.cgdd_for_termination
    
            #' increase cumGDD_term in SW Idaho to create longer late season
            #' use value of cropFlags, if greater than 1 as scaler
    
            ### This apparently does nothing, since crop_flags only either 0 or 1
            # skip for now
            #' <-------NOTE:  ONLY FUNCTIONAL FOR FLAG > 1.0, changed to >0, 1/2007
            #If cropFlags(ETCellCount, ctCount) > 0.001:     
            if et_cell.crop_flags[crop.class_number] > 0.001:
                #' <---- Jan 2007, invoke always to catch flag < or > 1
                cumGDD_term = cgdd_term * et_cell.crop_flags[crop.class_number] 
            #' cgdd_efc is not effected, only period following EFC
            logging.debug(
                'kcb_daily(): cropclass_num %s cropOneToggle %s cycle %s' %
                (crop.class_number, data.crop_one_flag, foo.cycle))

            #' special case for ALFALFA hay (typical, beef or dairy)  ' 4/09
            #If (ctCount = 1 and cropOneToggle = 1) or ctCount = 2 or ctCount = 3 or (ctCount > 3 and ccName.Equals("ALFALFA 1ST CYCLE")):     
            if ((crop.class_number == 1 and data.crop_one_flag) or
                crop.class_number == 2 or crop.class_number == 3 or
                (crop.class_number >= 4 and
                 crop.curve_name.upper() == "ALFALFA 1ST CYCLE")):
                cgdd_term = crop.cgdd_for_efc               #' termination for first cycle for alfalfa is in EFC cumGDD
                if foo.cycle > 1:                               #' termination for all other alfalfa cycles is stored in termination cumGDD.
                    cgdd_efc = crop.cgdd_for_termination    #' the 'term' cumGDD is for second cycles and on
                    cgdd_term = crop.cgdd_for_termination   #' CHECK to see if cumGDD should be incremented with cycle 3/08
                    if crop.class_number == 2:                             #' dairy hay.  Determine which of three kcb curves to use
                        #if foo.cycle < et_cell.dairyCuttings + 0.01 - 1:     #' this could be - 2 if at least one, and sometimes two final cycles are desired
                        if foo.cycle < dcuttings + 0.01 - 1:     #' this could be - 2 if at least one, and sometimes two final cycles are desired
                            curve_number = crop.curve_number + 1 #' increment alfalfa curve to intermediate cycle
                        else: #' R.Allen 4/1/08
                            curve_number = crop.curve_number + 2 #' increment alfalfa curve to fall/winter cycle
                        logging.debug(
                            'kcb_daily(): dairyCuttings %s  cycle %s  Crop_curve_number %s  curve_number %s' %
                            (dcuttings, foo.cycle, crop.curve_number, curve_number))

                    #' typical and beef hay.  Determine which of three kcb curves to use
                    if (crop.class_number == 1 or crop.class_number == 3 or
                        (crop.class_number >= 4 and
                         crop.curve_name.upper() == "ALFALFA 1ST CYCLE")):
                        #if foo.cycle < et_cell.beefCuttings + 0.01 - 1:     #' this could be - 2 if at least one, and sometimes two final cycles are desired
                        if foo.cycle < bcuttings + 0.01 - 1:     #' this could be - 2 if at least one, and sometimes two final cycles are desired
                            curve_number = crop.curve_number + 1 #' increment alfalfa curve to intermediate cycle
                        else:
                            curve_number = crop.curve_number + 2 #' increment alfalfa curve to fall/winter cycle
                        logging.debug(
                            'kcb_daily(): beefCuttings %s  cycle %s  Crop_curve_number %s  curve_number %s' %
                            (bcuttings, foo.cycle, crop.curve_number, curve_number))
    
                #' If ctCount = 2 and cycle > 3:     'dairy alfalfa 
                #'  curve_number = Crop_curve_number(ctCount) + 2  'end cycle (going into fall/winter)
                #' End If
                #' If ctCount = 3 and cycle > 2:     'beef alfalfa 
                #'  curve_number = Crop_curve_number(ctCount) + 2  'end cycle (going into fall/winter)
                #' End If
                #' Debug.Writeline "cycle, cgdd_efc, cumGDD_term, curve_number "; cycle, cgdd_efc, cumGDD_term, curve_number
                #' return false

            if cgdd_in_season < cgdd_efc:    
                foo.n_cgdd = cgdd_in_season / cgdd_efc
                int_cgdd = min(foo.max_lines_in_crop_curve_table - 1, int(foo.n_cgdd * 10))
                #kcb = cropco_val(curve_number, int_cgdd) + (foo.n_cgdd * 10 - int_cgdd) * (cropco_val(curve_number, int_cgdd + 1) - cropco_val(curve_number, int_cgdd))
                foo.kcb = (
                    et_cell.crop_coeffs[curve_number].data[int_cgdd] +
                    (foo.n_cgdd * 10 - int_cgdd) *
                    (et_cell.crop_coeffs[curve_number].data[int_cgdd+1] -
                     et_cell.crop_coeffs[curve_number].data[int_cgdd]))
                logging.debug(
                    'kcb_daily(): Kcb %.6f  ncumGDD %s  int_cgdd %s' %
                    (foo.kcb, foo.n_cgdd, int_cgdd))
                logging.debug(
                    'kcb_daily(): cgdd_in_season %s  cgdd_efc %s' %
                    (cgdd_in_season, cgdd_efc))
                logging.debug(
                    'kcb_daily(): cumGDD %.6f  cgdd_at_planting %.6f' %
                    (foo.cgdd, foo.cgdd_at_planting))
                ## Set management allowable depletion also
                foo.mad = foo.mad_ini
            else:
                if cgdd_in_season < cgdd_term:     #' function is same as for < EFC
                    foo.n_cgdd = cgdd_in_season / cgdd_efc #' use ratio of cumGDD for EFC
    
                    #' increase ncumGDD term in SW Idaho to stretch kcb curve during late season
                    #' use value of cropFlags, if greater than 1 as scaler
    
                    ## This apparently does nothing, since crop_flags only either 0 or 1
                    ## skip for now   
                    #If cropFlags(ETCellCount, ctCount) > 1:
                    #    #' reduce ncumGDD to make curve stretch longer
                    #    ncumGDD = ncumGDD / cropFlags(ETCellCount, ctCount) 
                    #End If
                    if foo.n_cgdd < 1:     
                        foo.n_cgdd = 1 #' keep from going back into dev. period
                    int_cgdd = min(foo.max_lines_in_crop_curve_table - 1, int(foo.n_cgdd * 10))
                    foo.mad = foo.mad_mid
                    lentry = et_cell.crop_coeffs[curve_number].lentry
                    #' more entries in kcb array
                    if int_cgdd < lentry:     
                        foo.kcb = (
                            et_cell.crop_coeffs[curve_number].data[int_cgdd] +
                            (foo.n_cgdd * 10 - int_cgdd) *
                            (et_cell.crop_coeffs[curve_number].data[int_cgdd+1] -
                             et_cell.crop_coeffs[curve_number].data[int_cgdd]))
                        logging.debug(
                            'kcb_daily(): Kcb %s  int_cgdd %s  curve_number %s  lentry %s' %
                            (foo.kcb, int_cgdd, curve_number, lentry))
                    else:
                        ## Hold kcb equal to last entry until either cumGDD 
                        ##   terminationis exceeded or killing frost
                        foo.kcb = et_cell.crop_coeffs[curve_number].data[lentry]
                        logging.debug(
                            'kcb_daily(): Kcb %s  int_cgdd %s  curve_number %s  lentry %s' %
                            (foo.kcb, int_cgdd, curve_number, lentry))
                else:
                    ## End of season by exceeding cumGDD for termination.
                    ## Set flag to 0

                    ## Note that for cumGDD based crops, there is no extension past computed end
                    foo.in_season = False 
                    logging.debug('kcb_daily(): InSeason0 %s' % (foo.in_season))
                    foo.stress_event = False
                    ## special case for ALFALFA   1 added 4/18/08
                    if (crop.class_number in [1,2,3] or
                        (crop.class_number >= 4 and
                         crop.curve_name.upper() == "ALFALFA 1ST CYCLE")):
                        ## (three curves for cycles, two cumGDD's for first and other cycles)
    
                        ## Remember gu, cutting and frost dates for alfalfa crops for review
                        foo.cutting[foo.cycle] = foo_day.doy
    
                        ## Increment and reset for next cycle
                        foo.cycle = foo.cycle + 1
                        foo.in_season = True
                        logging.debug('kcb_daily(): InSeason1 %s' % (foo.in_season))
                        ## set basis for next cycle
                        foo.cgdd_at_planting = foo.cgdd 
    
                        ## Following 2 lines added July 13, 2009 by RGA to reset
                        ##   alfalfa height to minimum each new cycle
                        foo.height = foo.height_min
    
                        #' and to set kcb to initial kcb value for first day following cutting.
    
                        #kcb = cropco_val(curve_number, 0)
                        foo.kcb = et_cell.crop_coeffs[curve_number].data[0]
                        logging.debug(
                            'kcb_daily(): Kcb %s  cgdd_at_planting %s' %
                            (foo.kcb, foo.cgdd_at_planting))

                ## First alfalfa crop (typical production alfalfa) where kcb is reduced   '4/18/08...
                if (crop.class_number == 1 and data.crop_one_flag):
                    #' xxx...apply only if cropOneToggle is set (4/09)
                    foo.kcb = foo.kcb * data.crop_one_reducer 
                    logging.debug('kcb_daily(): Kcb %s' % foo.kcb)
            ## Use this here only to invoke a total length limit
            days_into_season = float(foo_day.doy - foo.doy_start_cycle + 1) 
            if days_into_season < 1:    
                days_into_season += 365

            ## Real value for length constraint (used for spring grain)
            ## The cumGDD basis has exceeded length constraint.
            if (crop.time_for_harvest > 10 and
                days_into_season > crop.time_for_harvest):     
                ## End season
                foo.in_season = False #' This section added Jan. 2007
                logging.debug('kcb_daily(): InSeason2 %s' % (foo.in_season))
                foo.stress_event = False


        #### crop.curve_type Case 2 ####
        elif crop.curve_type == 2:
            ## Percent of time from PL to EFC for all season
            days_into_season = float(foo_day.doy - foo.doy_start_cycle + 1)
            if days_into_season < 1:     
                days_into_season = days_into_season + 365
            ## Deal with values of zero or null - added Dec. 29, 2011, rga
            if crop.time_for_efc < 1:
                crop.time_for_efc = 1 
            foo.n_pl_ec = days_into_season / crop.time_for_efc
            npl_ec100 = foo.n_pl_ec * 100
            if foo.n_pl_ec < 1:    
                foo.mad = foo.mad_ini
            else:
                foo.mad = foo.mad_mid
    
            ## In next line, make sure that "System.Math.Abs()" does not change
            ##   exact value for time_for_harvest() and that it is taking absolute value.
            ## Use absolute value for time_for_harvest since neg means to run
            ##   until frost (Jan. 2007). also changed to <= from <
            logging.debug(
                'kcb_daily(): npl_ec100 %s  time_for_harvest %s abs_time_for_harvest %s' %
                (npl_ec100, crop.time_for_harvest, abs(crop.time_for_harvest)))
            #if npl_ec100 <= abs(crop.time_for_harvest):    
            if round(npl_ec100,4) <= abs(crop.time_for_harvest):    
                logging.debug(
                    'kcb_daily(): n_pl_ec0 %s  max_lines_in_crop_curve_table %s' %
                    (foo.n_pl_ec, foo.max_lines_in_crop_curve_table))
                int_pl_ec = min(foo.max_lines_in_crop_curve_table - 1., int(foo.n_pl_ec * 10.))
                foo.kcb = (
                    et_cell.crop_coeffs[curve_number].data[int_pl_ec] +
                    (foo.n_pl_ec * 10 - int_pl_ec) *
                    (et_cell.crop_coeffs[curve_number].data[int_pl_ec+1] -
                     et_cell.crop_coeffs[curve_number].data[int_pl_ec]))
                logging.debug(
                    'kcb_daily():6 Kcb %s  int_pl_ec %s  n_pl_ec %s' %
                    (foo.kcb, int_pl_ec, foo.n_pl_ec))
                logging.debug(
                    'kcb_daily():6 days_into_season %s  time_for_EFC %s' %
                    ( days_into_season, crop.time_for_efc))
            else:
                #' beyond stated end of season
                #' ------need provision to extend until frost termination if indicated for crop -- added Jan. 2007
    
                if crop.time_for_harvest < -0.5:     #' negative value is a flag to extend until frost
                    #' XXXXXXXXX  Need to set to yesterday's kcb for a standard climate
    
                    #' use yesterday's kcb which should trace back to last valid day of stated growing season
                    foo.kcb = foo.kcb_yesterday
                    logging.debug('kcb_daily(): Kcb %s' % foo.kcb)
                else:
                    foo.in_season = False
                    foo.stress_event = False #' reset severe stress event flag
                    logging.debug('kcb_daily(): InSeason3 %s' % (foo.in_season))


        #### crop.curve_type Case 3 ####
        elif crop.curve_type == 3:
            ## Percent of time from PL to EFC for before EFC and days after EFC after EFC
            days_into_season = float(foo_day.doy - foo.doy_start_cycle + 1)
            if days_into_season < 1:     
                days_into_season += 365
            if crop.time_for_efc < 1:     
                crop.time_for_efc = 1 #' deal with values of zero or null - added Dec. 29, 2011, rga
            foo.n_pl_ec = days_into_season / crop.time_for_efc
            if foo.n_pl_ec < 1:    
                int_pl_ec = min(foo.max_lines_in_crop_curve_table - 1, int(foo.n_pl_ec * 10.))
                #kcb = cropco_val(curve_number, int_pl_ec) + (n_pl_ec * 10 - int_pl_ec) _
                #    * (cropco_val(curve_number, int_pl_ec + 1) - cropco_val(curve_number, int_pl_ec))
                foo.kcb = (
                    et_cell.crop_coeffs[curve_number].data[int_pl_ec] +
                    (foo.n_pl_ec * 10 - int_pl_ec) *
                    (et_cell.crop_coeffs[curve_number].data[int_pl_ec+1] -
                     et_cell.crop_coeffs[curve_number].data[int_pl_ec]))
                logging.debug('kcb_daily(): Kcb %s  n_pl_ec %s  max_lines_in_crop_curve_table %s  int_pl_ec %s' % (
                    foo.kcb, foo.n_pl_ec, foo.max_lines_in_crop_curve_table, int_pl_ec))
                foo.mad = foo.mad_ini
            else:
                foo.mad = foo.mad_mid
                DaysafterEFC = days_into_season - crop.time_for_efc
    
                ## In next line, make sure that "System.Math.Abs()" does not
                ##   change exact value for time_for_harvest() and that it is
                ##   taking absolute value.
                ## Use absolute value for time_for_harvest since neg means to
                ##   run until frost (Jan. 2007). also changed to <= from <
                if DaysafterEFC <= abs(crop.time_for_harvest):
                    ## Start at array index = 11 for 0 days into full cover
                    nDaysafterEFC = DaysafterEFC / 10 + 11 
                    int_pl_ec = min(foo.max_lines_in_crop_curve_table - 1, int(nDaysafterEFC))
                    foo.kcb = (
                        et_cell.crop_coeffs[curve_number].data[int_pl_ec] +
                        (nDaysafterEFC - int_pl_ec) *
                        (et_cell.crop_coeffs[curve_number].data[int_pl_ec+1] -
                         et_cell.crop_coeffs[curve_number].data[int_pl_ec]))
                    logging.debug('kcb_daily(): Kcb %s' % foo.kcb)
                else:
                    #' beyond stated end of season
                    #' ------need provision to extend until frost termination if indicated for crop -- added Jan. 2007

                    #' negative value is a flag to extend until frost -- added Jan. 2007
                    if crop.time_for_harvest < -0.5:     
    
                        #' XXXX need to set to yesterday's standard climate kcb
                        #' use yesterday's kcb which should trace back to last valid day of stated growing season
                        foo.kcb = foo.kcb_yesterday 
                        logging.debug('kcb_daily(): Kcb %s' % foo.kcb)
                    else:
                        foo.in_season = False
                        foo.stress_event = False #' reset severe stress event flag
                        logging.debug('kcb_daily(): InSeason4 %s' % (foo.in_season))


        #### crop.curve_type Case 4 ####
        elif crop.curve_type == 4:
            ## Percent of time from PL to end of season
            ## Note that type 4 kcb curve uses T30 to estimate GU
            ##   and symmetry around July 15 to estimate total season length.
    
            ## Estimate end of season
            if foo.doy_start_cycle < (crop.gdd_trigger_doy  + 195):
                ## CGM - end_of_season is not used anywhere else?
                ##end_of_season = (
                ##    crop.gdd_trigger_doy  + 195 +
                ##    (crop.gdd_trigger_doy  + 195 - foo.doy_start_cycle))
                length_of_season = 2 * (crop.gdd_trigger_doy  + 195 - foo.doy_start_cycle)
                #' end_of_season = 196 + (196 - foo.doy_start_cycle)
                #' length_of_season = 2 * (196 - foo.doy_start_cycle)
            else:
                logging.error(
                    "Problem with estimated Season length, Crop_curve_type_4")
                raise SystemExit()
                ##sys.exit()
    
            ## Put a minimum and maximum length on season for cheat grass (i= 47)
            ## Was 38, should have been 42   'corr. Jan 07
            if crop.class_number == 47:    
                length_of_season = max(length_of_season, 60)
                if length_of_season > 90:
                    length_of_season = 100

            days_into_season = float(foo_day.doy - foo.doy_start_cycle)
            if days_into_season < 1:     
                days_into_season += 365
            foo.n_pl_ec = days_into_season / length_of_season
            ## Assume season is split 50/50 for stress sensitivities for type 4
            if foo.n_pl_ec < 0.5:     
                foo.mad = foo.mad_ini
            else:
                foo.mad = foo.mad_mid

            if foo.n_pl_ec <= 1:    
                int_pl_ec = min(
                    foo.max_lines_in_crop_curve_table - 1, int(foo.n_pl_ec * 10))
                foo.kcb = (
                    cropco_val(curve_number, int_pl_ec) +
                    (foo.n_pl_ec * 10 - int_pl_ec) *
                    (cropco_val(curve_number, int_pl_ec + 1) -
                     cropco_val(curve_number, int_pl_ec)))
                logging.debug('kcb_daily(): Kcb %s' % foo.kcb)
            else:
                ## Beyond end of season
                foo.in_season = False
                foo.stress_event = False #' reset severe stress event flag
                logging.debug('kcb_daily(): InSeason5 %s' % (foo.in_season))



        ## Following is discounting for cold shock to alfalfa gets reset on Jan 1
        ##' check for -2C or -3C temperature for peak alfalfa curve to begin discount
        ## discount kcb .01 or .005 per day since first occurrence of -2 C or -3 C in fall.

        ## Peak alfalfa curve and both alfalfa crops (apply to all)(i=1,2,3) 
        if (crop.class_number < 4 or
            (crop.class_number > 3 and
             crop.curve_name.upper() == "ALFALFA 1ST CYCLE")):     
            if foo_day.doy > (crop.gdd_trigger_doy  + 211):    
                ## First occurrence of -3C (was -2, now -3)
                if foo_day.tmin < -3 and foo.T2Days < 1:     
                    foo.T2Days = 1
            else:
                foo.T2Days = 0 ## Reset discount timer if prior to August
            if foo.T2Days > 0:    
                foo.kcb -= foo.T2Days * 0.005 #'  was 0.01
                logging.debug('kcb_daily(): Kcb %s' % foo.kcb)
                if foo.kcb < 0.1:     
                    foo.kcb = 0.1
                    logging.debug('kcb_daily(): Kcb %s' % foo.kcb)
                foo.T2Days = foo.T2Days + 1

        ## Determine if killing frost to cut short - begin to check after August 1.   
        if foo_day.doy > (crop.gdd_trigger_doy  + 211):    
            ## All crops besides covers
            if ((foo_day.tmin < crop.killing_frost_temperature) and
                (crop.class_number < 44 or crop.class_number > 46) and
                foo.in_season):    
                logging.info(
                    "Killing frost for crop %s of %s was found on DOY %s of %s" %
                    (crop.class_number, crop.killing_frost_temperature,
                     foo_day.doy, foo_day.year))
                foo.in_season = False
                foo.stress_event = False
                logging.debug('kcb_daily(): in_season6 %s' % (foo.in_season))

                ## DEADBEEF - This is not currently implemented
                ### Print cutting information to a review file if alfalfa hay for select stations
                ##if crop.class_number == 2:     
                ##    output_str = ""
                ##    #output_str = output_str & DFormat(RefETIDs(ETCellCount), " #########") & DFormat(year, "  ####") & DFormat(doy_start_cycle, " ###")
                ##    #For cutCount = 1 To 10
                ##    for cutCount in range(1,11):
                ##        foo.cutting[cutCount] = 0
                ##    #output_str = output_str & DFormat(DoY, " #####")
                ##    #PrintLine(cd2FNum, output_str)
                ##elif (crop.class_number == 3 or
                ##    (crop.class_number > 3 and
                ##     crop.curve_name.upper() == "ALFALFA 1ST CYCLE")):     
                ##    output_str = ""
                ##    #output_str = output_str & DFormat(RefETIDs(ETCellCount), " #########") & DFormat(year, "  ####") & DFormat(doy_start_cycle, " ###")
                ##    #For cutCount = 1 To 10
                ##    #    foo.cutting(cutCount) = 0
                ##    #Next cutCount
                ##    #output_str = output_str & DFormat(DoY, " #####")
                ##    #PrintLine(cb2FNum, output_str)

            ## End of year, no killing frost on alfalfa
            elif (((crop.class_number == 2 or crop.class_number == 3) or
                   (crop.class_number > 3 and 
                   crop.curve_name.upper() == "ALFALFA 1ST CYCLE")) and
                  foo.in_season and foo_day.month == 12 and foo_day.day == 31):     
                logging.info("No killing frost in year %s" % (foo_day.year))

                ## DEADBEEF - Not currently implemented
                ###' print cutting information to a review file if alfalfa hay for select stations
                ##if crop.class_number == 2:     
                ##    output_str = ""
                ##    #output_str = output_str & DFormat(RefETIDs(ETCellCount), " #########") & DFormat(year, "  ####") & DFormat(doy_start_cycle, " ###")
                ##    #For cutCount = 1 To 10
                ##    #    output_str = output_str & DFormat(cutting(cutCount), " ####")
                ##    #    foo.cutting[cutCount] = 0
                ##    #output_str = output_str & DFormat(DoY, " #####")
                ##    #PrintLine(cd2FNum, output_str)
                ##elif (crop.class_number > 2 and
                ##    crop.curve_name.upper() == "ALFALFA 1ST CYCLE"):
                ##    output_str = ""
                ##    #output_str = output_str & DFormat(RefETIDs(ETCellCount), " #########") & DFormat(year, "  ####") & DFormat(doy_start_cycle, " ###")
                ##    #For cutCount = 1 To 10
                ##    #    output_str = output_str & DFormat(cutting(cutCount), " ####")
                ##    #    foo.cutting(cutCount) = 0
                ##    #Next
                ##    #output_str = output_str & DFormat(DoY, " #####")
                ##    #PrintLine(cb2FNum, output_str)

        ## This kcb is not adjusted for climate 'keep track of this for debugging
        kcb_noadj = foo.kcb

    ## Sub in winter time kcb if before or after season

    ## Kcb for winter time land use
    ##   44: Bare soil
    ##   45: Mulched soil, including grain stubble
    ##   46: Dormant turf/sod (winter time)
    ##   Note: set kc_max for winter time (Nov-Mar) and fc outside of this sub.
    if crop.class_number == 44:
        foo.kcb = 0.1 #' was 0.2
        foo.kcb_wscc[1] = foo.kcb #' remember this value to assign to regular crops, etc. during nonseason.
        logging.debug('kcb_daily(): Kcb %s' % foo.kcb)
    elif crop.class_number == 45:
        foo.kcb = 0.1 #' was 0.2
        foo.kcb_wscc[2] = foo.kcb
        logging.debug('kcb_daily(): Kcb %s' % foo.kcb)
    elif crop.class_number == 46:
        foo.kcb = 0.1 #' was 0.3
        foo.kcb_wscc[3] = foo.kcb
        logging.debug('kcb_daily(): Kcb %s' % foo.kcb)

    ## Open water evaporation "crops"
    ##   55: Open water shallow systems (large ponds, streams)
    ##   56: Open water deep systems (lakes, reservoirs)
    ##   57: Open water small stock ponds
    ##   This section for WATER only
    if crop.class_number in [55, 56, 57]:      
        if crop.class_number == 55:
            if data.refet_type > 0:     #' Allen 3/6/08
                foo.kcb = 0.6 #' for ETr basis
                logging.debug('kcb_daily(): Kcb %s' % foo.kcb)
            else:
                ## For ETo basis 'Allen 12/26/07....
                ## Note that these values are substantially different from FAO56
                foo.kcb = 1.05
                logging.debug('kcb_daily(): Kcb %s' % foo.kcb)
        elif crop.class_number == 56:
            ## This is a place holder, since an aerodynamic function is used
            foo.kcb = 0.3 
            foo.kcb = open_water_evap.open_water_evap(foo, foo_day)
            logging.debug('kcb_daily(): Kcb %s' % foo.kcb)
        elif crop.class_number == 57:
            if data.refet_type > 0:     #' Allen 3/6/08
                foo.kcb = 0.7 #' for ETr basis
                logging.debug('kcb_daily(): Kcb %s' % foo.kcb)
            else:
                foo.kcb = 0.85 #' for ETo basis 'Allen 12/26/07
                logging.debug('kcb_daily(): Kcb %s' % foo.kcb)
        ## Water has only 'kcb'
        foo.kc_act = foo.kcb 
        foo.kc_pot = foo.kcb
        ## ETr changed to ETref 12/26/2007
        foo.etc_act = foo.kc_act * foo_day.etref 
        foo.etc_pot = foo.kc_pot * foo_day.etref
        foo.etc_bas = foo.kcb * foo_day.etref
        ## Keep track of this for debugging
        kcb_noadj = foo.kcb 
    else:
        ## Added 12/26/07 to adjust kcb for ETo basis for climate
        ## Keep track of this for debugging '12/26/07
        kcb_noadj = foo.kcb 

    ## Save kcb value for use tomorrow in case curve needs to be extended until frost
    foo.kcb_yesterday = kcb_noadj

    ## Adjustment to kcb moved here 2/21/08 to catch when during growing season
    ## Limit crop height for numerical stability
    foo.height = max(foo.height, 0.05)

    ## RHmin and U2 are computed in Climate subroutine
    ## Allen 3/26/08
    if data.refet_type > 0:     
        ## ETr basis, therefore, no adjustment to kcb
        pass
    else:
        #' ******'12/26/07
        logging.debug(
            'kcb_daily(): Kcb0 %.6f  U2 %.6f  RHmin %.6f  Height %.6f' % 
            (foo.kcb, foo_day.u2, foo_day.rh_min, foo.height))
        foo.kcb = (
            foo.kcb + (0.04 * (foo_day.u2 - 2) - 0.004 * (foo_day.rh_min - 45)) *
            (foo.height / 3) ** 0.3) 
        logging.debug('kcb_daily(): Kcb %.6f' % (foo.kcb))

    ## Set up as yesterday's cumulative GDD for tomorrow
    foo.cgdd_prev = foo.cgdd
    
