#!/usr/bin/env python

import sys
from pprint import pprint
import numpy as np
import datetime
import time

import crop_parameters
import crop_coefficients
import et_cell

#DELIMITER = ','
DELIMITER = '\t'



def getDateParams(date='1/1/1950'):
    """ """
    mo,da,yr = date.split('/')
    mo = int(mo)
    da = int(da)
    yr = int(yr)
    doy = datetime.datetime(yr,mo,da).timetuple().tm_yday
    return yr,mo,da,doy


def ReadDailyRefETData(fn):
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

    ### may want to save the date field(s) as some point
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
  

class Cropet_data:

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
        self.crop_parameters = crop_parameters.ReadCropParameters(fn)
        #pprint(vars(self.crop_parameters[0]))

    def set_crop_coefficients(self, fn=''):
        """ List of <CropCoeff> instances """
        self.crop_coeffs = crop_coefficients.ReadCropCoefs(fn)
        #pprint(vars(self.crop_coeffs[0]))

    def set_refet_data(self, fn=''):
        """ Mapping refet output variables """
        self.refet = ReadDailyRefETData(fn)

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
        'CGDDMainDoy' : 1,


    }

def _test_old():
    """ """

    cet = Cropet_data()
    print '\nRead Cell data'
    # cell property files
    fn = 'DATA/EX/txt_KlamathMetAndDepletionNodes/ETCellsProperties.txt'
    # init cells with property info
    et_cells = et_cell.ReadETCellsProperties(fn)
    # cell crop mix files
    fn = 'DATA/EX/txt_KlamathMetAndDepletionNodes/ETCellsCrops.txt'
    # add the crop to cells
    et_cell.ReadETCellsCrops(fn, et_cells)
    # add mean cuttings
    fn = 'DATA/EX/txt_KlamathMetAndDepletionNodes/MeanCuttings.txt'
    et_cell.ReadMeanCuttings(fn, et_cells)
    #c = et_cells.values()[0]
    #pprint(vars(c))
    #print c
    cet.set_et_cells(et_cells)

    print '\nReadCropParameters'
    fn = 'DATA/EX/txt_KlamathMetAndDepletionNodes/CropParams.txt'
    cet.set_crop_parameters(fn)
    #print(cet.crop_parameters[0])

    print '\nReadCropCoefficients'
    fn = 'DATA/EX/txt_KlamathMetAndDepletionNodes/CropCoefs.txt'
    cet.set_crop_coefficients(fn)
    #print(coeff[0])
    #pprint(ReadCropCoefs(fn))

    '''
    print '\nReadDailyRefETData' 
    #fn = 'DATA/EX/Klamath_pmdata/ETo/OR1571E2_KL_2020_S0.dat'  # 1
    #fn = 'DATA/EX/Klamath_pmdata/ETo/OR8007E2_KL_2020_S0.dat'  # 2
    fn = 'DATA/EX/Klamath_pmdata/ETo/OR8007E2_KL_2020_S0.dat'  # 2
    cet.set_refet_data(fn)
    #pprint(ReadDailyRefETData(fn))
    '''
    return cet


def _test(ss_name='klamath', pth='DATA/EX/klamath/txt'):
    """ """
    cet = Cropet_data()
    #pth = pth % ss_name

    # cell property files
    #fn = 'DATA/EX/%s/txt/ETCellsProperties.txt' % ss_name
    fn = '%s/ETCellsProperties.txt' % pth
    print '\nRead Cell Properties', fn
    # init cells with property info
    et_cells = et_cell.ReadETCellsProperties(fn)

    # cell crop mix files
    #fn = 'DATA/EX/%s/txt/ETCellsCrops.txt' % ss_name
    fn = '%s/ETCellsCrops.txt' % pth
    print '\nRead Cell crops', fn
    # add the crop to cells
    et_cell.ReadETCellsCrops(fn, et_cells)

    # add mean cuttings
    #fn = 'DATA/EX/%s/txt/MeanCuttings.txt' % ss_name
    fn = '%s/MeanCuttings.txt' % pth
    print '\nRead mean cuttings', fn
    et_cell.ReadMeanCuttings(fn, et_cells)
    #c = et_cells.values()[0]
    #pprint(vars(c))
    #print c
    cet.set_et_cells(et_cells)

    #fn = 'DATA/EX/%s/txt/CropParams.txt' % ss_name
    fn = '%s/CropParams.txt' % pth
    print '\nReadCropParameters', fn
    cet.set_crop_parameters(fn)
    #print(cet.crop_parameters[0])

    #fn = 'DATA/EX/%s/txt/CropCoefs.txt' % ss_name
    fn = '%s/CropCoefs.txt' % pth
    print '\nReadCropCoefficients', fn
    cet.set_crop_coefficients(fn)
    #print(coeff[0])
    #pprint(ReadCropCoefs(fn))

    '''
    print '\nReadDailyRefETData' 
    #fn = 'DATA/EX/Klamath_pmdata/ETo/OR1571E2_KL_2020_S0.dat'  # 1
    #fn = 'DATA/EX/Klamath_pmdata/ETo/OR8007E2_KL_2020_S0.dat'  # 2
    fn = 'DATA/EX/Klamath_pmdata/ETo/OR8007E2_KL_2020_S0.dat'  # 2
    cet.set_refet_data(fn)
    #pprint(ReadDailyRefETData(fn))
    '''

    return cet


if __name__ == '__main__':
    #cet = _test()
    ss_name = 'klamath'
    ss_name = 'rioGrande'
    ss_name = 'CVP'
    ss_name = 'truckee'
    cet = _test(ss_name)




