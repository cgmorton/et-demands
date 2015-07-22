#!/usr/bin/env python

import argparse
import logging
import os
from pprint import pprint
import sys

import numpy as np

import crop_et_data
import crop_cycle
import util

def main(basin_id, output_ws, refet_fmt, txt_ws, nsteps=0, ncells=0):
    """ Main function for running the Crop ET model

    Args:
        basin_id (str) - basin/project name
        output_ws (str) - folder path of the output file
        refet_fmt (str) - format of the RefET data.  
        txt_ws (str) - folder path of the input static text file
        nsteps (int): number of time steps to process
        ncells (int): number cells to process

    Returns:
        None
    """
    logging.info('ET-Demands')
    logging.debug('  Basin: {}'.format(basin_id))

    ## All data will be handled in this class
    data = crop_et_data.CropETData()

    ## Read in cell properties, crops and cuttings
    logging.debug('  Static workspace: {}'.format(txt_ws))
    data.static_cell_properties(os.path.join(txt_ws, 'ETCellsProperties.txt'))
    data.static_cell_crops(os.path.join(txt_ws, 'ETCellsCrops.txt'))
    data.static_mean_cuttings(os.path.join(txt_ws, 'MeanCuttings.txt'))

    ## For testing, only process a subset of the cells/stations
    if ncells:
        cell_id_list = cell_id_list[:ncells]

    ## Process each cell/station
    for cell_id, cell in sorted(data.et_cells.items()):
        logging.warning('CellID: {}'.format(cell_id))

        ## Read in crop specific parameters and coefficients
        cell.static_crop_params(os.path.join(txt_ws, 'CropParams.txt'))
        cell.static_crop_coeffs(os.path.join(txt_ws, 'CropCoefs.txt'))
    
        ## Need to pass elevation to calculate pressure, ea, and Tdew
        cell.set_daily_refet_data(refet_fmt % (cell.refET_id), skiprows=[1])
        ##cell.set_daily_nldas_data(refet_fmt % (cell.refET_id))

        ## This impacts the long-term variables, like main_cgdd_0_lt & main_t30_lt
        if not nsteps:
            nsteps = len(cell.refet['Dates'])  # full period of refet

        ## Process climate arrays
        cell.process_climate(nsteps)

        ## Run the model
        crop_cycle.crop_cycle(data, cell, nsteps, basin_id, output_ws)


if __name__ == '__main__':
    output_ws = os.path.join(os.getcwd(), 'cet')
    output_help = os.path.join('cwd', 'cet')
    ## What is the difference between refet_fmt and refet_help
    refet_fmt = os.path.join(os.getcwd(), r'pmdata\ETo\%sE2.dat')
    refet_help = os.path.join('cwd', r'pmdata\ETo\\%%sE2.dat')
    ## NLDAS Defaults
    ##refet_fmt = os.path.join(os.getcwd(), r'pmdata\ETo\NLDAS4km_%s.csv')
    ##refet_help = os.path.join('cwd', r'pmdata\ETo\NLDAS4km_%%s.csv')
    text_ws = os.path.join(os.getcwd(), r'static')
    text_help = os.path.join('cwd', r'static')
    
    ## Assume script is run in the "basin" folder
    parser = argparse.ArgumentParser(description='Crop ET Demands')
    parser.add_argument(
        '-b', '--basin_id', required=True, metavar='BASIN',
        ##default=os.path.basename(workspace),
        help='basin ID')
    parser.add_argument(
        '--ncells', default=0, metavar='N', type=int,
        help='Number of cells')
    parser.add_argument(
        '--nsteps', default=0, metavar='N', type=int,
        help='Number of cells')
    parser.add_argument(
        '--output',  metavar='PATH', default=output_ws,
        help='Output workspace/path [%s]' % output_help)
    parser.add_argument(
        '--refet', metavar='FMT', default=refet_fmt, 
        help='RefET data path formatter [%s]' % refet_help)
    parser.add_argument(
        '--text', metavar='PATH', default=text_ws, 
        help='Static text workspace/path [%s]' % text_help)
    parser.add_argument(
        '-d', '--debug', action="store_const",
        dest='log_level', const=logging.DEBUG, default=logging.WARNING,
        help="Print debug level comments")
    parser.add_argument(
        '-v', '--verbose', action="store_const",
        dest='log_level', const=logging.INFO,  
        help="Print info level comments")
    args = parser.parse_args()

    ## Convert relative paths to absolute paths
    if args.output and os.path.isdir(os.path.abspath(args.output)):
        args.output = os.path.abspath(args.output)
    if args.refet and os.path.isfile(os.path.abspath(args.refet)):
        args.refet = os.path.abspath(args.refet)
    if args.text and os.path.isfile(os.path.abspath(args.text)):
        args.text = os.path.abspath(args.text)

    ## Log to file in debug mode
    if args.log_level == logging.DEBUG:
        ## Create File Logger
        logging.basicConfig(
            level = logging.DEBUG, format='%(message)s', filemode='w', 
            filename = os.path.join(args.output, 'debug.txt'))
        ## Create Display Logger
        log_console = logging.StreamHandler()
        log_console.setLevel(args.log_level)
        log_console.setFormatter(logging.Formatter('%(message)s'))
        logging.getLogger('').addHandler(log_console)
    else:
        logging.basicConfig(level=args.log_level, format='%(message)s')

    ##
    main(basin_id=args.basin_id, output_ws=args.output,
         refet_fmt=args.refet, txt_ws=args.text,
         nsteps=args.nsteps, ncells=args.ncells)
         ##nsteps=args.nsteps, ncells=args.ncells, OUT=OUT)
