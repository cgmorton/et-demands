#!/usr/bin/env python

import argparse
import datetime
import logging
import multiprocessing as mp
import os
import sys
import shutil
from time import clock

import numpy as np
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../lib')))
import aet_utils
import aet_config
import aet_cells
import mod_dmis

def main(ini_path, log_level = logging.WARNING, etcid_to_run = 'ALL', debug_flag = False, mp_procs = 1):
    """ Main function for running Area ET model

    Args:
        ini_path (str): file path ofproject INI file
        log_level (logging.lvl): 
        etcid_to_run: ET Cell id to run in lieu of 'ALL'
        debug_flag (bool): If True, write debug level comments to debug.txt
        mp_procs (int): number of cores to use for multiprocessing

    aeturns:
        None
    """
    clock_start = clock()
    
    # Start console logging immediately
    
    logger = aet_utils.console_logger(log_level = log_level)
    logging.warning('\nPython AREAET')
    if debug_flag and mp_procs > 1:
        logging.warning('  Debug mode, disabling multiprocessing')
        mp_procs = 1
    if mp_procs > 1:
        logging.warning('  Multiprocessing mode, {0} cores'.format(mp_procs))

    # Read INI file

    cfg = aet_config.AreaETConfig()
    cfg.read_aet_ini(ini_path, debug_flag)
 
    # Start file logging once INI file has been read in

    if debug_flag: logger = aet_utils.file_logger(logger, log_level = logging.DEBUG, output_ws = cfg.project_ws)

    # Read crop parameters needed for area calculations

    cfg.set_crop_params()

    # Read et cell properties and crop types

    cells = aet_cells.AETCellsData()
    cells.set_cell_crops(cfg)

    # Multiprocessing set up

    cell_mp_list =  []
    cell_mp_flag = False
    if mp_procs > 1:
        if cfg.output_aet_flag and cfg.output_aet['data_structure_type'].upper() == 'SF P':
            if not cfg.output_cir_flag or (cfg.output_cir_flag and cfg.output_cir['data_structure_type'].upper() == 'SF P'):
                if not cfg.output_cet_flag or (cfg.output_cet_flag and cfg.output_cet['data_structure_type'].upper() == 'SF P'):
                    if etcid_to_run == 'ALL':
                        cells_count = len(cells.et_cells_data.keys())
                        logging.warning('  Cells count: {}'.format(cells_count))
                        if cells_count > 1:
                            logging.warning("  Multiprocessing by cell")
                            cell_mp_flag = True
                    else:
                        logging.warning("Multiprocessing can only be used for multiple cells.")
                        mp_procs = 1
                else:
                    logging.warning("Area CET data structure type " + cfg.output_cet['data_structure_type'] + 
                                    " can not yet be created using multiple processing.")
                    mp_procs = 1
            else:
                logging.warning("Area CIR data structure type " + cfg.output_cir['data_structure_type'] + 
                                " can not yet be created using multiple processing.")
                mp_procs = 1
        else:
            logging.warning("Area ET data structure type " + cfg.output_aet['data_structure_type'] + 
                            " can not yet be created using multiple processing.")
            mp_procs = 1

    # loop thru et cells
    
    logging.warning("\n")
    cell_count = 0
    for cell_id, cell in sorted(cells.et_cells_data.items()):
        if etcid_to_run == 'ALL' or etcid_to_run == cell_id:
            logging.info('  Processing node id ' + cell_id + ' with name ' + cell.cell_name)
            cell_count += 1
            if cell_mp_flag and cfg.output_aet['data_structure_type'].upper() == 'SF P' and cell_count > 1:
                cell_mp_list.append([cell_count, cfg, cell, cells])
            else:
                if not cell.crop_types_cycle(cell_count, cfg, cells): 
                    sys.exit()
                if cell_count == 1:
                    cfg.number_days = int(cfg.end_dt.to_julian_date() - cfg.start_dt.to_julian_date() + 1)
                    cfg.number_years = int(cfg.end_dt.year - cfg.start_dt.year + 1)
                if not cell.read_cell_crop_mix(cfg):
                    sys.exit()
                if not cell.compute_area_requirements(cell_count, cfg, cells):
                    sys.exit()

    # Multiprocess all cells

    results = []
    if cell_mp_list:
        pool = mp.Pool(mp_procs)
        results = pool.imap(cell_mp, cell_mp_list, chunksize = 1)
        pool.close()
        pool.join()
        del pool, results

    # post output with parameter orientation
    
    if cfg.output_aet_flag and cfg.output_aet['data_structure_type'].upper() <> 'SF P':
        # post aet output data
        
        logging.info("\nPosting non 'SF P' output aet data")
        if 'date' in cfg.output_aet['fields'] and cfg.output_aet['fields'] is not None:
            date_is_posted = True
        else:
            date_is_posted = False
        if cfg.daily_output_aet_flag:
            if '%p' in cfg.output_aet['name_format']:    # individual parameter files
                for field_name, param_df in cells.cell_daily_output_aet_data.items():
                    field_key = None
                    for fk, fn in cfg.output_aet['fields'].items():
                        if fn == field_name:
                            field_key = fk
                            break
                    if field_key is None:
                        logging.error('ERROR:  Unable to determine key for ' + field_name + ' posting daily aet output')
                        sys.exit()
                    file_path = os.path.join(cfg.daily_output_aet_ws, 
                        cfg.output_aet['name_format'].replace('%p', cfg.output_aet['fnspec'][field_key]))
                    logging.debug('  Daily output path for {0} is {1}'.format(field_name, file_path))
                    if cfg.output_aet['file_type'].lower() == 'csf': 
                         if not mod_dmis.csf_output_by_dataframe(file_path, cfg.output_aet['delimiter'], 
                            param_df, cfg.output_aet['daily_float_format'], 
                            cfg.output_aet['daily_date_format'], date_is_posted):
                            sys.exit()
                    elif cfg.output_aet['file_type'].lower() == 'rdb': 
                         if not mod_dmis.rdb_output_by_dataframe(file_path, cfg.output_aet['delimiter'], 
                            param_df, cfg.output_aet['daily_float_format'], 
                            cfg.output_aet['daily_date_format'], date_is_posted):
                            sys.exit()
                    elif cfg.output_aet['file_type'].lower() == 'xls' or cfg.output_aet['file_type'].lower() == 'wb':
                        if os.path.isfile(file_path):
                            shutil.copyfile(file_path, file_path.replace('.xls', '_bu.xls'))
                        params_dict = {}
                        params_dict['[param_df'] = param_df
                        ws_names = []
                        ws_names.append(cfg.output_aet['wsspec'][field_key])
                        if not mod_dmis.wb_output_via_df_dict_openpyxl(
                                file_path, ws_names, params_dict, 
                                cfg.output_aet['daily_float_format'], 
                                cfg.output_aet['daily_date_format'].replace('%Y','yyyy').replace('%m', 'mm').replace('%d', 'dd'), 
                                cfg.time_step, cfg.ts_quantity):
                            sys.exit()
                        del params_dict
                    else:
                        logging.error('ERROR:  File type {} is not supported'.format(cfg.output_aet['file_type']))
                        sys.exit()
            else:    # common parameter file
                file_path = os.path.join(cfg.daily_output_aet_ws, cfg.output_aet['name_format'])
                if cfg.output_aet['file_type'].lower() == 'xls' or cfg.output_aet['file_type'].lower() == 'wb':
                    ws_names = []
                    for field_name, param_df in cells.cell_daily_output_aet_data.items():
                        field_key = None
                        for fk, fn in cfg.output_aet['fields'].items():
                            if fn == field_name:
                                field_key = fk
                                break
                        if field_key is None:
                            logging.error('ERROR:  Unable to determine key for ' + field_name + ' posting daily aet output')
                            sys.exit()
                        ws_names.append(cfg.output_aet['wsspec'][field_key])
                    if os.path.isfile(file_path):
                        shutil.copyfile(file_path, file_path.replace('.xls', '_bu.xls'))
                    if not mod_dmis.wb_output_via_df_dict_openpyxl(
                            file_path, ws_names, cells.cell_daily_output_aet_data, 
                            cfg.output_aet['daily_float_format'], 
                            cfg.output_aet['daily_date_format'], 
                            cfg.time_step, cfg.ts_quantity):
                        sys.exit()
                else:    # text output
                    field_count = 0
                    for field_name, param_df in cells.cell_daily_output_aet_data.items():
                        field_count += 1
                        if field_count == 1:
                            params_df = param_df.copy()
                        else:
                            params_df = params_df.merge(param_df, left_index = True, right_index = True)
                    if cfg.output_aet['file_type'].lower() == 'csf': 
                         if not mod_dmis.csf_output_by_dataframe(file_path, cfg.output_aet['delimiter'], 
                            params_df, cfg.output_aet['daily_float_format'], 
                            cfg.output_aet['daily_date_format'], date_is_posted):
                            sys.exit()
                    elif cfg.output_aet['file_type'].lower() == 'rdb': 
                         if not mod_dmis.rdb_output_by_dataframe(file_path, cfg.output_aet['delimiter'], 
                            params_df, cfg.output_aet['daily_float_format'], 
                            cfg.output_aet['daily_date_format'], date_is_posted):
                            sys.exit()
                    else:
                        logging.error('ERROR:  File type {} is not supported'.format(cfg.output_aet['file_type']))
                        sys.exit()
            del cells.cell_daily_output_aet_data
        if cfg.monthly_output_aet_flag:
            if '%p' in cfg.output_aet['name_format']:    # individual parameter files
                for field_name, param_df in cells.cell_monthly_output_aet_data.items():
                    field_key = None
                    for fk, fn in cfg.output_aet['fields'].items():
                        if fn == field_name:
                            field_key = fk
                            break
                    if field_key is None:
                        logging.error('ERROR:  Unable to determine key for ' + field_name + ' posting daily aet output')
                        sys.exit()
                    file_path = os.path.join(cfg.monthly_output_aet_ws, 
                        cfg.output_aet['name_format'].replace('%p', cfg.output_aet['fnspec'][field_key]))
                    logging.debug('  monthly output path for {0} is {1}'.format(field_name, file_path))
                    if cfg.output_aet['file_type'].lower() == 'csf': 
                         if not mod_dmis.csf_output_by_dataframe(file_path, cfg.output_aet['delimiter'], 
                            param_df, cfg.output_aet['monthly_float_format'], 
                            cfg.output_aet['monthly_date_format'], date_is_posted):
                            sys.exit()
                    elif cfg.output_aet['file_type'].lower() == 'rdb': 
                         if not mod_dmis.rdb_output_by_dataframe(file_path, cfg.output_aet['delimiter'], 
                            param_df, cfg.output_aet['monthly_float_format'], 
                            cfg.output_aet['monthly_date_format'], date_is_posted):
                            sys.exit()
                    elif cfg.output_aet['file_type'].lower() == 'xls' or cfg.output_aet['file_type'].lower() == 'wb':
                        if os.path.isfile(file_path):
                            shutil.copyfile(file_path, file_path.replace('.xls', '_bu.xls'))
                        params_dict = {}
                        params_dict['[param_df'] = param_df
                        ws_names = []
                        ws_names.append(cfg.output_aet['wsspec'][field_key])
                        if not mod_dmis.wb_output_via_df_dict_openpyxl(
                                file_path, ws_names, params_dict,
                                cfg.output_aet['monthly_float_format'], 
                                cfg.output_aet['monthly_date_format'].replace('%Y','yyyy').replace('%m', 'mm').replace('%d', 'dd'), 
                                cfg.time_step, cfg.ts_quantity):
                            sys.exit()
                        del params_dict
                    else:
                        logging.error('ERROR:  File type {} is not supported'.format(cfg.output_aet['file_type']))
                        sys.exit()
            else:    # common parameter file
                file_path = os.path.join(cfg.monthly_output_aet_ws, cfg.output_aet['name_format'])
                if cfg.output_aet['file_type'].lower() == 'xls' or cfg.output_aet['file_type'].lower() == 'wb':
                    ws_names = []
                    for field_name, param_df in cells.cell_monthly_output_aet_data.items():
                        field_key = None
                        for fk, fn in cfg.output_aet['fields'].items():
                            if fn == field_name:
                                field_key = fk
                                break
                        if field_key is None:
                            logging.error('ERROR:  Unable to determine key for ' + field_name + ' posting daily aet output')
                            sys.exit()
                        ws_names.append(cfg.output_aet['wsspec'][field_key])
                    if os.path.isfile(file_path):
                        shutil.copyfile(file_path, file_path.replace('.xls', '_bu.xls'))
                    if not mod_dmis.wb_output_via_df_dict_openpyxl(
                            file_path, ws_names, cells.cell_monthly_output_aet_data, 
                            cfg.output_aet['monthly_float_format'], 
                            cfg.output_aet['monthly_date_format'], 
                            cfg.time_step, cfg.ts_quantity):
                        sys.exit()
                else:    # text output
                    field_count = 0
                    for field_name, param_df in cells.cell_monthly_output_aet_data.items():
                        field_count += 1
                        if field_count == 1:
                            params_df = param_df.copy()
                        else:
                            params_df = params_df.merge(param_df, left_index = True, right_index = True)
                    if cfg.output_aet['file_type'].lower() == 'csf': 
                         if not mod_dmis.csf_output_by_dataframe(file_path, cfg.output_aet['delimiter'], 
                            params_df, cfg.output_aet['monthly_float_format'], 
                            cfg.output_aet['monthly_date_format'], date_is_posted):
                            sys.exit()
                    elif cfg.output_aet['file_type'].lower() == 'rdb': 
                         if not mod_dmis.rdb_output_by_dataframe(file_path, cfg.output_aet['delimiter'], 
                            params_df, cfg.output_aet['monthly_float_format'], 
                            cfg.output_aet['monthly_date_format'], date_is_posted):
                            sys.exit()
                    else:
                        logging.error('ERROR:  File type {} is not supported'.format(cfg.output_aet['file_type']))
                        sys.exit()
            del cells.cell_monthly_output_aet_data
        if cfg.annual_output_aet_flag:
            if '%p' in cfg.output_aet['name_format']:    # individual parameter files
                for field_name, param_df in cells.cell_annual_output_aet_data.items():
                    field_key = None
                    for fk, fn in cfg.output_aet['fields'].items():
                        if fn == field_name:
                            field_key = fk
                            break
                    if field_key is None:
                        logging.error('ERROR:  Unable to determine key for ' + field_name + ' posting daily aet output')
                        sys.exit()
                    file_path = os.path.join(cfg.annual_output_aet_ws, 
                        cfg.output_aet['name_format'].replace('%p', cfg.output_aet['fnspec'][field_key]))
                    logging.debug('  annual output path for {0} is {1}'.format(field_name, file_path))
                    if cfg.output_aet['file_type'].lower() == 'csf': 
                         if not mod_dmis.csf_output_by_dataframe(file_path, cfg.output_aet['delimiter'], 
                            param_df, cfg.output_aet['annual_float_format'], 
                            cfg.output_aet['annual_date_format'], date_is_posted):
                            sys.exit()
                    elif cfg.output_aet['file_type'].lower() == 'rdb': 
                         if not mod_dmis.rdb_output_by_dataframe(file_path, cfg.output_aet['delimiter'], 
                            param_df, cfg.output_aet['annual_float_format'], 
                            cfg.output_aet['annual_date_format'], date_is_posted):
                            sys.exit()
                    elif cfg.output_aet['file_type'].lower() == 'xls' or cfg.output_aet['file_type'].lower() == 'wb':
                        if os.path.isfile(file_path):
                            shutil.copyfile(file_path, file_path.replace('.xls', '_bu.xls'))
                        params_dict = {}
                        params_dict['[param_df'] = param_df
                        ws_names = []
                        ws_names.append(cfg.output_aet['wsspec'][field_key])
                        if not mod_dmis.wb_output_via_df_dict_openpyxl(
                                file_path, ws_names, params_dict,
                                cfg.output_aet['annual_float_format'], 
                                cfg.output_aet['annual_date_format'].replace('%Y','yyyy').replace('%m', 'mm').replace('%d', 'dd'), 
                                cfg.time_step, cfg.ts_quantity):
                            sys.exit()
                        del params_dict
                    else:
                        logging.error('ERROR:  File type {} is not supported'.format(cfg.output_aet['file_type']))
                        sys.exit()
            else:    # common parameter file
                file_path = os.path.join(cfg.annual_output_aet_ws, cfg.output_aet['name_format'])
                if cfg.output_aet['file_type'].lower() == 'xls' or cfg.output_aet['file_type'].lower() == 'wb':
                    ws_names = []
                    for field_name, param_df in cells.cell_annual_output_aet_data.items():
                        field_key = None
                        for fk, fn in cfg.output_aet['fields'].items():
                            if fn == field_name:
                                field_key = fk
                                break
                        if field_key is None:
                            logging.error('ERROR:  Unable to determine key for ' + field_name + ' posting daily aet output')
                            sys.exit()
                        ws_names.append(cfg.output_aet['wsspec'][field_key])
                    if os.path.isfile(file_path):
                        shutil.copyfile(file_path, file_path.replace('.xls', '_bu.xls'))
                    if not mod_dmis.wb_output_via_df_dict_openpyxl(
                            file_path, ws_names, cells.cell_annual_output_aet_data, 
                            cfg.output_aet['annual_float_format'], 
                            cfg.output_aet['annual_date_format'], 
                            cfg.time_step, cfg.ts_quantity):
                        sys.exit()
                else:    # text output
                    field_count = 0
                    for field_name, param_df in cells.cell_annual_output_aet_data.items():
                        field_count += 1
                        if field_count == 1:
                            params_df = param_df.copy()
                        else:
                            params_df = params_df.merge(param_df, left_index = True, right_index = True)
                    if cfg.output_aet['file_type'].lower() == 'csf': 
                         if not mod_dmis.csf_output_by_dataframe(file_path, cfg.output_aet['delimiter'], 
                            params_df, cfg.output_aet['annual_float_format'], 
                            cfg.output_aet['annual_date_format'], date_is_posted):
                            sys.exit()
                    elif cfg.output_aet['file_type'].lower() == 'rdb': 
                         if not mod_dmis.rdb_output_by_dataframe(file_path, cfg.output_aet['delimiter'], 
                            params_df, cfg.output_aet['annual_float_format'], 
                            cfg.output_aet['annual_date_format'], date_is_posted):
                            sys.exit()
                    else:
                        logging.error('ERROR:  File type {} is not supported'.format(cfg.output_aet['file_type']))
                        sys.exit()
            del cells.cell_annual_output_aet_data

    if cfg.output_cir_flag and cfg.output_cir['data_structure_type'].upper() <> 'SF P':
        # post cir output data
        
        logging.info("\nPosting non 'SF P' output cir data")
        if 'date' in cfg.output_cir['fields'] and cfg.output_cir['fields'] is not None:
            date_is_posted = True
        else:
            date_is_posted = False
        if cfg.daily_output_cir_flag:
            if '%' in cfg.output_cir['name_format']:
               logging.debug('  ERROR: No wildcards are allowed in CIR name format')
               sys.exit()
            else:
                file_path = os.path.join(cfg.daily_output_cir_ws, cfg.output_cir['name_format'])
            if cfg.output_cir['file_type'].lower() == 'csf': 
                 if not mod_dmis.csf_output_by_dataframe(file_path, cfg.output_cir['delimiter'], 
                    cells.etcDailyCropIRs_df, cfg.output_cir['daily_float_format'], 
                    cfg.output_cir['daily_date_format'], date_is_posted):
                    sys.exit()
            elif cfg.output_cir['file_type'].lower() == 'rdb': 
                 if not mod_dmis.rdb_output_by_dataframe(file_path, cfg.output_cir['delimiter'], 
                    cells.etcDailyCropIRs_df, cfg.output_cir['daily_float_format'], 
                    cfg.output_cir['daily_date_format'], date_is_posted):
                    sys.exit()
            elif cfg.output_cir['file_type'].lower() == 'xls' or cfg.output_cir['file_type'].lower() == 'wb':
                if os.path.isfile(file_path):
                    shutil.copyfile(file_path, file_path.replace('.xls', '_bu.xls'))
                params_dict = {}
                params_dict['[param_df'] = param_df
                ws_names = []
                ws_names.append(cfg.output_cir['wsspec'][field_key])
                if not mod_dmis.wb_output_via_df_dict_openpyxl(
                        file_path, ws_names, params_dict,
                        cfg.output_cir['daily_float_format'], 
                        cfg.output_cir['daily_date_format'].replace('%Y','yyyy').replace('%m', 'mm').replace('%d', 'dd'), 
                        cfg.time_step, cfg.ts_quantity):
                    sys.exit()
                del params_dict
            else:
                logging.error('ERROR:  File type {} is not supported'.format(cfg.output_cir['file_type']))
                sys.exit()
            del cells.etcDailyCropIRs_df
        if cfg.monthly_output_cir_flag:
            if '%' in cfg.output_cir['name_format']:
               logging.debug('  ERROR: No wildcards are allowed in CIR name format')
               sys.exit()
            else:
                file_path = os.path.join(cfg.monthly_output_cir_ws, cfg.output_cir['name_format'])
            if cfg.output_cir['file_type'].lower() == 'csf': 
                 if not mod_dmis.csf_output_by_dataframe(file_path, cfg.output_cir['delimiter'], 
                    cells.etcMonthlyCropIRs_df, cfg.output_cir['monthly_float_format'], 
                    cfg.output_cir['monthly_date_format'], date_is_posted):
                    sys.exit()
            elif cfg.output_cir['file_type'].lower() == 'rdb': 
                 if not mod_dmis.rdb_output_by_dataframe(file_path, cfg.output_cir['delimiter'], 
                    cells.etcMonthlyCropIRs_df, cfg.output_cir['monthly_float_format'], 
                    cfg.output_cir['monthly_date_format'], date_is_posted):
                    sys.exit()
            elif cfg.output_cir['file_type'].lower() == 'xls' or cfg.output_cir['file_type'].lower() == 'wb':
                if os.path.isfile(file_path):
                    shutil.copyfile(file_path, file_path.replace('.xls', '_bu.xls'))
                params_dict = {}
                params_dict['[param_df'] = param_df
                ws_names = []
                ws_names.append(cfg.output_cir['wsspec'][field_key])
                if not mod_dmis.wb_output_via_df_dict_openpyxl(
                        file_path, ws_names, params_dict,
                        cfg.output_cir['monthly_float_format'], 
                        cfg.output_cir['monthly_date_format'].replace('%Y','yyyy').replace('%m', 'mm').replace('%d', 'dd'), 
                        cfg.time_step, cfg.ts_quantity):
                    sys.exit()
                del params_dict
            else:
                logging.error('ERROR:  File type {} is not supported'.format(cfg.output_cir['file_type']))
                sys.exit()
            del cells.etcMonthlyCropIRs_df
        if cfg.annual_output_cir_flag:
            if '%' in cfg.output_cir['name_format']:
               logging.debug('  ERROR: No wildcards are allowed in CIR name format')
               sys.exit()
            else:
                file_path = os.path.join(cfg.annual_output_cir_ws, cfg.output_cir['name_format'])
            if cfg.output_cir['file_type'].lower() == 'csf': 
                 if not mod_dmis.csf_output_by_dataframe(file_path, cfg.output_cir['delimiter'], 
                    cells.etcAnnualCropIRs_df, cfg.output_cir['annual_float_format'], 
                    cfg.output_cir['annual_date_format'], date_is_posted):
                    sys.exit()
            elif cfg.output_cir['file_type'].lower() == 'rdb': 
                 if not mod_dmis.rdb_output_by_dataframe(file_path, cfg.output_cir['delimiter'], 
                    cells.etcAnnualCropIRs_df, cfg.output_cir['annual_float_format'], 
                    cfg.output_cir['annual_date_format'], date_is_posted):
                    sys.exit()
            elif cfg.output_cir['file_type'].lower() == 'xls' or cfg.output_cir['file_type'].lower() == 'wb':
                if os.path.isfile(file_path):
                    shutil.copyfile(file_path, file_path.replace('.xls', '_bu.xls'))
                params_dict = {}
                params_dict['[param_df'] = param_df
                ws_names = []
                ws_names.append(cfg.output_cir['wsspec'][field_key])
                if not mod_dmis.wb_output_via_df_dict_openpyxl(
                        file_path, ws_names, params_dict,
                        cfg.output_cir['annual_float_format'], 
                        cfg.output_cir['annual_date_format'].replace('%Y','yyyy').replace('%m', 'mm').replace('%d', 'dd'), 
                        cfg.time_step, cfg.ts_quantity):
                    sys.exit()
                del params_dict
            else:
                logging.error('ERROR:  File type {} is not supported'.format(cfg.output_cir['file_type']))
                sys.exit()
            del cells.etcAnnualCropIRs_df

    if cfg.output_cet_flag and cfg.output_cet['data_structure_type'].upper() <> 'SF P':
        # post cet output data
        
        logging.info("\nPosting non 'SF P' output cet data")
        if 'date' in cfg.output_cet['fields'] and cfg.output_cet['fields'] is not None:
            date_is_posted = True
        else:
            date_is_posted = False
        if cfg.daily_output_cet_flag:
            if '%' in cfg.output_cir['name_format']:
               logging.debug('  ERROR: No wildcards are allowed in CET name format')
               sys.exit()
            else:
                file_path = os.path.join(cfg.daily_output_cet_ws, cfg.output_cet['name_format'])
            if cfg.output_cet['file_type'].lower() == 'csf': 
                 if not mod_dmis.csf_output_by_dataframe(file_path, cfg.output_cet['delimiter'], 
                    cells.etcDailyCropETs_df, cfg.output_cet['daily_float_format'], 
                    cfg.output_cet['daily_date_format'], date_is_posted):
                    sys.exit()
            elif cfg.output_cet['file_type'].lower() == 'rdb': 
                 if not mod_dmis.rdb_output_by_dataframe(file_path, cfg.output_cet['delimiter'], 
                    cells.etcDailyCropETs_df, cfg.output_cet['daily_float_format'], 
                    cfg.output_cet['daily_date_format'], date_is_posted):
                    sys.exit()
            elif cfg.output_cet['file_type'].lower() == 'xls' or cfg.output_cet['file_type'].lower() == 'wb':
                if os.path.isfile(file_path):
                    shutil.copyfile(file_path, file_path.replace('.xls', '_bu.xls'))
                params_dict = {}
                params_dict['[param_df'] = param_df
                ws_names = []
                ws_names.append(cfg.output_cet['wsspec'][field_key])
                if not mod_dmis.wb_output_via_df_dict_openpyxl(
                        file_path, ws_names, params_dict,
                        cfg.output_cet['daily_float_format'], 
                        cfg.output_cet['daily_date_format'].replace('%Y','yyyy').replace('%m', 'mm').replace('%d', 'dd'), 
                        cfg.time_step, cfg.ts_quantity):
                    sys.exit()
                del params_dict
            else:
                logging.error('ERROR:  File type {} is not supported'.format(cfg.output_cet['file_type']))
                sys.exit()
            del cells.etcDailyCropETs_df
        if cfg.monthly_output_cet_flag:
            if '%' in cfg.output_cir['name_format']:
               logging.debug('  ERROR: No wildcards are allowed in CET name format')
               sys.exit()
            else:
                file_path = os.path.join(cfg.monthly_output_cet_ws, cfg.output_cet['name_format'])
            if cfg.output_cet['file_type'].lower() == 'csf': 
                 if not mod_dmis.csf_output_by_dataframe(file_path, cfg.output_cet['delimiter'], 
                    cells.etcMonthlyCropETs_df, cfg.output_cet['monthly_float_format'], 
                    cfg.output_cet['monthly_date_format'], date_is_posted):
                    sys.exit()
            elif cfg.output_cet['file_type'].lower() == 'rdb': 
                 if not mod_dmis.rdb_output_by_dataframe(file_path, cfg.output_cet['delimiter'], 
                    cells.etcMonthlyCropETs_df, cfg.output_cet['monthly_float_format'], 
                    cfg.output_cet['monthly_date_format'], date_is_posted):
                    sys.exit()
            elif cfg.output_cet['file_type'].lower() == 'xls' or cfg.output_cet['file_type'].lower() == 'wb':
                if os.path.isfile(file_path):
                    shutil.copyfile(file_path, file_path.replace('.xls', '_bu.xls'))
                params_dict = {}
                params_dict['[param_df'] = param_df
                ws_names = []
                ws_names.append(cfg.output_cet['wsspec'][field_key])
                if not mod_dmis.wb_output_via_df_dict_openpyxl(
                        file_path, ws_names, params_dict,
                        cfg.output_cet['monthly_float_format'], 
                        cfg.output_cet['monthly_date_format'].replace('%Y','yyyy').replace('%m', 'mm').replace('%d', 'dd'), 
                        cfg.time_step, cfg.ts_quantity):
                    sys.exit()
                del params_dict
            else:
                logging.error('ERROR:  File type {} is not supported'.format(cfg.output_cet['file_type']))
                sys.exit()
            del cells.etcMonthlyCropETs_df
        if cfg.annual_output_cet_flag:
            if '%' in cfg.output_cir['name_format']:
               logging.debug('  ERROR: No wildcards are allowed in CET name format')
               sys.exit()
            else:
                file_path = os.path.join(cfg.annual_output_cet_ws, cfg.output_cet['name_format'])
            if cfg.output_cet['file_type'].lower() == 'csf': 
                 if not mod_dmis.csf_output_by_dataframe(file_path, cfg.output_cet['delimiter'], 
                    cells.etcAnnualCropETs_df, cfg.output_cet['annual_float_format'], 
                    cfg.output_cet['annual_date_format'], date_is_posted):
                    sys.exit()
            elif cfg.output_cet['file_type'].lower() == 'rdb': 
                 if not mod_dmis.rdb_output_by_dataframe(file_path, cfg.output_cet['delimiter'], 
                    cells.etcAnnualCropETs_df, cfg.output_cet['annual_float_format'], 
                    cfg.output_cet['annual_date_format'], date_is_posted):
                    sys.exit()
            elif cfg.output_cet['file_type'].lower() == 'xls' or cfg.output_cet['file_type'].lower() == 'wb':
                if os.path.isfile(file_path):
                    shutil.copyfile(file_path, file_path.replace('.xls', '_bu.xls'))
                params_dict = {}
                params_dict['[param_df'] = param_df
                ws_names = []
                ws_names.append(cfg.output_cet['wsspec'][field_key])
                if not mod_dmis.wb_output_via_df_dict_openpyxl(
                        file_path, ws_names, params_dict,
                        cfg.output_cet['annual_float_format'], 
                        cfg.output_cet['annual_date_format'].replace('%Y','yyyy').replace('%m', 'mm').replace('%d', 'dd'), 
                        cfg.time_step, cfg.ts_quantity):
                    sys.exit()
                del params_dict
            else:
                logging.error('ERROR:  File type {} is not supported'.format(cfg.output_cet['file_type']))
                sys.exit()
            del cells.etcAnnualCropETs_df
    logging.warning('\nAREAET Run Completed')
    logging.info('\n{} seconds'.format(clock()-clock_start))

def cell_mp(tup):
    """Pool multiprocessing friendly function

    mp.Pool needs all inputs are packed into single tuple
    Tuple is unpacked and and single processing version of function is called

    """
    return cell_sp(*tup)

def cell_sp(cell_count, cfg, cell, cells):
    """Compute area requirements for each cell
    Args:
        cell_count: count of cell being processed
        cfg (): configuration data
        cell (): ETCell instance
        cells (): AETCellsData instance
    """
    if not cell.crop_types_cycle(cell_count, cfg, cells): 
        sys.exit()
    if cell_count == 1:
        cfg.number_days = cfg.end_dt.to_julian_date() - cfg.start_dt.to_julian_date() + 1
        cfg.number_years = cfg.end_dt.year - cfg.start_dt.year + 1
    if not cell.read_cell_crop_mix(cfg):
        sys.exit()
    if not cell.compute_area_requirements(cell_count, cfg, cells):
        sys.exit()

def parse_args():  
    parser = argparse.ArgumentParser(
        description = 'Area ET',
        formatter_class = argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        '-i', '--ini', required = True, metavar = 'PATH',
        type = lambda x: is_valid_file(parser, x), help = 'Input file')
    parser.add_argument(
        '-d', '--debug', action = "store_true", default = False,
        help = "Save debug level comments to debug.txt")
    parser.add_argument(
        '-c', '--etcid', metavar = 'etcid_to_run', default = 'ALL',
        help = "User specified et cell id to run")
    parser.add_argument(
        '-v', '--verbose', action = "store_const",
        dest = 'log_level', const = logging.INFO, default = logging.WARNING,
        help = "Print info level comments")
    parser.add_argument(
        '-mp', '--multiprocessing', default = 1, type = int, 
        metavar = 'N', nargs = '?', const = mp.cpu_count(),
        help = 'Number of processers to use')
    args = parser.parse_args()
    
    # Convert INI path to an absolute path if necessary
    
    if args.ini and os.path.isfile(os.path.abspath(args.ini)):
        args.ini = os.path.abspath(args.ini)    
    return args

def is_valid_file(parser, arg):
    if not os.path.isfile(arg):
        parser.error('The file {} does not exist!'.format(arg))
    else:
        return arg

def is_valid_directory(parser, arg):
    if not os.path.isdir(arg):
        parser.error('The directory {} does not exist!'.format(arg))
    else:
        return arg
    
if __name__ == '__main__':
    args = parse_args()

    main(ini_path=args.ini, log_level = args.log_level, etcid_to_run = args.etcid, 
         debug_flag = args.debug, mp_procs = args.multiprocessing)
