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
        if foo_day.doy < (crop.crop_gdd_trigger_doy + 195):
            #' before finding date of startup using normal cgdd, determine if it is after latest
            #' allowable start by checking to see if pl or gu need to be constrained based on long term means
            #' estimate date based on long term mean:
            #' prohibit specifying start of season as long term less 40 days when it is before that date.
            
            foo_day.cgdd_0_lt[0] = foo_day.cgdd_0_lt[1]
            try:
                longterm_pl = int(np.diff(
                    foo_day.cgdd_0_lt >
                    crop.t30_for_pl_or_gu_or_cgdd).nonzero()[0]) + 1
            except:
                logging.error('Error finding DOY index')
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
            if (longterm_pl > 0 and foo_day.doy > longterm_pl + 40 and
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
                if longterm_pl > 0 and foo_day.doy < longterm_pl - 40:    
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

    #### Flag_for_means_to_estimate_pl_or_gu Case 2 #########
    #Case 2
    ####crop.flag_for_means_to_estimate_pl_or_gu = 2
    elif crop.flag_for_means_to_estimate_pl_or_gu == 2:
        #' Use T30 for startup
        #' Caution - need some contraints for oscillating T30 and for late summer
        #' Use first occurrence

        if foo_day.doy < crop.crop_gdd_trigger_doy + 195:
            #' Only allow start flag to begin if < July 15 to prevent GU in fall after freezedown
            #' before finding date of startup using normal T30, determine if it is after latest
            #' allowable start by checking to see if pl or gu need to be constrained based on long term means
            #' estimate date based on long term mean:
            #' prohibit specifying start of season as long term less 40 days when it is before that date.

            t30_lt = et_cell.climate['main_t30_lt']
            t30_lt[0] = t30_lt[1]
            longterm_pl = 0
            for jDoy in range(1,367):
                if longterm_pl < 1:
                    #' line added 4/29/09 to keep from multiple longterm start dates.  duh.
                    #if foo_day.t30LT[jDoy] > crop.t30_for_pl_or_gu_or_cgdd and foo_day.t30LT[jDoy-1] < crop.t30_for_pl_or_gu_or_cgdd:
                    if (t30_lt[jDoy] > crop.t30_for_pl_or_gu_or_cgdd and
                        t30_lt[jDoy-1] <= crop.t30_for_pl_or_gu_or_cgdd):
                        longterm_pl = jDoy
            logging.debug('kcb_daily(): longterm_pl %s  t30_lt(0) %s  t30_lt(1) %s' % (
                longterm_pl, t30_lt[0], t30_lt[1]))

            if longterm_pl > 0:
                #' check if getting too late in season
                if foo_day.doy > longterm_pl+40: 
                    #' season hasn't started yet
                    if not foo.real_start:        
                        #' longterm_pl + 40 'it is unseasonably warm (too warm). Delay start ' set to Doy on 4/29/09 (nuts)
                        foo.doy_start_cycle = foo_day.doy 
                        logging.debug('kcb_daily(): doy_start_cycle %s' % (
                            foo.doy_start_cycle))
                        foo.real_start = True    #' Harleys Rule
                        #PrintLine(lfNum, "exceeded 40 days past longterm T30 turnon")

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

            #' if season start has been found then turn parameters on
            #' Look for day when DoY equals doy_start_cycle
            #' Note that this requires that all days be present (no missing days)
            if foo_day.doy == foo.doy_start_cycle:    
                foo.real_start = True
                foo.stress_event = False #' reset severe stress event flag
                foo.in_season = True #' turn season on
                foo.dormant_setup_flag = True #' set set up flag positive for next end of season
                foo.setup_crop(crop) #' initialize rooting depth, etc. for crop
                foo.cycle = 1 #' first cycle for alfalfa

                #' some range grasses require backing up 10 days
                #' note that following logic will cause first 10 days to not be assigned to range grasses, but to winter cover
                #' but this code needs to be here because process (or DoY) can not go back in time

                if crop.date_of_pl_or_gu < 0.0:    
                    foo.doy_start_cycle = foo.doy_start_cycle + int(crop.date_of_pl_or_gu)
                    logging.debug('kcb_daily(): doy_start_cycle %s' % (
                        foo.doy_start_cycle))
                    if foo.doy_start_cycle < 1:     
                        foo.doy_start_cycle = foo.doy_start_cycle + 365
                        logging.debug('kcb_daily(): doy_start_cycle %s' % (
                            foo.doy_start_cycle))

            logging.debug('kcb_daily(): doy_start_cycle %s  DoY %s  real_start %s' % (
                foo.doy_start_cycle, foo_day.doy, foo.real_start))
            logging.debug('kcb_daily(): T30 %s  t30_for_pl_or_gu_or_cgdd %s  Date_of_pl_or_gu %s' % (
                foo_day.t30, crop.t30_for_pl_or_gu_or_cgdd, crop.date_of_pl_or_gu))
            logging.debug('kcb_daily(): InSeason %s' % (foo.in_season))
    
            # print 'in kcbDaily().CASE 2', crop.crop_gdd_trigger_doy, longterm_pl, foo.doy_start_cycle, foo_day.doy

    #### Flag_for_means_to_estimate_pl_or_gu Case 3 #########
    #Case 3
    ###crop.flag_for_means_to_estimate_pl_or_gu = 3
    elif crop.flag_for_means_to_estimate_pl_or_gu == 3:
        # print 'in kcbDaily().CASE 3'
        #' a date is used for planting or greenup

        month = int(crop.date_of_pl_or_gu)
        day = (crop.date_of_pl_or_gu - month) * 30.4
        if day < 0.5:     
            day = 15

        # print Mo, dayMo, crop.date_of_pl_or_gu 
        # vb code (DateSerial) apparently resolves Mo=0 to 12
        if month == 0:
            month = 12
        doy = datetime.datetime(foo_day.year,month,day).timetuple().tm_yday
        #logging.debug('kcb_daily():c3 Date_of_pl_or_gu %s  Mo %s  doy %s' % (crop.date_of_pl_or_gu, Mo, doy))

        #' modified next statement to get winter grain to et and irrigate in first year of run.  dlk  08/16/2012

        if (foo_day.doy == doy or
            (foo_day.sdays == 1 and doy >= crop.crop_gdd_trigger_doy)):    
            foo.doy_start_cycle = doy
            foo.stress_event = False #' reset severe stress event flag
            foo.in_season = True #' turn season on
            foo.dormant_setup_flag = True #' set set up flag positive for next end of season
            foo.setup_crop(crop) #' initialize rooting depth, etc. for crop

        logging.debug('kcb_daily(): InSeason %s' % (foo.in_season))
    #### Flag_for_means_to_estimate_pl_or_gu Case 4 #########
    #Case 4
    ####crop.flag_for_means_to_estimate_pl_or_gu = 4
    elif crop.flag_for_means_to_estimate_pl_or_gu == 4:
        # print 'in kcbDaily().CASE 4'
        #' flag = 4 or 0 ('crop' is on all time)

        foo.in_season = True #' turn season on
        if foo_day.doy == crop.crop_gdd_trigger_doy:     
            foo.stress_event = False #' reset severe stress event flag if first of year
        foo.dormant_setup_flag = True #' set set up flag positive for next end of season

        logging.debug('kcb_daily(): InSeason %s' % (foo.in_season))
    #Case Else
    else:
        # print 'in kcbDaily().CASE else'
        #' flag = 4 or 0 ('crop' is on all time)

        foo.in_season = True #' turn season on
        if foo_day.doy == crop.crop_gdd_trigger_doy:     
            foo.stress_event = False #' reset severe stress event flag if first of year
        foo.dormant_setup_flag = True #' set set up flag positive for next end of season

        logging.debug('kcb_daily(): InSeason %s' % (foo.in_season))
    #### END Case  ####



    foo.mad = foo.mad_mid  #' set MAD to MADmid universally at the start.  Value will be changed later.  R.Allen 12/14/2011
    #### InSeason  ####
    if foo.in_season:     #' <------This kcb loop only conducted if inside growing season
        #' crop curve type: 1 = NcumGDD, 2 = %PL-EC, 3 = %PL-EC,daysafter, 4 = %PL-Term

        #### crop.curve_type Case 1 ####
        #    Select Case Crop_curve_type(ctCount)
        if crop.curve_type == 1:
        #Case 1  #' Ncgdd
            #' normalized cumulative growing degree days
    
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

            s = 'kcb_daily(): cropclass_num %s cropOneToggle %s cycle %s'
            logging.debug(s % (crop.class_number, data.crop_one_flag, foo.cycle))

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
                        logging.debug('kcb_daily(): dairyCuttings %s  cycle %s  Crop_curve_number %s  curve_number %s' % (
                            dcuttings, foo.cycle, crop.curve_number, curve_number))

                    #' typical and beef hay.  Determine which of three kcb curves to use
                    if (crop.class_number == 1 or crop.class_number == 3 or
                        (crop.class_number >= 4 and
                         crop.curve_name.upper() == "ALFALFA 1ST CYCLE")):
                        #if foo.cycle < et_cell.beefCuttings + 0.01 - 1:     #' this could be - 2 if at least one, and sometimes two final cycles are desired
                        if foo.cycle < bcuttings + 0.01 - 1:     #' this could be - 2 if at least one, and sometimes two final cycles are desired
                            curve_number = crop.curve_number + 1 #' increment alfalfa curve to intermediate cycle
                        else:
                            curve_number = crop.curve_number + 2 #' increment alfalfa curve to fall/winter cycle
                        logging.debug('kcb_daily(): beefCuttings %s  cycle %s  Crop_curve_number %s  curve_number %s' % (
                            bcuttings, foo.cycle, crop.curve_number, curve_number))
    
                #' If ctCount = 2 and cycle > 3:     'dairy alfalfa 
                #'  curve_number = Crop_curve_number(ctCount) + 2  'end cycle (going into fall/winter)
                #' End If
                #' If ctCount = 3 and cycle > 2:     'beef alfalfa 
                #'  curve_number = Crop_curve_number(ctCount) + 2  'end cycle (going into fall/winter)
                #' End If
                #' Debug.Writeline "cycle, cgdd_efc, cumGDD_term, curve_number "; cycle, cgdd_efc, cumGDD_term, curve_number
                #' return false

            if cgdd_in_season < cgdd_efc:    
                # print 'kcbDaily:in cgdd_in_season < cgdd_efc'
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
                foo.mad = foo.mad_ini #' set management allowable depletion also
                #If int_cgdd Mod 10 = 0:    
                    #' Debug.Writeline "DoY, foo.n_cgdd kcb "; DoY, foo.n_cgdd, kcb
                    #' return false
            else:
                if cgdd_in_season < cgdd_term:     #' function is same as for < EFC
                    # print 'kcbDaily:in cgdd_in_season < cumGDD_term'
                    foo.n_cgdd = cgdd_in_season / cgdd_efc #' use ratio of cumGDD for EFC
    
                    #' increase ncumGDD term in SW Idaho to stretch kcb curve during late season
                    #' use value of cropFlags, if greater than 1 as scaler
    
                    ## This apparently does nothing, since crop_flags only either 0 or 1
                    ## skip for now   
                    #If cropFlags(ETCellCount, ctCount) > 1:    
                    #    ncumGDD = ncumGDD / cropFlags(ETCellCount, ctCount) #' reduce ncumGDD to make curve stretch longer
                    #End If
                    if foo.n_cgdd < 1:     
                        foo.n_cgdd = 1 #' keep from going back into dev. period
                    int_cgdd = min(foo.max_lines_in_crop_curve_table - 1, int(foo.n_cgdd * 10))
                    foo.mad = foo.mad_mid
                    lentry = et_cell.crop_coeffs[curve_number].lentry
                    if int_cgdd < lentry:     #' more entries in kcb array
                        #kcb = cropco_val(curve_number, int_cgdd) + (ncumGDD * 10 - int_cgdd) * (cropco_val(curve_number, int_cgdd + 1) - cropco_val(curve_number, int_cgdd))
                        foo.kcb = (
                            et_cell.crop_coeffs[curve_number].data[int_cgdd] +
                            (foo.n_cgdd * 10 - int_cgdd) *
                            (et_cell.crop_coeffs[curve_number].data[int_cgdd+1] -
                             et_cell.crop_coeffs[curve_number].data[int_cgdd]))
                        logging.debug(
                            'kcb_daily(): Kcb %s  int_cgdd %s  curve_number %s  lentry %s' %
                            (foo.kcb, int_cgdd, curve_number, lentry))
                        #If ctCount = 7:     
                        #    #' Debug.Writeline "after EFC, DoY foo.n_cgdd, int_cgdd, kcb "; DoY, ncumGDD, int_cgdd, kcb
                        #    #' return false
                    else:
                        #' hold kcb equal to last entry until either cumGDD_termination is exceeded or killing frost
                        foo.kcb = et_cell.crop_coeffs[curve_number].data[lentry]
                        logging.debug(
                            'kcb_daily(): Kcb %s  int_cgdd %s  curve_number %s  lentry %s' %
                            (foo.kcb, int_cgdd, curve_number, lentry))

                else:
                    #' end of season by exceeding cumGDD for termination.  set flag to 0
    
                    foo.in_season = False #' <------note that for cumGDD based crops, there is no extension past computed end
                    logging.debug('kcb_daily(): InSeason0 %s' % (foo.in_season))
                    foo.stress_event = False #' reset severe stress event flag
                    #' special case for ALFALFA   1 added 4/18/08
                    #If ctCount = 1 or ctCount = 2 or ctCount = 3 or (ctCount > 3 and ccName.Equals("ALFALFA 1ST CYCLE")):     
                    if (crop.class_number in [1,2,3] or
                        (crop.class_number >= 4 and
                         crop.curve_name.upper() == "ALFALFA 1ST CYCLE")):
                        #' (three curves for cycles, two cumGDD's for first and other cycles)
    
                        #' remember gu, cutting and frost dates for alfalfa crops for review
                        foo.cutting[foo.cycle] = foo_day.doy
    
                        #' increment and reset for next cycle
                        foo.cycle = foo.cycle + 1
                        foo.in_season = True
                        logging.debug(
                            'kcb_daily(): InSeason1 %s' % (foo.in_season))
                        foo.cgdd_at_planting = foo.cgdd #' set basis for next cycle
    
                        #' Following 2 lines added July 13, 2009 by RGA to reset alfalfa height to minimum each new cycle
                        foo.height = foo.height_min
    
                        #' and to set kcb to initial kcb value for first day following cutting.
    
                        #kcb = cropco_val(curve_number, 0)
                        foo.kcb = et_cell.crop_coeffs[curve_number].data[0]
                        logging.debug(
                            'kcb_daily(): Kcb %s  cgdd_at_planting %s' %
                            (foo.kcb, foo.cgdd_at_planting))

                # first alfalfa crop (typical production alfalfa) where kcb is reduced   '4/18/08...
                if (crop.class_number == 1 and data.crop_one_flag):     
                    foo.kcb = foo.kcb * data.crop_one_reducer #' xxx...apply only if cropOneToggle is set (4/09)
                    logging.debug('kcb_daily(): Kcb %s' % foo.kcb)
            days_into_season = float(foo_day.doy - foo.doy_start_cycle + 1) #' use this here only to invoke a total length limit
            if days_into_season < 1:    
                days_into_season += 365

            # Real value for length constraint (used for spring grain)
            # The cumGDD basis has exceeded length constraint.
            if (crop.time_for_harvest > 10 and
                days_into_season > crop.time_for_harvest):     
                #' end season.  set flag to 0
                foo.in_season = False #' This section added Jan. 2007
                logging.debug('kcb_daily(): InSeason2 %s' % (foo.in_season))
                foo.stress_event = False #' reset severe stress event flag
                #PrintLine(lfNum, "Year " & year & " Crop no: " & ctCount & ", " & cropn & " Reached Time Limit: " & time_for_harvest(ctCount))
                #' return false
            #' If year < 1952:     PrintLine(lfNum, getDmiDate(dailyDates(sdays - 1)) & Chr(9) & "kcbDaily kcb" & Chr(9) & kcb)


        #### crop.curve_type Case 2 ####
        if crop.curve_type == 2:
        #Case 2  #' %PL-EC
            # Percent of time from PL to EFC for all season
            days_into_season = float(foo_day.doy - foo.doy_start_cycle + 1)
            if days_into_season < 1:     
                days_into_season = days_into_season + 365
            if crop.time_for_efc < 1:     
                crop.time_for_efc = 1 #' deal with values of zero or null - added Dec. 29, 2011, rga
            foo.n_pl_ec = days_into_season / crop.time_for_efc
            npl_ec100 = foo.n_pl_ec * 100
            if foo.n_pl_ec < 1:    
                foo.mad = foo.mad_ini
            else:
                foo.mad = foo.mad_mid
    
            #' In next line, make sure that "System.Math.Abs()" does not change exact value for time_for_harvest() and that it is taking absolute value.
            #' Use absolute value for time_for_harvest since neg means to run until frost (Jan. 2007). also changed to <= from <
    
            logging.debug('kcb_daily(): npl_ec100 %s  time_for_harvest %s abs_time_for_harvest %s' % (
                npl_ec100, crop.time_for_harvest, abs(crop.time_for_harvest)))
            #if npl_ec100 <= abs(crop.time_for_harvest):    
            if round(npl_ec100,4) <= abs(crop.time_for_harvest):    
                logging.debug('kcb_daily(): n_pl_ec0 %s  max_lines_in_crop_curve_table %s' % (
                    foo.n_pl_ec, foo.max_lines_in_crop_curve_table))
                int_PL_EC = min(foo.max_lines_in_crop_curve_table - 1., int(foo.n_pl_ec * 10.))
                foo.kcb = (
                    et_cell.crop_coeffs[curve_number].data[int_PL_EC] +
                    (foo.n_pl_ec * 10 - int_PL_EC) *
                    (et_cell.crop_coeffs[curve_number].data[int_PL_EC+1] -
                     et_cell.crop_coeffs[curve_number].data[int_PL_EC]))
                logging.debug('kcb_daily():6 Kcb %s  int_PL_EC %s  n_pl_ec %s' % (
                    foo.kcb, int_PL_EC, foo.n_pl_ec))
                logging.debug('kcb_daily():6 days_into_season %s  time_for_EFC %s' % (
                    days_into_season, crop.time_for_efc))
            else:
                #' beyond stated end of season
                #' ------need provision to extend until frost termination if indicated for crop -- added Jan. 2007
    
                if crop.time_for_harvest < -0.5:     #' negative value is a flag to extend until frost
                    #' XXXXXXXXX  Need to set to yesterday's kcb for a standard climate
    
                    foo.kcb = foo.kcb_yesterday #' use yesterday's kcb which should trace back to last valid day of stated growing season
                    logging.debug('kcb_daily(): Kcb %s' % foo.kcb)
                else:
                    foo.in_season = False
                    foo.stress_event = False #' reset severe stress event flag
                    logging.debug('kcb_daily(): InSeason3 %s' % (foo.in_season))


        #### crop.curve_type Case 2 ####
        if crop.curve_type == 3:
        #Case 3  #' %PL-EC,daysafter
            #' percent of time from PL to EFC for before EFC and days after EFC after EFC
    
            days_into_season = float(foo_day.doy - foo.doy_start_cycle + 1)
            if days_into_season < 1:     
                days_into_season += 365
            if crop.time_for_efc < 1:     
                crop.time_for_efc = 1 #' deal with values of zero or null - added Dec. 29, 2011, rga
            foo.n_pl_ec = days_into_season / crop.time_for_efc
            if foo.n_pl_ec < 1:    
                int_PL_EC = min(foo.max_lines_in_crop_curve_table - 1, int(foo.n_pl_ec * 10.))
                #kcb = cropco_val(curve_number, int_PL_EC) + (n_pl_ec * 10 - int_PL_EC) _
                #    * (cropco_val(curve_number, int_PL_EC + 1) - cropco_val(curve_number, int_PL_EC))
                foo.kcb = (
                    et_cell.crop_coeffs[curve_number].data[int_PL_EC] +
                    (foo.n_pl_ec * 10 - int_PL_EC) *
                    (et_cell.crop_coeffs[curve_number].data[int_PL_EC+1] -
                     et_cell.crop_coeffs[curve_number].data[int_PL_EC]))
                logging.debug('kcb_daily(): Kcb %s  n_pl_ec %s  max_lines_in_crop_curve_table %s  int_PL_EC %s' % (
                    foo.kcb, foo.n_pl_ec, foo.max_lines_in_crop_curve_table, int_PL_EC))
                foo.mad = foo.mad_ini
            else:
                foo.mad = foo.mad_mid
                DaysafterEFC = days_into_season - crop.time_for_efc
    
                #' In next line, make sure that "System.Math.Abs()" does not change exact value for time_for_harvest() and that it is taking absolute value.
                #' Use absolute value for time_for_harvest since neg means to run until frost (Jan. 2007). also changed to <= from <
    
                if DaysafterEFC <= abs(crop.time_for_harvest):    
                    nDaysafterEFC = DaysafterEFC / 10 + 11 #' start at array index = 11 for 0 days into full cover
                    int_PL_EC = min(foo.max_lines_in_crop_curve_table - 1, int(nDaysafterEFC))
                    #kcb = cropco_val(curve_number, int_PL_EC) + (nDaysafterEFC - int_PL_EC) _
                    #    * (cropco_val(curve_number, int_PL_EC + 1) - cropco_val(curve_number, int_PL_EC))
                    foo.kcb = (
                        et_cell.crop_coeffs[curve_number].data[int_PL_EC] +
                        (nDaysafterEFC - int_PL_EC) *
                        (et_cell.crop_coeffs[curve_number].data[int_PL_EC+1] -
                         et_cell.crop_coeffs[curve_number].data[int_PL_EC]))
                    logging.debug('kcb_daily(): Kcb %s' % foo.kcb)
                else:
                    #' beyond stated end of season
                    #' ------need provision to extend until frost termination if indicated for crop -- added Jan. 2007
    
                    if crop.time_for_harvest < -0.5:     #' negative value is a flag to extend until frost -- added Jan. 2007
    
                        #' XXXX need to set to yesterday's standard climate kcb
    
                        foo.kcb = foo.kcb_yesterday #' use yesterday's kcb which should trace back to last valid day of stated growing season
                        logging.debug('kcb_daily(): Kcb %s' % foo.kcb)
                    else:
                        foo.in_season = False
                        foo.stress_event = False #' reset severe stress event flag
                        logging.debug('kcb_daily(): InSeason4 %s' % (foo.in_season))


        #### crop.curve_type Case 2 ####
        if crop.curve_type == 4:
        #Case 4  #' %PL-Termintate
            #' percent of time from PL to end of season
            #' Note that type 4 kcb curve uses T30 to estimate GU
            #' and symmetry around July 15 to estimate total season length.
    
            # Estimate end of season
    
            # If doy_start_cycle < 196 Then
            if foo.doy_start_cycle < crop.crop_gdd_trigger_doy + 195:
                ## CGM - end_of_season is not used anywhere else?
                ##end_of_season = (
                ##    crop.crop_gdd_trigger_doy + 195 +
                ##    (crop.crop_gdd_trigger_doy + 195 - foo.doy_start_cycle))
                length_of_season = 2 * (crop.crop_gdd_trigger_doy + 195 - foo.doy_start_cycle)
                #' end_of_season = 196 + (196 - foo.doy_start_cycle)
                #' length_of_season = 2 * (196 - foo.doy_start_cycle)
            else:
                #PrintLine(lfNum, "Problem with estimated Season length, Crop_curve_type_4")
                #if not batchFlag:     MsgBox("Problem with estimated Season length, Crop_curve_type_4")
                logging.error(
                    "Problem with estimated Season length, Crop_curve_type_4")
                raise SystemExit()
                ##sys.exit()
    
            # Put a minimum and maximum length on season for cheat grass (i= 47)
            if crop.class_number == 47:     #' was 38, should have been 42   'corr. Jan 07
                length_of_season = max(length_of_season, 60)
                if length_of_season > 90:
                    length_of_season = 100

            days_into_season = float(foo_day.doy - foo.doy_start_cycle)
            if days_into_season < 1:     
                days_into_season += 365
            foo.n_pl_ec = days_into_season / length_of_season
            if foo.n_pl_ec < 0.5:     #' assume season is split 50/50 for stress sensitivities for type 4
                foo.mad = foo.mad_ini
            else:
                foo.mad = foo.mad_mid

            if foo.n_pl_ec <= 1:    
                int_PL_EC = min(foo.max_lines_in_crop_curve_table - 1, int(foo.n_pl_ec * 10))
                foo.kcb = (
                    cropco_val(curve_number, int_PL_EC) +
                    (foo.n_pl_ec * 10 - int_PL_EC) *
                    (cropco_val(curve_number, int_PL_EC + 1) - cropco_val(curve_number, int_PL_EC)))
                logging.debug('kcb_daily(): Kcb %s' % foo.kcb)
            else:
                # Beyond end of season
                foo.in_season = False
                foo.stress_event = False #' reset severe stress event flag
                logging.debug('kcb_daily(): InSeason5 %s' % (foo.in_season))
        #End Select



        #' Following is discounting for cold shock to alfalfa gets reset on Jan 1
        #' check for -2C or -3C temperature for peak alfalfa curve to begin discount
        #' discount kcb .01 or .005 per day since first occurrence of -2 C or -3 C in fall.

        # Peak alfalfa curve and both alfalfa crops (apply to all)(i=1,2,3) 
        if (crop.class_number < 4 or
            (crop.class_number > 3 and
             crop.curve_name.upper() == "ALFALFA 1ST CYCLE")):     
            if foo_day.doy > crop.crop_gdd_trigger_doy + 211:    
                # If doy > 212:
                # First occurrence of -3C (was -2, now -3)
                if foo_day.tmin < -3 and foo.T2Days < 1:     
                    foo.T2Days = 1
            else:
                foo.T2Days = 0 #' reset discount timer if prior to August
            if foo.T2Days > 0:    
                foo.kcb -= foo.T2Days * 0.005 #'  was 0.01
                logging.debug('kcb_daily(): Kcb %s' % foo.kcb)
                if foo.kcb < 0.1:     
                    foo.kcb = 0.1
                    logging.debug('kcb_daily(): Kcb %s' % foo.kcb)
                foo.T2Days = foo.T2Days + 1

        # Determine if killing frost to cut short - begin to check after August 1.
        # If doy > 212:    
        if foo_day.doy > crop.crop_gdd_trigger_doy + 211:    
            if foo_day.tmin < crop.killing_frost_temperature:    
                # All crops besides covers
                if crop.class_number < 44 or crop.class_number > 46:
                    #' If ctCount < 39 or ctCount > 41:         'was prior to Jan. 07
                    if foo.in_season:    
                        logging.info(
                            "Killing frost for crop %s of %s was found on DOY %s of %s" %
                            (crop.class_number, crop.killing_frost_temperature,
                             foo_day.doy, foo_day.year))
                        foo.in_season = False
                        foo.stress_event = False #' reset severe stress event flag
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
                        ##
                        ##if (crop.class_number == 3 or
                        ##    (crop.class_number > 3 and
                        ##     crop.curve_name.upper() == "ALFALFA 1ST CYCLE")):     
                        ##    output_str = ""
                        ##    #output_str = output_str & DFormat(RefETIDs(ETCellCount), " #########") & DFormat(year, "  ####") & DFormat(doy_start_cycle, " ###")
                        ##    #For cutCount = 1 To 10
                        ##    #    foo.cutting(cutCount) = 0
                        ##    #Next cutCount
                        ##    #output_str = output_str & DFormat(DoY, " #####")
                        ##    #PrintLine(cb2FNum, output_str)

            # Print out cycles for alfalfa when there is no killing frost
            if (crop.class_number == 2 or crop.class_number == 3 or
                (crop.class_number > 3 and
                 crop.curve_name.upper() == "ALFALFA 1ST CYCLE")):
                if foo.in_season:    
                    #' end of year, no killing frost on alfalfa, but print cycle information to file
                    if foo_day.month == 12 and foo_day.day == 31:     
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
                        ##
                        ##if (crop.class_number > 2 and
                        ##    crop.curve_name.upper() == "ALFALFA 1ST CYCLE"):
                        ##    output_str = ""
                        ##    #output_str = output_str & DFormat(RefETIDs(ETCellCount), " #########") & DFormat(year, "  ####") & DFormat(doy_start_cycle, " ###")
                        ##    #For cutCount = 1 To 10
                        ##    #    output_str = output_str & DFormat(cutting(cutCount), " ####")
                        ##    #    foo.cutting(cutCount) = 0
                        ##    #Next
                        ##    #output_str = output_str & DFormat(DoY, " #####")
                        ##    #PrintLine(cb2FNum, output_str)

        # This kcb is not adjusted for climate 'keep track of this for debugging
        kcb_noadj = foo.kcb

    #End If #' end of if season = 1

    #'  sub in winter time kcb if before or after season

    # Kcb for winter time land use
    # 44: Bare soil
    # 45: Mulched soil, including grain stubble
    # 46: Dormant turf/sod (winter time)
    # Note: set kc_max for winter time (Nov-Mar) and fc outside of this sub.
    if crop.class_number == 44:     #' bare soil   
        foo.kcb = 0.1 #' was 0.2
        logging.debug('kcb_daily(): Kcb %s' % foo.kcb)
        foo.kcb_wscc[1] = foo.kcb #' remember this value to assign to regular crops, etc. during nonseason.
    elif crop.class_number == 45:     #' Mulched soil, including wheat stubble 
        foo.kcb = 0.1 #' was 0.2
        logging.debug('kcb_daily(): Kcb %s' % foo.kcb)
        foo.kcb_wscc[2] = foo.kcb
    elif crop.class_number == 46:     #' Dormant turf/sod (winter time) 
        foo.kcb = 0.1 #' was 0.3
        logging.debug('kcb_daily(): Kcb %s' % foo.kcb)
        foo.kcb_wscc[3] = foo.kcb

    # Open water evaporation "crops"
    # 55: Open water shallow systems (large ponds, streams)
    # 56: Open water deep systems (lakes, reservoirs)
    # 57: Open water small stock ponds
    # This section for WATER only
    if crop.class_number in [55, 56, 57]:      
        if crop.class_number == 55:
            if data.refet_type > 0:     #' Allen 3/6/08
                foo.kcb = 0.6 #' for ETr basis
                logging.debug('kcb_daily(): Kcb %s' % foo.kcb)
            else:
                # For ETo basis 'Allen 12/26/07....
                # Note that these values are substantially different from FAO56
                foo.kcb = 1.05
                logging.debug('kcb_daily(): Kcb %s' % foo.kcb)
        elif crop.class_number == 56:
            # This is a place holder, since an aerodynamic function is used
            foo.kcb = 0.3 
            logging.debug('kcb_daily(): Kcb %s' % foo.kcb)
            etrf = open_water_evap.open_water_evap(foo, foo_day)
            foo.kcb = etrf
            logging.debug('kcb_daily(): Kcb %s' % foo.kcb)
        elif crop.class_number == 57:
            if data.refet_type > 0:     #' Allen 3/6/08
                foo.kcb = 0.7 #' for ETr basis
                logging.debug('kcb_daily(): Kcb %s' % foo.kcb)
            else:
                foo.kcb = 0.85 #' for ETo basis 'Allen 12/26/07
                logging.debug('kcb_daily(): Kcb %s' % foo.kcb)
        foo.kc_act = foo.kcb #' water has only 'kcb'
        foo.kc_pot = foo.kcb
        # ETr changed to ETref 12/26/2007
        foo.etc_act = foo.kc_act * foo_day.etref 
        foo.etc_pot = foo.kc_pot * foo_day.etref
        foo.etc_bas = foo.kcb * foo_day.etref
        # Keep track of this for debugging
        kcb_noadj = foo.kcb 
    else:
        # Added 12/26/07 to adjust kcb for ETo basis for climate
        # Keep track of this for debugging '12/26/07
        kcb_noadj = foo.kcb 

    # Save kcb value for use tomorrow in case curve needs to be extended until frost
    foo.kcb_yesterday = kcb_noadj

    # Adjustment to kcb moved here 2/21/08 to catch when during growing season
    # Limit crop height for numerical stability
    foo.height = max(foo.height, 0.05)

    # RHmin and U2 are computed in Climate subroutine
    #pprint(vars(foo_day))
    if data.refet_type > 0:     #' Allen 3/26/08
        #' ETr basis, therefore, no adjustment to kcb
        pass
    else:
        logging.debug(
            'kcb_daily(): Kcb0 %.6f  U2 %.6f  RHmin %.6f  Height %.6f' % 
            (foo.kcb, foo_day.u2, foo_day.rh_min, foo.height))
        #' ******'12/26/07
        foo.kcb = (
            foo.kcb + (0.04 * (foo_day.u2 - 2) - 0.004 * (foo_day.rh_min - 45)) *
            (foo.height / 3) ** 0.3) 
        logging.debug('kcb_daily(): Kcb %.6f' % (foo.kcb))
    # Set up as yesterday's cumulative GDD for tomorrow
    foo.l_cgdd = foo.cgdd
    