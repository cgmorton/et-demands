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


def read_et_cells_properties(fn=''):
    """ 
    read_et_cells_properties(ETCellIDs, ETCellNames, RefETIDs, station_lat, station_long, station_elevft, _
                             station_WHC, station_soildepth, station_HydroGroup, aridity_rating, refETPaths) Then

    # then calls
    read_et_cells_properties(etcIndices(), etcNames(), metIds(), lats(), longs(), elevs(), 
                             WHCs(), soilDepths(), HydroGroups(), aridityRatings(), refETPaths()

    ' #varies by ET cell, ie, huc8
    txt_KlamathMetAndDepletionNodes/ETCellsProperties.txt
    ET Cell ID^IET Cell Name^IRef ET MET ID^IMet Latitude^IMet Longitude^IMet Elevation (feet)^IArea weighted average Permeability - in/hr^IArea weighted average WHC - in/ft^IAverage soil depth - in^IHydrologic Group (A-C) (A='coarse'  B='medium')^IHydrologic Group  (1-3) (1='coarse'
    2='medium')^IAridity Rating (fromHuntington plus google)^IRef ET Data Path^IET Cell Latitude^IET Cell Longitude^IET Cell Elevation (feet)$
    Klamath_1^IWilliamson^IOR1571^I42.5833^I-121.8667^I4193.0000^I-999^I3.55^I60^IB^I2^I50^I^I42.9604^I-121.7570^I4203.0000$
    Klamath_2^ISprague^IOR8007^I42.4306^I-121.4892^I4483.0000^I-999^I2.25^I60^IB^I2^I50^I^I42.5008^I-121.3810^I4364.0000$
    Klamath_3^IUpper Klamath Lake^IOR1574^I42.7036^I-121.9953^I4180.0000^I-999^I3.23^I60^IB^I2^I50^I^I42.6167^I-122.0833^I4163.0000$


    # ETCellIDs, ETCellNames, RefETIDs, station_lat, station_long, station_elevft, _
    #  station_WHC, station_soildepth, station_HydroGroup, aridity_rating, refETPaths) 

    # these are all 1-d arrays, use nested dictionaries
    d = { ETCellID : { ETCellName : '', station_lat : '', ... }}
    # -OR-
    # class ETCell: with attributues
    """
    # klamath has one header, other has two lines
    a = np.loadtxt(fn, delimiter="\t", dtype='str')
    if a[0,0] == 'ET Cell ID':
        a = a[1:]
    else:
        a = a[2:]

    et_cells = {}
    for i,row in enumerate(a):
        #print i,row

        obj = ETCell()
        obj.init_properties_from_row(row)
        obj.source_file_properties = fn
        #pprint(vars(obj))
        #print i, obj

        #et_cells.append(obj)
        et_cells[obj.cell_id] = obj
        #sys.exit()

    return et_cells


def read_et_cells_crops(fn, et_cells={}):
    """
    read_et_cells_crops(CropsETCellIDs, cropFlags, station_irrigation_flag):

    # basically flags for each crop in CropParameters file
    txt_KlamathMetAndDepletionNodes/ETCellsCrops.txt
    """
    '''
    a = np.loadtxt(fn, delimiter="\t", dtype='str', skiprows=3)
    a = a[0:32,:]
    # replace empty fields
    b = np.where(a == '', '0', a)

    '''
    a = np.loadtxt(fn, delimiter="\t", dtype='str')
    crop_numbers = a[1,4:].astype(int)
    crop_names = a[2,4:]
    a = a[3:]

    for i,row in enumerate(a):
        #print i,row

        cell_id = row[0]
        #print cell_id
        if cell_id not in et_cells:
            print 'ReadETCellsCrops(), cell_id %s not found' % cell_id
            sys.exit()
        obj = et_cells[cell_id]
        obj.init_crops_from_row(row)
        obj.source_file_crop = fn
        obj.crop_names = crop_names
        obj.crop_numbers = crop_numbers
        i = (obj.crop_numbers*obj.crop_flags).nonzero()
        obj.num_crop_sequence = obj.crop_numbers[i]

        obj.crop_numbers = crop_numbers
        #pprint(vars(obj))
        #print i, obj

        #sys.exit()


def read_mean_cuttings(fn, et_cells={}):
    """
    # read into memory once
    If Not ReadMeanCuttingsGivenETCellID(ETCellIDs(ETCellCount), staLatitude, dcuttings, bcuttings)
    DATA/EX/ExampleData/Params/MeanCuttings.txt
        "Nevada final station file with many sites taken out (as of Jan 2, 2008).  
         This file contains first (temporary) numbers of cutting cycles for dairy 
         and beef hay, based on latitude.  R.Allen 4/1/08"                                   
        ETCell Name ET Cell ID  Lat noDairy noBeef  null    null            
        ET Cell 101 101 39.435  5   4   0   0   no dairy cuttings max   12
    """
    DELIMITER = '\t'
    skip = 2
    d = {}
    with open(fn) as fp:
      for i,line in enumerate(fp):
        #print i,line,
        if i < skip:
            continue
        row = line.split(DELIMITER)
        cell_id = row[1]
        #print cell_id
        if cell_id not in et_cells:
            print 'ReadMeanCuttings(), cell_id %s not found' % cell_id
            sys.exit()
        obj = et_cells[cell_id]
        obj.init_cuttings_from_row(row)
        obj.source_file_cuttings = fn
    return d



## Not used for CropET
def read_et_cells_crop_mix(fn, et_cells=[]):
    """
       DATA/EX/ExampleData/Params/ETCellsCropMix.txt
        Year    ET Cell ID/ET Index User Crop Name  Area or Percent Crop Number User Begin Month    User Begin Day  User End Month  User End Day
        9999    101 ALFALFA 3000    3   1   1   10  20
        9999    101 PASTURE 2000    15  1   1   12  31
        9999    101 CORN_GRAIN  5000    7   1   1   10  11
        9999    101 Total   10000   10000   NaN NaN NaN NaN
        9999    201 ALFALFA 3000    3   1   1   10  20

    # class ETCell: with attributues

    ====> used by modAreaET.vb to calculate actual area-based ET
    """

if __name__ == '__main__':
    project_ws = os.getcwd()
    static_ws = os.path.join(project_ws, 'static')
    
    # Initalize cells with property info
    fn = os.path.join(static_ws,'ETCellsProperties.txt')
    et_cells = read_et_cells_properties(fn)

    # Add the crop to cells
    fn = os.path.join(static_ws,'ETCellsCrops.txt')
    read_et_cells_crops(fn, et_cells)

    # Mean cuttings
    fn = os.path.join(static_ws,'MeanCuttings.txt')
    print '\nRead Mean Cuttings'
    read_mean_cuttings(fn, et_cells)

    #c = et_cells[0]
    c = et_cells.values()[0]
    pprint(vars(c))
    print c



