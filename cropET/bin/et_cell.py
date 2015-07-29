#!/usr/bin/env python

import datetime
import logging
import math
import os
import pprint
import sys
import time

import numpy as np
import pandas as pd

import crop_et_data
import crop_parameters
import crop_coefficients
import util

class ETCell():
    ##name = None
    def __init__(self):
        """ """
    def __str__(self):
        """ """
        return '<ETCell {0}, {1} {2}>'.format(
            self.cell_id, self.cell_name, self.refet_id)

    def set_crop_params(self, fn):
        """ List of <CropParameter> instances """
        self.crop_params = crop_parameters.read_crop_parameters(fn)
    
    def set_crop_coeffs(self, fn):
        """ List of <CropCoeff> instances """
        self.crop_coeffs = crop_coefficients.read_crop_coefs(fn)

    def init_properties_from_row(self, data):
        """ Parse a row of data from the ET cell properties file

        Order of the values:
        ETCellIDs, ETCellNames, RefETIDs, station_lat, station_long,
        station_elevft, station_WHC, station_soildepth, station_HydroGroup,
        aridity_rating, refet_path

        Args:
            data (list): row values

        """
        self.cell_id = data[0]
        self.cell_name = data[1]
        self.refet_id = data[2]    # met_id ??
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
        ##self.refet_path = data[12]
        ##if len(data) == 14:       # CVP
        ##    self.area = data[13]
        ##elif len(data) == 15:     # truckee
        ##    self.huc = data[13]
        ##    self.huc_name = data[14]
        ##elif len(data) > 13:
        ##    self.cell_lat = float(data[13])
        ##    self.cell_lon = float(data[14])
        ##    self.cell_elev = float(data[15])

        ## DEADBEEF - For now assume station and cell have the same lat/lon/elev
        ##self.cell_lat = float(data[13])
        ##self.cell_lon = float(data[14])
        ##self.cell_elev = float(data[15])

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

    def set_refet_data(self, refet_params):
        """Read the ETo/ETr data file for a single station using Pandas

        Klamath_pmdata/ETo/OR1571E2_KL_2020_S0.dat
        Example of data file:
            Date TMax TMin Precip Snow SDep EstRs EsWind EsTDew Penm48 PreTay ASCEr ASCEg 85Harg
                 C    C    In*100 In*100 In MJ/m2 m/s    C      mm/day mm/day mm/day mm/day mm/day
            1/1/1950 -1.655943 -14.90594 7.0347 0 0 7.7163 1.4369 -13.12652 0.3820 0.05878 0.6653 0.4011 0.3863
            1/2/1950 -1.825944 -13.92594 3.0854 0 0 7.4293 1.4369 -12.14653 0.3694 0.07820 0.6126 0.3757 0.3867

        Args:
            refet_params (dict): RefET parameters from the INI file

        Returns:
            Dictionary of the RefET data, keys are the columns,
                and values are numpy arrays of the data
        """
        logging.debug('\nRead ETo/ETr data')
        refet_path = os.path.join(
            refet_params['ws'], refet_params['format'] % self.refet_id)
        logging.debug('  {0}'.format(refet_path))

        ## Get list of 0 based line numbers to skip
        ## Ignore header but assume header was set as a 1's based index
        skiprows = [i for i in range(refet_params['header_lines'])
                    if i+1 <> refet_params['names_line']]
        data_pd = pd.read_table(
            refet_path, engine='python', header=refet_params['names_line']-1,
            skiprows=skiprows, delimiter=refet_params['delimiter'])
        logging.debug('  Columns: {}'.format(', '.join(list(data_pd.columns.values))))

        ## Array of date objects
        dt_array = np.array([dt.date() for dt in pd.to_datetime(data_pd['Date'])])
        ##date_array = np.array([dt.date() for dt in pd.to_datetime(data_pd['Date'])])     
        ## time.struct_time(tm_year=1950, tm_mon=1, tm_mday=3, tm_hour=0, tm_min=0,
        ## tm_sec=0, tm_wday=1, tm_yday=3, tm_isdst=-1)
        ##struct_time_array = np.array([
        ##    time.strptime(s, "%m/%d/%Y") for s in data_pd['Date'].tolist()])

        ## Check fields
        for field_key, field_name in refet_params['fields'].items():
            if field_name is not None and field_name not in data_pd.columns:
                logging.error(
                    ('\n  ERROR: Field "{0}" was not found in {1}\n'+
                     '    Check the {2}_field value in the INI file').format(
                    field_name, os.path.basename(refet_path), field_key))
                sys.exit()

        ## Check/modify units
        for k,v in refet_params['units'].items():
            if v is None:
                continue
            elif v.lower() in ['mm/day', 'mm']:
                continue
            else:
                logging.error('\n ERROR: Unknown {0} units {1}'.format(k, v))

        ##
        self.refet = {
             'etref': np.array(data_pd[refet_params['fields']['etref']]), 
             'dates': dt_array}
             ##'dates': struct_time_array}
             ##'ASCEPMStdETr': np.array(data_pd['ASCEr']), 
             ##'ASCEPMStdETo': np.array(data_pd['ASCEg']),
             ##'Penman':  a['Penm48'], 'PreTay': a['PreTay'], 'Harg': a['85Harg'],
             ##'dates': date_array,

    def set_weather_data(self, weather_params):
        """Read the meteorological/climate data file for a single station using Pandas

        Klamath_pmdata/ETo/OR1571E2_KL_2020_S0.dat
        Example of data file:
            Date TMax TMin Precip Snow SDep EstRs EsWind EsTDew Penm48 PreTay ASCEr ASCEg 85Harg
                 C    C    In*100 In*100 In MJ/m2 m/s    C      mm/day mm/day mm/day mm/day mm/day
            1/1/1950 -1.655943 -14.90594 7.0347 0 0 7.7163 1.4369 -13.12652 0.3820 0.05878 0.6653 0.4011 0.3863
            1/2/1950 -1.825944 -13.92594 3.0854 0 0 7.4293 1.4369 -12.14653 0.3694 0.07820 0.6126 0.3757 0.3867

        Args:
            met_params (dict): Weater parameters from the INI file

        Returns:
            Dictionary of the RefET data, keys are the columns,
                and values are numpy arrays of the data
        """
        logging.debug('Read meteorological/climate data')

        weather_path = os.path.join(
            weather_params['ws'], weather_params['format'] % self.refet_id)
        logging.debug('  {0}'.format(weather_path))

        ## Get list of 0 based line numbers to skip
        ## Ignore header but assume header was set as a 1's based index
        data_skip = [i for i in range(weather_params['header_lines'])
                     if i+1 <> weather_params['names_line']]
        data_pd = pd.read_table(
            weather_path, engine='python',
            header=weather_params['names_line']-1,
            skiprows=data_skip, sep=weather_params['delimiter'])
        logging.debug('  Columns: {0}'.format(', '.join(list(data_pd.columns.values))))

        ## Array of date objects
        dt_array = np.array([dt.date() for dt in pd.to_datetime(data_pd['Date'])])

        ## Check fields
        for field_key, field_name in weather_params['fields'].items():
            if field_name is not None and field_name not in data_pd.columns:
                logging.error(
                    ('\n  ERROR: Field "{0}" was not found in {1}\n'+
                     '    Check the {2}_field value in the INI file').format(
                    field_name, os.path.basename(weather_path), field_key))
                sys.exit()

        ## Check/modify units
        for k,v in weather_params['units'].items():
            if v is None:
                continue
            elif v.lower() in ['c', 'm/s', 'mj/m2']:
                continue
            elif v.lower() == 'k':
                data_pd[weather_params['fields'][k]] -= 273.15
            elif v.lower() == 'f':
                data_pd[weather_params['fields'][k]] -= 32
                data_pd[weather_params['fields'][k]] /= 1.8
            elif v.lower() == 'in*100':
                data_pd[weather_params['fields'][k]] *= 0.254
            elif v.lower() == 'in':
                data_pd[weather_params['fields'][k]] *= 25.4
            elif v.lower() == 'w/m^2':
                data_pd[weather_params['fields'][k]] *= 0.0864
            ##elif v.lower() == 'kg/kg':
            ##    data_pd[weather_params['fields'][k]] *= 1
            else:
                logging.error('\n ERROR: Unknown {0} units {1}'.format(k, v))

        ## Scale wind height to 2m if necessary
        if weather_params['wind_height'] <> 2:
            data_pd[weather_params['fields']['wind']] *= (
                4.87 / np.log(67.8 * weather_params['wind_height'] - 5.42))

        ## Calculate Tdew from specific humidity
        ## Convert station elevation from feet to meters
        if (not weather_params['fields']['tdew'] and
            weather_params['fields']['q']):
            logging.warning('Tdew from Ea needs to be tested!')
            raw_input('ENTER')
            pair = util.pair_func(0.3048 * self.stn_elev)
            ea_array = util.ea_from_q(pair, data_pd[weather_params['fields']['q']])
            tdew_array = util.tdew_from_ea(ea_array)
            weather_params['fields']['tdew'] = tdew_array

        ## Save arrays
        ## DEADBEEF - Eventually return dataframe directly?
        self.weather = {
             'tmax': np.array(data_pd[weather_params['fields']['tmax']]), 
             'tmin': np.array(data_pd[weather_params['fields']['tmin']]),
             'precip': np.array(data_pd[weather_params['fields']['ppt']]), 
             'snow': np.array(data_pd[weather_params['fields']['snow']]), 
             'snow_depth': np.array(data_pd[weather_params['fields']['depth']]), 
             'rs': np.array(data_pd[weather_params['fields']['rs']]), 
             'wind': np.array(data_pd[weather_params['fields']['wind']]), 
             'tdew': np.array(data_pd[weather_params['fields']['tdew']]),
             'dates': dt_array}

    def process_climate(self, start_dt=None, end_dt=None):
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
        tmax_array = np.copy(self.weather['tmax'])
        tmin_array = np.copy(self.weather['tmin'])

        for i, step_dt in enumerate(self.weather['dates']):
            if start_dt is not None and step_dt < start_dt:
                continue
            elif end_dt is not None and step_dt > end_dt:
                continue
            ## Compute long term averages
            ## Adjust and check temperature data
            ## Adjust T's downward if station is arid
            if self.aridity_rating > 0:
                # Interpolate value for aridity adjustment
                moa_frac = step_dt.month + (step_dt.day - 15) / 30.4
                moa_frac = min([max([moa_frac, 1]), 11])
                #moa_base = int(CDbl(moa_frac))
                #moa_base, frac = math.modf(moa_frac)
                moa_base = int(moa_frac)
                arid_adj = (
                    aridity_adj[moa_base] +
                    (aridity_adj[moa_base + 1] - aridity_adj[moa_base]) *
                    (moa_frac - moa_base))
                tmax_array[i] -= self.aridity_rating / 100. * arid_adj
                tmin_array[i] -= self.aridity_rating / 100. * arid_adj

                # Fill in missing data with long term doy average
                # This should be done in separate process,
                #   prior to any refet or cropet calcs (30 lines of code)

        ## T30 stuff, done after temperature adjustments above
        tmean_array = (tmax_array + tmin_array) * 0.5
        t30_array = np.zeros(len(tmax_array)) 
        main_t30_lt = np.zeros(367)
        main_cgdd_0_lt = np.zeros(367)
        nrecord_main_t30 = np.zeros(367)
        nrecord_main_cgdd = np.zeros(367)

        sd_array = np.copy(self.weather['snow_depth'])
        swe_array = np.copy(self.weather['snow'])
        ##precip_array = np.copy(self.weather['precip'])

        ## Build a mask of valid dates
        date_mask = np.array([
            isinstance(dt, datetime.date) for dt in self.weather['dates']])
        if start_dt is not None:
            date_mask[self.weather['dates'] < start_dt] = False
        if end_dt is not None:
            date_mask[self.weather['dates'] > end_dt] = False
        
        main_t30 = 0.0
        snow_accum = 0.0
        for i, step_dt in enumerate(self.weather['dates']):
            if not date_mask[i]:
                continue
            doy = int(step_dt.strftime('%j'))

            ## Calculate an estimated depth of snow on ground using simple melt rate function))
            if len(sd_array) > 0:
                snow = swe_array[i]
                snow_depth = sd_array[i]

                ## DEADBEEF - Units conversion is happening when data is read in
                ### [140610] TP, the ETo file has snow in hundreths, not tenths????
                ##snow = snow / 10 * 25.4 #'tenths of inches to mm
                swe_array[i] = snow
                #snow = swe_array(sdays - 1)  # ???
                ##snow_depth = snow_depth * 25.4 #' inches to mm
                
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

            ## Build cumulative over period of record
            nrecord_main_t30[doy] += 1
            main_t30_lt[doy] = (
                (main_t30_lt[doy] * (nrecord_main_t30[doy] - 1) + main_t30) /
                nrecord_main_t30[doy] )

            ## Compute main cgdd for period of record for various bases for
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

            main_gdd_0 += gdd
            main_cgdd_0_lt[doy] += main_gdd_0
            nrecord_main_cgdd[doy] += 1

        ## Compute long term mean cumGDD0 from sums
        for doy in range(1,367):
            if nrecord_main_cgdd[doy] > 0:
                 main_cgdd_0_lt[doy] /= nrecord_main_cgdd[doy]
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
        self.climate['snow_depth_array'] = sd_array
        self.climate['snow_array'] = swe_array
        ##self.climate['precip_array'] = precip_array


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
    ##(fn, et_cells)
    ##
    ###c = et_cells[0]
    ##c = et_cells.values()[0]
    ##pprint(vars(c))
    ##print c
    pass
