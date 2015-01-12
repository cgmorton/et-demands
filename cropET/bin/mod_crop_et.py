#!/usr/bin/env python

import argparse
import math
import os
from pprint import pprint
import sys

import numpy as np

import crop_et_data
import crop_cycle
from process_climate import ProcessClimate
import util

VERBOSE=True

class cropET:
    def __init(self):
        """ """

VERBOSE = False
VERBOSE = True


def et_cells_cycle(data, basin_id, nsteps, ncells, OUT,
                   odir, refet_fmt, txt_pth):
    """ """
    et_cells = sorted(data.et_cells.keys())

    ## For testing, only process a subset of the cells
    if ncells:
        et_cells = et_cells[:ncells]

    ##
    for i,cell_id in enumerate(et_cells):
        # print i, cell_id
        print '\nRead Daily RefET Data:', data.et_cells[cell_id].refET_id 
        fn = refet_fmt % (data.et_cells[cell_id].refET_id)
        data.set_refet_data(fn)
        ## This impacts the long-term variables, like maincumGDD0LT & mainT30LT
        if not nsteps:
            nsteps=len(data.refet['ts'])  # full period of refet

        data.climate = ProcessClimate(data, cell_id, nsteps)
        #pprint(data.climate)
    
        crop_cycle.crop_cycle(data, cell_id, nsteps, basin_id, OUT, odir)


def main(basin_id='klamath', nsteps=0, ncells=0, OUT=None,
         odir='', refet_pth='', txt_pth=''):
    """ """
    data = crop_et_data._test(txt_pth)
    #pprint(data.refet)

    et_cells_cycle(data, basin_id, nsteps, ncells, OUT,
                   odir, refet_pth, txt_pth)
    #pprint(cropet_data)


if __name__ == '__main__':
    output_ws = os.path.join(os.getcwd(), 'cet')
    output_help = os.path.join('cwd', 'cet')
    refet_fmt = os.path.join(os.getcwd(), r'pmdata\ETo\%sE2.dat')
    refet_help = os.path.join('cwd', r'pmdata\ETo\%%sE2.dat')
    static_ws = os.path.join(os.getcwd(), r'static')
    static_help = os.path.join('cwd', r'static')
    
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
        '-t', '--static', metavar='PATH', default=static_ws, 
        help='static text workspace/path [%s]' % static_help)
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
         args.output, args.refet, args.static)
