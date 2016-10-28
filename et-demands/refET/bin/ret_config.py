#!/usr/bin/env python

import ConfigParser
import datetime
import pandas as pd
import logging
import os
import sys

class RefETConfig():
    def __init__(self):
        """ """

    def __str__(self):
        """ """
        return '<RefETConfig>'

    # ref et configuration
    
    def read_refet_ini(self, ini_path, debug_flag = False):
        """Read and parse INI file
    
        This reads and processes configuration data
    
        Args:
            ini_path: configuration (initialization) file path
            debug_flag (bool): If True, write debug level comments to debug.txt

        Returns:
            None
        """

        logging.info('  INI: {}'.format(os.path.basename(ini_path)))

        # Check that INI file can be read
        
        config = ConfigParser.ConfigParser()
        try:
            ini = config.readfp(open(ini_path))
            if debug_flag: 
                cfg_path = os.path.join(os.getcwd(), "test_ret.cfg")
                with open(cfg_path, 'wb') as cf: config.write(cf)
        except:
            logging.error('\nERROR: Config file \n' + ini_path +
                          '\ncould not be read.  It is not an input file or does not exist.\n')
            sys.exit()
        project_sec = 'PROJECT'    # required
        meta_sec = 'RET_META'    # required
        input_met_sec = 'INMET'    # required
        output_ret_sec = 'OUTRET'    # required
        output_met_sec = 'OUTMET'    # not required
        units_list = (
            ['c', 'f', 'k'] +
            ['mm', 'mm/d', 'mm/day', 'm/s', 'in*100'] +
            ['in', 'in/d', 'in/day', 'inches', 'inches/d', 'inches/day'] +
            ['mj/m2', 'mj/m^2', 'mj/m2/d', 'mj/m^2/d', 'mj/m2/day', 'mj/m^2/day'] + 
            ['w/m2', 'w/m^2', 'cal/cm2', 'cal/cm2', 'cal/cm2/d', 'cal/cm^2/d'] +
            ['cal/cm2/day', 'cal/cm^2/day', 'langley'] +
            ['mps', 'm/d', 'm/day', 'mpd', 'miles/d', 'miles/day'] +
            ['m', 'meter', 'feet', 'kg/kg'])
        
        # Check that required sections are present
        
        cfgSecs = config.sections()
        if project_sec not in cfgSecs or meta_sec not in cfgSecs or input_met_sec not in cfgSecs or output_ret_sec not in cfgSecs:
            logging.error(
                '\nERROR:  reference et ini file must have following sections:\n'+
                '  [{}], [{}], and [{}]'.format(project_sec, meta_sec, input_met_sec, output_ret_sec))
            sys.exit()
            
        # project specfications
        
        #  project folder need to be full/absolute path
        
        self.project_ws = config.get(project_sec, 'project_folder')
        if not os.path.isdir(self.project_ws):
            logging.critical('ERROR:  project folder does not exist\n  %s' % self.project_ws)
            sys.exit()

        # Basin
        
        try:
            self.basin_id = config.get(project_sec, 'basin_id')
            if self.basin_id is None or self.basin_id == 'None': self.basin_id = 'Default Basin'
        except:
            self.basin_id = 'Default Basin'
        logging.info('  Basin: {}'.format(self.basin_id))

        # Timestep - specify in ini in DMI units
        # options are 'minute', 'hour', 'day', 'month', 'year'

        try:
            self.time_step = config.get(project_sec, 'time_step')
            if self.time_step is None or self.time_step == 'None': self.time_step = 'day'
        except:
            self.time_step = 'day'
        logging.info('  Time step: {}'.format(self.time_step))

        # Timestep quantity - specify an integer

        try:
            tsq = config.getint(project_sec, 'ts_quantity')
            if tsq is None or tsq == 'None':
                self.ts_quantity = int(1)
            else:
                self.ts_quantity = int(tsq)
        except:
            self.ts_quantity = int(1)
        logging.info('  Time step quantity: {}'.format(self.ts_quantity))
        if self.time_step == 'minute':
            self_dmi_timestep = 'instant'
        else:
            self.dmi_timestep = str(self.ts_quantity) + self.time_step
        
        # user starting date

        try:
            sdt = config.get(project_sec, 'start_date')
            if sdt == 'None': sdt = None
        except:
            sdt = None
        if sdt is None: self.start_dt = None
        else: self.start_dt = pd.to_datetime(sdt)

        # ending date

        try:
            edt = config.get(project_sec, 'end_date')
            if edt == 'None': edt = None
        except:
            edt = None
        if edt is None: self.end_dt = None
        else: self.end_dt = pd.to_datetime(edt)

        # Output met flag
        
        try:
            self.output_met_flag = config.getboolean(project_sec, 'output_met_flag')
        except:
            self.output_met_flag = False

        # Set default value for data_structure_type to keep multiprocessing test happy
        
        self.output_met = {}
        self.output_met['data_structure_type'] = 'SF P'
            
        # Average monthly output flag

        try:
            self.avg_monthly_met_flag = config.getboolean(project_sec, 'avg_monthly_met_flag')
        except:
            self.avg_monthly_met_flag = False

        # static (aka) meta data specfications
        
        try:
            self.static_folder = config.get(meta_sec, 'static_folder')
            if self.static_folder is None or self.static_folder == 'None':
                logging.warning("Static workspace set to default 'static'")
                self.static_folder = 'static'
        except:
            logging.warning("Static workspace set to default 'static'")
            self.static_folder = 'static'
        if not os.path.isdir(self.static_folder):
            self.static_folder = os.path.join(self.project_ws, self.static_folder)

        # Met nodes meta data specs
        
        try:
            met_nodes_meta_data_name = config.get(meta_sec, 'met_nodes_meta_data_name')
            if met_nodes_meta_data_name is None or met_nodes_meta_data_name == 'None':
                logging.error('ERROR:  Met nodes meta data data file must be specified')
                sys.exit()
        except:
            logging.error('ERROR:  Met nodes meta data data file must be specified')
            sys.exit()

        # test joined path
        
        self.met_nodes_meta_data_path = os.path.join(self.static_folder, met_nodes_meta_data_name)
        if not os.path.isfile(self.met_nodes_meta_data_path):
            self.met_nodes_meta_data_path = met_nodes_meta_data_name
            
            # test if fully specified path
            
            if not os.path.isfile(self.met_nodes_meta_data_path):
                logging.error('ERROR:  Met nodes meta data file {} does not exist'.format(self.met_nodes_meta_data_path))
                sys.exit()
        logging.info('  Met nodes meta data file: {}'.format(self.met_nodes_meta_data_path))
        if '.xls' in self.met_nodes_meta_data_path.lower():
            self.mnmd_delimiter = ','
            try:
                self.met_nodes_meta_data_ws = config.get(meta_sec, 'met_nodes_meta_data_ws')
                if self.met_nodes_meta_data_ws is None or self.met_nodes_meta_data_ws == 'None': 
                    logging.error('\nERROR: Worksheet name must be specified for\n' + self.met_nodes_meta_data_path + ".\n")
                    sys.exit()
            except:
                logging.error('\nERROR: Worksheet name must be specified for\n' + self.met_nodes_meta_data_path + ".\n")
                sys.exit()
        else:
            try:
                self.mnmd_delimiter = config.get(meta_sec, 'mnmd_delimiter')
                if self.mnmd_delimiter is None or self.mnmd_delimiter == 'None': 
                    self.mnmd_delimiter = ','
                else:
                    if self.mnmd_delimiter not in [' ', ',', '\\t']: self.mnmd_delimiter = ','
                    if "\\" in self.mnmd_delimiter and "t" in self.mnmd_delimiter:
                        self.mnmd_delimiter = self.mnmd_delimiter.replace('\\t', '\t')
            except:
                self.mnmd_delimiter = ','
        try:
            self.mnmd_header_lines = config.getint(meta_sec, 'mnmd_header_lines')
            if self.mnmd_header_lines is None: self.mnmd_header_lines = 1
        except:
            self.mnmd_header_lines = 1
        try:
            self.mnmd_names_line = config.getint(meta_sec, 'mnmd_names_line')
            if self.mnmd_names_line is None: self.mnmd_names_line = 1
        except:
            self.mnmd_names_line = 1

        # elevation units

        try:
            self.elev_units = config.get(meta_sec, 'elev_units')
            if self.elev_unit is None or self.elev_units == 'None': self.elev_units = 'feet'
        except:
            self.elev_units = 'feet'
        
        # input met data parameters
        
        self.input_met = {}
        self.input_met['fields'] = {}
        self.input_met['units'] = {}

        # fnspec - parameter extension to file name specification

        self.input_met['fnspec'] = {}
        self.input_met['wsspec'] = {}
        self.input_met['ws'] = config.get(input_met_sec, 'input_met_folder')
        
        # input met folder could be full or relative path
        # Assume relative paths or from  project folder
        
        if os.path.isdir(self.input_met['ws']):
            pass
        elif (not os.path.isdir(self.input_met['ws']) and
              os.path.isdir(os.path.join(self.project_ws, self.input_met['ws']))):
            self.input_met['ws'] = os.path.join(self.project_ws, self.input_met['ws'])
        else:
            logging.error('ERROR:  input met data folder {} does not exist'.format(self.input_met['ws']))
            sys.exit()
        if not os.path.isdir(self.input_met['ws']):
            logging.error(('  ERROR:  input met data folder does not ' +
                 'exist\n  %s') % self.input_met['ws'])
            sys.exit()
            
        self.input_met['file_type'] = config.get(input_met_sec, 'file_type')
        self.input_met['data_structure_type'] = config.get(input_met_sec, 'data_structure_type').upper()
        self.input_met['name_format'] = config.get(input_met_sec, 'name_format')
        self.input_met['header_lines'] = config.getint(input_met_sec, 'header_lines')
        self.input_met['names_line'] = config.getint(input_met_sec, 'names_line')
        try:
            self.input_met['delimiter'] = config.get(input_met_sec, 'delimiter')
            if self.input_met['delimiter'] is None or self.input_met['delimiter'] == 'None': 
                self.input_met['delimiter'] = ','
            else:
                if self.input_met['delimiter'] not in [' ', ',', '\\t']: self.input_met['delimiter'] = ','
                if "\\" in self.input_met['delimiter'] and "t" in self.input_met['delimiter']:
                    self.input_met['delimiter'] = self.input_met['delimiter'].replace('\\t', '\t')
        except:
                self.input_met['delimiter'] = ','

        # Date can be read directly or computed from year, month, and day
        
        try: self.input_met['fields']['date'] = config.get(input_met_sec, 'date_field')
        except: self.input_met['fields']['date'] = None
        try: self.input_met['fields']['year'] = config.get(input_met_sec, 'year_field')
        except: self.input_met['fields']['year'] = None
        try: self.input_met['fields']['month'] = config.get(input_met_sec, 'month_field')
        except: self.input_met['fields']['month'] = None
        try: self.input_met['fields']['day'] = config.get(input_met_sec, 'day_field')
        except: self.input_met['fields']['day'] = None
        try: self.input_met['fields']['doy'] = config.get(input_met_sec, 'doy_field')
        except: self.input_met['fields']['doy'] = None
        if self.input_met['fields']['date'] is not None:
            logging.info('  INMET: Reading date from date column')
        elif (self.input_met['fields']['year'] is not None and
              self.input_met['fields']['month'] is not None and
              self.input_met['fields']['day'] is not None):
            logging.info('  INMET: Reading date from year, month, and day columns')
        else:
            logging.error('  ERROR: INMET date_field (or year, month, and '+
                          'day fields) must be set in  INI')
            sys.exit()                  
        
        # Wind speeds measured at heights other than 2m are scaled

        try: self.input_met['wind_height'] = config.getfloat(input_met_sec, 'wind_height')
        except: self.input_met['wind_height'] = 2,0

        # Thorton and Running Solar Radiation Estimation Coefficients

        try: self.input_met['TR_b0'] = config.getfloat(input_met_sec, 'TR_b0')
        except: self.input_met['TR_b0'] = 0.0307075712855
        try: self.input_met['TR_b1'] = config.getfloat(input_met_sec, 'TR_b1')
        except: self.input_met['TR_b1'] = 0.1960418743712
        try: self.input_met['TR_b2'] = config.getfloat(input_met_sec, 'TR_b2')
        except: self.input_met['TR_b2'] = -0.2454592897026
        
        # Data filling support files - all optional if all time series data of parameter exists
        # Files should exist in static data folder

        # average monthly maximum temperature file
        
        try:
            fn = config.get(input_met_sec, 'avgm_tmax_name')
            if fn is None or fn == 'None': 
                self.input_met['avgm_tmax_path'] = None
                self.input_met['avgm_tmax_header_lines'] = 1
                self.input_met['avgm_tmax_delimitor'] = ','
            else:
                self.input_met['avgm_tmax_path'] = os.path.join(self.static_folder, fn)
                try:
                    self.input_met['avgm_tmax_header_lines'] = config.getint(input_met_sec, 'avgm_tmax_header_lines')
                    if self.input_met['avgm_tmax_header_lines'] is None: self.input_met['avgm_tmax_header_lines'] = 1
                except:
                    self.input_met['avgm_tmax_header_lines'] = 1
                if '.xls' in self.input_met['avgm_tmax_path'].lower():
                    self.input_met['avgm_tmax_delimitor'] = ','
                    try:
                        self.input_met['avgm_tmax_ws'] = config.get(input_met_sec, 'avgm_tmax_ws')
                        if self.input_met['avgm_tmax_ws'] is None or self.input_met['avgm_tmax_ws'] == 'None': 
                            logging.error('\nERROR: Worksheet name must be specified for\n' + self.input_met['avgm_tmax_path'] + ".\n")
                            sys.exit()
                    except:
                        logging.error('\nERROR: Worksheet name must be specified for\n' + self.input_met['avgm_tmax_path'] + ".\n")
                        sys.exit()
                else:
                    try:
                        self.input_met['avgm_tmax_delimitor'] = config.get(input_met_sec, 'avgm_tmax_delimiter')
                        if self.input_met['avgm_tmax_delimitor'] is None or self.input_met['avgm_tmax_delimitor'] == 'None': 
                            self.input_met['avgm_tmax_delimitor'] = ','
                        else:
                            if self.input_met['avgm_tmax_delimitor'] not in [' ', ',', '\\t']: self.input_met['avgm_tmax_delimitor'] = ','
                            if "\\" in self.input_met['avgm_tmax_delimitor'] and "t" in self.input_met['avgm_tmax_delimitor']:
                                self.input_met['avgm_tmax_delimitor'] = self.input_met['avgm_tmax_delimitor'].replace('\\t', '\t')
                    except:
                        self.input_met['avgm_tmax_delimitor'] = ','
        except:
            self.input_met['avgm_tmax_path'] = None
            self.input_met['avgm_tmax_delimitor'] = ','
            self.input_met['avgm_tmax_header_lines'] = 1

        # average monthly minimum temperature file
        
        try:
            fn = config.get(input_met_sec, 'avgm_tmin_name')
            if fn is None or fn == 'None': 
                self.input_met['avgm_tmin_path'] = None
                self.input_met['avgm_tmin_header_lines'] = 1
                self.input_met['avgm_tmin_delimitor'] = ','
            else:
                self.input_met['avgm_tmin_path'] = os.path.join(self.static_folder, fn)
                try:
                    self.input_met['avgm_tmin_header_lines'] = config.getint(input_met_sec, 'avgm_tmin_header_lines')
                    if self.input_met['avgm_tmin_header_lines'] is None: self.input_met['avgm_tmin_header_lines'] = 1
                except:
                    self.input_met['avgm_tmin_header_lines'] = 1
                if '.xls' in self.input_met['avgm_tmin_path'].lower():
                    self.input_met['avgm_tmin_delimitor'] = ','
                    try:
                        self.input_met['avgm_tmin_ws'] = config.get(input_met_sec, 'avgm_tmin_ws')
                        if self.input_met['avgm_tmin_ws'] is None or self.input_met['avgm_tmin_ws'] == 'None': 
                            logging.error('\nERROR: Worksheet name must be specified for\n' + self.input_met['avgm_tmin_path'] + ".\n")
                            sys.exit()
                    except:
                        logging.error('\nERROR: Worksheet name must be specified for\n' + self.input_met['avgm_tmin_path'] + ".\n")
                        sys.exit()
                else:
                    try:
                        self.input_met['avgm_tmin_delimitor'] = config.get(input_met_sec, 'avgm_tmin_delimiter')
                        if self.input_met['avgm_tmin_delimitor'] is None or self.input_met['avgm_tmin_delimitor'] == 'None': 
                            self.input_met['avgm_tmin_delimitor'] = ','
                        else:
                            if self.input_met['avgm_tmin_delimitor'] not in [' ', ',', '\\t']: self.input_met['avgm_tmin_delimitor'] = ','
                            if "\\" in self.input_met['avgm_tmin_delimitor'] and "t" in self.input_met['avgm_tmin_delimitor']:
                                self.input_met['avgm_tmin_delimitor'] = self.input_met['avgm_tmin_delimitor'].replace('\\t', '\t')
                    except:
                        self.input_met['avgm_tmin_delimitor'] = ','
        except:
            self.input_met['avgm_tmin_path'] = None
            self.input_met['avgm_tmin_delimitor'] = ','
            self.input_met['avgm_tmin_header_lines'] = 1

        # average monthly Ko (dewpoint depression) file
        
        try:
            fn = config.get(input_met_sec, 'avgm_Ko_name')
            if fn is None or fn == 'None': 
                self.input_met['avgm_Ko_path'] = None
                self.input_met['avgm_Ko_header_lines'] = 1
                self.input_met['avgm_Ko_delimitor'] = ','
            else:
                self.input_met['avgm_Ko_path'] = os.path.join(self.static_folder, fn)
                try:
                    self.input_met['avgm_Ko_header_lines'] = config.getint(input_met_sec, 'avgm_Ko_header_lines')
                    if self.input_met['avgm_Ko_header_lines'] is None: self.input_met['avgm_Ko_header_lines'] = 1
                except:
                    self.input_met['avgm_Ko_header_lines'] = 1
                if '.xls' in self.input_met['avgm_Ko_path'].lower():
                    self.input_met['avgm_Ko_delimitor'] = ','
                    try:
                        self.input_met['avgm_Ko_ws'] = config.get(input_met_sec, 'avgm_Ko_ws')
                        if self.input_met['avgm_Ko_ws'] is None or self.input_met['avgm_Ko_ws'] == 'None': 
                            logging.error('\nERROR: Worksheet name must be specified for\n' + self.input_met['avgm_Ko_path'] + ".\n")
                            sys.exit()
                    except:
                        logging.error('\nERROR: Worksheet name must be specified for\n' + self.input_met['avgm_Ko_path'] + ".\n")
                        sys.exit()
                else:
                    try:
                        self.input_met['avgm_Ko_delimitor'] = config.get(input_met_sec, 'avgm_Ko_delimiter')
                        if self.input_met['avgm_Ko_delimitor'] is None or self.input_met['avgm_Ko_delimitor'] == 'None': 
                            self.input_met['avgm_Ko_delimitor'] = ','
                        else:
                            if self.input_met['avgm_Ko_delimitor'] not in [' ', ',', '\\t']: self.input_met['avgm_Ko_delimitor'] = ','
                            if "\\" in self.input_met['avgm_Ko_delimitor'] and "t" in self.input_met['avgm_Ko_delimitor']:
                                self.input_met['avgm_Ko_delimitor'] = self.input_met['avgm_Ko_delimitor'].replace('\\t', '\t')
                    except:
                        self.input_met['avgm_Ko_delimitor'] = ','
        except:
            self.input_met['avgm_Ko_path'] = None
            self.input_met['avgm_Ko_delimitor'] = ','
            self.input_met['avgm_Ko_header_lines'] = 1

        # average monthly wind file
        
        try:
            fn = config.get(input_met_sec, 'avgm_wind_name')
            if fn is None or fn == 'None': 
                self.input_met['avgm_wind_path'] = None
                self.input_met['avgm_wind_header_lines'] = 1
                self.input_met['avgm_wind_delimitor'] = ','
            else:
                self.input_met['avgm_wind_path'] = os.path.join(self.static_folder, fn)
                try:
                    self.input_met['avgm_wind_header_lines'] = config.getint(input_met_sec, 'avgm_wind_header_lines')
                    if self.input_met['avgm_wind_header_lines'] is None: self.input_met['avgm_wind_header_lines'] = 1
                except:
                    self.input_met['avgm_wind_header_lines'] = 1
                if '.xls' in self.input_met['avgm_wind_path'].lower():
                    self.input_met['avgm_wind_delimitor'] = ','
                    try:
                        self.input_met['avgm_wind_ws'] = config.get(input_met_sec, 'avgm_wind_ws')
                        if self.input_met['avgm_wind_ws'] is None or self.input_met['avgm_wind_ws'] == 'None': 
                            logging.error('\nERROR: Worksheet name must be specified for\n' + self.input_met['avgm_wind_path'] + ".\n")
                            sys.exit()
                    except:
                        logging.error('\nERROR: Worksheet name must be specified for\n' + self.input_met['avgm_wind_path'] + ".\n")
                        sys.exit()
                else:
                    try:
                        self.input_met['avgm_wind_delimitor'] = config.get(input_met_sec, 'avgm_wind_delimiter')
                        if self.input_met['avgm_wind_delimitor'] is None or self.input_met['avgm_wind_delimitor'] == 'None': 
                            self.input_met['avgm_wind_delimitor'] = ','
                        else:
                            if self.input_met['avgm_wind_delimitor'] not in [' ', ',', '\\t']: self.input_met['avgm_wind_delimitor'] = ','
                            if "\\" in self.input_met['avgm_wind_delimitor'] and "t" in self.input_met['avgm_wind_delimitor']:
                                self.input_met['avgm_wind_delimitor'] = self.input_met['avgm_wind_delimitor'].replace('\\t', '\t')
                    except:
                        self.input_met['avgm_wind_delimitor'] = ','
        except:
            self.input_met['avgm_wind_path'] = None
            self.input_met['avgm_wind_delimitor'] = ','
            self.input_met['avgm_wind_header_lines'] = 1
        
        # input met data file name specifications, field names, and units
        
        # Required input met fields for computing reference et

        try:
            self.input_met['fields']['tmax'] = config.get(input_met_sec, 'tmax_field')
            if self.input_met['fields']['tmax'] is None or self.input_met['fields']['tmax'] == 'None':
                logging.error('\nERROR: tmax field name is required\n')
                sys.exit()
            else:
                try: self.input_met['units']['tmax'] = config.get(input_met_sec, 'tmax_units')
                except: self.input_met['units']['tmax'] = 'C'
                try: self.input_met['fnspec']['tmax'] = config.get(input_met_sec, 'tmax_name')
                except: self.input_met['fnspec']['tmax'] = 'Estimated'
                if self.input_met['file_type'].lower() == 'xls' or self.input_met['file_type'].lower() == 'wb':
                    try: 
                        self.input_met['wsspec']['tmax'] = config.get(input_met_sec, 'tmax_ws')
                        if self.input_met['wsspec']['tmax'] is None or self.input_met['wsspec']['tmax'] == 'None':
                            logging.info('  INFO:  INMET: tmax worksheet name set to TMax')
                            self.input_met['wsspec']['tmax'] = 'TMax'
                    except:
                        logging.info('  INFO:  INMET: tmax worksheet name set to TMax')
                        self.input_met['wsspec']['tmax'] = 'TMax'
        except:
            logging.error('\nERROR: tmax field name is required\n')
            sys.exit()

        try:
            self.input_met['fields']['tmin'] = config.get(input_met_sec, 'tmin_field')
            if self.input_met['fields']['tmin'] is None or self.input_met['fields']['tmin'] == 'None':
                logging.error('\nERROR: tmin field name is required\n')
                sys.exit()
            else:
                try: self.input_met['units']['tmin'] = config.get(input_met_sec, 'tmin_units')
                except: self.input_met['units']['tmin'] = 'C'
                try: self.input_met['fnspec']['tmin'] = config.get(input_met_sec, 'tmin_name')
                except: self.input_met['fnspec']['tmin'] = 'Estimated'
                if self.input_met['file_type'].lower() == 'xls' or self.input_met['file_type'].lower() == 'wb':
                    try: 
                        self.input_met['wsspec']['tmin'] = config.get(input_met_sec, 'tmin_ws')
                        if self.input_met['wsspec']['tmin'] is None or self.input_met['wsspec']['tmin'] == 'None':
                            logging.info('  INFO:  INMET: tmin worksheet name set to TMin')
                            self.input_met['wsspec']['tmin'] = 'TMin'
                    except:
                        logging.info('  INFO:  INMET: tmin worksheet name set to TMin')
                        self.input_met['wsspec']['tmin'] = 'TMin'
        except:
            logging.error('\nERROR: tmin field name is required\n')
            sys.exit()

        # optional input met fields and units - unprovided fields are estimated if needed for ref et computations
        
        try:
            self.input_met['fields']['ppt'] = config.get(input_met_sec, 'ppt_field')
            if self.input_met['fields']['ppt'] is None or self.input_met['fields']['ppt'] == 'None':
                self.input_met['fields']['ppt'] = 'Prcp'
                self.input_met['units']['ppt'] = 'mm/day'
                self.input_met['fnspec']['ppt'] = 'Estimated'
            else:
                try: self.input_met['units']['ppt'] = config.get(input_met_sec, 'ppt_units')
                except: self.input_met['units']['ppt'] = 'mm/day'
                try: self.input_met['fnspec']['ppt'] = config.get(input_met_sec, 'ppt_name')
                except: self.input_met['fnspec']['ppt'] = 'Estimated'
                if self.input_met['file_type'].lower() == 'xls' or self.input_met['file_type'].lower() == 'wb':
                    try: 
                        self.input_met['wsspec']['ppt'] = config.get(input_met_sec, 'ppt_ws')
                        if self.input_met['wsspec']['ppt'] is None or self.input_met['wsspec']['ppt'] == 'None':
                            logging.info('  INFO:  INMET: precip worksheet name set to Prcp')
                            self.input_met['wsspec']['ppt'] = 'Prcp'
                    except:
                        logging.info('  INFO:  INMET: precip worksheet name set to Prcp')
                        self.input_met['wsspec']['ppt'] = 'Prcp'
        except:
            self.input_met['fields']['ppt'] = 'Prcp'
            self.input_met['units']['ppt'] = 'mm/day'
            self.input_met['fnspec']['ppt'] = 'Estimated'

        try:
            self.input_met['fields']['wind'] = config.get(input_met_sec, 'wind_field')
            if self.input_met['fields']['wind'] is None or self.input_met['fields']['wind'] == 'None':
                self.input_met['fields']['wind'] = 'Wind'
                self.input_met['units']['wind'] = 'mps'
                self.input_met['fnspec']['wind'] = 'Estimated'
            else:
                try: self.input_met['units']['wind'] = config.get(input_met_sec, 'wind_units')
                except: self.input_met['units']['wind'] = 'mps'
                try: self.input_met['fnspec']['wind'] = config.get(input_met_sec, 'wind_name')
                except: self.input_met['fnspec']['wind'] = self.input_met['fields']['wind']
                if self.input_met['file_type'].lower() == 'xls' or self.input_met['file_type'].lower() == 'wb':
                    try: 
                        self.input_met['wsspec']['wind'] = config.get(input_met_sec, 'wind_ws')
                        if self.input_met['wsspec']['wind'] is None or self.input_met['wsspec']['wind'] == 'None':
                            logging.info('  INFO:  INMET: wind worksheet name set to Wind')
                            self.input_met['wsspec']['wind'] = 'Wind'
                    except:
                        logging.info('  INFO:  INMET: wind worksheet name set to Wind')
                        self.input_met['wsspec']['wind'] = 'Wind'
        except:
            self.input_met['fields']['wind'] = 'Wind'
            self.input_met['units']['wind'] = 'mps'
            self.input_met['fnspec']['wind'] = 'Estimated'

        try:
            self.input_met['fields']['rs'] = config.get(input_met_sec, 'rs_field')
            if self.input_met['fields']['rs'] is None or self.input_met['fields']['rs'] == 'None':
                self.input_met['fields']['rs'] = 'Rs'
                self.input_met['units']['rs'] = 'MJ/m2'
                self.input_met['fnspec']['rs'] = 'Estimated'
            else:
                try: self.input_met['units']['rs'] = config.get(input_met_sec, 'rs_units')
                except: self.input_met['units']['rs'] = 'MJ/m2'
                try: self.input_met['fnspec']['rs'] = config.get(input_met_sec, 'rs_name')
                except: self.input_met['fnspec']['rs'] = self.input_met['fields']['rs']
                if self.input_met['file_type'].lower() == 'xls' or self.input_met['file_type'].lower() == 'wb':
                    try: 
                        self.input_met['wsspec']['rs'] = config.get(input_met_sec, 'rs_ws')
                        if self.input_met['wsspec']['rs'] is None or self.input_met['wsspec']['rs'] == 'None':
                            logging.info('  INFO:  INMET: Rs worksheet name set to Rs')
                            self.input_met['wsspec']['rs'] = 'Rs'
                    except:
                        logging.info('  INFO:  INMET: Rs worksheet name set to Rs')
                        self.input_met['wsspec']['rs'] = 'Rs'
        except:
            self.input_met['fields']['rs'] = 'Rs'
            self.input_met['units']['rs'] = 'MJ/m2'
            self.input_met['fnspec']['rs'] = 'Estimated'
        
        try:
            self.input_met['fields']['snow'] = config.get(input_met_sec, 'snow_field')
            if self.input_met['fields']['snow'] is None or self.input_met['fields']['snow'] == 'None':
                self.input_met['fields']['snow'] = 'Snow'
                self.input_met['units']['snow'] = 'mm/day'
                self.input_met['fnspec']['snow'] = 'Estimated'
            else:
                try: self.input_met['units']['snow'] = config.get(input_met_sec, 'snow_units')
                except: self.input_met['units']['snow'] = 'mm/day'
                try: self.input_met['fnspec']['snow'] = config.get(input_met_sec, 'snow_name')
                except: self.input_met['fnspec']['snow'] = self.input_met['fields']['snow']
                if self.input_met['file_type'].lower() == 'xls' or self.input_met['file_type'].lower() == 'wb':
                    try: 
                        self.input_met['wsspec']['snow'] = config.get(input_met_sec, 'snow_ws')
                        if self.input_met['wsspec']['snow'] is None or self.input_met['wsspec']['snow'] == 'None':
                            logging.info('  INFO:  INMET: snow worksheet name set to Snow')
                            self.input_met['wsspec']['snow'] = 'Snow'
                    except:
                        logging.info('  INFO:  INMET: snow worksheet name set to Snow')
                        self.input_met['wsspec']['snow'] = 'Snow'
        except:
            self.input_met['fields']['snow'] = 'Snow'
            self.input_met['units']['snow'] = 'mm/day'
            self.input_met['fnspec']['snow'] = 'Estimated'

        try:
            self.input_met['fields']['snow_depth'] = config.get(input_met_sec, 'depth_field')
            if self.input_met['fields']['snow_depth'] is None or self.input_met['fields']['snow_depth'] == 'None':
                self.input_met['fields']['snow_depth'] = 'SDep'
                self.input_met['units']['snow_depth'] = 'mm'
                self.input_met['fnspec']['snow_depth'] = 'Estimated'
            else:
                try: self.input_met['units']['snow_depth'] = config.get(input_met_sec, 'depth_units')
                except: self.input_met['units']['snow_depth'] = 'mm'
                try: self.input_met['fnspec']['snow_depth'] = config.get(input_met_sec, 'depth_name')
                except: self.input_met['fnspec']['snow_depth'] = self.input_met['fields']['snow_depth']
                if self.input_met['file_type'].lower() == 'xls' or self.input_met['file_type'].lower() == 'wb':
                    try: self.input_met['wsspec']['snow_depth'] = config.get(input_met_sec, 'depth_ws')
                    except:
                        logging.error('  ERROR: INMET {}ws (worksheet name) must be set in  INI'.format(depth_ws))
                        sys.exit()
                    try: 
                        self.input_met['wsspec']['snow_depth'] = config.get(input_met_sec, 'depth_ws')
                        if self.input_met['wsspec']['snow_depth'] is None or self.input_met['wsspec']['snow_depth'] == 'None':
                            logging.info('  INFO:  INMET: snow depth worksheet name set to SDepth')
                            self.input_met['wsspec']['snow_depth'] = 'SDepth'
                    except:
                        logging.info('  INFO:  INMET: snow depth worksheet name set to SDepth')
                        self.input_met['wsspec']['snow_depth'] = 'SDepth'
        except:
            self.input_met['fields']['snow_depth'] = 'SDep'
            self.input_met['units']['snow_depth'] = 'mm'
            self.input_met['fnspec']['snow_depth'] = 'Estimated'

        # Dewpoint temperature can be set or computed from Q (specific humidity)
        # Field that is provided is used to estimate humidity
        
        try:
            self.input_met['fields']['tdew'] = config.get(input_met_sec, 'tdew_field')
            if self.input_met['fields']['tdew'] is None or self.input_met['fields']['tdew'] == 'None':
                self.input_met['fields']['tdew'] = 'TDew'
                self.input_met['units']['tdew'] = 'C'
                self.input_met['fnspec']['tdew'] = 'Estimated'
            else:
                try: self.input_met['units']['tdew'] = config.get(input_met_sec, 'tdew_units')
                except: self.input_met['units']['tdew'] = 'C'
                try: self.input_met['fnspec']['tdew'] = config.get(input_met_sec, 'tdew_name')
                except: self.input_met['fnspec']['tdew'] = self.input_met['fields']['tdew']
                if self.input_met['file_type'].lower() == 'xls' or self.input_met['file_type'].lower() == 'wb':
                    try: 
                        self.input_met['wsspec']['tdew'] = config.get(input_met_sec, 'tdew_ws')
                        if self.input_met['wsspec']['tdew'] is None or self.input_met['wsspec']['tdew'] == 'None':
                            logging.info('  INFO:  INMET: tdew worksheet name set to TDew')
                            self.input_met['wsspec']['tdew'] = 'TDew'
                    except:
                        logging.info('  INFO:  INMET: tdew worksheet name set to TDew')
                        self.input_met['wsspec']['tdew'] = 'TDew'
                self.input_met['fnspec']['q'] = 'Unused'
                self.input_met['fields']['q'] = None
                self.input_met['units']['q'] = 'kg/kg'
        except:
            self.input_met['fields']['tdew'] = 'TDew'
            self.input_met['units']['tdew'] = 'C'
            self.input_met['fnspec']['tdew'] = 'Estimated'
            try:
                self.input_met['fields']['q'] = config.get(input_met_sec, 'q_field')
                if self.input_met['fields']['q'] is None or self.input_met['fields']['q'] == 'None':
                    self.input_met['fields']['q'] = 'q'
                    self.input_met['units']['q'] = 'kg/kg'
                    self.input_met['fnspec']['q'] = 'Unused'
                else:
                    try: self.input_met['units']['q'] = config.get(input_met_sec, 'q_units')
                    except: self.input_met['units']['q'] = 'kg/kg'
                    try: self.input_met['fnspec']['q'] = config.get(input_met_sec, 'q_name')
                    except: self.input_met['fnspec']['q'] = self.input_met['fields']['q']
                    if self.input_met['file_type'].lower() == 'xls' or self.input_met['file_type'].lower() == 'wb':
                        try: 
                            self.input_met['wsspec']['q'] = config.get(input_met_sec, 'q_ws')
                            if self.input_met['wsspec']['q'] is None or self.input_met['wsspec']['q'] == 'None':
                                logging.info('  INFO:  INMET: q worksheet name set to Q')
                                self.input_met['wsspec']['q'] = 'Q'
                        except:
                            logging.info('  INFO:  INMET: q worksheet name set to Q')
                            self.input_met['wsspec']['q'] = 'Q'
            except:
                self.input_met['fields']['q'] = 'q'
                self.input_met['units']['q'] = 'kg/kg'
                self.input_met['fnspec']['q'] = 'Unused'

        # Check units
        
        for k, v in self.input_met['units'].iteritems():
            if v is not None and v.lower() not in units_list:
                logging.error('  ERROR: {0} units {1} are not currently supported'.format(k,v))
                sys.exit()

        # reference et parameters
        
        self.refet_out = {}
        self.refet_out['fields'] = {}
        self.refet_out['units'] = {}

        # fnspec - parameter extension to file name specification

        self.refet_out['fnspec'] = {}
        
        # ref et folder could be full or relative path
        # Assume relative paths or from  project folder
        
        # Output ref et flags
        
        try:
            self.daily_refet_flag = config.getboolean(output_ret_sec, 'daily_refet_flag')
        except:
            logging.debug('    daily_refet_flag = False')
            self.daily_refet_flag = False
        try:
            self.monthly_refet_flag = config.getboolean(output_ret_sec, 'monthly_refet_flag')
        except:
            logging.debug('    monthly_refet_flag = False')
            self.monthly_refet_flag = False
        try:
            self.annual_refet_flag = config.getboolean(output_ret_sec, 'annual_refet_flag')
        except:
            logging.debug('    annual_refet_flag = False')
            self.annual_refet_flag = False
        if self.daily_refet_flag or self.monthly_refet_flag or self.annual_refet_flag:
            self.refet_out_flag = True;
        else:
            self.refet_out_flag = False;

        # Output folders
        
        if self.daily_refet_flag:
            try:
                self.daily_refet_ws = os.path.join(
                    self.project_ws, config.get(output_ret_sec, 'daily_refet_folder'))
                if not os.path.isdir(self.daily_refet_ws):
                   os.makedirs(self.daily_refet_ws)
            except:
                logging.debug('    daily_refet_folder = daily_stats')
                self.daily_refet_ws = 'daily_stats'
        if self.monthly_refet_flag:
            try:
                self.monthly_refet_ws = os.path.join(
                    self.project_ws, config.get(output_ret_sec, 'monthly_refet_folder'))
                if not os.path.isdir(self.monthly_refet_ws):
                   os.makedirs(self.monthly_refet_ws)
            except:
                logging.debug('    monthly_refet_folder = monthly_stats')
                self.monthly_refet_ws = 'monthly_stats'             
        if self.annual_refet_flag:
            try:
                self.annual_refet_ws = os.path.join(
                    self.project_ws, config.get(output_ret_sec, 'annual_refet_folder'))
                if not os.path.isdir(self.annual_refet_ws):
                   os.makedirs(self.annual_refet_ws)
            except:
                logging.debug('    annual_refet_folder = annual_stats')
                self.annual_refet_ws = 'annual_stats'
        self.refet_out['data_structure_type'] = config.get(output_ret_sec, 'data_structure_type').upper()
        self.refet_out['name_format'] = config.get(output_ret_sec, 'name_format')
        self.refet_out['header_lines'] = config.getint(output_ret_sec, 'header_lines')
        if self.refet_out['header_lines'] > 2:
            logging.warning('\nReferemce ET ouput can have maximum of two header lines.')
            self.refet_out['header_lines'] = 2
        self.refet_out['names_line'] = config.getint(output_ret_sec, 'names_line')
        try:
            self.refet_out['delimiter'] = config.get(output_ret_sec, 'delimiter')
            if self.refet_out['delimiter'] is None or self.refet_out['delimiter'] == 'None': 
                self.refet_out['delimiter'] = ','
            else:
                if self.refet_out['delimiter'] not in [' ', ',', '\\t']: self.refet_out['delimiter'] = ','
                if "\\" in self.refet_out['delimiter'] and "t" in self.refet_out['delimiter']:
                    self.refet_out['delimiter'] = self.refet_out['delimiter'].replace('\\t', '\t')
        except:
                self.refet_out['delimiter'] = ','
        if self.refet_out['header_lines'] == 1:
            try:
                self.refet_out['units_in_header'] = config.getboolean(routput_ret_sec, 'units_in_header')
            except:
                    self.refet_out['units_in_header'] = False
        else:
            self.refet_out['units_in_header'] = False

        # date and values formats, etc

        try:
            self.refet_out['daily_date_format'] = config.get(output_ret_sec, 'daily_date_format')
            if self.refet_out['daily_date_format'] is None or self.refet_out['daily_date_format'] == 'None': 
                self.refet_out['daily_date_format'] = '%Y-%m-%d'
        except: self.refet_out['daily_date_format'] = '%Y-%m-%d'
        try: 
            self.refet_out['daily_float_format'] = config.get(output_ret_sec, 'daily_float_format')
            if self.refet_out['daily_float_format'] == 'None': self.refet_out['daily_float_format'] = None
        except: self.refet_out['daily_float_format'] = None
        try:
            self.refet_out['monthly_date_format'] = config.get(output_ret_sec, 'monthly_date_format')
            if self.refet_out['monthly_date_format'] is None or self.refet_out['monthly_date_format'] == 'None': 
                self.refet_out['monthly_date_format'] = '%Y-%m'
        except: self.refet_out['monthly_date_format'] = '%Y-%m'
        try: 
            self.refet_out['monthly_float_format'] = config.get(output_ret_sec, 'monthly_float_format')
            if self.refet_out['monthly_float_format'] == 'None': self.refet_out['monthly_float_format'] = None
        except: self.refet_out['monthly_float_format'] = None
        try:
            self.refet_out['annual_date_format'] = config.get(output_ret_sec, 'annual_date_format')
            if self.refet_out['monthly_date_format'] is None or self.refet_out['monthly_date_format'] == 'None': 
                self.refet_out['annual_date_format'] = '%Y'
        except: self.refet_out['annual_date_format'] = '%Y'
        try: 
            self.refet_out['annual_float_format'] = config.get(output_ret_sec, 'annual_float_format')
            if self.refet_out['annual_float_format'] == 'None': self.refet_out['annual_float_format'] = None
        except: self.refet_out['annual_float_format'] = None

        # Date or Year, Month, Day or both and/or DOY can be posted

        try: self.refet_out['fields']['date'] = config.get(output_ret_sec, 'date_field')
        except: self.refet_out['fields']['date'] = None
        try: self.refet_out['fields']['year'] = config.get(output_ret_sec, 'year_field')
        except: self.refet_out['fields']['year'] = None
        try: self.refet_out['fields']['month'] = config.get(output_ret_sec, 'month_field')
        except: self.refet_out['fields']['month'] = None
        try: self.refet_out['fields']['day'] = config.get(output_ret_sec, 'day_field')
        except: self.refet_out['fields']['day'] = None
        try: self.refet_out['fields']['doy'] = config.get(output_ret_sec, 'doy_field')
        except: self.refet_out['fields']['doy'] = None
        if self.refet_out['fields']['date'] is not None:
            logging.info('  OUTRET: Posting date from date column')
        elif (self.refet_out['fields']['year'] is not None and
              self.refet_out['fields']['month'] is not None and
              self.refet_out['fields']['day'] is not None):
            logging.info('  OUTRET: Posting date from year, month, and day columns')
        else:
            logging.error('  ERROR: refet date_field (or year, month, and ' +
                          'day fields) must be set in  INI')
            sys.exit()                  
        try: 
            self.refet_out['ret_units'] = config.get(output_ret_sec, 'refet_units')
        except: 
            logging.error('  ERROR: OUTRET etref_units must set in  INI')
            sys.exit()

        # ref et methods

        self.refet_out['ret_method'] = config.get(output_ret_sec, 'ret_method')
        if self.refet_out['ret_method'] is None or self.refet_out['ret_method'] == 'None':
            self.refet_out['ret_method'] = 'asceg'
        if self.refet_out['ret_method'].lower() not in ['penm', 'kimo', 'kimr', 'pretay', 'fao56', 'ascer', 'asceg', 'harg']:
            logging.error('  ERROR: RET method ' + self.refet_out['ret_method'] + ' is incorrect.')
            sys.exit()
        self.refet_out['etr_method'] = config.get(output_ret_sec, 'etr_method')
        if self.refet_out['etr_method'] is None or self.refet_out['etr_method'] == 'None':
            self.refet_out['etr_method'] = 'ASCEr'
        if self.refet_out['etr_method'].lower() not in ['penm', 'kimr', 'pretay', 'fao56', 'ascer', 'harg']:
            logging.error('  ERROR: ETr method ' + self.refet_out['etr_method'] + ' is incorrect.')
            sys.exit()
        self.refet_out['eto_method'] = config.get(output_ret_sec, 'eto_method')
        if self.refet_out['eto_method'] is None or self.refet_out['eto_method'] == 'None':
            self.refet_out['eto_method'] = 'asceg'
        if self.refet_out['eto_method'].lower() not in ['penm', 'kimo', 'pretay', 'fao56', 'asceg', 'harg']:
            logging.error('  ERROR: ETo method ' + self.refet_out['eto_method'] + ' is incorrect.')
            sys.exit()
            
        # output ref data file name specifications, field names, and units - all optional but should have at least one

        # generic ret, etr and eto output

        self.refet_out['units']['ret'] = self.refet_out['ret_units']
        try:
            self.refet_out['fields']['ret'] = config.get(output_ret_sec, 'ret_field')
            if self.refet_out['fields']['ret'] is None or self.refet_out['fields']['ret'] == 'None':
                self.refet_out['fnspec']['ret'] = 'Unused'
                self.refet_out['fields']['ret'] = 'RET'
            else:    # etr is being posted - set file name spec
                self.refet_out['fnspec']['ret'] = 'RET'
        except:
            self.refet_out['fnspec']['ret'] = 'Unused'
            self.refet_out['fields']['ret'] = 'RET'

        self.refet_out['units']['etr'] = self.refet_out['ret_units']
        try:
            self.refet_out['fields']['etr'] = config.get(output_ret_sec, 'etr_field')
            if self.refet_out['fields']['etr'] is None or self.refet_out['fields']['etr'] == 'None':
                self.refet_out['fnspec']['etr'] = 'Unused'
                self.refet_out['fields']['etr'] = 'ETr'
            else:    # etr is being posted - set file name spec
                self.refet_out['fnspec']['etr'] = 'ETr'
        except:
            self.refet_out['fnspec']['etr'] = 'Unused'
            self.refet_out['fields']['etr'] = 'ETr'

        self.refet_out['units']['eto'] = self.refet_out['ret_units']
        try:
            self.refet_out['fields']['eto'] = config.get(output_ret_sec, 'eto_field')
            if self.refet_out['fields']['eto'] is None or self.refet_out['fields']['eto'] == 'None':
                self.refet_out['fnspec']['eto'] = 'Unused'
                self.refet_out['fields']['eto'] = 'ETo'
            else:    # etr is being posted - set file name spec
                self.refet_out['fnspec']['eto'] = 'ETo'
        except:
            self.refet_out['fnspec']['eto'] = 'Unused'
            self.refet_out['fields']['eto'] = 'ETo'

        # specific method output
        
        self.refet_out['units']['penm'] = self.refet_out['ret_units']
        try:
            self.refet_out['fields']['penm'] = config.get(output_ret_sec, 'penm_field')
            if self.refet_out['fields']['penm'] is None or self.refet_out['fields']['penm'] == 'None':
                self.refet_out['fnspec']['penm'] = 'Unused'
                self.refet_out['fields']['penm'] = 'Penman'
            else:    # etr is being posted - set file name spec
                self.refet_out['fnspec']['penm'] = 'Penman'
        except:
            self.refet_out['fnspec']['penm'] = 'Unused'
            self.refet_out['fields']['penm'] = 'Penman'

        self.refet_out['units']['pretay'] = self.refet_out['ret_units']
        try:
            self.refet_out['fields']['pretay'] = config.get(output_ret_sec, 'pretay_field')
            if self.refet_out['fields']['pretay'] is None or self.refet_out['fields']['pretay'] == 'None':
                self.refet_out['fnspec']['pretay'] = 'Unused'
                self.refet_out['fields']['pretay'] = 'PreTay'
            else:    # pretay is being posted - set file name spec
                self.refet_out['fnspec']['pretay'] = 'PreTay'
        except:
            self.refet_out['fnspec']['pretay'] = 'Unused'
            self.refet_out['fields']['pretay'] = 'PreTay'

        self.refet_out['units']['kimo'] = self.refet_out['ret_units']
        try:
            self.refet_out['fields']['kimo'] = config.get(output_ret_sec, 'kimo_field')
            if self.refet_out['fields']['kimo'] is None or self.refet_out['fields']['kimo'] == 'None':
                self.refet_out['fnspec']['kimo'] = 'Unused'
                self.refet_out['fields']['kimo'] = "KimbPeng"
            else:    # etr is being posted - set file name spec
                self.refet_out['fnspec']['kimo'] = "KimbPeng"
        except:
            self.refet_out['fnspec']['kimo'] = 'Unused'
            self.refet_out['fields']['kimo'] = "KimbPeng"

        self.refet_out['units']['kimr'] = self.refet_out['ret_units']
        try:
            self.refet_out['fields']['kimr'] = config.get(output_ret_sec, 'kimr_field')
            if self.refet_out['fields']['kimr'] is None or self.refet_out['fields']['kimr'] == 'None':
                self.refet_out['fnspec']['kimr'] = 'Unused'
                self.refet_out['fields']['kimr'] = "KimbPen"
            else:    # etr is being posted - set file name spec
                self.refet_out['fnspec']['kimr'] = "KimbPen"
        except:
            self.refet_out['fnspec']['kimr'] = 'Unused'
            self.refet_out['fields']['kimr'] = "KimbPen"

        self.refet_out['units']['fao56'] = self.refet_out['ret_units']
        try:
            self.refet_out['fields']['fao56'] = config.get(output_ret_sec, 'fao56_field')
            if self.refet_out['fields']['fao56'] is None or self.refet_out['fields']['fao56'] == 'None':
                self.refet_out['fnspec']['fao56'] = 'Unused'
                self.refet_out['fields']['fao56'] = "FAO56PM"
            else:    # etr is being posted - set file name spec
                self.refet_out['fnspec']['fao56'] = "FAO56PM"
        except:
            self.refet_out['fnspec']['fao56'] = 'Unused'
            self.refet_out['fields']['fao56'] = "FAO56PM"

        self.refet_out['units']['ascer'] = self.refet_out['ret_units']
        try:
            self.refet_out['fields']['ascer'] = config.get(output_ret_sec, 'ascer_field')
            if self.refet_out['fields']['ascer'] is None or self.refet_out['fields']['ascer'] == 'None':
                self.refet_out['fnspec']['ascer'] = 'Unused'
                self.refet_out['fields']['ascer'] = 'ASCEr'
            else:    # ascer is being posted - set file name spec
                self.refet_out['fnspec']['ascer'] = 'ASCEr'
        except:
            self.refet_out['fnspec']['ascer'] = 'Unused'
            self.refet_out['fields']['ascer'] = 'ASCEr'

        self.refet_out['units']['asceg'] = self.refet_out['ret_units']
        try:
            self.refet_out['fields']['asceg'] = config.get(output_ret_sec, 'asceg_field')
            if self.refet_out['fields']['asceg'] is None or self.refet_out['fields']['asceg'] == 'None':
                self.refet_out['fnspec']['asceg'] = 'Unused'
                self.refet_out['fields']['asceg'] = 'asceg'
            else:    # ASCEo is being posted - set file name spec
                self.refet_out['fnspec']['asceg'] = 'asceg'
        except:
            self.refet_out['fnspec']['asceg'] = 'Unused'
            self.refet_out['fields']['asceg'] = 'asceg'

        self.refet_out['units']['harg'] = self.refet_out['ret_units']
        try:
            self.refet_out['fields']['harg'] = config.get(output_ret_sec, 'harg_field')
            if self.refet_out['fields']['harg'] is None or self.refet_out['fields']['harg'] == 'None':
                self.refet_out['fnspec']['harg'] = 'Unused'
                self.refet_out['fields']['harg'] = '85Harg'
            else:    # harg is being posted - set file name spec
                self.refet_out['fnspec']['harg'] = '85Harg'
        except:
            self.refet_out['fnspec']['harg'] = 'Unused'
            self.refet_out['fields']['harg'] = '85Harg'

        # output met data file name specifications, field names, and units - all optional
        
        try:
            self.refet_out['fields']['tmax'] = config.get(output_ret_sec, 'tmax_field')
            if self.refet_out['fields']['tmax'] is None or self.refet_out['fields']['tmax'] == 'None':
                self.refet_out['fnspec']['tmax'] = 'Unused'
                self.refet_out['fields']['tmax'] = 'TMax'
                self.refet_out['units']['tmax'] = 'C'
            else:    # tmax is being posted - get units
                self.refet_out['fnspec']['tmax'] = 'TMax'
                try: 
                    self.refet_out['units']['tmax'] = config.get(output_ret_sec, 'tmax_units')
                    if self.refet_out['units']['tmax'] is None: self.refet_out['units']['tmax'] = 'C'
                except: self.refet_out['units']['tmax'] = 'C'
        except:
            self.refet_out['fnspec']['tmax'] = 'Unused'
            self.refet_out['fields']['tmax'] = 'TMax'
            self.refet_out['units']['tmax'] = 'C'

        try:
            self.refet_out['fields']['tmin'] = config.get(output_ret_sec, 'tmin_field')
            if self.refet_out['fields']['tmin'] is None or self.refet_out['fields']['tmin'] == 'None':
                self.refet_out['fnspec']['tmin'] = 'Unused'
                self.refet_out['fields']['tmin'] = 'TMin'
                self.refet_out['units']['tmin'] = 'C'
            else:    # tmin is being posted - get units
                self.refet_out['fnspec']['tmin'] = 'TMin'
                try: 
                    self.refet_out['units']['tmin'] = config.get(output_ret_sec, 'tmin_units')
                    if self.refet_out['units']['tmin'] is None: self.refet_out['units']['TMin'] = 'C'
                except: self.refet_out['units']['tmin'] = 'C'
        except:
            self.refet_out['fnspec']['tmin'] = 'Unused'
            self.refet_out['fields']['tmin'] = 'TMin'
            self.refet_out['units']['tmin'] = 'C'

        try:
            self.refet_out['fields']['ppt'] = config.get(output_ret_sec, 'ppt_field')
            if self.refet_out['fields']['ppt'] is None or self.refet_out['fields']['ppt'] == 'None':
                self.refet_out['fnspec']['ppt'] = 'Unused'
                self.refet_out['fields']['ppt'] = 'Precip'
                self.refet_out['units']['ppt'] = 'In*100'
            else:    # ppt is being posted - get units
                self.refet_out['fnspec']['ppt'] = 'Precip'
                try: 
                    self.refet_out['units']['ppt'] = config.get(output_ret_sec, 'ppt_units')
                    if self.refet_out['units']['ppt'] is None: self.refet_out['units']['ppt'] = 'In*100'
                except: self.refet_out['units']['ppt'] = 'In*100'
        except:
            self.refet_out['fnspec']['ppt'] = 'Unused'
            self.refet_out['fields']['ppt'] = 'Precip'
            self.refet_out['units']['ppt'] = 'In*100'

        try:
            self.refet_out['fields']['snow'] = config.get(output_ret_sec, 'snow_field')
            if self.refet_out['fields']['snow'] is None or self.refet_out['fields']['snow'] == 'None':
                self.refet_out['fnspec']['snow'] = 'Unused'
                self.refet_out['fields']['snow'] = 'Snow'
                self.refet_out['units']['snow'] = 'In*100'
            else:    # snow is being posted - get units
                self.refet_out['fnspec']['snow'] = 'Snow'
                try: 
                    self.refet_out['units']['snow'] = config.get(output_ret_sec, 'snow_units')
                    if self.refet_out['units']['snow'] is None: self.refet_out['units']['snow'] = 'In*100'
                except: self.refet_out['units']['snow'] = 'In*100'
        except:
            self.refet_out['fnspec']['snow'] = 'Unused'
            self.refet_out['fields']['snow'] = 'Snow'
            self.refet_out['units']['snow'] = 'In*100'

        try:
            self.refet_out['fields']['snow_depth'] = config.get(output_ret_sec, 'depth_field')
            if self.refet_out['fields']['snow_depth'] is None or self.refet_out['fields']['snow_depth'] == 'None':
                self.refet_out['fnspec']['snow_depth'] = 'Unused'
                self.refet_out['fields']['snow_depth'] = 'SDep'
                self.refet_out['units']['snow_depth'] = 'In'
            else:    # snow depth is being posted - get units
                self.refet_out['fnspec']['snow_depth'] = 'SDep'
                try: 
                    self.refet_out['units']['snow_depth'] = config.get(output_ret_sec, 'depth_units')
                    if self.refet_out['units']['snow_depth'] is None: self.refet_out['units']['snow_depth'] = 'In'
                except: self.refet_out['units']['snow_depth'] = 'In'
        except:
            self.refet_out['fnspec']['snow_depth'] = 'Unused'
            self.refet_out['fields']['snow_depth'] = 'SDep'
            self.refet_out['units']['snow_depth'] = 'In'

        try:
            self.refet_out['fields']['rs'] = config.get(output_ret_sec, 'rs_field')
            if self.refet_out['fields']['rs'] is None or self.refet_out['fields']['rs'] == 'None':
                self.refet_out['fnspec']['rs'] = 'Unused'
                self.refet_out['fields']['rs'] = 'Rs'
                self.refet_out['units']['rs'] = 'MJ/m2'
            else:    # rs is being posted - get units
                self.refet_out['fnspec']['rs'] = 'Rs'
                try: 
                    self.refet_out['units']['rs'] = config.get(output_ret_sec, 'rs_units')
                    if self.refet_out['units']['rs'] is None: self.refet_out['units']['rs'] = 'MJ/m2'
                except: self.refet_out['units']['rs'] = 'MJ/m2'
        except:
            self.refet_out['fnspec']['rs'] = 'Unused'
            self.refet_out['fields']['rs'] = 'Rs'
            self.refet_out['units']['rs'] = 'MJ/m2'

        try:
            self.refet_out['fields']['wind'] = config.get(output_ret_sec, 'wind_field')
            if self.refet_out['fields']['wind'] is None or self.refet_out['fields']['wind'] == 'None':
                self.refet_out['fnspec']['wind'] = 'Unused'
                self.refet_out['fields']['wind'] = 'Wind'
                self.refet_out['units']['wind'] = 'm/s'
            else:    # wind is being posted - get units
                self.refet_out['fnspec']['wind'] = 'Wind'
                try: 
                    self.refet_out['units']['wind'] = config.get(output_ret_sec, 'wind_units')
                    if self.refet_out['units']['wind'] is None: self.refet_out['units']['wind'] = 'm/s'
                except: self.refet_out['units']['wind'] = 'm/s'
        except:
            self.refet_out['fnspec']['wind'] = 'Unused'
            self.refet_out['fields']['wind'] = 'Wind'
            self.refet_out['units']['wind'] = 'm/s'

        try:
            self.refet_out['fields']['tdew'] = config.get(output_ret_sec, 'tdew_field')
            if self.refet_out['fields']['tdew'] is None or self.refet_out['fields']['tdew'] == 'None':
                self.refet_out['fnspec']['tdew'] = 'Unused'
                self.refet_out['fields']['tdew'] = 'TDew'
                self.refet_out['units']['tdew'] = 'C'
            else:    # tmin is being posted - get units
                self.refet_out['fnspec']['tdew'] = 'TDew'
                try: 
                    self.refet_out['units']['tdew'] = config.get(output_ret_sec, 'tdew_units')
                    if self.refet_out['units']['tdew'] is None: self.refet_out['units']['TDew'] = 'C'
                except: self.refet_out['units']['tdew'] = 'C'
        except:
            self.refet_out['fnspec']['tdew'] = 'Unused'
            self.refet_out['fields']['tdew'] = 'TDew'
            self.refet_out['units']['tdew'] = 'C'

        if self.input_met['fnspec']['q'].lower().lower() == 'unused':
            self.refet_out['fnspec']['q'] = 'Unused'
            self.refet_out['fields']['q'] = 'q'
            self.refet_out['units']['q'] = 'kg/kg'
        else:
            try:
                self.refet_out['fields']['q'] = config.get(output_ret_sec, 'q_field')
                if self.refet_out['fields']['q'] is None or self.refet_out['fields']['q'] == 'None':
                    self.refet_out['fnspec']['q'] = 'Unused'
                    self.refet_out['fields']['q'] = 'q'
                    self.refet_out['units']['q'] = 'kg/kg'
                else:    # q is being posted - get units
                    self.refet_out['fnspec']['q'] = 'q'
                    try: 
                        self.refet_out['units']['q'] = config.get(output_ret_sec, 'q_units')
                        if self.refet_out['units']['q'] is None: self.refet_out['units']['q'] = 'kg/kg'
                    except: self.refet_out['units']['q'] = 'kg/kg'
            except:
                self.refet_out['fnspec']['q'] = 'Unused'
                self.refet_out['fields']['q'] = 'q'
                self.refet_out['units']['q'] = 'kg/kg'
                
        # drop unused fields

        all_refet_out_fields = ['date', 'year', 'month', 'day', 'doy', 'tmax', 'tmin', 'ppt', 'snow', 'snow_depth', 'rs', 'wind', 'q', 'tdew', 'ret', 'etr', 'eto', 'penm', 'kimo', 'kimr', 'pretay', 'fao56', 'ascer', 'asceg', 'harg']
        for k, v in self.refet_out['fnspec'].items():
            if not v is None:
                try:
                    if v.lower() == "unused":
                        del self.refet_out['units'][k] 
                        del self.refet_out['fnspec'][k] 
                        del self.refet_out['fields'][k] 
                except: pass
        for k, v in self.refet_out['fields'].items():
            if v is None:
                try: del self.refet_out['fields'][k] 
                except: pass

        # Check units

        for k, v in self.refet_out['units'].iteritems():
            if v is not None and v.lower() not in units_list:
                logging.error('  ERROR: {0} units {1} are not currently supported'.format(k, v))
                sys.exit()

        # set up header lines

        self.used_refet_out_fields = [fn for fn in all_refet_out_fields if fn in self.refet_out['fields'].keys()]
        self.refet_out['data_out_fields'] = [fn for fn in self.used_refet_out_fields if fn not in ['date', 'year', 'month', 'day', 'doy']]
        self.refet_out['refet_out_fields'] = [fn for fn in self.used_refet_out_fields if fn in ['ret', 'etr', 'eto', 'penm', 'kimo', 'kimr', 'pretay', 'fao56', 'ascer', 'asceg', 'harg']]
        self.refet_out['out_data_fields'] = []
        if self.refet_out['header_lines'] == 2:
            for fc, fn in enumerate(self.used_refet_out_fields):
                if fc == 0:
                    self.refet_out['daily_header1'] = self.refet_out['fields'][fn]
                    self.refet_out['daily_header2'] = "Units"
                else: 
                    self.refet_out['daily_header1'] = self.refet_out['daily_header1'] + self.refet_out['delimiter'] + self.refet_out['fields'][fn]
                    if fn in self.refet_out['data_out_fields']:
                        self.refet_out['daily_header2'] = self.refet_out['daily_header2'] + self.refet_out['delimiter'] + self.refet_out['units'][fn]
                        self.refet_out['out_data_fields'].append(self.refet_out['fields'][fn])
                    else:
                        self.refet_out['daily_header2'] = self.refet_out['daily_header2'] + self.refet_out['delimiter']
        else:
            for fc, fn in enumerate(self.used_refet_out_fields):
                if fc == 0:
                    self.refet_out['daily_header1'] = self.refet_out['fields'][fn]
                else: 
                    if fn in self.refet_out['data_out_fields']:
                        self.refet_out['daily_header1'] = self.refet_out['daily_header1'] + self.refet_out['delimiter'] + self.refet_out['fields'][fn]
                        if self.refet_out['units_in_header']:
                            self.refet_out['daily_header1'] = self.refet_out['daily_header1'] + " (" + self.refet_out['units'][fn] + ")"
                        self.refet_out['out_data_fields'].append(self.refet_out['fields'][fn])
                    else:
                        self.refet_out['daily_header1'] = self.refet_out['daily_header1'] + self.refet_out['delimiter'] + self.refet_out['fields'][fn]
            self.refet_out['daily_header2'] = ""
        if 'day' in self.refet_out['fields'] and self.refet_out['fields']['day'] is not None: 
            drop_string = self.refet_out['delimiter'] + self.refet_out['fields']['day']
            self.refet_out['monthly_header1'] = self.refet_out['daily_header1'].replace(drop_string, '')
            self.refet_out['monthly_header2'] = self.refet_out['daily_header2'].replace(drop_string, '')
        else:
            self.refet_out['monthly_header1'] = self.refet_out['daily_header1']
            self.refet_out['monthly_header2'] = self.refet_out['daily_header2']
        if 'doy' in self.refet_out['fields'] and self.refet_out['fields']['doy'] is not None: 
            drop_string = self.refet_out['delimiter'] + self.refet_out['fields']['doy']
            self.refet_out['monthly_header1'] = self.refet_out['monthly_header1'].replace(drop_string, '')
            self.refet_out['monthly_header2'] = self.refet_out['monthly_header2'].replace(drop_string, '')
        if 'month' in self.refet_out['fields'] and self.refet_out['fields']['month'] is not None: 
            drop_string = self.refet_out['delimiter'] + self.refet_out['fields']['month']
            self.refet_out['annual_header1'] = self.refet_out['monthly_header1'].replace(drop_string, '')
            self.refet_out['annual_header2'] = self.refet_out['monthly_header2'].replace(drop_string, '')
        else:
            self.refet_out['annual_header1'] = self.refet_out['monthly_header1']
            self.refet_out['annual_header2'] = self.refet_out['monthly_header2']

        # output met parameters
        
        if self.output_met_flag:
            logging.info('  OUTMET: Filled met data are being posted.')
            
            # output met data parameters
        
            self.output_met = {}
            self.output_met['fields'] = {}
            self.output_met['units'] = {}

            # fnspec - parameter extension to file name specification

            self.output_met['fnspec'] = {}
            self.output_met['wsspec'] = {}
            
            # Output met flags
        
            try:
                self.daily_output_met_flag = config.getboolean(output_met_sec, 'daily_output_met_flag')
            except:
                logging.debug('    daily_output_met_flag = False')
                self.daily_output_met_flag = False
            try:
                self.monthly_output_met_flag = config.getboolean(output_met_sec, 'monthly_output_met_flag')
            except:
                logging.debug('    monthly_output_met_flag = False')
                self.monthly_output_met_flag = False
            try:
                self.annual_output_met_flag = config.getboolean(output_met_sec, 'annual_output_met_flag')
            except:
                logging.debug('    annual_output_met_flag = False')
                self.annual_output_met_flag = False

            # Output folders
        
            if self.daily_output_met_flag:
                try:
                    self.daily_output_met_ws = os.path.join(
                        self.project_ws, config.get(output_met_sec, 'daily_output_met_folder'))
                    if not os.path.isdir(self.daily_output_met_ws):
                        os.makedirs(self.daily_output_met_ws)
                except:
                    logging.debug('    daily_output_met_folder = daily_stats')
                    self.daily_output_met_ws = 'daily_stats'
            if self.monthly_output_met_flag:
                try:
                    self.monthly_output_met_ws = os.path.join(
                        self.project_ws, config.get(output_met_sec, 'monthly_output_met_folder'))
                    if not os.path.isdir(self.monthly_output_met_ws):
                        os.makedirs(self.monthly_output_met_ws)
                except:
                    logging.debug('    monthly_output_met_folder = monthly_stats')
                    self.monthly_output_met_ws = 'monthly_stats'             
            if self.annual_output_met_flag:
                try:
                    self.annual_output_met_ws = os.path.join(
                        self.project_ws, config.get(output_met_sec, 'annual_output_met_folder'))
                    if not os.path.isdir(self.annual_output_met_ws):
                        os.makedirs(self.annual_output_met_ws)
                except:
                    logging.debug('    annual_output_met_folder = annual_stats')
                    self.annual_output_met_ws = 'annual_stats'
            self.output_met['file_type'] = config.get(output_met_sec, 'file_type')
            self.output_met['data_structure_type'] = config.get(output_met_sec, 'data_structure_type').upper()
            self.output_met['name_format'] = config.get(output_met_sec, 'name_format')
            self.output_met['header_lines'] = config.getint(output_met_sec, 'header_lines')
            self.output_met['names_line'] = config.getint(output_met_sec, 'names_line')
            self.output_met['delimiter'] = config.get(output_met_sec, 'delimiter')
            try:
                self.output_met['delimiter'] = config.get(output_met_sec, 'delimiter')
                if self.output_met['delimiter'] is None or self.output_met['delimiter'] == 'None': 
                    self.output_met['delimiter'] = ','
                else:
                    if self.output_met['delimiter'] not in [' ', ',', '\\t']: self.output_met['delimiter'] = ','
                    if "\\" in self.output_met['delimiter'] and "t" in self.output_met['delimiter']:
                        self.output_met['delimiter'] = self.output_met['delimiter'].replace('\\t', '\t')
            except:
                    self.output_met['delimiter'] = ','
            if self.output_met['header_lines'] == 1:
                try:
                    self.output_met['units_in_header'] = config.getboolean(output_met_sec, 'units_in_header')
                except:
                        self.output_met['units_in_header'] = False
            else:
                self.output_met['units_in_header'] = False
            # date and values formats, etc

            try:
                self.output_met['daily_date_format'] = config.get(output_met_sec, 'daily_date_format')
                if self.output_met['daily_date_format'] is None or self.output_met['daily_date_format'] == 'None':
                    if self.output_met['file_type'] == 'xls':
                        self.output_met['daily_date_format'] = 'm/d/yyyy'
                    else:
                        self.output_met['daily_date_format'] = '%Y-%m-%d'
            except:
                if self.output_met['file_type'] == 'xls':
                    self.output_met['daily_date_format'] = 'm/d/yyyy'
                else:
                    self.output_met['daily_date_format'] = '%Y-%m-%d'
            try:
                offset = config.getint(output_met_sec, 'daily_hour_offset')
                if offset is None or offset == 'None':
                    self.output_met['daily_hour_offset'] = int(0)
                else:
                    self.output_met['daily_hour_offset'] = int(offset)
            except: self.output_met['daily_hour_offset'] = int(0)
            try:
                offset = config.getint(output_met_sec, 'daily_minute_offset')
                if offset is None or offset == 'None':
                    self.output_met['daily_minute_offset'] = int(0)
                else:
                    self.output_met['daily_minute_offset'] = int(offset)
            except: self.output_met['daily_minute_offset'] = int(0)
            try: 
                self.output_met['daily_float_format'] = config.get(output_met_sec, 'daily_float_format')
                if self.output_met['daily_float_format'] == 'None': self.output_met['daily_float_format'] = None
            except: self.output_met['daily_float_format'] = None
            try:
                self.output_met['monthly_date_format'] = config.get(output_met_sec, 'monthly_date_format')
                if self.output_met['monthly_date_format'] is None or self.output_met['monthly_date_format'] == 'None':
                    if self.output_met['file_type'] == 'xls':
                        self.output_met['monthly_date_format'] = 'm/yyyy'
                    else:
                        self.output_met['monthly_date_format'] = '%Y-%m'
            except:
                if self.output_met['file_type'] == 'xls':
                    self.output_met['monthly_date_format'] = 'm/yyyy'
                else:
                    self.output_met['monthly_date_format'] = '%Y-%m'
            try:
                offset = config.getint(output_met_sec, 'monthly_hour_offset')
                if offset is None or offset == 'None':
                    self.output_met['monthly_hour_offset'] = int(0)
                else:
                    self.output_met['monthly_hour_offset'] = int(offset)
            except: self.output_met['monthly_hour_offset'] = int(0)
            try:
                offset = config.getint(output_met_sec, 'monthly_minute_offset')
                if offset is None or offset == 'None':
                    self.output_met['monthly_minute_offset'] = int(0)
                else:
                    self.output_met['monthly_minute_offset'] = int(offset)
            except: self.output_met['monthly_minute_offset'] = int(0)
            try: 
                self.output_met['monthly_float_format'] = config.get(output_met_sec, 'monthly_float_format')
                if self.output_met['monthly_float_format'] == 'None': self.output_met['monthly_float_format'] = None
            except: self.output_met['monthly_float_format'] = None
            try:
                self.output_met['annual_date_format'] = config.get(output_met_sec, 'annual_date_format')
                if self.output_met['annual_date_format'] is None or self.output_met['annual_date_format'] == 'None':
                    if self.output_met['file_type'] == 'xls':
                        self.output_met['annual_date_format'] = 'm/yyyy'
                    else:
                        self.output_met['annual_date_format'] = '%Y-%m'
            except:
                if self.output_met['file_type'] == 'xls':
                    self.output_met['annual_date_format'] = 'm/yyyy'
                else:
                    self.output_met['annual_date_format'] = '%Y-%m'
            try:
                offset = config.getint(output_met_sec, 'annual_hour_offset')
                if offset is None or offset == 'None':
                    self.output_met['annual_hour_offset'] = int(0)
                else:
                    self.output_met['annual_hour_offset'] = int(offset)
            except: self.output_met['annual_hour_offset'] = int(0)
            try:
                offset = config.getint(output_met_sec, 'annual_minute_offset')
                if offset is None or offset == 'None':
                    self.output_met['annual_minute_offset'] = int(0)
                else:
                    self.output_met['annual_minute_offset'] = int(offset)
            except: self.output_met['annual_minute_offset'] = int(0)
            try: 
                self.output_met['annual_float_format'] = config.get(output_met_sec, 'annual_float_format')
                if self.output_met['annual_float_format'] == 'None': self.output_met['annual_float_format'] = None
            except: self.output_met['annual_float_format'] = None

            # Date or Year, Month, Day or both and/or DOY can be posted
        
            try: self.output_met['fields']['date'] = config.get(output_met_sec, 'date_field')
            except: self.output_met['fields']['date'] = None
            try: self.output_met['fields']['year'] = config.get(output_met_sec, 'year_field')
            except: self.output_met['fields']['year'] = None
            try: self.output_met['fields']['month'] = config.get(output_met_sec, 'month_field')
            except: self.output_met['fields']['month'] = None
            try: self.output_met['fields']['day'] = config.get(output_met_sec, 'day_field')
            except: self.output_met['fields']['day'] = None
            try: self.output_met['fields']['doy'] = config.get(output_met_sec, 'doy_field')
            except: self.output_met['fields']['doy'] = None
            if self.output_met['fields']['date'] is not None:
                logging.info('  OUTMET: Posting date from date column')
            elif (self.output_met['fields']['year'] is not None and
                  self.output_met['fields']['month'] is not None and
                  self.output_met['fields']['day'] is not None):
                logging.info('  OUTMET: Posting date from year, month, and day columns')
            else:
                logging.error('  ERROR: OUTMET date_field (or year, month, and ' +
                              'day fields) must be set in  INI')
                sys.exit()                  

            # output met data file name specifications, field names, and units
        
            self.output_met['wsspec']['tmax'] = None
            try:
                self.output_met['fields']['tmax'] = config.get(output_met_sec, 'tmax_field')
                if self.output_met['fields']['tmax'] is None or self.output_met['fields']['tmax'] == 'None':
                    self.output_met['fnspec']['tmax'] = 'Unused'
                    self.output_met['fields']['tmax'] = 'TMax'
                    self.output_met['units']['tmax'] = 'C'
                else:    # tmax is being posted - get units and/or file name spec
                    try: 
                        self.output_met['units']['tmax'] = config.get(output_met_sec, 'tmax_units')
                        if self.output_met['units']['tmax'] is None or self.output_met['units']['tmax'] == 'None':
                            self.output_met['units']['tmax'] = 'C'
                    except: self.output_met['units']['tmax'] = 'C'
                    try:
                        self.output_met['fnspec']['tmax'] = config.get(output_met_sec, 'tmax_name')
                        if self.output_met['fnspec']['tmax'] is None or self.output_met['fnspec']['tmax'] == 'None':
                            self.output_met['fnspec']['tmax'] = self.output_met['fields']['tmax']
                    except: self.output_met['fnspec']['tmax'] = self.output_met['fields']['tmax']
                    if self.output_met['file_type'].lower() == 'xls' or self.output_met['file_type'].lower() == 'wb':
                        try: 
                            self.output_met['wsspec']['tmax'] = config.get(output_met_sec, 'tmax_ws')
                            if self.output_met['wsspec']['tmax'] is None or self.output_met['wsspec']['tmax'] == 'None':
                                logging.info('  INFO:  OUTMET: tmax worksheet name set to TMax')
                                self.output_met['wsspec']['tmax'] = 'TMax'
                        except:
                            logging.info('  INFO:  OUTMET: tmax worksheet name set to TMax')
                            self.output_met['wsspec']['tmax'] = 'TMax'
            except:
                self.output_met['fnspec']['tmax'] = 'Unused'
                self.output_met['fields']['tmax'] = 'TMax'
                self.output_met['units']['tmax'] = 'C'

            self.output_met['wsspec']['tmin'] = None
            try:
                self.output_met['fields']['tmin'] = config.get(output_met_sec, 'tmin_field')
                if self.output_met['fields']['tmin'] is None or self.output_met['fields']['tmin'] == 'None':
                    self.output_met['fnspec']['tmin'] = 'Unused'
                    self.output_met['fields']['tmin'] = 'TMin'
                    self.output_met['units']['tmin'] = 'C'
                else:    # tmin is being posted - get units and/or file name spec
                    try: 
                        self.output_met['units']['tmin'] = config.get(output_met_sec, 'tmin_units')
                        if self.output_met['units']['tmin'] is None or self.output_met['units']['tmin'] == 'None':
                            self.output_met['units']['tmin'] = 'C'
                    except: self.output_met['units']['tmin'] = 'C'
                    try:
                        self.output_met['fnspec']['tmin'] = config.get(output_met_sec, 'tmin_name')
                        if self.output_met['fnspec']['tmin'] is None or self.output_met['fnspec']['tmin'] == 'None':
                            self.output_met['fnspec']['tmin'] = self.output_met['fields']['tmin']
                    except: self.output_met['fnspec']['tmin'] = self.output_met['fields']['tmin']
                    if self.output_met['file_type'].lower() == 'xls' or self.output_met['file_type'].lower() == 'wb':
                        try: 
                            self.output_met['wsspec']['tmin'] = config.get(output_met_sec, 'tmin_ws')
                            if self.output_met['wsspec']['tmin'] is None or self.output_met['wsspec']['tmin'] == 'None':
                                logging.info('  INFO:  OUTMET: tmin worksheet name set to TMin')
                                self.output_met['wsspec']['tmin'] = 'TMin'
                        except:
                            logging.info('  INFO:  OUTMET: tmin worksheet name set to TMin')
                            self.output_met['wsspec']['tmin'] = 'TMin'
            except:
                self.output_met['fnspec']['tmin'] = 'Unused'
                self.output_met['fields']['tmin'] = 'TMin'
                self.output_met['units']['tmin'] = 'C'

            self.output_met['wsspec']['tavg'] = None
            try:
                self.output_met['fields']['tavg'] = config.get(output_met_sec, 'tavg_field')
                if self.output_met['fields']['tavg'] is None or self.output_met['fields']['tavg'] == 'None':
                    self.output_met['fnspec']['tavg'] = 'Unused'
                    self.output_met['fields']['tavg'] = 'TAvg'
                    self.output_met['units']['tavg'] = 'C'
                else:    # tavg is being posted - get units and/or file name spec
                    try: 
                        self.output_met['units']['tavg'] = config.get(output_met_sec, 'tavg_units')
                        if self.output_met['units']['tavg'] is None or self.output_met['units']['tavg'] == 'None':
                            self.output_met['units']['tavg'] = 'C'
                    except: self.output_met['units']['tavg'] = 'C'
                    try:
                        self.output_met['fnspec']['tavg'] = config.get(output_met_sec, 'tavg_name')
                        if self.output_met['fnspec']['tavg'] is None or self.output_met['fnspec']['tavg'] == 'None':
                            self.output_met['fnspec']['tavg'] = self.output_met['fields']['tavg']
                    except: self.output_met['fnspec']['tavg'] = self.output_met['fields']['tavg']
                    if self.output_met['file_type'].lower() == 'xls' or self.output_met['file_type'].lower() == 'wb':
                        try: 
                            self.output_met['wsspec']['tavg'] = config.get(output_met_sec, 'tavg_ws')
                            if self.output_met['wsspec']['tavg'] is None or self.output_met['wsspec']['tavg'] == 'None':
                                logging.info('  INFO:  OUTMET: tavg worksheet name set to TAvg')
                                self.output_met['wsspec']['tavg'] = 'TAvg'
                        except:
                            logging.info('  INFO:  OUTMET: tavg worksheet name set to TAvg')
                            self.output_met['wsspec']['tavg'] = 'TAvg'
            except:
                self.output_met['fnspec']['tavg'] = 'Unused'
                self.output_met['fields']['tavg'] = 'TAvg'
                self.output_met['units']['tavg'] = 'C'

            self.output_met['wsspec']['ppt'] = None
            try:
                self.output_met['fields']['ppt'] = config.get(output_met_sec, 'ppt_field')
                if self.output_met['fields']['ppt'] is None or self.output_met['fields']['ppt'] == 'None':
                    self.output_met['fnspec']['ppt'] = 'Unused'
                    self.output_met['fields']['ppt'] = 'Precip'
                    self.output_met['units']['ppt'] = 'In*100'
                else:    # ppt is being posted - get units
                    self.output_met['fnspec']['ppt'] = 'Precip'
                    try: 
                        self.output_met['units']['ppt'] = config.get(output_met_sec, 'ppt_units')
                        if self.output_met['units']['ppt'] is None: self.output_met['units']['ppt'] = 'In*100'
                    except: self.output_met['units']['ppt'] = 'In*100'
                    try:
                        self.output_met['fnspec']['ppt'] = config.get(output_met_sec, 'ppt_name')
                        if self.output_met['fnspec']['ppt'] is None or self.output_met['fnspec']['ppt'] == 'None':
                            self.output_met['fnspec']['ppt'] = self.output_met['fields']['ppt']
                    except: self.output_met['fnspec']['ppt'] = self.output_met['fields']['ppt']
                    if self.output_met['file_type'].lower() == 'xls' or self.output_met['file_type'].lower() == 'wb':
                        try: 
                            self.output_met['wsspec']['ppt'] = config.get(output_met_sec, 'ppt_ws')
                            if self.output_met['wsspec']['ppt'] is None or self.output_met['wsspec']['ppt'] == 'None':
                                logging.info('  INFO:  OUTMET: precip worksheet name set to Prcp')
                                self.output_met['wsspec']['ppt'] = 'Prcp'
                        except:
                            logging.info('  INFO:  OUTMET: precip worksheet name set to Prcp')
                            self.output_met['wsspec']['ppt'] = 'Prcp'
            except:
                self.output_met['fnspec']['ppt'] = 'Unused'
                self.output_met['fields']['ppt'] = 'Precip'
                self.output_met['units']['ppt'] = 'In*100'

            self.output_met['wsspec']['snow'] = None
            try:
                self.output_met['fields']['snow'] = config.get(output_met_sec, 'snow_field')
                if self.output_met['fields']['snow'] is None or self.output_met['fields']['snow'] == 'None':
                    self.output_met['fnspec']['snow'] = 'Unused'
                    self.output_met['fields']['snow'] = 'Snow'
                    self.output_met['units']['snow'] = 'mm/day'
                else:    # snow is being posted - get units and/or file name spec
                    try: 
                        self.output_met['units']['snow'] = config.get(output_met_sec, 'snow_units')
                        if self.output_met['units']['snow'] is None or self.output_met['units']['snow'] == 'None':
                            self.output_met['units']['snow'] = 'mm/day'
                    except: self.output_met['units']['snow'] = 'mm/day'
                    try:
                        self.output_met['fnspec']['snow'] = config.get(output_met_sec, 'snow_name')
                        if self.output_met['fnspec']['snow'] is None or self.output_met['fnspec']['snow'] == 'None':
                            self.output_met['fnspec']['snow'] = self.output_met['fields']['snow']
                    except: self.output_met['fnspec']['snow'] = self.output_met['fields']['snow']
                    if self.output_met['file_type'].lower() == 'xls' or self.output_met['file_type'].lower() == 'wb':
                        try: 
                            self.output_met['wsspec']['snow'] = config.get(output_met_sec, 'snow_ws')
                            if self.output_met['wsspec']['snow'] is None or self.output_met['wsspec']['snow'] == 'None':
                                logging.info('  INFO:  OUTMET: snow worksheet name set to Snow')
                                self.output_met['wsspec']['snow'] = 'Snow'
                        except:
                            logging.info('  INFO:  OUTMET: snow worksheet name set to Snow')
                            self.output_met['wsspec']['snow'] = 'Snow'
            except:
                self.output_met['fnspec']['snow'] = 'Unused'
                self.output_met['fields']['snow'] = 'Snow'
                self.output_met['units']['snow'] = 'mm/day'

            self.output_met['wsspec']['snow_depth'] = None
            try:
                self.output_met['fields']['snow_depth'] = config.get(output_met_sec, 'depth_field')
                if self.output_met['fields']['snow_depth'] is None or self.output_met['fields']['snow_depth'] == 'None':
                    self.output_met['fnspec']['snow_depth'] = 'Unused'
                    self.output_met['fields']['snow_depth'] = 'SDep'
                    self.output_met['units']['snow_depth'] = 'In'
                else:    # snow depth is being posted - get units
                    try: 
                        self.output_met['units']['snow_depth'] = config.get(output_met_sec, 'depth_units')
                        if self.output_met['units']['snow_depth'] is None or self.output_met['units']['snow_depth'] == 'None':
                            self.output_met['units']['snow_depth'] = 'In'
                    except: self.output_met['units']['snow_depth'] = 'In'
                    try:
                        self.output_met['fnspec']['snow_depth'] = config.get(output_met_sec, 'depth_name')
                        if self.output_met['fnspec']['snow_depth'] is None or self.output_met['fnspec']['snow_depth'] == 'None':
                            self.output_met['fnspec']['snow_depth'] = self.output_met['fields']['snow_depth']
                    except: self.output_met['fnspec']['snow_depth'] = self.output_met['fields']['snow_depth']
                    if self.output_met['file_type'].lower() == 'xls' or self.output_met['file_type'].lower() == 'wb':
                        try: 
                            self.output_met['wsspec']['snow_depth'] = config.get(output_met_sec, 'depth_ws')
                            if self.output_met['wsspec']['snow_depth'] is None or self.output_met['wsspec']['snow_depth'] == 'None':
                                logging.info('  INFO:  OUTMET: snow depth worksheet name set to SDepth')
                                self.output_met['wsspec']['snow_depth'] = 'SDepth'
                        except:
                            logging.info('  INFO:  OUTMET: snow depth worksheet name set to SDepth')
                            self.output_met['wsspec']['snow_depth'] = 'SDepth'
            except:
                self.output_met['fnspec']['snow_depth'] = 'Unused'
                self.output_met['fields']['snow_depth'] = 'SDep'
                self.output_met['units']['snow_depth'] = 'In'

            self.output_met['wsspec']['rs'] = None
            try:
                self.output_met['fields']['rs'] = config.get(output_met_sec, 'rs_field')
                if self.output_met['fields']['rs'] is None or self.output_met['fields']['rs'] == 'None':
                    self.output_met['fnspec']['rs'] = 'Unused'
                    self.output_met['fields']['rs'] = 'Rs'
                    self.output_met['units']['rs'] = 'MJ/m2'
                else:    # rs is being posted - get units and/or file name spec
                    try: 
                        self.output_met['units']['rs'] = config.get(output_met_sec, 'rs_units')
                        if self.output_met['units']['rs'] is None or self.output_met['units']['rs'] == 'None':
                            self.output_met['units']['rs'] = 'MJ/m2'
                    except: self.output_met['units']['rs'] = 'MJ/m2'
                    try:
                        self.output_met['fnspec']['rs'] = config.get(output_met_sec, 'rs_name')
                        if self.output_met['fnspec']['rs'] is None or self.output_met['fnspec']['rs'] == 'None':
                            self.output_met['fnspec']['rs'] = self.output_met['fields']['rs']
                    except: self.output_met['fnspec']['rs'] = self.output_met['fields']['rs']
                    if self.output_met['file_type'].lower() == 'xls' or self.output_met['file_type'].lower() == 'wb':
                        try: 
                            self.output_met['wsspec']['rs'] = config.get(output_met_sec, 'rs_ws')
                            if self.output_met['wsspec']['rs'] is None or self.output_met['wsspec']['rs'] == 'None':
                                logging.info('  INFO:  OUTMET: Rs worksheet name set to Rs')
                                self.output_met['wsspec']['rs'] = 'Rs'
                        except:
                            logging.info('  INFO:  OUTMET: Rs worksheet name set to Rs')
                            self.output_met['wsspec']['rs'] = 'Rs'
            except:
                self.output_met['fnspec']['rs'] = 'Unused'
                self.output_met['fields']['rs'] = 'Rs'
                self.output_met['units']['rs'] = 'MJ/m2'

            self.output_met['wsspec']['wind'] = None
            try:
                self.output_met['fields']['wind'] = config.get(output_met_sec, 'wind_field')
                if self.output_met['fields']['wind'] is None or self.output_met['fields']['wind'] == 'None':
                    self.output_met['fnspec']['wind'] = 'Unused'
                    self.output_met['fields']['wind'] = 'Wind'
                    self.output_met['units']['wind'] = 'm/s'
                else:    # wind is being posted - get units and/or file name spec
                    try: 
                        self.output_met['units']['wind'] = config.get(output_met_sec, 'wind_units')
                        if self.output_met['units']['wind'] is None or self.output_met['units']['wind'] == 'None':
                            self.output_met['units']['wind'] = 'm/s'
                    except: self.output_met['units']['wind'] = 'm/s'
                    try:
                        self.output_met['fnspec']['wind'] = config.get(output_met_sec, 'wind_name')
                        if self.output_met['fnspec']['wind'] is None or self.output_met['fnspec']['wind'] == 'None':
                            self.output_met['fnspec']['wind'] = self.output_met['fields']['wind']
                    except: self.output_met['fnspec']['wind'] = self.output_met['fields']['wind']
                    if self.output_met['file_type'].lower() == 'xls' or self.output_met['file_type'].lower() == 'wb':
                        try: 
                            self.output_met['wsspec']['wind'] = config.get(output_met_sec, 'wind_ws')
                            if self.output_met['wsspec']['wind'] is None or self.output_met['wsspec']['wind'] == 'None':
                                logging.info('  INFO:  OUTMET: wind worksheet name set to wind')
                                self.output_met['wsspec']['wind'] = 'wind'
                        except:
                            logging.info('  INFO:  OUTMET: wind worksheet name set to wind')
                            self.output_met['wsspec']['wind'] = 'wind'
            except:
                self.output_met['fnspec']['wind'] = 'Unused'
                self.output_met['fields']['wind'] = 'Wind'
                self.output_met['units']['wind'] = 'm/s'

            self.output_met['wsspec']['tdew'] = None
            try:
                self.output_met['fields']['tdew'] = config.get(output_met_sec, 'tdew_field')
                if self.output_met['fields']['tdew'] is None or self.output_met['fields']['tdew'] == 'None':
                    self.output_met['fnspec']['tdew'] = 'Unused'
                    self.output_met['fields']['tdew'] = 'TDew'
                    self.output_met['units']['tdew'] = 'C'
                else:    # tdew is being posted - get units and/or file name spec
                    try: 
                        self.output_met['units']['tdew'] = config.get(output_met_sec, 'tdew_units')
                        if self.output_met['units']['tdew'] is None or self.output_met['units']['tdew'] == 'None':
                            self.output_met['units']['tdew'] = 'C'
                    except: self.output_met['units']['tdew'] = 'C'
                    try:
                        self.output_met['fnspec']['tdew'] = config.get(output_met_sec, 'tdew_name')
                        if self.output_met['fnspec']['tdew'] is None or self.output_met['fnspec']['tdew'] == 'None':
                            self.output_met['fnspec']['tdew'] = self.output_met['fields']['tdew']
                    except: self.output_met['fnspec']['tdew'] = self.output_met['fields']['tdew']
                    if self.output_met['file_type'].lower() == 'xls' or self.output_met['file_type'].lower() == 'wb':
                        try: 
                            self.output_met['wsspec']['tdew'] = config.get(output_met_sec, 'tdew_ws')
                            if self.output_met['wsspec']['tdew'] is None or self.output_met['wsspec']['tdew'] == 'None':
                                logging.info('  INFO:  OUTMET: tdew worksheet name set to TDew')
                                self.output_met['wsspec']['tdew'] = 'TDew'
                        except:
                            logging.info('  INFO:  OUTMET: tdew worksheet name set to TDew')
                            self.output_met['wsspec']['tdew'] = 'TDew'
            except:
                self.output_met['fnspec']['tdew'] = 'Unused'
                self.output_met['fields']['tdew'] = 'TDew'
                self.output_met['units']['tdew'] = 'C'

            self.output_met['wsspec']['q'] = None
            if self.input_met['fnspec']['q'].lower() == 'unused':
                self.output_met['fnspec']['q'] = 'Unused'
                self.output_met['fields']['q'] = 'Q'
                self.output_met['units']['q'] = 'kg/kg'
            else:
                try:
                    self.output_met['fields']['q'] = config.get(output_met_sec, 'q_field')
                    if self.output_met['fields']['q'] is None or self.output_met['fields']['q'] == 'None':
                        self.output_met['fnspec']['q'] = 'Unused'
                        self.output_met['fields']['q'] = 'Q'
                        self.output_met['units']['q'] = 'kg/kg'
                    else:    # q is being posted - get units and/or file name spec
                        try: 
                            self.output_met['units']['q'] = config.get(output_met_sec, 'q_units')
                            if self.output_met['units']['q'] is None or self.output_met['units']['q'] == 'None':
                                self.output_met['units']['q'] = 'kg/kg'
                        except: self.output_met['units']['q'] = 'kg/kg'
                        try:
                            self.output_met['fnspec']['q'] = config.get(output_met_sec, 'q_name')
                            if self.output_met['fnspec']['q'] is None or self.output_met['fnspec']['q'] == 'None':
                                self.output_met['fnspec']['q'] = self.output_met['fields']['q']
                        except: self.output_met['fnspec']['q'] = self.output_met['fields']['q']
                    if self.output_met['file_type'].lower() == 'xls' or self.output_met['file_type'].lower() == 'wb':
                        try: 
                            self.output_met['wsspec']['q'] = config.get(output_met_sec, 'q_ws')
                            if self.output_met['wsspec']['q'] is None or self.output_met['wsspec']['q'] == 'None':
                                logging.info('  INFO:  OUTMET: q worksheet name set to Q')
                                self.output_met['wsspec']['q'] = 'Q'
                        except:
                            logging.info('  INFO:  OUTMET: q worksheet name set to Q')
                            self.output_met['wsspec']['q'] = 'Q'
                except:
                    self.output_met['fnspec']['q'] = 'Unused'
                    self.output_met['fields']['q'] = 'Q'
                    self.output_met['units']['q'] = 'kg/kg'

            self.output_met['wsspec']['refet'] = None
            try:
                self.output_met['fields']['refet'] = config.get(output_met_sec, 'refet_field')
                if self.output_met['fields']['refet'] is None or self.output_met['fields']['refet'] == 'None':
                    self.output_met['fnspec']['refet'] = 'Unused'
                    self.output_met['fields']['refet'] = 'refet'
                    self.output_met['units']['refet'] = 'mm/day'
                else:    # ref_et is being posted - get units and/or file name spec
                    try: 
                        self.output_met['units']['refet'] = config.get(output_met_sec, 'refet_units')
                        if self.output_met['units']['refet'] is None or self.output_met['units']['refet'] == 'None':
                            self.output_met['units']['refet'] = 'mm/day'
                    except: self.output_met['units']['refet'] = 'mm/day'
                    try:
                        self.output_met['fnspec']['refet'] = config.get(output_met_sec, 'refet_name')
                        if self.output_met['fnspec']['refet'] is None or self.output_met['fnspec']['refet'] == 'None':
                            self.output_met['fnspec']['refet'] = self.output_met['fields']['refet']
                    except: self.output_met['fnspec']['refet'] = self.output_met['fields']['refet']
                    if self.output_met['file_type'].lower() == 'xls' or self.output_met['file_type'].lower() == 'wb':
                        try: 
                            self.output_met['wsspec']['refet'] = config.get(output_met_sec, 'refet_ws')
                            if self.output_met['wsspec']['refet'] is None or self.output_met['wsspec']['refet'] == 'None':
                                logging.info('  INFO:  OUTMET: ref_et worksheet name set to ref_et')
                                self.output_met['wsspec']['refet'] = 'refet'
                        except:
                            logging.info('  INFO:  OUTMET: ref_et worksheet name set to ref_et')
                            self.output_met['wsspec']['refet'] = 'refet'
            except:
                self.output_met['fnspec']['refet'] = 'Unused'
                self.output_met['fields']['refet'] = 'refet'
                self.output_met['units']['refet'] = 'mm/day'

            # drop unused fields
        
            all_output_met_fields = ['date', 'year', 'month', 'day', 'doy', 'tmax', 'tmin', 'tavg', 'ppt', 'snow', 'snow_depth', 'rs', 'wind', 'q', 'tdew', 'refet']
            for k, v in self.output_met['fnspec'].items():
                if not v is None:
                    try:
                        if v.lower() == 'unused':
                            del self.output_met['units'][k] 
                            del self.output_met['fnspec'][k] 
                            del self.output_met['fields'][k] 
                    except: pass
            for k, v in self.output_met['fields'].items():
                if v is None:
                    try: del self.output_met['fields'][k] 
                    except: pass
                    
            # Check units
        
            for k, v in self.output_met['units'].iteritems():
                if v is not None and v.lower() not in units_list:
                    logging.error('  ERROR: {0} units {1} are not currently supported'.format(k,v))
                    sys.exit()

            # set up header lines

            self.used_output_met_fields = [fn for fn in all_output_met_fields if fn in self.output_met['fields'].keys()]
            self.output_met['data_out_fields'] = [fn for fn in self.used_output_met_fields if fn not in ['date', 'year', 'month', 'day', 'doy']]
            self.output_met['out_data_fields'] = []
            if self.output_met['header_lines'] == 2:
                for fc, fn in enumerate(self.used_output_met_fields):
                    if fc == 0:
                        self.output_met['daily_header1'] = self.output_met['fields'][fn]
                        self.output_met['daily_header2'] = "Units"
                    else: 
                        self.output_met['daily_header1'] = self.output_met['daily_header1'] + self.output_met['delimiter'] + self.output_met['fields'][fn]
                        if fn in self.output_met['data_out_fields']:
                            self.output_met['daily_header2'] = self.output_met['daily_header2'] + self.output_met['delimiter'] + self.output_met['units'][fn]
                            self.output_met['out_data_fields'].append(self.output_met['fields'][fn])
                        else:
                            self.output_met['daily_header2'] = self.output_met['daily_header2'] + self.output_met['delimiter']
            else:
                for fc, fn in enumerate(self.used_output_met_fields):
                    if fc == 0:
                        self.output_met['daily_header1'] = self.output_met['fields'][fn]
                    else: 
                        if fn in self.output_met['data_out_fields']:
                            self.output_met['daily_header1'] = self.output_met['daily_header1'] + self.output_met['delimiter'] + self.output_met['fields'][fn]
                            if self.output_met['units_in_header']:
                                self.output_met['daily_header1'] = self.output_met['daily_header1'] + " (" + self.output_met['units'][fn] + ")"
                            self.output_met['out_data_fields'].append(self.output_met['fields'][fn])
                        else:
                            self.output_met['daily_header1'] = self.output_met['daily_header1'] + self.output_met['delimiter'] + self.output_met['fields'][fn]
                self.output_met['daily_header2'] = ""
            if 'day' in self.output_met['fields'] and self.output_met['fields']['day'] is not None: 
                drop_string = self.output_met['delimiter'] + self.output_met['fields']['day']
                self.output_met['monthly_header1'] = self.output_met['daily_header1'].replace(drop_string, '')
                self.output_met['monthly_header2'] = self.output_met['daily_header2'].replace(drop_string, '')
            else:
                self.output_met['monthly_header1'] = self.output_met['daily_header1']
                self.output_met['monthly_header2'] = self.output_met['daily_header2']
            if 'doy' in self.output_met['fields'] and self.output_met['fields']['doy'] is not None: 
                drop_string = self.output_met['delimiter'] + self.output_met['fields']['doy']
                self.output_met['monthly_header1'] = self.output_met['monthly_header1'].replace(drop_string, '')
                self.output_met['monthly_header2'] = self.output_met['monthly_header2'].replace(drop_string, '')
            if 'month' in self.output_met['fields'] and self.output_met['fields']['month'] is not None: 
                drop_string = self.output_met['delimiter'] + self.output_met['fields']['month']
                self.output_met['annual_header1'] = self.output_met['monthly_header1'].replace(drop_string, '')
                self.output_met['annual_header2'] = self.output_met['monthly_header2'].replace(drop_string, '')
            else:
                self.output_met['annual_header1'] = self.output_met['monthly_header1']
                self.output_met['annual_header2'] = self.output_met['monthly_header2']

        # drop unused input met fields
        
        for k, v in self.input_met['fnspec'].items():
            if not v is None:
                try:
                    if v.lower() == 'unused':
                        del self.input_met['units'][k] 
                        del self.input_met['fnspec'][k] 
                        del self.input_met['fields'][k] 
                except: pass

def console_logger(logger = logging.getLogger(''), log_level = logging.INFO):
    # Create console logger

    logger.setLevel(log_level)
    log_console = logging.StreamHandler(stream = sys.stdout)
    log_console.setLevel(log_level)
    log_console.setFormatter(logging.Formatter('%(message)s'))
    logger.addHandler(log_console)
    return logger

def do_tests():
    # Simple testing of functions as developed
    # logger = console_logger(log_level = 'DEBUG')

    logger = console_logger(log_level = logging.DEBUG)
    ini_path = os.getcwd() + os.sep + "ret_template.ini"
    cfg = RefETConfig()
    cfg.read_refet_ini(ini_path, True)
    
if __name__ == '__main__':
    # testing during development
    do_tests()        
