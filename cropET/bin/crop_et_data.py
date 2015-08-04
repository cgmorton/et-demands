#!/usr/bin/env python

import ConfigParser
import datetime
import logging
import os
import sys

import numpy as np

import et_cell

class CropETData():
    def __init__(self):
        """ """
        self.et_cells = {}
        
        ### From PenmanMonteithManager & modPM.vb
        self.crop_one_reducer = 0.9
        
        ## False sets crop 1 to alfalfa peak with no cuttings
        ## True sets crop 1 to nonpristine alfalfa w/cuttings
        self.crop_one_flag = True  

        ## Also in crop_parameters.py
        self.cgdd_main_doy = 1
        self.cgdd_winter_doy = 274

        ## Static file names
        ## DEADBEEF - These needed to be pre-initialized/declared for some reason
        self.cell_properties_path =  os.path.join('static', 'ETCellsProperties.txt')
        self.cell_crops_path =  os.path.join('static', 'ETCellsCrops.txt')
        self.cell_cuttings_path = os.path.join('static', 'MeanCuttings.txt')
        self.crop_params_path = os.path.join('static', 'CropParams.txt')
        self.crop_coefs_path = os.path.join('static', 'CropCoefs.txt')

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
        project_ws = config.get(crop_et_sec, 'project_folder')
        crop_et_ws = config.get(crop_et_sec, 'crop_et_folder')
        if not os.path.isdir(project_ws):
            logging.critical(
                'ERROR: The project folder does not exist\n  %s' % project_ws)
            sys.exit()
        elif not os.path.isdir(crop_et_ws):
            logging.critical(
                'ERROR: The project folder does not exist\n  %s' % crop_et_ws)
            sys.exit()

        ## Basin   
        self.basin_id = config.get(crop_et_sec, 'basin_id')
        logging.info('  Basin: {}'.format(self.basin_id))

        ## Input/output folders
        pmdata_ws = os.path.join(project_ws, config.get(crop_et_sec, 'pmdata_folder'))
        static_ws = os.path.join(project_ws, config.get(crop_et_sec, 'static_folder'))
        self.output_ws = os.path.join(project_ws, config.get(crop_et_sec, 'et_folder'))
        self.stats_ws = os.path.join(project_ws, config.get(crop_et_sec, 'et_folder'))
        if not os.path.isdir(self.output_ws):
           os.makedirs(self.output_ws)
        if not os.path.isdir(self.stats_ws):
           os.makedirs(self.stats_ws)

        ## Input/output folders
        start_date = config.get(crop_et_sec, 'start_date')
        end_date = config.get(crop_et_sec, 'end_date')

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

        ## Static cell/crop files
        static_list = [
            [self.cell_properties_path, 'cell_properties_name', 'ETCellsProperties.txt'],
            [self.cell_crops_path, 'cell_crops_name', 'ETCellsCrops.txt'],
            [self.cell_cuttings_path, 'cell_cuttings_name', 'MeanCuttings.txt'],
            [self.crop_params_path, 'crop_params_name', 'CropParams.txt'],
            [self.crop_coefs_path, 'crop_coefs_name', 'CropCoefs.txt']]
        for static_path, static_var, static_default in static_list:
            try:
                static_name = config.get(crop_et_sec, static_var)
                static_path = os.path.join(static_ws, static_name)
            except:
                static_path = os.path.join(static_ws, static_default)
                logging.debug('  {0} = {1}'.format(static_var, static_default))
            if not os.path.isfile(static_path):
                logging.error('ERROR: The static file {} does not exist'.format(
                    static_path))
                sys.exit()

                
        ## RefET parameters
        self.refet = {}
        self.refet['fields'] = {}
        self.refet['units'] = {}
        self.refet['ws'] = os.path.join(
            project_ws, config.get(refet_sec, 'refet_folder'))
        self.refet['type'] = config.get(refet_sec, 'refet_type').lower()
        if self.refet['type'] not in ['eto', 'etr']:
            logging.error('  ERROR: RefET type must be ETo or ETr')
            sys.exit()
        self.refet['format'] = config.get(refet_sec, 'name_format')
        self.refet['header_lines'] = config.getint(refet_sec, 'header_lines')
        self.refet['names_line'] = config.getint(refet_sec, 'names_line')
        self.refet['delimiter'] = config.get(refet_sec, 'delimiter')
        
        ## Field names and units
        try: 
            self.refet['fields']['date'] = config.get(refet_sec, 'date_field')
        except: 
            logging.error('  ERROR: REFET date_field must set in the INI')
            sys.exit()
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
        self.weather['ws'] = os.path.join(
            project_ws, config.get(weather_sec, 'weather_folder'))
        self.weather['format'] = config.get(weather_sec, 'name_format')
        self.weather['header_lines'] = config.getint(weather_sec, 'header_lines')
        self.weather['names_line'] = config.getint(weather_sec, 'names_line')
        self.weather['delimiter'] = config.get(weather_sec, 'delimiter')
        
        ## Field names 
        ## The following fields are mandatory 
        ## DEADBEEF - Are snow and snow depth required?
        field_list = ['date', 'tmin', 'tmax', 'ppt', 'rs', 'wind']
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
        except:  self.weather['fields']['snow'] = None
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
        except:  self.weather['fields']['tdew'] = None
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
            ['c', 'mm', 'm/s', 'mj/m2', 'kg/kg'] + 
            ['k', 'f', 'in*100', 'in', 'w/m^2'])
        for k,v in self.weather['units'].items():
            if v is not None and v.lower() not in units_list:
                logging.error(
                    '  ERROR: {0} units {1} are not currently supported'.format(k,v))
                sys.exit()
    
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
            obj = et_cell.ETCell()
            obj.init_properties_from_row(row)
            obj.source_file_properties = fn
            self.et_cells[obj.cell_id] = obj

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
            if cell_id not in self.et_cells:
                logging.error(
                    'read_et_cells_crops(), cell_id %s not found' % cell_id)
                sys.exit()
            obj = self.et_cells[cell_id]
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
        a = a[skip_rows:]
        for i, line in enumerate(a):
            row = line.split(delimiter)
            cell_id = row[1]
            if cell_id not in self.et_cells.keys():
                logging.error(
                    'crop_et_data.static_mean_cuttings(), cell_id %s not found' % cell_id)
                sys.exit()
            obj = self.et_cells[cell_id]
            obj.init_cuttings_from_row(row)
            ##obj.source_file_cuttings = fn
            ##self.et_cells[cell_id] = obj

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
