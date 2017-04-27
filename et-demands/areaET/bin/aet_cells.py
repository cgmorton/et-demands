#!/usr/bin/env python

import datetime
import logging
import math
import os
import sys

import numpy as np
import pandas as pd
import xlrd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../lib')))
import aet_config
import aet_utils
import mod_dmis

mmHaPerDay_to_cms = 0.001 * 10000 / 86400    # 0.001 (mm/m) * 10000 (m2/hectare) / 86400 (seconds/day)

class AETCellsData():
    """Functions for loading ET Cell data fromstatic text files"""
    def __init__(self):
        """ """
        self.et_cells_data = dict()
        self.crop_num_list = []
        self.cell_daily_output_aet_data = {}
        self.cell_monthly_output_aet_data = {}
        self.cell_annual_output_aet_data = {}

    def set_cell_crops(self, cfg):
        """ExtractET cell crop data

        Args:
            cfg: configuration data from INI file

        Returns:
            None
        """
        logging.info('\nSetting cell crop types by ET cell')
        if ".xls" in cfg.cell_crops_path.lower():
            self.read_cell_crops_xls_xlrd(cfg)
        else:
            self.read_cell_crops_txt(cfg)

    def read_cell_crops_txt(self, cfg):
        """ExtractET cell crop data from text file

        Args:
            cfg: configuration data from INI file

        Returns:
            None
        """
        a = np.loadtxt(cfg.cell_crops_path, delimiter = cfg.cell_crops_delimiter, dtype = 'str')
        crop_type_numbers = a[cfg.cell_crops_names_line - 1, 4:].astype(int)
        crop_type_names = a[cfg.cell_crops_names_line, 4:]
        for ctCount in range(0, len(crop_type_names), 1):
            crop_type_names[ctCount] = str(crop_type_names[ctCount]).replace('"', '').split("-")[0].strip()
        a = a[cfg.cell_crops_header_lines:]
        for row_index, row in enumerate(a):
            cell = ETCell()
            cell.init_crops_from_row(row, crop_type_numbers)
            cell.crop_type_numbers = crop_type_numbers
            cell.crop_type_names = crop_type_names
            self.et_cells_data[cell.cell_id] = cell

    def read_cell_crops_xls_xlrd(self, cfg):
        """ExtractET cell crop data from Excel using xlrd

        Args:
            cfg: configuration data from INI file

        Returns:
            None
        """
        wb = xlrd.open_workbook(cfg.cell_crops_path)
        ws = wb.sheet_by_name(cfg.cell_crops_ws)
        num_crops = int(ws.cell_value(cfg.cell_crops_names_line - 1, 1))
        crop_type_names = []
        crop_type_numbers = []
        for col_index in range(4, num_crops + 4):
            crop_type_number = int(ws.cell_value(cfg.cell_crops_names_line - 1, col_index))
            crop_type_numbers.append(crop_type_number)
            crop_type_name = str(ws.cell_value(cfg.cell_crops_names_line, col_index)).replace('"', '').split("-")[0].strip()
            crop_type_names.append(crop_type_name)
        crop_type_numbers = np.asarray(crop_type_numbers)
        crop_type_names = np.asarray(crop_type_names)
        for row_index in range(cfg.cell_crops_header_lines, ws.nrows):
            row = np.asarray(ws.row_values(row_index), dtype = np.str)
            for col_index in range(3, num_crops + 4):
                row[col_index] = row[col_index].replace(".0", "")
            cell = ETCell()
            cell.init_crops_from_row(row, crop_type_numbers)
            cell.crop_type_numbers = crop_type_numbers
            cell.crop_type_names = crop_type_names
            self.et_cells_data[cell.cell_id] = cell

class ETCell():
    def __init__(self):
        """ """

    def __str__(self):
        """ """
        return '<ETCell {0}, {1}>'.format(self.cell_id, self.cell_name)

    def init_crops_from_row(self, row, crop_numbers):
        """Parse row of et cell data

        Args:
            row: row of data being processed
            cfg: configuration data from INI file
            crop_number: list of crop numbers
        """
        self.cell_id = row[0]
        self.cell_name = row[1]
        self.cell_irr_flag = row[3].astype(int)
        self.crop_type_flags = dict(zip(crop_numbers, row[4:].astype(bool)))
        self.numberCropTypes = len(self.crop_type_flags)

    def crop_types_cycle(self, cell_count, cfg, cells):
        """Read crop types data for et cell and compute some output

        Args:
            cell_count: count of ET cellbeing processed
            cfg: configuration data from INI file
            cells: ET cell data (dict)

        Returns:
            success: True or False
        """
        try:
            # parse used crop types

            self.usedCropTypes = []
            self.numUsedCropTypes = 0
            for ctCount in range(0, self.numberCropTypes, 1):
                if self.crop_type_flags[ctCount + 1]:
                    self.usedCropTypes.append(ctCount + 1)
                    self.numUsedCropTypes += 1
            logging.debug('Reading crop ET data')
            if cfg.input_cet['data_structure_type'].upper() == 'DRI':
                success = self.DRI_input_cet_data(cell_count, cfg, cells)
            else:
                success = self.RDB_input_cet_data(cell_count, cfg, cells)
            if not success:
                return False
            if cfg.ngs_toggle == 1:
                if not self.dist_ngs_to_gs(cfg): return False
            return True
        except:
            logging.error('\nERROR: ' + str(sys.exc_info()[0]) + 'occurred processing ET Cell crop type data for ' +  self.cell_id)
            return False

    def DRI_input_cet_data(self, cell_count, cfg, cells):
        """Read crop ET data for single station in DRI station files with all parameters

        Args:
            cell_count: count of et cell id being processed
            cfg: configuration data from INI file
            cells: ET cell data (dict)

        Returns:
            success: True or False
        """
        crops_dict = {}
        try:
            # Get list of 0 based line numbers to skip
            # Ignore header but assume header was set as 1's based index
            data_skip = [i for i in range(cfg.input_cet['header_lines']) if i + 1 <> cfg.input_cet['names_line']]
            for ctCount in range(0, self.numUsedCropTypes, 1):
                input_cet_path = os.path.join(cfg.input_cet['ws'], cfg.input_cet['name_format'].replace('%c', '%02d' % self.usedCropTypes[ctCount]) % self.cell_id)
                if not os.path.isfile(input_cet_path):
                    logging.error('ERROR:  input crop et file {} does not exist'.format(input_cet_path))
                    return False
                logging.debug('  {0}'.format(input_cet_path))
                crop_df = pd.read_table(input_cet_path, engine = 'python',
                        header = cfg.input_cet['names_line'] - len(data_skip) - 1, 
                        skiprows = data_skip, sep = cfg.input_cet['delimiter'], 
                        comment = "#", na_values = ['NaN'])

                # Check fields

                for field_key, field_name in cfg.input_cet['fields'].items():
                    if (field_name is not None and field_name not in crop_df.columns):
                        if cfg.input_cet['fnspec'][field_key].lower() == 'estimated': continue
                        if cfg.input_cet['fnspec'][field_key].lower() == 'unused': continue
                        logging.error(
                            ('\n  ERROR: Field "{0}" was not found in {1}\n'+
                             '    Check {2}_field value in INI file').format(
                            field_name, os.path.basename(input_cet_path), field_key))
                        return False
                    # Rename dataframe fields
                    if field_name is not None: crop_df = crop_df.rename(columns = {field_name:field_key})
                crop_df['niwr'] = crop_df['cir'].values

                # Convert date strings to datetimes and index on date
        
                if cfg.input_cet['fields']['date'] is not None:
                    crop_df['date'] = pd.to_datetime(crop_df['date'])
                else:
                    if cfg.time_step == 'day':
                        crop_df['date'] = crop_df[['year', 'month', 'day']].apply(
                            lambda s : datetime.datetime(*s),axis = 1)
                    else:
                        crop_df['date'] = crop_df[['year', 'month', 'day', 'hour']].apply(
                        lambda s : datetime.datetime(*s),axis = 1)
                crop_df.set_index('date', inplace = True)
                if cell_count == 0 and ctCount == 0:
                    # verify period
        
                    if cfg.start_dt is None:
                        pydt = crop_df.index[0]
                        cfg.start_dt = pd.to_datetime(datetime.datetime(pydt.year, pydt.month, pydt.day, pydt.hour, pydt.minute))
                    if cfg.end_dt is None: 
                        pydt = crop_df.index[len(crop_df) - 1]
                        cfg.end_dt = pd.to_datetime(datetime.datetime(pydt.year, pydt.month, pydt.day, pydt.hour, pydt.minute))
            
                # truncate period
        
                try:
                    crop_df = crop_df.truncate(before = cfg.start_dt, after = cfg.end_dt)
                except:
                    logging.error('\nERROR: ' + str(sys.exc_info()[0]) + 'occurred truncating input crop ET data')
                    return False
                if len(crop_df.index) < 1:
                    logging.error('No values found reading crop et data')
                    return False

                # compute seasonally adjusted crop et, effective precipitation and irrigation water requirement
                
                try:
                    crop_df['cet'], crop_df['effprcp'], crop_df['cir'] = seasonal_ctetdata(cfg.ngs_toggle, 
                        cfg.crop_irr_flags[self.usedCropTypes[ctCount] - 1], crop_df['season'], crop_df['etact'], 
                        crop_df['etpot'], crop_df['ppt'], crop_df['sro'], crop_df['dperc'], crop_df['sir'], crop_df['niwr'])
                except:
                    logging.error('\n  ERROR: ' + str(sys.exc_info()[0]) +  ' occurred computing seasonally adjusted crop type et data for ' +  self.cell_id + ' from DRI format\n')
                    return False
                
                if ctCount == 0:
                    # store ET Cell reference ET and precip if first crop

                    self.etcData_df = mod_dmis.make_ts_dataframe(cfg.time_step, cfg.ts_quantity, cfg.start_dt, cfg.end_dt)
                    self.etcData_df['refet'] = crop_df['refet']
                    self.etcData_df['ppt'] = crop_df['ppt']
                
                # drop unused columns               

                for fn in list(crop_df.columns):
                    if fn not in ['date', 'year', 'cet', 'effprcp', 'cir', 'season']:
                        crop_df.drop(fn, axis = 1, inplace = True)
                        
                # add crop number column
                
                crop_df['Crop Num'] = self.usedCropTypes[ctCount]
                crop_df.reset_index(inplace = True)
                crops_dict[self.usedCropTypes[ctCount]] = crop_df
                del crop_df
            self.crops_df = pd.concat(crops_dict)
            self.crops_df.set_index(['Crop Num', 'date'], inplace = True)
            return True
        except:
            logging.error('\n  ERROR: ' + str(sys.exc_info()[0]) +  ' occurred processing ET Cell crop type data for ' +  self.cell_id + ' from DRI format\n')
            return False

    def RDB_input_cet_data(self, cell_count, cfg, cells):
        """Read crop ET data for single ET cell using RDB format

        Args:
            cell_count: count of ET cell being processed
            cfg: configuration data from INI file
            cells: ET cell data (dict)

        Returns:
            success: True or False
        """
        crops_dict = {}
        try:
            # Get list of 0 based line numbers to skip
            # Ignore header but assume header was set as 1's based index
            data_skip = [i for i in range(cfg.input_cet['header_lines']) if i + 1 <> cfg.input_cet['names_line']]
            input_cet_path = os.path.join(cfg.input_cet['ws'], cfg.input_cet['name_format'].replace('%s', self.cell_id)).replace("%c", "")
            if not os.path.isfile(input_cet_path):
                logging.error('ERROR:  input crop et file {} does not exist'.format(input_cet_path))
                return False
            logging.debug('  {0}'.format(input_cet_path))
            """
                crop_df = pd.read_table(input_cet_path, engine = 'python',
                        header = cfg.input_cet['names_line'] - len(data_skip) - 1, 
                        skiprows = data_skip, sep = cfg.input_cet['delimiter'], 
                        comment = "#", na_values = ['NaN'])
            """
            rdb_cet_df = pd.read_table(input_cet_path, engine = 'python',
                    header = cfg.input_cet['names_line'] - len(data_skip) - 1, 
                    skiprows = data_skip, sep = cfg.input_cet['delimiter'], 
                    comment = "#", na_values = ['NaN'])
            crop_num_col = list(rdb_cet_df.columns)[0]
            rdb_cet_df[crop_num_col] = rdb_cet_df[[crop_num_col]].apply(lambda s: int(*s), axis = 1, raw = True, reduce = True)

            # Check fields

            for field_key, field_name in cfg.input_cet['fields'].items():
                if (field_name is not None and field_name not in rdb_cet_df.columns):
                    if cfg.input_cet['fnspec'][field_key].lower() == 'estimated': continue
                    if cfg.input_cet['fnspec'][field_key].lower() == 'unused': continue
                    logging.error(('\n  ERROR: Field "{0}" was not found in {1}\n' + 
                             '    Check {2}_field value in INI file').format(field_name, 
                             os.path.basename(input_cet_path), field_key))
                    return False
                # Rename dataframe fields
                if field_name is not None: rdb_cet_df = rdb_cet_df.rename(columns = {field_name:field_key})
            rdb_cet_df['niwr'] = rdb_cet_df['cir'].values

            # Convert date strings to datetimes and index on date
        
            if cfg.input_cet['fields']['date'] is not None:
                rdb_cet_df['date'] = pd.to_datetime(rdb_cet_df['date'])
            else:
                if cfg.time_step == 'day':
                    rdb_cet_df['date'] = rdb_cet_df[['year', 'month', 'day']].apply(
                        lambda s : datetime.datetime(*s),axis = 1)
                else:
                    rdb_cet_df['date'] = rdb_cet_df[['year', 'month', 'day', 'hour']].apply(
                    lambda s : datetime.datetime(*s),axis = 1)
            for ctCount in range(0, self.numUsedCropTypes, 1):
                try:
                    crop_df = rdb_cet_df[rdb_cet_df[crop_num_col] == self.usedCropTypes[ctCount]]
                except:
                    logging.error('\nERROR: ' + str(sys.exc_info()[0]) + 'occurred subsetting crop type ', crop_type, '.\n')
                crop_df.reset_index(inplace = True)
                crop_df.set_index('date', inplace = True)
                
                # sub set data for this crop
                
                if cell_count == 0 and ctCount == 0:
                    # verify period
        
                    if cfg.start_dt is None:
                        pydt = crop_df.index[0]
                        sdt = datetime.datetime(pydt.year, pydt.month, pydt.day, pydt.hour, pydt.minute)
                        cfg.start_dt = pd.to_datetime(sdt)
                    if cfg.end_dt is None: 
                        pydt = crop_df.index[len(crop_df) - 1]
                        edt = datetime.datetime(pydt.year, pydt.month, pydt.day, pydt.hour, pydt.minute)
                        cfg.end_dt = pd.to_datetime(edt)
            
                # truncate period
        
                try:
                    crop_df = crop_df.truncate(before = cfg.start_dt, after = cfg.end_dt)
                except:
                    logging.error('\nERROR: ' + str(sys.exc_info()[0]) + 'occurred truncating input crop ET data')
                    return False

                # compute seasonally adjusted crop et, effective precipitation and irrigation water requirement
                
                try:
                    crop_df['cet'], crop_df['effprcp'], crop_df['cir'] = seasonal_ctetdata(cfg.ngs_toggle, 
                        cfg.crop_irr_flags[self.usedCropTypes[ctCount] - 1], crop_df['season'], crop_df['etact'], 
                        crop_df['etpot'], crop_df['ppt'], crop_df['sro'], crop_df['dperc'], crop_df['sir'], crop_df['niwr'])
                except:
                    logging.error('\n  ERROR: ' + str(sys.exc_info()[0]) +  ' occurred computing seasonally adjusted crop type et data for ' +  self.cell_id + ' from RDB format\n')
                    return False
                
                if ctCount == 0:
                    # store ET Cell reference ET and precip if first crop

                    self.etcData_df = mod_dmis.make_ts_dataframe(cfg.time_step, cfg.ts_quantity, cfg.start_dt, cfg.end_dt)
                    self.etcData_df['refet'] = crop_df['refet']
                    self.etcData_df['ppt'] = crop_df['ppt']
                
                # drop unused columns               

                for fn in list(crop_df.columns):
                    if fn not in ['date', 'year', 'cet', 'effprcp', 'cir', 'season']:
                        crop_df.drop(fn, axis = 1, inplace = True)
                        
                # add crop number column
                
                crop_df['Crop Num'] = self.usedCropTypes[ctCount]
                crop_df.reset_index(inplace = True)
                crops_dict[self.usedCropTypes[ctCount]] = crop_df
                del crop_df
            del rdb_cet_df
            self.crops_df = pd.concat(crops_dict)
            self.crops_df.set_index(['Crop Num', 'date'], inplace = True)
            return True
        except:
            logging.error('\n  ERROR: ' + str(sys.exc_info()[0]) +  ' occurred processing ET Cell crop type data for ' +  self.cell_id + ' from RDB format\n')
            return False

    def dist_ngs_to_gs(self, cfg):
        """Redistribute et's and cir's to growing season

        Args:
            cfg: configuration data from INI file

        Returns:
            success: True or False
        """
        crops_dict = {}
        try:
            for ctCount in range(0, self.numUsedCropTypes, 1):
                unAdjCrop_df = self.crops_df.xs(self.usedCropTypes[ctCount], level = 0, drop_level = False)
                unAdjCrop_df.reset_index(inplace = True)
                unAdjCrop_df.set_index('date', inplace = True)
                adjCrop_df = mod_dmis.make_ts_dataframe(cfg.time_step, cfg.ts_quantity, cfg.start_dt, cfg.end_dt)
                adjCrop_df['season'] = np.nan
                adjCrop_df['cet'] = np.nan
                adjCrop_df['effprcp'] = np.nan
                adjCrop_df['cir'] = np.nan
                gsSD = cfg.start_dt
                ngsSD = cfg.start_dt
                gsED = cfg.end_dt
                ngsED = cfg.end_dt
                gsET = 0.0
                ngsET = 0.0
                gsCIR = 0.0
                ngsCIR = 0.0
                prev_dt = cfg.start_dt
                for dt, uac in unAdjCrop_df.iterrows():
                    adjCrop_df.at[dt, 'season'] = uac['season']
                    if dt > prev_dt:
                        if uac['season'] == 1 and unAdjCrop_df.at[prev_dt, 'season'] == 0:
                            gsSD = dt
                            ngsED = prev_dt
                        if uac['season'] == 0 and unAdjCrop_df.at[prev_dt, 'season'] == 1:
                            # next non growing season

                            gsED = prev_dt

                            # set non growing season values to 0.0
    
                            for tdt in mod_dmis.make_dt_index(cfg.time_step, cfg.ts_quantity, ngsSD, ngsED):
                                adjCrop_df.at[tdt, 'cir'] = 0.0
                                adjCrop_df.at[tdt, 'cet'] = 0.0
                                adjCrop_df.at[tdt, 'effprcp'] = 0.0

                            # redistribute non growing season totals to growing season

                            gDays = gsED.to_julian_date() - gsSD.to_julian_date()
                            if gDays > 0:
                                cirAdj = ngsCIR / gDays
                                etAdj = ngsET / gDays
                                for tdt in mod_dmis.make_dt_index(cfg.time_step, cfg.ts_quantity, gsSD, gsED):
                                    adjCrop_df.at[tdt, 'cir'] = unAdjCrop_df.at[tdt, 'cir'] + cirAdj
                                    adjCrop_df.at[tdt, 'cet'] = unAdjCrop_df.at[tdt, 'cet'] + etAdj
                                    adjCrop_df.at[tdt, 'effprcp'] = adjCrop_df.at[tdt, 'cet'] - adjCrop_df.at[tdt, 'cir']
                            ngsSD = dt
                            ngsED = cfg.end_dt
                            ngsCIR = 0.0
                            ngsET = 0.0
                            gsCIR = 0.0
                            gsET = 0.0
                        if uac['season'] == 1:
                            gsCIR = gsCIR + uac['cir']
                            gsET = gsET + uac['cet']
                        else:
                            ngsCIR = ngsCIR + uac['cir']
                            ngsET = ngsET + uac['cet']
                    prev_dt = dt

                # deal with last season

                if unAdjCrop_df.at[cfg.end_dt, 'season'] == 1:
                    gsED = dt
                    gsCIR = gsCIR + unAdjCrop_df.at[gsED, 'cir']
                    gsET = gsET + unAdjCrop_df.at[gsED, 'cet']
                    gDays = gsED.to_julian_date() - gsSD.to_julian_date()
                    if gDays > 0:
                        cirAdj = ngsCIR / gDays
                        etAdj = ngsET / gDays
                        for tdt in mod_dmis.make_dt_index(cfg.time_step, cfg.ts_quantity, gsSD, gsED):
                            adjCrop_df.at[tdt, 'cir'] = unAdjCrop_df.at[tdt, 'cir'] + cirAdj
                            adjCrop_df.at[tdt, 'cet'] = unAdjCrop_df.at[tdt, 'cet'] + etAdj
                            adjCrop_df.at[tdt, 'effprcp'] = adjCrop_df.at[tdt, 'cet'] - adjCrop_df.at[tdt, 'cir']
                else:
                    ngsED = dt
                    for tdt in mod_dmis.make_dt_index(cfg.time_step, cfg.ts_quantity, ngsSD, ngsED):
                        adjCrop_df.at[tdt, 'cir'] = 0.0
                        adjCrop_df.at[tdt, 'cet'] = 0.0
                        adjCrop_df.at[tdt, 'effprcp'] = 0.0
                del unAdjCrop_df
                # if self.usedCropTypes[ctCount] == 3: adjCrop_df.to_csv(path_or_buf = "crop3.csv", sep = ",")

                # add crop number column
                
                adjCrop_df['Crop Num'] = self.usedCropTypes[ctCount]
                adjCrop_df.reset_index(inplace = True)
                crops_dict[self.usedCropTypes[ctCount]] = adjCrop_df
                del adjCrop_df
            del self.crops_df
            self.crops_df = pd.concat(crops_dict)
            self.crops_df.set_index(['Crop Num', 'date'], inplace = True)
            return True
        except:
            if adjCrop_df is not None:
                adjCrop_df.to_csv(path_or_buf = "adjcrop" + str(self.usedCropTypes[ctCount]) + ".csv", sep = ",")
            logging.error('\n  ERROR: ' + str(sys.exc_info()[0]) +  ' occurred redistributing ngs to gs ET Cell crop type data for ' +  self.cell_id + ' from DRI format\n')
            return False

    def read_cell_crop_mix(self, cfg):
        """Read annual acres, cropping percentages, and crop information for an ET Cell

        Args:
            cfg: configuration data from INI file

        Returns:
            success: True or False
        """
        
        # set up some stuff
        
        try: # verify file existence and opening
            # Get list of 0 based line numbers to skip
            # Ignore header but assume header was set as 1's based index
            data_skip = [i for i in range(cfg.ccm_header_lines) if i + 1 <> cfg.ccm_names_line]
            if '.xls' in cfg.cell_mix_path.lower(): 
                input_df = pd.read_excel(cfg.cell_mix_path, sheetname = cfg.cell_mix_ws, 
                        header = cfg.ccm_names_line - len(data_skip) - 1, 
                        skiprows = data_skip, na_values = ['NaN'])
            else:
                input_df = pd.read_table(cfg.cell_mix_path, engine = 'python', 
                        header = cfg.ccm_names_line - len(data_skip) - 1, 
                        skiprows = data_skip, sep = cfg.ccm_delimiter)
            input_df.rename(columns = {input_df.columns[1]:'ETCellID'}, inplace = True) 
            input_df['ETCellID'] = input_df[[input_df.columns[1]]].apply(lambda s: str(*s), axis = 1, raw = True, reduce = True)
            input_df = input_df.query('ETCellID == @self.cell_id').copy().reset_index(drop = True)
            input_df.drop(['ETCellID'], axis = 1, inplace = True)
            if cfg.ccm_ts_type == 1: 
                # constant crop mix - copy 9999 year to other years

                if input_df.columns[0].lower() == 'year':
                    if input_df.columns[0] == 'Year':
                        input_df.rename(columns = {'Year':'year'}, inplace = True) 
                    input_df['year'] = input_df[['year']].apply(lambda s: int(*s), axis = 1, raw = True, reduce = True)
                # input_df.drop(input_df.columns[0], axis = 1, inplace = True)
                y9999_df = input_df.copy()
                del input_df
                num_crop_rows = len(y9999_df.index)
                year_to_use = cfg.start_dt.year - 1
                for yCount in range(0, cfg.number_years):
                    year_to_use += 1
                    year_df = y9999_df.copy()
                    year_df['year'] = year_to_use
                    if yCount == 0:
                        input_df = year_df.copy()
                    else:
                        input_df = pd.concat([input_df, year_df])
                    del year_df
                del y9999_df
                input_df.reset_index(drop = True, inplace = True)
            else:
                # variable crop mix - set up year column
                if input_df.columns[0].lower() == 'year':
                    if input_df.columns[0] == 'Year':
                        input_df.rename(columns = {'Year':'year'}, inplace = True) 
                    input_df['year'] = input_df[['year']].apply(lambda s: int(*s), axis = 1, raw = True, reduce = True)
                else:
                    # convert dates to years
                    
                    input_df['year'] = pd.to_datetime(self.input_met_df['Date']).year
                    input_df.drop('Date', axis = 1, inplace = True)

                # verify crop mix years for user's period
                
                if input_df['year'][0] > cfg.start_dt.year:
                    logging.warning("First year is after start year in crop mix for " + self.cell_id + ".")
                    return False
                if input_df['year'][len(input_df.index) - 1] < cfg.end_dt.year:
                    logging.warning("First year is before end year in crop mix for " + self.cell_id + ".")
                    return False

                # truncate for user's period
                
                input_df = input_df[input_df['year'] >= cfg.start_dt.year]
                if input_df is None:
                    logging.warning("Incomplete period in crop mix for " + self.cell_id + ".")
                    return False
                input_df = input_df[input_df['year'] <= cfg.end_dt.year]
                if input_df is None:
                    logging.warning("Incomplete period in crop mix for " + self.cell_id + ".")
                    return False
            input_df[input_df.columns[4]] = input_df[[input_df.columns[4]]].apply(lambda s: str(*s), axis = 1, raw = True, reduce = True)
            input_df[input_df.columns[5]] = input_df[[input_df.columns[5]]].apply(lambda s: str(*s), axis = 1, raw = True, reduce = True)
            input_df[input_df.columns[6]] = input_df[[input_df.columns[6]]].apply(lambda s: str(*s), axis = 1, raw = True, reduce = True)
            input_df[input_df.columns[7]] = input_df[[input_df.columns[7]]].apply(lambda s: str(*s), axis = 1, raw = True, reduce = True)
            input_df['UserBegDate'] = input_df[['year', input_df.columns[4], input_df.columns[5]]].apply(lambda s : user_begin_date(*s),axis = 1)
            input_df['UserEndDate'] = input_df[['year', input_df.columns[6], input_df.columns[7]]].apply(lambda s : user_end_date(*s),axis = 1)
            input_df[input_df.columns[1]] = input_df[[input_df.columns[1]]].apply(lambda s: str(*s), axis = 1, raw = True, reduce = True)
            input_df.rename(columns = {input_df.columns[1]:'UserCropName'}, inplace = True)
            input_df.rename(columns = {input_df.columns[3]:'CropNumber'}, inplace = True)
            input_df['CropNumber'] = input_df[['CropNumber']].apply(lambda s: int(*s), axis = 1, raw = True, reduce = True)
            self.user_crops_list = pd.unique(input_df[input_df.columns[1]].values).tolist()
            try:
                self.user_crops_list.remove('Total')
            except:
                try:
                    self.user_crops_list.remove('total')
                except:
                    try:
                        self.user_crops_list.remove('TOTAL')
                    except: pass
            
            # process annual total data
            
            self.ann_crops_df = input_df[input_df['UserCropName'] == 'Total'].copy().reset_index(drop = True)
            ann_crops_columns = list(self.ann_crops_df.columns)
            self.ann_crops_df.drop(ann_crops_columns[1], axis = 1, inplace = True)
            self.ann_crops_df = self.ann_crops_df.rename(columns = {ann_crops_columns[2]:'area'})
            self.ann_crops_df.drop(ann_crops_columns[3], axis = 1, inplace = True)

            # drop unused columns

            for fn in list(self.ann_crops_df.columns):
                if fn not in ['year', 'area', 'UserBegDate', 'UserEndDate', 'CropCount']:
                    self.ann_crops_df.drop(fn, axis = 1, inplace = True)
            
            # get rid of 'Total' row in crop mix
            
            self.ann_crops_df.set_index('year', inplace = True)
            input_df = input_df[input_df['UserCropName'] <> 'Total'].copy().reset_index(drop = True)

            # parse crop data for user's run period

            year_to_use = cfg.start_dt.year - 1
            for yCount in range(0, cfg.number_years):
                year_to_use += 1
                year_df = input_df[input_df['year'] == year_to_use].copy().reset_index(drop = True)
                year_df[year_df.columns[2]] = year_df[[year_df.columns[2]]].apply(lambda s: float(*s), axis = 1, raw = True, reduce = True)
                
                # set crop percents
                
                year_df['CropPercents'] = crop_percents(cfg.ccm_mix_type, self.ann_crops_df['area'][year_to_use], year_df[year_df.columns[2]])

                # drop unused columns

                for fn in list(year_df.columns):
                    if fn not in ['year', 'UserCropName', 'CropNumber', 'CropPercents', 'UserBegDate', 'UserEndDate']:
                        year_df.drop(fn, axis = 1, inplace = True)
                ubd = datetime.datetime(year_to_use, 1, 1)
                ued = datetime.datetime(year_to_use, 12, 31)
                        
                # check for missing crops
                
                year_crops = year_df['UserCropName'].values.tolist()
                for crop in self.user_crops_list:
                    if crop not in year_crops:
                        year_df.loc[len(year_df.index)] = [year_to_use, crop, 1, ubd, ued, 0.0]
                if yCount == 0:
                    self.crops_mix_df = year_df.copy()
                else:
                    self.crops_mix_df = pd.concat([self.crops_mix_df, year_df])
                del year_df
            del input_df
            self.crops_mix_df.reset_index(drop = True, inplace = True)
            
            # convert area units from acre to hectare if needed
            
            if cfg.area_units_type == 1:
                self.ann_crops_df['area'] *= 0.40468564224
            return True
        except:
            logging.error('\n  ERROR: ' + str(sys.exc_info()[0]) + " found reading cropping data for " + self.cell_id + ".")
            return False

    def compute_area_requirements(self, cell_count, cfg, cells):
        """ compute area requirements as rates, flows, or proportions

        Args:
            cell_count: count of ET cellbeing processed
            cfg: configuration data from INI file
            cells: ET cell data (dict)

        Returns:
            success: True or False
        """
        try:    # read crop types data
            # initialize all object variables to zero

            self.etcData_df['et'] = np.zeros((cfg.number_days), dtype = float)
            self.etcData_df['nir'] = np.zeros((cfg.number_days), dtype = float)
            self.etcData_df['effprcp'] = np.zeros((cfg.number_days), dtype = float)
            self.etcData_df['season'] = np.zeros((cfg.number_days), dtype = int)
            self.etcCropIRs_df = mod_dmis.make_ts_dataframe(cfg.time_step, cfg.ts_quantity, cfg.start_dt, cfg.end_dt)
            self.etcCropETs_df = mod_dmis.make_ts_dataframe(cfg.time_step, cfg.ts_quantity, cfg.start_dt, cfg.end_dt)
            
            # loop thru ET Cell's (user) crops

            for cCount in range(0, len(self.user_crops_list)):
                logging.debug ("Computing weighted irrigation requirements for " + self.cell_id +  " crop " + self.user_crops_list[cCount])
                cet_col_name = self.cell_id + "." + self.user_crops_list[cCount] + " " + cfg.output_cet['fields']['cet']
                self.etcCropETs_df[cet_col_name] = np.zeros((cfg.number_days), dtype = float)
                cir_col_name = self.cell_id + "." + self.user_crops_list[cCount] + " " + cfg.output_cir['fields']['cir']
                self.etcCropIRs_df[cir_col_name] = np.zeros((cfg.number_days), dtype = float)
                try:
                    crop_mix_df = self.crops_mix_df[self.crops_mix_df['UserCropName'] == self.user_crops_list[cCount]]
                except: continue
                crop_mix_df.set_index('year', inplace = True, drop = True)
                ct_index = self.crop_type_index(crop_mix_df['CropNumber'][cfg.start_dt.year])

                # set up crop by crop and weighted output
                
                if ct_index > -1:
                    # pick up crop cir's and et's and compute straight ET Cell cir's, et's and eff precip for current year

                    ct_df = self.crops_df.xs(crop_mix_df['CropNumber'][cfg.start_dt.year], level = 0, drop_level = False)
                    ct_df.reset_index(inplace = True)
                    ct_df.set_index('date', inplace = True)
                    
                    # following loop is really really slow; unclear how to speed it up

                    for dt, ctdata in ct_df.iterrows():
                        year_to_use = dt.year
                        if aet_utils.date_is_between(dt, self.ann_crops_df['UserBegDate'][year_to_use], \
                                                  self.ann_crops_df['UserEndDate'][year_to_use]):
                            self.etcCropETs_df.at[dt, cet_col_name] = ctdata['cet']
                            self.etcData_df.at[dt, 'et'] = self.etcData_df.at[dt, 'et'] \
                                + ctdata['cet'] * crop_mix_df['CropPercents'][year_to_use] * 0.001
                            if aet_utils.date_is_between(dt, crop_mix_df['UserBegDate'][year_to_use], \
                                    crop_mix_df['UserEndDate'][year_to_use]):
                                self.etcData_df.at[dt, 'effprcp'] = self.etcData_df.at[dt, 'effprcp'] \
                                    + ctdata['effprcp']  * crop_mix_df['CropPercents'][year_to_use] * 0.001
                                self.etcData_df.at[dt, 'season'] = 1
                                self.etcCropIRs_df.at[dt, cir_col_name] = ctdata['cir']
                    del ct_df
                del crop_mix_df
                
            # apply no negative ir's to crop by crop ir's if toggled
            
            # cfg.neg_nirs_toggle = 2    # debug
            if cfg.neg_nirs_toggle == 2 or cfg.neg_nirs_toggle == 3:
                adj_daily_df = mod_dmis.make_ts_dataframe(cfg.time_step, cfg.ts_quantity, cfg.start_dt, cfg.end_dt)
                col_names = list(self.etcCropIRs_df.columns)
            
                # compute non negative values and set up aggregations
            
                aggregation_func = {}
                for col_name in col_names:
                    adj_daily_df[col_name] = np.maximum(self.etcCropIRs_df[col_name].values, 0.0)
                    aggregation_func.update({col_name: np.sum})

                # compute annual sums

                unadj_ann_df = self.etcCropIRs_df.resample('AS').apply( aggregation_func)
                adj_ann_df = adj_daily_df.resample('AS').apply( aggregation_func)
                del aggregation_func
                
                # compute annual ratios for retaining annual totals

                ann_adj_ratios_df = pd.DataFrame(index = adj_ann_df.index)
                for col_name in col_names:
                    ann_adj_ratios_df['adj'] = adj_ann_df[col_name].values
                    ann_adj_ratios_df['unadj'] = unadj_ann_df[col_name].values
                    ann_adj_ratios_df[col_name] = ann_adj_ratios_df[['adj', 'unadj']].apply(lambda s : calculate_ratios(*s),axis = 1)
                    
                # apply annual ratios to retain annual totals

                del self.etcCropIRs_df
                self.etcCropIRs_df = mod_dmis.make_ts_dataframe(cfg.time_step, cfg.ts_quantity, cfg.start_dt, cfg.end_dt)
                for col_name in col_names:
                    self.etcCropIRs_df[col_name] = apply_annual_ratios(cfg.start_dt, adj_daily_df.index, adj_daily_df[col_name].values, ann_adj_ratios_df[col_name].values)
                    self.etcCropIRs_df[col_name] = np.maximum(self.etcCropIRs_df[col_name].values, 0.0)
                del adj_daily_df, unadj_ann_df, adj_ann_df, ann_adj_ratios_df
            
            # set up and/or post requested crop by crop output
            
            if cfg.output_cet_flag:
                if not self.setup_output_cet_data(cell_count, cfg, cells): return False
            else:
                del self.etcCropETs_df
            if cfg.output_cir_flag:
                if not self.setup_output_cir_data(cell_count, cfg, cells): return False
            else:
                del self.etcCropIRs_df

            # compute running average weighted et for smoothing if toggled
            
            # cfg.et_smoothing_days = 20    # debug
            if cfg.et_smoothing_days > 1:
                # compute running averages
                
                daily_df = mod_dmis.make_ts_dataframe(cfg.time_step, cfg.ts_quantity, cfg.start_dt, cfg.end_dt)
                daily_df['straight'] = self.etcData_df['et']
                daily_df['smoothed'] = pd.rolling_mean(daily_df['straight'], window = cfg.et_smoothing_days, center = True, min_periods = 1)
                
                # compute annual sums

                aggregation_func = {}
                for col_name in list(daily_df.columns):
                    aggregation_func.update({col_name: np.sum})
                annual_df = daily_df.resample('AS').apply( aggregation_func)
                del aggregation_func
                
                # compute annual ratios
                
                annual_df['ratios'] = annual_df[['straight', 'smoothed']].apply(lambda s : calculate_ratios(*s),axis = 1)
                
                # apply ratios
                
                """
                # following verified that annual sums are resepected
                
                daily_df['et'] = apply_annual_ratios(cfg.start_dt, daily_df.index, daily_df['smoothed'].values, annual_df['ratios'].values)
                aggregation_func.update({'et': np.sum})
                del annual_df
                annual_df = daily_df.resample('AS').apply( aggregation_func)
                del aggregation_func
                # print "annual df\n", annual_df.head(5)
                self.etcData_df['et'] = daily_df['et'].values
                """
                self.etcData_df['et'] = apply_annual_ratios(cfg.start_dt, daily_df.index, daily_df['smoothed'].values, annual_df['ratios'].values)
                del daily_df, annual_df
            
            # compute ET cell net irrigation requirement

            for dt, dailydata in self.etcData_df.iterrows():
                year_to_use = dt.year
                if (aet_utils.date_is_between(dt, self.ann_crops_df['UserBegDate'][year_to_use], \
                        self.ann_crops_df['UserEndDate'][year_to_use]) and dailydata['season'] == 1):
                    self.etcData_df.at[dt, 'nir'] = dailydata['et'] - dailydata['effprcp']
                else:
                    self.etcData_df.at[dt, 'effprcp'] = 0.0

            # apply no negative ir's to weighted ir's if toggled
            
            # cfg.neg_nirs_toggle = 1    # debug
            if cfg.neg_nirs_toggle == 1 or cfg.neg_nirs_toggle == 3:
                daily_df = mod_dmis.make_ts_dataframe(cfg.time_step, cfg.ts_quantity, cfg.start_dt, cfg.end_dt)
                daily_df['unadjusted'] = self.etcData_df['nir']
                daily_df['adjusted'] = np.maximum(daily_df['unadjusted'].values, 0.0)
                
                # compute annual sums

                aggregation_func = {}
                for col_name in list(daily_df.columns):
                    aggregation_func.update({col_name: np.sum})
                annual_df = daily_df.resample('AS').apply( aggregation_func)
                del aggregation_func
                
                # compute annual ratios
                
                annual_df['ratios'] = annual_df[['adjusted', 'unadjusted']].apply(lambda s : calculate_ratios(*s),axis = 1)
                
                # apply ratios
                
                self.etcData_df['nir'] = apply_annual_ratios(cfg.start_dt, daily_df.index, daily_df['adjusted'].values, annual_df['ratios'].values)
                self.etcData_df['nir'] = np.maximum(self.etcData_df['nir'].values, 0.0)
                del daily_df, annual_df

            # compute running average weighted ir for smoothing if toggled
            
            # cfg.nir_smoothing_days = 20    # debug
            if cfg.nir_smoothing_days > 1:
                # compute running averages
                
                daily_df = mod_dmis.make_ts_dataframe(cfg.time_step, cfg.ts_quantity, cfg.start_dt, cfg.end_dt)
                daily_df['straight'] = self.etcData_df['nir']
                daily_df['smoothed'] = pd.rolling_mean(daily_df['straight'], window = cfg.nir_smoothing_days, center = True, min_periods = 1)
                
                # compute annual sums

                aggregation_func = {}
                for col_name in list(daily_df.columns):
                    aggregation_func.update({col_name: np.sum})
                annual_df = daily_df.resample('AS').apply( aggregation_func)
                del aggregation_func
                
                # compute annual ratios
                
                annual_df['ratios'] = annual_df[['straight', 'smoothed']].apply(lambda s : calculate_ratios(*s),axis = 1)
                
                # apply ratios
                
                self.etcData_df['nir'] = apply_annual_ratios(cfg.start_dt, daily_df.index, daily_df['smoothed'].values, annual_df['ratios'].values)
                del daily_df, annual_df

            # compute nir disaggregation fractions

            daily_df = mod_dmis.make_ts_dataframe(cfg.time_step, cfg.ts_quantity, cfg.start_dt, cfg.end_dt)
            daily_df['nir'] = self.etcData_df['nir']
            aggregation_func = {}
            for col_name in list(daily_df.columns):
                aggregation_func.update({col_name: np.sum})
            monthly_df = daily_df.resample('MS').apply( aggregation_func)
            del aggregation_func
            self.etcData_df['nirfrac'] = compute_daily_fractions(cfg.start_dt, daily_df.index, daily_df['nir'].values, monthly_df['nir'].values)
            del daily_df, monthly_df
            
            # compute weighted et and ir as flow
            
            self.etcData_df['etflow'] = compute_flow(cfg.start_dt, self.etcData_df.index, self.etcData_df['et'].values, self.ann_crops_df['area'].values)
            self.etcData_df['nirflow'] = compute_flow(cfg.start_dt, self.etcData_df.index, self.etcData_df['nir'].values, self.ann_crops_df['area'].values)

            # set up and/or post requested weighted output
            
            if not self.setup_output_aet_data(cell_count, cfg, cells): return False
            return True
        except:
            logging.error('\n  ERROR: ' + str(sys.exc_info()[0]) + " processing ET Cell requirements for " + self.cell_id + ".")
            return False

    def setup_output_aet_data(self, cell_count, cfg, cells):
        """Set up aet output data

        Args:
            cell_count: count of et cell being processed
            cfg: configuration data from INI file
            cells: ET Cell data (dict)

        Returns:
            success: True or False
        """
        logging.debug('Processing specified area et data')
        
        try:
            
            # Check/modify units

            for field_key, field_units in cfg.output_aet['units'].items():
                if field_units is None:
                    continue
                elif field_units.lower() in ['mm', 'mm/d', 'mm/day']:
                    continue
                elif field_units.lower() in ['m3/s', 'cms', 'decimal', 'fraction', 'none']:
                    continue
                elif field_units.lower() == 'm':
                    self.etcData_df[field_key] *= 0.001
                elif field_units.lower() == 'm/day':
                    self.etcData_df[field_key] *= 0.001
                elif field_units.lower() == 'meter':
                    self.etcData_df[field_key] *= 0.001
                elif field_units.lower() == 'in*100':
                    self.etcData_df[field_key] /= 0.254
                elif field_units.lower() == 'in*10':
                    self.etcData_df[field_key] /= 2.54
                elif field_units.lower() in ['in', 'in/d', 'in/day', 'inches/day', 'inches']:
                    self.etcData_df[field_key] /= 25.4
                elif field_units.lower() in ['cfs', 'ft3/s']:
                    self.etcData_df[field_key] *= 35.3146667215
                else:
                    logging.error('\n ERROR: Unknown {0} units {1}'.format(field_key, field_units) + 'converting aet output')
            data_fields = list(self.etcData_df.columns)
            for fn in data_fields:
                if fn == "date": continue
                if fn in cfg.used_output_aet_fields:
                    self.etcData_df = self.etcData_df.rename(columns={fn:cfg.output_aet['fields'][fn]})
                else:
                    self.etcData_df.drop(fn, axis = 1, inplace = True)
            if 'date' in cfg.output_aet['fields'] and cfg.output_aet['fields']['date'] is not None: 
                try:
                    daily_output_aet_df.index.set_names(cfg.output_aet['fields']['date'], inplace = True)
                except: pass    # Index is probably already named 'Date'
            data_fields = list(self.etcData_df.columns)

            # set up aggregations
            
            aggregation_func = {}
            for fn in data_fields:
                fc = cfg.output_aet['out_data_fields'].index(fn)
                field_name = cfg.output_aet['data_out_fields'][fc]
                if "flow" in field_name: 
                    aggregation_func.update({fn: np.mean})
                else:
                    aggregation_func.update({fn: np.sum})
            if cfg.monthly_output_aet_flag:
                # monthly_output_aet_df = self.etcData_df.resample('MS').apply( aggregation_func)
                monthly_output_aet_df = self.etcData_df.resample('M').apply( aggregation_func)
            if cfg.annual_output_aet_flag:
                # annual_output_aet_df = self.etcData_df.resample('AS').apply( aggregation_func)
                annual_output_aet_df = self.etcData_df.resample('A').apply( aggregation_func)
             
            # set up output fields

            if cfg.daily_output_aet_flag:
                adj_daily_fields = []
                if 'year' in cfg.used_output_aet_fields: 
                    adj_daily_fields.append(cfg.output_aet['fields']['year'])
                    self.etcData_df[cfg.output_aet['fields']['year']] = self.etcData_df.index.year
                if 'month' in cfg.used_output_aet_fields: 
                    adj_daily_fields.append(cfg.output_aet['fields']['month'])
                    self.etcData_df[cfg.output_aet['fields']['month']] = self.etcData_df.index.month
                if 'day' in cfg.used_output_aet_fields: 
                    adj_daily_fields.append(cfg.output_aet['fields']['day'])
                    self.etcData_df[cfg.output_aet['fields']['day']] = self.etcData_df.index.day
                if 'doy' in cfg.used_output_aet_fields: 
                    adj_daily_fields.append(cfg.output_aet['fields']['doy'])
                    self.etcData_df[cfg.output_aet['fields']['doy']] = self.etcData_df.index.doy
                adj_daily_fields.extend(cfg.output_aet['out_data_fields'])
            
                # convert flows to volume if specified

                if cfg.output_aet['daily_volume_units'] is not None:
                    if 'etflow' in cfg.used_output_aet_fields:
                        self.etcData_df[cfg.output_aet['fields']['etflow']] = compute_daily_volume(self.etcData_df.index, self.etcData_df[cfg.output_aet['fields']['etflow']].values, cfg.output_aet['daily_volume_units'])
                    if 'nirflow' in cfg.used_output_aet_fields:
                        self.etcData_df[cfg.output_aet['fields']['nirflow']] = compute_daily_volume(self.etcData_df.index, self.etcData_df[cfg.output_aet['fields']['nirflow']].values, cfg.output_aet['daily_volume_units'])
                self.etcData_df.index = self.etcData_df.index + pd.Timedelta( \
                    hours = cfg.output_aet['daily_hour_offset'], \
                    minutes = cfg.output_aet['daily_minute_offset'])
            if cfg.monthly_output_aet_flag:
                adj_monthly_fields = []
                if 'year' in cfg.used_output_aet_fields: 
                    adj_monthly_fields.append(cfg.output_aet['fields']['year'])
                    monthly_output_aet_df[cfg.output_aet['fields']['year']] = monthly_output_aet_df.index.year
                if 'month' in cfg.used_output_aet_fields: 
                    adj_monthly_fields.append(cfg.output_aet['fields']['month'])
                    monthly_output_aet_df[cfg.output_aet['fields']['month']] = monthly_output_aet_df.index.month
                adj_monthly_fields.extend(cfg.output_aet['out_data_fields'])
            
                # convert flows to volume if specified

                if cfg.output_aet['monthly_volume_units'] is not None:
                    if 'etflow' in cfg.used_output_aet_fields:
                        monthly_output_aet_df[cfg.output_aet['fields']['etflow']] = compute_monthly_volume(monthly_output_aet_df.index, monthly_output_aet_df[cfg.output_aet['fields']['etflow']].values, cfg.output_aet['monthly_volume_units'])
                    if 'nirflow' in cfg.used_output_aet_fields:
                        monthly_output_aet_df[cfg.output_aet['fields']['nirflow']] = compute_monthly_volume(monthly_output_aet_df.index, monthly_output_aet_df[cfg.output_aet['fields']['nirflow']].values, cfg.output_aet['monthly_volume_units'])
                self.etcData_df.index = self.etcData_df.index + pd.Timedelta( \
                    hours = cfg.output_aet['monthly_hour_offset'], \
                    minutes = cfg.output_aet['monthly_minute_offset'])
            if cfg.annual_output_aet_flag:
                adj_annual_fields = []
                if 'year' in cfg.used_output_aet_fields: 
                    adj_annual_fields.append(cfg.output_aet['fields']['year'])
                    annual_output_aet_df[cfg.output_aet['fields']['year']] = annual_output_aet_df.index.year
                adj_annual_fields.extend(cfg.output_aet['out_data_fields'])
            
                # convert flows to volume if specified

                if cfg.output_aet['annual_volume_units'] is not None:
                    if 'etflow' in cfg.used_output_aet_fields:
                        annual_output_aet_df[cfg.output_aet['fields']['etflow']] = compute_annual_volume(annual_output_aet_df.index.year, annual_output_aet_df[cfg.output_aet['fields']['etflow']].values, cfg.output_aet['annual_volume_units'])
                    if 'nirflow' in cfg.used_output_aet_fields:
                        annual_output_aet_df[cfg.output_aet['fields']['nirflow']] = compute_annual_volume(annual_output_aet_df.index.year, annual_output_aet_df[cfg.output_aet['fields']['nirflow']].values, cfg.output_aet['annual_volume_units'])
                self.etcData_df.index = self.etcData_df.index + pd.Timedelta( \
                    hours = cfg.output_aet['annual_hour_offset'], \
                    minutes = cfg.output_aet['annual_minute_offset'])
            if cfg.output_aet['data_structure_type'].upper() == 'SF P':
                logging.debug('Posting specified area et data')
                
                # post SF P format output

                if cfg.daily_output_aet_flag:
                    # format date attributes if values are formatted
                    
                    if cfg.output_aet['daily_float_format'] is not None:
                        if 'year' in cfg.used_out_aet_fields:
                            self.etcData_df[cfg.out_aet['fields']['year']] = \
                                self.etcData_df[cfg.out_aet['fields']['year']].map(lambda x: ' %4d' % x)
  	                if 'month' in cfg.used_out_aet_fields:
                            self.etcData_df[cfg.out_aet['fields']['month']] = \
                                self.etcData_df[cfg.out_aet['fields']['month']].map(lambda x: ' %2d' % x)
	                if 'day' in cfg.used_out_aet_fields:
                            self.etcData_df[cfg.out_aet['fields']['day']] = \
                                self.etcData_df[cfg.out_aet['fields']['day']].map(lambda x: ' %2d' % x)
	                if 'doy' in cfg.used_out_aet_fields:
                            self.etcData_df[cfg.out_aet['fields']['doy']] = \
                                self.etcData_df[cfg.out_aet['fields']['doy']].map(lambda x: ' %3d' % x)
                                
                    # post daily output
            
                    daily_output_aet_path = os.path.join(cfg.daily_output_aet_ws, cfg.output_aet['name_format'] % self.cell_id)
                    logging.debug('  {0}'.format(daily_output_aet_path))
                    with open(daily_output_aet_path, 'w') as daily_output_aet_f:
                        daily_output_aet_f.write(cfg.output_aet['daily_header1'] + '\n')
                        if cfg.output_aet['header_lines'] == 2:
                            daily_output_aet_f.write(cfg.output_aet['daily_header2'] + '\n')
           	        if 'date' in cfg.used_output_aet_fields:
                            self.etcData_df.to_csv(daily_output_aet_f, sep = cfg.output_aet['delimiter'], 
                                header = False, date_format = cfg.output_aet['daily_date_format'],
                                float_format = cfg.output_aet['daily_float_format'],
                                na_rep = 'NaN', columns = adj_daily_fields)
    	                else:
                            self.etcData_df.to_csv(daily_output_aet_f, sep = cfg.output_aet['delimiter'],
                                header = False, index = False, na_rep = 'NaN', columns = adj_daily_fields, 
                                float_format = cfg.output_aet['daily_float_format'])
                    del self.etcData_df, daily_output_aet_path, adj_daily_fields
                if cfg.monthly_output_aet_flag:
                    # format date attributes if values are formatted
                    
                    if cfg.output_aet['monthly_float_format'] is not None:
                        if 'year' in cfg.used_out_aet_fields:
                            monthly_output_aet_df[cfg.out_aet['fields']['year']] = \
                                monthly_output_aet_df[cfg.out_aet['fields']['year']].map(lambda x: ' %4d' % x)
  	                if 'month' in cfg.used_out_aet_fields:
                            monthly_output_aet_df[cfg.out_aet['fields']['month']] = \
                                monthly_output_aet_df[cfg.out_aet['fields']['month']].map(lambda x: ' %2d' % x)

                    # post monthly output
            
                    monthly_output_aet_path = os.path.join(cfg.monthly_output_aet_ws, cfg.output_aet['name_format'] % self.cell_id)
                    logging.debug('  {0}'.format(monthly_output_aet_path))
                    with open(monthly_output_aet_path, 'w') as monthly_output_aet_f:
                        monthly_output_aet_f.write(cfg.output_aet['monthly_header1'] + '\n')
                        if cfg.output_aet['header_lines'] == 2:
                            monthly_output_aet_f.write(cfg.output_aet['monthly_header2'] + '\n')
                        if 'date' in cfg.used_output_aet_fields:
                            monthly_output_aet_df.to_csv(monthly_output_aet_f, sep = cfg.output_aet['delimiter'], 
                                header = False, date_format = cfg.output_aet['monthly_date_format'],
                                float_format = cfg.output_aet['monthly_float_format'],
                                na_rep = 'NaN', columns = adj_monthly_fields)
    	                else:
                            monthly_output_aet_df.to_csv(monthly_output_aet_f, sep = cfg.output_aet['delimiter'],
                                header = False, index = False, na_rep = 'NaN', columns = adj_monthly_fields, 
                                float_format = cfg.output_aet['monthly_float_format'])
                    del monthly_output_aet_df, monthly_output_aet_path, adj_monthly_fields
                if cfg.annual_output_aet_flag:
                    # format date attributes if values are formatted
                    
                    if cfg.output_aet['annual_float_format'] is not None:
                        if 'year' in cfg.used_out_aet_fields:
                            annual_output_aet_df[cfg.out_aet['fields']['year']] = \
                                annual_output_aet_df[cfg.out_aet['fields']['year']].map(lambda x: ' %4d' % x)

                    # post annual output
            
                    annual_output_aet_path = os.path.join(cfg.annual_output_aet_ws, cfg.output_aet['name_format'] % self.cell_id)
                    logging.debug('  {0}'.format(annual_output_aet_path))
                    with open(annual_output_aet_path, 'w') as annual_output_aet_f:
                        annual_output_aet_f.write(cfg.output_aet['annual_header1'] + '\n')
                        if cfg.output_aet['header_lines'] == 2:
                            annual_output_aet_f.write(cfg.output_aet['annual_header2'] + '\n')
                        if 'date' in cfg.used_output_aet_fields:
                            annual_output_aet_df.to_csv(annual_output_aet_f, sep = cfg.output_aet['delimiter'], 
                                header = False, date_format = cfg.output_aet['annual_date_format'],
                                float_format = cfg.output_aet['annual_float_format'],
                                na_rep = 'NaN', columns = adj_annual_fields)
    	                else:
                            annual_output_aet_df.to_csv(annual_output_aet_f, sep = cfg.output_aet['delimiter'],
                                header = False, index = False, na_rep = 'NaN', columns = adj_annual_fields, 
                                float_format = cfg.output_aet['annual_float_format'])
                    del annual_output_aet_df, annual_output_aet_path, adj_annual_fields
            else:    # formats other than SF P
                logging.debug('Processing specified area et data by parameter')
                if cell_count == 1:
                    logging.warning('Setting up specified area et data by parameter')

                    # construct empty data frame for each output parameter
                    
                    if cfg.daily_output_aet_flag:
                        daily_index = pd.date_range(cfg.start_dt, cfg.end_dt, freq = "D", name = "Date")
                        daily_index = daily_index + pd.Timedelta( \
                            hours = cfg.output_aet['daily_hour_offset'], \
                            minutes = cfg.output_aet['daily_minute_offset'])
                        for field_name in adj_daily_fields:
                            if field_name.lower() in ['year', 'month', 'day', 'doy']: continue
                            cells.cell_daily_output_aet_data[field_name] = pd.DataFrame(index = daily_index)
                    if cfg.monthly_output_aet_flag:
                        monthly_index = pd.date_range(cfg.start_dt, cfg.end_dt, freq = "M", name = "Date")
                        monthly_index = monthly_index + pd.Timedelta( \
                            hours = cfg.output_aet['monthly_hour_offset'], \
                            minutes = cfg.output_aet['monthly_minute_offset'])
                        for field_name in adj_monthly_fields:
                            if field_name.lower() in ['year', 'month', 'day', 'doy']: continue
                            cells.cell_monthly_output_aet_data[field_name] = pd.DataFrame(index = monthly_index)
                    if cfg.annual_output_aet_flag:
                        annual_index = pd.date_range(cfg.start_dt, cfg.end_dt, freq = "A", name = "Date")
                        annual_index = annual_index + pd.Timedelta( \
                            hours = cfg.output_aet['annual_hour_offset'], \
                            minutes = cfg.output_aet['annual_minute_offset'])
                        for field_name in adj_annual_fields:
                            if field_name.lower() in ['year', 'month', 'day', 'doy']: continue
                            cells.cell_annual_output_aet_data[field_name] = pd.DataFrame(index = annual_index)
                if cfg.daily_output_aet_flag:
                    for field_name in adj_daily_fields:
                        if field_name.lower() in ['year', 'month', 'day', 'doy']: continue
                        param_df = cells.cell_daily_output_aet_data.get(field_name)
                        sp_name = self.cell_id + "." + field_name
                        param_df[sp_name] = self.etcData_df[field_name].values
                        cells.cell_daily_output_aet_data[field_name] = param_df
                        del param_df
                    del self.etcData_df, adj_daily_fields
                if cfg.monthly_output_aet_flag:
                    for field_name in adj_monthly_fields:
                        if field_name.lower() in ['year', 'month', 'day', 'doy']: continue
                        param_df = cells.cell_monthly_output_aet_data.get(field_name)
                        sp_name = self.cell_id + "." + field_name
                        param_df[sp_name] = monthly_output_aet_df[field_name].values
                        cells.cell_monthly_output_aet_data[field_name] = param_df
                        del param_df
                    del monthly_output_aet_df, adj_monthly_fields
                if cfg.annual_output_aet_flag:
                    for field_name in adj_annual_fields:
                        if field_name.lower() in ['year', 'month', 'day', 'doy']: continue
                        param_df = cells.cell_annual_output_aet_data.get(field_name)
                        sp_name = self.cell_id + "." + field_name
                        param_df[sp_name] = annual_output_aet_df[field_name].values
                        cells.cell_annual_output_aet_data[field_name] = param_df
                        del param_df
                    del annual_output_aet_df, adj_annual_fields
            return True;
        except:
            logging.error('\nERROR: ' + str(sys.exc_info()[0]) + 'occurred setting up output aet data for {0}', format(self.cell_id))
            return False

    def setup_output_cir_data(self, cell_count, cfg, cells):
        """Set up optional cir data output

        Args:
            cell_count: count of cir node being processed
            cfg: configuration data from INI file
            cells: ET cells data (dict)

        Returns:
            success: True or False
        """
        logging.debug('Processing individual cir output')
        try:
            if 'date' in cfg.output_cir['fields'] and cfg.output_cir['fields']['date'] is not None: 
                self.etcCropIRs_df.index.set_names(cfg.output_cir['fields']['date'], inplace = True)
            data_fields = list(self.etcCropIRs_df.columns)
        
            # Check/modify units

            if cfg.output_cir['cir_units'].lower() == 'in*100':
                for col_name in data_fields:
                    self.etcCropIRs_df[col_name] /= 0.254
            elif cfg.output_cir['cir_units'].lower() == 'in*10':
                for col_name in data_fields:
                    self.etcCropIRs_df[col_name] /= 2.54
            elif cfg.output_cir['cir_units'].lower() in ['in', 'in/d', 'in/day', 'inches/day', 'inches']:
                for col_name in data_fields:
                    self.etcCropIRs_df[col_name] /= 25.4
            elif cfg.output_cir['cir_units'].lower() == 'm':
                for col_name in data_fields:
                    self.etcCropIRs_df[col_name] *= 0.001
            elif cfg.output_cir['cir_units'].lower() == 'm/day':
                for col_name in data_fields:
                    self.etcCropIRs_df[col_name] *= 0.001
            elif cfg.output_cir['cir_units'].lower() == 'meter':
                for col_name in data_fields:
                    self.etcCropIRs_df[col_name] *= 0.001

            # set up aggregations
            
            aggregation_func = {}
            for col_name in data_fields:
                aggregation_func.update({col_name: np.sum})
            if cfg.monthly_output_cir_flag:
                # monthly_output_cir_df = self.etcCropIRs_df.resample('MS').apply( aggregation_func)
                monthly_output_cir_df = self.etcCropIRs_df.resample('M').apply( aggregation_func)
            if cfg.annual_output_cir_flag:
                # annual_output_cir_df = self.etcCropIRs_df.resample('AS').apply( aggregation_func)
                annual_output_cir_df = self.etcCropIRs_df.resample('A').apply( aggregation_func)
             
            # set up output fields

            if cfg.daily_output_cir_flag:
                # adj_daily_fields = list(self.etcCropIRs_df.columns)
                adj_daily_fields = []
                if cfg.output_cir['fields']['year'] is not None: 
                    adj_daily_fields.append(cfg.output_cir['fields']['year'])
                    self.etcCropIRs_df[cfg.output_cir['fields']['year']] = self.etcCropIRs_df.index.year
                if cfg.output_cir['fields']['month'] is not None: 
                    adj_daily_fields.append(cfg.output_cir['fields']['month'])
                    self.etcCropIRs_df[cfg.output_cir['fields']['month']] = self.etcCropIRs_df.index.month
                if cfg.output_cir['fields']['day'] is not None: 
                    adj_daily_fields.append(cfg.output_cir['fields']['day'])
                    self.etcCropIRs_df[cfg.output_cir['fields']['day']] = self.etcCropIRs_df.index.day
                adj_daily_fields.extend(data_fields)
                self.etcCropIRs_df.index = self.etcCropIRs_df.index + pd.Timedelta( \
                    hours = cfg.output_cir['daily_hour_offset'], \
                    minutes = cfg.output_cir['daily_minute_offset'])
            if cfg.monthly_output_cir_flag:
                # adj_monthly_fields = list(monthly_output_cir_df)
                adj_monthly_fields = []
                if cfg.output_cir['fields']['year'] is not None: 
                    adj_monthly_fields.append(cfg.output_cir['fields']['year'])
                    monthly_output_cir_df[cfg.output_cir['fields']['year']] = monthly_output_cir_df.index.year
                if cfg.output_cir['fields']['month'] is not None: 
                    adj_monthly_fields.append(cfg.output_cir['fields']['month'])
                    monthly_output_cir_df[cfg.output_cir['fields']['month']] = monthly_output_cir_df.index.month
                adj_monthly_fields.extend(data_fields)
                self.etcCropIRs_df.index = self.etcCropIRs_df.index + pd.Timedelta( \
                    hours = cfg.output_cir['monthly_hour_offset'], \
                    minutes = cfg.output_cir['monthly_minute_offset'])
            if cfg.annual_output_cir_flag:
                # adj_annual_fields = list(annual_output_cir_df)
                adj_annual_fields = []
                if cfg.output_cir['fields']['year'] is not None: 
                    adj_annual_fields.append(cfg.output_cir['fields']['year'])
                    annual_output_cir_df[cfg.output_cir['fields']['year']] = annual_output_cir_df.index.year
                adj_annual_fields.extend(data_fields)
                self.etcCropIRs_df.index = self.etcCropIRs_df.index + pd.Timedelta( \
                    hours = cfg.output_cir['annual_hour_offset'], \
                    minutes = cfg.output_cir['annual_minute_offset'])
            if cfg.output_cir['data_structure_type'].upper() == 'SF P':
                logging.debug('Posting individual cir output')
                
                # post SF P format output

                # set up header(s)
                
                if cfg.output_cir['fields']['date'] is None: 
                    header1 = ""
                else:
                    header1 = cfg.output_cir['fields']['date']
                if cfg.output_cir['fields']['year'] is not None: 
                    if header1 == "":
                        header1 = cfg.output_cir['fields']['year']
                    else:
                        header1 = header1 + \
                            cfg.output_cir['delimiter'] + cfg.output_cir['fields']['year']
                if cfg.output_cir['fields']['month'] is not None: 
                    if header1 == "":
                        header1 = cfg.output_cir['fields']['month']
                    else:
                        header1 = header1 + \
                            cfg.output_cir['delimiter'] + cfg.output_cir['fields']['month']
                if cfg.output_cir['fields']['day'] is not None: 
                    if header1 == "":
                        header1 =  cfg.output_cir['fields']['day']
                    else:
                        header1 = header1 + \
                            cfg.output_cir['delimiter'] + cfg.output_cir['fields']['day']
                for fn in data_fields:
                    header1 = header1 + cfg.output_cir['delimiter'] + fn
                if cfg.output_cir['fields']['date'] is None: 
                    header2 = ""
                else:
                    header2 = "Units"
                if cfg.output_cir['fields']['year'] is not None: 
                    if header2 == "":
                        header2 = cfg.output_cir['fields']['year']
                    else:
                        header2 = header2 + \
                            cfg.output_cir['delimiter'] + cfg.output_cir['fields']['year']
                if cfg.output_cir['fields']['month'] is not None: 
                    if header2 == "":
                        header2 = cfg.output_cir['fields']['month']
                    else:
                        header2 = header2 + \
                            cfg.output_cir['delimiter'] + cfg.output_cir['fields']['month']
                if cfg.output_cir['fields']['day'] is not None: 
                    if header2 == "":
                        header2 = cfg.output_cir['fields']['day']
                    else:
                        header2 = header2 + \
                            cfg.output_cir['delimiter'] + cfg.output_cir['fields']['day']
                for fn in data_fields:
                    header2 = header2 + cfg.output_cir['delimiter'] + cfg.output_cir['cir_units']
                if cfg.daily_output_cir_flag:
                    # post daily output
            
                    daily_output_cir_path = os.path.join(cfg.daily_output_cir_ws, cfg.output_cir['name_format'] % self.cell_id)
                    logging.debug('  Daily CIR output path is {0}'.format(daily_output_cir_path))
                    with open(daily_output_cir_path, 'w') as daily_output_cir_f:
                        daily_output_cir_f.write(header1 + '\n')
                        if cfg.output_cir['header_lines'] == 2:
                            daily_output_cir_f.write(header2 + '\n')
                        if cfg.output_cir['fields']['date'] is None: 
                            self.etcCropIRs_df.to_csv(daily_output_cir_f, sep = cfg.output_cir['delimiter'],
                                header = False, index = False, columns = adj_daily_fields, 
                                na_rep = 'NaN', float_format = cfg.output_cir['daily_float_format'])
    	                else:
                            self.etcCropIRs_df.to_csv(daily_output_cir_f, sep = cfg.output_cir['delimiter'], 
                                header = False, date_format = cfg.output_cir['daily_date_format'],
                                float_format = cfg.output_cir['daily_float_format'],
                                na_rep = 'NaN', columns = adj_daily_fields)
                    del self.etcCropIRs_df, daily_output_cir_path, adj_daily_fields
                if cfg.output_cir['fields']['day'] is not None: 
                    drop_string = cfg.output_cir['delimiter'] + cfg.output_cir['fields']['day']
                    header1 = header1.replace(drop_string, '')
                    header2 = header2.replace(drop_string, '')
                if cfg.monthly_output_cir_flag:
                    # post monthly output

                    monthly_output_cir_path = os.path.join(cfg.monthly_output_cir_ws, cfg.output_cir['name_format'] % self.cell_id)
                    logging.debug('  Monthly CIR output path is {0}'.format(monthly_output_cir_path))
                    with open(monthly_output_cir_path, 'w') as monthly_output_cir_f:
                        monthly_output_cir_f.write(header1 + '\n')
                        if cfg.output_cir['header_lines'] == 2:
                            monthly_output_cir_f.write(header2 + '\n')
                        if cfg.output_cir['fields']['date'] is None: 
                            monthly_output_cir_df.to_csv(monthly_output_cir_f, sep = cfg.output_cir['delimiter'],
                                header = False, index = False, columns = adj_monthly_fields, 
                                na_rep = 'NaN', float_format = cfg.output_cir['monthly_float_format'])
    	                else:
                            monthly_output_cir_df.to_csv(monthly_output_cir_f, sep = cfg.output_cir['delimiter'], 
                                header = False, date_format = cfg.output_cir['monthly_date_format'],
                                float_format = cfg.output_cir['monthly_float_format'],
                                na_rep = 'NaN', columns = adj_monthly_fields)
                    del monthly_output_cir_df, monthly_output_cir_path, adj_monthly_fields
                if cfg.output_cir['fields']['month'] is not None: 
                    drop_string = cfg.output_cir['delimiter'] + cfg.output_cir['fields']['month']
                    header1 = header1.replace(drop_string, '')
                    header2 = header2.replace(drop_string, '')
                if cfg.annual_output_cir_flag:
                    # post annual output
            
                    annual_output_cir_path = os.path.join(cfg.annual_output_cir_ws, cfg.output_cir['name_format'] % self.cell_id)
                    logging.debug('  Annual CIR output path is {0}'.format(annual_output_cir_path))
                    with open(annual_output_cir_path, 'w') as annual_output_cir_f:
                        annual_output_cir_f.write(header1 + '\n')
                        if cfg.output_cir['header_lines'] == 2:
                            annual_output_cir_f.write(header2 + '\n')
                        if cfg.output_cir['fields']['date'] is None: 
                            annual_output_cir_df.to_csv(annual_output_cir_f, sep = cfg.output_cir['delimiter'],
                                header = False, index = False, columns = adj_annual_fields, 
                                na_rep = 'NaN', float_format = cfg.output_cir['annual_float_format'])
    	                else:
                            annual_output_cir_df.to_csv(annual_output_cir_f, sep = cfg.output_cir['delimiter'], 
                                header = False, date_format = cfg.output_cir['annual_date_format'],
                                float_format = cfg.output_cir['annual_float_format'],
                                na_rep = 'NaN', columns = adj_annual_fields)
                    del annual_output_cir_df, annual_output_cir_path, adj_annual_fields
            else:    # formats other than SF P
                if cfg.daily_output_cir_flag:
                    if cell_count == 1:
                        cells.etcDailyCropIRs_df = self.etcCropIRs_df.copy()
                    else:
                        cells.etcDailyCropIRs_df = cells.etcDailyCropIRs_df.merge(self.etcCropIRs_df, left_index = True, right_index = True)
                del self.etcCropIRs_df
                if cfg.monthly_output_cir_flag:
                    if cell_count == 1:
                        cells.etcMonthlyCropIRs_df = monthly_output_cir_df.copy()
                    else:
                        cells.etcMonthlyCropIRs_df = cells.etcMonthlyCropIRs_df.merge(monthly_output_cir_df, left_index = True, right_index = True)
                    del monthly_output_cir_df
                if cfg.annual_output_cir_flag:
                    if cell_count == 1:
                        cells.etcAnnualCropIRs_df = annual_output_cir_df.copy()
                    else:
                        cells.etcAnnualCropIRs_df = cells.etcAnnualCropIRs_df.merge(annual_output_cir_df, left_index = True, right_index = True)
                    del annual_output_cir_df
            return True;
        except:
            logging.error('\nERROR: ' + str(sys.exc_info()[0]) + 'occurred setting up output_cir data for {0}', format(self.cell_id))
            return False

    def setup_output_cet_data(self, cell_count, cfg, cells):
        """Set up optional cet data output

        Args:
            cell_count: count of cet node being processed
            cfg: configuration data from INI file
            cells: ET cells data (dict)

        Returns:
            success: True or False
        """
        logging.debug('Processing individual cet output')
        try:
            if 'date' in cfg.output_cet['fields'] and cfg.output_cet['fields']['date'] is not None: 
                self.etcCropETs_df.index.set_names(cfg.output_cet['fields']['date'], inplace = True)
            data_fields = list(self.etcCropETs_df.columns)
        
            # Check/modify units

            if cfg.output_cet['cet_units'].lower() == 'in*100':
                for col_name in data_fields:
                    self.etcCropETs_df[col_name] /= 0.254
            elif cfg.output_cet['cet_units'].lower() == 'in*10':
                for col_name in data_fields:
                    self.etcCropETs_df[col_name] /= 2.54
            elif cfg.output_cet['cet_units'].lower() in ['in', 'in/d', 'in/day', 'inches/day', 'inches']:
                for col_name in data_fields:
                    self.etcCropETs_df[col_name] /= 25.4
            elif cfg.output_cet['cet_units'].lower() == 'm':
                for col_name in data_fields:
                    self.etcCropETs_df[col_name] *= 0.001
            elif cfg.output_cet['cet_units'].lower() == 'm/day':
                for col_name in data_fields:
                    self.etcCropETs_df[col_name] *= 0.001
            elif cfg.output_cet['cet_units'].lower() == 'meter':
                for col_name in data_fields:
                    self.etcCropETs_df[col_name] *= 0.001

            # set up aggregations
            
            aggregation_func = {}
            for col_name in data_fields:
                aggregation_func.update({col_name: np.sum})
            if cfg.monthly_output_cet_flag:
                # monthly_output_cet_df = self.etcCropETs_df.resample('MS').apply( aggregation_func)
                monthly_output_cet_df = self.etcCropETs_df.resample('M').apply( aggregation_func)
            if cfg.annual_output_cet_flag:
                # annual_output_cet_df = self.etcCropETs_df.resample('AS').apply( aggregation_func)
                annual_output_cet_df = self.etcCropETs_df.resample('A').apply( aggregation_func)
             
            # set up output fields

            if cfg.daily_output_cet_flag:
                # adj_daily_fields = list(self.etcCropETs_df.columns)
                adj_daily_fields = []
                if cfg.output_cet['fields']['year'] is not None: 
                    adj_daily_fields.append(cfg.output_cet['fields']['year'])
                    self.etcCropETs_df[cfg.output_cet['fields']['year']] = self.etcCropETs_df.index.year
                if cfg.output_cet['fields']['month'] is not None: 
                    adj_daily_fields.append(cfg.output_cet['fields']['month'])
                    self.etcCropETs_df[cfg.output_cet['fields']['month']] = self.etcCropETs_df.index.month
                if cfg.output_cet['fields']['day'] is not None: 
                    adj_daily_fields.append(cfg.output_cet['fields']['day'])
                    self.etcCropETs_df[cfg.output_cet['fields']['day']] = self.etcCropETs_df.index.day
                adj_daily_fields.extend(data_fields)
                self.etcCropETs_df.index = self.etcCropETs_df.index + pd.Timedelta( \
                    hours = cfg.output_cet['daily_hour_offset'], \
                    minutes = cfg.output_cet['daily_minute_offset'])
            if cfg.monthly_output_cet_flag:
                # adj_monthly_fields = list(monthly_output_cet_df)
                adj_monthly_fields = []
                if cfg.output_cet['fields']['year'] is not None: 
                    adj_monthly_fields.append(cfg.output_cet['fields']['year'])
                    monthly_output_cet_df[cfg.output_cet['fields']['year']] = monthly_output_cet_df.index.year
                if cfg.output_cet['fields']['month'] is not None: 
                    adj_monthly_fields.append(cfg.output_cet['fields']['month'])
                    monthly_output_cet_df[cfg.output_cet['fields']['month']] = monthly_output_cet_df.index.month
                adj_monthly_fields.extend(data_fields)
                self.etcCropETs_df.index = self.etcCropETs_df.index + pd.Timedelta( \
                    hours = cfg.output_cet['monthly_hour_offset'], \
                    minutes = cfg.output_cet['monthly_minute_offset'])
            if cfg.annual_output_cet_flag:
                # adj_annual_fields = list(annual_output_cet_df)
                adj_annual_fields = []
                if cfg.output_cet['fields']['year'] is not None: 
                    adj_annual_fields.append(cfg.output_cet['fields']['year'])
                    annual_output_cet_df[cfg.output_cet['fields']['year']] = annual_output_cet_df.index.year
                adj_annual_fields.extend(data_fields)
                self.etcCropETs_df.index = self.etcCropETs_df.index + pd.Timedelta( \
                    hours = cfg.output_cet['annual_hour_offset'], \
                    minutes = cfg.output_cet['annual_minute_offset'])
            if cfg.output_cet['data_structure_type'].upper() == 'SF P':
                logging.debug('Posting individual cet output')
                
                # post SF P format output

                # set up header(s)
                
                if cfg.output_cet['fields']['date'] is None: 
                    header1 = ""
                else:
                    header1 = cfg.output_cet['fields']['date']
                if cfg.output_cet['fields']['year'] is not None: 
                    if header1 == "":
                        header1 = cfg.output_cet['fields']['year']
                    else:
                        header1 = header1 + \
                            cfg.output_cet['delimiter'] + cfg.output_cet['fields']['year']
                if cfg.output_cet['fields']['month'] is not None: 
                    if header1 == "":
                        header1 = cfg.output_cet['fields']['month']
                    else:
                        header1 = header1 + \
                            cfg.output_cet['delimiter'] + cfg.output_cet['fields']['month']
                if cfg.output_cet['fields']['day'] is not None: 
                    if header1 == "":
                        header1 =  cfg.output_cet['fields']['day']
                    else:
                        header1 = header1 + \
                            cfg.output_cet['delimiter'] + cfg.output_cet['fields']['day']
                for fn in data_fields:
                    header1 = header1 + cfg.output_cet['delimiter'] + fn
                if cfg.output_cet['fields']['date'] is None: 
                    header2 = ""
                else:
                    header2 = "Units"
                if cfg.output_cet['fields']['year'] is not None: 
                    if header2 == "":
                        header2 = cfg.output_cet['fields']['year']
                    else:
                        header2 = header2 + \
                            cfg.output_cet['delimiter'] + cfg.output_cet['fields']['year']
                if cfg.output_cet['fields']['month'] is not None: 
                    if header2 == "":
                        header2 = cfg.output_cet['fields']['month']
                    else:
                        header2 = header2 + \
                            cfg.output_cet['delimiter'] + cfg.output_cet['fields']['month']
                if cfg.output_cet['fields']['day'] is not None: 
                    if header2 == "":
                        header2 = cfg.output_cet['fields']['day']
                    else:
                        header2 = header2 + \
                            cfg.output_cet['delimiter'] + cfg.output_cet['fields']['day']
                for fn in data_fields:
                    header2 = header2 + cfg.output_cet['delimiter'] + cfg.output_cet['cet_units']
                if cfg.daily_output_cet_flag:
                    # post daily output
            
                    daily_output_cet_path = os.path.join(cfg.daily_output_cet_ws, cfg.output_cet['name_format'] % self.cell_id)
                    logging.debug('  Daily CET output path is {0}'.format(daily_output_cet_path))
                    with open(daily_output_cet_path, 'w') as daily_output_cet_f:
                        daily_output_cet_f.write(header1 + '\n')
                        if cfg.output_cet['header_lines'] == 2:
                            daily_output_cet_f.write(header2 + '\n')
                        if cfg.output_cet['fields']['date'] is None: 
                            self.etcCropETs_df.to_csv(daily_output_cet_f, sep = cfg.output_cet['delimiter'],
                                header = False, index = False, columns = adj_daily_fields, 
                                na_rep = 'NaN', float_format = cfg.output_cet['daily_float_format'])
    	                else:
                            self.etcCropETs_df.to_csv(daily_output_cet_f, sep = cfg.output_cet['delimiter'], 
                                header = False, date_format = cfg.output_cet['daily_date_format'],
                                float_format = cfg.output_cet['daily_float_format'],
                                na_rep = 'NaN', columns = adj_daily_fields)
                    del self.etcCropETs_df, daily_output_cet_path, adj_daily_fields
                if cfg.output_cet['fields']['day'] is not None: 
                    drop_string = cfg.output_cet['delimiter'] + cfg.output_cet['fields']['day']
                    header1 = header1.replace(drop_string, '')
                    header2 = header2.replace(drop_string, '')
                if cfg.monthly_output_cet_flag:
                    # post monthly output

                    monthly_output_cet_path = os.path.join(cfg.monthly_output_cet_ws, cfg.output_cet['name_format'] % self.cell_id)
                    logging.debug('  Monthly CET output path is {0}'.format(monthly_output_cet_path))
                    with open(monthly_output_cet_path, 'w') as monthly_output_cet_f:
                        monthly_output_cet_f.write(header1 + '\n')
                        if cfg.output_cet['header_lines'] == 2:
                            monthly_output_cet_f.write(header2 + '\n')
                        if cfg.output_cet['monthly_float_format'] is None:
                            if cfg.output_cet['fields']['date'] is None: 
                                monthly_output_cet_df.to_csv(monthly_output_cet_f, sep = cfg.output_cet['delimiter'],
                                    header = False, index = False, columns = adj_monthly_fields)
    	                    else:
                                monthly_output_cet_df.to_csv(monthly_output_cet_f, sep = cfg.output_cet['delimiter'], 
                                    header = False, date_format = cfg.output_cet['monthly_date_format'],
                                    columns = adj_monthly_fields)
                        else:    # formatted output causes loss of precision in crop et computations
                            if cfg.output_cet['fields']['date'] is None: 
                                monthly_output_cet_df.to_csv(monthly_output_cet_f, sep = cfg.output_cet['delimiter'],
                                    header = False, index = False, columns = adj_monthly_fields, 
                                    float_format = cfg.output_cet['monthly_float_format'])
    	                    else:
                                monthly_output_cet_df.to_csv(monthly_output_cet_f, sep = cfg.output_cet['delimiter'], 
                                    header = False, date_format = cfg.output_cet['monthly_date_format'],
                                    float_format = cfg.output_cet['monthly_float_format'],
                                    columns = adj_monthly_fields)
                    del monthly_output_cet_df, monthly_output_cet_path, adj_monthly_fields
                if cfg.output_cet['fields']['month'] is not None: 
                    drop_string = cfg.output_cet['delimiter'] + cfg.output_cet['fields']['month']
                    header1 = header1.replace(drop_string, '')
                    header2 = header2.replace(drop_string, '')
                if cfg.annual_output_cet_flag:
                    # post annual output
            
                    annual_output_cet_path = os.path.join(cfg.annual_output_cet_ws, cfg.output_cet['name_format'] % self.cell_id)
                    logging.debug('  Annual CET output path is {0}'.format(annual_output_cet_path))
                    with open(annual_output_cet_path, 'w') as annual_output_cet_f:
                        annual_output_cet_f.write(header1 + '\n')
                        if cfg.output_cet['header_lines'] == 2:
                            annual_output_cet_f.write(header2 + '\n')
                        if cfg.output_cet['annual_float_format'] is None:
                            if cfg.output_cet['fields']['date'] is None: 
                                annual_output_cet_df.to_csv(annual_output_cet_f, sep = cfg.output_cet['delimiter'],
                                    header = False, index = False, columns = adj_annual_fields)
        	            else:
                                annual_output_cet_df.to_csv(annual_output_cet_f, sep = cfg.output_cet['delimiter'], 
                                    header = False, date_format = cfg.output_cet['annual_date_format'],
                                    columns = adj_annual_fields)
                        else:    # formatted output causes loss of precision in crop et computations
                            if cfg.output_cet['fields']['date'] is None: 
                                annual_output_cet_df.to_csv(annual_output_cet_f, sep = cfg.output_cet['delimiter'],
                                    header = False, index = False, columns = adj_annual_fields, 
                                    float_format = cfg.output_cet['annual_float_format'])
    	                    else:
                                annual_output_cet_df.to_csv(annual_output_cet_f, sep = cfg.output_cet['delimiter'], 
                                    header = False, date_format = cfg.output_cet['annual_date_format'],
                                    float_format = cfg.output_cet['annual_float_format'],
                                    columns = adj_annual_fields)
                    del annual_output_cet_df, annual_output_cet_path, adj_annual_fields
            else:    # formats other than SF P
                if cfg.daily_output_cet_flag:
                    if cell_count == 1:
                        cells.etcDailyCropETs_df = self.etcCropETs_df.copy()
                    else:
                        cells.etcDailyCropETs_df = cells.etcDailyCropETs_df.merge(self.etcCropETs_df, left_index = True, right_index = True)
                del self.etcCropETs_df
                if cfg.monthly_output_cet_flag:
                    if cell_count == 1:
                        cells.etcMonthlyCropETs_df = monthly_output_cet_df.copy()
                    else:
                        cells.etcMonthlyCropETs_df = cells.etcMonthlyCropETs_df.merge(monthly_output_cet_df, left_index = True, right_index = True)
                    del monthly_output_cet_df
                if cfg.annual_output_cet_flag:
                    if cell_count == 1:
                        cells.etcAnnualCropETs_df = annual_output_cet_df.copy()
                    else:
                        cells.etcAnnualCropETs_df = cells.etcAnnualCropETs_df.merge(annual_output_cet_df, left_index = True, right_index = True)
                    del annual_output_cet_df
            return True;
        except:
            logging.error('\nERROR: ' + str(sys.exc_info()[0]) + 'occurred setting up output_cet data for {0}', format(self.cell_id))
            return False

    def crop_type_index(self, crop_number):
        """crop type index

        Args:
            crop_number: crop number to index

        Returns:
            ct_index
        """
        try:
            ct_index = self.usedCropTypes.index(crop_number)
        except:
            ct_index = - 1
        return ct_index

def seasonal_ctetdata(ngs_toggle, crop_irr_flag, season, actet, potet, precip, runoff, deep_perc, sim_irr, niwr):
    """Seasonal crop type et
    
    Args:
        ngs_toggle: non growing season toggle
        crop_irr_flag: crop irrigation flag
        season: season flag
        actet: actual crop type et
        potet: potential crop type et
        precip: total precipitation
        runoff: surface runoff
        deep_perc: deep percolation
        sim_irr: simulated irrigation

    Returns:
        cet, eff_prcp, cir: seasonally adjusted crop type et data
    """
    if ngs_toggle == 2 and season == 0:
        cet = 0.0
        eff_prcp = 0.0
        cir = 0.0
    else:
        if crop_irr_flag < 1:
            cet = potet
        else:
            cet = actet
        try:
            if sim_irr > 0:
                eff_prcp = precip - runoff
            else:
                eff_prcp = precip - runoff - deep_perc
        except ValueError:
            eff_prcp = precip - runoff - deep_perc
        if niwr is None:
            cir = cet - eff_prcp
        else:
            cir = niwr
    return cet, eff_prcp, cir

def crop_percents(crop_mix_type, irr_area, area_or_percent):
    """computes crop percents from crop area and total area

    Args:
        crop_mix_type: 0 for percents 1 for areas
        irr_area: total irrigated area
        area_or_percent: input area or percent

    Returns:
        crop_percent
    """
    if crop_mix_type == 1:
        if irr_area == 0.0:
            crop_percent  = 0.0
        else:
            crop_percent = area_or_percent * 1000 / irr_area
    else:
        crop_percent = area_or_percent * 1000
    return crop_percent

def calculate_ratios(c1, c2):
    """Calculate ratios of two NumPy arrays or df columns

    Args:
        c1: column 1 values
        c2: column 2 values

    Returns:
        NumPy array of ratios
    """
    if c2 == 0.0:
        return 1.0
    else:
        return c1 / c2
    
def apply_annual_ratios(ref_date, dt, ib_values, ann_ratios):
    """Apply annual ratios to daily array

    Args
        ref_date: Reference date
        dt: DateTimeIndex
        ib_values: NumPy array of values to be adjusted
        ann_ratios: annual adjustment ratios

    Returns:
        NumPy array of adjusted values
    """
    yCount = dt.year - ref_date.year
    return ib_values * ann_ratios[yCount]
    
def compute_flow(ref_date, dt, rate_values, area_values):
    """Compute flow from rate and area

    Args
        ref_date: Reference date
        dt: DateTimeIndex
        rate_values: NumPy array of rates
        area_values: annual areas

    Returns:
        NumPy array of adjusted values
    """
    yCount = dt.year - ref_date.year
    return rate_values * area_values[yCount] * mmHaPerDay_to_cms
    
def compute_daily_volume(dt, flow_values, units):
    """Convert daily flow to a volume

    Args
        dt: DateTimeIndex
        flow_values: NumPy array of flows
        unit: output units

    Returns:
        NumPy array of volumes
    """
    if ("acre-feet" in units.lower() or "af" in units.lower() or "acre-ft" in units.lower()):
        volume_values = flow_values * 1.983471074
    else:
        volume_values = flow_values * 86400.0
    return volume_values
    
def compute_monthly_volume(dt, flow_values, units):
    """Convert monthly flow to a volume

    Args
        dt: DateTimeIndex
        flow_values: NumPy array of flows
        unit: output units

    Returns:
        NumPy array of volumes
    """
    if ("acre-feet" in units.lower() or "af" in units.lower() or "acre-ft" in units.lower()):
        volume_values = flow_values * dt.days_in_month * 1.983471074
    else:
        volume_values = flow_values * dt.days_in_month * 86400.0
    return volume_values
    
def compute_annual_volume(years, flow_values, units):
    """Convert annual flow to a volume

    Args
        years: NumPy array of years
        flow_values: NumPy array of flows
        unit: output units

    Returns:
        NumPy array of volumes
    """
    volume_values = np.copy(flow_values)
    for yCount, year in enumerate(years):
        if ("acre-feet" in units.lower() or "af" in units.lower() or "acre-ft" in units.lower()):
            if (year % 400 == 0 or year % 100 == 0 or year % 4 == 0):
                volume_values[yCount] = flow_values[yCount] * 366 * 1.983471074
            else:
                volume_values[yCount] = flow_values[yCount] * 365 * 1.983471074
        else:
            if (year % 400 == 0 or year % 100 == 0 or year % 4 == 0):
                volume_values[yCount] = flow_values[yCount] * 366 * 86400.0
            else:
                volume_values[yCount] = flow_values[yCount] * 365 * 86400.0
    return volume_values
    
def compute_annual_volume_not_working(year, flow_values, units):
    """Convert annual flow to a volume

    Args
        year: NumPy array of years
        flow_values: NumPy array of flows
        unit: output units

    Returns:
        NumPy array of volumes
    """
    if ("acre-feet" in units.lower() or "af" in units.lower()):
        if (year % 400 == 0 or year % 100 == 0 or year % 4 == 0):
            volume_values = flow_values * 366 * 1.983471074
        else:
            volume_values = flow_values * 365 * 1.983471074
    else:
        if (year % 400 == 0 or year % 100 == 0 or year % 4 == 0):
            volume_values = flow_values * 366 * 86400.0
        else:
            volume_values = flow_values * 365 * 86400.0
    return volume_values
    
def compute_daily_fractions(ref_date, dt, daily_values, monthly_values):
    """Compute daily fractdions for daily and monthly values arrays

    Args:
        ref_date: Reference date
        dt: DateTimeIndex
        daily_values: NumPy array of daily values
        monthly_values: NumPy array of monthly values

    Returns:
        NumPy array of daily fractions
    """
    mCount = 12 * (dt.year - ref_date.year - 1) + dt.month - ref_date.month + 12
    try:
        daily_fractions = daily_values / monthly_values[mCount]
    except:
        daily_fractions = 1.0 / dt.days_in_month
    return daily_fractions
    
def user_begin_date(year_to_use, ibm, ibd):
    """computes user begin date

    Args:
        year_to_use: year to process
        ibm: input begin month
        ibd: input begin day

    Returns:
        begin_date
    """
    try:
        begMonth = max(1, min(12, int(ibm)))
    except:
        begMonth = 1
    try:
        begDay = max(1, min(31, int(ibd)))
    except:
        begDay = 1
    begin_date = datetime.datetime(year_to_use, begMonth, begDay)
    return begin_date

def user_end_date(year_to_use, iem, ied):
    """computes user end date

    Args:
        year_to_use: year to process
        iem: input end month
        ied: input end day

    Returns:
        end_dt
    """
    try:
        endMonth = max(1, min(12, int(iem)))
    except:
        endMonth = 12
    try:
        endDay = max(1, min(31, int(ied)))
    except:
        endDay = 31
    end_dt = datetime.datetime(year_to_use, endMonth, endDay)
    return end_dt

if __name__ == '__main__':
    pass
