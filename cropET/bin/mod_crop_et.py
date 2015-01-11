#!/usr/bin/env python

import getopt
import math
from pprint import pprint
import sys

import numpy as np

import cropet_data
from crop_cycle import CropCycle
from process_climate import ProcessClimate
import util

VERBOSE=True

class cropET:

    def __init(self):
        """ """

VERBOSE = False
VERBOSE = True


def ETCellsCycle(data, basin_id, nsteps, ncells, OUT, odir, refet_msk, txt_pth):
    """ """
    #refETfn = 'DATA/EX/%s/pmdata/ETo/%sE2.dat'
    refETfn = refet_msk

    et_cells = data.et_cells.keys()
    et_cells.sort()
    # print et_cells
    #et_cells = et_cells[1:]
    #sys.exit()

    #et_cells = ['CB17040218A']

    ## for testing
    if ncells:
        et_cells = et_cells[:ncells]
    for i,cell_id in enumerate(et_cells):
        # print i, cell_id

        print '\nReadDailyRefETData', data.et_cells[cell_id].refET_id 
        #fn = 'DATA/EX/Klamath_pmdata/ETo/OR1571E2_KL_2020_S0.dat'  # 1
        #fn = 'DATA/EX/Klamath_pmdata/ETo/OR8007E2_KL_2020_S0.dat'  # 2
        #fn = 'DATA/EX/Klamath_pmdata/ETo/%sE2_KL_2020_S0.dat' % data.et_cells[cell_id].refET_id
        #fn = refETfn % (basin_id, data.et_cells[cell_id].refET_id)
        fn = refETfn % (data.et_cells[cell_id].refET_id)
        data.set_refet_data(fn)
        #sys.exit()

        ## this impacts the long-term variables, like maincumGDD0LT & mainT30LT
        if not nsteps:
            nsteps=len(data.refet['ts'])  # full period of refet
        #ntseps = 365
        #nsteps = 730
        # print nsteps

        data.climate = ProcessClimate(data, cell_id, nsteps)
        #pprint(data.climate)
    
        CropCycle(data, cell_id, nsteps, basin_id, OUT, odir)

        #sys.exit()



def main(basin_id='klamath', nsteps=0, ncells=0, OUT=None, odir='', refet_pth='', txt_pth=''):
    """ """
    data = cropet_data._test(basin_id, txt_pth)
    #sys.exit()
    #pprint(data.refet)

    ETCellsCycle(data, basin_id, nsteps, ncells, OUT, odir, refet_pth, txt_pth)

    #pprint(cropet_data)



use = '''
Usage: %s -[h] -b<basin_id>

    -b  <basin_id>, klamath, rioGrande, CVP, truckee, ...
    -h  help

'''
if __name__ == '__main__':

    def usage():
        sys.stderr.write(use % sys.argv[0])
        sys.exit(1)

    try:
        (opts, args) = getopt.getopt(sys.argv[1:], 'hb:n:o:c:r:t:')
    except getopt.error:
        usage()

    basin_id = ''
    odir = ''
    nsteps = 0
    ncells = 0
    refet_msk = ''
    txt_pth = ''
    for (opt,val) in opts:
        if opt == '-h':
            usage()
        elif opt == '-b':
            basin_id = val
        elif opt == '-n':
            nsteps = int(val)
        elif opt == '-c':
            ncells = int(val)
        elif opt == '-o':
            odir = val
        elif opt == '-r':
            refet_msk = val
        elif opt == '-t':
            txt_pth = val
        else:
            raise OptionError, opt
            usage()

    ## output control
    #OUT = util.Output('cet/%s' % basin_id, DEBUG=True)
    OUT = util.Output('cet/%s' % basin_id, DEBUG=False)

    main(basin_id, nsteps, ncells, OUT, odir, refet_msk, txt_pth)








