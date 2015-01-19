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

#DELIMITER = ','
DELIMITER = '\t'

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

def pair_func(elevation):
    """Calculates air pressure as a function of elevation

    Args:
        elevation: NumPy array of elevations [m]

    Returns:
        NumPy array of air pressures [kPa]
    """
    return 101.3 * np.power((293.0 - 0.0065 * elevation) / 293.0, 5.26)

def ea_from_q(p, q):
    """Calculates vapor pressure from pressure and specific humidity

    Args:
        p: NumPy array of pressures [kPa]
        q: NumPy array of specific humidities [kg / kg]

    Returns:
        NumPy array of vapor pressures [kPa]
    """
    return p * q / (0.622 + 0.378 * q)

def tdew_from_ea(ea):
    """Calculates vapor pressure at a given temperature

    Args:
        temperature: NumPy array of temperatures [C]

    Returns:
        NumPy array of vapor pressures [kPa]
    """
    return (237.3 * np.log(ea / 0.6108)) / (17.27 - np.log(ea / 0.6108))


def read_daily_nldas_data(fn, cell_elev):
    """

    Year,Month,Day,DOY,Tmin(K),Tmax(K),Specific Humidity(kg kg-1),Wind @ 10m (m s-1),Solar Radiation (W m-2),Precipitation (mm),ETo @ 2m (mm day-1),ETr @ 2m(mm day-1)
    1979,1,1,1,252.7,263.62,0.00028215,1.9643,143.58,0,0.5754,0.92938
    1979,1,2,2,252.24,267.21,0.00035664,0.80539,76.738,0,0.43268,0.64418
    1979,1,3,3,257.46,272.2,0.00073107,0.64853,89.89,0,0.45107,0.6639

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

    ## Calculate Tdew from specific humidity
    ## Convert station elevation from feet to meters
    ea = ea_from_q(pair_func(0.3048 * cell_elev), a['Specific_Humiditykg_kg1'])
    tdew = tdew_from_ea(ea)

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
  

class CropETData:
    climate = None

    def __init__(self):
        """ """

    def __str__(self):
        """ """
        s = '<Cropet_data>'
        return s
    
    def set_et_cells(self, et_cells={}):
        """ Mapping of ET Cell instances keyed by ET Cell ID"""
        self.et_cells = et_cells

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

##def _test_old():
##    """ """
##    cet = Cropet_data()
##    print '\nRead Cell data'
##    # cell property files
##    fn = 'DATA/EX/txt_KlamathMetAndDepletionNodes/ETCellsProperties.txt'
##    # init cells with property info
##    et_cells = et_cell.read_et_cells_properties(fn)
##    # cell crop mix files
##    fn = 'DATA/EX/txt_KlamathMetAndDepletionNodes/ETCellsCrops.txt'
##    # add the crop to cells
##    et_cell.read_et_cells_crops(fn, et_cells)
##    # add mean cuttings
##    fn = 'DATA/EX/txt_KlamathMetAndDepletionNodes/MeanCuttings.txt'
##    et_cell.ReadMeanCuttings(fn, et_cells)
##    #c = et_cells.values()[0]
##    #pprint(vars(c))
##    #print c
##    cet.set_et_cells(et_cells)
##
##    print '\nReadCropParameters'
##    fn = 'DATA/EX/txt_KlamathMetAndDepletionNodes/CropParams.txt'
##    cet.set_crop_parameters(fn)
##    #print(cet.crop_parameters[0])
##
##    print '\nReadCropCoefficients'
##    fn = 'DATA/EX/txt_KlamathMetAndDepletionNodes/CropCoefs.txt'
##    cet.set_crop_coefficients(fn)
##    #print(coeff[0])
##    #pprint(ReadCropCoefs(fn))
##
##    '''
##    print '\nReadDailyRefETData' 
##    #fn = 'DATA/EX/Klamath_pmdata/ETo/OR1571E2_KL_2020_S0.dat'  # 1
##    #fn = 'DATA/EX/Klamath_pmdata/ETo/OR8007E2_KL_2020_S0.dat'  # 2
##    fn = 'DATA/EX/Klamath_pmdata/ETo/OR8007E2_KL_2020_S0.dat'  # 2
##    cet.set_refet_data(fn)
##    #pprint(ReadDailyRefETData(fn))
##    '''
##    return cet

def _test(static_ws=os.getcwd()):
    """ """
    if not os.path.isdir(static_ws):
        raise SystemExit()
    cet = CropETData()

    # Init cells with property info
    fn = os.path.join(static_ws, 'ETCellsProperties.txt')
    print '\nRead Cell Properties:', fn
    et_cells = et_cell.read_et_cells_properties(fn)

    # Add the crop to cells
    fn = os.path.join(static_ws, 'ETCellsCrops.txt')
    print '\nRead Cell crops:', fn
    et_cell.read_et_cells_crops(fn, et_cells)

    # Add mean cuttings
    fn = os.path.join(static_ws, 'MeanCuttings.txt')
    print '\nRead mean cuttings:', fn
    et_cell.read_mean_cuttings(fn, et_cells)
    cet.set_et_cells(et_cells)

    fn = os.path.join(static_ws, 'CropParams.txt')
    print '\nRead Crop Parameters:', fn
    cet.set_crop_parameters(fn)

    fn = os.path.join(static_ws, 'CropCoefs.txt')
    print '\nRead Crop Coefficients:', fn
    cet.set_crop_coefficients(fn)
    return cet

if __name__ == '__main__':
    basin_id = 'klamath'
    cet = _test(basin_id)
