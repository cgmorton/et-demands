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
import ret_utils
import ret_config
import met_nodes
import mod_dmis

def main(ini_path, log_level = logging.WARNING, mnid_to_run = 'ALL', 
        debug_flag = False, mp_procs = 1):
    """ Main function for running Reference ET model

    Args:
        ini_path (str): file path ofproject INI file
        log_level (logging.lvl): 
        mnid_to_run: Met node id to run in lieu of 'ALL'
        debug_flag (bool): If True, write debug level comments to debug.txt
        mp_procs (int): number of cores to use for multiprocessing

    Returns:
        None
    """
    clock_start = clock()
    
    # Start console logging immediately
    
    logger = ret_utils.console_logger(log_level = log_level)
    logging.warning('\nPython REFET')
    if debug_flag and mp_procs > 1:
        logging.warning('  Debug mode, disabling multiprocessing')
        mp_procs = 1
    if mp_procs > 1:
        logging.warning('  Multiprocessing mode, {0} cores'.format(mp_procs))

    # Read INI file

    cfg = ret_config.RefETConfig()
    cfg.read_refet_ini(ini_path, debug_flag)
 
    # Start file logging once INI file has been read in

    if debug_flag: logger = ret_utils.file_logger(logger, log_level = logging.DEBUG, output_ws = cfg.project_ws)

    # Read Met Nodes Meta Data
    
    mnd = met_nodes.MetNodesData()
    mnd.set_met_nodes_meta_data(cfg)

    # Read average monthly data

    mnd.read_avg_monthly_data(cfg)
    
    # Set up average monthly output if flagged
    
    if cfg.avg_monthly_met_flag:
        avg_monthly_header = 'Met Node ID,Met Node Name,Jan,Feb,Mar,Apr,May,Jun,Jul,Aug,Sep,Oct,Nov,Dec'
        if "xls" in cfg.input_met['avgm_tmax_path'].lower():
            avgTMaxRev_path = cfg.input_met['avgm_tmax_path'].replace(".xlsx", "avgTMaxMon.txt.").replace(".xls", "avgTMaxMon.txt.")
        else:
            avgTMaxRev_path = cfg.input_met['avgm_tmax_path'].replace(".", "_rev.")
        avgTMaxRev_hand = file(avgTMaxRev_path, 'w')
        avgTMaxRev_hand.write(avg_monthly_header + "\n")
        if "xls" in cfg.input_met['avgm_tmin_path'].lower():
            avgTMinRev_path = cfg.input_met['avgm_tmin_path'].replace(".xlsx", "avgTMinMon.txt.").replace(".xls", "avgTMinMon.txt.")
        else:
            avgTMinRev_path = cfg.input_met['avgm_tmin_path'].replace(".", "_rev.")
        avgTMinRev_hand = file(avgTMinRev_path, 'w')
        avgTMinRev_hand.write(avg_monthly_header + "\n")

    # Multiprocessing set up

    node_mp_list =  []
    node_mp_flag = False
    if mp_procs > 1:
        if not cfg.avg_monthly_met_flag:
            if cfg.output_met_flag and cfg.output_met['data_structure_type'].upper() <> 'SF P':
                logging.warning("Met output data structure type " + cfg.output_met['data_structure_type'] + 
                                " can not yet be created using multiple processing.")
                mp_procs = 1
            else:
                if mnid_to_run == 'ALL':
                    nodes_count = len(mnd.met_nodes_data.keys())
                    logging.warning('  nodes count: {}'.format(nodes_count))
                    if nodes_count > 1:
                        logging.warning("  Multiprocessing by node")
                        node_mp_flag = True
                else:
                    logging.warning("Multiprocessing can only be used for multiple nodes.")
                    mp_procs = 1
        else:
            logging.warning("Multiprocessing can not be used when posting average monthly data.")
            mp_procs = 1

    # loop thru met nodes meta data
    
    logging.warning("\n")
    met_node_count = 0
    for met_node_id, met_node in sorted(mnd.met_nodes_data.items()):
        if mnid_to_run == 'ALL' or mnid_to_run == met_node_id:
            logging.info('  Processing node id' + met_node_id + ' with name ' + met_node.met_node_name)
	    if met_node.TR_b0 is None: met_node.TR_b0 = cfg.input_met['TR_b0']
	    if met_node.TR_b1 is None: met_node.TR_b1 = cfg.input_met['TR_b1']
	    if met_node.TR_b2 is None: met_node.TR_b2 = cfg.input_met['TR_b2']
	    
	    # read input met data

            met_node_count += 1
            if node_mp_flag and cfg.output_met['data_structure_type'].upper() == 'SF P' and met_node_count > 1:
                node_mp_list.append([met_node_count, cfg, met_node, mnd])
            else:
                if not met_node.read_and_fill_met_data(met_node_count, cfg, mnd):
                    if cfg.avg_monthly_met_flag:
                        avgTMaxRev_hand.close()
                        avgTMinRev_hand.close()
                    sys.exit()
	    
                # calculate and post refet et and requested met output

                if cfg.refet_out_flag:
                    if not met_node.calculate_and_post_ret_data(cfg):
                        if cfg.avg_monthly_met_flag:
                            avgTMaxRev_hand.close()
                            avgTMinRev_hand.close()
                        sys.exit()
            
                # post updated average monthly temperatures if requested
            
                if cfg.avg_monthly_met_flag:
                    avgTMaxRev_string = met_node_id + cfg.input_met['avgm_tmax_delimitor'] + met_node.met_node_name
                    avgTMinRev_string = avgTMaxRev_string
                    for month, row in met_node.input_met_df.groupby(['month'])['tmax'].agg([np.mean]).iterrows():
                        avgTMaxRev_string = avgTMaxRev_string + cfg.input_met['avgm_tmax_delimitor'] + str(row['mean'])
                    for month, row in met_node.input_met_df.groupby(['month'])['tmin'].agg([np.mean]).iterrows():
 		        avgTMinRev_string = avgTMinRev_string + cfg.input_met['avgm_tmax_delimitor'] + str(row['mean'])
                    avgTMaxRev_hand.write(avgTMaxRev_string + "\n")
                    avgTMinRev_hand.write(avgTMinRev_string + "\n")
            
                # setup output met data posting

                if cfg.output_met_flag:
                    if not met_node.setup_output_met_data(met_node_count, cfg, mnd):
                        if cfg.avg_monthly_met_flag:
                            avgTMaxRev_hand.clos
                            avgTMinRev_hand.close()
                        sys.exit()
                del met_node.input_met_df
    if cfg.avg_monthly_met_flag:
        avgTMaxRev_hand.close()
        avgTMinRev_hand.close()

    # Multiprocess all nodes

    results = []
    if node_mp_list:
        pool = mp.Pool(mp_procs)
        results = pool.imap(node_mp, node_mp_list, chunksize = 1)
        pool.close()
        pool.join()
        del pool, results

    # post output with parameter orientation
    
    if cfg.output_met_flag and cfg.output_met['data_structure_type'].upper() <> 'SF P':
        # post optional met output data
        
        logging.info("\nPosting non 'SF P' output met data")
        if 'date' in cfg.output_met['fields'] and cfg.output_met['fields'] is not None:
            date_is_posted = True
        else:
            date_is_posted = False
        if cfg.daily_output_met_flag:
            if '%p' in cfg.output_met['name_format']:    # individual parameter files
                for field_name, param_df in mnd.mn_daily_output_met_data.items():
                    field_key = None
                    for fk, fn in cfg.output_met['fields'].items():
                        if fn == field_name:
                            field_key = fk
                            break
                    if field_key is None:
                        logging.error('ERROR  Unable to determine key for ' + field_name + ' posting daily met output')
                        sys.exit()
                    file_path = os.path.join(cfg.daily_output_met_ws, 
                        cfg.output_met['name_format'].replace('%p', cfg.output_met['fnspec'][field_key]))
                    logging.debug('  Daily output path for {0} is {1}'.format(field_name, file_path))
                    if cfg.output_met['file_type'].lower() == 'csf': 
                         if not mod_dmis.csf_output_by_dataframe(file_path, cfg.output_met['delimiter'], 
                            param_df, cfg.output_met['daily_float_format'], 
                            cfg.output_met['daily_date_format'], date_is_posted):
                            sys.exit()
                    elif cfg.output_met['file_type'].lower() == 'rdb': 
                         if not mod_dmis.rdb_output_by_dataframe(file_path, cfg.output_met['delimiter'], 
                            param_df, cfg.output_met['daily_float_format'], 
                            cfg.output_met['daily_date_format'], date_is_posted):
                            sys.exit()
                    elif cfg.output_met['file_type'].lower() == 'xls' or cfg.output_met['file_type'].lower() == 'wb':
                        if os.path.isfile(file_path):
                            shutil.copyfile(file_path, file_path.replace('.xls', '_bu.xls'))
                        params_dict = {}
                        params_dict['[param_df'] = param_df
                        ws_names = []
                        ws_names.append(cfg.output_met['wsspec'][field_key])
                        if not mod_dmis.wb_output_via_df_dict_openpyxl(
                                file_path, ws_names, params_dict, 
                                cfg.output_met['daily_float_format'], 
                                cfg.output_met['daily_date_format'].replace('%Y','yyyy').replace('%m', 'mm').replace('%d', 'dd'), 
                                cfg.time_step, cfg.ts_quantity):
                            sys.exit()
                    else:
                        logging.error('ERROR:  File type {} is not supported'.format(cfg.output_met['file_type']))
                        sys.exit()
            else:    # common parameter file
                file_path = os.path.join(cfg.daily_output_met_ws, cfg.output_met['name_format'])
                if cfg.output_met['file_type'].lower() == 'xls' or cfg.output_met['file_type'].lower() == 'wb':
                    ws_names = []
                    for field_name, param_df in mnd.mn_daily_output_met_data.items():
                        field_key = None
                        for fk, fn in cfg.output_met['fields'].items():
                            if fn == field_name:
                                field_key = fk
                                break
                        if field_key is None:
                            logging.error('ERROR:  Unable to determine key for ' + field_name + ' posting daily met output')
                            sys.exit()
                        ws_names.append(cfg.output_met['wsspec'][field_key])
                    if os.path.isfile(file_path):
                        shutil.copyfile(file_path, file_path.replace('.xls', '_bu.xls'))
                    if not mod_dmis.wb_output_via_df_dict_openpyxl(
                            file_path, ws_names, mnd.mn_daily_output_met_data, 
                            cfg.output_met['daily_float_format'], 
                            cfg.output_met['daily_date_format'], 
                            cfg.time_step, cfg.ts_quantity):
                        sys.exit()
                else:    # text output
                    field_count = 0
                    for field_name, param_df in mnd.mn_daily_output_met_data.items():
                        field_count += 1
                        if field_count == 1:
                            params_df = param_df.copy()
                        else:
                            # daily_refet_df = pd.merge(self.input_met_df, ret_df, left_index = True, right_index = True)
                            params_df = params_df.merge(param_df, left_index = True, right_index = True)
                    if cfg.output_met['file_type'].lower() == 'csf': 
                         if not mod_dmis.csf_output_by_dataframe(file_path, cfg.output_met['delimiter'], 
                            params_df, cfg.output_met['daily_float_format'], 
                            cfg.output_met['daily_date_format'], date_is_posted):
                            sys.exit()
                    elif cfg.output_met['file_type'].lower() == 'rdb': 
                         if not mod_dmis.rdb_output_by_dataframe(file_path, cfg.output_met['delimiter'], 
                            params_df, cfg.output_met['daily_float_format'], 
                            cfg.output_met['daily_date_format'], date_is_posted):
                            sys.exit()
                    else:
                        logging.error('ERROR:  File type {} is not supported'.format(cfg.output_met['file_type']))
                        sys.exit()
            del mnd.mn_daily_output_met_data
        if cfg.monthly_output_met_flag:
            if '%p' in cfg.output_met['name_format']:    # individual parameter files
                for field_name, param_df in mnd.mn_monthly_output_met_data.items():
                    field_key = None
                    for fk, fn in cfg.output_met['fields'].items():
                        if fn == field_name:
                            field_key = fk
                            break
                    if field_key is None:
                        logging.error('ERROR:  Unable to determine key for ' + field_name + ' posting daily met output')
                        sys.exit()
                    file_path = os.path.join(cfg.monthly_output_met_ws, 
                        cfg.output_met['name_format'].replace('%p', cfg.output_met['fnspec'][field_key]))
                    logging.debug('  monthly output path for {0} is {1}'.format(field_name, file_path))
                    if cfg.output_met['file_type'].lower() == 'csf': 
                         if not mod_dmis.csf_output_by_dataframe(file_path, cfg.output_met['delimiter'], 
                            param_df, cfg.output_met['monthly_float_format'], 
                            cfg.output_met['monthly_date_format'], date_is_posted):
                            sys.exit()
                    elif cfg.output_met['file_type'].lower() == 'rdb': 
                         if not mod_dmis.rdb_output_by_dataframe(file_path, cfg.output_met['delimiter'], 
                            param_df, cfg.output_met['monthly_float_format'], 
                            cfg.output_met['monthly_date_format'], date_is_posted):
                            sys.exit()
                    elif cfg.output_met['file_type'].lower() == 'xls' or cfg.output_met['file_type'].lower() == 'wb':
                        if os.path.isfile(file_path):
                            shutil.copyfile(file_path, file_path.replace('.xls', '_bu.xls'))
                        params_dict = {}
                        params_dict['[param_df'] = param_df
                        ws_names = []
                        ws_names.append(cfg.output_met['wsspec'][field_key])
                        if not mod_dmis.wb_output_via_df_dict_openpyxl(
                                file_path, ws_names, params_dict, 
                                cfg.output_met['monthly_float_format'], 
                                cfg.output_met['monthly_date_format'].replace('%Y','yyyy').replace('%m', 'mm').replace('%d', 'dd'), 
                                cfg.time_step, cfg.ts_quantity):
                            sys.exit()
                    else:
                        logging.error('ERROR:  File type {} is not supported'.format(cfg.output_met['file_type']))
                        sys.exit()
            else:    # common parameter file
                file_path = os.path.join(cfg.monthly_output_met_ws, cfg.output_met['name_format'])
                if cfg.output_met['file_type'].lower() == 'xls' or cfg.output_met['file_type'].lower() == 'wb':
                    ws_names = []
                    for field_name, param_df in mnd.mn_monthly_output_met_data.items():
                        field_key = None
                        for fk, fn in cfg.output_met['fields'].items():
                            if fn == field_name:
                                field_key = fk
                                break
                        if field_key is None:
                            logging.error('ERROR:  Unable to determine key for ' + field_name + ' posting daily met output')
                            sys.exit()
                        ws_names.append(cfg.output_met['wsspec'][field_key])
                    if os.path.isfile(file_path):
                        shutil.copyfile(file_path, file_path.replace('.xls', '_bu.xls'))
                    if not mod_dmis.wb_output_via_df_dict_openpyxl(
                            file_path, ws_names, mnd.mn_monthly_output_met_data, 
                            cfg.output_met['monthly_float_format'], 
                            cfg.output_met['monthly_date_format'], 
                            cfg.time_step, cfg.ts_quantity):
                        sys.exit()
                else:    # text output
                    field_count = 0
                    for field_name, param_df in mnd.mn_monthly_output_met_data.items():
                        field_count += 1
                        if field_count == 1:
                            params_df = param_df.copy()
                        else:
                            # monthly_refet_df = pd.merge(self.input_met_df, ret_df, left_index = True, right_index = True)
                            params_df = params_df.merge(param_df, left_index = True, right_index = True)
                    if cfg.output_met['file_type'].lower() == 'csf': 
                         if not mod_dmis.csf_output_by_dataframe(file_path, cfg.output_met['delimiter'], 
                            params_df, cfg.output_met['monthly_float_format'], 
                            cfg.output_met['monthly_date_format'], date_is_posted):
                            sys.exit()
                    elif cfg.output_met['file_type'].lower() == 'rdb': 
                         if not mod_dmis.rdb_output_by_dataframe(file_path, cfg.output_met['delimiter'], 
                            params_df, cfg.output_met['monthly_float_format'], 
                            cfg.output_met['monthly_date_format'], date_is_posted):
                            sys.exit()
                    else:
                        logging.error('ERROR:  File type {} is not supported'.format(cfg.output_met['file_type']))
                        sys.exit()
            del mnd.mn_monthly_output_met_data
        if cfg.annual_output_met_flag:
            if '%p' in cfg.output_met['name_format']:    # individual parameter files
                for field_name, param_df in mnd.mn_annual_output_met_data.items():
                    field_key = None
                    for fk, fn in cfg.output_met['fields'].items():
                        if fn == field_name:
                            field_key = fk
                            break
                    if field_key is None:
                        logging.error('ERROR:  Unable to determine key for ' + field_name + ' posting daily met output')
                        sys.exit()
                    file_path = os.path.join(cfg.annual_output_met_ws, 
                        cfg.output_met['name_format'].replace('%p', cfg.output_met['fnspec'][field_key]))
                    logging.debug('  annual output path for {0} is {1}'.format(field_name, file_path))
                    if cfg.output_met['file_type'].lower() == 'csf': 
                         if not mod_dmis.csf_output_by_dataframe(file_path, cfg.output_met['delimiter'], 
                            param_df, cfg.output_met['annual_float_format'], 
                            cfg.output_met['annual_date_format'], date_is_posted):
                            sys.exit()
                    elif cfg.output_met['file_type'].lower() == 'rdb': 
                         if not mod_dmis.rdb_output_by_dataframe(file_path, cfg.output_met['delimiter'], 
                            param_df, cfg.output_met['annual_float_format'], 
                            cfg.output_met['annual_date_format'], date_is_posted):
                            sys.exit()
                    elif cfg.output_met['file_type'].lower() == 'xls' or cfg.output_met['file_type'].lower() == 'wb':
                        if os.path.isfile(file_path):
                            shutil.copyfile(file_path, file_path.replace('.xls', '_bu.xls'))
                        params_dict = {}
                        params_dict['[param_df'] = param_df
                        ws_names = []
                        ws_names.append(cfg.output_met['wsspec'][field_key])
                        if not mod_dmis.wb_output_via_df_dict_openpyxl(
                                file_path, ws_names, params_dict, 
                                cfg.output_met['annual_float_format'], 
                                cfg.output_met['annual_date_format'].replace('%Y','yyyy').replace('%m', 'mm').replace('%d', 'dd'), 
                                cfg.time_step, cfg.ts_quantity):
                            sys.exit()
                    else:
                        logging.error('ERROR:  File type {} is not supported'.format(cfg.output_met['file_type']))
                        sys.exit()
            else:    # common parameter file
                file_path = os.path.join(cfg.annual_output_met_ws, cfg.output_met['name_format'])
                if cfg.output_met['file_type'].lower() == 'xls' or cfg.output_met['file_type'].lower() == 'wb':
                    ws_names = []
                    for field_name, param_df in mnd.mn_annual_output_met_data.items():
                        field_key = None
                        for fk, fn in cfg.output_met['fields'].items():
                            if fn == field_name:
                                field_key = fk
                                break
                        if field_key is None:
                            logging.error('ERROR:  Unable to determine key for ' + field_name + ' posting daily met output')
                            sys.exit()
                        ws_names.append(cfg.output_met['wsspec'][field_key])
                    if os.path.isfile(file_path):
                        shutil.copyfile(file_path, file_path.replace('.xls', '_bu.xls'))
                    if not mod_dmis.wb_output_via_df_dict_openpyxl(
                            file_path, ws_names, mnd.mn_annual_output_met_data, 
                            cfg.output_met['annual_float_format'], 
                            cfg.output_met['annual_date_format'], 
                            cfg.time_step, cfg.ts_quantity):
                        sys.exit()
                else:    # text output
                    field_count = 0
                    for field_name, param_df in mnd.mn_annual_output_met_data.items():
                        field_count += 1
                        if field_count == 1:
                            params_df = param_df.copy()
                        else:
                            # annual_refet_df = pd.merge(self.input_met_df, ret_df, left_index = True, right_index = True)
                            params_df = params_df.merge(param_df, left_index = True, right_index = True)
                    if cfg.output_met['file_type'].lower() == 'csf': 
                         if not mod_dmis.csf_output_by_dataframe(file_path, cfg.output_met['delimiter'], 
                            params_df, cfg.output_met['annual_float_format'], 
                            cfg.output_met['annual_date_format'], date_is_posted):
                            sys.exit()
                    elif cfg.output_met['file_type'].lower() == 'rdb': 
                         if not mod_dmis.rdb_output_by_dataframe(file_path, cfg.output_met['delimiter'], 
                            params_df, cfg.output_met['annual_float_format'], 
                            cfg.output_met['annual_date_format'], date_is_posted):
                            sys.exit()
                    else:
                        logging.error('ERROR:  File type {} is not supported'.format(cfg.output_met['file_type']))
                        sys.exit()
            del mnd.mn_annual_output_met_data
    logging.warning('\nREFET Run Completed')
    logging.info('\n{} seconds'.format(clock()-clock_start))

def node_mp(tup):
    """Pool multiprocessing friendly function

    mp.Pool needs all inputs are packed into single tuple
    Tuple is unpacked and and single processing version of function is called
    """
    return node_sp(*tup)

def node_sp(met_node_count, cfg, met_node, mnd):
    """Compute output for each node
    Args:
        met_node_count: count of node being processed
        cfg (): configuration data
        met_node (): MetNode instance
        mnd (): MetNodesData instance
    """
    if not met_node.read_and_fill_met_data(met_node_count, cfg, mnd):
        sys.exit()
	    
    # calculate and post refet et and requested met output

    if cfg.refet_out_flag:
        if not met_node.calculate_and_post_ret_data(cfg):
            sys.exit()
            
    # setup output met data posting

    if cfg.output_met_flag:
        if not met_node.setup_output_met_data(met_node_count, cfg, mnd):
            sys.exit()
    del met_node.input_met_df

def parse_args():  
    parser = argparse.ArgumentParser(
        description = 'Reference ET',
        formatter_class = argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        '-i', '--ini', required = True, metavar = 'PATH',
        type = lambda x: is_valid_file(parser, x), help = 'Input file')
    parser.add_argument(
        '-d', '--debug', action = "store_true", default = False,
        help = "Save debug level comments to debug.txt")
    parser.add_argument(
        '-m', '--metid', metavar = 'mnid_to_run', default='ALL',
        help = "User specified met node id to run")
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

    main(ini_path=args.ini, log_level = args.log_level, mnid_to_run = args.metid, 
         debug_flag = args.debug, mp_procs = args.multiprocessing)
