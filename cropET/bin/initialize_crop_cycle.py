from pprint import pprint
import sys

import numpy as np

# from modCropET.vb
Deinitial = 10.0 #' mm initial depletion for first day of crop

class InitializeCropCycle:
    #' initialize for crops cycle
    #Private Sub InitializeCropCycle()
    hmin = 0.
    hmax = 0.
    Hcrop = 0
    Zrn = 0.
    Zrx = 0.
    AW = 0
    MADini = 0.
    MADmid = 0.0
    CN2 = 0.
    REW = 0.
    TEW2 = 0.
    TEW3 = 0.
    Kr2 = 0.
    fwstd = 0.
    Kcbmid = 0.
    Kcmax = 0.
    Kcmin = 0.
    Kcb = 0.
    Ks = 0.
    Ke = 0.
    #Kei = 0
    Kep = 0.
    fc = 0.
    fw = 0.
    #few = 0
    fwspec = 0.
    fwi = 0.
    TEW = 0.
    De = 0.
    Dep = 0.
    Depl_surface = 0.
    Dr = 0.
    AD = 0.
    #Ei = 0
    #Ep = 0
    cummevap = 0.
    cummevap1 = 0.
    Dpe = 0.
    Dpep = 0.
    Pinf = 0.
    Pinfyest = 0.
    #Ireal = 0
    Iauto = 0.
    #Imanual = 0
    #Ispecial = 0
    #Pnet4 = 0
    #Pnet3 = 0
    #Pnet2 = 0
    #Pnet1 = 0
    S4 = 0.
    S3 = 0.
    S2 = 0.
    S1 = 0.
    S = 0.
    #Kr = 0
    Zr = 0.
    simulatedIrr = 0.
    Kcact = 0.
    #Kcpot = 0
    ETcact = 0.
    ETcpot = 0.
    ETcbas = 0.
    E = 0.
    lDoy = 0
    frostflag = 0.
    penalty = 0.
    cumGDDPenalty = 0.
    lcumGDD = 0.
    RealStart = False
    Pressure = 0.0
    density = 0.
    ncumGDD = 0.
    nPL_EC = 0.
    MAD = 0.
    AW3 = 0.
    #Tei = 0
    #Ktprop = 1
    KTreducer = 1.
    #Kcmult = 1
    SRO = 0.
    Dpr = 0.
    jdStartCycle = 0
    ETref30 = 0.                 #' thirty day mean ETref  ' added 12/2007
    cumGDD = 0.0
    GDD = 0.0
    irrFlag = False
    InSeason = False            #' false if outside season, true if inside
    dormantSetupFlag = False
    cropSetupFlag = True        #' flag to setup crop parameter information
    cycle = 1.
    cumET = 0.
    cumP = 0.

    # [140609] TP added this, looks like its value comes from ComputeCropET(),
    # but needed for SetupDormant() below...
    totwatinZe = 0.0

    cumGDDAtPlanting = 0.0

    ### TP added these
    # from modCropET.vb
    #Private Const maxLinesInCropCurveTable As Short = 34
    maxLinesInCropCurveTable = 34
    # cutting(20) As Short
    cutting = np.zeros(20, dtype=np.int)

    ## [140820] not initialized in crop cycle in vb code, so 1st time-step
    ## was the final time step value from the previous crop.
    #Kcb_yesterday = 0.1
    Kcb_yesterday = 0.
    T2Days = 0.

    Kcb_wscc = np.zeros(4)  # kcb_daily.py
    ## [140801] cannot figure out how these are assigned 0.1 in the vb code,
    ## this is necessary to get Kcb right for non-growing season
    Kcb_wscc[1] = 0.1
    Kcb_wscc[2] = 0.1
    Kcb_wscc[3] = 0.1

    wtirr = 0.0   # ComputeCropET()

    # from modCropET.vb:    Private irrigMin As Double = 10 ' mm minimum net depth of
    # application for germination irrig., etc.
    irrigMin = 10.0

    #End Sub

    def __init__(self):
        """ """

#' Initialize some variables for beginning of crop seasons
#' Called in CropCycle if not in season and crop setup flag is true
#' Called in KcbDaily for startup/greenup type 1, 2, and 3 when startup conditions are met

    #Private Sub SetupCrop()
    #def SetupCrop(self, data, et_cell, crop):
    def SetupCrop(self, crop):
        #Dim DAW3, TAW3 As Double
    
        #' Zrdormant was never assigned a value - what's its purpose - dlk 10/26/2011 ???????????????????
    
        #Dim Zrdormant As Double = 0.0
        Zrdormant = 0.0
    
        #' SetupCrop is called from CropCycle if isseason is false and cropsetupflag is true
        #' thus only setup 1st time for crop (not each year)
        #' also called from KcbDaily each time GU/Plant date is reached, thus at growing season start
    
        self.hmin = crop.Starting_Crop_height  #' hminArray(ctCount)
        self.hmax = crop.Maximum_Crop_height   #' hmaxArray(ctCount)
        self.Zrn =  crop.Initial_rooting_depth #' ZrnArray(ctCount)
        self.Zrx =  crop.Maximum_rooting_depth #' ZrxArray(ctCount)
        self.Hcrop = self.hmin
        self.TEW = self.TEW2 #' find total evaporable water
        if self.TEW3 > self.TEW:  
            self.TEW = self.TEW3
        self.fwi = self.fwstd #' fw changed to fwi 8/10/06
        self.Iauto = 0
        self.simulatedIrr = 0
    
        #'  reinitialize Zr, but actCount for additions of DP into reserve (zrmax - zr) for rainfed
    
        #' Convert current moisture content below Zr at end of season to AW for new crop
        #' (into starting moisture content of layer 3).  This is required if Zrn <> Zrdormant
        #' Calc total water currently in layer 3
    
        DAW3 = self.AW3 * (self.Zrx - Zrdormant) #' AW3 is mm/m and DAW3 is mm in layer 3 (in case Zr<Zrx)
    
        #' layer 3 is soil depth between current rootzone (or dormant rootdepth) and max root for crop
        #' AW3 is set to 0 first time throught for crop.
    
        TAW3 = self.AW * (self.Zrx - Zrdormant) #' potential water in root zone below Zrdormant
    
        #' make sure that AW3 has been collecting DP from Zrdormant layer during winter
    
        if DAW3 < 0.:
            DAW3 = 0.
        if TAW3 < 0.:
            TAW3 = 0.
        if self.Zrn > Zrdormant: #' adjust depletion for extra starting root zone at plant or GU
            #' assume fully mixed layer 3
            self.Dr = self.Dr + (TAW3 - DAW3) * (self.Zrn - Zrdormant) / (self.Zrx - Zrdormant)
        else:
            if self.Zrx > self.Zrn:
                #' was, until 5/9/07: Dr = Dr - (TAW3 - DAW3) * (Zrdormant - Zrn) / (Zrx - Zrn) 'assume moisture right above Zrdormant is same as below
                #' following added 5/9/07
    
                DAW3 = DAW3 + (Zrdormant - self.Zrn) / Zrdormant * (self.AW * Zrdormant - self.Dr) #' enlarge dpeth of water
                self.Dr = self.Dr * self.Zrn / Zrdormant #' adjust Dr in proportion to Zrn/Zdormant and increase DAW3 and AW3
                self.AW3 = DAW3 / (self.Zrx - self.Zrn) #' the denom is layer 3 depth at start of season
                if self.AW3 < 0.:
                    self.AW3 = 0.
                if self.AW3 > self.AW:
                    self.AW3 = self.AW
            else:
                self.Dr = self.Dr
        if self.Dr < 0.:
            self.Dr = 0.
        self.Zr = self.Zrn #' initialize rooting depth at beginning of time  <----DO??? Need recalc on Reserve?
        self.cropSetupFlag = False


    #  assign characteristics for crop from crop Arrays - called by CropCycle just before time loop
    #Private Sub CropLoad()
    def CropLoad(self, data, et_cell, crop):
        #Dim cCurveNo, kCount As Short
        self.hmin = crop.Starting_Crop_height #' hminArray(ctCount)
        self.hmax = crop.Maximum_Crop_height  #' hmaxArray(ctCount)
        self.Zrn = crop.Initial_rooting_depth #' ZrnArray(ctCount)
        self.Zrx = crop.Maximum_rooting_depth #' ZrxArray(ctCount)
    
        self.De = Deinitial #' (10 mm) at start of new crop at beginning of time
        self.Dr = Deinitial #' (20 mm) at start of new crop at beginning of time
        self.Zr = self.Zrn #' initialize rooting depth at beginning of time
        self.Hcrop = self.hmin
        self.stressEvent = False
    
        #' Find maximum Kcb in array for this crop (used later in height calc)
        #' Kcbmid is the maximum Kcb found in the Kcb table read into program
        #' Following code was repaired to properly parse crop curve arrays on 7/31/2012.  dlk
    
        cCurveNo = crop.Crop_curve_number
        #print 'cCurveNo', cCurveNo
        #pprint(vars(data.crop_coeffs[cCurveNo]))
        self.Kcbmid = 0.
        ## bare soil 44, mulched soil 45, dormant turf/sod (winter) 46 do not have curve
        if cCurveNo > 0:
            self.Kcbmid = data.crop_coeffs[cCurveNo].max_value(self.Kcbmid)
        #print 'initialize_crop_cycle', self.Kcbmid, cCurveNo

        #' available water in soil
    
        #AW = station_WHC(ETCellCount) / 12 * 1000 #' in/ft to mm/m  'AWArray(ctCount)
        #MADini = MAD_initial(ctCount) #' MADiniArray(ctCount)
        #MADmid = MAD_midseason(ctCount) #' MADmidArray(ctCount)
        self.AW = et_cell.stn_whc / 12 * 1000.  #' in/ft to mm/m
        self.MADini = crop.MAD_initial
        self.MADmid = crop.MAD_midseason
    
        #' setup curve number for antecedent II condition

        #If station_HydroGroup(ETCellCount) = 1 Then CN2 = Curve_Number_coarse(ctCount)
        #If station_HydroGroup(ETCellCount) = 2 Then CN2 = Curve_Number_medium(ctCount)
        #If station_HydroGroup(ETCellCount) = 3 Then CN2 = Curve_Number_fine(ctCount)
        if et_cell.stn_hydrogroup == 1:   
            self.CN2 = crop.Curve_Number_coarse_soil
        if et_cell.stn_hydrogroup == 2:   
            self.CN2 = crop.Curve_Number_medium_soil
        if et_cell.stn_hydrogroup == 3:   
            self.CN2 = crop.Curve_Number_fine_soil
        self.CN2crop = self.CN2
    
        #' estimate readily evaporable water and total evaporable water from WHC
        #' REW is from regression of REW vs. AW from FAO-56 soils table
        #' R.Allen, August 2006, R2=0.92, n = 9
    
        self.REW = 0.8 + 54.4 * self.AW / 1000 #'REW is in mm and AW is in mm/m
    
        #' estimate TEW from AW and Ze = 0.1 m
        #' use FAO-56 based regression, since WHC from statso database does not have texture indication
        #' R.Allen, August 2006, R2=0.88, n = 9
    
        self.TEW = -3.7 + 166 * self.AW / 1000 #'TEW is in mm and AW is in mm/m
        if self.REW > (0.8 * self.TEW): 
            self.REW = 0.8 * self.TEW #'limit REW based on TEW
        self.TEW2 = self.TEW #' TEW2Array(ctCount)
        self.TEW3 = self.TEW #' TEW3Array(ctCount) '(no severely cracking clays in Idaho)
        self.Kr2 = 0 #' Kr2Array(ctCount)'(no severely cracking clays in Idaho)
        self.fwstd = crop.crop_fw #' fwarray(ctCount)
    
        #' Irrigation flag
    
        self.irrFlag = False #' no irrigations for this crop or station
        if crop.Irrigation_Flag > 0:
            self.irrFlag = True #' turn irrigation on for a generally 'irrigated' region
        if crop.Irrigation_Flag < 1:
            self.irrFlag = False #' turn irrigation off even in irrigated region if this crop has no flag
        if crop.Irrigation_Flag > 2:  #' added Jan 2007 to force grain and turf irrigation in rainfed region
            self.irrFlag = True #' turn irrigation on for specific irrigated crops even in nonirrigated region if this crop has flag=3
        self.SetupCrop(crop)



    def SetupDormant(self, data, et_cell, crop):
    #Private Sub SetupDormant()
        #Dim wscc As Short
        #Dim Zrdormant, DAW3, DAWroot, TAWroot, ze As Double

        #' Start of dormant season.
        #' set up for soil water reservoir during nongrowing season
        #' to collect soil moisture for next growing season

        #' also set for type of surface during nongrowing season

        #' called at termination of crop from CropCycle if inseason is false and dormantflag is true
        #' dormantflag set at GU each year.
        #' Thus will be called each year as soon as season = 0

        #pprint(vars(crop))
        wscc = crop.winter_surface_cover_class
        #sys.exit()

        #' wscc = 1 bare, 2 mulch, 3 sod

        #' Kcb for wintertime land use
        #'  44: Bare soil
        #'  45: Mulched soil, including wheat stubble
        #'  46: Dormant turf/sod (winter time)
        #'   note: set Kcmax for winter time (Nov-Mar) and fc outside of this sub.

        if wscc == 1:        #' bare soil
            self.Kcb = 0.1  #' was 0.2
            self.fc = 0
        if wscc == 2:        #' Mulched soil, including wheat stubble
            self.Kcb = 0.1  #' was 0.2
            self.fc = 0.4
        if wscc == 3:        #' Dormant turf/sod (winter time)
            self.Kcb = 0.2  #' was 0.3
            self.fc = 0.7   #' was 0.6

        #' setup curve number for antecedent II condition for winter covers
        #print wscc, data.crop_parameters[wscc+43-1] 
        if et_cell.stn_hydrogroup == 1:   
            self.CN2 = data.crop_parameters[wscc+43-1].Curve_Number_coarse_soil
        if et_cell.stn_hydrogroup == 2:   
            self.CN2 = data.crop_parameters[wscc+43-1].Curve_Number_medium_soil
        if et_cell.stn_hydrogroup == 3:   
            self.CN2 = data.crop_parameters[wscc+43-1].Curve_Number_fine_soil
        #If station_HydroGroup(ETCellCount) = 1 Then CN2w = Curve_Number_coarse(wscc + 43)
        #If station_HydroGroup(ETCellCount) = 2 Then CN2w = Curve_Number_medium(wscc + 43)
        #If station_HydroGroup(ETCellCount) = 3 Then CN2w = Curve_Number_fine(wscc + 43)

        #' assume that 'rooting depth' for dormant surfaces is 0.1 or 0.15 m
        #' this is depth that will be applied with a stress function to reduce Kcb

        Zrdormant = 0.1 #'  was 0.15

        #' Convert current moisture content of Zr layer (which should be at Zrx at end of season)
        #' into starting moisture content of layer 3
        #' This is done at end of season

        #' Calc total water currently in layer 3 (the dynamic layer below Zr)

        DAW3 = self.AW3 * (self.Zrx - self.Zr) #' AW is mm/m and DAW3 is mm in layer 3 (in case Zr<Zrx)

        #' Add TAW - Dr that is in root zone below Zrdormant.
        #' Assume fully mixed root zone inclding Zrdormant part

        TAWroot = self.AW * (self.Zr) #' potential water in root zone
        DAWroot = TAWroot - self.Dr #' actual water in root zone based on Dr at end of season
        if DAWroot < 0: 
            DAWroot = 0
        ze = 0.1 #' depth of evaporation layer   #' (This only works when Ze < Zrdormant)
        if Zrdormant < self.Zr:  #' reduce DAWroot by water in  evap layer and rest of zrdormant and then proportion

            #' determine water in Zrdormant layer
            #' combine water in Ze layer (1-fc fraction) to that in balance of Zrdormant depth
            #' need to mix Ze and Zrdormant zones.  Assume current Zr zone of crop just ended is fully mixed.
            #' totwatinZe is water in fc fraction of Ze.

            AWroot = DAWroot / self.Zr
            if Zrdormant > ze:
                totwatinZrdormant = (self.totwatinZe + AWroot * (Zrdormant - ze)) * (1 - self.fc) + AWroot * Zrdormant * fc
            else:
                #' was, until 5/9/07: totwatinZrdormant = (self.totwatinZe * (Ze - Zrdormant) / Ze) * (1 - fc) + AWroot * Zrdormant * fc
                totwatinZrdormant = (self.totwatinZe * (1 - (ze - Zrdormant) / ze)) * (1 - self.fc) + AWroot * Zrdormant * self.fc #' corrected

            #' This requires that Zrdormant > Ze.

            if DAWroot > totwatinZrdormant:
                DAWbelow = (DAWroot - totwatinZrdormant) #' proportionate water between Zrdormant and Zr
                #'  DAWbelow = DAWroot * (Zr - Zrdormant) / Zr #'actual water between Zrdormant and Zr

            else:
                DAWbelow = 0
            self.AW3 = (DAWbelow + DAW3) / (self.Zrx - Zrdormant) #' actual water in mm/m below Zrdormant
        else:
            self.AW3 = self.AW3 #' this should never happen, since Zrx for all crops > 0.15 m


        #' initialize Dr for dormant season
        #' Depletion below evaporation layer:

        #' Dr_below_Ze = (Dr - De) #' / (Zr - Ze) #'mm/m
        #' If Dr_below_Ze < 0 Then Dr_below_Ze = 0
        #' Dr = Dr_below_Ze * (Zrdormant - Ze) / (Zr - Ze) + De  #'assume fully mixed profile below Ze

        self.Dr = self.AW * Zrdormant - totwatinZrdormant

        #' set Zr for dormant season

        self.Zr = Zrdormant

        #' This value for Zr will hold constant all dormant season.  DP from Zr will be
        #' used to recharge Zrx - Zr zone
        #' make sure that GrowRoot is not called during dormant season

        self.fwi = self.fwstd #' fw changed to fwi 8/10/06
        self.Iauto = 0
        self.simulatedIrr = 0
        self.dormantSetupFlag = False

