from pprint import pprint
import sys

import numpy as np

# from modCropET.vb
de_initial = 10.0 #' mm initial depletion for first day of crop

class InitializeCropCycle:
    """Initialize for crops cycle"""
    ad = 0.
    aw = 0
    aw3 = 0.
    cn2 = 0.
    cgdd = 0.0
    cum_et = 0.
    cummevap = 0.
    cummevap1 = 0.
    cum_ppt = 0.
    de = 0.
    density = 0.
    dep = 0.
    depl_surface = 0.
    dpe = 0.
    dpe_yest = 0.
    dr = 0.
    ##ei = 0
    ##ep = 0
    etc_act = 0.
    etc_pot = 0.
    etc_bas = 0.
    etref_30 = 0.                 #' thirty day mean ETref  ' added 12/2007
    fc = 0.
    ##few = 0
    fw = 0.
    fw_spec = 0.
    fw_std = 0.
    fwi = 0.
    gdd = 0.0
    hmin = 0.
    hmax = 0.
    height = 0
    irr_auto = 0.
    ##irr_manual = 0
    ##irr_real = 0
    ##irr_special = 0
    irr_simulated = 0.
    kc_act = 0.
    ##kc_pot = 0
    kc_max = 0.
    kc_min = 0.
    kcb = 0.
    kcb_mid = 0.
    ke = 0.
    kei = 0
    kep = 0.
    ##kr = 0
    kr2 = 0.
    ks = 0.
    ##kt_prop = 1
    kt_reducer = 1.
    mad = 0.
    mad_ini = 0.
    mad_mid = 0.0
    ppt_inf = 0.
    ppt_inf_yest = 0.
    ##ppt_net4 = 0
    ##ppt_net3 = 0
    ##ppt_net2 = 0
    ##ppt_net1 = 0
    rew = 0.
    tew = 0.
    tew2 = 0.
    tew3 = 0.
    S = 0.
    S1 = 0.
    S2 = 0.
    S3 = 0.
    S4 = 0.
    zrn = 0.
    zrx = 0.
    z = 0.

    e = 0.
    lDoy = 0
    frost_flag = 0.
    penalty = 0.
    cgdd_penalty = 0.
    l_cumgdd = 0.
    pressure = 0.0
    n_cumgdd = 0.
    nPL_EC = 0.
    #tei = 0
    #Kcmult = 1
    sro = 0.
    Dpr = 0.
    doy_start_cycle = 0

    real_start = False
    irr_flag = False
    in_season = False             #' false if outside season, true if inside
    dormant_setup_flag = False
    crop_setup_flag = True        #' flag to setup crop parameter information
    cycle = 1.

    # [140609] TP added this, looks like its value comes from compute_crop_et(),
    # but needed for setup_dormant() below...
    totwatinZe = 0.0

    cgdd_at_planting = 0.0

    ### TP added these
    # from modCropET.vb
    #Private Const max_lines_in_crop_curve_table As Short = 34
    max_lines_in_crop_curve_table = 34
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

    # Minimum net depth of application for germination irrig., etc.
    irr_min = 10.0

    def __init__(self):
        """ """

    # Initialize some variables for beginning of crop seasons
    # Called in crop_cycle if not in season and crop setup flag is true
    # Called in kcb_daily for startup/greenup type 1, 2, and 3 when startup conditions are met
    def setup_crop(self, crop):
        #' zr_dormant was never assigned a value - what's its purpose - dlk 10/26/2011 ???????????????????
        zr_dormant = 0.0
    
        #' setup_crop is called from crop_cycle if is_season is false and crop_setup_flag is true
        #' thus only setup 1st time for crop (not each year)
        #' also called from kcb_daily each time GU/Plant date is reached, thus at growing season start
        self.hmin = crop.height_initial
        self.hmax = crop.height_maximum
        self.zrn = crop.rooting_depth_initial
        self.zrx = crop.rooting_depth_maximum
        self.hcrop = self.hmin
        self.tew = self.tew2 #' find total evaporable water
        if self.tew3 > self.tew:  
            self.tew = self.tew3
        self.fwi = self.fw_std #' fw changed to fwi 8/10/06
        self.irr_auto = 0
        self.irr_simulated = 0
    
        # Reinitialize zr, but actCount for additions of DP into reserve (zrmax - zr) for rainfed
    
        # Convert current moisture content below Zr at end of season to AW for new crop
        # (into starting moisture content of layer 3).  This is required if zrn <> zr_dormant
        # Calc total water currently in layer 3

        # AW3 is mm/m and daw3 is mm in layer 3 (in case Zr<Zrx)
        daw3 = self.aw3 * (self.zrx - zr_dormant) 
    
        # Layer 3 is soil depth between current rootzone (or dormant rootdepth) and max root for crop
        # AW3 is set to 0 first time throught for crop.

        # Potential water in root zone below zr_dormant
        taw3 = self.aw * (self.zrx - zr_dormant) 
    
        # Make sure that AW3 has been collecting DP from zr_dormant layer during winter
        if daw3 < 0.:
            daw3 = 0.
        if taw3 < 0.:
            taw3 = 0.
        if self.zrn > zr_dormant:
            #' adjust depletion for extra starting root zone at plant or GU
            #' assume fully mixed layer 3
            self.dr = (
                self.dr + (taw3 - daw3) *
                (self.zrn - zr_dormant) / (self.zrx - zr_dormant))
        elif self.zrx > self.zrn:
            # Was, until 5/9/07:
            # Assume moisture right above zr_dormant is same as below
            #dr = dr - (taw3 - daw3) * (zr_dormant - zrn) / (zrx - zrn) 
            # Following added 5/9/07
            # Enlarge depth of water
            daw3 = (
                daw3 + (zr_dormant - self.zrn) / zr_dormant *
                (self.aw * zr_dormant - self.dr))
            # Adjust dr in proportion to zrn / zdormant and increase daw3 and AW3
            self.dr = self.dr * self.zrn / zr_dormant
            # The denom is layer 3 depth at start of season
            self.aw3 = daw3 / (self.zrx - self.zrn) 
            if self.aw3 < 0.:
                self.aw3 = 0.
            if self.aw3 > self.aw:
                self.aw3 = self.aw
        if self.dr < 0.:
            self.dr = 0.
        # Initialize rooting depth at beginning of time  <----DO??? Need recalc on Reserve?
        self.zr = self.zrn
        self.crop_setup_flag = False

    def crop_load(self, data, et_cell, crop):
        """Assign characteristics for crop from crop Arrays

        Called by CropCycle just before time loop
        """
        self.hmin = crop.height_initial
        self.hmax = crop.height_maximum
        self.zrn = crop.rooting_depth_initial
        self.zrx = crop.rooting_depth_maximum
    
        self.de = de_initial #' (10 mm) at start of new crop at beginning of time
        self.dr = de_initial #' (20 mm) at start of new crop at beginning of time
        self.zr = self.zrn #' initialize rooting depth at beginning of time
        self.hcrop = self.hmin
        self.stress_event = False
    
        # Find maximum kcb in array for this crop (used later in height calc)
        # kcb_mid is the maximum kcb found in the kcb table read into program
        # Following code was repaired to properly parse crop curve arrays on 7/31/2012.  dlk
        #print 'cCurveNo', crop.curve_number
        #pprint(vars(et_cell.crop_coeffs[cCurveNo]))
        self.kcb_mid = 0.
        ## Bare soil 44, mulched soil 45, dormant turf/sod (winter) 46 do not have curve
        if crop.curve_number > 0:
            self.kcb_mid = et_cell.crop_coeffs[crop.curve_number].max_value(self.kcb_mid)
        #print 'initialize_crop_cycle', self.kcb_mid, cCurveNo

        # Available water in soil    
        self.aw = et_cell.stn_whc / 12 * 1000.  #' in/ft to mm/m
        self.mad_ini = crop.mad_initial
        self.mad_mid = crop.mad_midseason
    
        # Setup curve number for antecedent II condition
        if et_cell.stn_hydrogroup == 1:   
            self.cn2 = crop.cn_coarse_soil
        elif et_cell.stn_hydrogroup == 2:   
            self.cn2 = crop.cn_medium_soil
        elif et_cell.stn_hydrogroup == 3:   
            self.cn2 = crop.cn_fine_soil
        self.cn2_crop = self.cn2
    
        # Estimate readily evaporable water and total evaporable water from WHC
        # REW is from regression of REW vs. AW from FAO-56 soils table
        # R.Allen, August 2006, R2=0.92, n = 9
        self.rew = 0.8 + 54.4 * self.aw / 1000 #'REW is in mm and AW is in mm/m
    
        # Estimate TEW from AW and Ze = 0.1 m
        # use FAO-56 based regression, since WHC from statso database does not have texture indication
        # R.Allen, August 2006, R2=0.88, n = 9
        self.tew = -3.7 + 166 * self.aw / 1000 #'TEW is in mm and AW is in mm/m
        if self.rew > (0.8 * self.tew): 
            self.rew = 0.8 * self.tew #'limit REW based on TEW
        self.tew2 = self.tew #' TEW2Array(ctCount)
        self.tew3 = self.tew #' TEW3Array(ctCount) '(no severely cracking clays in Idaho)
        self.kr2 = 0 #' Kr2Array(ctCount)'(no severely cracking clays in Idaho)
        self.fw_std = crop.crop_fw #' fwarray(ctCount)
    
        ## Irrigation flag
        ## CGM - How are these different?
        ## For flag=1 or 2, turn irrigation on for a generally 'irrigated' region
        ## For flag=3, turn irrigation on for specific irrigated crops even in nonirrigated region
        ## Added Jan 2007 to force grain and turf irrigation in rainfed region
        if crop.irrigation_flag >= 1:
            self.irr_flag = True #' turn irrigation on for a generally 'irrigated' region
        ## Either no irrigations for this crop or station or 
        ##   turn irrigation off even in irrigated region if this crop has no flag
        else:
            self.irr_flag = False #' no irrigations for this crop or station
            
        ## CGM - Original code for setting irrigation flag
        ##self.irr_flag = False #' no irrigations for this crop or station
        ##if crop.irrigation_flag > 0:
        ##    self.irr_flag = True #' turn irrigation on for a generally 'irrigated' region
        ##if crop.irrigation_flag < 1:
        ##    self.irr_flag = False #' turn irrigation off even in irrigated region if this crop has no flag
        ##if crop.irrigation_flag > 2:  #' added Jan 2007 to force grain and turf irrigation in rainfed region
        ##    self.irr_flag = True #' turn irrigation on for specific irrigated crops even in nonirrigated region if this crop has flag=3
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

        #' wscc = 1 bare, 2 mulch, 3 sod

        #' kcb for wintertime land use
        #'  44: Bare soil
        #'  45: Mulched soil, including wheat stubble
        #'  46: Dormant turf/sod (winter time)
        #'   note: set Kcmax for winter time (Nov-Mar) and fc outside of this sub.
        if wscc == 1:        #' bare soil
            self.kcb = 0.1   #' was 0.2
            self.fc = 0
        elif wscc == 2:        #' Mulched soil, including wheat stubble
            self.kcb = 0.1   #' was 0.2
            self.fc = 0.4
        elif wscc == 3:        #' Dormant turf/sod (winter time)
            self.kcb = 0.2   #' was 0.3
            self.fc = 0.7    #' was 0.6

        #' setup curve number for antecedent II condition for winter covers
        #print wscc, et_cell.crop_params[wscc+43-1] 
        if et_cell.stn_hydrogroup == 1:   
            self.cn2 = et_cell.crop_params[wscc+43-1].cn_coarse_soil
        elif et_cell.stn_hydrogroup == 2:   
            self.cn2 = et_cell.crop_params[wscc+43-1].cn_medium_soil
        elif et_cell.stn_hydrogroup == 3:   
            self.cn2 = et_cell.crop_params[wscc+43-1].cn_fine_soil

        # Assume that 'rooting depth' for dormant surfaces is 0.1 or 0.15 m
        # This is depth that will be applied with a stress function to reduce kcb
        zr_dormant = 0.1 #'  was 0.15

        #' Convert current moisture content of Zr layer (which should be at zrx at end of season)
        #' into starting moisture content of layer 3
        #' This is done at end of season

        #' Calc total water currently in layer 3 (the dynamic layer below zr)

        daw3 = self.aw3 * (self.zrx - self.zr) #' AW is mm/m and daw3 is mm in layer 3 (in case zr < zrx)

        #' Add TAW - Dr that is in root zone below zr_dormant.
        #' Assume fully mixed root zone inclding zr_dormant part

        #' potential water in root zone
        taw_root = self.aw * (self.zr) #' potential water in root zone
        #' actual water in root zone based on Dr at end of season
        daw_root = max(taw_root - self.dr, 0) 
        ze = 0.1 #' depth of evaporation layer   #' (This only works when ze < zr_dormant)
        if zr_dormant < self.zr:  #' reduce daw_root by water in  evap layer and rest of zrdormant and then proportion

            #' determine water in zr_dormant layer
            #' combine water in ze layer (1-fc fraction) to that in balance of zr_dormant depth
            #' need to mix ze and zr_dormant zones.  Assume current Zr zone of crop just ended is fully mixed.
            #' totwatinZe is water in fc fraction of Ze.

            aw_root = daw_root / self.zr
            if zr_dormant > ze:
                totwatinzr_dormant = (
                    (self.totwatinZe + aw_root * (zr_dormant - ze)) * (1 - self.fc) +
                    aw_root * zr_dormant * fc)
            else:
                # Was, until 5/9/07
                #totwatinzr_dormant = (
                #    (self.totwatinZe * (ze - zr_dormant) / ze) * (1 - fc) +
                #    aw_root * zr_dormant * fc)
                totwatinzr_dormant = (
                    (self.totwatinZe * (1 - (ze - zr_dormant) / ze)) * (1 - self.fc) +
                    aw_root * zr_dormant * self.fc) #' corrected

            #' This requires that zr_dormant > ze.

            if daw_root > totwatinzr_dormant:
                daw_below = (daw_root - totwatinzr_dormant) #' proportionate water between zr_dormant and zr
                #'  daw_below = daw_root * (zr - zr_dormant) / zr #'actual water between zr_dormant and zr

            else:
                daw_below = 0
            self.aw3 = (daw_below + daw3) / (self.zrx - zr_dormant) #' actual water in mm/m below zr_dormant
        else:
            self.aw3 = self.aw3 #' this should never happen, since zrx for all crops > 0.15 m


        #' initialize dr for dormant season
        #' Depletion below evaporation layer:

        #' dr_below_Ze = (dr - de) #' / (zr - ze) #'mm/m
        #' If dr_below_ze < 0 Then dr_below_ze = 0
        #' dr = dr_below_ze * (zr_dormant - ze) / (zr - ze) + de  #'assume fully mixed profile below Ze
            
        self.dr = self.aw * zr_dormant - totwatinzr_dormant

        #' set Zr for dormant season
        self.zr = zr_dormant

        #' This value for zr will hold constant all dormant season.  dp from zr will be
        #' used to recharge zrx - zr zone
        #' make sure that grow_root is not called during dormant season

        self.fwi = self.fw_std #' fw changed to fwi 8/10/06
        self.irr_auto = 0
        self.irr_simulated = 0
        self.dormant_setup_flag = False

