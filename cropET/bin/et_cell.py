#!/usr/bin/env python

import logging
import math
import os
import pprint
import sys
import time

import numpy as np

import crop_parameters
import crop_coefficients
import util

class ETCell:
    name = None

    def __init__(self):
        """ """

    def __str__(self):
        """ """
        return '<ETCell {0}, {1} {2}>'.format(
            self.cell_id, self.cell_name, self.refET_id)

    def static_crop_params(self, fn):
        """ List of <CropParameter> instances """
        self.crop_params = crop_parameters.read_crop_parameters(fn)
    
    def static_crop_coeffs(self, fn):
        """ List of <CropCoeff> instances """
        self.crop_coeffs = crop_coefficients.read_crop_coefs(fn)

    def init_properties_from_row(self, data):
        """ Parse a row of data from the ET cell properties file

        Order of the values:
        ETCellIDs, ETCellNames, RefETIDs, station_lat, station_long,
        station_elevft, station_WHC, station_soildepth, station_HydroGroup,
        aridity_rating, refETPaths

        Args:
            data: list of row values

        """
        self.cell_id = data[0]
        self.cell_name = data[1]
        self.refET_id = data[2]    # met_id ??
        self.stn_lat = float(data[3])
        self.stn_lon = float(data[4])
        self.stn_elev = float(data[5])
        self.permeability = float(data[6])
        self.stn_whc = float(data[7])
        self.stn_soildepth = float(data[8])
        self.stn_hydrogroup_str = data[9]
        ## [140822] changed for RioGrande
        #self.stn_hydrogroup = int(data[10])
        self.stn_hydrogroup = int(eval(data[10]))
        self.aridity_rating = float(data[11])
        ##self.refET_path = data[12]
        ##if len(data) == 14:       # CVP
        ##    self.area = data[13]
        ##elif len(data) == 15:     # truckee
        ##    self.huc = data[13]
        ##    self.huc_name = data[14]
        ##elif len(data) > 13:
        ##    self.cell_lat = float(data[13])
        ##    self.cell_lon = float(data[14])
        ##    self.cell_elev = float(data[15])
        self.cell_lat = float(data[13])
        self.cell_lon = float(data[14])
        self.cell_elev = float(data[15])

    def init_crops_from_row(self, data, crop_numbers):
        """ Parse the row of data """
        self.irrigation_flag = int(data[3])
        self.crop_flags = dict(zip(crop_numbers, data[4:].astype(bool)))
        self.ncrops = len(self.crop_flags)

    def init_cuttings_from_row(self, data):
        """ Parse the row of data """
        ##self.cuttingsLat = float(data[2])
        self.dairy_cuttings = int(data[3])
        self.beef_cuttings = int(data[4])

    def set_daily_refet_data(self, fn, skip_rows=2):
        """Read the RefET data file for a single station

        Observed
        Station Coop No: 101       Lat:  39.44 Long: -118.81 Elev  3964 ft
        Monthly Wind Station Id:1007 Newlands  Monthly Ko Station Id:1007 Newlands  Computed at 02:27:30 PM  Tuesday, Dec 20, 2011
          mo  da  Yr  DoY   TMax   TMin  Precip  Snow  SDep EstRs EsWind EsTDew Penm48 PreTay ASCEr  ASCEg  85Harg
                             C     C     In*100 In*100  In  MJ/m2   m/s    C    mm/day mm/day mm/day mm/day mm/day 
           1   1  1950   1    12.7   -8.7    0     0     0    9.74   1.28  -7.7   0.98   0.16   1.85   1.11   1.19
           1   2  1950   2    14.3   -6.6    0     0     0    9.67   1.28  -5.6   1.03   0.17   1.92   1.15   1.30
           1   3  1950   3    -0.5  -19.8    0     0     0    9.74   1.28 -18.8   0.61   0.20   1.03   0.65   0.44

        Klamath_pmdata/ETo/OR1571E2_KL_2020_S0.dat
        Date    TMax    TMin    Precip  Snow    SDep    EstRs   EsWind  EsTDew  Penm48  PreTay  ASCEr   ASCEg   85Harg
            C   C   In*100  In*100  In  MJ/m2   m/s C   mm/day  mm/day  mm/day  mm/day  mm/day
        1/1/1950 -1.655943 -14.90594 7.034732 0 0 7.7162696684745 1.43687307834625 -13.12652 0.381984510542489 0.0587799121198262 0.665315332840188 0.401054956936277 0.386316892227767
        1/2/1950 -1.825944 -13.92594 3.085409 0 0 7.42927547945495 1.43687307834625 -12.14653 0.3694645610536 0.0782057303930262 0.612602954878387 0.375671086093519 0.386741543162141

        Args:
            fn: string
            skip_rows: integer indicating the number of header rows to skip
        Returns:
            Dictionary of the NLDAS data, keys are the columns,
                and values are numpy arrays of the data
        """
        
        a = np.loadtxt(fn, dtype='str', skiprows=skip_rows)

        ## May want to save the date field(s) as some point
        date_list = a[:,0].tolist()
        a = a[:,1:].astype(float)

        # time.struct_time(tm_year=1950, tm_mon=1, tm_mday=3, tm_hour=0, tm_min=0,
        # tm_sec=0, tm_wday=1, tm_yday=3, tm_isdst=-1)
        struct_time_list = [time.strptime(s, "%m/%d/%Y") for s in date_list]
        
        self.refet = {
             'TMax': a[:,0], 'TMin': a[:,1],
             'Precip': a[:,2], 'Snow': a[:,3], 'SnowDepth': a[:,4],
             'EstRs': a[:,5], 'Wind': a[:,6], 'TDew': a[:,7],
             'ASCEPMStdETr': a[:,10], 'ASCEPMStdETo': a[:,11],
             ##'Penman':  a[:,8], 'PreTay': a[:,9], 'Harg': a[:,12],
             ##'Dates': np.asarray(date_list),
             'Dates': np.asarray(struct_time_list)}

    def set_daily_nldas_data(self, fn):
        """Read the NLDAS data rod CSV file for a single station

        Example of data file:
            Year,Month,Day,DOY,Tmin(K),Tmax(K),Specific Humidity(kg kg-1),
            Wind @ 10m (m s-1),Solar Radiation (W m-2),Precipitation (mm),
            ETo @ 2m (mm day-1),ETr @ 2m(mm day-1)
            1979,1,1,1,252.7,263.62,0.00028215,1.9643,143.58,0,0.5754,0.92938
            1979,1,2,2,252.24,267.21,0.00035664,0.80539,76.738,0,0.43268,0.64418
            1979,1,3,3,257.46,272.2,0.00073107,0.64853,89.89,0,0.45107,0.6639

        genfromtxt replaces spaces, hyphens, and paranethesis with underscores
        Field names become:
            Year,Month,Day,DOY,TminK,TmaxK,Specific_Humiditykg_kg1,
            Wind__10m_m_s1,Solar_Radiation_W_m2,Precipitation_mm,
            ETo__2m_mm_day1,ETr__2mmm_day1

        Args:
            fn: string
        Returns:
            Dictionary of the NLDAS data, keys are the columns,
                and values are numpy arrays of the data
        """

        a = np.genfromtxt(fn, delimiter=',', names=True)
        ##print a.dtype.names
     
        date_str_list = ['{0}/{1}/{2}'.format(int(m),int(d),int(y))
                         for y, m, d in zip(a['Year'], a['Month'], a['Day'])]
        struct_time_list = [time.strptime(s, "%m/%d/%Y") for s in date_str_list]

        ## Convert temperatures from K to C
        a['TmaxK'] -= 273.15
        a['TminK'] -= 273.15

        ## Convert W/m2 to MJ/m2
        a['Solar_Radiation_W_m2'] *= 0.0864

        ## Scale wind from 10m to 2m
        a['Wind__10m_m_s1'] *= 4.87 / math.log(67.8 * 10 - 5.42)

        ## Calculate Tdew from specific humidity
        ## Convert station elevation from feet to meters
        pair = util.pair_func(0.3048 * self.stn_elev)
        ea = util.ea_from_q(pair, a['Specific_Humiditykg_kg1'])
        tdew = util.tdew_from_ea(ea)

        zero_array = np.zeros(a['TmaxK'].shape, dtype=np.float32)
        self.refet = {
             'TMax': a['TmaxK'], 'TMin': a['TminK'],
             'Precip': a['Precipitation_mm'],                     
             'Snow': zero_array,
             'SnowDepth': zero_array,
             'EstRs': a['Solar_Radiation_W_m2'],                     
             'Wind': a['Wind__10m_m_s1'],
             'TDew' : tdew,
             'ASCEPMStdETr': a['ETr__2mmm_day1'],
             'ASCEPMStdETo': a['ETo__2m_mm_day1'],                     
             ##'Penman' : zero_array,                     
             ##'PreTay' : zero_array,
             ##'Harg': zero_array,
             ##'Dates': np.asarray(date_str_list),
             'Dates': np.asarray(struct_time_list)}        

    def process_climate(self, nsteps):
        """ 
        
        compute long term averages (DAY LOOP)
            adjust and check temperature data
            process alternative TMax and TMin
        fill in missing data with long term doy average (DAY LOOP)
            Calculate an estimated depth of snow on ground using simple melt rate function))
            compute main cumGDD for period of record for various bases for constraining earliest/latest planting or GU
            only Tbase = 0 needs to be evaluated (used to est. GU for alfalfa, mint, hops)
        compute long term mean cumGDD0 from sums (JDOY LOOP)

        AltTMaxArray, AltTMinArray in code has to do with when future climate
        gets so much warmer that annuals are starting too soon, in this case,
        they used the historical, ie, AltTMaxArray, AltTMinArray == historical,
        so IGNORE   

        Also lots of missing data substitution stuff going on, ignore, this
        should be taken care of outside of process
        """
        ##logging.debug(pprint.pformat(self.refet))

        aridity_adj = [0., 0., 0., 0., 1., 1.5, 2., 3.5, 4.5, 3., 0., 0., 0.]

        ## Hold onto original TMax value for computing RHmin later on (for Kco), 12/2007, Allen
        tmax_array = np.copy(self.refet['TMax'])
        tmin_array = np.copy(self.refet['TMin'])

        ## Seems most/all of what goes on in day loop could be done with array math    
        ## Maybe change later after validating code
        #for i,ts in enumerate(self.refet['ts']):
        for i,ts in enumerate(self.refet['Dates'][:nsteps]):
            logging.debug((i,ts,type(ts)))

            month = ts[1]
            day = ts[2]

            ## Compute long term averages
            ## Adjust and check temperature data
            ## Adjust T's downward if station is arid
            if self.aridity_rating > 0:
                # Interpolate value for aridity adjustment
                moa_frac = month + (day - 15) / 30.4
                moa_frac = min([max([moa_frac, 1]), 11])
                #moa_base = Int(CDbl(moa_frac))
                #moa_base, frac = math.modf(moa_frac)
                moa_base = int(moa_frac)
                arid_adj = (
                    aridity_adj[moa_base] +
                    (aridity_adj[moa_base + 1] - aridity_adj[moa_base]) *
                    (moa_frac - moa_base))
                logging.debug(tmax_array[i])
                ##logging.debug('Tmax: {0}'.format(tmax[i]))
                tmax_array[i] -= self.aridity_rating / 100. * arid_adj
                tmin_array[i] -= self.aridity_rating / 100. * arid_adj
                logging.debug((moa_frac, tmax_array[i]))

                # Fill in missing data with long term doy average
                # This should be done in separate process,
                #   prior to any refet or cropet calcs (30 lines of code)

        ## T30 stuff, done after temperature adjustments above
        tmean_array = (tmax_array + tmin_array) * 0.5
        t30_array = np.zeros(len(tmax_array)) 
        nrecord_main_t30 = np.zeros(367)
        main_t30_lt = np.zeros(367)
        main_cgdd_0_lt = np.zeros(367)
        nrecord_main_cgdd = np.zeros(367)

        sd_array = np.copy(self.refet['SnowDepth'])
        swe_array = np.copy(self.refet['Snow'])

        ## Need to do precip conversion to mm, from hundreths of inches
        precip_array = np.copy(self.refet['Precip']) * 25.4 / 100.

        main_t30 = 0.0
        snow_accum = 0.0
        for i in range(len(self.refet['Dates'][:nsteps])):
            doy = self.refet['Dates'][i][7] 

            ## Calculate an estimated depth of snow on ground using simple melt rate function))
            if len(sd_array) > 0:
                snow = swe_array[i]
                snow_depth = sd_array[i]
                
                ### [140610] TP, the ETo file has snow in hundreths, not tenths????
                snow = snow / 10 * 25.4 #'tenths of inches to mm
                swe_array[i] = snow
                #snow = swe_array(sdays - 1)  # ???
                snow_depth = snow_depth * 25.4 #' inches to mm
                
                ## Calculate an estimated depth of snow on ground using simple melt rate function))
                snow_accum += snow * 0.5 #' assume a settle rate of 2 to 1
                snow_melt = 4 * tmax_array[i] #' 4 mm/day melt per degree C
                snow_melt = max(snow_melt, 0.0)
                snow_accum = snow_accum - snow_melt
                snow_accum = max(snow_accum, 0.0)
                snow_depth = min(snow_depth, snow_accum)
                sd_array[i] = snow_depth

            if i > 29:
                main_t30 = sum(tmean_array[i-29:i+1]) / 30
            else:
                main_t30 = (main_t30 * (i) + tmean_array[i]) / (i+1)
            t30_array[i] = main_t30

            ## Build cummulative over period of record
            nrecord_main_t30[doy] += 1
            main_t30_lt[doy] = (main_t30_lt[doy] * (nrecord_main_t30[doy] - 1) +
                                main_t30) / nrecord_main_t30[doy] 

            logging.debug((i, self.refet['Dates'][i], t30_array[i]))

            ## Compute main cumgdd for period of record for various bases for
            ##   constraining earliest/latest planting or GU
            ## Only Tbase = 0 needs to be evaluated
            ##   (used to est. GU for alfalfa, mint, hops)
            if i == 0 or doy == 1: 
                main_gdd_0 = 0.0

            ## Tbase(ctCount) -- have no idea what ctCount value should be, since this
            ## is before start of CropCycle & each crop has own Tbase value in
            ## crop_parameters.py, use 0.0 for now, since appears may be ctCount
            ##  Based on previous comment, assume Tbase = 0.0
            tbase = 0.0
            if tmean_array[i] > 0: #' simple method for all other crops
                gdd = tmean_array[i] - tbase
            else:
                gdd = 0.0

            main_gdd_0 = main_gdd_0 + gdd
            main_cgdd_0_lt[doy] = main_cgdd_0_lt[doy] + main_gdd_0
            nrecord_main_cgdd[doy] += 1

        ## Compute long term mean cumGDD0 from sums
        for doy in range(1,367):
            if nrecord_main_cgdd[doy] > 0:
                 main_cgdd_0_lt[doy] = main_cgdd_0_lt[doy] / nrecord_main_cgdd[doy]
            else:
                 main_cgdd_0_lt[doy] = 0.0

        ## Keep refet values intact & return any 'modified' variables in new mapping 
        self.climate = {}
        self.climate['tmax_array'] = tmax_array
        self.climate['tmin_array'] = tmin_array
        self.climate['tmean_array'] = tmean_array
        self.climate['t30_array'] = t30_array
        self.climate['main_t30_lt'] = main_t30_lt
        self.climate['main_cgdd_0_lt'] = main_cgdd_0_lt
        self.climate['snow_depth'] = sd_array
        self.climate['snow'] = swe_array
        self.climate['precip'] = precip_array


if __name__ == '__main__':
    ##project_ws = os.getcwd()
    ##static_ws = os.path.join(project_ws, 'static')
    ##
    ### Initalize cells with property info
    ##fn = os.path.join(static_ws,'ETCellsProperties.txt')
    ##et_cells = read_et_cells_properties(fn)
    ##
    ### Add the crop to cells
    ##fn = os.path.join(static_ws,'ETCellsCrops.txt')
    ##read_et_cells_crops(fn, et_cells)
    ##
    ### Mean cuttings
    ##fn = os.path.join(static_ws,'MeanCuttings.txt')
    ##print '\nRead Mean Cuttings'
    ##read_mean_cuttings(fn, et_cells)
    ##
    ###c = et_cells[0]
    ##c = et_cells.values()[0]
    ##pprint(vars(c))
    ##print c
    pass
