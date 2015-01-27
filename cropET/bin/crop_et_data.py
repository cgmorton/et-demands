#!/usr/bin/env python

import datetime
import os
from pprint import pprint
import sys

import numpy as np

import crop_parameters
import crop_coefficients
import et_cell

class CropETData():
    climate = None

    def __init__(self):
        """ """
        self.et_cells = {}

    def __str__(self):
        """ """
        return '<Cropet_data>'
    
    def set_et_cells(self, fn):
        """ Read ET cell properties, crops, and cuttings from a shapefile """
        field_list = [f.name for f in arcpy.ListFields(fn)]
        print field_list
        ##crop_list = [f for f in field_list if f.startswith('CROP_')]
        print crop_list
        crop_flag_list = [
            i for i in range(1,81,1) if 'CROP_{0:02d}'.format(i) in field_list]
        print crop_flag_list
        with arcpy.da.UpdateCursor(fn, "*") as u_cursor:
            for row in u_cursor:        
                ##self.cell_id = data[0]
                ##self.cell_name = data[1]
                ##self.refET_id = data[2]    # met_id ??
                self.stn_lat = float(row[field_list.index('LAT')])
                self.stn_lon = float(row[field_list.index('LON')])
                self.stn_elev = float(row[field_list.index('ELEV')])
                self.permeability = float(row[field_list.index('PERMEABIL')])
                self.stn_whc = float(row[field_list.index('AWC')])
                self.stn_soildepth = float(row[field_list.index('SOIL_DEPTH')])
                self.stn_hydrogroup_str = row[field_list.index('HYDGRP')]
                self.stn_hydrogroup = int(row[field_list.index('HYDGRP_NUM')])
                self.aridity_rating = float(row[field_list.index('ARIDITY')])
                ##self.refET_path = data[12]
                ####self.area = data[13]
                ####self.huc = data[13]
                ####self.huc_name = data[14]
                self.cell_lat = float(row[field_list.index('LAT')])
                self.cell_lon = float(row[field_list.index('LON')])
                self.cell_elev = float(row[field_list.index('ELEV')])
                self.irrigation_flag = int(row[field_list.index('IRRIG_FLAG')])
                self.crop_flags = crop_flag_list.astype(bool)
                self.ncrops = len(self.crop_flags)
                self.cuttingsLat = float(row[field_list.index('LAT')])
                self.dairy_cuttings = int(row[field_list.index('DAIRY_CUT')])
                self.beef_cuttings = int(row[field_list.index('BEEF_CUT')])

    def set_et_cells_properties(self, fn='ETCellsProperties.txt',
                                delimiter='\t'):
        """Extract the ET cell property data from the text file

        This function will build the ETCell objects and must be run first.

        Args:
            fn: file path  of the ET cell properties text file
            delimiter: string of the file delimiter value
        Returns:
            None
        """
        a = np.loadtxt(fn, delimiter=delimiter, dtype='str')
        ## Klamath has one header, other has two lines
        if a[0,0] == 'ET Cell ID':
            a = a[1:]
        else:
            a = a[2:]
        for i, row in enumerate(a):
            obj = et_cell.ETCell()
            obj.init_properties_from_row(row)
            obj.source_file_properties = fn
            self.et_cells[obj.cell_id] = obj

    def set_et_cells_crops(self, fn='ETCellsCrops.txt', delimiter='\t'):
        """Extract the ET cell crop data from the text file

        Args:
            fn: file path  of the ET cell crops text file
            delimiter: string of the file delimiter value
        Returns:
            None
        """
        a = np.loadtxt(fn, delimiter=delimiter, dtype='str')
        crop_numbers = a[1,4:].astype(int)
        crop_names = a[2,4:]
        a = a[3:]
        for i,row in enumerate(a):
            cell_id = row[0]
            if cell_id not in self.et_cells:
                logging.error(
                    'read_et_cells_crops(), cell_id %s not found' % cell_id)
                sys.exit()
            obj = self.et_cells[cell_id]
            obj.init_crops_from_row(row)
            obj.source_file_crop = fn
            obj.crop_names = crop_names
            obj.crop_numbers = crop_numbers
            i = (obj.crop_numbers*obj.crop_flags).nonzero()
            obj.num_crop_sequence = obj.crop_numbers[i]
            obj.crop_numbers = crop_numbers

    def set_mean_cuttings(self, fn='MeanCuttings.txt', delimiter='\t',
                          skip_rows=2):
        """Extract the mean cutting data from the text file

        Args:
            fn: file path of the mean cuttings text file
            delimiter: string of the file delimiter value
            skip_rows: integer indicating the number of header rows to skip
        Returns:
            None
        """
        with open(fn, 'r') as fp:
            a = fp.readlines()
        a = a[skip_rows:]
        for i, line in enumerate(a):
            row = line.split(delimiter)
            cell_id = row[1]
            #print cell_id
            if cell_id not in self.et_cells.keys():
                logging.error(
                    'read_mean_cuttings(), cell_id %s not found' % cell_id)
                sys.exit()
            obj = self.et_cells[cell_id]
            obj.init_cuttings_from_row(row)
            ##obj.source_file_cuttings = fn
            ##self.et_cells[cell_id] = obj

    def set_crop_parameters(self, fn=''):
        """ List of <CropParameter> instances """
        self.crop_parameters = crop_parameters.read_crop_parameters(fn)
        #pprint(vars(self.crop_parameters[0]))
    
    def set_crop_coefficients(self, fn=''):
        """ List of <CropCoeff> instances """
        self.crop_coeffs = crop_coefficients.read_crop_coefs(fn)
        #pprint(vars(self.crop_coeffs[0]))

    # options from the KLPenmanMonteithManager.txt, or PMControl spreadsheet
    ctrl = {
        #' set refETType to 0 for grass ETo,  1 for alfalfa ETr
        #' refETType impacts adjustment of Kcb for climate (ETo basis is adjusted, ETr basis is not)
        #' refETType also impacts value for Kcmax
        'refETType' : 0,  #  0 for Klamath

        ### from PenmanMonteithManager & modPM.vb
        'alfalfa1Reducer' : 0.9,
        # for cropOneToggle '0 sets crop 1 to alfalfa peak with no cuttings; 1 sets crop 1 to nonpristine alfalfa w/cuttings.
        'cropOneToggle' : 1,  

        # also in crop_parameters.py
        'CGDDWinterDoy' : 274,
        'CGDDMainDoy' : 1}

##def get_date_params(date_str='1/1/1950', date_fmt='%m/%d/%Y'):
##    dt = datetime.strptime(date_str, date_fmt)
##    return dt.year, dt.month, dt.day, dt.timetuple().tm_yday

  
##def read_cell_txt_files(static_ws=os.getcwd()):
##    """ """
##    if not os.path.isdir(static_ws):
##        raise SystemExit()
##    cet = CropETData()
##
##    # Init cells with property info
##    fn = os.path.join(static_ws, 'ETCellsProperties.txt')
##    print '\nRead Cell Properties:', fn
##    et_cells = et_cell.read_et_cells_properties(fn)
##
##    # Add the crop to cells
##    fn = os.path.join(static_ws, 'ETCellsCrops.txt')
##    print '\nRead Cell crops:', fn
##    et_cell.read_et_cells_crops(fn, et_cells)
##
##    # Add mean cuttings
##    fn = os.path.join(static_ws, 'MeanCuttings.txt')
##    print '\nRead mean cuttings:', fn
##    et_cell.read_mean_cuttings(fn, et_cells)
##    cet.set_et_cells(et_cells)
##
##    fn = os.path.join(static_ws, 'CropParams.txt')
##    print '\nRead Crop Parameters:', fn
##    cet.set_crop_parameters(fn)
##
##    fn = os.path.join(static_ws, 'CropCoefs.txt')
##    print '\nRead Crop Coefficients:', fn
##    cet.set_crop_coefficients(fn)
##    return cet

if __name__ == '__main__':
    pass
    ##data = CropETData()
    ##data.set_et_cells_properties(os.path.join(txt_ws, 'ETCellsProperties.txt'))
    ##data.set_et_cells_crops(os.path.join(txt_ws, 'ETCellsCrops.txt'))
    ##data.set_mean_cuttings(os.path.join(txt_ws, 'MeanCuttings.txt'))
    ##data.set_crop_parameters(os.path.join(txt_ws, 'CropParams.txt'))
    ##data.set_crop_coefficients(os.path.join(txt_ws, 'CropCoefs.txt'))
