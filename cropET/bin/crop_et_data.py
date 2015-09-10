#!/usr/bin/env python

import ConfigParser
import datetime
import logging
import os
import sys

import numpy as np

##import et_cell
import util

class CropETData():
    def __init__(self):
        """ """
        ### From PenmanMonteithManager & modPM.vb
        self.crop_one_reducer = 0.9
        
        ## False sets crop 1 to alfalfa peak with no cuttings
        ## True sets crop 1 to nonpristine alfalfa w/cuttings
        self.crop_one_flag = True  

    def __str__(self):
        """ """
        return '<Cropet_data>'

    def read_ini(self, ini_path):
        """Read and parse the INI file"""
        logging.info('  INI: {}'.format(os.path.basename(ini_path)))

        ## Check that the INI file can be read
        config = ConfigParser.ConfigParser()
        try:
            ini = config.readfp(open(ini_path))
        except:
            logging.error('\nERROR: Config file could not be read, '+
                          'is not an input file, or does not exist\n')
            sys.exit()

        ## Check that all the sections are present
        crop_et_sec = 'CROP_ET'
        weather_sec = 'WEATHER'
        refet_sec = 'REFET'
        if set(config.sections()) <> set([crop_et_sec, weather_sec, refet_sec]):
            logging.error(
                '\nERROR: The input file must have the following sections:\n'+
                '  [{}], [{}], and [{}]'.format(crop_et_sec, weather_sec, refet_sec))
            sys.exit()

        ## The project and CropET folders need to be full/absolute paths
        self.project_ws = config.get(crop_et_sec, 'project_folder')
        crop_et_ws = config.get(crop_et_sec, 'crop_et_folder')
        if not os.path.isdir(self.project_ws):
            logging.critical(
                'ERROR: The project folder does not exist\n  %s' % self.project_ws)
            sys.exit()
        elif not os.path.isdir(crop_et_ws):
            logging.critical(
                'ERROR: The project folder does not exist\n  %s' % crop_et_ws)
            sys.exit()

        ## Basin   
        self.basin_id = config.get(crop_et_sec, 'basin_id')
        logging.info('  Basin: {}'.format(self.basin_id))

        ## Stats flags
        try:
            self.daily_output_flag = config.getboolean(
                crop_et_sec, 'daily_stats_flag')
        except:
            logging.debug('    daily_stats_flag = False')
            self.daily_output_flag = False
        try:
            self.monthly_output_flag = config.getboolean(
                crop_et_sec, 'monthly_stats_flag')
        except:
            logging.debug('    monthly_stats_flag = False')
            self.daily_output_flag = False
        try:
            self.annual_output_flag = config.getboolean(
                crop_et_sec, 'annual_stats_flag')
        except:
            logging.debug('    annual_stats_flag = False')
            self.daily_output_flag = False
        try:
            self.gs_output_flag = config.getboolean(
                crop_et_sec, 'growing_season_stats_flag')
        except:
            logging.debug('    growing_season_stats_flag = False')
            self.daily_output_flag = False

        ## For testing, allow the user to process a subset of the crops
        try: 
            self.crop_skip_list = config.get(crop_et_sec, 'crop_skip_list').split(',')
            self.crop_skip_list = [int(c.strip()) for c in self.crop_skip_list]
        except: 
            logging.debug('    crop_skip_list = []')
            self.crop_skip_list = []
        try: 
            self.crop_test_list = config.get(crop_et_sec, 'crop_test_list').split(',')
            self.crop_test_list = [int(c.strip()) for c in self.crop_test_list]
        except: 
            logging.debug('    crop_test_list = False')
            self.crop_test_list = []
            
        ## Input/output folders
        static_ws = os.path.join(
            self.project_ws, config.get(crop_et_sec, 'static_folder'))
        if self.daily_output_flag:
            try:
                self.daily_output_ws = os.path.join(
                    self.project_ws, config.get(crop_et_sec, 'daily_output_folder'))
                if not os.path.isdir(self.daily_output_ws):
                   os.makedirs(self.daily_output_ws)
            except:
                logging.debug('    daily_output_folder = daily_stats')
                self.daily_output_ws = 'daily_stats'
        if self.monthly_output_flag:
            try:
                self.monthly_output_ws = os.path.join(
                    self.project_ws, config.get(crop_et_sec, 'monthly_output_folder'))
                if not os.path.isdir(self.monthly_output_ws):
                   os.makedirs(self.monthly_output_ws)
            except:
                logging.debug('    monthly_output_folder = monthly_stats')
                self.monthly_output_ws = 'monthly_stats'             
        if self.annual_output_flag:
            try:
                self.annual_output_ws = os.path.join(
                    self.project_ws, config.get(crop_et_sec, 'annual_output_folder'))
                if not os.path.isdir(self.annual_output_ws):
                   os.makedirs(self.annual_output_ws)
            except:
                logging.debug('    annual_output_folder = annual_stats')
                self.annual_output_ws = 'annual_stats'
        if self.gs_output_flag:
            try:
                self.gs_output_ws = os.path.join(
                    self.project_ws, config.get(crop_et_sec, 'gs_output_folder'))
                if not os.path.isdir(self.gs_output_ws):
                   os.makedirs(self.gs_output_ws)
            except:
                logging.debug('    gs_output_folder = growing_season_stats')
                self.gs_output_ws = 'growing_season_stats'

        ## Start/end date
        try:
            self.start_dt = datetime.strptime(config.get(
                crop_et_sec, 'start_date'), '%Y-%m-%d')
            logging.info('  Start date: {0}'.format(self.start_dt.date()))
        except:
            logging.debug('  Start date not set or invalid')
            self.start_dt = None
        try:
            self.end_dt = datetime.datetime.strptime(
                config.get(crop_et_sec, 'end_date'), '%Y-%m-%d')
            logging.info('  End date:   {0}'.format(self.end_dt.date()))
        except:
            logging.debug('  End date not set or invalid')
            self.end_dt = None

        ## Compute additional variables
        self.niwr_flag = config.getboolean(crop_et_sec, 'niwr_flag')
        self.kc_flag = config.getboolean(crop_et_sec, 'kc_flag')
        self.co2_flag = config.getboolean(crop_et_sec, 'co2_flag')

        ## Static cell/crop files
        def check_static_file(static_name, static_var):
            try:
                static_path = os.path.join(
                    static_ws, config.get(crop_et_sec, static_var))
            except:
                static_path = os.path.join(static_ws, static_name)
                logging.debug('  {0} = {1}'.format(static_var, static_name))
            if not os.path.isfile(static_path):
                logging.error('ERROR: The static file {} does not exist'.format(
                    static_path))
                sys.exit()
            else:
                return static_path
        self.cell_properties_path = check_static_file(
            'ETCellsProperties.txt', 'cell_properties_name')
        self.cell_crops_path = check_static_file(
            'ETCellsCrops.txt', 'cell_crops_name')
        self.cell_cuttings_path = check_static_file(
            'MeanCuttings.txt', 'cell_cuttings_name')
        self.crop_params_path = check_static_file(
            'CropParams.txt', 'crop_params_name')
        self.crop_coefs_path = check_static_file(
            'CropCoefs.txt', 'crop_coefs_name')
        
        ## RefET parameters
        self.refet = {}
        self.refet['fields'] = {}
        self.refet['units'] = {}
        self.refet['ws'] = config.get(refet_sec, 'refet_folder')
        ## The refet folder could be a full or relative path
        ## Assume relative paths or from the project folder
        if os.path.isdir(self.refet['ws']):
            pass
        elif (not os.path.isdir(self.refet['ws']) and
              os.path.isdir(os.path.join(self.project_ws, self.refet['ws']))):
            self.refet['ws'] = os.path.join(self.project_ws, self.refet['ws'])
        else:
            logging.error('ERROR: The refet folder {} does not exist'.format(
                self.refet['ws']))
            sys.exit()
        ## DEADBEEF   
        ##self.refet['ws'] = os.path.join(
        ##    self.project_ws, config.get(refet_sec, 'refet_folder'))
        self.refet['type'] = config.get(refet_sec, 'refet_type').lower()
        if self.refet['type'] not in ['eto', 'etr']:
            logging.error('  ERROR: RefET type must be ETo or ETr')
            sys.exit()
        self.refet['format'] = config.get(refet_sec, 'name_format')
        self.refet['header_lines'] = config.getint(refet_sec, 'header_lines')
        self.refet['names_line'] = config.getint(refet_sec, 'names_line')
        self.refet['delimiter'] = config.get(refet_sec, 'delimiter')
        
        ## Field names and units      
        ## Date can be read directly or computed from year, month, and day
        try: 
            self.refet['fields']['date'] = config.get(weather_sec, 'date_field')
        except: 
            self.refet['fields']['date'] = None
        try: 
            self.refet['fields']['year'] = config.get(weather_sec, 'year_field')
            self.refet['fields']['month'] = config.get(weather_sec, 'month_field')
            self.refet['fields']['day'] = config.get(weather_sec, 'day_field')
        except: 
            self.refet['fields']['year'] = None
            self.refet['fields']['month'] = None
            self.refet['fields']['day'] = None
        if self.refet['fields']['date'] is not None:
            logging.debug('  REFET: Reading date from date column')
        elif (self.refet['fields']['year'] is not None and
              self.refet['fields']['month'] is not None and
              self.refet['fields']['day'] is not None):
            logging.debug('  REFET: Reading date from year, month, and day columns')
        else:
            logging.error('  ERROR: REFET date_field (or year, month, and '+
                          'day fields) must be set in the INI')
            sys.exit()                  
        ##try: 
        ##    self.refet['fields']['date'] = config.get(refet_sec, 'date_field')
        ##except: 
        ##    logging.error('  ERROR: REFET date_field must set in the INI')
        ##    sys.exit()

        try: 
            self.refet['fields']['etref'] = config.get(refet_sec, 'etref_field')
        except: 
            logging.error('  ERROR: REFET etref_field must set in the INI')
            sys.exit()
        try: 
           self.refet['units']['etref'] = config.get(refet_sec, 'etref_units')
        except: 
            logging.error('  ERROR: REFET etref_units must set in the INI')
            sys.exit()
        
        ## Check RefET parameters
        if not os.path.isdir(self.refet['ws']):
            logging.error(
                ('  ERROR: The RefET data folder does not '+
                 'exist\n  %s') % self.refet['ws'])
            sys.exit()
        ## Check fields and units
        elif self.refet['units']['etref'].lower() not in ['mm/day', 'mm']:
            logging.error(
                '  ERROR:  ETref units {0} are not currently supported'.format(
                    self.refet['units']['etref']))
            sys.exit()
            
        ## Weather parameters
        self.weather = {}
        self.weather['fields'] = {}
        self.weather['units'] = {}
        self.weather['ws'] = config.get(weather_sec, 'weather_folder')
        ## The weather folder could be a full or relative path
        ## Assume relative paths or from the project folder
        if os.path.isdir(self.weather['ws']):
            pass
        elif (not os.path.isdir(self.weather['ws']) and
              os.path.isdir(os.path.join(self.project_ws, self.weather['ws']))):
            self.weather['ws'] = os.path.join(self.project_ws, self.weather['ws'])
        else:
            logging.error('ERROR: The refet folder {} does not exist'.format(
                self.weather['ws']))
            sys.exit()
        ## DEADBEEF   
        ##self.weather['ws'] = os.path.join(
        ##    self.project_ws, config.get(weather_sec, 'weather_folder'))
        self.weather['format'] = config.get(weather_sec, 'name_format')
        self.weather['header_lines'] = config.getint(weather_sec, 'header_lines')
        self.weather['names_line'] = config.getint(weather_sec, 'names_line')
        self.weather['delimiter'] = config.get(weather_sec, 'delimiter')

        ## Field names and units      
        ## Date can be read directly or computed from year, month, and day
        try: 
            self.weather['fields']['date'] = config.get(weather_sec, 'date_field')
        except: 
            self.weather['fields']['date'] = None
        try: 
            self.weather['fields']['year'] = config.get(weather_sec, 'year_field')
            self.weather['fields']['month'] = config.get(weather_sec, 'month_field')
            self.weather['fields']['day'] = config.get(weather_sec, 'day_field')
        except: 
            self.weather['fields']['year'] = None
            self.weather['fields']['month'] = None
            self.weather['fields']['day'] = None
        if self.weather['fields']['date'] is not None:
            logging.debug('  WEATHER: Reading date from date column')
        elif (self.weather['fields']['year'] is not None and
              self.weather['fields']['month'] is not None and
              self.weather['fields']['day'] is not None):
            logging.debug('  WEATHER: Reading date from year, month, and day columns')
        else:
            logging.error('  ERROR: WEATHER date_field (or year, month, and '+
                          'day fields) must be set in the INI')
            sys.exit()                  
        
        ## Field names 
        ## The following fields are mandatory 
        ## DEADBEEF - Are snow and snow depth required?
        field_list = ['tmin', 'tmax', 'ppt', 'rs', 'wind']
        for f_name in field_list:
            try: 
                self.weather['fields'][f_name] = config.get(
                    weather_sec, f_name+'_field')
            except:
                logging.error('  ERROR: WEATHER {}_field must be set in the INI'.format(f_name))
                sys.exit()
        ## Units
        for f_name in field_list:
            if f_name == 'date':
                continue
            elif self.weather['fields'][f_name] is not None:
                try: 
                    self.weather['units'][f_name] = config.get(
                        weather_sec, f_name+'_units')
                except:
                    logging.error(
                        '  ERROR: WEATHER {}_units must be set in the INI'.format(f_name))
                    sys.exit()

        ## Snow and snow depth are optional
        try: self.weather['fields']['snow'] = config.get(weather_sec, 'snow_field')
        except: self.weather['fields']['snow'] = None
        try: self.weather['fields']['snow_depth'] = config.get(weather_sec, 'depth_field')
        except: self.weather['fields']['snow_depth'] = None
        if self.weather['fields']['snow'] is not None:
            try: self.weather['units']['snow'] = config.get(weather_sec, 'snow_units')
            except:                     
                logging.error('  ERROR: WEATHER {}_units must be set in the INI'.format('snow'))
                sys.exit()
        elif self.weather['fields']['snow_depth'] is not None:
            try:  self.weather['units']['snow_depth'] = config.get(weather_sec, 'depth_units')
            except:                     
                logging.error('  ERROR: WEATHER {}_units must be set in the INI'.format('depth'))
                sys.exit()
                
        ## Tdew can be set or computed from Q (specific humidity)
        try: self.weather['fields']['tdew'] = config.get(weather_sec, 'tdew_field')
        except: self.weather['fields']['tdew'] = None
        try: self.weather['fields']['q'] = config.get(weather_sec, 'q_field')
        except: self.weather['fields']['q'] = None
        if self.weather['fields']['tdew'] is not None:
            try: self.weather['units']['tdew'] = config.get(weather_sec, 'tdew_units')
            except:                     
                logging.error('  ERROR: WEATHER {}_units must be set in the INI'.format('tdew'))
                sys.exit()
        elif self.weather['fields']['q'] is not None:
            try:  self.weather['units']['q'] = config.get(weather_sec, 'q_units')
            except:                     
                logging.error('  ERROR: WEATHER {}_units must be set in the INI'.format('q'))
                sys.exit()

        ## CO2 correction factors are optional
        try: self.weather['fields']['co2_grass'] = config.get(weather_sec, 'co2_grass_field')
        except: self.weather['fields']['co2_grass'] = None
        try: self.weather['fields']['co2_trees'] = config.get(weather_sec, 'co2_trees_field')
        except: self.weather['fields']['co2_trees'] = None
        try: self.weather['fields']['co2_c4'] = config.get(weather_sec, 'co2_c4_field')
        except: self.weather['fields']['co2_c4'] = None
        ## For now, assume values are always 0-1, eventually let user change this?
        self.weather['units']['co2_grass'] = None
        self.weather['units']['co2_trees'] = None
        self.weather['units']['co2_c4'] = None
        if self.co2_flag:
            logging.info('  CO2 correction')
            try: self.co2_grass_crops = sorted(list(util.parse_int_set(
                config.get(crop_et_sec, 'co2_grass_list'))))
            except: self.co2_grass_crops = []
            try: self.co2_trees_crops = sorted(list(util.parse_int_set(
                config.get(crop_et_sec, 'co2_trees_list'))))
            except: self.co2_trees_crops = []
            try: self.co2_c4_crops = sorted(list(util.parse_int_set(
                config.get(crop_et_sec, 'co2_c4_list'))))
            except: self.co2_c4_crops = []
            logging.info('    Grass (C3): {}'.format(self.co2_grass_crops))
            logging.info('    Trees (C3): {}'.format(self.co2_trees_crops))
            logging.info('    C4: {}'.format(self.co2_c4_crops))
            
        ## Wind speeds measured at heights other than 2m will be scaled
        try: 
            self.weather['wind_height'] = config.getfloat(
                weather_sec, 'wind_height')
        except: 
            self.weather['wind_height'] = 2
            
        ## Check weather parameters
        if not os.path.isdir(self.weather['ws']):
            logging.error(
                ('  ERROR: The weather data folder does not '+
                 'exist\n  %s') % self.weather['ws'])
            sys.exit()
        ## Check units
        units_list = (
            ['c', 'mm', 'm/s', 'mj/m2', 'mj/m^2', 'kg/kg'] + 
            ['k', 'f', 'in*100', 'in', 'w/m2', 'w/m^2'])
        for k,v in self.weather['units'].items():
            if v is not None and v.lower() not in units_list:
                logging.error(
                    '  ERROR: {0} units {1} are not currently supported'.format(k,v))
                sys.exit()
    
##def get_date_params(date_str='1/1/1950', date_fmt='%m/%d/%Y'):
##    dt = datetime.strptime(date_str, date_fmt)
##    return dt.year, dt.month, dt.day, dt.timetuple().tm_yday

  
##def read_cell_txt_files(static_ws=os.getcwd()):
##    """ """
##    if not os.path.isdir(static_ws):
##        logging.warning(
##            'crop_et_data.read_cell_txt_files(): static workspace not found')
##        sys.exit()
##    cet = CropETData()
##
##    # Init cells with property info
##    fn = os.path.join(static_ws, 'ETCellsProperties.txt')
##    print '\nRead Cell Properties:', fn
##    et_cells = et_cell.read_et_cells_properties(fn)
##
##    # Add the crop to cells
##    fn = os.path.join(static_ws, 'ETCellsCrops.txt')
##    print '\nRead Cell crops:', fn
##    et_cell.read_et_cells_crops(fn, et_cells)
##
##    # Add mean cuttings
##    fn = os.path.join(static_ws, 'MeanCuttings.txt')
##    print '\nRead mean cuttings:', fn
##    et_cell.read_mean_cuttings(fn, et_cells)
##    cet.set_et_cells(et_cells)
##
##    fn = os.path.join(static_ws, 'CropParams.txt')
##    print '\nRead Crop Parameters:', fn
##    cet.set_crop_parameters(fn)
##
##    fn = os.path.join(static_ws, 'CropCoefs.txt')
##    print '\nRead Crop Coefficients:', fn
##    cet.set_crop_coefficients(fn)
##    return cet

if __name__ == '__main__':
    pass
    ##data = CropETData()
    ##data.set_et_cells_properties(os.path.join(txt_ws, 'ETCellsProperties.txt'))
    ##data.set_et_cells_crops(os.path.join(txt_ws, 'ETCellsCrops.txt'))
    ##data.set_mean_cuttings(os.path.join(txt_ws, 'MeanCuttings.txt'))
    ##data.set_crop_parameters(os.path.join(txt_ws, 'CropParams.txt'))
    ##data.set_crop_coefficients(os.path.join(txt_ws, 'CropCoefs.txt'))
