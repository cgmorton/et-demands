#!/usr/bin/env python

import ConfigParser
import datetime
import logging
import os
import sys

import numpy as np
import pandas as pd
import xlrd

class AreaETConfig():
    def __init__(self):
        """ """

    def __str__(self):
        """ """
        return '<AreaETConfig>'

    # area et configuration
    
    def read_aet_ini(self, ini_path, debug_flag = False):
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
                cfg_path = os.path.join(os.getcwd(), "test_aet.cfg")
                with open(cfg_path, 'wb') as cf: config.write(cf)
        except:
            logging.error('\nERROR: Config file \n' + ini_path +
                          '\ncould not be read.  It is not an input file or does not exist.\n')
            sys.exit()

        project_sec = 'PROJECT'    # required
        meta_sec = 'AET_META'    # required
        input_cet_sec = 'INCET'    # required
        output_cet_sec = 'OUTCET'    # not required
        output_cir_sec = 'OUTCIR'    # not required
        output_aet_sec = 'OUTAET'    # not required
        units_list = (
            ['c', 'f', 'k'] +
            ['mm', 'mm/d', 'mm/day', 'm/s', 'in*100', 'in', 'in/d', 'in/day', 'inches/day', 'inches'] +
            ['mj/m2', 'mj/m^2', 'kg/kg', 'w/m2', 'w/m^2'] +
            ['mps', 'm/d', 'm/day', 'mpd', 'miles/d', 'miles/day'] +
            ['m', 'meter', 'feet'] +
            ['cms', 'cfs', 'acre-feet/day', 'acre-feet/month', 'acre-feet/year', 'af/day', 'af/month', 'af/year'] +
            ['kg/kg'] +
            ['fraction'])
        
        # Check that required sections are present
        
        cfgSecs = config.sections()
        if project_sec not in cfgSecs or meta_sec not in cfgSecs or input_cet_sec not in cfgSecs:
            logging.error(
                '\nERROR:  reference et ini file must have following sections:\n'+
                '  [{}], [{}], and [{}]'.format(project_sec, meta_sec, input_cet_sec))
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
        
        # Output cet flag
        
        try:
            self.output_cet_flag = config.getboolean(project_sec, 'output_cet_flag')
        except:
            logging.debug('    output_cet_flag = False')
            self.output_cet_flag = False
        self.output_cet = {}
        self.output_cet['data_structure_type'] = 'SF P'

        # Output cir flag
        
        try:
            self.output_cir_flag = config.getboolean(project_sec, 'output_cir_flag')
        except:
            logging.debug('    output_cir_flag = False')
            self.output_cir_flag = False
        self.output_cir = {}
        self.output_cir['data_structure_type'] = 'SF P'

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
        
        # ET Cells Crops

        try:
            cell_crops_name = config.get(meta_sec, 'cell_crops_name')
            if cell_crops_name is None or cell_crops_name == 'None':
                logging.error('ERROR:  ET Cells crops data file must be specified')
                sys.exit()
        except:
            logging.error('ERROR:  ET Cells crops data file must be specified')
            sys.exit()
        self.cell_crops_path = os.path.join(self.static_folder, cell_crops_name)
        if not os.path.isfile(self.cell_crops_path):
            self.cell_crops_path = cell_crops_name
            if not os.path.isfile(self.cell_crops_path):
                logging.error('ERROR:  ET Cells crops file {} does not exist'.format(self.self.cell_crops_path))
                sys.exit()
        logging.info('  ET Cell crops file: {}'.format(self.cell_crops_path))
        if '.xls' in self.cell_crops_path.lower():
            self.cell_crops_delimiter = ','
            try:
                self.cell_crops_ws = config.get(meta_sec, 'cell_crops_ws')
                if self.cell_crops_ws is None or self.cell_crops_ws == 'None': 
                    logging.error('\nERROR: Worksheet name must be specified for\n' + self.cell_crops_path + ".\n")
                    sys.exit()
            except:
                logging.error('\nERROR: Worksheet name must be specified for\n' + self.cell_crops_path + ".\n")
                sys.exit()
        else:
            try:
                self.cell_crops_delimiter = config.get(meta_sec, 'cell_crops_delimiter')
                if self.cell_crops_delimiter is None or self.cell_crops_delimiter == 'None': 
                    self.cell_crops_delimiter = ','
                else:
                    if self.cell_crops_delimiter not in [' ', ',', '\\t']: self.cell_crops_delimiter = ','
                    if "\\" in self.cell_crops_delimiter and "t" in self.cell_crops_delimiter:
                        self.cell_crops_delimiter = self.cell_crops_delimiter.replace('\\t', '\t')
            except:
                self.cell_crops_delimiter = ','
        try:
            self.cell_crops_header_lines = config.getint(meta_sec, 'cell_crops_header_lines')
            if self.cell_crops_header_lines is None: self.cell_crops_header_lines = 1
        except:
            self.cell_crops_header_lines = 1
        try:
            self.cell_crops_names_line = config.getint(meta_sec, 'cell_crops_names_line')
            if self.cell_crops_names_line is None: self.cell_crops_names_line = 1
        except:
            self.cell_crops_names_line = 1

        # ET Cells Crop Mix

        try:
            cell_mix_name = config.get(meta_sec, 'cell_mix_name')
            if cell_mix_name is None or cell_mix_name == 'None':
                logging.error('ERROR:  ET Cells crop mixture file must be specified')
                sys.exit()
        except:
            logging.error('ERROR:  ET Cells crop mixture file must be specified')
            sys.exit()
        self.cell_mix_path = os.path.join(self.static_folder, cell_mix_name)
        if not os.path.isfile(self.cell_mix_path):
            self.cell_mix_path = cell_mix_name
            if not os.path.isfile(self.cell_mix_path):
                logging.error('ERROR:  ET Cells crop mixture file {} does not exist'.format(self.cell_mix_path))
                sys.exit()
        logging.info('  ET Cell crop mixture file: {}'.format(self.cell_mix_path))
        if '.xls' in self.cell_mix_path.lower():
            self.ccm_delimiter = ','
            try:
                self.cell_mix_ws = config.get(meta_sec, 'cell_mix_ws')
                if self.cell_mix_ws is None or self.cell_mix_ws == 'None': 
                    logging.error('\nERROR: Worksheet name must be specified for\n' + self.cell_mix_path + ".\n")
                    sys.exit()
            except:
                logging.error('\nERROR: Worksheet name must be specified for\n' + self.cell_mix_path + ".\n")
                sys.exit()
        else:
            try:
                self.ccm_delimiter = config.get(meta_sec, 'ccm_delimiter')
                if self.ccm_delimiter is None or self.ccm_delimiter == 'None': 
                    self.ccm_delimiter = ','
                else:
                    if self.ccm_delimiter not in [' ', ',', '\\t']: self.ccm_delimiter = ','
                    if "\\" in self.ccm_delimiter and "t" in self.ccm_delimiter:
                        self.ccm_delimiter = self.ccm_delimiter.replace('\\t', '\t')
            except:
                self.ccm_delimiter = ','
        try:
            self.ccm_header_lines = config.getint(meta_sec, 'ccm_header_lines')
            if self.ccm_header_lines is None: self.ccm_header_lines = 1
        except:
            self.ccm_header_lines = 1
        try:
            self.ccm_names_line = config.getint(meta_sec, 'ccm_names_line')
            if self.ccm_names_line is None: self.ccm_names_line = 1
        except:
            self.ccm_names_line = 1

        """
        Crop mixture time series options are:
        dafault - constant
        0 - variable (time series)
        1 - constant
        """
        try:
            self.ccm_ts_type = config.getint(meta_sec, 'ccm_ts_type')
            if self.ccm_ts_type is None or self.ccm_ts_type == 'None': self.ccm_ts_type = 1
        except:
            self.ccm_ts_type = 1

        """
        Crop mixture type options are:
        dafault - area
        0 - percentages
        1 - area
        """
        try:
            self.ccm_mix_type = config.getint(meta_sec, 'ccm_mix_type')
            if self.ccm_mix_type is None or self.ccm_mix_type == 'None': self.ccm_mix_type = 1
        except:
            self.ccm_mix_type = 1

        """
        Crop mixture area options are:
        default - hectare
        0 - hectare
        1 - acre
        """
        try:
            self.area_units_type = config.getint(meta_sec, 'area_units_type')
            if self.area_units_type is None or self.area_units_type == 'None': self.area_units_type = 1
        except:
            self.area_units_type = 0

        # set crop parameter specs
        
        self.crop_params_path = os.path.join(self.static_folder, config.get(meta_sec, 'crop_params_name'))
        if not os.path.isfile(self.crop_params_path):
            logging.error('ERROR:  ET Cells cuttings file {} does not exist'.format(self.self.crop_params_path))
            sys.exit()
        if '.xls' in self.crop_params_path.lower():
            self.crop_params_delimiter = ','
            try:
                self.crop_params_ws = config.get(meta_sec, 'crop_params_ws')
                if self.crop_params_ws is None or self.crop_params_ws == 'None': 
                    logging.error('\nERROR: Worksheet name must be specified for\n' + self.crop_params_path + ".\n")
                    sys.exit()
            except:
                logging.error('\nERROR: Worksheet name must be specified for\n' + self.crop_params_path + ".\n")
                sys.exit()
        else:
            try:
                self.crop_params_delimiter = config.get(meta_sec, 'crop_params_delimiter')
                if self.crop_params_delimiter is None or self.crop_params_delimiter == 'None': 
                    self.crop_params_delimiter = ','
                else:
                    if self.crop_params_delimiter not in [' ', ',', '\\t']: self.crop_params_delimiter = ','
                    if "\\" in self.crop_params_delimiter and "t" in self.crop_params_delimiter:
                        self.crop_params_delimiter = self.crop_params_delimiter.replace('\\t', '\t')
            except:
                self.crop_params_delimiter = ','
        try:
            self.crop_params_header_lines = config.getint(meta_sec, 'crop_params_header_lines')
            if self.crop_params_header_lines is None: self.crop_params_header_lines = 1
        except:
            self.crop_params_header_lines = 4
        try:
            self.crop_params_names_line = config.getint(meta_sec, 'crop_params_names_line')
            if self.crop_params_names_line is None: self.crop_params_names_line = 1
        except:
            self.crop_params_names_line = 3

        """
        NSG distribution options are:
        default - none
        0 - none
        1 - Distributed to growing season
        2 - Only use crop growing season
        """
        try:
            self.ngs_toggle = config.getint(meta_sec, 'ngs_toggle')
            if self.ngs_toggle is None or self.ngs_toggle == 'None': self.ngs_toggle = 0
        except:
            self.ngs_toggle = 0

        """
        Allow negative NIR's options are:
        default - yes
        0 - yes
        1 - no for NIR's, 
        2 - no for CIR's, 
        3 - no for both
        """
        try:
            self.neg_nirs_toggle = config.getint(meta_sec, 'neg_nirs_toggle')
            if self.neg_nirs_toggle is None or self.neg_nirs_toggle == 'None': self.neg_nirs_toggle = 0
        except:
            self.neg_nirs_toggle = 0

        try:
            self.et_smoothing_days = config.getint(meta_sec, 'et_smoothing_days')
            if self.et_smoothing_days is None or self.et_smoothing_days == 'None': self.et_smoothing_days = 1
        except:
            self.et_smoothing_days = 1
        try:
            self.nir_smoothing_days = config.gnirint(meta_sec, 'nir_smoothing_days')
            if self.nir_smoothing_days is None or self.nir_smoothing_days == 'None': self.nir_smoothing_days = 0
        except:
            self.nir_smoothing_days = 1

        # input cet data parameters
        
        self.input_cet = {}
        self.input_cet['fields'] = {}
        self.input_cet['units'] = {}
        
        # fnspec - parameter extension to file name specification
        
        self.input_cet['fnspec'] = {}
        self.input_cet['wsspec'] = {}
        self.input_cet['ws'] = config.get(input_cet_sec, 'daily_input_cet_folder')
        
        # input input cet folder could be  full or relative path
        # Assume relative paths or from  project folder
        
        if os.path.isdir(self.input_cet['ws']):
            pass
        elif (not os.path.isdir(self.input_cet['ws']) and
              os.path.isdir(os.path.join(self.project_ws, self.input_cet['ws']))):
            self.input_cet['ws'] = os.path.join(self.project_ws, self.input_cet['ws'])
        else:
            logging.error('ERROR:  crop et folder {} does not exist'.format(self.input_cet['ws']))
            sys.exit()
        if not os.path.isdir(self.input_cet['ws']):
            logging.error(('  ERROR:  input_cet dat folder does not ' +
                 'exist\n  %s') % self.input_cet['ws'])
            sys.exit()
            
        # cet file type specifications
        
        try:
            self.input_cet['file_type'] = config.get(input_cet_sec, 'file_type').upper()
            if self.input_cet['file_type'] is None or self.input_cet['file_type'] == 'None':
                self.input_cet['file_type'] = "csv"
        except:
            self.input_cet['file_type'] = "csv"
        try:
            self.input_cet['data_structure_type'] = config.get(input_cet_sec, 'data_structure_type').upper()
            if self.input_cet['data_structure_type'] is None or self.input_cet['data_structure_type'] == 'None':
                self.input_cet['data_structure_type'] = "DRI"
        except:
            self.input_cet['data_structure_type'] = "DRI"
        try:
            self.input_cet['name_format'] = config.get(input_cet_sec, 'name_format')
            if self.input_cet['name_format'] is None or self.input_cet['name_format'] == 'None':
                if self.input_cet['data_structure_type'] == "DRI":
                    self.input_cet['name_format'] = '%s_crop_%c.csv'
                else:    # RDB format
                    self.input_cet['name_format'] = '%s_crop.csv'
        except:
            if self.input_cet['data_structure_type'] == "DRI":
                self.input_cet['name_format'] = '%s_crop_%c.csv'
            else:    # RDB format
                self.input_cet['name_format'] = '%s_crop.csv'
        try:
            self.input_cet['header_lines'] = config.getint(input_cet_sec, 'header_lines')
            if self.input_cet['header_lines'] is None or self.input_cet['header_lines'] == 'None': self.input_cet['header_lines'] = 1
        except:
            self.input_cet['header_lines'] = 1
        try:
            self.input_cet['names_line'] = config.getint(input_cet_sec, 'names_line')
            if self.input_cet['names_line'] is None or self.input_cet['names_line'] == 'None': self.input_cet['names_line'] = 1
        except:
            self.input_cet['names_line'] = 1
        try:
            self.input_cet['delimiter'] = config.get(input_cet_sec, 'delimiter')
            if self.input_cet['delimiter'] is None or self.input_cet['delimiter'] == 'None':
                self.input_cet['delimiter'] = '.'
            else:
                if self.input_cet['delimiter'] not in [' ', ',', '\\t']: self.input_cet['delimiter'] = ','
                if "\\" in self.input_cet['delimiter'] and "t" in self.input_cet['delimiter']:
                    self.input_cet['delimiter'] = self.input_cet['delimiter'].replace('\\t', '\t')
        except:
            self.input_cet['delimiter'] = '.'

        # Date can be read directly or computed from year, month, and day
        
        try: self.input_cet['fields']['date'] = config.get(input_cet_sec, 'date_field')
        except: self.input_cet['fields']['date'] = None
        try: self.input_cet['fields']['year'] = config.get(input_cet_sec, 'year_field')
        except: self.input_cet['fields']['year'] = None
        try: self.input_cet['fields']['month'] = config.get(input_cet_sec, 'month_field')
        except: self.input_cet['fields']['month'] = None
        try: self.input_cet['fields']['day'] = config.get(input_cet_sec, 'day_field')
        except: self.input_cet['fields']['day'] = None
        try: self.input_cet['fields']['doy'] = config.get(input_cet_sec, 'doy_field')
        except: self.input_cet['fields']['doy'] = None
        if self.input_cet['fields']['date'] is not None:
            logging.info('  INCET: Reading date from date column')
        elif (self.input_cet['fields']['year'] is not None and
              self.input_cet['fields']['month'] is not None and
              self.input_cet['fields']['day'] is not None):
            logging.info('  INCET: Reading date from year, month, and day columns')
        else:
            logging.error('  ERROR: INCET date_field (or year, month, and '+
                          'day fields) must be set in  INI')
            sys.exit()                  
        
        # input cet data file name specifications, field names, and units
        
        # Required input cet fields for computing cell output data

        try:
            self.input_cet['fields']['refet'] = config.get(input_cet_sec, 'ret_field')
            if self.input_cet['fields']['refet'] is None or self.input_cet['fields']['refet'] == 'None':
                logging.error('\nERROR: refet field name is required\n')
                sys.exit()
            else:
                try: self.input_cet['units']['refet'] = config.get(input_cet_sec, 'ret_units')
                except: self.input_cet['units']['refet'] = 'mm/day'
                try: self.input_cet['fnspec']['refet'] = config.get(input_cet_sec, 'ret_name')
                except: self.input_cet['fnspec']['refet'] = 'Used'
                if self.input_cet['file_type'].lower() == 'xls' or self.input_cet['file_type'].lower() == 'wb':
                    try: 
                        self.input_cet['wsspec']['refet'] = config.get(input_cet_sec, 'ret_ws')
                        if self.input_cet['wsspec']['refet'] is None or self.input_cet['wsspec']['refet'] == 'None':
                            logging.info('  INFO:  INCET: reference et worksheet name set to RET')
                            self.input_cet['wsspec']['refet'] = 'RET'
                    except:
                        logging.info('  INFO:  INCET: reference et worksheet name set to RET')
                        self.input_cet['wsspec']['refet'] = 'RET'
        except:
            logging.error('\nERROR: refet field name is required\n')
            sys.exit()

        try:
            self.input_cet['fields']['ppt'] = config.get(input_cet_sec, 'ppt_field')
            if self.input_cet['fields']['ppt'] is None or self.input_cet['fields']['ppt'] == 'None':
                logging.error('\nERROR: ppt field name is required\n')
                sys.exit()
            else:
                try: self.input_cet['units']['ppt'] = config.get(input_cet_sec, 'ppt_units')
                except: self.input_cet['units']['ppt'] = 'mm/day'
                try: self.input_cet['fnspec']['ppt'] = config.get(input_cet_sec, 'ppt_name')
                except: self.input_cet['fnspec']['ppt'] = 'Used'
                if self.input_cet['file_type'].lower() == 'xls' or self.input_cet['file_type'].lower() == 'wb':
                    try: 
                        self.input_cet['wsspec']['ppt'] = config.get(input_cet_sec, 'ppt_ws')
                        if self.input_cet['wsspec']['ppt'] is None or self.input_cet['wsspec']['ppt'] == 'None':
                            logging.info('  INFO:  INCET: precip worksheet name set to Prcp')
                            self.input_cet['wsspec']['ppt'] = 'Prcp'
                    except:
                        logging.info('  INFO:  INCET: precip worksheet name set to Prcp')
                        self.input_cet['wsspec']['ppt'] = 'Prcp'
        except:
            logging.error('\nERROR: ppt field name is required\n')
            sys.exit()

        try:
            self.input_cet['fields']['etact'] = config.get(input_cet_sec, 'etact_field')
            if self.input_cet['fields']['etact'] is None or self.input_cet['fields']['etact'] == 'None':
                logging.error('\nERROR: etact field name is required\n')
                sys.exit()
            else:
                try: self.input_cet['units']['etact'] = config.get(input_cet_sec, 'etact_units')
                except: self.input_cet['units']['etact'] = 'mm/day'
                try: self.input_cet['fnspec']['etact'] = config.get(input_cet_sec, 'etact_name')
                except: self.input_cet['fnspec']['etact'] = 'Used'
                if self.input_cet['file_type'].lower() == 'xls' or self.input_cet['file_type'].lower() == 'wb':
                    try: 
                        self.input_cet['wsspec']['etact'] = config.get(input_cet_sec, 'etact_ws')
                        if self.input_cet['wsspec']['etact'] is None or self.input_cet['wsspec']['etact'] == 'None':
                            logging.info('  INFO:  INCET: actual ET worksheet name set to ETAct')
                            self.input_cet['wsspec']['etact'] = 'ETAct'
                    except:
                        logging.info('  INFO:  INCET: actual ET worksheet name set to ETAct')
                        self.input_cet['wsspec']['etact'] = 'ETAct'
        except:
            logging.error('\nERROR: etact field name is required\n')
            sys.exit()

        try:
            self.input_cet['fields']['etpot'] = config.get(input_cet_sec, 'etpot_field')
            if self.input_cet['fields']['etpot'] is None or self.input_cet['fields']['etpot'] == 'None':
                logging.error('\nERROR: etpot field name is required\n')
                sys.exit()
            else:
                try: self.input_cet['units']['etpot'] = config.get(input_cet_sec, 'etpot_units')
                except: self.input_cet['units']['etpot'] = 'mm/day'
                try: self.input_cet['fnspec']['etpot'] = config.get(input_cet_sec, 'etpot_name')
                except: self.input_cet['fnspec']['etpot'] = 'Used'
                if self.input_cet['file_type'].lower() == 'xls' or self.input_cet['file_type'].lower() == 'wb':
                    try: 
                        self.input_cet['wsspec']['etpot'] = config.get(input_cet_sec, 'etpot_ws')
                        if self.input_cet['wsspec']['etpot'] is None or self.input_cet['wsspec']['etpot'] == 'None':
                            logging.info('  INFO:  INCET: potential ET worksheet name set to ETPot')
                            self.input_cet['wsspec']['etpot'] = 'ETPot'
                    except:
                        logging.info('  INFO:  INCET: potential ET worksheet name set to ETPot')
                        self.input_cet['wsspec']['etpot'] = 'ETPot'
        except:
            logging.error('\nERROR: etpot field name is required\n')
            sys.exit()

        try:
            self.input_cet['fields']['sir'] = config.get(input_cet_sec, 'sir_field')
            if self.input_cet['fields']['sir'] is None or self.input_cet['fields']['sir'] == 'None':
                logging.error('\nERROR: sir field name is required\n')
                sys.exit()
            else:
                try: self.input_cet['units']['sir'] = config.get(input_cet_sec, 'sir_units')
                except: self.input_cet['units']['sir'] = 'mm/day'
                try: self.input_cet['fnspec']['sir'] = config.get(input_cet_sec, 'sir_name')
                except: self.input_cet['fnspec']['sir'] = 'Used'
                if self.input_cet['file_type'].lower() == 'xls' or self.input_cet['file_type'].lower() == 'wb':
                    try: 
                        self.input_cet['wsspec']['sir'] = config.get(input_cet_sec, 'sir_ws')
                        if self.input_cet['wsspec']['sir'] is None or self.input_cet['wsspec']['sir'] == 'None':
                            logging.info('  INFO:  INCET: irrigation worksheet name set to Irrigation')
                            self.input_cet['wsspec']['sir'] = 'Irrigation'
                    except:
                        logging.info('  INFO:  INCET: irrigation worksheet name set to Irrigation')
                        self.input_cet['wsspec']['sir'] = 'Irrigation'
        except:
            logging.error('\nERROR: sir field name is required\n')
            sys.exit()

        try:
            self.input_cet['fields']['sro'] = config.get(input_cet_sec, 'sro_field')
            if self.input_cet['fields']['sro'] is None or self.input_cet['fields']['sro'] == 'None':
                logging.error('\nERROR: sro field name is required\n')
                sys.exit()
            else:
                try: self.input_cet['units']['sro'] = config.get(input_cet_sec, 'sro_units')
                except: self.input_cet['units']['sro'] = 'mm/day'
                try: self.input_cet['fnspec']['sro'] = config.get(input_cet_sec, 'sro_name')
                except: self.input_cet['fnspec']['sro'] = 'Used'
                if self.input_cet['file_type'].lower() == 'xls' or self.input_cet['file_type'].lower() == 'wb':
                    try: 
                        self.input_cet['wsspec']['sro'] = config.get(input_cet_sec, 'sro_ws')
                        if self.input_cet['wsspec']['sro'] is None or self.input_cet['wsspec']['sro'] == 'None':
                            logging.info('  INFO:  INCET: runoff worksheet name set to Runoff')
                            self.input_cet['wsspec']['sro'] = 'Runoff'
                    except:
                        logging.info('  INFO:  INCET: runoff worksheet name set to Runoff')
                        self.input_cet['wsspec']['sro'] = 'Runoff'
        except:
            logging.error('\nERROR: sro field name is required\n')
            sys.exit()

        try:
            self.input_cet['fields']['dperc'] = config.get(input_cet_sec, 'dperc_field')
            if self.input_cet['fields']['dperc'] is None or self.input_cet['fields']['dperc'] == 'None':
                logging.error('\nERROR: dperc field name is required\n')
                sys.exit()
            else:
                try: self.input_cet['units']['dperc'] = config.get(input_cet_sec, 'dperc_units')
                except: self.input_cet['units']['dperc'] = 'mm/day'
                try: self.input_cet['fnspec']['dperc'] = config.get(input_cet_sec, 'dperc_name')
                except: self.input_cet['fnspec']['dperc'] = 'Used'
                if self.input_cet['file_type'].lower() == 'xls' or self.input_cet['file_type'].lower() == 'wb':
                    try: 
                        self.input_cet['wsspec']['dperc'] = config.get(input_cet_sec, 'dperc_ws')
                        if self.input_cet['wsspec']['dperc'] is None or self.input_cet['wsspec']['dperc'] == 'None':
                            logging.info('  INFO:  INCET: deep perc worksheet name set to DPerc')
                            self.input_cet['wsspec']['dperc'] = 'DPerc'
                    except:
                        logging.info('  INFO:  INCET: deep perc worksheet name set to DPerc')
                        self.input_cet['wsspec']['dperc'] = 'DPerc'
        except:
            logging.error('\nERROR: dperc field name is required\n')
            sys.exit()

        try:
            self.input_cet['fields']['season'] = config.get(input_cet_sec, 'season_field')
            if self.input_cet['fields']['season'] is None or self.input_cet['fields']['season'] == 'None':
                logging.error('\nERROR: season field name is required\n')
                sys.exit()
            else:
                try: self.input_cet['fnspec']['season'] = config.get(input_cet_sec, 'season_name')
                except: self.input_cet['fnspec']['season'] = 'Used'
                if self.input_cet['file_type'].lower() == 'xls' or self.input_cet['file_type'].lower() == 'wb':
                    try: 
                        self.input_cet['wsspec']['season'] = config.get(input_cet_sec, 'season_ws')
                        if self.input_cet['wsspec']['season'] is None or self.input_cet['wsspec']['season'] == 'None':
                            logging.info('  INFO:  INCET: season worksheet name set to Season')
                            self.input_cet['wsspec']['season'] = 'Season'
                    except:
                        logging.info('  INFO:  INCET: season worksheet name set to Season')
                        self.input_cet['wsspec']['season'] = 'Season'
        except:
            logging.error('\nERROR: season field name is required\n')
            sys.exit()

        # optional input cet fields and units - unprovided fields are estimated if needed for ref et computations
        
        try:
            self.input_cet['fields']['cir'] = config.get(input_cet_sec, 'cir_field')
            if self.input_cet['fields']['cir'] is None or self.input_cet['fields']['cir'] == 'None':
                self.input_cet['fields']['cir'] = 'NIWR'
                self.input_cet['units']['cir'] = 'mm/day'
                self.input_cet['fnspec']['cir'] = 'Unused'
            else:
                try: self.input_cet['units']['cir'] = config.get(input_cet_sec, 'cir_units')
                except: self.input_cet['units']['cir'] = 'mm/day'
                try: self.input_cet['fnspec']['cir'] = config.get(input_cet_sec, 'cir_name')
                except: self.input_cet['fnspec']['cir'] = 'Unused'
                if self.input_cet['file_type'].lower() == 'xls' or self.input_cet['file_type'].lower() == 'wb':
                    try: 
                        self.input_cet['wsspec']['cir'] = config.get(input_cet_sec, 'cir_sheet')
                        if self.input_cet['wsspec']['cir'] is None or self.input_cet['wsspec']['cir'] == 'None':
                            logging.info('  INFO:  INCET: niwr worksheet name set to NIWR')
                            self.input_cet['wsspec']['cir'] = 'NIWR'
                    except:
                        logging.info('  INFO:  INCET: niwr worksheet name set to NIWR')
                        self.input_cet['wsspec']['cir'] = 'NIWR'
        except:
            self.input_cet['fields']['cir'] = 'NIWR'
            self.input_cet['units']['cir'] = 'mm/day'
            self.input_cet['fnspec']['cir'] = 'Unused'

        # Check units
        
        for k, v in self.input_cet['units'].iteritems():
            if v is not None and v.lower() not in units_list:
                logging.error('  ERROR: {0} units {1} are not currently supported'.format(k,v))
                sys.exit()
        self.output_cet = {}
        self.output_cet['fields'] = {}
        if self.output_cet_flag:

            # area cell crop type et output parameters
        
            # cell crop type et folder could be  full or relative path
            # Assume relative paths or from project folder
        
            # Output cet flags
        
            try:
                self.daily_output_cet_flag = config.getboolean(output_cet_sec, 'daily_output_cet_flag')
            except:
                logging.debug('    daily_output_cet_flag = False')
                self.daily_output_cet_flag = False
            try:
                self.monthly_output_cet_flag = config.getboolean(output_cet_sec, 'monthly_output_cet_flag')
            except:
                logging.debug('    monthly_output_cet_flag = False')
                self.monthly_output_cet_flag = False
            try:
                self.annual_output_cet_flag = config.getboolean(output_cet_sec, 'annual_output_cet_flag')
            except:
                logging.debug('    annual_output_cet_flag = False')
                self.annual_output_cet_flag = False
            if not self.daily_output_cet_flag and self.monthly_output_cet_flag and self.annual_output_cet_flag:
                self.output_cet_flag = False;
            
            # crop by crop output cet specs
        
            if self.daily_output_cet_flag:
                try:
                    self.daily_output_cet_ws = os.path.join(
                        self.project_ws, config.get(output_cet_sec, 'daily_output_cet_folder'))
                    if not os.path.isdir(self.daily_output_cet_ws):
                       os.makedirs(self.daily_output_cet_ws)
                except:
                    logging.debug('    daily_output_cet_folder = daily_cet')
                    self.daily_output_cet_ws = 'daily_cet'
            if self.monthly_output_cet_flag:
                try:
                    self.monthly_output_cet_ws = os.path.join(
                        self.project_ws, config.get(output_cet_sec, 'monthly_output_cet_folder'))
                    if not os.path.isdir(self.monthly_output_cet_ws):
                       os.makedirs(self.monthly_output_cet_ws)
                except:
                    logging.debug('    monthly_output_cet_folder = monthly_cet')
                    self.monthly_output_cet_ws = 'monthly_cet'             
            if self.annual_output_cet_flag:
                try:
                    self.annual_output_cet_ws = os.path.join(
                        self.project_ws, config.get(output_cet_sec, 'annual_output_cet_folder'))
                    if not os.path.isdir(self.annual_output_cet_ws):
                       os.makedirs(self.annual_output_cet_ws)
                except:
                    logging.debug('    annual_output_cet_folder = annual_cet')
                    self.annual_output_cet_ws = 'annual_cet'
            self.output_cet['file_type'] = config.get(output_cet_sec, 'file_type')
            self.output_cet['data_structure_type'] = config.get(output_cet_sec, 'data_structure_type').upper()
            self.output_cet['name_format'] = config.get(output_cet_sec, 'name_format')
            self.output_cet['header_lines'] = config.getint(output_cet_sec, 'header_lines')
            if self.output_cet['header_lines'] > 2:
                logging.warning('\nReferemce ET ouput can have maximum of two header lines.')
                self.output_cet['header_lines'] = 2
            self.output_cet['names_line'] = config.getint(output_cet_sec, 'names_line')
            try:
                self.output_cet['delimiter'] = config.get(output_cet_sec, 'delimiter')
                if self.output_cet['delimiter'] is None or self.output_cet['delimiter'] == 'None': 
                    self.output_cet['delimiter'] = ','
                else:
                    if self.output_cet['delimiter'] not in [' ', ',', '\\t']: self.output_cet['delimiter'] = ','
                    if "\\" in self.output_cet['delimiter'] and "t" in self.output_cet['delimiter']:
                        self.output_cet['delimiter'] = self.output_cet['delimiter'].replace('\\t', '\t')
            except:
                    self.output_cet['delimiter'] = ','
            self.output_cet_sheet = None

            # date and values formats, etc

            try:
                self.output_cet['daily_date_format'] = config.get(output_cet_sec, 'daily_date_format')
                if self.output_cet['daily_date_format'] is None or self.output_cet['daily_date_format'] == 'None':
                    if self.output_cet['file_type'] == 'xls':
                        self.output_cet['daily_date_format'] = 'm/d/yyyy'
                    else:
                        self.output_cet['daily_date_format'] = '%Y-%m-%d'
            except:
                if self.output_cet['file_type'] == 'xls':
                    self.output_cet['daily_date_format'] = 'm/d/yyyy'
                else:
                    self.output_cet['daily_date_format'] = '%Y-%m-%d'
            try:
                offset = config.getint(output_cet_sec, 'daily_hour_offset')
                if offset is None or offset == 'None':
                    self.output_cet['daily_hour_offset'] = int(0)
                else:
                    self.output_cet['daily_hour_offset'] = int(offset)
            except: self.output_cet['daily_hour_offset'] = int(0)
            try:
                offset = config.getint(output_cet_sec, 'daily_minute_offset')
                if offset is None or offset == 'None':
                    self.output_cet['daily_minute_offset'] = int(0)
                else:
                    self.output_cet['daily_minute_offset'] = int(offset)
            except: self.output_cet['daily_minute_offset'] = int(0)
            try: 
                self.output_cet['daily_float_format'] = config.get(output_cet_sec, 'daily_float_format')
                if self.output_cet['daily_float_format'] == 'None': self.output_cet['daily_float_format'] = None
            except: self.output_cet['daily_float_format'] = None
            try:
                self.output_cet['monthly_date_format'] = config.get(output_cet_sec, 'monthly_date_format')
                if self.output_cet['monthly_date_format'] is None or self.output_cet['monthly_date_format'] == 'None':
                    if self.output_cet['file_type'] == 'xls':
                        self.output_cet['monthly_date_format'] = 'm/yyyy'
                    else:
                        self.output_cet['monthly_date_format'] = '%Y-%m'
            except:
                if self.output_cet['file_type'] == 'xls':
                    self.output_cet['monthly_date_format'] = 'm/yyyy'
                else:
                    self.output_cet['monthly_date_format'] = '%Y-%m'
            try:
                offset = config.getint(output_cet_sec, 'monthly_hour_offset')
                if offset is None or offset == 'None':
                    self.output_cet['monthly_hour_offset'] = int(0)
                else:
                    self.output_cet['monthly_hour_offset'] = int(offset)
            except: self.output_cet['monthly_hour_offset'] = int(0)
            try:
                offset = config.getint(output_cet_sec, 'monthly_minute_offset')
                if offset is None or offset == 'None':
                    self.output_cet['monthly_minute_offset'] = int(0)
                else:
                    self.output_cet['monthly_minute_offset'] = int(offset)
            except: self.output_cet['monthly_minute_offset'] = int(0)
            try: 
                self.output_cet['monthly_float_format'] = config.get(output_cet_sec, 'monthly_float_format')
                if self.output_cet['monthly_float_format'] == 'None': self.output_cet['monthly_float_format'] = None
            except: self.output_cet['monthly_float_format'] = None
            try:
                self.output_cet['annual_date_format'] = config.get(output_cet_sec, 'annual_date_format')
                if self.output_cet['annual_date_format'] is None or self.output_cet['annual_date_format'] == 'None':
                    if self.output_cet['file_type'] == 'xls':
                        self.output_cet['annual_date_format'] = 'm/yyyy'
                    else:
                        self.output_cet['annual_date_format'] = '%Y-%m'
            except:
                if self.output_cet['file_type'] == 'xls':
                    self.output_cet['annual_date_format'] = 'm/yyyy'
                else:
                    self.output_cet['annual_date_format'] = '%Y-%m'
            try:
                offset = config.getint(output_cet_sec, 'annual_hour_offset')
                if offset is None or offset == 'None':
                    self.output_cet['annual_hour_offset'] = int(0)
                else:
                    self.output_cet['annual_hour_offset'] = int(offset)
            except: self.output_cet['annual_hour_offset'] = int(0)
            try:
                offset = config.getint(output_cet_sec, 'annual_minute_offset')
                if offset is None or offset == 'None':
                    self.output_cet['annual_minute_offset'] = int(0)
                else:
                    self.output_cet['annual_minute_offset'] = int(offset)
            except: self.output_cet['annual_minute_offset'] = int(0)
            try: 
                self.output_cet['annual_float_format'] = config.get(output_cet_sec, 'annual_float_format')
                if self.output_cet['annual_float_format'] == 'None': self.output_cet['annual_float_format'] = None
            except: self.output_cet['annual_float_format'] = None

            # Date or Year, Month, Day or both and/or DOY can be posted

            try: self.output_cet['fields']['date'] = config.get(output_cet_sec, 'date_field')
            except: self.output_cet['fields']['date'] = None
            try: self.output_cet['fields']['year'] = config.get(output_cet_sec, 'year_field')
            except: self.output_cet['fields']['year'] = None
            try: self.output_cet['fields']['month'] = config.get(output_cet_sec, 'month_field')
            except: self.output_cet['fields']['month'] = None
            try: self.output_cet['fields']['day'] = config.get(output_cet_sec, 'day_field')
            except: self.output_cet['fields']['day'] = None
            if self.output_cet['fields']['date'] is not None:
                logging.info('  OUTCET: Posting date to date column')
            elif (self.output_cet['fields']['year'] is not None and
                  self.output_cet['fields']['month'] is not None and
                  self.output_cet['fields']['day'] is not None):
                logging.info('  OUTCET: Posting date to year, month, and day columns')
            else:
                logging.error('  ERROR: refet date_field (or year, month, and ' +
                              'day fields) must be set in  INI')
                sys.exit()                  

            # output cet data file name specifications, field names, and units - all optional but should have at least one

            try:
                self.output_cet['fields']['cet'] = config.get(output_cet_sec, 'cet_field')
                if self.output_cet['fields']['cet'] is None or self.output_cet['fields']['cet'] == 'None':
                    self.output_cet['fields']['cet'] = 'CET'
                    self.output_cet['cet_units'] = 'mm/day'
                    self.output_cet['cet_name'] = 'Unused'
                else:
                    try: self.output_cet['cet_units'] = config.get(output_cet_sec, 'cet_units')
                    except: self.output_cet['cet_units'] = 'mm/day'
                    try: self.output_cet['cet_name'] = config.get(output_cet_sec, 'cet_name')
                    except: self.output_cet['cet_name'] = 'Unused'
                    if self.output_cet['file_type'].lower() == 'xls' or self.output_cet['file_type'].lower() == 'wb':
                        try: 
                            self.output_cet_sheet = config.get(output_cet_sec, 'cet_sheet')
                            if self.output_cet_sheet is None or self.output_cet_sheet == 'None':
                                logging.info('  INFO:  OUTCET: cet worksheet name set to CET')
                                self.output_cet_sheet = 'CET'
                        except:
                            logging.info('  INFO:  OUTCET: cet worksheet name set to CET')
                            self.output_cet_sheet = 'CET'
            except:
                self.output_cet['fields']['cet'] = 'CET'
                self.output_cet['cet_units'] = 'mm/day'
                self.output_cet['cet_name'] = 'Unused'

            # Check units

            if self.output_cet['cet_units'] is not None and self.output_cet['cet_units'].lower() not in units_list:
                logging.error('  ERROR: units {0} are not currently supported'.format(self.output_cet['cet_units']))
                sys.exit()
        else:
            self.output_cet['fields']['cet'] = 'CET'
            self.output_cet['cet_units'] = 'mm/day'
            self.output_cet['cet_name'] = 'Unused'
         
        self.output_cir = {}
        self.output_cir['fields'] = {}
        if self.output_cir_flag:

            # area cell crop type cir output parameters
        
            # cell crop type et folder could be  full or relative path
            # Assume relative paths or from project folder
        
            # Output cir flags
        
            try:
                self.daily_output_cir_flag = config.getboolean(output_cir_sec, 'daily_output_cir_flag')
            except:
                logging.debug('    daily_output_cir_flag = False')
                self.daily_output_cir_flag = False
            try:
                self.monthly_output_cir_flag = config.getboolean(output_cir_sec, 'monthly_output_cir_flag')
            except:
                logging.debug('    monthly_output_cir_flag = False')
                self.monthly_output_cir_flag = False
            try:
                self.annual_output_cir_flag = config.getboolean(output_cir_sec, 'annual_output_cir_flag')
            except:
                logging.debug('    annual_output_cir_flag = False')
                self.annual_output_cir_flag = False
            if not self.daily_output_cir_flag and self.monthly_output_cir_flag and self.annual_output_cir_flag:
                self.output_cir_flag = False;
            
            # crop by crop output cir specs
        
            if self.daily_output_cir_flag:
                try:
                    self.daily_output_cir_ws = os.path.join(
                        self.project_ws, config.get(output_cir_sec, 'daily_output_cir_folder'))
                    if not os.path.isdir(self.daily_output_cir_ws):
                       os.makedirs(self.daily_output_cir_ws)
                except:
                    logging.debug('    daily_output_cir_folder = daily_cir')
                    self.daily_output_cir_ws = 'daily_cir'
            if self.monthly_output_cir_flag:
                try:
                    self.monthly_output_cir_ws = os.path.join(
                        self.project_ws, config.get(output_cir_sec, 'monthly_output_cir_folder'))
                    if not os.path.isdir(self.monthly_output_cir_ws):
                       os.makedirs(self.monthly_output_cir_ws)
                except:
                    logging.debug('    monthly_output_cir_folder = monthly_cir')
                    self.monthly_output_cir_ws = 'monthly_cir'             
            if self.annual_output_cir_flag:
                try:
                    self.annual_output_cir_ws = os.path.join(
                        self.project_ws, config.get(output_cir_sec, 'annual_output_cir_folder'))
                    if not os.path.isdir(self.annual_output_cir_ws):
                       os.makedirs(self.annual_output_cir_ws)
                except:
                    logging.debug('    annual_output_cir_folder = annual_cir')
                    self.annual_output_cir_ws = 'annual_cir'
            self.output_cir['file_type'] = config.get(output_cir_sec, 'file_type')
            self.output_cir['data_structure_type'] = config.get(output_cir_sec, 'data_structure_type').upper()
            self.output_cir['name_format'] = config.get(output_cir_sec, 'name_format')
            self.output_cir['header_lines'] = config.getint(output_cir_sec, 'header_lines')
            if self.output_cir['header_lines'] > 2:
                logging.warning('\nReferemce ET ouput can have maximum of two header lines.')
                self.output_cir['header_lines'] = 2
            self.output_cir['names_line'] = config.getint(output_cir_sec, 'names_line')
            try:
                self.output_cir['delimiter'] = config.get(output_cir_sec, 'delimiter')
                if self.output_cir['delimiter'] is None or self.output_cir['delimiter'] == 'None': 
                    self.output_cir['delimiter'] = ','
                else:
                    if self.output_cir['delimiter'] not in [' ', ',', '\\t']: self.output_cir['delimiter'] = ','
                    if "\\" in self.output_cir['delimiter'] and "t" in self.output_cir['delimiter']:
                        self.output_cir['delimiter'] = self.output_cir['delimiter'].replace('\\t', '\t')
            except:
                    self.output_cir['delimiter'] = ','
            self.output_cir_sheet = None

            # date and values formats, etc

            try:
                self.output_cir['daily_date_format'] = config.get(output_cir_sec, 'daily_date_format')
                if self.output_cir['daily_date_format'] is None or self.output_cir['daily_date_format'] == 'None':
                    if self.output_cir['file_type'] == 'xls':
                        self.output_cir['daily_date_format'] = 'm/d/yyyy'
                    else:
                        self.output_cir['daily_date_format'] = '%Y-%m-%d'
            except:
                if self.output_cir['file_type'] == 'xls':
                    self.output_cir['daily_date_format'] = 'm/d/yyyy'
                else:
                    self.output_cir['daily_date_format'] = '%Y-%m-%d'
            try:
                offset = config.getint(output_cir_sec, 'daily_hour_offset')
                if offset is None or offset == 'None':
                    self.output_cir['daily_hour_offset'] = int(0)
                else:
                    self.output_cir['daily_hour_offset'] = int(offset)
            except: self.output_cir['daily_hour_offset'] = int(0)
            try:
                offset = config.getint(output_cir_sec, 'daily_minute_offset')
                if offset is None or offset == 'None':
                    self.output_cir['daily_minute_offset'] = int(0)
                else:
                    self.output_cir['daily_minute_offset'] = int(offset)
            except: self.output_cir['daily_minute_offset'] = int(0)
            try: 
                self.output_cir['daily_float_format'] = config.get(output_cir_sec, 'daily_float_format')
                if self.output_cir['daily_float_format'] == 'None': self.output_cir['daily_float_format'] = None
            except: self.output_cir['daily_float_format'] = None
            try:
                self.output_cir['monthly_date_format'] = config.get(output_cir_sec, 'monthly_date_format')
                if self.output_cir['monthly_date_format'] is None or self.output_cir['monthly_date_format'] == 'None':
                    if self.output_cir['file_type'] == 'xls':
                        self.output_cir['monthly_date_format'] = 'm/yyyy'
                    else:
                        self.output_cir['monthly_date_format'] = '%Y-%m'
            except:
                if self.output_cir['file_type'] == 'xls':
                    self.output_cir['monthly_date_format'] = 'm/yyyy'
                else:
                    self.output_cir['monthly_date_format'] = '%Y-%m'
            try:
                offset = config.getint(output_cir_sec, 'monthly_hour_offset')
                if offset is None or offset == 'None':
                    self.output_cir['monthly_hour_offset'] = int(0)
                else:
                    self.output_cir['monthly_hour_offset'] = int(offset)
            except: self.output_cir['monthly_hour_offset'] = int(0)
            try:
                offset = config.getint(output_cir_sec, 'monthly_minute_offset')
                if offset is None or offset == 'None':
                    self.output_cir['monthly_minute_offset'] = int(0)
                else:
                    self.output_cir['monthly_minute_offset'] = int(offset)
            except: self.output_cir['monthly_minute_offset'] = int(0)
            try: 
                self.output_cir['monthly_float_format'] = config.get(output_cir_sec, 'monthly_float_format')
                if self.output_cir['monthly_float_format'] == 'None': self.output_cir['monthly_float_format'] = None
            except: self.output_cir['monthly_float_format'] = None
            try:
                self.output_cir['annual_date_format'] = config.get(output_cir_sec, 'annual_date_format')
                if self.output_cir['annual_date_format'] is None or self.output_cir['annual_date_format'] == 'None':
                    if self.output_cir['file_type'] == 'xls':
                        self.output_cir['annual_date_format'] = 'm/yyyy'
                    else:
                        self.output_cir['annual_date_format'] = '%Y-%m'
            except:
                if self.output_cir['file_type'] == 'xls':
                    self.output_cir['annual_date_format'] = 'm/yyyy'
                else:
                    self.output_cir['annual_date_format'] = '%Y-%m'
            try:
                offset = config.getint(output_cir_sec, 'annual_hour_offset')
                if offset is None or offset == 'None':
                    self.output_cir['annual_hour_offset'] = int(0)
                else:
                    self.output_cir['annual_hour_offset'] = int(offset)
            except: self.output_cir['annual_hour_offset'] = int(0)
            try:
                offset = config.getint(output_cir_sec, 'annual_minute_offset')
                if offset is None or offset == 'None':
                    self.output_cir['annual_minute_offset'] = int(0)
                else:
                    self.output_cir['annual_minute_offset'] = int(offset)
            except: self.output_cir['annual_minute_offset'] = int(0)
            try: 
                self.output_cir['annual_float_format'] = config.get(output_cir_sec, 'annual_float_format')
                if self.output_cir['annual_float_format'] == 'None': self.output_cir['annual_float_format'] = None
            except: self.output_cir['annual_float_format'] = None

            # Date or Year, Month, Day or both and/or DOY can be posted

            try: self.output_cir['fields']['date'] = config.get(output_cir_sec, 'date_field')
            except: self.output_cir['fields']['date'] = None
            try: self.output_cir['fields']['year'] = config.get(output_cir_sec, 'year_field')
            except: self.output_cir['fields']['year'] = None
            try: self.output_cir['fields']['month'] = config.get(output_cir_sec, 'month_field')
            except: self.output_cir['fields']['month'] = None
            try: self.output_cir['fields']['day'] = config.get(output_cir_sec, 'day_field')
            except: self.output_cir['fields']['day'] = None
            if self.output_cir['fields']['date'] is not None:
                logging.info('  OUTCET: Posting date to date column')
            elif (self.output_cir['fields']['year'] is not None and
                  self.output_cir['fields']['month'] is not None and
                  self.output_cir['fields']['day'] is not None):
                logging.info('  OUTCET: Posting date to year, month, and day columns')
            else:
                logging.error('  ERROR: refet date_field (or year, month, and ' +
                              'day fields) must be set in  INI')
                sys.exit()                  

            # output cir data file name specifications, field names, and units - all optional but should have at least one

            try:
                self.output_cir['fields']['cir'] = config.get(output_cir_sec, 'cir_field')
                if self.output_cir['fields']['cir'] is None or self.output_cir['fields']['cir'] == 'None':
                    self.output_cir['fields']['cir'] = 'CET'
                    self.output_cir['cir_units'] = 'mm/day'
                    self.output_cir['cir_name'] = 'Unused'
                else:
                    try: self.output_cir['cir_units'] = config.get(output_cir_sec, 'cir_units')
                    except: self.output_cir['cir_units'] = 'mm/day'
                    try: self.output_cir['cir_name'] = config.get(output_cir_sec, 'cir_name')
                    except: self.output_cir['cir_name'] = 'Unused'
                    if self.output_cir['file_type'].lower() == 'xls' or self.output_cir['file_type'].lower() == 'wb':
                        try: 
                            self.output_cir_sheet = config.get(output_cir_sec, 'cir_sheet')
                            if self.output_cir_sheet is None or self.output_cir_sheet == 'None':
                                logging.info('  INFO:  OUTCET: cir worksheet name set to CET')
                                self.output_cir_sheet = 'CET'
                        except:
                            logging.info('  INFO:  OUTCET: cir worksheet name set to CET')
                            self.output_cir_sheet = 'CET'
            except:
                self.output_cir['fields']['cir'] = 'CET'
                self.output_cir['cir_units'] = 'mm/day'
                self.output_cir['cir_name'] = 'Unused'

            # Check units

            if self.output_cir['cir_units'] is not None and self.output_cir['cir_units'].lower() not in units_list:
                logging.error('  ERROR: units {0} are not currently supported'.format(self.output_cir['cir_units']))
                sys.exit()
        else:
            self.output_cir['fields']['cir'] = 'CIR'
            self.output_cir['cir_units'] = 'mm/day'
            self.output_cir['cir_name'] = 'Unused'

        # output aet data parameters
    
        self.output_aet = {}
        self.output_aet['fields'] = {}
        self.output_aet['units'] = {}

        # fnspec - parameter extension to file name specification

        self.output_aet['fnspec'] = {}
        self.output_aet['wsspec'] = {}
        
        # Output aet flags
    
        try:
            self.daily_output_aet_flag = config.getboolean(output_aet_sec, 'daily_output_aet_flag')
        except:
            logging.debug('    daily_output_aet_flag = False')
            self.daily_output_aet_flag = False
        try:
            self.monthly_output_aet_flag = config.getboolean(output_aet_sec, 'monthly_output_aet_flag')
        except:
            logging.debug('    monthly_output_aet_flag = False')
            self.monthly_output_aet_flag = False
        try:
            self.annual_output_aet_flag = config.getboolean(output_aet_sec, 'annual_output_aet_flag')
        except:
            logging.debug('    annual_output_aet_flag = False')
            self.annual_output_aet_flag = False
        if not self.daily_output_aet_flag or self.monthly_output_aet_flag or self.annual_output_aet_flag:
            self.output_aet_flag = True;
        else:
            self.output_aet_flag = False;

        # Input/output folders
    
        if self.daily_output_aet_flag:
            try:
                self.daily_output_aet_ws = os.path.join(
                    self.project_ws, config.get(output_aet_sec, 'daily_output_aet_folder'))
                if not os.path.isdir(self.daily_output_aet_ws):
                   os.makedirs(self.daily_output_aet_ws)
            except:
                logging.debug('    daily_output_aet_folder = daily_aet')
                self.daily_output_aet_ws = 'daily_aet'
        if self.monthly_output_aet_flag:
            try:
                self.monthly_output_aet_ws = os.path.join(
                    self.project_ws, config.get(output_aet_sec, 'monthly_output_aet_folder'))
                if not os.path.isdir(self.monthly_output_aet_ws):
                   os.makedirs(self.monthly_output_aet_ws)
            except:
                logging.debug('    monthly_output_aet_folder = monthly_aet')
                self.monthly_output_aet_ws = 'monthly_aet'             
        if self.annual_output_aet_flag:
            try:
                self.annual_output_aet_ws = os.path.join(
                    self.project_ws, config.get(output_aet_sec, 'annual_output_aet_folder'))
                if not os.path.isdir(self.annual_output_aet_ws):
                   os.makedirs(self.annual_output_aet_ws)
            except:
                logging.debug('    annual_output_aet_folder = annual_aet')
                self.annual_output_aet_ws = 'annual_aet'

        self.output_aet['file_type'] = config.get(output_aet_sec, 'file_type')
        self.output_aet['data_structure_type'] = config.get(output_aet_sec, 'data_structure_type').upper()
        self.output_aet['name_format'] = config.get(output_aet_sec, 'name_format')
        self.output_aet['header_lines'] = config.getint(output_aet_sec, 'header_lines')
        self.output_aet['names_line'] = config.getint(output_aet_sec, 'names_line')
        try:
            self.output_aet['delimiter'] = config.get(output_aet_sec, 'delimiter')
            if self.output_aet['delimiter'] is None or self.output_aet['delimiter'] == 'None': 
                self.output_aet['delimiter'] = ','
            else:
                if self.output_aet['delimiter'] not in [' ', ',', '\\t']: self.output_aet['delimiter'] = ','
                if "\\" in self.output_aet['delimiter'] and "t" in self.output_aet['delimiter']:
                    self.output_aet['delimiter'] = self.output_aet['delimiter'].replace('\\t', '\t')
        except:
                self.output_aet['delimiter'] = ','
        if self.output_aet['header_lines'] == 1:
            try:
                self.output_aet['units_in_header'] = config.getboolean(output_aet_sec, 'units_in_header')
            except:
                    self.output_aet['units_in_header'] = False
        else:
            self.output_aet['units_in_header'] = False
        try:
            self.output_aet['et_running_avg_days'] = config.get(output_aet_sec, 'et_running_avg_day')
            if self.output_aet['et_running_avg_days'] == 'None': self.output_aet['et_running_avg_days'] = 1
        except: self.output_aet['et_running_avg_days'] = 1
        try:
            self.output_aet['nir_running_avg_days'] = config.get(output_aet_sec, 'nir_running_avg_day')
            if self.output_aet['nir_running_avg_days'] == 'None': self.output_aet['nir_running_avg_days'] = 1
        except: self.output_aet['nir_running_avg_days'] = 1

        # date and values formats, etc

        try:
            self.output_aet['daily_date_format'] = config.get(output_aet_sec, 'daily_date_format')
            if self.output_aet['daily_date_format'] is None or self.output_aet['daily_date_format'] == 'None':
                if self.output_aet['file_type'] == 'xls':
                    self.output_aet['daily_date_format'] = 'm/d/yyyy'
                else:
                    self.output_aet['daily_date_format'] = '%Y-%m-%d'
        except:
            if self.output_aet['file_type'] == 'xls':
                self.output_aet['daily_date_format'] = 'm/d/yyyy'
            else:
                self.output_aet['daily_date_format'] = '%Y-%m-%d'
        try:
            offset = config.getint(output_aet_sec, 'daily_hour_offset')
            if offset is None or offset == 'None':
                self.output_aet['daily_hour_offset'] = int(0)
            else:
                self.output_aet['daily_hour_offset'] = int(offset)
        except: self.output_aet['daily_hour_offset'] = int(0)
        try:
            offset = config.getint(output_aet_sec, 'daily_minute_offset')
            if offset is None or offset == 'None':
                self.output_aet['daily_minute_offset'] = int(0)
            else:
                self.output_aet['daily_minute_offset'] = int(offset)
        except: self.output_aet['daily_minute_offset'] = int(0)
        try: 
            self.output_aet['daily_float_format'] = config.get(output_aet_sec, 'daily_float_format')
            if self.output_aet['daily_float_format'] == 'None': self.output_aet['daily_float_format'] = None
        except: self.output_aet['daily_float_format'] = None
        try:
            self.output_aet['monthly_date_format'] = config.get(output_aet_sec, 'monthly_date_format')
            if self.output_aet['monthly_date_format'] is None or self.output_aet['monthly_date_format'] == 'None':
                if self.output_aet['file_type'] == 'xls':
                    self.output_aet['monthly_date_format'] = 'm/yyyy'
                else:
                    self.output_aet['monthly_date_format'] = '%Y-%m'
        except:
            if self.output_aet['file_type'] == 'xls':
                self.output_aet['monthly_date_format'] = 'm/yyyy'
            else:
                self.output_aet['monthly_date_format'] = '%Y-%m'
        try:
            offset = config.getint(output_aet_sec, 'monthly_hour_offset')
            if offset is None or offset == 'None':
                self.output_aet['monthly_hour_offset'] = int(0)
            else:
                self.output_aet['monthly_hour_offset'] = int(offset)
        except: self.output_aet['monthly_hour_offset'] = int(0)
        try:
            offset = config.getint(output_aet_sec, 'monthly_minute_offset')
            if offset is None or offset == 'None':
                self.output_aet['monthly_minute_offset'] = int(0)
            else:
                self.output_aet['monthly_minute_offset'] = int(offset)
        except: self.output_aet['monthly_minute_offset'] = int(0)
        try: 
            self.output_aet['monthly_float_format'] = config.get(output_aet_sec, 'monthly_float_format')
            if self.output_aet['monthly_float_format'] == 'None': self.output_aet['monthly_float_format'] = None
        except: self.output_aet['monthly_float_format'] = None
        try:
            self.output_aet['annual_date_format'] = config.get(output_aet_sec, 'annual_date_format')
            if self.output_aet['annual_date_format'] is None or self.output_aet['annual_date_format'] == 'None':
                if self.output_aet['file_type'] == 'xls':
                    self.output_aet['annual_date_format'] = 'm/yyyy'
                else:
                    self.output_aet['annual_date_format'] = '%Y-%m'
        except:
            if self.output_aet['file_type'] == 'xls':
                self.output_aet['annual_date_format'] = 'm/yyyy'
            else:
                self.output_aet['annual_date_format'] = '%Y-%m'
        try:
            offset = config.getint(output_aet_sec, 'annual_hour_offset')
            if offset is None or offset == 'None':
                self.output_aet['annual_hour_offset'] = int(0)
            else:
                self.output_aet['annual_hour_offset'] = int(offset)
        except: self.output_aet['annual_hour_offset'] = int(0)
        try:
            offset = config.getint(output_aet_sec, 'annual_minute_offset')
            if offset is None or offset == 'None':
                self.output_aet['annual_minute_offset'] = int(0)
            else:
                self.output_aet['annual_minute_offset'] = int(offset)
        except: self.output_aet['annual_minute_offset'] = int(0)
        try: 
            self.output_aet['annual_float_format'] = config.get(output_aet_sec, 'annual_float_format')
            if self.output_aet['annual_float_format'] == 'None': self.output_aet['annual_float_format'] = None
        except: self.output_aet['annual_float_format'] = None

        # Date or Year, Month, Day or both and/or DOY can be posted
    
        try: self.output_aet['fields']['date'] = config.get(output_aet_sec, 'date_field')
        except: self.output_aet['fields']['date'] = None
        try: self.output_aet['fields']['year'] = config.get(output_aet_sec, 'year_field')
        except: self.output_aet['fields']['year'] = None
        try: self.output_aet['fields']['month'] = config.get(output_aet_sec, 'month_field')
        except: self.output_aet['fields']['month'] = None
        try: self.output_aet['fields']['day'] = config.get(output_aet_sec, 'day_field')
        except: self.output_aet['fields']['day'] = None
        try: self.output_aet['fields']['doy'] = config.get(output_aet_sec, 'doy_field')
        except: self.output_aet['fields']['doy'] = None
        if self.output_aet['fields']['date'] is not None:
            logging.info('  OUTAET: Posting date to date column')
        elif (self.output_aet['fields']['year'] is not None and
              self.output_aet['fields']['month'] is not None and
              self.output_aet['fields']['day'] is not None):
            logging.info('  OUTAET: Posting date to year, month, and day columns')
        else:
            logging.error('  ERROR: OUTAET date_field (or year, month, and ' +
                          'day fields) must be set in  INI')
            sys.exit()                  

        # output aet data file name specifications, field names, and units
    
        self.output_aet['wsspec']['et'] = None
        try:
            self.output_aet['fields']['et'] = config.get(output_aet_sec, 'et_field')
            if self.output_aet['fields']['et'] is None or self.output_aet['fields']['et'] == 'None':
                self.output_aet['fnspec']['et'] = 'Unused'
                self.output_aet['fields']['et'] = 'ET'
                self.output_aet['units']['et'] = 'inches/day'
            else:    # et is being posted - get units and/or file name spec
                try: 
                    self.output_aet['units']['et'] = config.get(output_aet_sec, 'et_units')
                    if self.output_aet['units']['et'] is None or self.output_aet['units']['et'] == 'None':
                        self.output_aet['units']['et'] = 'inches/day'
                except: self.output_aet['units']['et'] = 'inches/day'
                try:
                    self.output_aet['fnspec']['et'] = config.get(output_aet_sec, 'et_name')
                    if self.output_aet['fnspec']['et'] is None or self.output_aet['fnspec']['et'] == 'None':
                        self.output_aet['fnspec']['et'] = self.output_aet['fields']['et']
                except: self.output_aet['fnspec']['et'] = self.output_aet['fields']['et']
                if self.output_aet['file_type'].lower() == 'xls' or self.output_aet['file_type'].lower() == 'wb':
                    try: 
                        self.output_aet['wsspec']['et'] = config.get(output_aet_sec, 'et_ws')
                        if self.output_aet['wsspec']['et'] is None or self.output_aet['wsspec']['et'] == 'None':
                            logging.info('  INFO:  OUTAET: et worksheet name set to ET')
                            self.output_aet['wsspec']['et'] = 'ET'
                    except:
                        logging.info('  INFO:  OUTAET: et worksheet name set to ET')
                        self.output_aet['wsspec']['et'] = 'ET'
        except:
            self.output_aet['fnspec']['et'] = 'Unused'
            self.output_aet['fields']['et'] = 'ET'
            self.output_aet['units']['et'] = 'inches/day'

        self.output_aet['wsspec']['nir'] = None
        try:
            self.output_aet['fields']['nir'] = config.get(output_aet_sec, 'nir_field')
            if self.output_aet['fields']['nir'] is None or self.output_aet['fields']['nir'] == 'None':
                self.output_aet['fnspec']['nir'] = 'Unused'
                self.output_aet['fields']['nir'] = 'NIR'
                self.output_aet['units']['nir'] = 'inches/day'
            else:    # nir is being posted - gnir units and/or file name spec
                try: 
                    self.output_aet['units']['nir'] = config.get(output_aet_sec, 'nir_units')
                    if self.output_aet['units']['nir'] is None or self.output_aet['units']['nir'] == 'None':
                        self.output_aet['units']['nir'] = 'inches/day'
                except: self.output_aet['units']['nir'] = 'inches/day'
                try:
                    self.output_aet['fnspec']['nir'] = config.get(output_aet_sec, 'nir_name')
                    if self.output_aet['fnspec']['nir'] is None or self.output_aet['fnspec']['nir'] == 'None':
                        self.output_aet['fnspec']['nir'] = self.output_aet['fields']['nir']
                except: self.output_aet['fnspec']['nir'] = self.output_aet['fields']['nir']
                if self.output_aet['file_type'].lower() == 'xls' or self.output_aet['file_type'].lower() == 'wb':
                    try: 
                        self.output_aet['wsspec']['nir'] = config.get(output_aet_sec, 'nir_ws')
                        if self.output_aet['wsspec']['nir'] is None or self.output_aet['wsspec']['nir'] == 'None':
                            logging.info('  INFO:  OUTAET: nir worksheet name set to NIR')
                            self.output_aet['wsspec']['nir'] = 'NIR'
                    except:
                        logging.info('  INFO:  OUTAET: nir worksheet name set to NIR')
                        self.output_aet['wsspec']['nir'] = 'NIR'
        except:
            self.output_aet['fnspec']['nir'] = 'Unused'
            self.output_aet['fields']['nir'] = 'NIR'
            self.output_aet['units']['nir'] = 'inches/day'

        self.output_aet['wsspec']['etflow'] = None
        try:
            self.output_aet['fields']['etflow'] = config.get(output_aet_sec, 'etflow_field')
            if self.output_aet['fields']['etflow'] is None or self.output_aet['fields']['etflow'] == 'None':
                self.output_aet['fnspec']['etflow'] = 'Unused'
                self.output_aet['fields']['etflow'] = 'ET_Flow'
                self.output_aet['units']['etflow'] = 'cfs'
            else:    # etflow is being posted - getflow units and/or file name spec
                try: 
                    self.output_aet['units']['etflow'] = config.get(output_aet_sec, 'etflow_units')
                    if self.output_aet['units']['etflow'] is None or self.output_aet['units']['etflow'] == 'None':
                        self.output_aet['units']['etflow'] = 'cfs'
                except: self.output_aet['units']['etflow'] = 'cfs'
                try:
                    self.output_aet['fnspec']['etflow'] = config.get(output_aet_sec, 'etflow_name')
                    if self.output_aet['fnspec']['etflow'] is None or self.output_aet['fnspec']['etflow'] == 'None':
                        self.output_aet['fnspec']['etflow'] = self.output_aet['fields']['etflow']
                except: self.output_aet['fnspec']['etflow'] = self.output_aet['fields']['etflow']
                if self.output_aet['file_type'].lower() == 'xls' or self.output_aet['file_type'].lower() == 'wb':
                    try: 
                        self.output_aet['wsspec']['etflow'] = config.get(output_aet_sec, 'etflow_ws')
                        if self.output_aet['wsspec']['etflow'] is None or self.output_aet['wsspec']['etflow'] == 'None':
                            logging.info('  INFO:  OUTAET: et flow worksheet name set to ET_Flow')
                            self.output_aet['wsspec']['etflow'] = 'ET_Flow'
                    except:
                        logging.info('  INFO:  OUTAET: et flow worksheet name set to ET_Flow')
                        self.output_aet['wsspec']['etflow'] = 'ET_Flow'
        except:
            self.output_aet['fnspec']['etflow'] = 'Unused'
            self.output_aet['fields']['etflow'] = 'ET_Flow'
            self.output_aet['units']['etflow'] = 'cfs'

        self.output_aet['wsspec']['nirflow'] = None
        try:
            self.output_aet['fields']['nirflow'] = config.get(output_aet_sec, 'nirflow_field')
            if self.output_aet['fields']['nirflow'] is None or self.output_aet['fields']['nirflow'] == 'None':
                self.output_aet['fnspec']['nirflow'] = 'Unused'
                self.output_aet['fields']['nirflow'] = 'NIR_Flow'
                self.output_aet['units']['nirflow'] = 'cfs'
            else:    # nirflow is being posted - get nirflow units and/or file name spec
                try: 
                    self.output_aet['units']['nirflow'] = config.get(output_aet_sec, 'nirflow_units')
                    if self.output_aet['units']['nirflow'] is None or self.output_aet['units']['nirflow'] == 'None':
                        self.output_aet['units']['nirflow'] = 'cfs'
                except: self.output_aet['units']['nirflow'] = 'cfs'
                try:
                    self.output_aet['fnspec']['nirflow'] = config.get(output_aet_sec, 'nirflow_name')
                    if self.output_aet['fnspec']['nirflow'] is None or self.output_aet['fnspec']['nirflow'] == 'None':
                        self.output_aet['fnspec']['nirflow'] = self.output_aet['fields']['nirflow']
                except: self.output_aet['fnspec']['nirflow'] = self.output_aet['fields']['nirflow']
                if self.output_aet['file_type'].lower() == 'xls' or self.output_aet['file_type'].lower() == 'wb':
                    try: 
                        self.output_aet['wsspec']['nirflow'] = config.get(output_aet_sec, 'nirflow_ws')
                        if self.output_aet['wsspec']['nirflow'] is None or self.output_aet['wsspec']['nirflow'] == 'None':
                            logging.info('  INFO:  OUTAET: et flow worksheet name set to NIR_Flow')
                            self.output_aet['wsspec']['nirflow'] = 'NIR_Flow'
                    except:
                        logging.info('  INFO:  OUTAET: et flow worksheet name set to NIR_Flow')
                        self.output_aet['wsspec']['nirflow'] = 'NIR_Flow'
        except:
            self.output_aet['fnspec']['nirflow'] = 'Unused'
            self.output_aet['fields']['nirflow'] = 'NIR_Flow'
            self.output_aet['units']['nirflow'] = 'cfs'

        self.output_aet['wsspec']['refet'] = None
        try:
            self.output_aet['fields']['refet'] = config.get(output_aet_sec, 'ret_field')
            if self.output_aet['fields']['refet'] is None or self.output_aet['fields']['refet'] == 'None':
                self.output_aet['fnspec']['refet'] = 'Unused'
                self.output_aet['fields']['refet'] = 'RET'
                self.output_aet['units']['refet'] = 'inches/day'
            else:    # refet is being posted - get units and/or file name spec
                try: 
                    self.output_aet['units']['refet'] = config.get(output_aet_sec, 'ret_units')
                    if self.output_aet['units']['refet'] is None or self.output_aet['units']['refet'] == 'None':
                        self.output_aet['units']['refet'] = 'inches/day'
                except: self.output_aet['units']['refet'] = 'inches/day'
                try:
                    self.output_aet['fnspec']['refet'] = config.get(output_aet_sec, 'ret_name')
                    if self.output_aet['fnspec']['refet'] is None or self.output_aet['fnspec']['refet'] == 'None':
                        self.output_aet['fnspec']['refet'] = self.output_aet['fields']['refet']
                except: self.output_aet['fnspec']['refet'] = self.output_aet['fields']['refet']
                if self.output_aet['file_type'].lower() == 'xls' or self.output_aet['file_type'].lower() == 'wb':
                    try: 
                        self.output_aet['wsspec']['refet'] = config.get(output_aet_sec, 'ret_ws')
                        if self.output_aet['wsspec']['refet'] is None or self.output_aet['wsspec']['refet'] == 'None':
                            logging.info('  INFO:  OUTAET: ret worksheet name set to RET')
                            self.output_aet['wsspec']['refet'] = 'RET'
                    except:
                        logging.info('  INFO:  OUTAET: ret worksheet name set to RET')
                        self.output_aet['wsspec']['refet'] = 'RET'
        except:
            self.output_aet['fnspec']['refet'] = 'Unused'
            self.output_aet['fields']['refet'] = 'RET'
            self.output_aet['units']['refet'] = 'inches/day'

        self.output_aet['wsspec']['ppt'] = None
        try:
            self.output_aet['fields']['ppt'] = config.get(output_aet_sec, 'ppt_field')
            if self.output_aet['fields']['ppt'] is None or self.output_aet['fields']['ppt'] == 'None':
                self.output_aet['fnspec']['ppt'] = 'Unused'
                self.output_aet['fields']['ppt'] = 'Precip'
                self.output_aet['units']['ppt'] = 'inches/day'
            else:    # ppt is being posted - get units
                self.output_aet['fnspec']['ppt'] = 'Precip'
                try: 
                    self.output_aet['units']['ppt'] = config.get(output_aet_sec, 'ppt_units')
                    if self.output_aet['units']['ppt'] is None: 
                        self.output_aet['units']['ppt'] = 'inches/day'
                except: self.output_aet['units']['ppt'] = 'inches/day'
                try:
                    self.output_aet['fnspec']['ppt'] = config.get(output_aet_sec, 'ppt_name')
                    if self.output_aet['fnspec']['ppt'] is None or self.output_aet['fnspec']['ppt'] == 'None':
                        self.output_aet['fnspec']['ppt'] = self.output_aet['fields']['ppt']
                except: self.output_aet['fnspec']['ppt'] = self.output_aet['fields']['ppt']
                if self.output_aet['file_type'].lower() == 'xls' or self.output_aet['file_type'].lower() == 'wb':
                    try: 
                        self.output_aet['wsspec']['ppt'] = config.get(output_aet_sec, 'ppt_ws')
                        if self.output_aet['wsspec']['ppt'] is None or self.output_aet['wsspec']['ppt'] == 'None':
                            logging.info('  INFO:  OUTAET: precip worksheet name set to Prcp')
                            self.output_aet['wsspec']['ppt'] = 'Prcp'
                    except:
                        logging.info('  INFO:  OUTAET: precip worksheet name set to Prcp')
                        self.output_aet['wsspec']['ppt'] = 'Prcp'
        except:
            self.output_aet['fnspec']['ppt'] = 'Unused'
            self.output_aet['fields']['ppt'] = 'Precip'
            self.output_aet['units']['ppt'] = 'inches/day'
            
        self.output_aet['wsspec']['nirfrac'] = None
        try:
            self.output_aet['fields']['nirfrac'] = config.get(output_aet_sec, 'nirfrac_field')
            if self.output_aet['fields']['nirfrac'] is None or self.output_aet['fields']['nirfrac'] == 'None':
                self.output_aet['fnspec']['nirfrac'] = 'Unused'
                self.output_aet['fields']['nirfrac'] = 'NIR_Frac'
                self.output_aet['units']['nirfrac'] = 'fraction'
            else:    # nirfrac is being posted - gnirfrac units and/or file name spec
                try: 
                    self.output_aet['units']['nirfrac'] = config.get(output_aet_sec, 'nirfrac_units')
                    if self.output_aet['units']['nirfrac'] is None or self.output_aet['units']['nirfrac'] == 'None':
                        self.output_aet['units']['nirfrac'] = 'fraction'
                except: self.output_aet['units']['nirfrac'] = 'fraction'
                try:
                    self.output_aet['fnspec']['nirfrac'] = config.get(output_aet_sec, 'nirfrac_name')
                    if self.output_aet['fnspec']['nirfrac'] is None or self.output_aet['fnspec']['nirfrac'] == 'None':
                        self.output_aet['fnspec']['nirfrac'] = self.output_aet['fields']['nirfrac']
                except: self.output_aet['fnspec']['nirfrac'] = self.output_aet['fields']['nirfrac']
                if self.output_aet['file_type'].lower() == 'xls' or self.output_aet['file_type'].lower() == 'wb':
                    try: 
                        self.output_aet['wsspec']['nirfrac'] = config.get(output_aet_sec, 'nirfrac_ws')
                        if self.output_aet['wsspec']['nirfrac'] is None or self.output_aet['wsspec']['nirfrac'] == 'None':
                            logging.info('  INFO:  OUTAET: nir fractions worksheet name set to NIR_Frac')
                            self.output_aet['wsspec']['nirfrac'] = 'NIR_Frac'
                    except:
                        logging.info('  INFO:  OUTAET: nir fractions worksheet name set to NIR_Frac')
                        self.output_aet['wsspec']['nirfrac'] = 'NIR_Frac'
        except:
            self.output_aet['fnspec']['nirfrac'] = 'Unused'
            self.output_aet['fields']['nirfrac'] = 'NIR_Frac'
            self.output_aet['units']['nirfrac'] = 'fraction'

        # drop unused fields
    
        all_output_aet_fields = ['date', 'year', 'month', 'day', 'doy', 'refet', 'ppt', 'et', 'nir', 'etflow', 'nirflow', 'nirfrac']
        for k, v in self.output_aet['fnspec'].items():
            if not v is None:
                try:
                    if v.lower() == 'unused':
                        del self.output_aet['units'][k] 
                        del self.output_aet['fnspec'][k] 
                        del self.output_aet['fields'][k] 
                except: pass
        for k, v in self.output_aet['fields'].items():
            if v is None:
                try: del self.output_aet['fields'][k] 
                except: pass
                        
        # Check units
    
        for k, v in self.output_aet['units'].iteritems():
            if v is not None and v.lower() not in units_list:
                logging.error('  ERROR: {0} units {1} are not currently supported'.format(k,v))
                sys.exit()
                
        # Flow as volume units

        try:
            self.output_aet['daily_volume_units'] = config.get(output_aet_sec, 'daily_volume_units')
            if self.output_aet['daily_volume_units'] == 'None':
                self.output_aet['daily_volume_units'] = None
        except:
            self.output_aet['daily_volume_units'] = None
        try:
            self.output_aet['monthly_volume_units'] = config.get(output_aet_sec, 'monthly_volume_units')
            if self.output_aet['monthly_volume_units'] == 'None':
                self.output_aet['monthly_volume_units'] = None
        except:
            self.output_aet['monthly_volume_units'] = None
        try:
            self.output_aet['annual_volume_units'] = config.get(output_aet_sec, 'annual_volume_units')
            if self.output_aet['annual_volume_units'] == 'None':
                self.output_aet['annual_volume_units'] = None
        except:
            self.output_aet['annual_volume_units'] = None

        # set up header lines

        self.used_output_aet_fields = [fn for fn in all_output_aet_fields if fn in self.output_aet['fields'].keys()]
        self.output_aet['data_out_fields'] = [fn for fn in self.used_output_aet_fields if fn not in ['date', 'year', 'month', 'day', 'doy']]
        self.output_aet['out_data_fields'] = []
        if self.output_aet['header_lines'] == 2:
            for fc, fn in enumerate(self.used_output_aet_fields):
                if fc == 0:
                    self.output_aet['daily_header1'] = self.output_aet['fields'][fn]
                    self.output_aet['daily_header2'] = "Units"
                else: 
                    self.output_aet['daily_header1'] = self.output_aet['daily_header1'] + self.output_aet['delimiter'] + self.output_aet['fields'][fn]
                    if fn in self.output_aet['data_out_fields']    :
                        self.output_aet['daily_header2'] = self.output_aet['daily_header2'] + \
                                    self.output_aet['delimiter'] + self.output_aet['units'][fn]
                        self.output_aet['out_data_fields'].append(self.output_aet['fields'][fn])
                    else:
                        self.output_aet['daily_header2'] = self.output_aet['daily_header2'] + self.output_aet['delimiter']
        else:
            for fc, fn in enumerate(self.used_output_aet_fields):
                if fc == 0:
                    self.output_aet['daily_header1'] = self.output_aet['fields'][fn]
                else: 
                    if fn in self.output_aet['data_out_fields']    :
                        self.output_aet['daily_header1'] = self.output_aet['daily_header1'] + self.output_aet['delimiter'] + self.output_aet['fields'][fn]
                        if self.output_aet['units_in_header']:
                            self.output_aet['daily_header1'] = self.output_aet['daily_header1'] + " (" + self.output_aet['units'][fn] + ")"
                        self.output_aet['out_data_fields'].append(self.output_aet['fields'][fn])
                    else:
                        self.output_aet['daily_header1'] = self.output_aet['daily_header1'] + self.output_aet['delimiter'] + self.output_aet['fields'][fn]
            self.output_aet['daily_header2'] = ""
        if self.output_aet['daily_volume_units'] is not None:
            if 'etflow' in self.used_output_aet_fields:
                self.output_aet['daily_header1'] = self.output_aet['daily_header1'].replace(self.output_aet['units']['etflow'], self.output_aet['daily_volume_units'])
                self.output_aet['daily_header2'] = self.output_aet['daily_header2'].replace(self.output_aet['units']['etflow'], self.output_aet['daily_volume_units'])
            if 'nirflow' in self.used_output_aet_fields:
                self.output_aet['daily_header1'] = self.output_aet['daily_header1'].replace(self.output_aet['units']['nirflow'], self.output_aet['daily_volume_units'])
                self.output_aet['daily_header2'] = self.output_aet['daily_header2'].replace(self.output_aet['units']['nirflow'], self.output_aet['daily_volume_units'])
        if 'day' in self.output_aet['fields'] and self.output_aet['fields']['day'] is not None: 
            drop_string = self.output_aet['delimiter'] + self.output_aet['fields']['day']
            self.output_aet['monthly_header1'] = self.output_aet['daily_header1'].replace(drop_string, '')
            self.output_aet['monthly_header2'] = self.output_aet['daily_header2'].replace(drop_string, '')
        else:
            self.output_aet['monthly_header1'] = self.output_aet['daily_header1']
            self.output_aet['monthly_header2'] = self.output_aet['daily_header2']
        if 'doy' in self.output_aet['fields'] and self.output_aet['fields']['doy'] is not None: 
            drop_string = self.output_aet['delimiter'] + self.output_aet['fields']['doy']
            self.output_aet['monthly_header1'] = self.output_aet['monthly_header1'].replace(drop_string, '')
            self.output_aet['monthly_header2'] = self.output_aet['monthly_header2'].replace(drop_string, '')
        if self.output_aet['monthly_volume_units'] is not None:
            if 'etflow' in self.used_output_aet_fields:
                self.output_aet['monthly_header1'] = self.output_aet['monthly_header1'].replace(self.output_aet['units']['etflow'], self.output_aet['monthly_volume_units'])
                self.output_aet['monthly_header2'] = self.output_aet['monthly_header2'].replace(self.output_aet['units']['etflow'], self.output_aet['monthly_volume_units'])
            if 'nirflow' in self.used_output_aet_fields:
                self.output_aet['monthly_header1'] = self.output_aet['monthly_header1'].replace(self.output_aet['units']['nirflow'], self.output_aet['monthly_volume_units'])
                self.output_aet['monthly_header2'] = self.output_aet['monthly_header2'].replace(self.output_aet['units']['nirflow'], self.output_aet['monthly_volume_units'])
        if 'month' in self.output_aet['fields'] and self.output_aet['fields']['month'] is not None: 
            drop_string = self.output_aet['delimiter'] + self.output_aet['fields']['month']
            self.output_aet['annual_header1'] = self.output_aet['monthly_header1'].replace(drop_string, '')
            self.output_aet['annual_header2'] = self.output_aet['monthly_header2'].replace(drop_string, '')
        else:
            self.output_aet['annual_header1'] = self.output_aet['monthly_header1']
            self.output_aet['annual_header2'] = self.output_aet['monthly_header2']
        if self.output_aet['annual_volume_units'] is not None:
            if 'etflow' in self.used_output_aet_fields:
                self.output_aet['annual_header1'] = self.output_aet['annual_header1'].replace(self.output_aet['units']['etflow'], self.output_aet['annual_volume_units'])
                self.output_aet['annual_header2'] = self.output_aet['annual_header2'].replace(self.output_aet['units']['etflow'], self.output_aet['annual_volume_units'])
            if 'nirflow' in self.used_output_aet_fields:
                self.output_aet['annual_header1'] = self.output_aet['annual_header1'].replace(self.output_aet['units']['nirflow'], self.output_aet['annual_volume_units'])
                self.output_aet['annual_header2'] = self.output_aet['annual_header2'].replace(self.output_aet['units']['nirflow'], self.output_aet['annual_volume_units'])

        # drop unused output aet fields from fnspec and units
        
        for k, v in self.output_aet['fnspec'].items():
            if not v is None:
                try:
                    if v.lower() == 'unused':
                        del self.output_aet['units'][k] 
                        del self.output_aet['fnspec'][k] 
                        del self.output_aet['fields'][k] 
                except: pass

    def set_crop_params(self):
        """ Reads crop parameters from specified file and type"""
        logging.info('\nReading crop parameters data from\n' + self.crop_params_path)
        self.crop_type_names = []
        self.crop_type_numbers = []
        self.crop_irr_flags = []
        if ".xls" in self.crop_params_path.lower():
            params_df = pd.read_excel(self.crop_params_path, sheetname = self.crop_params_ws, 
                header = None, skiprows = self.crop_params_header_lines -1, na_values = ['NaN'])
        else:
            params_df = pd.read_table(self.crop_params_path, delimiter = self.crop_params_delimiter, 
                    header = None, skiprows = self.crop_params_header_lines -1, na_values = ['NaN'])
        params_df.applymap(str)
        params_df.fillna('0', inplace = True)
        for crop_i in range(2, len(list(params_df.columns))):
            crop_param_data = params_df[crop_i].values.astype(str)
            crop_type_number = abs(int(crop_param_data[1]))
            crop_type_name = str(crop_param_data[0]).replace('"', '').split("-")[0].strip()
            crop_irr_flag = int(crop_param_data[2])
            self.crop_type_names.append(crop_type_name)
            self.crop_type_numbers.append(crop_type_number)
            self.crop_irr_flags.append(crop_irr_flag)

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
    ini_path = os.getcwd() + os.sep + "aet_template.ini"
    cfg = AreaETConfig()
    cfg.read_aet_ini(ini_path, True)
    
if __name__ == '__main__':
    # testing during development
    do_tests()        
