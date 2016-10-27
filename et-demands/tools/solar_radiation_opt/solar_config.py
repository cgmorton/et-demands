#!/usr/bin/env python

import ConfigParser
import datetime
import pandas as pd
import os
import sys

class SolarConfig():
    def __init__(self):
        """ """

    def __str__(self):
        """ """
        return '<SolarConfig>'

    def set_solar_ini(self, sheet_delim, elevation, latitude, longitude, missing_data_value):
        """set solar calibration optimization configuration
    
        This uses a mixture of command line values and hard wired values
    
        Args:

        Returns:
            None
        """

        self.project_ws = os.getcwd()
        self.file_type = None
        self.file_path = None
        self.start_dt = None
        self.end_dt = None
        self.elevation = elevation
        self.latitude = latitude
        self.longitude = longitude
        self.missing_data_value = missing_data_value
        self.header_lines = 1
        self.names_line = 1
        self.sheet_delim = sheet_delim
        self.input_met = {}
        self.input_met['fields'] = {}
        self.input_met['units'] = {}
        self.input_met['fields']['date'] = 'Date'
        self.input_met['fields']['year'] = 'Year'
        self.input_met['fields']['month'] = 'Month'
        self.input_met['fields']['day'] = 'Day'
        self.input_met['fields']['tmax'] = 'TmaxC'
        self.input_met['units']['tmax'] = 'C'
        self.input_met['fields']['tmin'] = 'TminC'
        self.input_met['units']['tmin'] = 'C'
        self.input_met['fields']['tdew'] = 'TdewC'
        self.input_met['units']['tdew'] = 'C'
        self.input_met['fields']['rs'] = 'Rs_MJ_m2'
        self.input_met['units']['rs'] = 'MJ/m2'

    def read_solar_ini(self, ini_path, debug_flag = False):
        """read solar calibration optimization configuration
    
        This reads and processes configuration data
    
        Args:
            ini_path: configuration (initialization) file path
            debug_flag (bool): If True, write debug level comments to debug.txt

        Returns:
            None
        """

        # print "arg ini path is " + ini_pathReading date
        print 'INI: ', os.path.basename(ini_path)

        # Check that INI file can be read
        
        config = ConfigParser.ConfigParser()
        try:
            ini = config.readfp(open(ini_path))
            if debug_flag: 
                cfg_path = os.path.join(os.getcwd(), "test_ret.cfg")
                with open(cfg_path, 'wb') as cf: config.write(cf)
        except:
            print '\nERROR: Config file \n' + ini_path + \
                '\ncould not be read.  It is not an input file or does not exist.\n'
            sys.exit()

        project_sec = 'PROJECT'    # required
        meta_sec = 'SOLAR_META'    # required
        input_met_sec = 'INMET'    # required
        units_list = (['c', 'f', 'k'] +
            ['mj/m2', 'mj/m^2', 'mj/m2/d', 'mj/m^2/d', 'mj/m2/day', 'mj/m^2/day'] + 
            ['w/m2', 'w/m^2', 'cal/cm2', 'cal/cm2', 'cal/cm2/d', 'cal/cm^2/d'] +
            ['cal/cm2/day', 'cal/cm^2/day', 'langley'])
        
        # Check that required sections are present
        
        cfgSecs = config.sections()
        if project_sec not in cfgSecs or meta_sec not in cfgSecs or input_met_sec not in cfgSecs:
            print '\nERROR:  reference et ini file must have  following sections:\n', \
                project_sec, meta_sec, input_met_sec
            sys.exit()
            
        # project specfications
        
        #  project folder need to be full/absolute path
        
        self.project_ws = config.get(project_sec, 'project_folder')
        if debug_flag: print "Project workspace is " + self.project_ws
        if not os.path.isdir(self.project_ws):
            print '\nERROR:  project folder does not exist in', self.project_ws
            sys.exit()
        
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
        
        # station meta data

        # elevation units

        try:
            elev_units = config.get(meta_sec, 'elev_units').lower()
            if elev_unit is None or self.elev_units == 'None': elev_units = 'meter'
        except:
            elev_units = 'meter'

        # elevation

        try: self.elevation = config.getfloat(meta_sec, 'elevation')
        except: self.elevation = None
        
        # convert elevation if needed

        if not self.elevation is None and elev_units == 'feet':
            self.elevation *= 0.3048

        # latitude

        try: self.latitude = config.getfloat(meta_sec, 'latitude')
        except: self.latitude = None

        # longitude

        try: self.longitude = config.getfloat(meta_sec, 'longitude')
        except: self.longitude = None

        # missing  data value

        try:
            self.missing_data_value = config.get(meta_sec, 'missing_data_value')
            if self.missing_data_value == 'None': self.missing_data_value = 'NaN'
        except:
            self.missing_data_value = 'NaN'

        # input met data parameters
        
        self.input_met = {}
        self.input_met['fields'] = {}
        self.input_met['units'] = {}
        self.input_met['ws'] = config.get(input_met_sec, 'input_met_folder')
        
        # input met folder could be  full or relative path
        # Assume relative paths or from  project folder
        
        if os.path.isdir(self.input_met['ws']):
            pass
        elif (not os.path.isdir(self.input_met['ws']) and
              os.path.isdir(os.path.join(self.project_ws, self.input_met['ws']))):
            self.input_met['ws'] = os.path.join(self.project_ws, self.input_met['ws'])
        else:
            print '\nERROR:  input met data folder', self.input_met['ws'], 'does not exist.'
            sys.exit()
        if not os.path.isdir(self.input_met['ws']):
            print '\nERROR:  input met data folder', self.input_met['ws'], 'does not exist'
            sys.exit()
            
        self.file_type = config.get(input_met_sec, 'file_type').lower()
        file_name = config.get(input_met_sec, 'file_name')
        self.file_path = os.path.join(self.input_met['ws'], file_name)
        if not os.path.isfile(self.file_path):
            print '\nERROR:  input met file ', self.file_path, 'does not exist.'
            sys.exit()
        self.header_lines = config.getint(input_met_sec, 'header_lines')
        self.names_line = config.getint(input_met_sec, 'names_line')
        try:
            self.sheet_delim = config.get(input_met_sec, 'sheet_delim')
            if self.sheet_delim is None or self.sheet_delim == 'None': 
                if self.file_type == 'xls':
                    self.sheet_delim = 'sheet1'
                else:
                    self.sheet_delim = ','
            else:
                if self.file_type != 'xls':
                    if self.sheet_delim not in [' ', ',', '\\t']: self.sheet_delim = ','
                    if "\\" in self.sheet_delim and "t" in self.sheet_delim:
                        self.sheet_delim = self.sheet_delim.replace('\\t', '\t')
        except:
            if self.file_type == 'xls':
                self.sheet_delim = 'sheet1'
            else:
                self.sheet_delim = ','

        # Date can be read directly or computed from year, month, and day
        
        try: self.input_met['fields']['date'] = config.get(input_met_sec, 'date_field')
        except: self.input_met['fields']['date'] = None
        try: self.input_met['fields']['year'] = config.get(input_met_sec, 'year_field')
        except: self.input_met['fields']['year'] = 'Year'
        try: self.input_met['fields']['month'] = config.get(input_met_sec, 'month_field')
        except: self.input_met['fields']['month'] = 'Month'
        try: self.input_met['fields']['day'] = config.get(input_met_sec, 'day_field')
        except: self.input_met['fields']['day'] = 'Day'
        if self.input_met['fields']['date'] is not None:
            print 'INMET:  Reading date from date column'
        elif (self.input_met['fields']['year'] is not None and
              self.input_met['fields']['month'] is not None and
              self.input_met['fields']['day'] is not None):
            print 'INMET:  Reading date from year, month, and day columns'
        else:
            print '\nERROR: INMET date_field or year, month, and', \
                'day fields must be set in  INI'
            sys.exit()                  

        # Required input met fields for computing reference et

        try:
            self.input_met['fields']['tmax'] = config.get(input_met_sec, 'tmax_field')
            if self.input_met['fields']['tmax'] is None or self.input_met['fields']['tmax'] == 'None':
                print '\nERROR: tmax field name is required\n'
                sys.exit()
            else:
                try: self.input_met['units']['tmax'] = config.get(input_met_sec, 'tmax_units')
                except: self.input_met['units']['tmax'] = 'C'
        except:
            print '\nERROR: tmax field name is required\n'
            sys.exit()

        try:
            self.input_met['fields']['tmin'] = config.get(input_met_sec, 'tmin_field')
            if self.input_met['fields']['tmin'] is None or self.input_met['fields']['tmin'] == 'None':
                print '\nERROR: tmin field name is required\n'
                sys.exit()
            else:
                try: self.input_met['units']['tmin'] = config.get(input_met_sec, 'tmin_units')
                except: self.input_met['units']['tmin'] = 'C'
        except:
            print '\nERROR: tmin field name is required\n'
            sys.exit()

        try:
            self.input_met['fields']['tdew'] = config.get(input_met_sec, 'tdew_field')
            if self.input_met['fields']['tdew'] is None or self.input_met['fields']['tdew'] == 'None':
                print '\nERROR: tdew field name is required\n'
                sys.exit()
            else:
                try: self.input_met['units']['tdew'] = config.get(input_met_sec, 'tdew_units')
                except: self.input_met['units']['tdew'] = 'C'
        except:
            print '\nERROR: tdew field name is required\n'
            sys.exit()

        try:
            self.input_met['fields']['rs'] = config.get(input_met_sec, 'rs_field')
            if self.input_met['fields']['rs'] is None or self.input_met['fields']['rs'] == 'None':
                print '\nERROR: rs field name is required\n'
                sys.exit()
            else:
                try: self.input_met['units']['rs'] = config.get(input_met_sec, 'rs_units')
                except: self.input_met['units']['rs'] = 'MJ/m2'
        except:
            print '\nERROR: rs field name is required\n'
            sys.exit()

        """
        print "\n"
        for k, v in self.input_met['fields'].items():
            try: print "input met", k, "field name is", v
            except: pass
        print "\n"
        for k, v in self.input_met['units'].items():
            try: print "input met", k, "units are ", v
            except: pass
        print "\n"
        for k, v in self.input_met['fnspec'].items():
            try: print "input met", k, "file name specification is", v
            except: pass
        print "\n"
        for k, v in self.input_met['fields'].items():
            if not v is None:
                try:
                    print "input met 'fields' value for", k, "is", self.input_met['fields'][k]
                    if not self.input_met['units'][k] is None: print "input met 'units' value for", k, "is", self.input_met['units'][k]
                    if not self.input_met['fnspec'][k] is None: print "input met 'fnspec' value for", k, "is", self.input_met['fnspec'][k]
                except: pass
        print "\n"
        """

        # Check units
        
        for k, v in self.input_met['units'].iteritems():
            # print "input met field " + k + " units are " + v
            if v is not None and v.lower() not in units_list:
                print '\nERROR: field', k, 'units', v, 'are not currently supported.'
                sys.exit()
def do_tests():
    # Simple testing of functions as developed
    ini_path = os.getcwd() + os.sep + "solar_template.ini"
    cfg = SolarConfig()
    cfg.read_solar_ini(ini_path, True)
    
######################################## 
if __name__ == '__main__':
    ## testing during development
    do_tests()        
