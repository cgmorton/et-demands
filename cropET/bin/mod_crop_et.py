#!/usr/bin/env python

import argparse
import os
from pprint import pprint
import sys

import numpy as np

import crop_et_data
import crop_cycle
import process_climate
import util

VERBOSE = True
VERBOSE = False

##class CropET:
##    def __init(self):
##        """ """

def et_cells_cycle(data, basin_id, nsteps, ncells, OUT,
                   output_ws, refet_fmt, text_ws):
    """ """
    et_cells = sorted(data.et_cells.keys())

    ## For testing, only process a subset of the cells/stations
    if ncells:
        et_cells = et_cells[:ncells]

    ## Process each cell/station
    for i, cell_id in enumerate(et_cells):
        # print i, cell_id
        print '\nRead Daily RefET Data:', data.et_cells[cell_id].refET_id 
        fn = refet_fmt % (data.et_cells[cell_id].refET_id)

        ## Need to pass elevation to calculate pressure, ea, and Tdew
        data.set_refet_data(fn, data.et_cells[cell_id].stn_elev)
        ##data.set_refet_data(fn, data.et_cells[cell_id].cell_elev)

        ## This impacts the long-term variables, like maincumGDD0LT & mainT30LT
        if not nsteps:
            nsteps = len(data.refet['ts'])  # full period of refet

        data.climate = process_climate.process_climate(data, cell_id, nsteps)
        #pprint(data.climate)
    
        crop_cycle.crop_cycle(data, cell_id, nsteps, basin_id, OUT, output_ws)


def main(basin_id='klamath', nsteps=0, ncells=0, OUT=None,
         output_ws='', refet_fmt='', txt_ws=''):
    """ """
    
    data = crop_et_data._test(txt_ws)
    #pprint(data.refet)

    et_cells_cycle(data, basin_id, nsteps, ncells, OUT,
                   output_ws, refet_fmt, txt_ws)
    #pprint(cropet_data)


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
        help='number of steps')
    parser.add_argument(
        '-n', '--nsteps', default=0, metavar='N', type=int,
        help='number of cells')
    parser.add_argument(
        '-o', '--output',  metavar='PATH', default=output_ws,
        help='output workspace/path [%s]' % output_help)
    parser.add_argument(
        '-r', '--refet', metavar='FMT', default=refet_fmt, 
        help='RefET data path formatter [%s]' % refet_help)
    parser.add_argument(
        '-t', '--text', metavar='PATH', default=text_ws, 
        help='static text workspace/path [%s]' % text_help)
    ##parser.add_argument(
    ##    '-d', '--debug', action="store_true", 
    ##    help="increase output verbosity")
    ##parser.add_argument(
    ##    '-v', '--verbose', action="store_true", 
    ##    help="increase output verbosity")
    args = parser.parse_args()

    ## Set logging verbosity level
    ##if args.verbose:
    ##    logging.basicConfig(level=logging.DEBUG, format='%(message)s')
    ##else:
    ##    logging.basicConfig(level=logging.INFO, format='%(message)s')

    ## Output control
    OUT = util.Output(args.output, DEBUG=False)
    ##OUT = util.Output(args.output, debug_flag=args.verbose)

    main(args.basin_id, args.nsteps, args.ncells, OUT,
         args.output, args.refet, args.text)
