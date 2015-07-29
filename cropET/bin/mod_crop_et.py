#!/usr/bin/env python

import argparse
import datetime
import logging
import os
import sys

import numpy as np

import crop_et_data
import crop_cycle
import util

def main(ini_path):
    """ Main function for running the Crop ET model

    Args:
        ini_path (str) - file path of the project INI file

    Returns:
        None
    """
    logging.warning('\nRunning Python ET-Demands')

    ## All data will be handled in this class
    data = crop_et_data.CropETData()

    ## Read in the INI file
    ## DEADBEEF - This could be called directly from the CropETData class
    data.read_ini(ini_path)

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

        ## Need to pass elevation to calculate pressure, ea, and Tdew
        cell.set_refet_data(data.refet_params)
        cell.set_weather_data(data.weather_params)

        ## Process climate arrays
        cell.process_climate(data.start_dt, data.end_dt)

        ## Run the model
        crop_cycle.crop_cycle(data, cell)

################################################################################

def parse_args():  
    parser = argparse.ArgumentParser(
        description='Crop ET-Demands',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        '-i', '--ini', required=True, metavar='PATH',
        type=lambda x: is_valid_file(parser, x), help='Input file')
    parser.add_argument(
        '--debug', action="store_true", default=False,
        help="Save debug level comments to debug.txt")
    parser.add_argument(
        '--verbose', action="store_const",
        dest='log_level', const=logging.INFO, default=logging.WARNING,   
        help="Print info level comments")
    args = parser.parse_args()
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

    ## Logging
    logger = logging.getLogger('')
    if args.debug:
        ## Log to file in debug mode
        logger.setLevel(logging.DEBUG)
        log_file = logging.FileHandler(
            os.path.join(os.getcwd(), 'debug.txt'), mode='w')
        log_file.setLevel(logging.DEBUG)
        log_file.setFormatter(logging.Formatter('%(message)s'))
        logger.addHandler(log_file)
        ## Force console logger to INFO if DEBUG
        args.log_level = logging.INFO
    else:
        logger.setLevel(args.log_level)
    ## Create console logger
    log_console = logging.StreamHandler(stream=sys.stdout)
    log_console.setLevel(args.log_level)
    log_console.setFormatter(logging.Formatter('%(message)s'))
    logger.addHandler(log_console)

    ##
    main(ini_path=args.ini)
