import logging

import numpy as np

# from modCropET.vb

de_initial = 10.0  # mm initial depletion for first day of crop

class InitializeCropCycle:
    def __init__(self):
        """Initialize for crops cycle"""
        self.ad = 0.
        self.aw = 0
        self.aw3 = 0.
        self.cn2 = 0.
        self.cgdd = 0.
        self.cgdd_penalty = 0.
        self.cum_evap = 0.
        self.cum_evap_prev = 0.
        self.depl_ze = 0.
        self.depl_zep = 0.
        self.dperc = 0.
        self.dperc_ze = 0.
        self.density = 0.
        self.depl_surface = 0.
        self.depl_root = 0.
        self.etc_act = 0.
        self.etc_pot = 0.
        self.etc_bas = 0.
        self.etref_30 = 0.   # thirty day mean ETref  ' added 12/2007
        self.fc = 0.
        self.fw = 0.
        self.fw_spec = 0.
        self.fw_std = 0.
        self.fw_irr = 0.
        self.gdd = 0.0
        self.gdd_penalty = 0.
        self.height_min = 0.
        self.height_max = 0.
        self.height = 0
        self.irr_auto = 0.
        self.irr_sim = 0.
        self.kc_act = 0.
        self.kc_pot = 0
        self.kc_max = 0.
        self.kc_min = 0.
        self.kc_bas = 0.
        self.kc_bas_mid = 0.
        self.kc_bas_prev = 0.
        self.ke = 0.
        self.ke_irr = 0
        self.ke_ppt = 0.
        self.kr2 = 0.
        self.ks = 0.
        self.kt_reducer = 1.
        self.mad = 0.
        self.mad_ini = 0.
        self.mad_mid = 0.
        self.n_cgdd = 0.
        self.n_pl_ec = 0.
        self.niwr = 0.
        self.ppt_inf = 0.
        self.ppt_inf_prev = 0.
        self.rew = 0.
        self.tew = 0.
        self.tew2 = 0.
        self.tew3 = 0.
        self.s = 0.
        self.s1 = 0.
        self.s2 = 0.
        self.s3 = 0.
        self.s4 = 0.
        self.sro = 0.
        self.zr_min = 0.
        self.zr_max = 0.
        self.z = 0.

        # CGM - I don't remember why these are grouped separately
        # Maybe because they are "flags"

        self.doy_start_cycle = 0
        self.cutting = 0
        self.cycle = 1
        self.real_start = False
        self.irr_flag = False
        self.in_season = False  # false if outside season, true if inside
        self.dormant_setup_flag = False
        self.crop_setup_flag = True  # flag to setup crop parameter information

        # TP - Looks like its value comes from compute_crop_et(),
        # but needed for setup_dormant() below...

        self.totwatin_ze = 0.

        # CGM - These are not pre-initialized in the 32-bit VB code

        self.cgdd_at_planting = 0.
        self.wt_irr = 0.

        # CGM - Initialized to 0 in latest VB code

        self.kc_bas_prev = 0.

        # TP - Added

        self.max_lines_in_crop_curve_table = 34

        # CGM - In VB code, crops 44-46 were run first to set these values kn kcb_daily()
        #   Initialize here instead
        #   Using a dictionary instead of an array to make the indexing more obvious

        self.kc_bas_wscc = dict()
        self.kc_bas_wscc[1] = 0.1
        self.kc_bas_wscc[2] = 0.1
        self.kc_bas_wscc[3] = 0.1

        # TP - Minimum net depth of application for germination irrigation, etc.

        self.irr_min = 10.

        # CGM - Code to write a cutting review file is not currently implemented
        # self.cutting = np.zeros(20, dtype=np.int)

        # TP - Not initialized in VB code, probably should be initialized to 0
        # self.T2Days = 0

        # CGM - It doesn't seem like these need to be initialized?
        # self.e = 0.
        # self.tei = 0
        # self.Kcmult = 1
        # self.irr_manual = 0
        # self.irr_real = 0
        # self.irr_special = 0
        # self.ei = 0
        # self.ep = 0
        # self.few = 0
        # self.kr = 0
        # self.kt_prop = 1
        # self.ze = 0.

    def crop_load(self, data, et_cell, crop):
        """Assign characteristics for crop from crop Arrays

        Called by crop_cycle.crop_cycle() just before time loop

        Args:
            et_cell ():
            crop ():
        """
        self.height_min = crop.height_initial
        self.height_max = crop.height_max
        self.zr_min = crop.rooting_depth_initial
        self.zr_max = crop.rooting_depth_max

        self.depl_ze = de_initial  # (10 mm) at start of new crop at beginning of time
        self.depl_root = de_initial  # (20 mm) at start of new crop at beginning of time
        self.zr = self.zr_min  # initialize rooting depth at beginning of time
        self.height = self.height_min
        self.stress_event = False

        # Find maximum kc_bas in array for this crop (used later in height calc)
        # kc_bas_mid is the maximum kc_bas found in the kc_bas table read into program
        # Following code was repaired to properly parse crop curve arrays on 7/31/2012.  dlk

        self.kc_bas_mid = 0.

        # Bare soil 44, mulched soil 45, dormant turf/sod (winter) 46 do not have curve

        if crop.curve_number > 0:
            self.kc_bas_mid = np.max(et_cell.crop_coeffs[crop.curve_number].data)

        # Available water in soil

        self.aw = et_cell.stn_whc / 12 * 1000.   # in/ft to mm/m
        self.mad_ini = crop.mad_initial
        self.mad_mid = crop.mad_midseason

        # Setup curve number for antecedent II condition

        if et_cell.stn_hydrogroup == 1:
            self.cn2 = crop.cn_coarse_soil
        elif et_cell.stn_hydrogroup == 2:
            self.cn2 = crop.cn_medium_soil
        elif et_cell.stn_hydrogroup == 3:
            self.cn2 = crop.cn_fine_soil

        # Estimate readily evaporable water and total evaporable water from WHC
        # REW is from regression of REW vs. AW from FAO-56 soils table
        # R.Allen, August 2006, R2=0.92, n = 9

        self.rew = 0.8 + 54.4 * self.aw / 1000  # REW is in mm and AW is in mm/m

        # Estimate TEW from AW and Ze = 0.1 m
        # use FAO-56 based regression, since WHC from statso database does not have texture indication
        # R.Allen, August 2006, R2=0.88, n = 9

        self.tew = -3.7 + 166 * self.aw / 1000  # TEW is in mm and AW is in mm/m
        if self.rew > (0.8 * self.tew):
            self.rew = 0.8 * self.tew # limit REW based on TEW
        self.tew2 = self.tew  # TEW2Array(ctCount)
        self.tew3 = self.tew  # TEW3Array(ctCount) '(no severely cracking clays in Idaho)
        self.kr2 = 0  # Kr2Array(ctCount)'(no severely cracking clays in Idaho)
        self.fw_std = crop.crop_fw  # fwarray(ctCount)

        # Irrigation flag
        # CGM - How are these different?
        # For flag=1 or 2, turn irrigation on for a generally 'irrigated' region
        # For flag=3, turn irrigation on for specific irrigated crops even in non-irrigated region
        # Added Jan 2007 to force grain and turf irrigation in rainfed region
        if crop.irrigation_flag >= 1:
            self.irr_flag = True  # turn irrigation on for a generally 'irrigated' region
        # Either no irrigations for this crop or station or
        #      irrigation off even in irrigated region if this crop has no flag
        else:
            self.irr_flag = False  # no irrigations for this crop or station

        # CGM - Original code for setting irrigation flag
        # DLK - one is by crop in crop parameters; other is by crop in by et cell
        # self.irr_flag = False  # no irrigations for this crop or station
        # if crop.irrigation_flag > 0:
        #     self.irr_flag = True  # turn irrigation on for a generally 'irrigated' region
        # if crop.irrigation_flag < 1:
        #     self.irr_flag = False  # turn irrigation off even in irrigated region if this crop has no flag
        # if crop.irrigation_flag > 2:   # added Jan 2007 to force grain and turf irrigation in rainfed region
        #     self.irr_flag = True  # turn irrigation on for specific irrigated crops even in nonirrigated region if this crop has flag=3

        # Pre-compute parameters instead of re-computing them daily

        # Flag_for_means_to_estimate_pl_or_gu Case 1

        if crop.flag_for_means_to_estimate_pl_or_gu == 1:
            if data.phenology_option == 0:
                cgdd_col = 'main_cgdd_0_lt'
            elif data.phenology_option == 1:    # annual crops only
                if crop.is_annual:
                    cgdd_col = 'hist_cgdd_0_lt'
                else:
                    cgdd_col = 'main_cgdd_0_lt'
            elif data.phenology_option == 2:    # perennial crops only
                if not crop.is_annual:
                    cgdd_col = 'hist_cgdd_0_lt'
                else:
                    cgdd_col = 'main_cgdd_0_lt'
            else:    # both annual and perennial
                cgdd_col = 'hist_cgdd_0_lt'
            try:
                self.longterm_pl = int(np.where(np.diff(np.array(
                    et_cell.climate[cgdd_col] > crop.t30_for_pl_or_gu_or_cgdd,
                    dtype = np.int8)) > 0)[0][0]) + 1
            except:
                logging.error(
                    ('  initialize_crop_cycle():\n  Crop: {0:2d}, CellID: {1}\n' +
                     '  Error computing longterm_pl, CGDD (LT) didn\'t go above threshold ({2})\n' +
                     '  Setting longerm_pl = 0').format(
                        crop.class_number, et_cell.cell_id,
                        crop.t30_for_pl_or_gu_or_cgdd))
                self.longterm_pl = 0

        # Flag_for_means_to_estimate_pl_or_gu Case 2

        elif crop.flag_for_means_to_estimate_pl_or_gu == 2:
            if data.phenology_option == 0:
                t30_col = 'main_t30_lt'
            elif data.phenology_option == 1:    # annual crops only
                if crop.is_annual:
                    t30_col = 'hist_t30_lt'
                else:
                    t30_col = 'main_t30_lt'
            elif data.phenology_option == 2:    # perennial crops only
                if not crop.is_annual:
                    t30_col = 'hist_t30_lt'
                else:
                    t30_col = 'main_t30_lt'
            else:    # both annual and perennial
                t30_col = 'hist_t30_lt'
            try:
                self.longterm_pl = int(np.where(np.diff(np.array(
                    et_cell.climate[t30_col] > crop.t30_for_pl_or_gu_or_cgdd,
                    dtype = np.int8)) > 0)[0][0]) + 1
            except IndexError:
                self.longterm_pl = 0
                logging.error(
                    ('  initialize_crop_cycle(): \n  Crop: {0:2d}, CellID: {1}\n' +
                     '  Error computing longterm_pl, T30 (LT) didn\'t go above threshold ({2})\n' +
                     '  Setting longerm_pl = 0').format(
                        crop.class_number, et_cell.cell_id,
                        crop.t30_for_pl_or_gu_or_cgdd))
                logging.info('  Station long term T30:')
                logging.info(et_cell.climate['main_t30_lt'])
                self.longterm_pl = 0
            except:
                self.longterm_pl = 0
                logging.error(
                    ('  initialize_crop_cycle():\n' +
                     '  Crop: {0:2d}, CellID: {1}\n' +
                     '  Unknown error computing longterm_pl\n' +
                     '  Setting longerm_pl = 0').format(
                        crop.class_number, et_cell.cell_id))
        self.setup_crop(crop)

    def setup_crop(self, crop):
        """Initialize some variables for beginning of crop seasons

        Called in crop_cycle if not in season and crop setup flag is true
        Called in kcb_daily for startup/greenup type 1, 2, and 3 when startup conditions are met
        """
        # zr_dormant was never assigned a value - what's its purpose - dlk 10/26/2011 ???????????????????

        zr_dormant = 0.0

        # setup_crop is called from crop_cycle if is_season is false and crop_setup_flag is true
        # thus only setup 1st time for crop (not each year)
        # also called from kcb_daily each time GU/Plant date is reached, thus at growing season start

        self.height_min = crop.height_initial
        self.height_max = crop.height_max
        self.zr_min = crop.rooting_depth_initial
        self.zr_max = crop.rooting_depth_max
        self.height = self.height_min
        self.tew = self.tew2  # find total evaporable water
        if self.tew < self.tew3:
            self.tew = self.tew3
        self.fw_irr = self.fw_std  # fw changed to fw_irr 8/10/06
        self.irr_auto = 0
        self.irr_sim = 0

        # Reinitialize zr, but actCount for additions of DP into reserve (zrmax - zr) for rainfed

        # Convert current moisture content below Zr at end of season to AW for new crop
        # (into starting moisture content of layer 3).  This is required if zr_min != zr_dormant
        # Calc total water currently in layer 3

        # AW3 is mm/m and daw3 is mm in layer 3 (in case Zr<zr_max)

        daw3 = self.aw3 * (self.zr_max - zr_dormant)

        # Layer 3 is soil depth between current rootzone (or dormant rootdepth) and max root for crop
        # AW3 is set to 0 first time throught for crop.

        # Potential water in root zone below zr_dormant

        taw3 = self.aw * (self.zr_max - zr_dormant)

        # Make sure that AW3 has been collecting DP from zr_dormant layer during winter

        # if daw3 < 0.0: daw3 = 0.
        daw3 = max(0, daw3)
        # if taw3 < 0.0: taw3 = 0.
        taw3 = max(0, taw3)
        if self.zr_min > zr_dormant:
            # adjust depletion for extra starting root zone at plant or GU
            # assume fully mixed layer 3

            self.depl_root = (
                self.depl_root + (taw3 - daw3) *
                (self.zr_min - zr_dormant) / (self.zr_max - zr_dormant))
        elif self.zr_max > self.zr_min:
            # Was, until 5/9/07:
            # Assume moisture right above zr_dormant is same as below
            # depl_root = depl_root - (taw3 - daw3) * (zr_dormant - zr_min) / (zr_max - zr_min)
            # Following added 5/9/07
            # Enlarge depth of water

            daw3 = (
                daw3 + (zr_dormant - self.zr_min) / zr_dormant *
                (self.aw * zr_dormant - self.depl_root))

            # Adjust depl_root in proportion to zr_min / zdormant and increase daw3 and AW3

            self.depl_root *= self.zr_min / zr_dormant

            # denom is layer 3 depth at start of season
            
            self.aw3 = daw3 / (self.zr_max - self.zr_min)
            # if self.aw3 < 0.0: self.aw3 = 0.
            self.aw3 = max(0.0, self.aw3)
            if self.aw3 > self.aw: self.aw3 = self.aw
            self.aw3 = min(self.aw, self.aw3)
        if self.depl_root < 0.:self.depl_root = 0.

        # Initialize rooting depth at beginning of time  <----DO??? Need recalc on Reserve?

        self.zr = self.zr_min
        self.crop_setup_flag = False

    def setup_dormant(self,  et_cell, crop):
        """Start of dormant season

        Set up for soil water reservoir during non-growing season
          to collect soil moisture for next growing season

        Also set for type of surface during non-growing season

        Called at termination of crop from crop_cycle()
        If in_season is false and dormant_flag is true,
        dormant_flag set at GU each year.
        It is called each year as soon as season is 0.
        """

        # winter_surface_cover_class = 1 bare, 2 mulch, 3 sod

        wscc = crop.winter_surface_cover_class

        # Kc_bas for wintertime land use
        #  44: Bare soil
        #  45: Mulched soil, including wheat stubble
        #  46: Dormant turf/sod (winter time)
        #  note: set Kcmax for winter time (Nov-Mar) and fc outside of this sub.

        if wscc == 1:
            self.kc_bas = 0.1    # was 0.2
            self.fc = 0
        elif wscc == 2:
            self.kc_bas = 0.1    # was 0.2
            self.fc = 0.4
        elif wscc == 3:
            self.kc_bas = 0.2    # was 0.3
            self.fc = 0.7     # was 0.6

        # Setup curve number for antecedent II condition for winter covers
        # Crop params dictionary uses crop number as key
        # Don't subtract 1 to convert to an index
        if et_cell.stn_hydrogroup == 1:
            self.cn2 = et_cell.crop_params[wscc+43].cn_coarse_soil
        elif et_cell.stn_hydrogroup == 2:
            self.cn2 = et_cell.crop_params[wscc+43].cn_medium_soil
        elif et_cell.stn_hydrogroup == 3:
            self.cn2 = et_cell.crop_params[wscc+43].cn_fine_soil

        # Assume that 'rooting depth' for dormant surfaces is 0.1 or 0.15 m
        # This is depth that will be applied with a stress function to reduce kc_bas

        zr_dormant = 0.1  #  was 0.15

        # Convert current moisture content of Zr layer
        #   (which should be at zr_max at end of season)
        #   into starting moisture content of layer 3
        # This is done at end of season

        # Calc total water currently in layer 3 (the dynamic layer below zr)
        # AW is mm/m and daw3 is mm in layer 3 (in case zr < zr_max)

        daw3 = self.aw3 * (self.zr_max - self.zr)

        # Add TAW - depl_root that is in root zone below zr_dormant.
        # Assume fully mixed root zone including zr_dormant part

        # Potential water in root zone

        taw_root = self.aw * (self.zr)

        # Actual water in root zone based on depl_root at end of season

        daw_root = max(taw_root - self.depl_root, 0)

        # Depth of evaporation layer (This only works when ze < zr_dormant)

        ze = 0.1

        # Reduce daw_root by water in evap layer and rest of zr_dormant and then proportion

        if zr_dormant < self.zr:
            # determine water in zr_dormant layer
            # combine water in ze layer (1-fc fraction) to that in balance of zr_dormant depth
            # need to mix ze and zr_dormant zones.  Assume current Zr zone of crop just ended is fully mixed.
            # totwatin_ze is water in fc fraction of Ze.

            aw_root = daw_root / self.zr
            if zr_dormant > ze:
                totwatinzr_dormant = (
                    (self.totwatin_ze + aw_root * (zr_dormant - ze)) * (1 - self.fc) +
                    aw_root * zr_dormant * fc)
            else:
                # Was, until 5/9/07
                # totwatinzr_dormant = (
                #     .totwatin_ze * (ze - zr_dormant) / ze) * (1 - fc) +
                #     _root * zr_dormant * fc)
                totwatinzr_dormant = (
                    (self.totwatin_ze * (1 - (ze - zr_dormant) / ze)) * (1 - self.fc) +
                    aw_root * zr_dormant * self.fc)  # corrected

            # This requires that zr_dormant > ze.

            if daw_root > totwatinzr_dormant:
                # Proportionate water between zr_dormant and zr

                daw_below = (daw_root - totwatinzr_dormant)

                # Actual water between zr_dormant and zr
                # daw_below = daw_root * (zr - zr_dormant) / zr
            else:
                daw_below = 0

            # Actual water in mm/m below zr_dormant

            self.aw3 = (daw_below + daw3) / (self.zr_max - zr_dormant)
        else:
            # This should never happen, since zr_max for all crops > 0.15 m

            self.aw3 = self.aw3

        # initialize depl_root for dormant season
        # Depletion below evaporation layer:

        # depl_root_below_Ze = (depl_root - de)  # / (zr - ze) #'mm/m
        # If depl_root_below_ze < 0 Then depl_root_below_ze = 0
        # assume fully mixed profile below Ze
        # depl_root = depl_root_below_ze * (zr_dormant - ze) / (zr - ze) + de

        self.depl_root = self.aw * zr_dormant - totwatinzr_dormant

        # set Zr for dormant season

        self.zr = zr_dormant

        # This value for zr will hold constant all dormant season.  dp from zr will be
        # used to recharge zr_max - zr zone.
        # Make sure that grow_root is not called during dormant season.

        self.fw_irr = self.fw_std  # fw changed to fw_irr 8/10/06
        self.irr_auto = 0
        self.irr_sim = 0
        self.dormant_setup_flag = False

        # Clear cutting flag (just in case)

        self.cutting = 0

    def setup_dataframe(self, et_cell):
        """Initialize output dataframe"""
        self.crop_df = et_cell.refet_df[['doy', 'etref']].copy()
        self.crop_df['et_act'] = np.nan
        self.crop_df['et_pot'] = np.nan
        self.crop_df['et_bas'] = np.nan
        self.crop_df['kc_act'] = np.nan
        self.crop_df['kc_bas'] = np.nan
        self.crop_df['irrigation'] = np.nan
        self.crop_df['runoff'] = np.nan
        self.crop_df['dperc'] = np.nan
        self.crop_df['niwr'] = np.nan
        self.crop_df['season'] = 0
        self.crop_df['cutting'] = 0

    def setup_co2(self, et_cell, crop):
        """Get the CO2 correction factor dataframe for the target cell/crop

        Args:
            et_cell ():
            crop ():
        """
        if crop.co2_type == 'GRASS':
            self.co2 = et_cell.weather_pd['co2_grass']
        elif crop.co2_type == 'TREE':
            self.co2 = et_cell.weather_pd['co2_tree']
        elif crop.co2_type == 'C4':
            self.co2 = et_cell.weather_pd['co2_c4']
        return True

