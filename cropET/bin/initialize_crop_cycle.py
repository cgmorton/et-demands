from pprint import pprint
import sys

import numpy as np

# from modCropET.vb
de_initial = 10.0 #' mm initial depletion for first day of crop

class InitializeCropCycle:
    """Initialize for crops cycle"""
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
    kcb_mid = 0.
    kc_max = 0.
    kc_min = 0.
    kcb = 0.
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
    depl_surface = 0.
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
    simulated_irr = 0.
    kc_act = 0.
    #kc_pot = 0
    etc_act = 0.
    etc_pot = 0.
    etc_bas = 0.
    E = 0.
    lDoy = 0
    frost_flag = 0.
    penalty = 0.
    cumgdd_penalty = 0.
    lcumGDD = 0.
    real_start = False
    pressure = 0.0
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
    jd_start_cycle = 0
    ETref30 = 0.                 #' thirty day mean ETref  ' added 12/2007
    cumgdd = 0.0
    gdd = 0.0
    irr_flag = False
    in_season = False            #' false if outside season, true if inside
    dormant_setup_flag = False
    crop_setup_flag = True        #' flag to setup crop parameter information
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
    #kcb_yesterday = 0.1
    kcb_yesterday = 0.
    T2Days = 0.

    kcb_wscc = np.zeros(4)  # kcb_daily.py
    ## [140801] cannot figure out how these are assigned 0.1 in the vb code,
    ## this is necessary to get kcb right for non-growing season
    kcb_wscc[1] = 0.1
    kcb_wscc[2] = 0.1
    kcb_wscc[3] = 0.1

    wtirr = 0.0   # compute_crop_et()

    # from modCropET.vb:    Private irrigMin As Double = 10 ' mm minimum net depth of
    # application for germination irrig., etc.
    irrigMin = 10.0

    def __init__(self):
        """ """

    # Initialize some variables for beginning of crop seasons
    # Called in crop_cycle if not in season and crop setup flag is true
    # Called in kcb_daily for startup/greenup type 1, 2, and 3 when startup conditions are met
    def setup_crop(self, crop):
        #' zr_dormant was never assigned a value - what's its purpose - dlk 10/26/2011 ???????????????????
    
        #Dim zr_dormant As Double = 0.0
        zr_dormant = 0.0
    
        #' SetupCrop is called from CropCycle if isseason is false and cropsetupflag is true
        #' thus only setup 1st time for crop (not each year)
        #' also called from kcb_daily each time GU/Plant date is reached, thus at growing season start
        self.hmin = crop.starting_crop_height  #' hminArray(ctCount)
        self.hmax = crop.maximum_crop_height   #' hmaxArray(ctCount)
        self.Zrn = crop.initial_rooting_depth  #' ZrnArray(ctCount)
        self.Zrx = crop.maximum_rooting_depth  #' ZrxArray(ctCount)
        self.Hcrop = self.hmin
        self.TEW = self.TEW2 #' find total evaporable water
        if self.TEW3 > self.TEW:  
            self.TEW = self.TEW3
        self.fwi = self.fwstd #' fw changed to fwi 8/10/06
        self.Iauto = 0
        self.simulated_irr = 0
    
        #'  reinitialize Zr, but actCount for additions of DP into reserve (zrmax - zr) for rainfed
    
        #' Convert current moisture content below Zr at end of season to AW for new crop
        #' (into starting moisture content of layer 3).  This is required if Zrn <> zr_dormant
        #' Calc total water currently in layer 3
    
        DAW3 = self.AW3 * (self.Zrx - zr_dormant) #' AW3 is mm/m and DAW3 is mm in layer 3 (in case Zr<Zrx)
    
        #' layer 3 is soil depth between current rootzone (or dormant rootdepth) and max root for crop
        #' AW3 is set to 0 first time throught for crop.
    
        TAW3 = self.AW * (self.Zrx - zr_dormant) #' potential water in root zone below zr_dormant
    
        # Make sure that AW3 has been collecting DP from zr_dormant layer during winter
        if DAW3 < 0.:
            DAW3 = 0.
        if TAW3 < 0.:
            TAW3 = 0.
        if self.Zrn > zr_dormant:
            #' adjust depletion for extra starting root zone at plant or GU
            #' assume fully mixed layer 3
            self.Dr = self.Dr + (TAW3 - DAW3) * (self.Zrn - zr_dormant) / (self.Zrx - zr_dormant)
        else:
            if self.Zrx > self.Zrn:
                #' was, until 5/9/07: Dr = Dr - (TAW3 - DAW3) * (zr_dormant - Zrn) / (Zrx - Zrn) 'assume moisture right above zr_dormant is same as below
                #' following added 5/9/07
                DAW3 = DAW3 + (zr_dormant - self.Zrn) / zr_dormant * (self.AW * zr_dormant - self.Dr) #' enlarge dpeth of water
                self.Dr = self.Dr * self.Zrn / zr_dormant #' adjust Dr in proportion to Zrn/Zdormant and increase DAW3 and AW3
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
        self.crop_setup_flag = False

    def crop_load(self, data, et_cell, crop):
        """Assign characteristics for crop from crop Arrays

        Called by CropCycle just before time loop
        """
        self.hmin = crop.starting_crop_height #' hminArray(ctCount)
        self.hmax = crop.maximum_crop_height  #' hmaxArray(ctCount)
        self.Zrn = crop.initial_rooting_depth #' ZrnArray(ctCount)
        self.Zrx = crop.maximum_rooting_depth #' ZrxArray(ctCount)
    
        self.De = de_initial #' (10 mm) at start of new crop at beginning of time
        self.Dr = de_initial #' (20 mm) at start of new crop at beginning of time
        self.Zr = self.Zrn #' initialize rooting depth at beginning of time
        self.Hcrop = self.hmin
        self.stressEvent = False
    
        #' Find maximum kcb in array for this crop (used later in height calc)
        #' kcb_mid is the maximum kcb found in the kcb table read into program
        #' Following code was repaired to properly parse crop curve arrays on 7/31/2012.  dlk
    
        cCurveNo = crop.crop_curve_number
        #print 'cCurveNo', cCurveNo
        #pprint(vars(data.crop_coeffs[cCurveNo]))
        self.kcb_mid = 0.
        ## bare soil 44, mulched soil 45, dormant turf/sod (winter) 46 do not have curve
        if cCurveNo > 0:
            self.kcb_mid = data.crop_coeffs[cCurveNo].max_value(self.kcb_mid)
        #print 'initialize_crop_cycle', self.kcb_mid, cCurveNo

        #' available water in soil
    
        #AW = station_WHC(ETCellCount) / 12 * 1000 #' in/ft to mm/m  'AWArray(ctCount)
        #MADini = MAD_initial(ctCount) #' MADiniArray(ctCount)
        #MADmid = MAD_midseason(ctCount) #' MADmidArray(ctCount)
        self.AW = et_cell.stn_whc / 12 * 1000.  #' in/ft to mm/m
        self.MADini = crop.mad_initial
        self.MADmid = crop.mad_midseason
    
        #' setup curve number for antecedent II condition

        #If station_HydroGroup(ETCellCount) = 1 Then CN2 = Curve_Number_coarse(ctCount)
        #If station_HydroGroup(ETCellCount) = 2 Then CN2 = Curve_Number_medium(ctCount)
        #If station_HydroGroup(ETCellCount) = 3 Then CN2 = Curve_Number_fine(ctCount)
        if et_cell.stn_hydrogroup == 1:   
            self.CN2 = crop.curve_number_coarse_soil
        if et_cell.stn_hydrogroup == 2:   
            self.CN2 = crop.curve_number_medium_soil
        if et_cell.stn_hydrogroup == 3:   
            self.CN2 = crop.curve_number_fine_soil
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
    
        self.irr_flag = False #' no irrigations for this crop or station
        if crop.irrigation_flag > 0:
            self.irr_flag = True #' turn irrigation on for a generally 'irrigated' region
        if crop.irrigation_flag < 1:
            self.irr_flag = False #' turn irrigation off even in irrigated region if this crop has no flag
        if crop.irrigation_flag > 2:  #' added Jan 2007 to force grain and turf irrigation in rainfed region
            self.irr_flag = True #' turn irrigation on for specific irrigated crops even in nonirrigated region if this crop has flag=3
        self.setup_crop(crop)

    def setup_dormant(self, data, et_cell, crop):
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

        #' kcb for wintertime land use
        #'  44: Bare soil
        #'  45: Mulched soil, including wheat stubble
        #'  46: Dormant turf/sod (winter time)
        #'   note: set Kcmax for winter time (Nov-Mar) and fc outside of this sub.

        if wscc == 1:        #' bare soil
            self.kcb = 0.1  #' was 0.2
            self.fc = 0
        if wscc == 2:        #' Mulched soil, including wheat stubble
            self.kcb = 0.1  #' was 0.2
            self.fc = 0.4
        if wscc == 3:        #' Dormant turf/sod (winter time)
            self.kcb = 0.2  #' was 0.3
            self.fc = 0.7   #' was 0.6

        #' setup curve number for antecedent II condition for winter covers
        #print wscc, data.crop_parameters[wscc+43-1] 
        if et_cell.stn_hydrogroup == 1:   
            self.CN2 = data.crop_parameters[wscc+43-1].curve_number_coarse_soil
        if et_cell.stn_hydrogroup == 2:   
            self.CN2 = data.crop_parameters[wscc+43-1].curve_number_medium_soil
        if et_cell.stn_hydrogroup == 3:   
            self.CN2 = data.crop_parameters[wscc+43-1].curve_number_fine_soil
        #If station_HydroGroup(ETCellCount) = 1 Then CN2w = Curve_Number_coarse(wscc + 43)
        #If station_HydroGroup(ETCellCount) = 2 Then CN2w = Curve_Number_medium(wscc + 43)
        #If station_HydroGroup(ETCellCount) = 3 Then CN2w = Curve_Number_fine(wscc + 43)

        #' assume that 'rooting depth' for dormant surfaces is 0.1 or 0.15 m
        #' this is depth that will be applied with a stress function to reduce kcb

        zr_dormant = 0.1 #'  was 0.15

        #' Convert current moisture content of Zr layer (which should be at Zrx at end of season)
        #' into starting moisture content of layer 3
        #' This is done at end of season

        #' Calc total water currently in layer 3 (the dynamic layer below Zr)

        DAW3 = self.AW3 * (self.Zrx - self.Zr) #' AW is mm/m and DAW3 is mm in layer 3 (in case Zr<Zrx)

        #' Add TAW - Dr that is in root zone below zr_dormant.
        #' Assume fully mixed root zone inclding zr_dormant part

        TAWroot = self.AW * (self.Zr) #' potential water in root zone
        DAWroot = TAWroot - self.Dr #' actual water in root zone based on Dr at end of season
        if DAWroot < 0: 
            DAWroot = 0
        ze = 0.1 #' depth of evaporation layer   #' (This only works when Ze < zr_dormant)
        if zr_dormant < self.Zr:  #' reduce DAWroot by water in  evap layer and rest of zrdormant and then proportion

            #' determine water in zr_dormant layer
            #' combine water in Ze layer (1-fc fraction) to that in balance of zr_dormant depth
            #' need to mix Ze and zr_dormant zones.  Assume current Zr zone of crop just ended is fully mixed.
            #' totwatinZe is water in fc fraction of Ze.

            AWroot = DAWroot / self.Zr
            if zr_dormant > ze:
                totwatinzr_dormant = (self.totwatinZe + AWroot * (zr_dormant - ze)) * (1 - self.fc) + AWroot * zr_dormant * fc
            else:
                #' was, until 5/9/07: totwatinzr_dormant = (self.totwatinZe * (Ze - zr_dormant) / Ze) * (1 - fc) + AWroot * zr_dormant * fc
                totwatinzr_dormant = (self.totwatinZe * (1 - (ze - zr_dormant) / ze)) * (1 - self.fc) + AWroot * zr_dormant * self.fc #' corrected

            #' This requires that zr_dormant > Ze.

            if DAWroot > totwatinzr_dormant:
                DAWbelow = (DAWroot - totwatinzr_dormant) #' proportionate water between zr_dormant and Zr
                #'  DAWbelow = DAWroot * (Zr - zr_dormant) / Zr #'actual water between zr_dormant and Zr

            else:
                DAWbelow = 0
            self.AW3 = (DAWbelow + DAW3) / (self.Zrx - zr_dormant) #' actual water in mm/m below zr_dormant
        else:
            self.AW3 = self.AW3 #' this should never happen, since Zrx for all crops > 0.15 m


        #' initialize Dr for dormant season
        #' Depletion below evaporation layer:

        #' Dr_below_Ze = (Dr - De) #' / (Zr - Ze) #'mm/m
        #' If Dr_below_Ze < 0 Then Dr_below_Ze = 0
        #' Dr = Dr_below_Ze * (zr_dormant - Ze) / (Zr - Ze) + De  #'assume fully mixed profile below Ze

        self.Dr = self.AW * zr_dormant - totwatinzr_dormant

        #' set Zr for dormant season

        self.Zr = zr_dormant

        #' This value for Zr will hold constant all dormant season.  DP from Zr will be
        #' used to recharge Zrx - Zr zone
        #' make sure that GrowRoot is not called during dormant season

        self.fwi = self.fwstd #' fw changed to fwi 8/10/06
        self.Iauto = 0
        self.simulated_irr = 0
        self.dormant_setup_flag = False

