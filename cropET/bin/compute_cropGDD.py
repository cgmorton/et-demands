import util
from pprint import pprint


    #' Compute crop growing degree days

    #Private Sub ComputeCropGDD()
    #    Dim cCurveNo, idx As Short
    #    Dim esTMax, esTDew, ETreflost As Double
    #    Dim TMaxOriginal, TMeanl, TMinl, TMaxl As Double


def ComputeCropGDD(data, crop, foo, foo_day, OUT):
    """ """
    #print 'in ComputeCropGDD()'
    #' Following RHmin and U2 was moved here to be hit for each crop type.  June 2, 2009 Allen
    #' 12/2007, calculate RHmin and U2 for use in computing Kcmax and Kcbo for ETo based ETc ***

    '''
        TDew, TMaxOriginal, wind, sdays, ETref, ETref30

        ETrefarray(30) 
    '''
    #pprint(vars(foo_day))

    #TMaxOriginal = originalTMax(sdays - 1)
    if foo_day.TDew < -90 or foo_day.TMaxOriginal < -90:
        RHmin = 30.0
    else:
        esTDew = util.aFNEs(foo_day.TDew)
        #' for now do not consider SVP over ice (it was not used in ETr or ETo computations, anyway)
        esTMax = util.aFNEs(foo_day.TMaxOriginal) 
        RHmin = esTDew / esTMax * 100

    foo_day.RHmin = min(RHmin, 100.0)
    # --> move to ComputeCropET()
    foo_day.U2 = foo_day.wind #' at 2 m height

    #' calculate 30 day ETr each year
    #' shift entries in 30 day array to add today's ETref

    ETreflost = 0.0
    if foo_day.sdays > 30:
        #ETreflost = ETrefarray(1)
        #For idx = 1 To 29 #' idx = 1 is 30 days ago
        ETreflost = foo_day.ETrefarray[0]
        for idx in range(29):   #' idx = 1 is 30 days ago
            foo_day.ETrefarray[idx] = foo_day.ETrefarray[idx + 1]
        foo_day.ETrefarray[29] = foo_day.ETref
        foo.ETref30 = foo.ETref30 + (foo_day.ETref - ETreflost) / 30.
    else:
        foo_day.ETrefarray[foo_day.sdays-1] = foo_day.ETref
        foo.ETref30 = (foo.ETref30 * (foo_day.sdays - 1) + foo_day.ETref) / foo_day.sdays
        #foo.ETref30 = (foo.ETref30 * (foo_day.sdays) + foo_day.ETref) / (foo_day.sdays + 1)
    #print 'ETref30', foo.ETref30, foo_day.sdays, foo_day.ETref


    #' reset cumGDD if new year
    #' for all crops, but winter grain, reset cumGDD counter on cropGDDTriggerDoy (formerly hard wired to Jan 1 or Oct 1)
    #' ctCount = 13 and 14 are winter grain (irrigated and nonirrigated)

    #' winter grain '<------ specific value for crop number, changed to two ww crops Jan 07
    #If ctCount = 13 Or ctCount = 14 Or ccName.Equals("WINTER WHEAT") Then 
    #if crop.Crop_curve_number in [13,14] or crop.Crop_curve_name == 'WINTER WHEAT':
    if crop.cropclass_num in [13,14] or 'WINTER' in crop.Crop_curve_name:
        if foo.lDoy < crop.cropGDDTriggerDoy and foo_day.DoY >= crop.cropGDDTriggerDoy:
            foo.cumGDD = 0.0
            foo.jdStartCycle = 0    #' DoY 0 - reset planting date also
            foo.RealStart = False   #' April 12, 2009 rga
            foo.InSeason = False    #' July 30, 20120 dlk
            #' PrintLine(lfNum, "Setting winter grain off " & Chr(9) & dailyDates(sdays - 1) & ", doy " & Chr(9) & DoY)
        foo.lDoy = foo_day.DoY
    else:
        if foo.lDoy > crop.cropGDDTriggerDoy+199 and foo_day.DoY < crop.cropGDDTriggerDoy+199:
            foo.cumGDD = 0.0
            foo.jdStartCycle = 0    #' DoY 0 - reset planting date also
            foo.RealStart = False   #' April 12, 2009 rga
            foo.InSeason = False    #' July 30, 20120 dlk
        foo.lDoy = foo_day.DoY

    s = '0ComputeCropGDD(): ETref30 %s  sdays %s  ETref %s  ETreflost %s jdStartCycle %s  Crop_curve_number %s  cropclass_num %s  InSeason %s\n'
    t = (foo.ETref30, foo_day.sdays, foo_day.ETref, ETreflost, foo.jdStartCycle, crop.Crop_curve_number, crop.cropclass_num, foo.InSeason) 
    OUT.debug(s % t)

    #' calculate cumGDD since trigger date

    #cCurveNo = Crop_curve_number(ctCount)
    #If cCurveNo > 0 Then #' only needed if a crop
    if crop.Crop_curve_number > 0:    #' only needed if a crop
        #' use general GDD basis except for corn (crop types 7 thru 10), which require 86-50 method.
        #' evalute winter grain separately because of penalties during winter
        #' Development of winter grain is followed through winter,
        #' beginning with an assumed October 1 planting in Northern hemisphere
        #' Any periods during winter with favorable growing conditions are assumed to advance development of winter grain crop subject to following conditions:
        #'   Initial GDD calculation is TMean - Tbase if TMean > Tbase, or 0 otherwise.
        #'   GDD is set to zero if TMin for that day is less than -3 C to actCount for negative impacts of freezing.
        #'   In addition, subtract 10 GDD from daily GDD if TMin of previous day < -5 C to actCount for retardation (stunning) that carries over into next day.
        #'   Minimum adjusted GDD for any day is 0.
        #'   If TMin for day is < -25 C (very cold temperature) and no snow cover, burning of leaves is assumed to occur and cumGDD is reduced.
        #'      On first day following -25 C TMin, cumGDD prior to day is reduced by 30%.

        #If ctCount = 13 Or ctCount = 14 Or ccName.Equals("WINTER WHEAT") Then 
        #' winter grain '<------ specific value for crop number
        #if crop.Crop_curve_number in [13,14] or crop.Crop_curve_name == 'WINTER WHEAT':
        if crop.cropclass_num in [13,14] or crop.Crop_curve_name == 'WINTER WHEAT':
            foo.GDD = 0.0
            if foo_day.TMin < -4.0:       #' no growth if <-3C (was -3, now -4)
                foo.GDD = 0.0
            else:
                if foo_day.TMean > crop.Tbase:  #' simple method for all other crops
                    foo.GDD = foo_day.TMean - crop.Tbase
            foo.GDD = foo.GDD - foo.penalty
            #If penalty > 0 Then PrintLine(lfNum, "Winter grain penalty on " & getDmiDate(dailyDates(sdays - 1)) & " is " & penalty & " GDD with penalty is " & GDD)
            foo.penalty = 0.0
            foo.GDD = max(foo.GDD, 0.0)
            foo.cumGDD = foo.cumGDD + foo.GDD - foo.cumGDDPenalty
            foo.cumGDDPenalty = 0.0
            foo.cumGDD = max(0.0, foo.cumGDD)
            #print '->', foo.GDD, foo.penalty

            #' set up for tommorrow's penalties for winter grain

            if foo_day.TMin < -10:
                foo.penalty = 5.0
            else:
                foo.penalty = 0.0 #' set up for tomorrow's penalty for low TMin today (was 10), TMin was -5
            if foo_day.TMin < -25:
                if foo_day.Snowdepth <= 0:
                    foo.cumGDDPenalty = foo.cumGDD * 0.1 #' was 0.3  'burn back on winter grain from severe cold if no snow cover


        else: #' all other crops
            if crop.Tbase < 0:  #' corn
                TMaxl = foo_day.TMax
                TMinl = foo_day.TMin
                if foo_day.TMax > 30: TMaxl = 30 #' TMax and TMin are subject to Tbase limits for corn
                if foo_day.TMin > 30: TMinl = 30 #' and to maximum limits for corn
                if foo_day.TMax < -crop.Tbase: TMaxl = -crop.Tbase #' sub Tbase since it is artificially neg. for corn as a flag
                if foo_day.TMin < -crop.Tbase: TMinl = -crop.Tbase
                TMeanl = 0.5 * (TMaxl + TMinl)
                foo.cumGDD = foo.cumGDD + TMeanl + crop.Tbase  #' add Tbase since it is artificially set negative as an indicator
            else:
                if foo_day.TMean > crop.Tbase:  #' simple method for all other crops
                    foo.GDD = foo_day.TMean - crop.Tbase
                    foo.cumGDD = foo.cumGDD + foo.GDD

    s = '0ComputeCropGDD(): GDD %s  cumGDD %s\n'
    t = (foo.GDD, foo.cumGDD) 
    OUT.debug(s % t)
    #End If #' of crop with crop curve
"""
"""
    #If debugFlag And ctCount = debugCrop And dailyDates(sdays - 1) = debugDate Then
    #    PrintLine(lfNum, ETCellIDs(ETCellCount) & Chr(9) & "Second Crop GDD" & Chr(9) & getDmiDate(dailyDates(sdays - 1)) & Chr(9) & "crop no" & Chr(9) & ctCount & ", " & cropn)
    #    PrintLine(lfNum, "jdstartcycle" & Chr(9) & jdStartCycle & Chr(9) & "cumgdd" & Chr(9) & cumGDD & Chr(9) & "GDD" & Chr(9) & GDD & Chr(9) & "From TMean " & TMean)
    #End If
    #End Sub

