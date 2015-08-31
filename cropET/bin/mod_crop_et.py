#!/usr/bin/env python

import argparse
import datetime
import logging
import multiprocessing as mp
import os
import sys

import numpy as np
import pandas as pd

import crop_et_data
import crop_cycle
import util

def main(ini_path, log_level=logging.WARNING, 
         debug_flag=False, vb_flag=False,  mp_procs=1):
    """ Main function for running the Crop ET model

    Args:
        ini_path (str): file path of the project INI file
        log_level (logging.lvl): 
        debug_flag (bool): If True, write debug level comments to debug.txt
        vb_flag (bool): If True, mimic calculations in VB version of code
        mp_procs (int): number of cores to use

    Returns:
        None
    """
    ## Start console logging immediatly
    logger = util.console_logger(log_level=log_level)
    
    logging.warning('\nRunning Python ET-Demands')
    if vb_flag:
        logging.warning('Mimicking VB calculations')

    ## All data will be handled in this class
    data = crop_et_data.CropETData()
    
    ## Read in the INI file
    ## DEADBEEF - This could be called directly from the CropETData class
    data.read_ini(ini_path)
 
    ## Start file logging once the INI file has been read in
    if debug_flag:
        logger = util.file_logger(
            logger, log_level=logging.DEBUG, output_ws=data.project_ws)

    ## Read in cell properties, crops and cuttings
    ## DEADBEEF - These could be called directly from the CropETData class
    data.set_cell_properties(data.cell_properties_path)
    data.set_cell_crops(data.cell_crops_path)
    data.set_cell_cuttings(data.cell_cuttings_path)

    ## Process each cell/station
    for cell_id, cell in sorted(data.et_cells.items()):
        logging.warning('CellID: {}'.format(cell_id))

        ## DEADBEEF - The "cell" could inherit the "data" values instead
        ## Read in crop specific parameters and coefficients
        cell.set_crop_params(data.crop_params_path)
        cell.set_crop_coeffs(data.crop_coefs_path)

        ## DEADBEEF - The pandas dataframes could be inherited instead
        cell.set_refet_data(data.refet)
        cell.set_weather_data(data.weather)

        ## Process climate arrays
        cell.process_climate()
        cell.subset_weather_data(data.start_dt, data.end_dt)

        ## Run the model
        crop_cycle.crop_cycle(data, cell, debug_flag, vb_flag, mp_procs)

################################################################################

def parse_args():  
    parser = argparse.ArgumentParser(
        description='Crop ET-Demands',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        '-i', '--ini', required=True, metavar='PATH',
        type=lambda x: is_valid_file(parser, x), help='Input file')
    parser.add_argument(
        '-vb', '--vb', action="store_true", default=False,
        help="Mimic calculations in VB version of code")
    parser.add_argument(
        '-d', '--debug', action="store_true", default=False,
        help="Save debug level comments to debug.txt")
    parser.add_argument(
        '-v', '--verbose', action="store_const",
        dest='log_level', const=logging.INFO, default=logging.WARNING,   
        help="Print info level comments")
    parser.add_argument(
        '-mp', '--multiprocessing', default=1, type=int, 
        metavar='N', nargs='?', const=mp.cpu_count(),
        help='Number of processers to use')
    args = parser.parse_args()
    ## Convert INI path to an absolute path if necessary
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
    
################################################################################
if __name__ == '__main__':
    args = parse_args()

    main(ini_path=args.ini, log_level=args.log_level, debug_flag=args.debug,
         vb_flag=args.vb, mp_procs=args.multiprocessing)
