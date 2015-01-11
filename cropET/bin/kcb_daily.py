import datetime
import sys
from pprint import pprint

import util

from open_water_evap import OpenWaterEvaporation


#    ' compute basal et

#    Private Function KcbDaily(ByVal T30 As Double) As Boolean
#        Dim jDoy, cutCount, cCurveNo, DaysafterEFC, longtermpl As Short
#        Dim intcumGDD, int_PL_EC As Integer
#        Dim ETrF, npl_ec100, nDaysafterEFC, cumGDD_term, cumGDD_EFC, cumGDDinseason As Double
#        Dim outputString As String

def KcbDaily(data, crop, et_cell, foo, foo_day, OUT):
    """ """
    #print 'in KcbDaily()'
    #print crop
    #pprint(vars(crop))
    #sys.exit()

    #' Following two variables are used in one equation each but are never assigned a value - dlk - ??????????????

    #Dim bcuttings, dcuttings As Double
    bcuttings = 0
    dcuttings = 0

    #Try
    #' determine if inside or outside growing period
    #' procedure for deciding start and return false of season.

    #cCurveNo = Crop_curve_number(ctCount)
    cCurveNo = crop.Crop_curve_number

    #' determination of start of season was rearranged April 12 2009 by R.Allen
    #' to correct computation error in limiting first and latest starts of season that
    #' caused a complete loss of crop start turnon.

    #' XXX Need to reset Realstart = false twice in Climate Sub.

    #' Flag for estimating start of season 1 = cumGDD, 2 = T30, 3 = date, 4 or 0 is on all the time
    OUT.debug('2KcbDaily():0 Flag_for_means_to_estimate_pl_or_gu %s\n' % (crop.Flag_for_means_to_estimate_pl_or_gu))
    OUT.debug('2KcbDaily():0 Kcb %s  Kcb_yesterday %s\n' % (foo.Kcb, foo.Kcb_yesterday))


    ############################################# Flag_for_means_to_estimate_pl_or_gu Case 1 #########
    #Select Case Flag_for_means_to_estimate_pl_or_gu(ctCount)
    #    Case 1
    if crop.Flag_for_means_to_estimate_pl_or_gu == 1:
        # print 'in KcbDaily().CASE 1'
        #' cumGDD

        #' only allow start flag to begin if < July 15 to prevent GU in fall after freezedown

        #' If DoY < 196 Then
        if foo_day.DoY < crop.cropGDDTriggerDoy+195:
            #' before finding date of startup using normal cumGDD, determine if it is after latest
            #' allowable start by checking to see if pl or gu need to be constrained based on long term means
            #' estimate date based on long term mean:
            #' prohibit specifying start of season as long term less 40 days when it is before that date.

            foo_day.cumGDD0LT[0] = foo_day.cumGDD0LT[1]
            longtermpl = 0
            #For jDoy = 1 To 366
            for jDoy in range(1,367):
                if foo_day.cumGDD0LT[jDoy] > crop.T30_for_pl_or_gu_or_cumGDD and foo_day.cumGDD0LT[jDoy-1] < crop.T30_for_pl_or_gu_or_cumGDD:
                    longtermpl = jDoy

            if longtermpl > 0:
                if foo_day.DoY > longtermpl + 40: #' check if getting too late in season
                    if not foo.RealStart:  #' season hasn't started yet
                        foo.jdStartCycle = foo_day.DoY #' was longtermpl + 40 ----4/30/2009
                        foo.RealStart = True

            if not foo.RealStart:     #' start of season has not yet been determined.  Look for it in normal fashion:
                if foo.cumGDD > crop.T30_for_pl_or_gu_or_cumGDD:     #' JH,RGA 4/13/09
                    #' if cumGDD > T30_for_pl_or_gu_or_cumGDD(ctCount) And lcumGDD < T30_for_pl_or_gu_or_cumGDD(ctCount) Then 'was until 4/13/09.  last part not needed now, with Realstart 'JH,RGA
                    #' planting or GU is today

                    #' This is modeled startup day, but check to see if it is too early

                    if longtermpl > 0:    
                        if foo_day.DoY < longtermpl - 40:     #' use +/- 40 days from longterm as constraint
                            foo.RealStart = False #' too early to start season
                            foo.jdStartCycle = longtermpl - 40
                            if foo.jdStartCycle < 1:     
                                foo.jdStartCycle = foo.jdStartCycle + 365
                        else:
                            foo.jdStartCycle = foo_day.DoY
                            foo.RealStart = True
                    else:
                        foo.jdStartCycle = foo_day.DoY
                        foo.RealStart = True

            #' if season start has been found then turn parameters on
            #' Look for day when DoY equals JDstartcycle
            #' Note that this requires that all days be present (no missing days)

            if foo_day.DoY == foo.jdStartCycle:    
                foo.RealStart = True
                foo.stressEvent = False #' reset severe stress event flag
                foo.InSeason = True #' turn season on
                foo.dormantSetupFlag = True #' set set up flag positive for next end of season
                foo.SetupCrop(crop) #' initialize rooting depth, etc. for crop
                foo.cycle = 1 #' first cycle for alfalfa

                #' some range grasses require backing up 10 days
                #' note that following logic will cause first 10 days to not be assigned to range grasses, but to winter cover
                #' but this code needs to be here because process (or DoY) can not go back in time

                if crop.Date_of_pl_or_gu < 0.0:    
                    foo.jdStartCycle = foo.jdStartCycle + int(crop.Date_of_pl_or_gu)
                    if foo.jdStartCycle < 1:     
                        foo.jdStartCycle = foo.jdStartCycle + 365

            OUT.debug('2KcbDaily():c1 InSeason %s  longtermpl %s  DoY %s  jdStartCycle %s\n' % (foo.InSeason, longtermpl, foo_day.DoY, foo.jdStartCycle))
            OUT.debug('2KcbDaily():c1 T30_for_pl_or_gu_or_cumGDD %s  cumGDD0LT156 %s  cumGDD0LT155 %s\n' % (crop.T30_for_pl_or_gu_or_cumGDD,
                foo_day.cumGDD0LT[156], foo_day.cumGDD0LT[155]))

    ############################################# Flag_for_means_to_estimate_pl_or_gu Case 2 #########
    #Case 2
    ####crop.Flag_for_means_to_estimate_pl_or_gu = 2
    elif crop.Flag_for_means_to_estimate_pl_or_gu == 2:
        #' Use T30 for startup
        #' Caution - need some contraints for oscillating T30 and for late summer
        #' Use first occurrence

        if foo_day.DoY < crop.cropGDDTriggerDoy+195:
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
                    #if foo_day.T30LT[jDoy] > crop.T30_for_pl_or_gu_or_cumGDD and foo_day.T30LT[jDoy-1] < crop.T30_for_pl_or_gu_or_cumGDD:
                    if T30LT[jDoy] > crop.T30_for_pl_or_gu_or_cumGDD and T30LT[jDoy-1] <= crop.T30_for_pl_or_gu_or_cumGDD:
                        longtermpl = jDoy
            OUT.debug('2KcbDaily():c2 longtermpl %s  T30LT(0) %s  T30LT(1) %s\n' % (longtermpl, T30LT[0], T30LT[1]))

            if longtermpl > 0:
                if foo_day.DoY > longtermpl+40:  #' check if getting too late in season
                    if not foo.RealStart:        #' season hasn't started yet
                        foo.jdStartCycle = foo_day.DoY #' longtermpl + 40 'it is unseasonably warm (too warm). Delay start ' set to Doy on 4/29/09 (nuts)
                        OUT.debug('2KcbDaily():c2a jdStartCycle %s\n' % (foo.jdStartCycle))
                        foo.RealStart = True    #' Harleys Rule
                        #PrintLine(lfNum, "exceeded 40 days past longterm T30 turnon")

            if not foo.RealStart:     #' start of season has not yet been determined.  Look for it in normal fashion:
                if foo_day.T30 > crop.T30_for_pl_or_gu_or_cumGDD:     #' 'JH,RGA 4/13/09
                    if longtermpl > 0:    
                        if foo_day.DoY < longtermpl - 40:     #' use +/- 40 days from longterm as constraint
                            foo.RealStart = False #' too early to start season
                            foo.jdStartCycle = longtermpl - 40
                            OUT.debug('2KcbDaily():c2b jdStartCycle %s\n' % (foo.jdStartCycle))
                            if foo.jdStartCycle < 1:     
                                foo.jdStartCycle = foo.jdStartCycle + 365
                                OUT.debug('2KcbDaily():c2c jdStartCycle %s\n' % (foo.jdStartCycle))
                        else:
                            foo.jdStartCycle = foo_day.DoY
                            OUT.debug('2KcbDaily():c2d jdStartCycle %s\n' % (foo.jdStartCycle))
                            foo.RealStart = True
                    else:
                        foo.jdStartCycle = foo_day.DoY
                        OUT.debug('2KcbDaily():c2e jdStartCycle %s\n' % (foo.jdStartCycle))
                        foo.RealStart = True

            #' if season start has been found then turn parameters on
            #' Look for day when DoY equals JDstartcycle
            #' Note that this requires that all days be present (no missing days)

            if foo_day.DoY == foo.jdStartCycle:    
                foo.RealStart = True
                foo.stressEvent = False #' reset severe stress event flag
                foo.InSeason = True #' turn season on
                foo.dormantSetupFlag = True #' set set up flag positive for next end of season
                foo.SetupCrop(crop) #' initialize rooting depth, etc. for crop
                foo.cycle = 1 #' first cycle for alfalfa

                #' some range grasses require backing up 10 days
                #' note that following logic will cause first 10 days to not be assigned to range grasses, but to winter cover
                #' but this code needs to be here because process (or DoY) can not go back in time

                if crop.Date_of_pl_or_gu < 0.0:    
                    foo.jdStartCycle = foo.jdStartCycle + int(crop.Date_of_pl_or_gu)
                    OUT.debug('2KcbDaily():c2f jdStartCycle %s\n' % (foo.jdStartCycle))
                    if foo.jdStartCycle < 1:     
                        foo.jdStartCycle = foo.jdStartCycle + 365
                        OUT.debug('2KcbDaily():c2g jdStartCycle %s\n' % (foo.jdStartCycle))

            OUT.debug('2KcbDaily():c2 jdStartCycle %s  DoY %s  RealStart %s\n' % (foo.jdStartCycle, foo_day.DoY, foo.RealStart))
            OUT.debug('2KcbDaily():c2 T30 %s  T30_for_pl_or_gu_or_cumGDD %s  Date_of_pl_or_gu %s\n' % (foo_day.T30, crop.T30_for_pl_or_gu_or_cumGDD, crop.Date_of_pl_or_gu))
            OUT.debug('2KcbDaily():c2 InSeason %s\n' % (foo.InSeason))
    
            # print 'in KcbDaily().CASE 2', crop.cropGDDTriggerDoy, longtermpl, foo.jdStartCycle, foo_day.DoY

    ############################################# Flag_for_means_to_estimate_pl_or_gu Case 3 #########
    #Case 3
    ###crop.Flag_for_means_to_estimate_pl_or_gu = 3
    elif crop.Flag_for_means_to_estimate_pl_or_gu == 3:
        # print 'in KcbDaily().CASE 3'
        #' a date is used for planting or greenup

        Mo = int(crop.Date_of_pl_or_gu)
        dayMo = (crop.Date_of_pl_or_gu - Mo) * 30.4
        if dayMo < 0.5:     
            dayMo = 15

        # print Mo, dayMo, crop.Date_of_pl_or_gu 
        # vb code (DateSerial) apparently resolves Mo=0 to 12
        # JDL = DateSerial(yearOfCalcs, Mo, dayMo).DayOfYear
        if Mo == 0:
            Mo = 12
        JDL = datetime.datetime(foo_day.yearOfCalcs,Mo,dayMo).timetuple().tm_yday
        #OUT.debug('2KcbDaily():c3 Date_of_pl_or_gu %s  Mo %s  JDL %s\n' % (crop.Date_of_pl_or_gu, Mo, JDL))

        #' modified next statement to get winter grain to et and irrigate in first year of run.  dlk  08/16/2012

        if foo_day.DoY == JDL or (foo_day.sdays == 1 and JDL >= crop.cropGDDTriggerDoy):    
            foo.jdStartCycle = JDL
            foo.stressEvent = False #' reset severe stress event flag
            foo.InSeason = True #' turn season on
            foo.dormantSetupFlag = True #' set set up flag positive for next end of season
            foo.SetupCrop(crop) #' initialize rooting depth, etc. for crop

        OUT.debug('2KcbDaily():c3 InSeason %s\n' % (foo.InSeason))
    ############################################# Flag_for_means_to_estimate_pl_or_gu Case 4 #########
    #Case 4
    ####crop.Flag_for_means_to_estimate_pl_or_gu = 4
    elif crop.Flag_for_means_to_estimate_pl_or_gu == 4:
        # print 'in KcbDaily().CASE 4'
        #' flag = 4 or 0 ('crop' is on all time)

        foo.InSeason = True #' turn season on
        if foo_day.DoY == crop.cropGDDTriggerDoy:     
            foo.stressEvent = False #' reset severe stress event flag if first of year
        foo.dormantSetupFlag = True #' set set up flag positive for next end of season

        OUT.debug('2KcbDaily():c4 InSeason %s\n' % (foo.InSeason))
    #Case Else
    else:
        # print 'in KcbDaily().CASE else'
        #' flag = 4 or 0 ('crop' is on all time)

        foo.InSeason = True #' turn season on
        if foo_day.DoY == crop.cropGDDTriggerDoy:     
            foo.stressEvent = False #' reset severe stress event flag if first of year
        foo.dormantSetupFlag = True #' set set up flag positive for next end of season

        OUT.debug('2KcbDaily():cE InSeason %s\n' % (foo.InSeason))
    ############################################# END Case  ##########################



    #cCurveNo = Crop_curve_number(ctCount)
    foo.MAD = foo.MADmid  #' set MAD to MADmid universally at the start.  Value will be changed later.  R.Allen 12/14/2011
    ############################################# InSeason  ##########################
    if foo.InSeason:     #' <------This Kcb loop only conducted if inside growing season
        #' crop curve type: 1 = NcumGDD, 2 = %PL-EC, 3 = %PL-EC,daysafter, 4 = %PL-Term

        ############################################# crop.Crop_curve_type Case 1 #########
        #    Select Case Crop_curve_type(ctCount)
        if crop.Crop_curve_type == 1:
        #Case 1  #' NCGDD
            #' normalized cumulative growing degree days
    
            if foo.jdStartCycle == foo_day.DoY:     
                foo.cumGDDAtPlanting = foo.cumGDD
            cumGDDinseason = foo.cumGDD - foo.cumGDDAtPlanting
            cumGDDinseason = max(0, cumGDDinseason)
            cumGDD_EFC = crop.cumGDD_For_EFC
            cumGDD_term = crop.cumGDD_For_Termination
    
            #' increase cumGDD_term in SW Idaho to create longer late season
            #' use value of cropFlags, if greater than 1 as scaler
    
            ### This apparently does nothing, since crop_flags only either 0 or 1
            # skip for now
            #' <-------NOTE:  ONLY FUNCTIONAL FOR FLAG > 1.0, changed to >0, 1/2007
            #If cropFlags(ETCellCount, ctCount) > 0.001:     
            if et_cell.crop_flags[crop.cropclass_num] > 0.001:
                #' <---- Jan 2007, invoke always to catch flag < or > 1
                cumGDD_term = cumGDD_term * et_cell.crop_flags[crop.cropclass_num] 
            #' cumGDD_EFC is not effected, only period following EFC

            s = '2KcbDaily():1P cropclass_num %s cropOneToggle %s cycle %s\n'
            OUT.debug(s % (crop.cropclass_num, data.ctrl['cropOneToggle'], foo.cycle))

            #' special case for ALFALFA hay (typical, beef or dairy) '<------ specific value for crop number ' 4/09
            #If (ctCount = 1 and cropOneToggle = 1) or ctCount = 2 or ctCount = 3 or (ctCount > 3 and ccName.Equals("ALFALFA 1ST CYCLE")):     
            if (crop.cropclass_num == 1 and data.ctrl['cropOneToggle'] == 1) or crop.cropclass_num == 2 or crop.cropclass_num == 3 or (crop.cropclass_num > 3 and crop.Crop_curve_name == "Alfalfa 1st cycle"):
                cumGDD_term = crop.cumGDD_For_EFC               #' termination for first cycle for alfalfa is in EFC cumGDD
                if foo.cycle > 1:                               #' termination for all other alfalfa cycles is stored in termination cumGDD.
                    cumGDD_EFC = crop.cumGDD_For_Termination    #' the 'term' cumGDD is for second cycles and on
                    cumGDD_term = crop.cumGDD_For_Termination   #' CHECK to see if cumGDD should be incremented with cycle 3/08
                    if crop.cropclass_num == 2:                             #' dairy hay.  Determine which of three Kcb curves to use
                        #if foo.cycle < et_cell.dairyCuttings + 0.01 - 1:     #' this could be - 2 if at least one, and sometimes two final cycles are desired
                        if foo.cycle < dcuttings + 0.01 - 1:     #' this could be - 2 if at least one, and sometimes two final cycles are desired
                            cCurveNo = crop.Crop_curve_number + 1 #' increment alfalfa curve to intermediate cycle
                        else: #' R.Allen 4/1/08
                            cCurveNo = crop.Crop_curve_number + 2 #' increment alfalfa curve to fall/winter cycle
                        OUT.debug('2KcbDaily():1a dairyCuttings %s  cycle %s  Crop_curve_number %s  cCurveNo %s\n' % (dcuttings, foo.cycle, crop.Crop_curve_number, cCurveNo))

                    #' typical and beef hay.  Determine which of three Kcb curves to use
                    if crop.cropclass_num == 1 or crop.cropclass_num == 3 or (crop.cropclass_num > 3 and crop.Crop_curve_name == "Alfalfa 1st cycle"):
                        #if foo.cycle < et_cell.beefCuttings + 0.01 - 1:     #' this could be - 2 if at least one, and sometimes two final cycles are desired
                        if foo.cycle < bcuttings + 0.01 - 1:     #' this could be - 2 if at least one, and sometimes two final cycles are desired
                            cCurveNo = crop.Crop_curve_number + 1 #' increment alfalfa curve to intermediate cycle
                        else:
                            cCurveNo = crop.Crop_curve_number + 2 #' increment alfalfa curve to fall/winter cycle
                        OUT.debug('2KcbDaily():1b beefCuttings %s  cycle %s  Crop_curve_number %s  cCurveNo %s\n' % (bcuttings, foo.cycle, crop.Crop_curve_number, cCurveNo))
    
                #' If ctCount = 2 and cycle > 3:     'dairy alfalfa '<------ specific value for crop number
                #'  ccurveno = Crop_curve_number(ctCount) + 2  'end cycle (going into fall/winter)
                #' End If
                #' If ctCount = 3 and cycle > 2:     'beef alfalfa '<------ specific value for crop number
                #'  ccurveno = Crop_curve_number(ctCount) + 2  'end cycle (going into fall/winter)
                #' End If
                #' Debug.Writeline "cycle, cumGDD_EFC, cumGDD_term, ccurveno "; cycle, cumGDD_EFC, cumGDD_term, ccurveno
                #' return false

            if cumGDDinseason < cumGDD_EFC:    
                # print 'KcbDaily:in cumGDDinseason < cumGDD_EFC'
                foo.ncumGDD = cumGDDinseason / cumGDD_EFC
                intcumGDD = min(foo.maxLinesInCropCurveTable - 1, int(foo.ncumGDD * 10))
                #Kcb = cropco_val(cCurveNo, intcumGDD) + (foo.ncumGDD * 10 - intcumGDD) * (cropco_val(cCurveNo, intcumGDD + 1) - cropco_val(cCurveNo, intcumGDD))
                foo.Kcb = data.crop_coeffs[cCurveNo].data[intcumGDD]+ (foo.ncumGDD * 10 - intcumGDD) * (data.crop_coeffs[cCurveNo].data[intcumGDD+1] - data.crop_coeffs[cCurveNo].data[intcumGDD])
                OUT.debug('2KcbDaily():1 Kcb %s  ncumGDD %s  intcumGDD %s\n' % (foo.Kcb, foo.ncumGDD, intcumGDD))
                OUT.debug('2KcbDaily():1 cumGDDinseason %s  cumGDD_EFC %s\n' % (cumGDDinseason, cumGDD_EFC))
                OUT.debug('2KcbDaily():1 cumGDD %s  cumGDDAtPlanting %s\n' % (foo.cumGDD, foo.cumGDDAtPlanting))
                foo.MAD = foo.MADini #' set management allowable depletion also
                #If intcumGDD Mod 10 = 0:    
                    #' Debug.Writeline "DoY, foo.ncumGDD Kcb "; DoY, foo.ncumGDD, Kcb
                    #' return false
            else:
                if cumGDDinseason < cumGDD_term:     #' function is same as for < EFC
                    # print 'KcbDaily:in cumGDDinseason < cumGDD_term'
                    foo.ncumGDD = cumGDDinseason / cumGDD_EFC #' use ratio of cumGDD for EFC
    
                    #' increase ncumGDD term in SW Idaho to stretch Kcb curve during late season
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
                    if intcumGDD < lentry:     #' more entries in Kcb array
                        #Kcb = cropco_val(cCurveNo, intcumGDD) + (ncumGDD * 10 - intcumGDD) * (cropco_val(cCurveNo, intcumGDD + 1) - cropco_val(cCurveNo, intcumGDD))
                        foo.Kcb = data.crop_coeffs[cCurveNo].data[intcumGDD]+ (foo.ncumGDD * 10 - intcumGDD) * (data.crop_coeffs[cCurveNo].data[intcumGDD+1] - data.crop_coeffs[cCurveNo].data[intcumGDD])
                        OUT.debug('2KcbDaily():2 Kcb %s  intcumGDD %s  cCurveNo %s  lentry %s\n' % (foo.Kcb, intcumGDD, cCurveNo, lentry))
                        #If ctCount = 7:     #' <------ specific value for crop number
                        #    #' Debug.Writeline "after EFC, DoY foo.ncumGDD, intcumGDD, Kcb "; DoY, ncumGDD, intcumGDD, Kcb
                        #    #' return false
                    else:
                        #' hold Kcb equal to last entry until either cumGDD_termination is exceeded or killing frost
                        foo.Kcb = data.crop_coeffs[cCurveNo].data[lentry]
                        OUT.debug('2KcbDaily():3 Kcb %s  intcumGDD %s  cCurveNo %s  lentry %s\n' % (foo.Kcb, intcumGDD, cCurveNo, lentry))

                else:
                    #' end of season by exceeding cumGDD for termination.  set flag to 0
    
                    foo.InSeason = False #' <------note that for cumGDD based crops, there is no extension past computed end
                    OUT.debug('2KcbDaily(): InSeason0 %s\n' % (foo.InSeason))
                    foo.stressEvent = False #' reset severe stress event flag
                    #' special case for ALFALFA '<------ specific value for crop number  1 added 4/18/08
                    #If ctCount = 1 or ctCount = 2 or ctCount = 3 or (ctCount > 3 and ccName.Equals("ALFALFA 1ST CYCLE")):     
                    #if crop.cropclass_num == 1 or crop.cropclass_num == 2 or crop.cropclass_num == 3 or (crop.cropclass_num > 3 and crop.Crop_curve_name == "Alfalfa 1st cycle"):
                    if crop.cropclass_num in [1,2,3] or (crop.cropclass_num > 3 and crop.Crop_curve_name == "Alfalfa 1st cycle"):
                        #' (three curves for cycles, two cumGDD's for first and other cycles)
    
                        #' remember gu, cutting and frost dates for alfalfa crops for review
                        foo.cutting[foo.cycle] = foo_day.DoY
    
                        #' increment and reset for next cycle
                        foo.cycle = foo.cycle + 1
                        foo.InSeason = True
                        OUT.debug('2KcbDaily(): InSeason1 %s\n' % (foo.InSeason))
                        foo.cumGDDAtPlanting = foo.cumGDD #' set basis for next cycle
    
                        #' Following 2 lines added July 13, 2009 by RGA to reset alfalfa height to minimum each new cycle
                        foo.Hcrop = foo.hmin
    
                        #' and to set Kcb to initial Kcb value for first day following cutting.
    
                        #Kcb = cropco_val(cCurveNo, 0)
                        foo.Kcb = data.crop_coeffs[cCurveNo].data[0]
                        OUT.debug('2KcbDaily():4 Kcb %s  cumGDDAtPlanting %s\n' % (foo.Kcb, foo.cumGDDAtPlanting))

                #' first alfalfa crop (typical production alfalfa) where Kcb is reduced   '4/18/08...
                if (crop.cropclass_num == 1 and data.ctrl['cropOneToggle'] == 1):     
                    foo.Kcb = foo.Kcb * data.ctrl['alfalfa1Reducer'] #' xxx...apply only if cropOneToggle is set (4/09)
                    OUT.debug('2KcbDaily():5 Kcb %s\n' % foo.Kcb)
            daysIntoSeason = float(foo_day.DoY - foo.jdStartCycle + 1) #' use this here only to invoke a total length limit
            if daysIntoSeason < 1:    
                daysIntoSeason = daysIntoSeason + 365
            if crop.time_for_harvest > 10:     #' real value for length constraint (used for spring grain)
                if daysIntoSeason > crop.time_for_harvest:     #' the cumGDD basis has exceeded length constraint.
                    #' end season.  set flag to 0
                    foo.InSeason = False #' This section added Jan. 2007
                    OUT.debug('2KcbDaily(): InSeason2 %s\n' % (foo.InSeason))
                    foo.stressEvent = False #' reset severe stress event flag
                    #PrintLine(lfNum, "Year " & yearOfCalcs & " Crop no: " & ctCount & ", " & cropn & " Reached Time Limit: " & time_for_harvest(ctCount))
                    #' return false
            #' If yearOfCalcs < 1952:     PrintLine(lfNum, getDmiDate(dailyDates(sdays - 1)) & Chr(9) & "KcbDaily kcb" & Chr(9) & Kcb)



        ############################################# crop.Crop_curve_type Case 2 #########
        if crop.Crop_curve_type == 2:
        #Case 2  #' %PL-EC
            #' percent of time from PL to EFC for all season
    
            daysIntoSeason = float(foo_day.DoY - foo.jdStartCycle + 1)
            if daysIntoSeason < 1:     
                daysIntoSeason = daysIntoSeason + 365
            if crop.time_for_EFC < 1:     
                crop.time_for_EFC = 1 #' deal with values of zero or null - added Dec. 29, 2011, rga
            foo.nPL_EC = daysIntoSeason / crop.time_for_EFC
            npl_ec100 = foo.nPL_EC * 100
            if foo.nPL_EC < 1:    
                foo.MAD = foo.MADini
            else:
                foo.MAD = foo.MADmid
    
            #' In next line, make sure that "System.Math.Abs()" does not change exact value for time_for_harvest() and that it is taking absolute value.
            #' Use absolute value for time_for_harvest since neg means to run until frost (Jan. 2007). also changed to <= from <
    
            OUT.debug('2KcbDaily():6_7 npl_ec100 %s  time_for_harvest %s abs_time_for_harvest %s\n' % (npl_ec100, 
                crop.time_for_harvest, abs(crop.time_for_harvest)))
            #if npl_ec100 <= abs(crop.time_for_harvest):    
            if round(npl_ec100,4) <= abs(crop.time_for_harvest):    
                OUT.debug('2KcbDaily():6 nPL_EC0 %s  maxLinesInCropCurveTable %s\n' % (foo.nPL_EC, foo.maxLinesInCropCurveTable))
                int_PL_EC = min(foo.maxLinesInCropCurveTable - 1., int(foo.nPL_EC * 10.))
                foo.Kcb = data.crop_coeffs[cCurveNo].data[int_PL_EC]+ (foo.nPL_EC * 10 - int_PL_EC) * (data.crop_coeffs[cCurveNo].data[int_PL_EC+1] - data.crop_coeffs[cCurveNo].data[int_PL_EC])
                OUT.debug('2KcbDaily():6 Kcb %s  int_PL_EC %s  nPL_EC %s\n' % (foo.Kcb, int_PL_EC, foo.nPL_EC))
                OUT.debug('2KcbDaily():6 daysIntoSeason %s  time_for_EFC %s\n' % (daysIntoSeason, crop.time_for_EFC))
            else:
                #' beyond stated end of season
                #' ------need provision to extend until frost termination if indicated for crop -- added Jan. 2007
    
                if crop.time_for_harvest < -0.5:     #' negative value is a flag to extend until frost
                    #' XXXXXXXXX  Need to set to yesterday's Kcb for a standard climate
    
                    foo.Kcb = foo.Kcb_yesterday #' use yesterday's Kcb which should trace back to last valid day of stated growing season
                    OUT.debug('2KcbDaily():7 Kcb %s\n' % foo.Kcb)
                else:
                    foo.InSeason = False
                    foo.stressEvent = False #' reset severe stress event flag
                    OUT.debug('2KcbDaily(): InSeason3 %s\n' % (foo.InSeason))


        ############################################# crop.Crop_curve_type Case 2 #########
        if crop.Crop_curve_type == 3:
        #Case 3  #' %PL-EC,daysafter
            #' percent of time from PL to EFC for before EFC and days after EFC after EFC
    
            daysIntoSeason = float(foo_day.DoY - foo.jdStartCycle + 1)
            if daysIntoSeason < 1:     
                daysIntoSeason = daysIntoSeason + 365
            if crop.time_for_EFC < 1:     
                crop.time_for_EFC = 1 #' deal with values of zero or null - added Dec. 29, 2011, rga
            foo.nPL_EC = daysIntoSeason / crop.time_for_EFC
            if foo.nPL_EC < 1:    
                int_PL_EC = min(foo.maxLinesInCropCurveTable - 1, int(foo.nPL_EC * 10.))
                #Kcb = cropco_val(cCurveNo, int_PL_EC) + (nPL_EC * 10 - int_PL_EC) _
                #    * (cropco_val(cCurveNo, int_PL_EC + 1) - cropco_val(cCurveNo, int_PL_EC))
                foo.Kcb = data.crop_coeffs[cCurveNo].data[int_PL_EC]+ (foo.nPL_EC * 10 - int_PL_EC) * (data.crop_coeffs[cCurveNo].data[int_PL_EC+1] - data.crop_coeffs[cCurveNo].data[int_PL_EC])
                OUT.debug('2KcbDaily():8 Kcb %s  nPL_EC %s  maxLinesInCropCurveTable %s  int_PL_EC %s\n' % (foo.Kcb, foo.nPL_EC, foo.maxLinesInCropCurveTable, int_PL_EC))
                foo.MAD = foo.MADini
            else:
                foo.MAD = foo.MADmid
                DaysafterEFC = daysIntoSeason - crop.time_for_EFC
    
                #' In next line, make sure that "System.Math.Abs()" does not change exact value for time_for_harvest() and that it is taking absolute value.
                #' Use absolute value for time_for_harvest since neg means to run until frost (Jan. 2007). also changed to <= from <
    
                if DaysafterEFC <= abs(crop.time_for_harvest):    
                    nDaysafterEFC = DaysafterEFC / 10 + 11 #' start at array index = 11 for 0 days into full cover
                    int_PL_EC = min(foo.maxLinesInCropCurveTable - 1, int(nDaysafterEFC))
                    #Kcb = cropco_val(cCurveNo, int_PL_EC) + (nDaysafterEFC - int_PL_EC) _
                    #    * (cropco_val(cCurveNo, int_PL_EC + 1) - cropco_val(cCurveNo, int_PL_EC))
                    foo.Kcb = data.crop_coeffs[cCurveNo].data[int_PL_EC]+ (nDaysafterEFC - int_PL_EC) * (data.crop_coeffs[cCurveNo].data[int_PL_EC+1] - data.crop_coeffs[cCurveNo].data[int_PL_EC])
                    OUT.debug('2KcbDaily():9 Kcb %s\n' % foo.Kcb)
                else:
                    #' beyond stated end of season
                    #' ------need provision to extend until frost termination if indicated for crop -- added Jan. 2007
    
                    if crop.time_for_harvest < -0.5:     #' negative value is a flag to extend until frost -- added Jan. 2007
    
                        #' XXXX need to set to yesterday's standard climate Kcb
    
                        foo.Kcb = foo.Kcb_yesterday #' use yesterday's Kcb which should trace back to last valid day of stated growing season
                        OUT.debug('2KcbDaily():10 Kcb %s\n' % foo.Kcb)
                    else:
                        foo.InSeason = False
                        foo.stressEvent = False #' reset severe stress event flag
                        OUT.debug('2KcbDaily(): InSeason4 %s\n' % (foo.InSeason))


        ############################################# crop.Crop_curve_type Case 2 #########
        if crop.Crop_curve_type == 4:
        #Case 4  #' %PL-Termintate
            #' percent of time from PL to end of season
            #' Note that type 4 Kcb curve uses T30 to estimate GU
            #' and symmetry around July 15 to estimate total season length.
    
            #' estimate end of season
    
            #' If jdStartCycle < 196 Then
            if foo.jdStartCycle < crop.cropGDDTriggerDoy + 195:    
                endOfSeason = crop.cropGDDTriggerDoy + 195 + (crop.cropGDDTriggerDoy + 195 - foo.jdStartCycle)
                lengthOfSeason = 2 * (crop.cropGDDTriggerDoy + 195 - foo.jdStartCycle)
                #' endOfSeason = 196 + (196 - foo.jdStartCycle)
                #' lengthOfSeason = 2 * (196 - foo.jdStartCycle)
            else:
                #PrintLine(lfNum, "Problem with estimated Season length, Crop_curve_type_4")
                #if not batchFlag:     MsgBox("Problem with estimated Season length, Crop_curve_type_4")
                print "Problem with estimated Season length, Crop_curve_type_4"
                sys.exit()
    
            #' put a minimum and maximum length on season for cheat grass (i= 47)
    
            if crop.cropclass_num == 47:     #' was 38, should have been 42  '<------ specific value for crop number 'corr. Jan 07
                if lengthOfSeason < 60:     lengthOfSeason = 60
                if lengthOfSeason > 90:     lengthOfSeason = 100

            daysIntoSeason = float(foo_day.DoY - foo.jdStartCycle)
            if daysIntoSeason < 1:     
                daysIntoSeason = daysIntoSeason + 365
            foo.nPL_EC = daysIntoSeason / lengthOfSeason
            if foo.nPL_EC < 0.5:     #' assume season is split 50/50 for stress sensitivities for type 4
                foo.MAD = foo.MADini
            else:
                foo.MAD = foo.MADmid

            if foo.nPL_EC <= 1:    
                int_PL_EC = min(foo.maxLinesInCropCurveTable - 1, int(foo.nPL_EC * 10))
                foo.Kcb = cropco_val(cCurveNo, int_PL_EC) + (foo.nPL_EC * 10 - int_PL_EC) * (cropco_val(cCurveNo, int_PL_EC + 1) - cropco_val(cCurveNo, int_PL_EC))
                OUT.debug('2KcbDaily():11 Kcb %s\n' % foo.Kcb)
            else:
                #' beyond end of season
    
                foo.InSeason = False
                foo.stressEvent = False #' reset severe stress event flag
                OUT.debug('2KcbDaily(): InSeason5 %s\n' % (foo.InSeason))
        #End Select



        #' Following is discounting for cold shock to alfalfa gets reset on Jan 1
        #' check for -2C or -3C temperature for peak alfalfa curve to begin discount
        #' discount Kcb .01 or .005 per day since first occurrence of -2 C or -3 C in fall.

        #' peak alfalfa curve and both alfalfa crops (apply to all)(i=1,2,3) '<------ specific value for crop number
        if crop.cropclass_num < 4 or (crop.cropclass_num > 3 and crop.Crop_curve_name == "Alfalfa 1st cycle"):     
            if foo_day.DoY > crop.cropGDDTriggerDoy + 211:    
                #' If DoY > 212:    
                if foo_day.TMin < -3 and foo.T2Days < 1:     #' first occurrence of -3C (was -2, now -3)
                    foo.T2Days = 1
            else:
                foo.T2Days = 0 #' reset discount timer if prior to August
            if foo.T2Days > 0:    
                foo.Kcb = foo.Kcb - foo.T2Days * 0.005 #'  was 0.01
                OUT.debug('2KcbDaily():12 Kcb %s\n' % foo.Kcb)
                if foo.Kcb < 0.1:     
                    foo.Kcb = 0.1
                    OUT.debug('2KcbDaily():13 Kcb %s\n' % foo.Kcb)
                foo.T2Days = foo.T2Days + 1

        #' Determine if killing frost to cut short - begin to check after August 1.

        #' If DoY > 212:    
        if foo_day.DoY > crop.cropGDDTriggerDoy + 211:    
            if foo_day.TMin < crop.Killing_frost_temperature:    
                if crop.cropclass_num < 44 or crop.cropclass_num > 46:     #' <------ specific value for crop number (all crops besides covers)
                    #' If ctCount < 39 or ctCount > 41:       '<------ specific value for crop number  'was prior to Jan. 07
                    if foo.InSeason:    
                        #PrintLine(lfNum, "Killing frost for crop " & Chr(9) & ctCount & Chr(9) & " of " & Chr(9) & Killing_frost_temperature(ctCount) & Chr(9) & " was found on " & Chr(9) & getDmiDate(dailyDates(sdays - 1)) & Chr(9) & "DOY " & DoY & Chr(9) & "TMin" & Chr(9) & TMin)
                        print "Killing frost for crop ", crop.cropclass_num, " of ",  crop.Killing_frost_temperature, " was found on ..." 
                        foo.InSeason = False
                        foo.stressEvent = False #' reset severe stress event flag
                        OUT.debug('2KcbDaily(): InSeason6 %s\n' % (foo.InSeason))

                        #' print cutting information to a review file if alfalfa hay for select stations

                        if crop.cropclass_num == 2:     #' <------ specific value for crop number

                            outputString = ""
                            #outputString = outputString & DFormat(RefETIDs(ETCellCount), " #########") & DFormat(yearOfCalcs, "  ####") & DFormat(jdStartCycle, " ###")
                            #For cutCount = 1 To 10
                            for cutCount in range(1,11):
                                foo.cutting[cutCount] = 0
                            #outputString = outputString & DFormat(DoY, " #####")
                            #PrintLine(cd2FNum, outputString)

                        #if crop.cropclass_num == 3 or (crop.cropclass_num > 3 and ccName.Equals("ALFALFA 1ST CYCLE")):     #' <------ specific value for crop number
                        if crop.cropclass_num == 3 or (crop.cropclass_num > 3 and crop.Crop_curve_name == "Alfalfa 1st cycle"):     #' <------ specific value for crop number
                            outputString = ""
                            #outputString = outputString & DFormat(RefETIDs(ETCellCount), " #########") & DFormat(yearOfCalcs, "  ####") & DFormat(jdStartCycle, " ###")
                            #For cutCount = 1 To 10
                            #    foo.cutting(cutCount) = 0
                            #Next cutCount
                            #outputString = outputString & DFormat(DoY, " #####")
                            #PrintLine(cb2FNum, outputString)


            #' print out cycles for alfalfa when there is no killing frost
            if crop.cropclass_num == 2 or crop.cropclass_num == 3 or (crop.cropclass_num > 3 and crop.Crop_curve_name == "Alfalfa 1st cycle"):    
                if foo.InSeason:    
                    #' end of year, no killing frost on alfalfa, but print cycle information to file
                    if foo_day.monthOfCalcs == 12 and foo_day.dayOfCalcs == 31:     
                        #PrintLine(lfNum, "No killing frost in year " & yearOfCalcs)
                        print "No killing frost in year ", foo_day.yearOfCalcs

                        #' print cutting information to a review file if alfalfa hay for select stations

                        if crop.cropclass_num == 2:     #' <------ specific value for crop number
                            outputString = ""
                            #outputString = outputString & DFormat(RefETIDs(ETCellCount), " #########") & DFormat(yearOfCalcs, "  ####") & DFormat(jdStartCycle, " ###")
                            #For cutCount = 1 To 10
                            #    outputString = outputString & DFormat(cutting(cutCount), " ####")
                            #    foo.cutting[cutCount] = 0
                            #outputString = outputString & DFormat(DoY, " #####")
                            #PrintLine(cd2FNum, outputString)

                        if crop.cropclass_num > 2 and crop.Crop_curve_name == "Alfalfa 1st cycle":     #' <------ specific value for crop number
                            outputString = ""
                            #outputString = outputString & DFormat(RefETIDs(ETCellCount), " #########") & DFormat(yearOfCalcs, "  ####") & DFormat(jdStartCycle, " ###")
                            #For cutCount = 1 To 10
                            #    outputString = outputString & DFormat(cutting(cutCount), " ####")
                            #    foo.cutting(cutCount) = 0
                            #Next
                            #outputString = outputString & DFormat(DoY, " #####")
                            #PrintLine(cb2FNum, outputString)

        Kcb_noadj = foo.Kcb #' this Kcb is not adjusted for climate 'keep track of this for debugging

        #' If DoY = 250:     return false

    #End If #' end of if season = 1

    #'  sub in winter time Kcb if before or after season

    #'  Kcb for winter time land use
    #'  44: Bare soil
    #'  45: Mulched soil, including grain stubble
    #'  46: Dormant turf/sod (winter time)
    #'   note: set Kcmax for winter time (Nov-Mar) and fc outside of this sub.

    if crop.cropclass_num == 44:     #' bare soil   '<------ specific value for crop number
        foo.Kcb = 0.1 #' was 0.2
        OUT.debug('2KcbDaily():14 Kcb %s\n' % foo.Kcb)
        foo.Kcb_wscc[1] = foo.Kcb #' remember this value to assign to regular crops, etc. during nonseason.
    if crop.cropclass_num == 45:     #' Mulched soil, including wheat stubble '<------ specific value for crop number
        foo.Kcb = 0.1 #' was 0.2
        OUT.debug('2KcbDaily():15 Kcb %s\n' % foo.Kcb)
        foo.Kcb_wscc[2] = foo.Kcb
    if crop.cropclass_num == 46:     #' Dormant turf/sod (winter time) '<------ specific value for crop number
        foo.Kcb = 0.1 #' was 0.3
        OUT.debug('2KcbDaily():16 Kcb %s\n' % foo.Kcb)
        foo.Kcb_wscc[3] = foo.Kcb

    #'  Open water evaporation "crops"
    #'  55: Open water shallow systems (large ponds, streams)
    #'  56: Open water deep systems (lakes, reservoirs)
    #'  57: Open water small stock ponds

    if crop.cropclass_num > 54 and crop.cropclass_num < 58:     #' <------ specific value for crop number (this section for WATER only)
        if crop.cropclass_num == 55:     #' Open water shallow systems (large ponds, streams) '<------ specific value for crop number
            if data.ctrl['refETType'] > 0:     #' Allen 3/6/08
                foo.Kcb = 0.6 #' for ETr basis
                OUT.debug('2KcbDaily():17 Kcb %s\n' % foo.Kcb)
            else:
                foo.Kcb = 1.05 #' for ETo basis 'Allen 12/26/07....note that these values are substantially different from FAO56 ****
                OUT.debug('2KcbDaily():18 Kcb %s\n' % foo.Kcb)
        if crop.cropclass_num == 56:     #' Open water deep systems (lakes, reservoirs) '<------ specific value for crop number
            foo.Kcb = 0.3 #' this is a place holder, since an aerodynamic function is used
            OUT.debug('2KcbDaily():19 Kcb %s\n' % foo.Kcb)
            ETrF = OpenWaterEvaporation(foo, foo_day)
            foo.Kcb = ETrF
            OUT.debug('2KcbDaily():20 Kcb %s\n' % foo.Kcb)
        if crop.cropclass_num == 57:     #' Open water small stock ponds '<------ specific value for crop number
            if data.ctrl['refETType'] > 0:     #' Allen 3/6/08
                foo.Kcb = 0.7 #' for ETr basis
                OUT.debug('2KcbDaily():21 Kcb %s\n' % foo.Kcb)
            else:
                foo.Kcb = 0.85 #' for ETo basis 'Allen 12/26/07
                OUT.debug('2KcbDaily():22 Kcb %s\n' % foo.Kcb)
        foo.Kcact = foo.Kcb #' water has only 'Kcb'
        foo.Kcpot = foo.Kcb
        foo.ETcact = foo.Kcact * foo_day.ETref #' ETr changed to ETref 12/26/2007
        foo.ETcpot = foo.Kcpot * foo_day.ETref
        foo.ETcbas = foo.Kcb * foo_day.ETref
        Kcb_noadj = foo.Kcb #' keep track of this for debugging
    else: #' added 12/26/07 to adjust Kcb for ETo basis for climate
        Kcb_noadj = foo.Kcb #' keep track of this for debugging '12/26/07

    #' save Kcb value for use tomorrow in case curve needs to be extended until frost
    foo.Kcb_yesterday = Kcb_noadj

    #' Adjustment to Kcb moved here 2/21/08 to catch when during growing season
    if foo.Hcrop < 0.05:     
        foo.Hcrop = 0.05 #' m 'limit Hcrop for numerical stability

    #' RHmin and U2 are computed in Climate subroutine

    #pprint(vars(foo_day))
    if data.ctrl['refETType'] > 0:     #' Allen 3/26/08
        #' ETr basis, therefore, no adjustment to Kcb
        pass
    else:
        OUT.debug('2KcbDaily():23 Kcb0 %s  U2 %s  RHmin %s  Hcrop %s\n' % (foo.Kcb, foo_day.U2, foo_day.RHmin, foo.Hcrop))
        foo.Kcb = foo.Kcb + (0.04 * (foo_day.U2 - 2) - 0.004 * (foo_day.RHmin - 45)) * (foo.Hcrop / 3) ** 0.3 #' ******'12/26/07
        OUT.debug('2KcbDaily():23 Kcb %s\n' % (foo.Kcb))
    foo.lcumGDD = foo.cumGDD #' set up as yesterday's cummulative GDD for tommorrow
    #if debugFlag and ctCount = debugCrop and dailyDates(sdays - 1) = debugDate:    
    #    PrintLine(lfNum, ETCellIDs(ETCellCount) & Chr(9) & "Kcb, etc in KcbDaily" & Chr(9) & getDmiDate(dailyDates(sdays - 1)) & Chr(9) & "crop no" & Chr(9) & ctCount)
    #    PrintLine(lfNum, "kcb" & Chr(9) & Kcb & Chr(9) & "hcrop" & Chr(9) & Hcrop & Chr(9) & "cumgdd" & Chr(9) & cumGDD)
    #Return True
"""
"""

#Catch ex As Exception
#    If Not batchFlag Then MsgBox(Err.Description & " occurred computing KcbDaily for ET Cell " & ETCellCount & " and crop " & ctCount & ".")
#    PrintLine(lfNum, Err.Description & " occurred computing KcbDaily for ET Cell " & ETCellCount & " and crop " & ctCount & ".")
#    Return False
#End Try
#End Function

