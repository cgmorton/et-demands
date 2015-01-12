import datetime
from pprint import pprint
import sys

import open_water_evap

def kcb_daily(data, crop, et_cell, foo, foo_day, OUT):
    """Compute basal ET."""
    #print 'in kcb_daily()'
    #print crop
    #pprint(vars(crop))

    # Following two variables are used in one equation each but are never assigned a value - dlk - ?
    bcuttings = 0
    dcuttings = 0

    #Try
    # Determine if inside or outside growing period
    # Procedure for deciding start and return false of season.
    #cCurveNo = Crop_curve_number(ctCount)
    cCurveNo = crop.crop_curve_number

    # Determination of start of season was rearranged April 12 2009 by R.Allen
    # To correct computation error in limiting first and latest starts of season 
    #   that caused a complete loss of crop start turnon.

    # XXX Need to reset Realstart = false twice in Climate Sub.

    # Flag for estimating start of season 1 = cumGDD, 2 = T30, 3 = date, 4 or 0 is on all the time
    OUT.debug('2kcb_daily():0 Flag_for_means_to_estimate_pl_or_gu %s\n' % (
        crop.flag_for_means_to_estimate_pl_or_gu))
    OUT.debug('2kcb_daily():0 kcb %s  kcb_yesterday %s\n' % (
        foo.kcb, foo.kcb_yesterday))

    #### Flag_for_means_to_estimate_pl_or_gu Case 1 #########
    #Select Case Flag_for_means_to_estimate_pl_or_gu(ctCount)
    #    Case 1
    if crop.flag_for_means_to_estimate_pl_or_gu == 1:
        # print 'in kcbDaily().CASE 1'
        #' cumGDD

        # Only allow start flag to begin if < July 15 to prevent GU in fall after freezedown
        if foo_day.doy < crop.crop_gdd_trigger_doy + 195:
            #' before finding date of startup using normal cumGDD, determine if it is after latest
            #' allowable start by checking to see if pl or gu need to be constrained based on long term means
            #' estimate date based on long term mean:
            #' prohibit specifying start of season as long term less 40 days when it is before that date.

            foo_day.cumGDD0LT[0] = foo_day.cumGDD0LT[1]
            longtermpl = 0
            #For jDoy = 1 To 366
            for jDoy in range(1,367):
                if (foo_day.cumGDD0LT[jDoy] > crop.t30_for_pl_or_gu_or_cumgdd and
                    foo_day.cumGDD0LT[jDoy-1] < crop.t30_for_pl_or_gu_or_cumgdd):
                    longtermpl = jDoy

            if longtermpl > 0:
                if foo_day.doy > longtermpl + 40: #' check if getting too late in season
                    if not foo.real_start:  #' season hasn't started yet
                        foo.jd_start_cycle = foo_day.doy #' was longtermpl + 40 ----4/30/2009
                        foo.real_start = True

            # Start of season has not yet been determined.  Look for it in normal fashion:
            if not foo.real_start:
                #' JH,RGA 4/13/09
                if foo.cumgdd > crop.t30_for_pl_or_gu_or_cumgdd:
                    #' if cumgdd > t30_for_pl_or_gu_or_cumgdd(ctCount) And lcumGDD < T30_for_pl_or_gu_or_cumGDD(ctCount) Then 'was until 4/13/09.  last part not needed now, with Realstart 'JH,RGA
                    #' planting or GU is today

                    #' This is modeled startup day, but check to see if it is too early
                    if longtermpl > 0:    
                        if foo_day.doy < longtermpl - 40:     #' use +/- 40 days from longterm as constraint
                            foo.real_start = False #' too early to start season
                            foo.jd_start_cycle = longtermpl - 40
                            if foo.jd_start_cycle < 1:     
                                foo.jd_start_cycle = foo.jd_start_cycle + 365
                        else:
                            foo.jd_start_cycle = foo_day.doy
                            foo.real_start = True
                    else:
                        foo.jd_start_cycle = foo_day.doy
                        foo.real_start = True

            #' if season start has been found then turn parameters on
            #' Look for day when DoY equals jd_start_cycle
            #' Note that this requires that all days be present (no missing days)

            if foo_day.doy == foo.jd_start_cycle:    
                foo.real_start = True
                foo.stress_event = False #' reset severe stress event flag
                foo.in_season = True #' turn season on
                foo.dormant_setup_flag = True #' set set up flag positive for next end of season
                foo.setup_crop(crop) #' initialize rooting depth, etc. for crop
                foo.cycle = 1 #' first cycle for alfalfa

                #' some range grasses require backing up 10 days
                #' note that following logic will cause first 10 days to not be assigned to range grasses, but to winter cover
                #' but this code needs to be here because process (or doy) can not go back in time

                if crop.date_of_pl_or_gu < 0.0:    
                    foo.jd_start_cycle = foo.jd_start_cycle + int(crop.date_of_pl_or_gu)
                    if foo.jd_start_cycle < 1:     
                        foo.jd_start_cycle = foo.jd_start_cycle + 365

            OUT.debug('2kcb_daily():c1 InSeason %s  longtermpl %s  doy %s  jd_start_cycle %s\n' % (
                foo.in_season, longtermpl, foo_day.doy, foo.jd_start_cycle))
            OUT.debug('2kcb_daily():c1 T30_for_pl_or_gu_or_cumGDD %s  cumGDD0LT156 %s  cumGDD0LT155 %s\n' % (
                crop.t30_for_pl_or_gu_or_cumgdd, foo_day.cumGDD0LT[156], foo_day.cumGDD0LT[155]))

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

            T30LT = data.climate['mainT30LT']
            T30LT[0] = T30LT[1]
            longtermpl = 0
            for jDoy in range(1,367):
                if longtermpl < 1:
                    #' line added 4/29/09 to keep from multiple longterm start dates.  duh.
                    #if foo_day.t30LT[jDoy] > crop.t30_for_pl_or_gu_or_cumgdd and foo_day.t30LT[jDoy-1] < crop.t30_for_pl_or_gu_or_cumgdd:
                    if (T30LT[jDoy] > crop.t30_for_pl_or_gu_or_cumgdd and
                        T30LT[jDoy-1] <= crop.t30_for_pl_or_gu_or_cumgdd):
                        longtermpl = jDoy
            OUT.debug('2kcb_daily():c2 longtermpl %s  T30LT(0) %s  T30LT(1) %s\n' % (
                longtermpl, T30LT[0], T30LT[1]))

            if longtermpl > 0:
                if foo_day.doy > longtermpl+40:  #' check if getting too late in season
                    if not foo.real_start:        #' season hasn't started yet
                        foo.jd_start_cycle = foo_day.doy #' longtermpl + 40 'it is unseasonably warm (too warm). Delay start ' set to Doy on 4/29/09 (nuts)
                        OUT.debug('2kcb_daily():c2a jd_start_cycle %s\n' % (
                            foo.jd_start_cycle))
                        foo.real_start = True    #' Harleys Rule
                        #PrintLine(lfNum, "exceeded 40 days past longterm T30 turnon")

            if not foo.real_start:     #' start of season has not yet been determined.  Look for it in normal fashion:
                if foo_day.t30 > crop.t30_for_pl_or_gu_or_cumgdd:     #' 'JH,RGA 4/13/09
                    if longtermpl > 0:    
                        if foo_day.doy < longtermpl - 40:     #' use +/- 40 days from longterm as constraint
                            foo.real_start = False #' too early to start season
                            foo.jd_start_cycle = longtermpl - 40
                            OUT.debug('2kcb_daily():c2b jd_start_cycle %s\n' % (
                                foo.jd_start_cycle))
                            if foo.jd_start_cycle < 1:     
                                foo.jd_start_cycle = foo.jd_start_cycle + 365
                                OUT.debug('2kcb_daily():c2c jd_start_cycle %s\n' % (
                                    foo.jd_start_cycle))
                        else:
                            foo.jd_start_cycle = foo_day.doy
                            OUT.debug('2kcb_daily():c2d jd_start_cycle %s\n' % (
                                foo.jd_start_cycle))
                            foo.real_start = True
                    else:
                        foo.jd_start_cycle = foo_day.doy
                        OUT.debug('2kcb_daily():c2e jd_start_cycle %s\n' % (
                            foo.jd_start_cycle))
                        foo.real_start = True

            #' if season start has been found then turn parameters on
            #' Look for day when DoY equals jd_start_cycle
            #' Note that this requires that all days be present (no missing days)
            if foo_day.doy == foo.jd_start_cycle:    
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
                    foo.jd_start_cycle = foo.jd_start_cycle + int(crop.date_of_pl_or_gu)
                    OUT.debug('2kcb_daily():c2f jd_start_cycle %s\n' % (
                        foo.jd_start_cycle))
                    if foo.jd_start_cycle < 1:     
                        foo.jd_start_cycle = foo.jd_start_cycle + 365
                        OUT.debug('2kcb_daily():c2g jd_start_cycle %s\n' % (
                            foo.jd_start_cycle))

            OUT.debug('2kcb_daily():c2 jd_start_cycle %s  DoY %s  real_start %s\n' % (
                foo.jd_start_cycle, foo_day.doy, foo.real_start))
            OUT.debug('2kcb_daily():c2 T30 %s  t30_for_pl_or_gu_or_cumGDD %s  Date_of_pl_or_gu %s\n' % (
                foo_day.t30, crop.t30_for_pl_or_gu_or_cumgdd, crop.date_of_pl_or_gu))
            OUT.debug('2kcb_daily():c2 InSeason %s\n' % (foo.in_season))
    
            # print 'in kcbDaily().CASE 2', crop.crop_gdd_trigger_doy, longtermpl, foo.jd_start_cycle, foo_day.doy

    #### Flag_for_means_to_estimate_pl_or_gu Case 3 #########
    #Case 3
    ###crop.flag_for_means_to_estimate_pl_or_gu = 3
    elif crop.flag_for_means_to_estimate_pl_or_gu == 3:
        # print 'in kcbDaily().CASE 3'
        #' a date is used for planting or greenup

        Mo = int(crop.date_of_pl_or_gu)
        dayMo = (crop.date_of_pl_or_gu - Mo) * 30.4
        if dayMo < 0.5:     
            dayMo = 15

        # print Mo, dayMo, crop.date_of_pl_or_gu 
        # vb code (DateSerial) apparently resolves Mo=0 to 12
        # JDL = DateSerial(yearOfCalcs, Mo, dayMo).DayOfYear
        if Mo == 0:
            Mo = 12
        JDL = datetime.datetime(foo_day.yearOfCalcs,Mo,dayMo).timetuple().tm_yday
        #OUT.debug('2kcb_daily():c3 Date_of_pl_or_gu %s  Mo %s  JDL %s\n' % (crop.date_of_pl_or_gu, Mo, JDL))

        #' modified next statement to get winter grain to et and irrigate in first year of run.  dlk  08/16/2012

        if (foo_day.doy == JDL or
            (foo_day.sdays == 1 and JDL >= crop.crop_gdd_trigger_doy)):    
            foo.jd_start_cycle = JDL
            foo.stress_event = False #' reset severe stress event flag
            foo.in_season = True #' turn season on
            foo.dormant_setup_flag = True #' set set up flag positive for next end of season
            foo.setup_crop(crop) #' initialize rooting depth, etc. for crop

        OUT.debug('2kcb_daily():c3 InSeason %s\n' % (foo.in_season))
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

        OUT.debug('2kcb_daily():c4 InSeason %s\n' % (foo.in_season))
    #Case Else
    else:
        # print 'in kcbDaily().CASE else'
        #' flag = 4 or 0 ('crop' is on all time)

        foo.in_season = True #' turn season on
        if foo_day.doy == crop.crop_gdd_trigger_doy:     
            foo.stress_event = False #' reset severe stress event flag if first of year
        foo.dormant_setup_flag = True #' set set up flag positive for next end of season

        OUT.debug('2kcb_daily():cE InSeason %s\n' % (foo.in_season))
    #### END Case  ####



    #cCurveNo = Crop_curve_number(ctCount)
    foo.MAD = foo.MADmid  #' set MAD to MADmid universally at the start.  Value will be changed later.  R.Allen 12/14/2011
    #### InSeason  ####
    if foo.in_season:     #' <------This kcb loop only conducted if inside growing season
        #' crop curve type: 1 = NcumGDD, 2 = %PL-EC, 3 = %PL-EC,daysafter, 4 = %PL-Term

        #### crop.crop_curve_type Case 1 ####
        #    Select Case Crop_curve_type(ctCount)
        if crop.crop_curve_type == 1:
        #Case 1  #' NCGDD
            #' normalized cumulative growing degree days
    
            if foo.jd_start_cycle == foo_day.doy:     
                foo.cumGDDAtPlanting = foo.cumgdd
            cumGDDinseason = foo.cumgdd - foo.cumGDDAtPlanting
            cumGDDinseason = max(0, cumGDDinseason)
            cumGDD_EFC = crop.cumgdd_for_efc
            cumGDD_term = crop.cumgdd_for_termination
    
            #' increase cumGDD_term in SW Idaho to create longer late season
            #' use value of cropFlags, if greater than 1 as scaler
    
            ### This apparently does nothing, since crop_flags only either 0 or 1
            # skip for now
            #' <-------NOTE:  ONLY FUNCTIONAL FOR FLAG > 1.0, changed to >0, 1/2007
            #If cropFlags(ETCellCount, ctCount) > 0.001:     
            if et_cell.crop_flags[crop.crop_class_num] > 0.001:
                #' <---- Jan 2007, invoke always to catch flag < or > 1
                cumGDD_term = cumGDD_term * et_cell.crop_flags[crop.crop_class_num] 
            #' cumGDD_EFC is not effected, only period following EFC

            s = '2kcb_daily():1P cropclass_num %s cropOneToggle %s cycle %s\n'
            OUT.debug(s % (crop.crop_class_num, data.ctrl['cropOneToggle'], foo.cycle))

            #' special case for ALFALFA hay (typical, beef or dairy)  ' 4/09
            #If (ctCount = 1 and cropOneToggle = 1) or ctCount = 2 or ctCount = 3 or (ctCount > 3 and ccName.Equals("ALFALFA 1ST CYCLE")):     
            if ((crop.crop_class_num == 1 and data.ctrl['cropOneToggle'] == 1) or
                crop.crop_class_num == 2 or crop.crop_class_num == 3 or
                (crop.crop_class_num > 3 and
                 crop.crop_curve_name == "Alfalfa 1st cycle")):
                cumGDD_term = crop.cumgdd_for_efc               #' termination for first cycle for alfalfa is in EFC cumGDD
                if foo.cycle > 1:                               #' termination for all other alfalfa cycles is stored in termination cumGDD.
                    cumGDD_EFC = crop.cumgdd_for_termination    #' the 'term' cumGDD is for second cycles and on
                    cumGDD_term = crop.cumgdd_for_termination   #' CHECK to see if cumGDD should be incremented with cycle 3/08
                    if crop.crop_class_num == 2:                             #' dairy hay.  Determine which of three kcb curves to use
                        #if foo.cycle < et_cell.dairyCuttings + 0.01 - 1:     #' this could be - 2 if at least one, and sometimes two final cycles are desired
                        if foo.cycle < dcuttings + 0.01 - 1:     #' this could be - 2 if at least one, and sometimes two final cycles are desired
                            cCurveNo = crop.crop_curve_number + 1 #' increment alfalfa curve to intermediate cycle
                        else: #' R.Allen 4/1/08
                            cCurveNo = crop.crop_curve_number + 2 #' increment alfalfa curve to fall/winter cycle
                        OUT.debug('2kcb_daily():1a dairyCuttings %s  cycle %s  Crop_curve_number %s  cCurveNo %s\n' % (
                            dcuttings, foo.cycle, crop.crop_curve_number, cCurveNo))

                    #' typical and beef hay.  Determine which of three kcb curves to use
                    if (crop.crop_class_num == 1 or crop.crop_class_num == 3 or
                        (crop.crop_class_num > 3 and crop.crop_curve_name == "Alfalfa 1st cycle")):
                        #if foo.cycle < et_cell.beefCuttings + 0.01 - 1:     #' this could be - 2 if at least one, and sometimes two final cycles are desired
                        if foo.cycle < bcuttings + 0.01 - 1:     #' this could be - 2 if at least one, and sometimes two final cycles are desired
                            cCurveNo = crop.crop_curve_number + 1 #' increment alfalfa curve to intermediate cycle
                        else:
                            cCurveNo = crop.crop_curve_number + 2 #' increment alfalfa curve to fall/winter cycle
                        OUT.debug('2kcb_daily():1b beefCuttings %s  cycle %s  Crop_curve_number %s  cCurveNo %s\n' % (
                            bcuttings, foo.cycle, crop.crop_curve_number, cCurveNo))
    
                #' If ctCount = 2 and cycle > 3:     'dairy alfalfa 
                #'  ccurveno = Crop_curve_number(ctCount) + 2  'end cycle (going into fall/winter)
                #' End If
                #' If ctCount = 3 and cycle > 2:     'beef alfalfa 
                #'  ccurveno = Crop_curve_number(ctCount) + 2  'end cycle (going into fall/winter)
                #' End If
                #' Debug.Writeline "cycle, cumGDD_EFC, cumGDD_term, ccurveno "; cycle, cumGDD_EFC, cumGDD_term, ccurveno
                #' return false

            if cumGDDinseason < cumGDD_EFC:    
                # print 'kcbDaily:in cumGDDinseason < cumGDD_EFC'
                foo.ncumGDD = cumGDDinseason / cumGDD_EFC
                intcumGDD = min(foo.maxLinesInCropCurveTable - 1, int(foo.ncumGDD * 10))
                #kcb = cropco_val(cCurveNo, intcumGDD) + (foo.ncumGDD * 10 - intcumGDD) * (cropco_val(cCurveNo, intcumGDD + 1) - cropco_val(cCurveNo, intcumGDD))
                foo.kcb = (
                    data.crop_coeffs[cCurveNo].data[intcumGDD] +
                    (foo.ncumGDD * 10 - intcumGDD) *
                    (data.crop_coeffs[cCurveNo].data[intcumGDD+1] -
                     data.crop_coeffs[cCurveNo].data[intcumGDD]))
                OUT.debug('2kcb_daily():1 kcb %s  ncumGDD %s  intcumGDD %s\n' % (
                    foo.kcb, foo.ncumGDD, intcumGDD))
                OUT.debug('2kcb_daily():1 cumGDDinseason %s  cumGDD_EFC %s\n' % (
                    cumGDDinseason, cumGDD_EFC))
                OUT.debug('2kcb_daily():1 cumGDD %s  cumGDDAtPlanting %s\n' % (
                    foo.cumgdd, foo.cumGDDAtPlanting))
                foo.MAD = foo.MADini #' set management allowable depletion also
                #If intcumGDD Mod 10 = 0:    
                    #' Debug.Writeline "DoY, foo.ncumGDD kcb "; DoY, foo.ncumGDD, kcb
                    #' return false
            else:
                if cumGDDinseason < cumGDD_term:     #' function is same as for < EFC
                    # print 'kcbDaily:in cumGDDinseason < cumGDD_term'
                    foo.ncumGDD = cumGDDinseason / cumGDD_EFC #' use ratio of cumGDD for EFC
    
                    #' increase ncumGDD term in SW Idaho to stretch kcb curve during late season
                    #' use value of cropFlags, if greater than 1 as scaler
    
                    ## This apparently does nothing, since crop_flags only either 0 or 1
                    ## skip for now   
                    #If cropFlags(ETCellCount, ctCount) > 1:    
                    #    ncumGDD = ncumGDD / cropFlags(ETCellCount, ctCount) #' reduce ncumGDD to make curve stretch longer
                    #End If
                    if foo.ncumGDD < 1:     
                        foo.ncumGDD = 1 #' keep from going back into dev. period
                    intcumGDD = min(foo.maxLinesInCropCurveTable - 1, int(foo.ncumGDD * 10))
                    foo.MAD = foo.MADmid
                    lentry = data.crop_coeffs[cCurveNo].lentry
                    if intcumGDD < lentry:     #' more entries in kcb array
                        #kcb = cropco_val(cCurveNo, intcumGDD) + (ncumGDD * 10 - intcumGDD) * (cropco_val(cCurveNo, intcumGDD + 1) - cropco_val(cCurveNo, intcumGDD))
                        foo.kcb = (
                            data.crop_coeffs[cCurveNo].data[intcumGDD] +
                            (foo.ncumGDD * 10 - intcumGDD) *
                            (data.crop_coeffs[cCurveNo].data[intcumGDD+1] -
                             data.crop_coeffs[cCurveNo].data[intcumGDD]))
                        OUT.debug('2kcb_daily():2 kcb %s  intcumGDD %s  cCurveNo %s  lentry %s\n' % (
                            foo.kcb, intcumGDD, cCurveNo, lentry))
                        #If ctCount = 7:     
                        #    #' Debug.Writeline "after EFC, DoY foo.ncumGDD, intcumGDD, kcb "; DoY, ncumGDD, intcumGDD, kcb
                        #    #' return false
                    else:
                        #' hold kcb equal to last entry until either cumGDD_termination is exceeded or killing frost
                        foo.kcb = data.crop_coeffs[cCurveNo].data[lentry]
                        OUT.debug('2kcb_daily():3 kcb %s  intcumGDD %s  cCurveNo %s  lentry %s\n' % (
                            foo.kcb, intcumGDD, cCurveNo, lentry))

                else:
                    #' end of season by exceeding cumGDD for termination.  set flag to 0
    
                    foo.in_season = False #' <------note that for cumGDD based crops, there is no extension past computed end
                    OUT.debug('2kcb_daily(): InSeason0 %s\n' % (foo.in_season))
                    foo.stress_event = False #' reset severe stress event flag
                    #' special case for ALFALFA   1 added 4/18/08
                    #If ctCount = 1 or ctCount = 2 or ctCount = 3 or (ctCount > 3 and ccName.Equals("ALFALFA 1ST CYCLE")):     
                    #if crop.crop_class_num == 1 or crop.crop_class_num == 2 or crop.crop_class_num == 3 or (crop.crop_class_num > 3 and crop.crop_curve_name == "Alfalfa 1st cycle"):
                    if (crop.crop_class_num in [1,2,3] or
                        (crop.crop_class_num > 3 and
                         crop.crop_curve_name == "Alfalfa 1st cycle")):
                        #' (three curves for cycles, two cumGDD's for first and other cycles)
    
                        #' remember gu, cutting and frost dates for alfalfa crops for review
                        foo.cutting[foo.cycle] = foo_day.doy
    
                        #' increment and reset for next cycle
                        foo.cycle = foo.cycle + 1
                        foo.in_season = True
                        OUT.debug('2kcb_daily(): InSeason1 %s\n' % (foo.in_season))
                        foo.cumGDDAtPlanting = foo.cumgdd #' set basis for next cycle
    
                        #' Following 2 lines added July 13, 2009 by RGA to reset alfalfa height to minimum each new cycle
                        foo.Hcrop = foo.hmin
    
                        #' and to set kcb to initial kcb value for first day following cutting.
    
                        #kcb = cropco_val(cCurveNo, 0)
                        foo.kcb = data.crop_coeffs[cCurveNo].data[0]
                        OUT.debug('2kcb_daily():4 kcb %s  cumGDDAtPlanting %s\n' % (
                            foo.kcb, foo.cumGDDAtPlanting))

                #' first alfalfa crop (typical production alfalfa) where kcb is reduced   '4/18/08...
                if (crop.crop_class_num == 1 and data.ctrl['cropOneToggle'] == 1):     
                    foo.kcb = foo.kcb * data.ctrl['alfalfa1Reducer'] #' xxx...apply only if cropOneToggle is set (4/09)
                    OUT.debug('2kcb_daily():5 kcb %s\n' % foo.kcb)
            days_into_eason = float(foo_day.doy - foo.jd_start_cycle + 1) #' use this here only to invoke a total length limit
            if days_into_eason < 1:    
                days_into_eason = days_into_eason + 365
            if crop.time_for_harvest > 10:     #' real value for length constraint (used for spring grain)
                if days_into_eason > crop.time_for_harvest:     #' the cumGDD basis has exceeded length constraint.
                    #' end season.  set flag to 0
                    foo.in_season = False #' This section added Jan. 2007
                    OUT.debug('2kcb_daily(): InSeason2 %s\n' % (foo.in_season))
                    foo.stress_event = False #' reset severe stress event flag
                    #PrintLine(lfNum, "Year " & yearOfCalcs & " Crop no: " & ctCount & ", " & cropn & " Reached Time Limit: " & time_for_harvest(ctCount))
                    #' return false
            #' If yearOfCalcs < 1952:     PrintLine(lfNum, getDmiDate(dailyDates(sdays - 1)) & Chr(9) & "kcbDaily kcb" & Chr(9) & kcb)



        #### crop.crop_curve_type Case 2 ####
        if crop.crop_curve_type == 2:
        #Case 2  #' %PL-EC
            #' percent of time from PL to EFC for all season
    
            days_into_eason = float(foo_day.doy - foo.jd_start_cycle + 1)
            if days_into_eason < 1:     
                days_into_eason = days_into_eason + 365
            if crop.time_for_efc < 1:     
                crop.time_for_efc = 1 #' deal with values of zero or null - added Dec. 29, 2011, rga
            foo.nPL_EC = days_into_eason / crop.time_for_efc
            npl_ec100 = foo.nPL_EC * 100
            if foo.nPL_EC < 1:    
                foo.MAD = foo.MADini
            else:
                foo.MAD = foo.MADmid
    
            #' In next line, make sure that "System.Math.Abs()" does not change exact value for time_for_harvest() and that it is taking absolute value.
            #' Use absolute value for time_for_harvest since neg means to run until frost (Jan. 2007). also changed to <= from <
    
            OUT.debug('2kcb_daily():6_7 npl_ec100 %s  time_for_harvest %s abs_time_for_harvest %s\n' % (
                npl_ec100, crop.time_for_harvest, abs(crop.time_for_harvest)))
            #if npl_ec100 <= abs(crop.time_for_harvest):    
            if round(npl_ec100,4) <= abs(crop.time_for_harvest):    
                OUT.debug('2kcb_daily():6 nPL_EC0 %s  maxLinesInCropCurveTable %s\n' % (
                    foo.nPL_EC, foo.maxLinesInCropCurveTable))
                int_PL_EC = min(foo.maxLinesInCropCurveTable - 1., int(foo.nPL_EC * 10.))
                foo.kcb = (
                    data.crop_coeffs[cCurveNo].data[int_PL_EC] +
                    (foo.nPL_EC * 10 - int_PL_EC) *
                    (data.crop_coeffs[cCurveNo].data[int_PL_EC+1] -
                     data.crop_coeffs[cCurveNo].data[int_PL_EC]))
                OUT.debug('2kcb_daily():6 kcb %s  int_PL_EC %s  nPL_EC %s\n' % (
                    foo.kcb, int_PL_EC, foo.nPL_EC))
                OUT.debug('2kcb_daily():6 days_into_eason %s  time_for_EFC %s\n' % (
                    days_into_eason, crop.time_for_efc))
            else:
                #' beyond stated end of season
                #' ------need provision to extend until frost termination if indicated for crop -- added Jan. 2007
    
                if crop.time_for_harvest < -0.5:     #' negative value is a flag to extend until frost
                    #' XXXXXXXXX  Need to set to yesterday's kcb for a standard climate
    
                    foo.kcb = foo.kcb_yesterday #' use yesterday's kcb which should trace back to last valid day of stated growing season
                    OUT.debug('2kcb_daily():7 kcb %s\n' % foo.kcb)
                else:
                    foo.in_season = False
                    foo.stress_event = False #' reset severe stress event flag
                    OUT.debug('2kcb_daily(): InSeason3 %s\n' % (foo.in_season))


        #### crop.crop_curve_type Case 2 ####
        if crop.crop_curve_type == 3:
        #Case 3  #' %PL-EC,daysafter
            #' percent of time from PL to EFC for before EFC and days after EFC after EFC
    
            days_into_eason = float(foo_day.doy - foo.jd_start_cycle + 1)
            if days_into_eason < 1:     
                days_into_eason = days_into_eason + 365
            if crop.time_for_efc < 1:     
                crop.time_for_efc = 1 #' deal with values of zero or null - added Dec. 29, 2011, rga
            foo.nPL_EC = days_into_eason / crop.time_for_efc
            if foo.nPL_EC < 1:    
                int_PL_EC = min(foo.maxLinesInCropCurveTable - 1, int(foo.nPL_EC * 10.))
                #kcb = cropco_val(cCurveNo, int_PL_EC) + (nPL_EC * 10 - int_PL_EC) _
                #    * (cropco_val(cCurveNo, int_PL_EC + 1) - cropco_val(cCurveNo, int_PL_EC))
                foo.kcb = (
                    data.crop_coeffs[cCurveNo].data[int_PL_EC] +
                    (foo.nPL_EC * 10 - int_PL_EC) *
                    (data.crop_coeffs[cCurveNo].data[int_PL_EC+1] -
                     data.crop_coeffs[cCurveNo].data[int_PL_EC]))
                OUT.debug('2kcb_daily():8 kcb %s  nPL_EC %s  maxLinesInCropCurveTable %s  int_PL_EC %s\n' % (
                    foo.kcb, foo.nPL_EC, foo.maxLinesInCropCurveTable, int_PL_EC))
                foo.MAD = foo.MADini
            else:
                foo.MAD = foo.MADmid
                DaysafterEFC = days_into_eason - crop.time_for_efc
    
                #' In next line, make sure that "System.Math.Abs()" does not change exact value for time_for_harvest() and that it is taking absolute value.
                #' Use absolute value for time_for_harvest since neg means to run until frost (Jan. 2007). also changed to <= from <
    
                if DaysafterEFC <= abs(crop.time_for_harvest):    
                    nDaysafterEFC = DaysafterEFC / 10 + 11 #' start at array index = 11 for 0 days into full cover
                    int_PL_EC = min(foo.maxLinesInCropCurveTable - 1, int(nDaysafterEFC))
                    #kcb = cropco_val(cCurveNo, int_PL_EC) + (nDaysafterEFC - int_PL_EC) _
                    #    * (cropco_val(cCurveNo, int_PL_EC + 1) - cropco_val(cCurveNo, int_PL_EC))
                    foo.kcb = (
                        data.crop_coeffs[cCurveNo].data[int_PL_EC] +
                        (nDaysafterEFC - int_PL_EC) *
                        (data.crop_coeffs[cCurveNo].data[int_PL_EC+1] -
                         data.crop_coeffs[cCurveNo].data[int_PL_EC]))
                    OUT.debug('2kcb_daily():9 kcb %s\n' % foo.kcb)
                else:
                    #' beyond stated end of season
                    #' ------need provision to extend until frost termination if indicated for crop -- added Jan. 2007
    
                    if crop.time_for_harvest < -0.5:     #' negative value is a flag to extend until frost -- added Jan. 2007
    
                        #' XXXX need to set to yesterday's standard climate kcb
    
                        foo.kcb = foo.kcb_yesterday #' use yesterday's kcb which should trace back to last valid day of stated growing season
                        OUT.debug('2kcb_daily():10 kcb %s\n' % foo.kcb)
                    else:
                        foo.in_season = False
                        foo.stress_event = False #' reset severe stress event flag
                        OUT.debug('2kcb_daily(): InSeason4 %s\n' % (foo.in_season))


        #### crop.crop_curve_type Case 2 ####
        if crop.crop_curve_type == 4:
        #Case 4  #' %PL-Termintate
            #' percent of time from PL to end of season
            #' Note that type 4 kcb curve uses T30 to estimate GU
            #' and symmetry around July 15 to estimate total season length.
    
            #' estimate end of season
    
            #' If jd_start_cycle < 196 Then
            if foo.jd_start_cycle < crop.crop_gdd_trigger_doy + 195:    
                endOfSeason = (
                    crop.crop_gdd_trigger_doy + 195 +
                    (crop.crop_gdd_trigger_doy + 195 - foo.jd_start_cycle))
                length_of_season = 2 * (crop.crop_gdd_trigger_doy + 195 - foo.jd_start_cycle)
                #' endOfSeason = 196 + (196 - foo.jd_start_cycle)
                #' length_of_season = 2 * (196 - foo.jd_start_cycle)
            else:
                #PrintLine(lfNum, "Problem with estimated Season length, Crop_curve_type_4")
                #if not batchFlag:     MsgBox("Problem with estimated Season length, Crop_curve_type_4")
                print "Problem with estimated Season length, Crop_curve_type_4"
                sys.exit()
    
            #' put a minimum and maximum length on season for cheat grass (i= 47)
    
            if crop.crop_class_num == 47:     #' was 38, should have been 42   'corr. Jan 07
                if length_of_season < 60:
                    length_of_season = 60
                if length_of_season > 90:
                    length_of_season = 100

            days_into_eason = float(foo_day.doy - foo.jd_start_cycle)
            if days_into_eason < 1:     
                days_into_eason = days_into_eason + 365
            foo.nPL_EC = days_into_eason / length_of_season
            if foo.nPL_EC < 0.5:     #' assume season is split 50/50 for stress sensitivities for type 4
                foo.MAD = foo.MADini
            else:
                foo.MAD = foo.MADmid

            if foo.nPL_EC <= 1:    
                int_PL_EC = min(foo.maxLinesInCropCurveTable - 1, int(foo.nPL_EC * 10))
                foo.kcb = (
                    cropco_val(cCurveNo, int_PL_EC) +
                    (foo.nPL_EC * 10 - int_PL_EC) *
                    (cropco_val(cCurveNo, int_PL_EC + 1) - cropco_val(cCurveNo, int_PL_EC)))
                OUT.debug('2kcb_daily():11 kcb %s\n' % foo.kcb)
            else:
                #' beyond end of season
    
                foo.in_season = False
                foo.stress_event = False #' reset severe stress event flag
                OUT.debug('2kcb_daily(): InSeason5 %s\n' % (foo.in_season))
        #End Select



        #' Following is discounting for cold shock to alfalfa gets reset on Jan 1
        #' check for -2C or -3C temperature for peak alfalfa curve to begin discount
        #' discount kcb .01 or .005 per day since first occurrence of -2 C or -3 C in fall.

        #' peak alfalfa curve and both alfalfa crops (apply to all)(i=1,2,3) 
        if (crop.crop_class_num < 4 or
            (crop.crop_class_num > 3 and
             crop.crop_curve_name.upper() == "ALFALFA 1ST CYCLE")):     
            if foo_day.doy > crop.crop_gdd_trigger_doy + 211:    
                #' If DoY > 212:    
                if foo_day.tmin < -3 and foo.T2Days < 1:     #' first occurrence of -3C (was -2, now -3)
                    foo.T2Days = 1
            else:
                foo.T2Days = 0 #' reset discount timer if prior to August
            if foo.T2Days > 0:    
                foo.kcb = foo.kcb - foo.T2Days * 0.005 #'  was 0.01
                OUT.debug('2kcb_daily():12 kcb %s\n' % foo.kcb)
                if foo.kcb < 0.1:     
                    foo.kcb = 0.1
                    OUT.debug('2kcb_daily():13 kcb %s\n' % foo.kcb)
                foo.T2Days = foo.T2Days + 1

        #' Determine if killing frost to cut short - begin to check after August 1.

        #' If DoY > 212:    
        if foo_day.doy > crop.crop_gdd_trigger_doy + 211:    
            if foo_day.tmin < crop.killing_frost_temperature:    
                # All crops besides covers
                if crop.crop_class_num < 44 or crop.crop_class_num > 46:
                    #' If ctCount < 39 or ctCount > 41:         'was prior to Jan. 07
                    if foo.in_season:    
                        #PrintLine(lfNum, "Killing frost for crop " & Chr(9) & ctCount & Chr(9) & " of " & Chr(9) & Killing_frost_temperature(ctCount) & Chr(9) & " was found on " & Chr(9) & getDmiDate(dailyDates(sdays - 1)) & Chr(9) & "DOY " & DoY & Chr(9) & "TMin" & Chr(9) & TMin)
                        print "Killing frost for crop %s of %s was found on DOY %s" % (
                            crop.crop_class_num, crop.killing_frost_temperature, foo_day.doy)
                        foo.in_season = False
                        foo.stress_event = False #' reset severe stress event flag
                        OUT.debug('2kcb_daily(): in_season6 %s\n' % (foo.in_season))

                        #' print cutting information to a review file if alfalfa hay for select stations
                        if crop.crop_class_num == 2:     
                            output_str = ""
                            #output_str = output_str & DFormat(RefETIDs(ETCellCount), " #########") & DFormat(yearOfCalcs, "  ####") & DFormat(jd_start_cycle, " ###")
                            #For cutCount = 1 To 10
                            for cutCount in range(1,11):
                                foo.cutting[cutCount] = 0
                            #output_str = output_str & DFormat(DoY, " #####")
                            #PrintLine(cd2FNum, output_str)

                        if (crop.crop_class_num == 3 or
                            (crop.crop_class_num > 3 and
                             crop.crop_curve_name.upper() == "ALFALFA 1ST CYCLE")):     
                            output_str = ""
                            #output_str = output_str & DFormat(RefETIDs(ETCellCount), " #########") & DFormat(yearOfCalcs, "  ####") & DFormat(jd_start_cycle, " ###")
                            #For cutCount = 1 To 10
                            #    foo.cutting(cutCount) = 0
                            #Next cutCount
                            #output_str = output_str & DFormat(DoY, " #####")
                            #PrintLine(cb2FNum, output_str)


            #' print out cycles for alfalfa when there is no killing frost
            if (crop.crop_class_num == 2 or crop.crop_class_num == 3 or
                (crop.crop_class_num > 3 and
                 crop.crop_curve_name.upper() == "ALFALFA 1ST CYCLE")):
                if foo.in_season:    
                    #' end of year, no killing frost on alfalfa, but print cycle information to file
                    if foo_day.monthOfCalcs == 12 and foo_day.dayOfCalcs == 31:     
                        #PrintLine(lfNum, "No killing frost in year " & yearOfCalcs)
                        print "No killing frost in year ", foo_day.yearOfCalcs

                        #' print cutting information to a review file if alfalfa hay for select stations
                        if crop.crop_class_num == 2:     
                            output_str = ""
                            #output_str = output_str & DFormat(RefETIDs(ETCellCount), " #########") & DFormat(yearOfCalcs, "  ####") & DFormat(jd_start_cycle, " ###")
                            #For cutCount = 1 To 10
                            #    output_str = output_str & DFormat(cutting(cutCount), " ####")
                            #    foo.cutting[cutCount] = 0
                            #output_str = output_str & DFormat(DoY, " #####")
                            #PrintLine(cd2FNum, output_str)

                        if (crop.crop_class_num > 2 and
                            crop.crop_curve_name.upper() == "ALFALFA 1ST CYCLE"):
                            output_str = ""
                            #output_str = output_str & DFormat(RefETIDs(ETCellCount), " #########") & DFormat(yearOfCalcs, "  ####") & DFormat(jd_start_cycle, " ###")
                            #For cutCount = 1 To 10
                            #    output_str = output_str & DFormat(cutting(cutCount), " ####")
                            #    foo.cutting(cutCount) = 0
                            #Next
                            #output_str = output_str & DFormat(DoY, " #####")
                            #PrintLine(cb2FNum, output_str)

        # This kcb is not adjusted for climate 'keep track of this for debugging
        kcb_noadj = foo.kcb

        #' If DoY = 250:     return false

    #End If #' end of if season = 1

    #'  sub in winter time kcb if before or after season

    #'  kcb for winter time land use
    #'  44: Bare soil
    #'  45: Mulched soil, including grain stubble
    #'  46: Dormant turf/sod (winter time)
    #'   note: set Kcmax for winter time (Nov-Mar) and fc outside of this sub.

    if crop.crop_class_num == 44:     #' bare soil   
        foo.kcb = 0.1 #' was 0.2
        OUT.debug('2kcb_daily():14 kcb %s\n' % foo.kcb)
        foo.kcb_wscc[1] = foo.kcb #' remember this value to assign to regular crops, etc. during nonseason.
    if crop.crop_class_num == 45:     #' Mulched soil, including wheat stubble 
        foo.kcb = 0.1 #' was 0.2
        OUT.debug('2kcb_daily():15 kcb %s\n' % foo.kcb)
        foo.kcb_wscc[2] = foo.kcb
    if crop.crop_class_num == 46:     #' Dormant turf/sod (winter time) 
        foo.kcb = 0.1 #' was 0.3
        OUT.debug('2kcb_daily():16 kcb %s\n' % foo.kcb)
        foo.kcb_wscc[3] = foo.kcb

    # Open water evaporation "crops"
    # 55: Open water shallow systems (large ponds, streams)
    # 56: Open water deep systems (lakes, reservoirs)
    # 57: Open water small stock ponds
    # This section for WATER only
    if crop.crop_class_num > 54 and crop.crop_class_num < 58:      
        if crop.crop_class_num == 55:     #' Open water shallow systems (large ponds, streams) 
            if data.ctrl['refETType'] > 0:     #' Allen 3/6/08
                foo.kcb = 0.6 #' for ETr basis
                OUT.debug('2kcb_daily():17 kcb %s\n' % foo.kcb)
            else:
                # For ETo basis 'Allen 12/26/07....
                # Note that these values are substantially different from FAO56
                foo.kcb = 1.05
                OUT.debug('2kcb_daily():18 kcb %s\n' % foo.kcb)
        if crop.crop_class_num == 56:     #' Open water deep systems (lakes, reservoirs) 
            foo.kcb = 0.3 #' this is a place holder, since an aerodynamic function is used
            OUT.debug('2kcb_daily():19 kcb %s\n' % foo.kcb)
            etrf = open_water_evap.open_water_evap(foo, foo_day)
            foo.kcb = etrf
            OUT.debug('2kcb_daily():20 kcb %s\n' % foo.kcb)
        if crop.crop_class_num == 57:     #' Open water small stock ponds 
            if data.ctrl['refETType'] > 0:     #' Allen 3/6/08
                foo.kcb = 0.7 #' for ETr basis
                OUT.debug('2kcb_daily():21 kcb %s\n' % foo.kcb)
            else:
                foo.kcb = 0.85 #' for ETo basis 'Allen 12/26/07
                OUT.debug('2kcb_daily():22 kcb %s\n' % foo.kcb)
        foo.kc_act = foo.kcb #' water has only 'kcb'
        foo.kc_pot = foo.kcb
        # ETr changed to ETref 12/26/2007
        foo.etc_act = foo.kc_act * foo_day.ETref 
        foo.etc_pot = foo.kc_pot * foo_day.ETref
        foo.etc_bas = foo.kcb * foo_day.ETref
        # Keep track of this for debugging
        kcb_noadj = foo.kcb 
    else: #' added 12/26/07 to adjust kcb for ETo basis for climate
        # Keep track of this for debugging '12/26/07
        kcb_noadj = foo.kcb 

    # Save kcb value for use tomorrow in case curve needs to be extended until frost
    foo.kcb_yesterday = kcb_noadj

    # Adjustment to kcb moved here 2/21/08 to catch when during growing season
    if foo.Hcrop < 0.05:     
        foo.Hcrop = 0.05 #' m 'limit Hcrop for numerical stability

    # RHmin and U2 are computed in Climate subroutine

    #pprint(vars(foo_day))
    if data.ctrl['refETType'] > 0:     #' Allen 3/26/08
        #' ETr basis, therefore, no adjustment to kcb
        pass
    else:
        OUT.debug('2kcb_daily():23 kcb0 %s  U2 %s  RHmin %s  Hcrop %s\n' % (
            foo.kcb, foo_day.u2, foo_day.rhmin, foo.Hcrop))
        #' ******'12/26/07
        foo.kcb = (
            foo.kcb + (0.04 * (foo_day.u2 - 2) - 0.004 * (foo_day.rhmin - 45)) *
            (foo.Hcrop / 3) ** 0.3) 
        OUT.debug('2kcb_daily():23 kcb %s\n' % (foo.kcb))
    # Set up as yesterday's cummulative GDD for tommorrow
    foo.lcumGDD = foo.cumgdd
    
    #if debugFlag and ctCount = debugCrop and dailyDates(sdays - 1) = debugDate:    
    #    PrintLine(lfNum, ETCellIDs(ETCellCount) & Chr(9) & "kcb, etc in kcb_daily" & Chr(9) & getDmiDate(dailyDates(sdays - 1)) & Chr(9) & "crop no" & Chr(9) & ctCount)
    #    PrintLine(lfNum, "kcb" & Chr(9) & kcb & Chr(9) & "hcrop" & Chr(9) & Hcrop & Chr(9) & "cumgdd" & Chr(9) & cumgdd)
    #Return True
