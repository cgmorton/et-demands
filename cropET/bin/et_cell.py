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

class ETCellData():
    """Functions for loading ET Cell data from the static text files"""
    def __init__(self):
        """ """
        self.et_cells_dict = dict()

    def set_cell_properties(self, fn, delimiter='\t'):
        """Extract the ET cell property data from the text file
    
        This function will build the ETCell objects and must be run first.
    
        Args:
            fn (str): file path of the ET cell properties text file
            delimiter (str): file delimiter (i.e. space, comma, tab, etc.)
            
        Returns:
            None
        """
        a = np.loadtxt(fn, delimiter=delimiter, dtype='str')
        ## Klamath file has one header, other has two lines
        if a[0,0] == 'ET Cell ID':
            a = a[1:]
        else:
            a = a[2:]
        for i, row in enumerate(a):
            obj = ETCell()
            obj.init_properties_from_row(row)
            obj.source_file_properties = fn
            self.et_cells_dict[obj.cell_id] = obj
    
    def set_cell_crops(self, fn, delimiter='\t'):
        """Extract the ET cell crop data from the text file
    
        Args:
            fn (str): file path  of the ET cell crops text file
            delimiter (str): file delimiter (i.e. space, comma, tab, etc.)
            
        Returns:
            None
        """
        a = np.loadtxt(fn, delimiter=delimiter, dtype='str')
        crop_numbers = a[1,4:].astype(int)
        crop_names = a[2,4:]
        a = a[3:]
        for i, row in enumerate(a):
            cell_id = row[0]
            if cell_id not in self.et_cells_dict.keys():
                logging.error(
                    'read_et_cells_crops(), cell_id %s not found' % cell_id)
                sys.exit()
            obj = self.et_cells_dict[cell_id]
            obj.init_crops_from_row(row, crop_numbers)
            obj.source_file_crop = fn
            obj.crop_names = crop_names
            obj.crop_numbers = crop_numbers
            ## List of active crop numbers (i.e. flag is True)
            obj.num_crop_sequence = [k for k,v in obj.crop_flags.items() if v]
    
    def set_cell_cuttings(self, fn, delimiter='\t', skip_rows=2):
        """Extract the mean cutting data from the text file
    
        Args:
            fn (str): file path of the mean cuttings text file
            delimiter (str): file delimiter (i.e. space, comma, tab, etc.)
            skip_rows (str): number of header rows to skip
            
        Returns:
            None
        """
        with open(fn, 'r') as fp:
            a = fp.readlines()
            
        ## ET Cell ID may not be the first column in older files
        ## Older excel files had ID as the second column in the cuttings tab
        ## Try to find it in the header row
        try:
            ##header = a[1].split(delimiter)
            cell_id_index = a[1].split(delimiter).index('ET Cell ID')
        except:
            cell_id_index = None
            
        a = a[skip_rows:]
        for i, line in enumerate(a):
            row = line.split(delimiter)
            if cell_id_index is not None:
                cell_id = row[cell_id_index]
            else:
                cell_id = row[0]
            ##cell_id = row[1]
            if cell_id not in self.et_cells_dict.keys():
                logging.error(
                    'crop_et_data.static_mean_cuttings(), cell_id %s not found' % cell_id)
                sys.exit()
            obj = self.et_cells_dict[cell_id]
            obj.init_cuttings_from_row(row)
            ##obj.source_file_cuttings = fn
            ##self.et_cells_dict[cell_id] = obj
        
class ETCell():
    def __init__(self):
        """ """
    def __str__(self):
        """ """
        return '<ETCell {0}, {1} {2}>'.format(
            self.cell_id, self.cell_name, self.refet_id)

    def set_crop_params(self, fn, vb_flag=False):
        """ List of <CropParameter> instances """
        logging.info('  Reading crop parameters')
        self.crop_params = crop_parameters.read_crop_parameters(fn, vb_flag)
    
    def set_crop_coeffs(self, fn):
        """ List of <CropCoeff> instances """
        logging.info('  Reading crop coefficients')
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
        ## DEADBEEF - RefET path will be build from the ID and format
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
        
        ## Compute air pressure of the station/cell
        self.air_pressure = util.pair_from_elev(0.3048 * self.stn_elev)
        ##self.air_pressure = util.pair_from_elev(0.3048 * self.cell_elev)

    def init_crops_from_row(self, data, crop_numbers):
        """Parse the row of data
        
        There is code in kcb_daily to adjust cgdd_term using the crop flag as a multiplier
        This code is currently commented out and crop_flags are being read in as booleans 

        """
        self.irrigation_flag = int(data[3])
        self.crop_flags = dict(zip(crop_numbers, data[4:].astype(bool)))
        ##self.crop_flags = dict(zip(crop_numbers, data[4:]))
        self.ncrops = len(self.crop_flags)

    def init_cuttings_from_row(self, data):
        """ Parse the row of data """
        ##self.cuttingsLat = float(data[2])
        self.dairy_cuttings = int(data[3])
        self.beef_cuttings = int(data[4])

    def set_refet_data(self, refet):
        """Read the ETo/ETr data file for a single station using Pandas

        Args:
            refet (dict): RefET parameters from the INI file

        Returns:
            Dictionary of the RefET data, keys are the columns,
                and values are numpy arrays of the data
        """
        logging.debug('\nRead ETo/ETr data')
        refet_path = os.path.join(refet['ws'], refet['format'] % self.refet_id)
        logging.debug('  {0}'.format(refet_path))

        ## Get list of 0 based line numbers to skip
        ## Ignore header but assume header was set as a 1's based index
        skiprows = [i for i in range(refet['header_lines'])
                    if i+1 <> refet['names_line']]
        self.refet_pd = pd.read_table(
            refet_path, engine='python', header=refet['names_line']-1,
            skiprows=skiprows, delimiter=refet['delimiter'])
        logging.debug('  Columns: {}'.format(
            ', '.join(list(self.refet_pd.columns.values))))

        ## Check fields
        for field_key, field_name in refet['fields'].items():
            if field_name is not None and field_name not in self.refet_pd.columns:
                logging.error(
                    ('\n  ERROR: Field "{0}" was not found in {1}\n'+
                     '    Check the {2}_field value in the INI file').format(
                    field_name, os.path.basename(refet_path), field_key))
                sys.exit()
            ## Rename the dataframe fields
            self.refet_pd = self.refet_pd.rename(columns = {field_name:field_key})
        ## Check/modify units
        for field_key, field_units in refet['units'].items():
            if field_units is None:
                continue
            elif field_units.lower() in ['mm/day', 'mm']:
                continue
            else:
                logging.error('\n ERROR: Unknown {0} units {1}'.format(
                    field_key, field_units))
                    
        ## Convert date strings to datetimes
        if refet['fields']['date'] is not None:
            self.refet_pd['date'] = pd.to_datetime(self.refet_pd['date'])
        else:
            self.refet_pd['date'] = self.refet_pd[['year', 'month', 'day']].apply(
                lambda s : datetime.datetime(*s),axis = 1)
        ##self.refet_pd['date'] = pd.to_datetime(self.refet_pd['date'])
        self.refet_pd.set_index('date', inplace=True)
        self.refet_pd['doy'] = [int(ts.strftime('%j')) for ts in self.refet_pd.index]
        
        return True
        ## return refet_pd

    def set_weather_data(self, weather):
        """Read the meteorological/climate data file for a single station using Pandas

        Args:
            met_params (dict): Weater parameters from the INI file

        Returns:
            Dictionary of the RefET data, keys are the columns,
                and values are numpy arrays of the data
        """
        logging.debug('Read meteorological/climate data')

        weather_path = os.path.join(
            weather['ws'], weather['format'] % self.refet_id)
        logging.debug('  {0}'.format(weather_path))

        ## Get list of 0 based line numbers to skip
        ## Ignore header but assume header was set as a 1's based index
        data_skip = [i for i in range(weather['header_lines'])
                     if i+1 <> weather['names_line']]
        self.weather_pd = pd.read_table(
            weather_path, engine='python',
            header=weather['names_line']-1,
            skiprows=data_skip, sep=weather['delimiter'])
        logging.debug('  Columns: {0}'.format(
            ', '.join(list(self.weather_pd.columns.values))))

        ## Check fields
        for field_key, field_name in weather['fields'].items():
            if (field_name is not None and 
                field_name not in self.weather_pd.columns):
                logging.error(
                    ('\n  ERROR: Field "{0}" was not found in {1}\n'+
                     '    Check the {2}_field value in the INI file').format(
                    field_name, os.path.basename(weather_path), field_key))
                sys.exit()
            ## Rename the dataframe fields
            self.weather_pd = self.weather_pd.rename(
                columns = {field_name:field_key})
        ## Check/modify units
        for field_key, field_units in weather['units'].items():
            if field_units is None:
                continue
            elif field_units.lower() in ['c', 'mm', 'm/s', 'mj/m2', 'mj/m^2', 'kg/kg']:
                continue
            elif field_units.lower() == 'k':
                self.weather_pd[field_key] -= 273.15
            elif field_units.lower() == 'f':
                self.weather_pd[field_key] -= 32
                self.weather_pd[field_key] /= 1.8
            elif field_units.lower() == 'in*100':
                self.weather_pd[field_key] *= 0.254
            elif field_units.lower() == 'in':
                self.weather_pd[field_key] *= 25.4
            elif field_units.lower() in ['w/m2', 'w/m^2']:
                self.weather_pd[field_key] *= 0.0864
            else:
                logging.error('\n ERROR: Unknown {0} units {1}'.format(
                    field_key, field_units))
                    
        ## Convert date strings to datetimes
        if weather['fields']['date'] is not None:
            self.weather_pd['date'] = pd.to_datetime(self.weather_pd['date'])
        else:
            self.weather_pd['date'] = self.weather_pd[['year', 'month', 'day']].apply(
                lambda s : datetime.datetime(*s),axis = 1)
        ##self.weather_pd['date'] = pd.to_datetime(self.weather_pd['date'])
        self.weather_pd.set_index('date', inplace=True)
        self.weather_pd['doy'] = [int(ts.strftime('%j')) for ts in self.weather_pd.index]
                    
        ## Scale wind height to 2m if necessary
        if weather['wind_height'] <> 2:
            self.weather_pd['wind'] *= (
                4.87 / np.log(67.8 * weather['wind_height'] - 5.42))
                
        ## Add snow and snow_depth if necessary
        if 'snow' not in self.weather_pd.columns:
            self.weather_pd['snow'] = 0
        if 'snow_depth' not in self.weather_pd.columns:
            self.weather_pd['snow_depth'] = 0

        ## Calculate Tdew from specific humidity
        ## Convert station elevation from feet to meters
        if ('tdew' not in self.weather_pd.columns and 
            'q' in self.weather_pd.columns):
            self.weather_pd['tdew'] = util.tdew_from_ea(util.ea_from_q(
                self.air_pressure, self.weather_pd['q'].values))

        ## Compute RH from Tdew and Tmax
        if ('rh_min' not in self.weather_pd.columns and 
            'tdew' in self.weather_pd.columns and 
            'tmax' in self.weather_pd.columns):
            ## For now do not consider SVP over ice
            ## (it was not used in ETr or ETo computations, anyway)
            self.weather_pd['rh_min'] = 100 * np.clip(
                util.es_from_t(self.weather_pd['tdew'].values) / 
                util.es_from_t(self.weather_pd['tmax'].values), 0, 1)
        
        ## Set CO2 correction values to 1 if they are not in the data
        ##if 'co2_grass' not in self.weather_pd.columns:
        ##    self.weather_pd['co2_grass'] = 1
        ##if 'co2_trees' not in self.weather_pd.columns:
        ##    self.weather_pd['co2_trees'] = 1
        ##if 'co2_c4' not in self.weather_pd.columns:
        ##    self.weather_pd['co2_c4'] = 1
        
        return True
        ## return weather_pd

    def process_climate(self):
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
       
        ## Initialize the climate dataframe
        self.climate_pd = self.weather_pd[
            ['doy', 'tmax', 'tmin', 'snow', 'snow_depth']].copy()

        ## Adjust T's downward if station is arid
        if self.aridity_rating > 0:
            ## Interpolate value for aridity adjustment
            aridity_adj = [0., 0., 0., 0., 1., 1.5, 2., 3.5, 4.5, 3., 0., 0., 0.]
            month = np.array([dt.month for dt in self.weather_pd.index])
            day = np.array([dt.day for dt in self.weather_pd.index])
            moa_frac = np.clip((month + (day - 15) / 30.4), 1, 11)
            arid_adj = np.interp(moa_frac, range(len(aridity_adj)), aridity_adj)
            arid_adj *= self.aridity_rating / 100.
            self.climate_pd['tmax'] -= arid_adj
            self.climate_pd['tmin'] -= arid_adj
            del month, day, arid_adj

        ## T30 stuff, done after temperature adjustments above
        self.climate_pd['tmean'] = self.climate_pd[["tmax", "tmin"]].mean(axis=1)
        self.climate_pd['t30'] = pd.rolling_mean(
            self.climate_pd['tmean'], window=30, min_periods=1)
        
        ## Build cumulative T30 over period of record
        main_t30_lt = np.array(self.climate_pd[['t30', 'doy']].groupby('doy').mean()['t30'])
        
        ## Compute GDD for each day
        self.climate_pd['cgdd'] = self.climate_pd['tmean']
        self.climate_pd.ix[self.climate_pd['tmean'] <= 0, 'cgdd'] = 0
        # Tbase(ctCount) -- have no idea what ctCount value should be, since this
        # is before start of CropCycle & each crop has own Tbase value in
        # crop_parameters.py, use 0.0 for now, since appears may be ctCount
        #  Based on previous comment, assume Tbase = 0.0
        ## DEADBEEF - Uncomment if tbase is set to anything other than 0
        ##tbase = 0.0
        ##self.climate_pd.ix[self.climate_pd['tmean'] > 0, 'ggdd'] -= tbase
        
        ## Compute cumulative GDD for each year
        self.climate_pd['cgdd'] = self.climate_pd[['doy', 'cgdd']].groupby(
            self.climate_pd.index.map(lambda x: x.year)).cgdd.cumsum()
        ## DEADBEEF - Compute year column then compute cumulative GDD
        ##self.climate_pd['year'] = [dt.year for dt in self.climate_pd.index]
        ##self.climate_pd['cgdd'] = self.climate_pd[['year', 'doy', 'gdd']].groupby('year').gdd.cumsum()
        
        ## Compute mean cumulative GDD for each DOY
        main_cgdd_0_lt = np.array(self.climate_pd[['cgdd', 'doy']].groupby('doy').mean()['cgdd'])
          
        ## Revert from indexing by I to indexing by DOY (for now)
        ## Copy DOY 1 value into DOY 0
        main_t30_lt = np.insert(main_t30_lt, 0, main_t30_lt[0])
        main_cgdd_0_lt = np.insert(main_cgdd_0_lt, 0, main_cgdd_0_lt[0])
        
        ##
        self.climate = {}           
        self.climate['main_t30_lt'] = main_t30_lt
        self.climate['main_cgdd_0_lt'] = main_cgdd_0_lt

        ## Calculate an estimated depth of snow on ground using simple melt rate function))   
        if np.any(self.climate_pd['snow']):
            for i, doy in self.weather_pd['doy'].iteritems():
                ## Calculate an estimated depth of snow on ground using simple melt rate function
                snow = self.climate_pd['snow'][i]
                snow_depth = self.climate_pd['snow_depth'][i]
                ## Assume a settle rate of 2 to 1
                snow_accum += snow * 0.5 #' assume a settle rate of 2 to 1
                ## 4 mm/day melt per degree C
                snow_melt = max(4 * self.climate_pd['tmax'][i], 0.0)
                snow_accum = max(snow_accum - snow_melt, 0.0)
                snow_depth = min(snow_depth, snow_accum)
                self.weather_pd['snow_depth'][i] = snow_depth
        return True
        ## return climate_pd

    def subset_weather_data(self, start_dt=None, end_dt=None): 
        """Subset the dataframes based on the start and end date"""
        if start_dt is not None:
            self.refet_pd = self.refet_pd[self.refet_pd.index >= start_dt]
            self.weather_pd = self.weather_pd[self.weather_pd.index >= start_dt]
            self.climate_pd = self.climate_pd[self.climate_pd.index >= start_dt]
        if end_dt is not None:
            self.refet_pd = self.refet_pd[self.refet_pd.index <= end_dt]
            ##self.refet_pd = self.refet_pd.ix[self.refet_pd.index <= end_dt]
            self.weather_pd = self.weather_pd[self.weather_pd.index <= end_dt]
            self.climate_pd = self.climate_pd[self.climate_pd.index <= end_dt]
        return True       

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
