#!/usr/bin/env python

from collections import defaultdict
import datetime
import logging
import math
import os
import re
import sys
import copy

import numpy as np
import pandas as pd
import xlrd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../lib')))
import crop_et_data
import util
import mod_dmis

mpdToMps = 3.2808399 * 5280 / 86400

class ETCellData():
    """Functions for loading ET Cell data fromstatic text files"""
    def __init__(self):
        """ """
        self.et_cells_dict = dict()
        self.crop_num_list = []
        self.et_cells_weather_data = {}
        self.et_cells_historic_data = {}

    def set_cell_properties(self, data):
        """Extract ET cells properties data from specified file

        This function builds ETCell objects and must be run first.
    
        Args:
            data:configuration data from INI file

        Returns:
            None
        """
        logging.info('\nReading ET Cells properties data from\n' + data.cell_properties_path)
        try:
            # Get list of 0 based line numbers to skip
            # Ignore header but assume header was set as 1's based index
            skiprows = [i for i in range(data.cell_properties_header_lines) if i + 1 <> data.cell_properties_names_line]
            if '.xls' in data.cell_properties_path.lower(): 
                df = pd.read_excel(data.cell_properties_path, 
                        sheetname = data.cell_properties_ws, 
                        header = data.cell_properties_names_line - len(skiprows) - 1, 
                        skiprows = skiprows, na_values = ['NaN'])
                        # skiprows = 0, na_values = ['NaN'])
            else:
                df = pd.read_table(data.cell_properties_path, engine = 'python', 
                        header = data.cell_properties_names_line - len(skiprows) - 1, 
                        skiprows = skiprows, sep = data.cell_properties_delimiter)
            uc_columns = list(df.columns)
            columns = [x.lower() for x in uc_columns]

            # remove excess baggage from column names
            
            columns = [x.replace(' (feet)', '').replace('in/hr', '').replace('in/ft', '').replace(' - in', '').replace('decimal ','') for x in columns]
            columns = [x.replace('met ', '').replace(' - ', '').replace(" (a='coarse'  b='medium')", '').replace(" (1='coarse' 2='medium')", '') for x in columns]
            columns = [x.replace(' (fromhuntington plus google)', '').replace('  ',' ') for x in columns]
            
            # parse et cells properties for each cell

            for rc, row in df.iterrows():
                row_list = row.tolist()
                cell = ETCell()
                if not(cell.read_cell_properties_from_row(row.tolist(), columns, 
                        data.elev_units)): 
                    sys.exit()
                self.et_cells_dict[cell.cell_id] = cell
        except: 
            logging.error('Unable to read ET Cells Properties from ' + data.cell_properties_path)
            logging.error('\nERROR: ' + str(sys.exc_info()[0]) + 'occurred\n')
            sys.exit()

    def set_cell_crops(self, data):
        """Read crop crop flags using specified file type
    
        Args:
            data:configuration data from INI file

        Returns:
            None
        """
        if ".xls" in data.cell_crops_path.lower():
            self.read_cell_crops_xls_xlrd(data)
        else:
            self.read_cell_crops_txt(data)
        
    def read_cell_crops_txt(self, data):
        """ExtractET cell crop data from text file

        Args:
            data:configuration data from INI file

        Returns:
            None
        """
        logging.info('\nReading cell crop flags from\n' + data.cell_crops_path)
        a = np.loadtxt(data.cell_crops_path, delimiter = data.cell_crops_delimiter, dtype = 'str')
        crop_numbers = a[data.cell_crops_names_line - 1, 4:].astype(int)
        crop_names = a[data.cell_crops_names_line ,4:]
        a = a[data.cell_crops_names_line + 1:]
        for i, row in enumerate(a):
            cell_id = row[0]
            # print('cell id: {}').format(cell_id)
            # print(self.et_cells_dict.keys())
            # sys.exit()
            if cell_id not in self.et_cells_dict.keys():
                logging.error('read_et_cells_crops(), cell_id %s not found' % cell_id)
                sys.exit()
            cell = self.et_cells_dict[cell_id]
            cell.init_crops_from_row(row, crop_numbers)
            cell.crop_names = crop_names
            cell.crop_numbers = crop_numbers
            # Make list of active crop numbers (i.e. flag is True) in cell
            
            cell.crop_num_list = sorted(
                [k for k,v in cell.crop_flags.items() if v])
            self.crop_num_list.extend(cell.crop_num_list)

        # Update list of active crop numbers in all cells
        
        self.crop_num_list = sorted(list(set(self.crop_num_list)))

    def read_cell_crops_xls_xlrd(self, data):
        """ExtractET cell crop data from Excel using xlrd

        Args:
            data: configuration data from INI file

        Returns:
            None
        """
        logging.info('\nReading cell crop flags from\n' + data.cell_crops_path)
        wb = xlrd.open_workbook(data.cell_crops_path)
        ws = wb.sheet_by_name(data.cell_crops_ws)
        num_crops = int(ws.cell_value(data.cell_crops_names_line - 1, 1))
        crop_names = []
        crop_numbers = []
        for col_index in range(4, num_crops + 4):
            crop_type_number = int(ws.cell_value(data.cell_crops_names_line - 1, col_index))
            crop_numbers.append(crop_type_number)
            crop_type_name = str(ws.cell_value(data.cell_crops_names_line, col_index)).replace('"', '').split("-")[0].strip()
            crop_names.append(crop_type_name)
        crop_numbers = np.asarray(crop_numbers)
        crop_names = np.asarray(crop_names)
        for row_index in range(data.cell_crops_header_lines, ws.nrows):
            row = np.asarray(ws.row_values(row_index), dtype = np.str)
            for col_index in range(3, num_crops + 4):
                row[col_index] = row[col_index].replace(".0", "")
            cell_id = row[0]
            cell = self.et_cells_dict[cell_id]
            cell.init_crops_from_row(row, crop_numbers)
            cell.crop_numbers = crop_numbers
            cell.crop_names = crop_names

            # make List of active crop numbers (i.e. flag is True) in cell
            
            cell.crop_num_list = sorted(
                [k for k,v in cell.crop_flags.items() if v])
            self.crop_num_list.extend(cell.crop_num_list)

    def set_cell_cuttings(self, data):
        """Extract mean cutting data from specified file
    
        Args:
            data:configuration data from INI file

        Returns:
            None
        """
        logging.info('\nReading cell crop cuttings from\n' + data.cell_cuttings_path)
        try:
            # Get list of 0 based line numbers to skip
            # Ignore header but assume header was set as 1's based index
            skiprows = [i for i in range(data.cell_cuttings_header_lines) if i + 1 <> data.cell_cuttings_names_line]
            if '.xls' in data.cell_cuttings_path.lower(): 
                df = pd.read_excel(data.cell_cuttings_path, sheetname = data.cell_cuttings_ws, 
                        header = data.cell_cuttings_names_line- len(skiprows)  - 1, 
                        skiprows = skiprows, na_values = ['NaN'], parse_cols = [0, 1, 2, 3, 4])
                        # skiprows = 0, na_values = ['NaN'], parse_cols = [0, 1, 2, 3, 4])
            else:
                df = pd.read_table(data.cell_cuttings_path, engine = 'python', na_values = ['NaN'],
                        header = data.cell_cuttings_names_line - len(skiprows) - 1, 
                        skiprows = skiprows, sep = data.cell_cuttings_delimiter, 
                        usecols = [0, 1, 2, 3, 4])
            uc_columns = list(df.columns)
            columns = [x.lower() for x in uc_columns]
            cell_col = columns.index('et cell id')
            dairy_col = columns.index('number dairy')
            beef_col = columns.index('number beef')
            
            # parse et cells cuttings for each cell

            for rc, row in df.iterrows():
                row_list = row.tolist()
                cell_id = str(row[cell_col])
                if cell_id not in self.et_cells_dict.keys():
                    logging.error('crop_et_data.static_mean_cuttings(), cell_id %s not found' % cell_id)
                    sys.exit()
                cell = self.et_cells_dict[cell_id]
                cell.dairy_cuttings = int(row[dairy_col])
                cell.beef_cuttings = int(row[beef_col])
        except: 
            logging.error('Unable to read ET Cells cuttings from ' + data.cell_cuttings_path)
            logging.error('\nERROR: ' + str(sys.exc_info()[0]) + 'occurred\n')
            sys.exit()

    def filter_crops(self, data):
        logging.info('\nFiltering crop lists')
        crop_numbers = set(self.crop_num_list)

        # Update master crop list

        if data.annual_skip_flag:
            annual_crops = set(
                crop_num
                for crop_num, crop_param in data.crop_params.items()
                if not crop_param.is_annual)
            crop_numbers &= annual_crops
            logging.info('  Active perennial crops: {}'.format(
                ', '.join(map(str, sorted(crop_numbers)))))
        if data.perennial_skip_flag:
            perennial_crops = set(
                crop_num
                for crop_num, crop_param in data.crop_params.items()
                if crop_param.is_annual)
            crop_numbers &= perennial_crops
            logging.info('  Active annual crops: {}'.format(
                ', '.join(map(str, sorted(crop_numbers)))))
        if data.crop_skip_list:
            logging.info('  Crop skip list: {}'.format(
                ', '.join(map(str, data.crop_skip_list))))
            crop_numbers -= set(data.crop_skip_list)
        if data.crop_test_list:
            logging.info('  Crop test list: {}'.format(
                ', '.join(map(str, data.crop_test_list))))
            crop_numbers &= set(data.crop_test_list)

        # Get max length of CELL_ID for formatting of log string

        cell_id_len = max([
            len(cell_id) for cell_id in self.et_cells_dict.keys()])

        # Filter each cell with updated master crop list

        for cell_id, cell in sorted(self.et_cells_dict.items()):
            cell.crop_num_list = sorted(
                crop_numbers & set(cell.crop_num_list))
            # Turn off the crop flag

            cell.crop_flags = {
                c: f and c in cell.crop_num_list
                for c, f in cell.crop_flags.iteritems()}
            logging.info('  CellID: {1:{0}s}: {2}'.format(
                cell_id_len, cell_id,
                ', '.join(map(str, cell.crop_num_list))))

    def filter_cells(self, data):
        """Remove cells with no active crops"""
        logging.info('\nFiltering ET Cells')
        cell_ids = set(self.et_cells_dict.keys())
        if data.cell_skip_list:
            cell_ids -= set(data.cell_skip_list)
            logging.info('  Cell skip list: {}'.format(
                ','.join(map(str, data.cell_skip_list))))
        if data.cell_test_list:
            cell_ids &= set(data.cell_test_list)
            logging.info('  Cell test list: {}'.format(
                ','.join(map(str, data.cell_test_list))))

        # Get max length of CELL_ID for formatting of log string

        cell_id_len = max([
            len(cell_id) for cell_id in self.et_cells_dict.keys()])
        for cell_id, cell in sorted(self.et_cells_dict.items()):
            # Remove cells without any active crops
            
            if cell_id not in cell_ids:
                logging.info('  CellID: {1:{0}s} skipping'.format(
                    cell_id_len, cell_id))
                del self.et_cells_dict[cell_id]
            elif not set(self.crop_num_list) & set(cell.crop_num_list):
                logging.info('  CellID: {1:{0}s} skipping (no active crops)'.format(
                    cell_id_len, cell_id))
                del self.et_cells_dict[cell_id]

    def set_static_crop_params(self, crop_params):
        """"""
        logging.info('\nSetting static crop parameters')
        
        # copy crop_params
        
        for cell_id in sorted(self.et_cells_dict.keys()):
            cell = self.et_cells_dict[cell_id]
            cell.crop_params = copy.deepcopy(crop_params)

    def set_static_crop_coeffs(self, crop_coeffs):
        """"""
        logging.info('Setting static crop coefficients')
        for cell_id in sorted(self.et_cells_dict.keys()):
            cell = self.et_cells_dict[cell_id]
            cell.crop_coeffs = copy.deepcopy(crop_coeffs)

    def set_spatial_crop_params(self, calibration_ws):
        """"""
        import shapefile

        logging.info('Setting spatially varying crop parameters')
        cell_id_field = 'CELL_ID'
        crop_dbf_re = re.compile('crop_\d{2}_\w+.dbf$', re.I)

        # Get list of crop parameter shapefiles DBFs
        
        crop_dbf_dict = dict([
            (int(item.split('_')[1]), os.path.join(calibration_ws, item))
            for item in os.listdir(calibration_ws)
            if crop_dbf_re.match(item)])

        #Check to see if crop_dbf_dict is empty
        if not crop_dbf_dict:
            logging.error('\nSpatially Varying Calibration Files Do Not Exist. Run build_spatial_crop_params_arcpy.py')
            sys.exit()
            # return False
  
          # Filter the file list based on the "active" crops
        for crop_num in crop_dbf_dict.keys():
            if crop_num not in self.crop_num_list:
                try:
                    del crop_dbf_dict[crop_num]
                except:
                    pass

        #Check to see that all "active" crops have shapefiles in spatially varying calibration folder
        missing_set=set(self.crop_num_list)-set(crop_dbf_dict.keys())
        # if self.crop_num_list not in crop_dbf_dict.keys(): ###WHY DOESN't THIS WORK (Data Type Issue???)
        if len(missing_set) > 0:
            logging.error(('\nMissing Crop Shapefiles In Calibration Folder. Re-Run build_spatial_crop_params_arcpy.py'))
            missing_set_str=', '.join(str(s) for s in missing_set)
            logging.error(('Missing Crops: ' + missing_set_str))
            sys.exit()
            # return False  
            

        # DEADBEEF - This really shouldn't be hard coded here
        # Dictionary to convert shapefile field names to crop parameters

        param_field_dict = {
            'Name':      'name',
            'ClassNum':  'class_number',
            'IsAnnual':  'is_annual',
            'IrrigFlag': 'irrigation_flag',
            'IrrigDays': 'days_after_planting_irrigation',
            'Crop_FW':   'crop_fw',
            'WinterCov': 'winter_surface_cover_class',
            'CropKcMax': 'kc_max',
            'MAD_Init':  'mad_initial',
            'MAD_Mid':   'mad_midseason',
            'RootDepIni':'rooting_depth_initial',
            'RootDepMax':'rooting_depth_max',
            'EndRootGrw':'end_of_root_growth_fraction_time',
            'HeightInit':'height_initial',
            'HeightMax': 'height_max',
            'CurveNum':  'curve_number',
            'CurveName': 'curve_name',
            'CurveType': 'curve_type',
            'PL_GU_Flag':'flag_for_means_to_estimate_pl_or_gu',
            'T30_CGDD':  't30_for_pl_or_gu_or_cgdd',
            'PL_GU_Date':'date_of_pl_or_gu',
            'CGDD_Tbase':'tbase',
            'CGDD_EFC':  'cgdd_for_efc',
            'CGDD_Term': 'cgdd_for_termination',
            'Time_EFC':  'time_for_efc',
            'Time_Harv': 'time_for_harvest',
            'KillFrostC':'killing_frost_temperature',
            'InvokeStrs':'invoke_stress',
            'CN_Coarse': 'cn_coarse_soil',
            'CN_Medium': 'cn_medium_soil',
            'CN_Fine':   'cn_fine_soil'}
            
        # Cuttings values can also be updated spatially
        
        cutting_field_dict = {
            'Beef_Cut':  'beef_cuttings',
            'Dairy_Cur': 'dairy_cuttings'}

        # Crop parameter shapefiles are by crop,
        #   but parameters need to be separated first by ETCell
        # Process each crop parameter shapefile
        
        for crop_num, crop_dbf in sorted(crop_dbf_dict.items()):
            logging.debug('    {0:2d} {1}'.format(crop_num, crop_dbf))

            # Process using dbfread
            # crop_f = DBF(crop_dbf)
            # for record in crop_f:
            #     _id = record[cell_id_field]
            #      field_name, row_value in dict(record).items():

            # Process using shapefile/pyshp

            crop_f = shapefile.Reader(crop_dbf)
            crop_fields = [f[0] for f in crop_f.fields if f[0] != 'DeletionFlag']
            for record in crop_f.iterRecords():
                cell_id = record[crop_fields.index(cell_id_field)]

                # Skip cells

                if cell_id not in self.et_cells_dict.keys():
                    continue
                for field_name, row_value in zip(crop_fields, record):
                    # DEADBEEF - I really want to skip non-crop parameter fields
                    #   but also tell the user if a crop parameter field is missing

                    try:
                        param_name = param_field_dict[field_name]
                    except:
                        param_name = None
                    try:
                        cutting_name = cutting_field_dict[field_name]
                    except:
                        cutting_name = None
                    if param_name is not None:
                        try:
                            setattr(
                                self.et_cells_dict[cell_id].crop_params[crop_num],
                                param_name, float(row_value))
                        except:
                            logging.warning(
                                ('  The spatial crop parameter was not updated\n' +
                                 '    cell_id:    {0}\n    crop_num:   {1}\n' +
                                 '    field_name: {2}\n    parameter:  {3}').format(
                                 cell_id, crop_num, field_name, param_name))
                    elif cutting_name is not None:
                        try:
                            setattr(
                                self.et_cells_dict[cell_id],
                                cutting_name, float(row_value))
                        except:
                            logging.warning(
                                ('  The spatial cutting parameter was not updated\n' +
                                 '    cell_id:    {0}\n    crop_num:   {1}\n' +
                                 '    field_name: {2}\n    parameter:  {3}').format(
                                 cell_id, crop_num, field_name, cutting_name))
        return True

class ETCell():
    def __init__(self):
        """ """
        pass

    def __str__(self):
        """ """
        return '<ETCell {0}, {1} {2}>'.format(
            self.cell_id, self.cell_name, self.refet_id)

    def read_cell_properties_from_row(self, row, columns, elev_units = 'feet'):
        """ Parse row of data from ET Cells properties file

        Args:
            row (list): one row of ET Cells Properties
            start_column (int): first zero based row column

        Returns:
            True or False
        """
        # ET Cell id is cell id for crop and area et computations
        # Ref ET MET ID is met node id, aka ref et node id of met and ref et row
        
        if 'et cell id' in columns:
            self.cell_id = str(row[columns.index('et cell id')])
        else:
            logging.error('Unable to read ET Cell id')
            return False
        if 'et cell name' in columns:
            self.cell_name = row[columns.index('et cell name')]
        else:
            self.cell_name = self.cell_id
        if 'ref et id' in columns:
            self.refet_id = row[columns.index('ref et id')]
        else:
            logging.error('Unable to read reference et id')
            return False
        if 'latitude' in columns:
            self.latitude = float(row[columns.index('latitude')])
        else:
            logging.error('Unable to read latitude')
            return False
        if 'longitude' in columns:
            self.longitude = float(row[columns.index('longitude')])
        else:
            logging.error('Unable to read longitude')
            return False
        if 'elevation' in columns:
            self.elevation = float(row[columns.index('elevation')])
        else:
            logging.error('Unable to read elevation')
            return False
	if elev_units == 'feet' or elev_units == 'ft': self.elevation *= 0.3048
	
        # Compute air pressure of station/cell
        
        self.air_pressure = util.pair_from_elev(0.3048 * self.elevation)
        if 'area weighted average permeability' in columns:
            self.permeability = float(row[columns.index('area weighted average permeability')])
        else:
            logging.error('Unable to read area weighted average permeability')
            return False
        if 'area weighted average whc' in columns:
            self.stn_whc = float(row[columns.index('area weighted average whc')])
        else:
            logging.error('Unable to read area weighted average WHC')
            return False
        if 'average soil depth' in columns:
            self.stn_soildepth = float(row[columns.index('average soil depth')])
        else:
            logging.error('Unable to read average soil depth')
            return False
        if 'hydrologic group (a-c)' in columns:
            self.stn_hydrogroup_str = str(row[columns.index('hydrologic group (a-c)')])
        else:
            logging.error('Unable to read Hydrologic Group (A-C)')
            return False
        if 'hydrologic group (1-3)' in columns:
            self.stn_hydrogroup = int(row[columns.index('hydrologic group (1-3)')])
        else:
            logging.error('Unable to read Hydrologic Group (1-3)')
            return False
        if 'aridity rating' in columns:
            self.aridity_rating = float(row[columns.index('aridity rating')])
        else:
            logging.error('Unable to read elevation')
            return False
        """
        # Additional optional meta row
        # These items were in vb.net version to support previous vb6 versions.
        # Not yet used in python but could be useful for specifying
        # an alternative source of data.

        self.refet_row_path = None
        if 'refet row path' in columns:
            if not pd.isnull(row[columns.index('refet row path')]):
                if len(row[columns.index('refet row path')]) > 3:
                    self.refet_row_path = row[columns.index('refet row path')]
        self.source_refet_id = self.cell_id
        if 'source refet id' in columns:
            if not pd.isnull(row[columns.index('source refet id')]):
                if len(row[columns.index('source refet id')]) > 0:
                    self.source_refet_id = row[columns.index('source refet id')]
        """
        return True

    def init_crops_from_row(self, data, crop_numbers):
        """Parse row of data

        Code exists in kcb_daily to adjust cgdd_term using crop flag as a multiplier.
        This code is currently commented out and crop_flags are being read in as booleans.

        """
        self.irrigation_flag = int(data[3])
        self.crop_flags = dict(zip(crop_numbers, data[4:].astype(bool)))
        # self.crop_flags = dict(zip(crop_numbers, data[4:]))
        self.ncrops = len(self.crop_flags)

    def set_input_timeseries(self, cell_count, data, cells):
        """Wrapper for setting all refet/weather/climate data
        Args:
            cell_count: count of et cell being processed
            data: configuration data from INI file
            cells: ET cells data (dict)

        Returns:
            success: True or False
        """
        if not self.set_refet_data(data, cells): return False
        if data.refet_ratios_path:
            self.set_refet_ratio_data(data)
        if not self.set_weather_data(cell_count, data, cells): return False
        if data.phenology_option > 0:
            if not self.set_historic_temps(cell_count, data, cells): return False

        # Process climate arrays

        self.process_climate(data)
        return True

    def set_refet_data(self, data, cells):
        """Read ETo/ETr data file for single station

        Args:
            cell_count: count of et cell being processed
            data: configuration data from INI file
            cells: ET cells data (dict)

        Returns:
            success: True or False
        """
        logging.debug('\nRead ETo/ETr data')

        logging.debug('Read meteorological/climate data')
        if data.refet['data_structure_type'].upper() == 'SF P':
            success = self.SF_P_refet_data(data)
        else:
            success = self.DMI_refet_data(data, cells)
        if not success:
            logging.error('Unable to read reference ET data.')
            return False
        
        # Check/modify units
        
        for field_key, field_units in data.refet['units'].items():
            if field_units is None:
                continue
            elif field_units.lower() in ['mm', 'mm/day', 'mm/d']:
                continue
            elif field_units.lower() == 'in*100':
                self.refet_df[field_key] *= 0.254
            elif field_units.lower() == 'in':
                self.refet_df[field_key] *= 25.4
            elif field_units.lower() == 'inches/day':
                self.refet_df[field_key] *= 25.4
            elif field_units.lower() == 'in/day':
                self.refet_df[field_key] *= 25.4
            elif field_units.lower() == 'm':
                self.refet_df[field_key] *= 1000.0
            elif field_units.lower() in ['m/d', 'm/day']:
                if field_key == 'wind':
                    self.refet_df[field_key] /= 86400
                else:
                    self.refet_df[field_key] *= 1000.0
            elif field_units.lower() in ['mpd', 'miles/d', 'miles/day']:
                self.refet_df[field_key] /= mpdToMps
            else:
                logging.error('\n ERROR: Unknown {0} units {1}'.format(
                    field_key, field_units))

        # set date attributes
        
        self.refet_df['doy'] = [int(ts.strftime('%j')) for ts in self.refet_df.index]
        return True

    def SF_P_refet_data(self, data):
        """Read meteorological/climate data for single station with all parameters

        Args:
            data: configuration data from INI file

        Returns:
            success: True or False
        """
        refet_path = os.path.join(data.refet['ws'], data.refet['name_format'] % self.refet_id)
        logging.debug('  {0}'.format(refet_path))

        # Get list of 0 based line numbers to skip
        # Ignore header but assume header was set as a 1's based index
        skiprows = [i for i in range(data.refet['header_lines'])
                    if i + 1 != data.refet['names_line']]
        try:
            self.refet_df = pd.read_table(
                refet_path, engine = 'python', header = data.refet['names_line']- len(skiprows)  - 1,
                skiprows = skiprows, delimiter = data.refet['delimiter'])
        except IOError:
            logging.error(('  IOError: RefET data file could not be read ' +
                           'and may not exist\n  {}').format(refet_path))
            sys.exit()
        except:
            logging.error(('  Unknown error reading RefET data ' +
                           'file\n {}').format(refet_path))
            sys.exit()
        logging.debug('  Columns: {}'.format(', '.join(list(self.refet_df.columns))))

        # Check that fields exist in data table
        
        for field_key, field_name in data.refet['fields'].items():
            if (field_name is not None and
                    field_name not in self.refet_df.columns):
                logging.error(
                    ('\n  ERROR: Field "{0}" was not found in {1}\n' +
                     '    Check{2}_field value inINI file').format(
                    field_name, os.path.basename(temps_path), field_key))
                sys.exit()
                
            # Rename dataframe fields
            
            self.refet_df = self.refet_df.rename(columns = {field_name:field_key})

        # Convert date strings to datetimes
        
        if data.refet['fields']['date'] is not None:
            self.refet_df['date'] = pd.to_datetime(self.refet_df['date'])
        else:
            self.refet_df['date'] = self.refet_df[['year', 'month', 'day']].apply(
                lambda s : datetime.datetime(*s),axis = 1)
        self.refet_df.set_index('date', inplace = True)

        # truncate period
        
        try:
            self.refet_df = self.refet_df.truncate(before = data.start_dt, after = data.end_dt)
        except:
            logging.error('\nERROR: ' + str(sys.exc_info()[0]) + 'occurred truncating weather data')
            return False
        if len(self.refet_df.index) < 1:
            logging.error('No data found reading ret data')
            return False
        return True

    def DMI_refet_data(self, data):
        """Read reference ET for single station using specified DMI format

        Args:
            data: configuration data from INI file

        Returns:
            success: True or False
        """
        self.refet_df = None
        if '%p' in data.refet['name_format']:
            refet_path = os.path.join(data.refet['ws'], data.refet['name_format'].replace('%p', data.refet['fnspec']))
        else:
            refet_path = os.path.join(data.refet['ws'], data.refet['name_format'])
        if not os.path.isfile(refet_path):
            logging.error('ERROR:  Reference ET data path {0} does not exist'.format(refet_path))
            return False
        logging.debug('  Reference ET path is {0}'.format(refet_path))
        if data.refet['data_structure_type'].upper() == 'PF S.P':
            if data.refet['file_type'].lower() == 'csf':
                param_df = mod_dmis.ReadOneColumnSlot(
                    refet_path, data.refet['header_lines'], data.refet['names_line'],
                    self.refet_id, data.refet['fields']['etref'], data.refet['units']['etref'], 1.0,
                    'day', 1, data.refet['delimiter'], data.start_dt, data.end_dt)
            elif data.refet['file_type'].lower() == 'rdb':
                param_df = mod_dmis.ReadOneTextRDB(
                    refet_path, data.refet['header_lines'], data.refet['names_line'],
                    self.refet_id, data.refet['fields']['etref'], data.refet['units']['etref'], 1.0,
                    'day', 1, data.refet['delimiter'], data.start_dt, data.end_dt)
            elif data.refet['file_type'].lower() == 'xls' or data.refet['file_type'].lower() == 'wb':
                param_df = mod_dmis.ReadOneExcelColumn(
                    refet_path, data.refet['wsspec'], data.refet['header_lines'], data.refet['names_line'],
                    self.refet_id, data.refet['fields']['etref'], data.refet['units']['etref'], 1.0,
                    'day', 1, data.start_dt, data.end_dt)
        else:
            logging.error('ERROR:  File type {} is not supported'.format(data.refet['file_type']))
            return False
        if param_df is None:
            logging.error('ERROR:  unable to read {}'.format(refet_path))
            return False
        else:
            self.refet_df = mod_dmis.make_ts_dataframe('day', 1, data.start_dt, data.end_dt)
            self.refet_df['etref'] = param_df[[0]].values
        return True

    def set_refet_ratio_data(self, data):
        """Read ETo/ETr ratios static file

        Args:
            data: configuration data from INI file

        """
        logging.info('  Reading ETo/ETr ratios')
        try:
            if ".xls" in data.refet_ratios_path.lower():
                refet_ratios_df = pd.read_excel(data.refet_ratios_path, sheetname = data.eto_ratios_ws,
                        header = None, skiprows = data.eto_ratios_header_lines - 1, na_values = ['NaN'])
            else:
                refet_ratios_df = pd.read_table(data.refet_ratios_path, delimiter = data.eto_ratios_delimiter,
                        header = 'infer', skiprows = data.eto_ratios_header_lines - 1, na_values = ['NaN'])
                # print(refet_ratios_df)
                # print(refet_ratios_df[data.eto_ratios_name_field])
                # print(data.eto_ratios_name_field)
            del refet_ratios_df[data.eto_ratios_name_field]
        except IOError:
            logging.error(
                ('  IOError: ETo ratios static file could not be ' +
                 'read and may not exist\n  {}').format(data.refet_ratios_path))
            sys.exit()
        except:
            logging.error(('  Unknown error reading ETo ratios static ' +
                           'file\n {}').format(data.refet_ratios_path))
            sys.exit()

        # Remove duplicates
        # If there are duplicate station IDs, for now only use first instance
        # Eventually allow users to tie station IDs to cells
        
        if refet_ratios_df.duplicated(subset = data.eto_ratios_id_field).any():
            logging.warning(
                '  There are duplicate station IDs in ETo Ratios file\n' 
                '  Only the first instance of station ID will be applied')
            refet_ratios_df.drop_duplicates(subset = data.eto_ratios_id_field, inplace = True)

        # Flatten/flip data so that ratio values are in one column
        
        refet_ratios_df = pd.melt(
            refet_ratios_df, id_vars=[data.eto_ratios_id_field],
            var_name = data.eto_ratios_month_field, value_name = data.eto_ratios_ratio_field)
        refet_ratios_df[data.eto_ratios_ratio_field] = refet_ratios_df[data.eto_ratios_ratio_field].astype(np.float)
        
        # Set any missing values to 1.0
        
        refet_ratios_df.fillna(value=1.0, inplace=True)

        # Convert month abbreviations to numbers
        
        refet_ratios_df[data.eto_ratios_month_field] = [
            datetime.datetime.strptime(m, '%b').month
            for m in refet_ratios_df[data.eto_ratios_month_field]]
        # print(refet_ratios_df)
        # Filter to current station
        
        refet_ratios_df = refet_ratios_df[
           refet_ratios_df[data.eto_ratios_id_field] == self.refet_id]
        if refet_ratios_df.empty:
            logging.warning('  Empty table, ETo/ETr ratios not applied')
            return False

        # Set month as index
        
        refet_ratios_df.set_index(data.eto_ratios_month_field, inplace=True)
        logging.info(refet_ratios_df)

        # Scale ETo/ETr values
        #WHY 'Month' vs 'month' change needed? Input climate files have Year, Month, Day.
        self.refet_df = self.refet_df.join(refet_ratios_df, 'Month')

        self.refet_df['etref'] *= self.refet_df[data.eto_ratios_ratio_field]
        del self.refet_df[data.eto_ratios_ratio_field]
        del self.refet_df[data.eto_ratios_month_field]
        del self.refet_df[data.eto_ratios_id_field]
        return True

    def set_weather_data(self, cell_count, data, cells):
        """Read meteorological/climate data for single station and fill missing values

        Args:
            cell_count: count of et cell being processed
            data: configuration data from INI file
            cells: ET cells data (dict)

        Returns:
            success: True or False
        """
        logging.debug('Read meteorological/climate data')
        if data.weather['data_structure_type'].upper() == 'SF P':
            success = self.SF_P_weather_data(data)
        else:
            success = self.DMI_weather_data(cell_count, data, cells)
        if not success:
            logging.error('Unable to read and fill daily metereorological data.')
            return False
        
        # Check/modify units
        
        for field_key, field_units in data.weather['units'].items():
            if field_units is None:
                continue
            elif field_units.lower() in ['c', 'mm', 'mm/day', 'm/s', 'mps', 'mj/m2', 'mj/m^2', 'kg/kg']:
                continue
            elif field_units.lower() == 'k':
                self.weather_df[field_key] -= 273.15
            elif field_units.lower() == 'f':
                self.weather_df[field_key] -= 32
                self.weather_df[field_key] /= 1.8
            elif field_units.lower() == 'in*100':
                self.weather_df[field_key] *= 0.254
            elif field_units.lower() == 'in':
                self.weather_df[field_key] *= 25.4
            elif field_units.lower() == 'inches/day':
                self.weather_df[field_key] *= 25.4
            elif field_units.lower() == 'in/day':
                self.weather_df[field_key] *= 25.4
            elif field_units.lower() == 'm':
                self.weather_df[field_key] *= 1000.0
            elif field_units.lower() in ['m/d', 'm/day']:
                if field_key == 'wind':
                    self.weather_df[field_key] /= 86400
                else:
                    self.weather_df[field_key] *= 1000.0
            elif field_units.lower() == 'meter':
                self.weather_df[field_key] *= 1000.0
            elif field_units.lower() in ['mpd', 'miles/d', 'miles/day']:
                self.weather_df[field_key] /= mpdToMps
            else:
                logging.error('\n ERROR: Unknown {0} units {1}'.format(field_key, field_units))

        # set date attributes
        
        self.weather_df['doy'] = [int(ts.strftime('%j')) for ts in self.weather_df.index]

        # Scale wind height to 2m if necessary
        
        if data.weather['wind_height'] != 2:
            self.weather_df['wind'] *= (4.87 / np.log(67.8 * data.weather['wind_height'] - 5.42))

        # Add snow and snow_depth if necessary
        
        if 'snow' not in self.weather_df.columns:
            self.weather_df['snow'] = 0
        if 'snow_depth' not in self.weather_df.columns:
            self.weather_df['snow_depth'] = 0

        # Calculate Tdew from specific humidity
        # Convert station elevation from feet to meters
        
        if ('tdew' not in self.weather_df.columns and
                'q' in self.weather_df.columns):
            self.weather_df['tdew'] = util.tdew_from_ea(util.ea_from_q(
                self.air_pressure, self.weather_df['q'].values))

        # Compute RH from Tdew and Tmax
        
        if ('rh_min' not in self.weather_df.columns and
                'tdew' in self.weather_df.columns and
                'tmax' in self.weather_df.columns):
                
            # For now do not consider SVP over ice
            # (it was not used in ETr or ETo computations, anyway)
            
            self.weather_df['rh_min'] = 100 * np.clip(
                util.es_from_t(self.weather_df['tdew'].values) /
                util.es_from_t(self.weather_df['tmax'].values), 0, 1)

        # DEADBEEF
        # Don't default CO2 correction values to 1 if they aren't in the data
        # CO2 corrections must be in the weather file
        # Is this going for work for all BOR data sets?

        """
        # Set CO2 correction values to 1 if they are not in data

        if 'co2_grass' not in self.weather_df.columns:
            logging.info('  Grass CO2 factor not in weather data, setting co2_grass = 1')
            self.weather_df['co2_grass'] = 1
        if 'co2_tree' not in self.weather_df.columns:
            logging.info('  Tree CO2 factor not in weather data, setting co2_trees = 1')
            self.weather_df['co2_trees'] = 1
        if 'co2_c4' not in self.weather_df.columns:
            logging.info('  C4 CO2 factor not in weather data, setting co2_c4 = 1')
            self.weather_df['co2_c4'] = 1
        """
        return True

    def SF_P_weather_data(self, data):
        """Read meteorological/climate data for single station with all parameters

        Args:
            data: configuration data from INI file

        Returns:
            success: True or False
        """
        weather_path = os.path.join(data.weather['ws'], data.weather['name_format'] % self.refet_id)
        logging.debug('  {0}'.format(weather_path))

        # Get list of 0 based line numbers to skip
        # Ignore header but assume header was set as 1's based index
        skiprows = [i for i in range(data.weather['header_lines'])
                    if i+1 != data.weather['names_line']]
        try:
            self.weather_df = pd.read_table(weather_path, engine = 'python', 
                    header = data.weather['names_line'] - len(skiprows) - 1,
                    skiprows = skiprows, delimiter = data.weather['delimiter'])
        except IOError:
            logging.error(('  IOError: Weather data file could not be read ' +
                           'and may not exist\n  {}').format(weather_path))
            return False
            # sys.exit()
        except:
            logging.error(('  Unknown error reading Weather data ' +
                           'file\n {}').format(weather_path))
            return False
            # sys.exit()
        logging.debug('  Columns: {0}'.format(
            ', '.join(list(self.weather_df.columns))))

        # Check fields
        
        for field_key, field_name in data.weather['fields'].items():
            if (field_name is not None and
                    field_name not in self.weather_df.columns):
                if data.weather['fnspec'][field_key].lower() == 'estimated':
                    continue
                elif data.weather['fnspec'][field_key].lower() == 'unused':
                    continue
                logging.error(
                    ('\n  ERROR: Field "{0}" was not found in {1}\n' +
                     '    Check{2}_field value inINI file').format(
                    field_name, os.path.basename(weather_path), field_key))
                return False
            # Rename dataframe field
            
            self.weather_df = self.weather_df.rename(columns = {field_name:field_key})

        # Convert date strings to datetimes
        
        if data.weather['fields']['date'] is not None:
            self.weather_df['date'] = pd.to_datetime(self.weather_df['date'])
        else:
            self.weather_df['date'] = self.weather_df[['year', 'month', 'day']].apply(
                lambda s : datetime.datetime(*s),axis = 1)
        self.weather_df.set_index('date', inplace = True)

        # truncate period
        
        try:
            self.weather_df = self.weather_df.truncate(before = data.start_dt, after = data.end_dt)
        except:
            logging.error('\nERROR: ' + str(sys.exc_info()[0]) + 'occurred truncating weather data')
            return False
        if len(self.weather_df.index) < 1:
            logging.error('No data found reading weather data')
            return False
        return True

    def DMI_weather_data(self, cell_count, data, cells):
        """Read meteorological/climate data for single station using specified DMI format

        Args:
            cell_count: count of et cell being processed
            data: configuration data from INI file

        Returns:
            success: True or False
        """

        # Read data from files by fields

        self.weather_df = None
        input_buffer = None
        field_count = 0
        for field_key, field_name in data.weather['fields'].items():
            if field_name is None or field_name.lower() == 'date': continue
            if field_name.lower() == 'year' or field_name.lower() == 'month': continue
            if field_name.lower() == 'day' or field_name.lower() == 'doy': continue
            if data.weather['fnspec'][field_key].lower() == 'estimated': continue
            if data.weather['fnspec'][field_key].lower() == 'unused': continue

            # pull data for field_name

            if cell_count == 1:
                last_path = ''
                if '%p' in data.weather['name_format']:
                    weather_path = os.path.join(data.weather['ws'], 
                        data.weather['name_format'].replace('%p', data.weather['fnspec'][field_key]))
                else:
                    weather_path = os.path.join(data.weather['ws'], data.weather['name_format'])
                if not os.path.isfile(weather_path):
                    logging.error('ERROR:  Weather data path for {0} is {1} does not exist'.format(field_key, weather_path))
                    return False
                logging.debug('  Weather data path for {0} is {1}'.format(field_key, weather_path))
                if data.weather['data_structure_type'].upper() == 'PF S.P':
                    if data.weather['file_type'].lower() == 'csf':
                        param_df = mod_dmis.ColumnSlotToDataframe(weather_path, data.weather['header_lines'],
                            data.weather['names_line'], 'day', 1,
                            data.weather['delimiter'], data.start_dt, data.end_dt)
                    elif data.weather['file_type'].lower() == 'rdb':
                        param_df = mod_dmis.TextRDBToDataframe(weather_path, data.weather['header_lines'],
                            data.weather['names_line'], 'day', 1,
                            data.weather['delimiter'], data.start_dt, data.end_dt)
                    elif data.weather['file_type'].lower() == 'xls' or data.weather['file_type'].lower() == 'wb':
                        # TODO weather_buffer Isn't Used; input_buffer no defined
                        if '%p' in data.weather['name_format'] or field_count == 1:
                            weather_buffer = pd.ExcelFile(weather_path)
                        param_df = mod_dmis.ExcelWorksheetToDataframe(input_buffer, 
                            data.weather['wsspec'][field_key],
                            data.weather['header_lines'], data.weather['names_line'],
                            time_step='day', ts_quantity=1,
                            start_dt=data.start_dt, end_dt=data.end_dt)
                    else:
                        logging.error('ERROR:  File type {} is not supported'.format(data.weather['file_type']))
                        return False
                    if param_df is None:
                        logging.error('ERROR:  unable to read {}'.format(weather_path))
                        return False
                    else:
                        if data.start_dt is None:
                            pydt = param_df.index[0]
                            data.start_dt = pd.to_datetime(datetime.datetime(pydt.year, pydt.month, pydt.day, pydt.hour, pydt.minute))
                        if data.end_dt is None: 
                            pydt = param_df.index[len(param_df) - 1]
                            data.end_date = pd.to_datetime(datetime.datetime(pydt.year, pydt.month, pydt.day, pydt.hour, pydt.minute))
                        param_df = mod_dmis.ReduceDataframeToParameter(param_df, field_name)
                        cells.et_cells_weather_data[field_key] = param_df
                    del param_df
        del input_buffer

        # pull et cell's data from parameter data frames
        
        self.weather_df = mod_dmis.make_ts_dataframe('day', 1, data.start_dt, data.end_dt)
        for field_key, param_df in cells.et_cells_weather_data.items():
            self.weather_df[field_key] = mod_dmis.ReadOneDataframeColumn(param_df, self.refet_id, 
                    data.weather['fields'][field_key], data.weather['units'][field_key], 1,
                    'day', 1,
                    data.start_dt, data.end_dt).values
        return True

    def set_historic_temps(self, cell_count, data, cells):
        """Read historic max and min temperatures to support historic phenology

        Args:
            cell_count: count of et cell being processed
            data: configuration data from INI file
            cells: ET cells data (dict)

        Returns:
            success: True or False
        """
        logging.debug('Read historic temperature data')
        if data.hist_temps['data_structure_type'].upper() == 'SF P':
            success = self.SF_P_historic_temps(data)
        else:
            success = self.DMI_historic_temps(cell_count, data, cells)
        if not success:
            logging.error('Unable to read historic temperture data.')
            return False
        
        # Check/modify units
        
        for field_key, field_units in data.hist_temps['units'].items():
            if field_units is None:
                continue
            elif field_units.lower() == 'c':
                continue
            elif field_units.lower() == 'k':
                self.hist_temps_df[field_key] -= 273.15
            elif field_units.lower() == 'f':
                self.hist_temps_df[field_key] -= 32
                self.hist_temps_df[field_key] /= 1.8
            else:
                logging.error('\n ERROR: Unknown {0} units {1}'.format(
                    field_key, field_units))

        # set date attributes
        
        self.hist_temps_df['doy'] = [int(ts.strftime('%j')) for ts in self.hist_temps_df.index]
        return True

    def SF_P_historic_temps(self, data):
        """Read meteorological/climate data for single station with all parameters

        Args:
            data: configuration data from INI file

        Returns:
            success: True or False
        """
        historic_path = os.path.join(data.hist_temps['ws'], data.hist_temps['name_format'] % self.refet_id)
        logging.debug('  {0}'.format(historic_path))

        # Get list of 0 based line numbers to skip
        # Ignore header but assume header was set as 1's based index
        skiprows = [i for i in range(data.hist_temps['header_lines'])
                    if i+1 != data.hist_temps['names_line']]
        try:
            self.hist_temps_df = pd.read_table(historic_path, engine = 'python', 
                    header = data.hist_temps['names_line'] - len(skiprows) - 1,
                    skiprows = skiprows, delimiter = data.hist_temps['delimiter'])
        except IOError:
            logging.error(('  IOError: historic data file could not be read ' +
                           'and may not exist\n  {}').format(historic_path))
            return False
        except:
            logging.error(('  Unknown error reading historic data ' +
                           'file\n {}').format(historic_path))
            return False
        logging.debug('  Columns: {0}'.format(
            ', '.join(list(self.hist_temps_df.columns))))

        # Check fields
        
        for field_key, field_name in data.hist_temps['fields'].items():
            if (field_name is not None and
                    field_name not in self.hist_temps_df.columns):
                logging.error(
                    ('\n  ERROR: Field "{0}" was not found in {1}\n' +
                     '    Check{2}_field value in INI file').format(
                    field_name, os.path.basename(historic_path), field_key))
                sys.exit()
                
            # Rename dataframe fields
            
            self.hist_temps_df = self.hist_temps_df.rename(columns = {field_name:field_key})

        # Convert date strings to datetimes
        
        if data.hist_temps['fields']['date'] is not None:
            self.hist_temps_df['date'] = pd.to_datetime(self.hist_temps_df['date'])
        else:
            self.hist_temps_df['date'] = self.hist_temps_df[['year', 'month', 'day']].apply(
                lambda s : datetime.datetime(*s),axis = 1)
        self.hist_temps_df.set_index('date', inplace = True)

        # truncate period
        
        try:
            self.hist_temps_df = self.hist_temps_df.truncate(before = data.start_dt, after = data.end_dt)
        except:
            logging.error('\nERROR: ' + str(sys.exc_info()[0]) + 'occurred truncating historic data')
            return False
        if len(self.hist_temps_df.index) < 1:
            logging.error('No data found reading historic temperature data')
            return False
        return True

    def DMI_historic_temps(self, cell_count, data, cells):
        """Read meteorological/climate data for single station using specified DMI format

        Args:
            cell_count: count of et cell being processed
            data: configuration data from INI file

        Returns:
            success: True or False
        """

        # Read data from files by fields

        self.hist_temps_df = None
        input_buffer = None
        field_count = 0
        for field_key, field_name in data.hist_temps['fields'].items():
            if field_name is None or field_name.lower() == 'date': continue
            if field_name.lower() == 'year' or field_name.lower() == 'month': continue
            if field_name.lower() == 'day' or field_name.lower() == 'doy': continue
            if data.hist_temps['fnspec'][field_key].lower() == 'estimated': continue
            if data.hist_temps['fnspec'][field_key].lower() == 'unused': continue

            # pull data for field_name

            if cell_count == 1:
                last_path = ''
                if '%p' in data.hist_temps['name_format']:
                    historic_path = os.path.join(data.hist_temps['ws'], 
                    data.hist_temps['name_format'].replace('%p', data.hist_temps['fnspec'][field_key]))
                else:
                    historic_path = os.path.join(data.hist_temps['ws'], data.hist_temps['name_format'])
                if not os.path.isfile(historic_path):
                    logging.error('ERROR:  historic data path for {0} is {1} does not exist'.format(field_key, historic_path))
                    return False
                logging.debug('  historic data path for {0} is {1}'.format(field_key, historic_path))
                # TODO Use keyword function calls
                if data.hist_temps['data_structure_type'].upper() == 'PF S.P':
                    if data.hist_temps['file_type'].lower() == 'csf':
                        param_df = mod_dmis.ColumnSlotToDataframe(historic_path, data.hist_temps['header_lines'],
                                data.hist_temps['names_line'], 'day', 1, 
                                data.hist_temps['delimiter'], data.start_dt, data.end_dt)
                    elif data.hist_temps['file_type'].lower() == 'rdb':
                        param_df = mod_dmis.TextRDBToDataframe(historic_path, data.hist_temps['header_lines'], 

                                data.hist_temps['names_line'], 'day', 1, 
                                data.hist_temps['delimiter'], data.start_dt, data.end_dt)
                    elif data.hist_temps['file_type'].lower() == 'xls' or data.hist_temps['file_type'].lower() == 'wb':
                        if '%p' in data.hist_temps['name_format'] or field_count == 1:
                            #TODO What are historic_buffer and last_path used for
                            historic_buffer = pd.ExcelFile(historic_path)
                        last_path = historic_path
                        param_df = mod_dmis.ExcelWorksheetToDataframe(input_buffer, 
                                data.hist_temps['wsspec'][field_key], 
                                data.hist_temps['header_lines'], data.hist_temps['names_line'],
                                'day', 1, data.start_dt, data.end_dt)
                    else:
                        logging.error('ERROR:  File type {} is not supported'.format(data.hist_temps['file_type']))
                        return False
                    if param_df is None:
                        logging.error('ERROR:  unable to read {}'.format(historic_path))
                        return False
                    else:
                        if data.start_dt is None:
                            pydt = param_df.index[0]
                            data.start_dt = pd.to_datetime(datetime.datetime(pydt.year, pydt.month, pydt.day, pydt.hour, pydt.minute))
                        if data.end_dt is None: 
                            pydt = param_df.index[len(param_df) - 1]
                            data.end_date = pd.to_datetime(datetime.datetime(pydt.year, pydt.month, pydt.day, pydt.hour, pydt.minute))
                        param_df = mod_dmis.ReduceDataframeToParameter(param_df, field_name)
                        cells.et_cells_historic_data[field_key] = param_df
                    del param_df
        del input_buffer

        # pull et cell's data from parameter data frames
        
        self.hist_temps_df = mod_dmis.make_ts_dataframe('day', 1, data.start_dt, data.end_dt)
        for field_key, param_df in cells.et_cells_historic_data.items():
            self.hist_temps_df[field_key] = mod_dmis.ReadOneDataframeColumn(param_df, self.refet_id, 
                    data.hist_temps['fields'][field_key], data.hist_temps['units'][field_key], 1,
                    'day', 1, 
                    data.start_dt, data.end_dt).values
        return True

    def process_climate(self, data):
        """
        Compute long term averages (DAY LOOP)
            adjust and check temperature data
            process alternative TMax and TMin
        Fill missing data with long term doy average (DAY LOOP)
            Calculate an estimated depth of snow on ground using simple melt rate function))
            compute main cumGDD for period of record for various bases for constraining earliest/latest planting or GU
            only Tbase = 0 needs to be evaluated (used to est. GU for alfalfa, mint, hops)
        compute long term mean cumGDD0 from sums (JDOY LOOP)
        Time series data have reversed field names support historic (constant) phenology
        maxt, mint, meant, 30T are historic equivalents of tmax, tmin, meant, t30
        Cumulative variables use 'hist' in lieu of 'main'

        Args:
            data (dict): data from INI file

        Returns:
            success: True or False
        """
        
        # Initialize climate dataframe

        self.climate_df = self.weather_df[['doy', 'ppt', 'tmax', 'tmin', 'tdew', 'wind', 'rh_min', 'snow', 'snow_depth']].copy()
        
        # Extend to support historic (constant) phenology
        
        if data.phenology_option > 0:
	    self.climate_df['maxt'] = self.hist_temps_df['maxt'].values
	    self.climate_df['mint'] = self.hist_temps_df['mint'].values
	    del self.hist_temps_df
	else:
	    self.climate_df['maxt'] = self.weather_df['tmax'].values
	    self.climate_df['mint'] = self.weather_df['tmin'].values
        del self.weather_df
        
        # pick up reference et

	self.climate_df['etref'] = self.refet_df['etref'].values
	
        # Adjust T's downward if station is arid
        
        if self.aridity_rating > 0:
            # Interpolate value for aridity adjustment
            
            aridity_adj = [0., 0., 0., 0., 1., 1.5, 2., 3.5, 4.5, 3., 0., 0., 0.]
            month = np.array([dt.month for dt in self.climate_df.index])
            day = np.array([dt.day for dt in self.climate_df.index])
            moa_frac = np.clip((month + (day - 15) / 30.4), 1, 11)
            arid_adj = np.interp(moa_frac, range(len(aridity_adj)), aridity_adj)
            arid_adj *= self.aridity_rating / 100.
            self.climate_df['tmax'] -= arid_adj
            self.climate_df['tmin'] -= arid_adj
            self.climate_df['maxt'] -= arid_adj
            self.climate_df['mint'] -= arid_adj
            del month, day, arid_adj

        # T30 stuff - done after temperature adjustments
        
        self.climate_df['tmean'] = self.climate_df[["tmax", "tmin"]].mean(axis=1)
        self.climate_df['meant'] = self.climate_df[["maxt", "mint"]].mean(axis=1)
        # self.climate_df['t30'] = pd.rolling_mean(self.climate_df['tmean'], window = 30, min_periods = 1)
        self.climate_df['t30'] = self.climate_df['tmean'].rolling(window = 30, min_periods=1).mean()
        # self.climate_df['30t'] = pd.rolling_mean(self.climate_df['meant'], window = 30, min_periods = 1)
        self.climate_df['30t'] = self.climate_df['meant'].rolling(window = 30, min_periods=1).mean()

        # Accumulate T30 over period of record
        
        main_t30_lt = np.array(
            self.climate_df[['t30', 'doy']].groupby('doy').mean()['t30'])
        hist_t30_lt = np.array(
            self.climate_df[['30t', 'doy']].groupby('doy').mean()['30t'])

        # Compute GDD for each day
        
        self.climate_df['main_cgdd'] = self.climate_df['tmean']
        self.climate_df.ix[self.climate_df['tmean'] <= 0, 'main_cgdd'] = 0
        self.climate_df['hist_cgdd'] = self.climate_df['meant']
        self.climate_df.ix[self.climate_df['tmean'] <= 0, 'hist_cgdd'] = 0

        # Compute cumulative GDD for each year
        
        self.climate_df['main_cgdd'] = self.climate_df[['doy', 'main_cgdd']].groupby(
            self.climate_df.index.map(lambda x: x.year)).main_cgdd.cumsum()
        self.climate_df['hist_cgdd'] = self.climate_df[['doy', 'hist_cgdd']].groupby(
            self.climate_df.index.map(lambda x: x.year)).hist_cgdd.cumsum()

        # Compute mean cumulative GDD for each DOY

        main_cgdd_0_lt = np.array(
            self.climate_df[['main_cgdd', 'doy']].groupby('doy').mean()['main_cgdd'])
        hist_cgdd_0_lt = np.array(
            self.climate_df[['hist_cgdd', 'doy']].groupby('doy').mean()['hist_cgdd'])

        # Revert from indexing by I to indexing by DOY (for now)
        # Copy DOY 1 value into DOY 0

        main_t30_lt = np.insert(main_t30_lt, 0, main_t30_lt[0])
        main_cgdd_0_lt = np.insert(main_cgdd_0_lt, 0, main_cgdd_0_lt[0])
        hist_t30_lt = np.insert(hist_t30_lt, 0, hist_t30_lt[0])
        hist_cgdd_0_lt = np.insert(hist_cgdd_0_lt, 0, hist_cgdd_0_lt[0])

        self.climate = {}
        self.climate['main_t30_lt'] = main_t30_lt
        self.climate['main_cgdd_0_lt'] = main_cgdd_0_lt
        self.climate['hist_t30_lt'] = hist_t30_lt
        self.climate['hist_cgdd_0_lt'] = hist_cgdd_0_lt

        # Calculate an estimated depth of snow on ground using simple melt rate function))

        if np.any(self.climate_df['snow']):
            for i, doy in self.climate_df['doy'].iteritems():
                # Calculate an estimated depth of snow on ground using simple melt rate function
                
                snow = self.climate_df['snow'][i]
                snow_depth = self.climate_df['snow_depth'][i]
                
                # Assume settle rate of 2 to 1
                
                snow_accum += snow * 0.5  # assume a settle rate of 2 to 1
                
                # 4 mm/day melt per degree C
                
                snow_melt = max(4 * self.climate_df['tmax'][i], 0.0)
                snow_accum = max(snow_accum - snow_melt, 0.0)
                snow_depth = min(snow_depth, snow_accum)
                self.climate_df['snow_depth'][i] = snow_depth
        return True

if __name__ == '__main__':
    pass
