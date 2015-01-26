#!/usr/bin/env python

import datetime
import math
import os
from pprint import pprint
import sys
import time

import numpy as np

import crop_parameters
import crop_coefficients
import et_cell
import util

class CropETData:
    climate = None

    def __init__(self):
        self.et_cells = {}
        """ """

    def __str__(self):
        """ """
        s = '<Cropet_data>'
        return s
    
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
            skip_rows: integer indicating the number of header rows
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

    def set_refet_data(self, fn, cell_elev):
        """ Mapping refet output variables """
        self.refet = read_daily_nldas_data(fn, cell_elev)
        ##self.refet = read_daily_refet_data(fn)

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

def get_date_params(date_str='1/1/1950', date_fmt='%m/%d/%Y'):
    dt = datetime.strptime(date_str, date_fmt)
    return dt.year, dt.month, dt.day, dt.timetuple().tm_yday

def read_daily_refet_data(fn):
    """ 
    ' in modPM.vb, several different formats supported.
    ' #file per ETCell
    If Not ReadDailyRefETDataGivenPath(ETrPath, ETCellCount, TMaxArray, TMinArray, precipArray, sweArray, _
                               sdArray, srArray, windArray, dpArray, ETrArray, EToArray) Then
    DATA/EX/ExampleData/ETo/my101E2.dat
    Observed
    Station Coop No: 101       Lat:  39.44 Long: -118.81 Elev  3964 ft
    Monthly Wind Station Id:1007 Newlands  Monthly Ko Station Id:1007 Newlands  Computed at 02:27:30 PM  Tuesday, Dec 20, 2011
      mo  da  Yr  DoY   TMax   TMin  Precip  Snow  SDep EstRs EsWind EsTDew Penm48 PreTay ASCEr  ASCEg  85Harg
                         C     C     In*100 In*100  In  MJ/m2   m/s    C    mm/day mm/day mm/day mm/day mm/day 
       1   1  1950   1    12.7   -8.7    0     0     0    9.74   1.28  -7.7   0.98   0.16   1.85   1.11   1.19
       1   2  1950   2    14.3   -6.6    0     0     0    9.67   1.28  -5.6   1.03   0.17   1.92   1.15   1.30
       1   3  1950   3    -0.5  -19.8    0     0     0    9.74   1.28 -18.8   0.61   0.20   1.03   0.65   0.44

Klamath_pmdata/ETo/OR1571E2_KL_2020_S0.dat
Date    TMax    TMin    Precip  Snow    SDep    EstRs   EsWind  EsTDew  Penm48  PreTay  ASCEr   ASCEg   85Harg
    C   C   In*100  In*100  In  MJ/m2   m/s C   mm/day  mm/day  mm/day  mm/day  mm/day
1/1/1950 -1.655943 -14.90594 7.034732 0 0 7.7162696684745 1.43687307834625 -13.12652 0.381984510542489 0.0587799121198262 0.665315332840188 0.401054956936277 0.386316892227767
1/2/1950 -1.825944 -13.92594 3.085409 0 0 7.42927547945495 1.43687307834625 -12.14653 0.3694645610536 0.0782057303930262 0.612602954878387 0.375671086093519 0.386741543162141

    """

    sr = 2
    o = 1
    # for my101E2.dat example above
    #sr = 5
    #o = 4

    a = np.loadtxt(fn, dtype='str', skiprows=sr)

    ## may want to save the date field(s) as some point
    dates = a[:,0]
    a = a[:,o:].astype(float)

    ts = [ time.strptime(s, "%m/%d/%Y") for s in dates.tolist() ]
    # time.struct_time(tm_year=1950, tm_mon=1, tm_mday=3, tm_hour=0, tm_min=0,
    # tm_sec=0, tm_wday=1, tm_yday=3, tm_isdst=-1)

    d = {
         'TMax' : a[:,0], 'TMin' : a[:,1], 'Precip' :  a[:,2],                     
         'Snow' : a[:,3], 'SnowDepth' : a[:,4], 'EstRs' :  a[:,5],                     
         'Wind' : a[:,6], 'TDew' : a[:,7], 'Penman' :  a[:,8],                     
         'PreTay' : a[:,9], 'ASCEPMStdETr' : a[:,10], 'ASCEPMStdETo' : a[:,11],                     
         'Harg' : a[:,12], 'Dates': dates, 'ts': np.asarray(ts)                    
         }
    #for i,date in enumerate(dates[:10]):
    #    print i,date

    return d


def read_daily_nldas_data(fn, cell_elev):
    """

    Example of data file:
        Year,Month,Day,DOY,Tmin(K),Tmax(K),Specific Humidity(kg kg-1),
        Wind @ 10m (m s-1),Solar Radiation (W m-2),Precipitation (mm),
        ETo @ 2m (mm day-1),ETr @ 2m(mm day-1)
        1979,1,1,1,252.7,263.62,0.00028215,1.9643,143.58,0,0.5754,0.92938
        1979,1,2,2,252.24,267.21,0.00035664,0.80539,76.738,0,0.43268,0.64418
        1979,1,3,3,257.46,272.2,0.00073107,0.64853,89.89,0,0.45107,0.6639

    genfromtxt replaces spaces, hyphens, and paranethesis with underscores
    Field names become:
        Year,Month,Day,DOY,TminK,TmaxK,Specific_Humiditykg_kg1,
        Wind__10m_m_s1,Solar_Radiation_W_m2,Precipitation_mm,
        ETo__2m_mm_day1,ETr__2mmm_day1

    Args:
        fn: string 
    """

    a = np.genfromtxt(fn, delimiter=',', names=True)
    ##print a.dtype.names
 
    ## Original Field Names
    ##Year,Month,Day,DOY,Tmin(K),Tmax(K),
    ##Specific Humidity(kg kg-1),Wind @ 10m (m s-1),Solar Radiation (W m-2),
    ##Precipitation (mm),ETo @ 2m (mm day-1),ETr @ 2m(mm day-1)

    ## Modified Field Names
    ##Year,Month,Day,DOY,TminK,TmaxK,
    ##Specific_Humiditykg_kg1,Wind__10m_m_s1,Solar_Radiation_W_m2,
    ##Precipitation_mm,ETo__2m_mm_day1,ETr__2mmm_day1

    dates = ['{0}/{1}/{2}'.format(int(m),int(d),int(y))
             for y, m, d in zip(a['Year'], a['Month'], a['Day'])]
    time_array = np.array([time.strptime(s, "%m/%d/%Y") for s in dates])

    ## Convert temperatures from K to C
    a['TmaxK'] -= 273.15
    a['TminK'] -= 273.15

    ## Convert W/m2 to MJ/m2
    a['Solar_Radiation_W_m2'] *= 0.0864

    ## Scale wind from 10m to 2m
    a['Wind__10m_m_s1'] *= 4.87 / math.log(67.8 * 10 - 5.42)

    ## Calculate Tdew from specific humidity
    ## Convert station elevation from feet to meters
    pair = util.pair_func(0.3048 * cell_elev)
    ea = util.ea_from_q(pair, a['Specific_Humiditykg_kg1'])
    tdew = util.tdew_from_ea(ea)

    zero_array = np.zeros(a['TmaxK'].shape, dtype=np.float32)
    return {
         'TMax': a['TmaxK'], 'TMin': a['TminK'],
         'Precip': a['Precipitation_mm'],                     
         'Snow': zero_array,
         'SnowDepth': zero_array,
         'EstRs': a['Solar_Radiation_W_m2'],                     
         'Wind': a['Wind__10m_m_s1'],
         'TDew' : tdew,
         'ASCEPMStdETr': a['ETr__2mmm_day1'],
         'ASCEPMStdETo': a['ETo__2m_mm_day1'],                     
         ##'Penman' : zero_array,                     
         ##'PreTay' : zero_array,
         ##'Harg': zero_array,
         'Dates': dates,
         'ts': time_array                    
         }
  
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
    data = CropETData()
    data.set_et_cells_properties(os.path.join(txt_ws, 'ETCellsProperties.txt'))
    data.set_et_cells_crops(os.path.join(txt_ws, 'ETCellsCrops.txt'))
    data.set_mean_cuttings(os.path.join(txt_ws, 'MeanCuttings.txt'))
    data.set_crop_parameters(os.path.join(txt_ws, 'CropParams.txt'))
    data.set_crop_coefficients(os.path.join(txt_ws, 'CropCoefs.txt'))
