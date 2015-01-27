#!/usr/bin/env python

import argparse
import logging
import os
from pprint import pprint
import sys

import numpy as np

import crop_et_data
import crop_cycle
import process_climate
import util

def main(basin_id='klamath', nsteps=0, ncells=0, OUT=None,
         output_ws='', refet_fmt='', txt_ws=''):
    """ """
    ## All data will be handled in this class
    data = crop_et_data.CropETData()

    ## Read in crop data from shapefile
    ##data.set_et_cells(
    ##    r'D:\Projects\NLDAS_Demands\texas\gis\nldas_4km\nldas_4km_albers_sub.shp')
    ##data.set_et_cells(os.path.join(txt_ws, 'ETCells.shp'))

    ## Read in cell properties, crops and cuttings
    data.set_et_cells_properties(os.path.join(txt_ws, 'ETCellsProperties.txt'))
    data.set_et_cells_crops(os.path.join(txt_ws, 'ETCellsCrops.txt'))
    data.set_mean_cuttings(os.path.join(txt_ws, 'MeanCuttings.txt'))
    ## Read in crop specific parameters and coefficients
    data.set_crop_parameters(os.path.join(txt_ws, 'CropParams.txt'))
    data.set_crop_coefficients(os.path.join(txt_ws, 'CropCoefs.txt'))
    ##pprint(cropet_data)
    
    ## For testing, only process a subset of the cells/stations
    if ncells:
        cell_id_list = cell_id_list[:ncells]

    ## Process each cell/station
    for cell_id, cell in sorted(data.et_cells.items()):
        logging.warning('CellID: {}'.format(cell_id))
        fn = refet_fmt % (cell.refET_id)

        ## Need to pass elevation to calculate pressure, ea, and Tdew
        cell.set_daily_nldas_data(fn)
        ##data.et_cells[cell_id].set_daily_refet_data(fn)
        ##pprint(data.refet)

        ## This impacts the long-term variables, like maincumGDD0LT & mainT30LT
        if not nsteps:
            nsteps = len(cell.refet['Dates'])  # full period of refet

        cell.climate = process_climate.process_climate(cell, nsteps)
        #pprint(data.climate)
    
        crop_cycle.crop_cycle(data, cell, nsteps, basin_id, OUT, output_ws)
        ##crop_cycle.crop_cycle(data, cell_id, nsteps, basin_id, OUT, output_ws)


if __name__ == '__main__':
    output_ws = os.path.join(os.getcwd(), 'cet')
    output_help = os.path.join('cwd', 'cet')
    refet_fmt = os.path.join(os.getcwd(), r'pmdata\ETo\%sE2.dat')
    refet_help = os.path.join('cwd', r'pmdata\ETo\%%sE2.dat')
    text_ws = os.path.join(os.getcwd(), r'static')
    text_help = os.path.join('cwd', r'static')
    
    ## Assume script is run in the "basin" folder
    parser = argparse.ArgumentParser(description='Crop ET Demands')
    parser.add_argument(
        '-b', '--basin_id', required=True, metavar='BASIN',
        ##default=os.path.basename(workspace),
        help='basin ID')
    parser.add_argument(
        '-c', '--ncells', default=0, metavar='N', type=int,
        help='Number of steps')
    parser.add_argument(
        '-n', '--nsteps', default=0, metavar='N', type=int,
        help='Number of cells')
    parser.add_argument(
        '-o', '--output',  metavar='PATH', default=output_ws,
        help='Output workspace/path [%s]' % output_help)
    parser.add_argument(
        '-r', '--refet', metavar='FMT', default=refet_fmt, 
        help='RefET data path formatter [%s]' % refet_help)
    parser.add_argument(
        '-t', '--text', metavar='PATH', default=text_ws, 
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

    ## Set logging verbosity level
    logging.basicConfig(level=args.log_level, format='%(message)s')

    ## Output control
    OUT = util.Output(args.output, DEBUG=False)
    ##OUT = util.Output(args.output, debug_flag=args.verbose)

    main(args.basin_id, args.nsteps, args.ncells, OUT,
         args.output, args.refet, args.text)
