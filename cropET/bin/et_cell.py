#!/usr/bin/env python

import os
from pprint import pprint
import sys

import numpy as np

class ETCell:
    name = None

    def __init__(self):
        """ """

    def __str__(self):
        """ """
        # add any info to help in debugging, etc
        s = '<ETCell %s, %s %s>' % (self.cell_id, self.cell_name, self.refET_id)
        return s

    def init_properties_from_row(self, data):
        """ Parse the row of data
        """

        # ETCellIDs, ETCellNames, RefETIDs, station_lat, station_long, station_elevft, _
        #  station_WHC, station_soildepth, station_HydroGroup, aridity_rating, refETPaths) 

        #  info
        self.cell_id = data[0]
        self.cell_name = data[1]
        self.refET_id = data[2]    # met_id ??
        self.stn_lat = float(data[3])
        self.stn_lon = float(data[4])
        self.stn_elev = float(data[5])
        self.permeability = float(data[6])
        self.stn_whc = float(data[7])
        self.stn_soildepth = float(data[8])
        self.stn_hydrogroup_str = data[9]
        ## [140822] changed for RioGrande
        #self.stn_hydrogroup = int(data[10])
        self.stn_hydrogroup = int(eval(data[10]))
        self.aridity_rating = float(data[11])
        self.refET_path = data[12]
        #print data
        #print len(data)

        if len(data) == 14:       # CVP
            self.area = data[13]
        elif len(data) == 15:     # truckee
            self.huc = data[13]
            self.huc_name = data[14]
        elif len(data) > 13:
            self.cell_lat = float(data[13])
            self.cell_lon = float(data[14])
            self.cell_elev = float(data[15])

    def init_crops_from_row(self, data):
        """ Parse the row of data
        """
        #  info
        self.irrigation_flag = int(data[3])
        self.crop_flags = data[4:].astype(bool)
        self.ncrops = len(self.crop_flags)

    def init_cuttings_from_row(self, data):
        """ Parse the row of data
        """
        #  info
        self.cuttingsLat = float(data[2])
        self.dairy_cuttings = int(data[3])
        self.beef_cuttings = int(data[4])

    def read(self):
        """ Read from ETCell file 
            Eventually each crop stored in own text file...maybe.
        """
        print 'not implemented'

    def write(self, fn=''):
        """ Write individual ETCell file 
        """
        print 'not implemented'

if __name__ == '__main__':
    ##project_ws = os.getcwd()
    ##static_ws = os.path.join(project_ws, 'static')
    ##
    ### Initalize cells with property info
    ##fn = os.path.join(static_ws,'ETCellsProperties.txt')
    ##et_cells = read_et_cells_properties(fn)
    ##
    ### Add the crop to cells
    ##fn = os.path.join(static_ws,'ETCellsCrops.txt')
    ##read_et_cells_crops(fn, et_cells)
    ##
    ### Mean cuttings
    ##fn = os.path.join(static_ws,'MeanCuttings.txt')
    ##print '\nRead Mean Cuttings'
    ##read_mean_cuttings(fn, et_cells)
    ##
    ###c = et_cells[0]
    ##c = et_cells.values()[0]
    ##pprint(vars(c))
    ##print c
    pass
