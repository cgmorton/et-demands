#!/usr/bin/env python

import math
import os
from pprint import pprint
import sys
import time

import numpy as np

import util

class ETCell:
    name = None

    def __init__(self):
        """ """

    def __str__(self):
        """ """
        s = '<ETCell %s, %s %s>' % (self.cell_id, self.cell_name, self.refET_id)
        return s

    def init_properties_from_row(self, data):
        """ Parse a row of data from the ET cell properties file

        Order of the values:
        ETCellIDs, ETCellNames, RefETIDs, station_lat, station_long,
        station_elevft, station_WHC, station_soildepth, station_HydroGroup,
        aridity_rating, refETPaths

        Args:
            data: list of row values

        """
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
        """ Parse the row of data """
        self.irrigation_flag = int(data[3])
        self.crop_flags = data[4:].astype(bool)
        self.ncrops = len(self.crop_flags)

    def init_cuttings_from_row(self, data):
        """ Parse the row of data """
        self.cuttingsLat = float(data[2])
        self.dairy_cuttings = int(data[3])
        self.beef_cuttings = int(data[4])

    def set_daily_refet_data(self, fn, skip_rows=2):
        """Read the RefET data file for a single station

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

        Args:
            fn: string
            skip_rows: integer indicating the number of header rows to skip
        Returns:
            Dictionary of the NLDAS data, keys are the columns,
                and values are numpy arrays of the data
        """
        
        a = np.loadtxt(fn, dtype='str', skiprows=skip_rows)

        ## May want to save the date field(s) as some point
        date_list = a[:,0].tolist()
        a = a[:,1:].astype(float)

        # time.struct_time(tm_year=1950, tm_mon=1, tm_mday=3, tm_hour=0, tm_min=0,
        # tm_sec=0, tm_wday=1, tm_yday=3, tm_isdst=-1)
        struct_time_list = [time.strptime(s, "%m/%d/%Y") for s in date_list]
        
        self.refet = {
             'TMax': a[:,0], 'TMin': a[:,1],
             'Precip': a[:,2], 'Snow': a[:,3], 'SnowDepth': a[:,4],
             'EstRs': a[:,5], 'Wind': a[:,6], 'TDew': a[:,7],
             'ASCEPMStdETr': a[:,10], 'ASCEPMStdETo': a[:,11],
             ##'Penman':  a[:,8], 'PreTay': a[:,9], 'Harg': a[:,12],
             ##'Dates': np.asarray(date_list),
             'Dates': np.asarray(struct_time_list)}

    def set_daily_nldas_data(self, fn):
        """Read the NLDAS data rod CSV file for a single station

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
        Returns:
            Dictionary of the NLDAS data, keys are the columns,
                and values are numpy arrays of the data
        """

        a = np.genfromtxt(fn, delimiter=',', names=True)
        ##print a.dtype.names
     
        date_str_list = ['{0}/{1}/{2}'.format(int(m),int(d),int(y))
                         for y, m, d in zip(a['Year'], a['Month'], a['Day'])]
        struct_time_list = [time.strptime(s, "%m/%d/%Y") for s in date_str_list]

        ## Convert temperatures from K to C
        a['TmaxK'] -= 273.15
        a['TminK'] -= 273.15

        ## Convert W/m2 to MJ/m2
        a['Solar_Radiation_W_m2'] *= 0.0864

        ## Scale wind from 10m to 2m
        a['Wind__10m_m_s1'] *= 4.87 / math.log(67.8 * 10 - 5.42)

        ## Calculate Tdew from specific humidity
        ## Convert station elevation from feet to meters
        pair = util.pair_func(0.3048 * self.stn_elev)
        ea = util.ea_from_q(pair, a['Specific_Humiditykg_kg1'])
        tdew = util.tdew_from_ea(ea)

        zero_array = np.zeros(a['TmaxK'].shape, dtype=np.float32)
        self.refet = {
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
             ##'Dates': np.asarray(date_str_list),
             'Dates': np.asarray(struct_time_list)}        

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
