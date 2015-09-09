#!/usr/bin/env python
import datetime
import fileinput
import logging
import math
import multiprocessing as mp
import os
import re
import sys

import numpy as np
import pandas as pd

import calculate_height
import crop_et_data
import compute_crop_et
import compute_crop_gdd
from initialize_crop_cycle import InitializeCropCycle
import kcb_daily
import util

class DayData:
    def __init__(self):
        """ """
        ## Used in compute_crop_gdd(), needs to be persistent during day loop
        self.etref_array = np.zeros(30)

def crop_cycle(data, et_cell, debug_flag=False, vb_flag=False):
    """Compute crop ET for all crops

    Args:
        data (): 
        et_cell ():
        debug_flag (bool): If True, write debug level comments to debug.txt
        vb_flag (bool): If True, mimic calculations in VB version of code
        
    Returns:
        None
    """
    ## Following is for one crop grown back to back over entire ETr sequence
    ##
    ## do bare soil first, before looping through crops
    ## current curve file has 60 curves, so 44 is not correct relative to coefficients
    ##'''
    ##   ' start with crop type 44 (bare soil, winter mulch) and run through last crop first '<------ specific value for crop number
    ##   ' this is done to compute 'winter covers', which are bare soil, mulch and dormant turf,
    ##   ' before any crops are processed.  Bare soil is "crop" no. 44.
    ##'''
    #### no curve for bare soil
    ##ctCount = 43  # bare soil
    ##ctCount = 1  # bare soil
    
    ##logging.debug('in crop_cycle()')

    ## crop loop through all crops, doesn't include bare soil??
    for crop_num, crop in sorted(et_cell.crop_params.items()):
        ## Check to see if crop/landuse is at station
        if et_cell.crop_flags[crop_num] == 0:
            logging.debug('Crop %2d %s' % (crop_num, crop))
            logging.debug('  NOT USED')
            continue
        elif ((data.crop_skip_list and crop_num in data.crop_skip_list) or 
              (data.crop_test_list and crop_num not in data.crop_test_list)):
            ##logging.debug('Crop %2d %s' % (crop_num, crop))
            ##logging.debug('  SKIPPING')
            continue               
        else:      
            logging.warning('Crop %2d %s' % (crop_num, crop))                 
        logging.debug(
            'crop_day_loop():  Curve %d %s  Class %s  Flag %s' %
            (crop.curve_number, crop.curve_name,
             crop.class_number, et_cell.crop_flags[crop_num]))
        logging.debug('  GDD trigger DOY: {}'.format(crop.gdd_trigger_doy ))
        
        ## 'foo' is holder of all these global variables for now
        foo = InitializeCropCycle()

        ## First time through for crop, load basic crop parameters and process climate data
        foo.crop_load(et_cell, crop)
        
        ## Initialize crop data frame
        foo.setup_dataframe(et_cell)

        ## Run ET-Demands
        crop_day_loop(data, et_cell, crop, foo, debug_flag, vb_flag)
        
        ## Merge the crop and weather data frames to form the daily output
        if (data.daily_output_flag or 
            data.monthly_output_flag or 
            data.annual_output_flag):
            daily_output_pd = pd.merge(
                foo.crop_pd, et_cell.weather_pd[['ppt']], 
                ##foo.crop_pd, et_cell.weather_pd[['ppt', 't30']], 
                left_index=True, right_index=True)
            ## Rename the output columns
            daily_output_pd.index.rename('Date', inplace=True)
            daily_output_pd['Year'] = daily_output_pd.index.year
            daily_output_pd = daily_output_pd.rename(columns = {
                'doy':'DOY', 'ppt':'PPT', 'etref':'PMETo',
                'et_act':'ETact', 'et_pot':'ETpot', 'et_bas':'ETbas',
                'kc_act':'Kc', 'kc_bas':'Kcb',
                'niwr':'NIWR', 'irrigation':'Irrigation', 'runoff':'Runoff', 
                'dperc':'DPerc', 'season':'Season'})
                ##'t30':'T30', 
        ## Compute monthly and annual stats before modifying daily format below
        if data.monthly_output_flag:
            monthly_resample_func = {
                'PMETo':np.sum, 'ETact':np.sum, 'ETpot':np.sum, 'ETbas':np.sum,
                'Kc':np.mean, 'Kcb':np.mean, 'NIWR':np.sum, 'PPT':np.sum, 
                'Irrigation':np.sum, 'Runoff':np.sum, 'DPerc':np.sum, 'Season':np.sum}
            monthly_output_pd = daily_output_pd.resample('MS', how=monthly_resample_func)
        if data.annual_output_flag:
            resample_func = {
                'PMETo':np.sum, 'ETact':np.sum, 'ETpot':np.sum, 'ETbas':np.sum,
                'Kc':np.mean, 'Kcb':np.mean, 'NIWR':np.sum, 'PPT':np.sum,
                'Irrigation':np.sum, 'Runoff':np.sum, 'DPerc':np.sum, 'Season':np.sum}
            annual_output_pd = daily_output_pd.resample('AS', how=resample_func)
        ## Get growing season start and end DOY for each year
        ## Compute growing season length for each year
        if data.gs_output_flag:
            gs_output_pd = daily_output_pd.resample('AS', how={'Year':np.mean})
            gs_output_pd['Start_DOY'] = np.nan
            gs_output_pd['End_DOY'] = np.nan
            gs_output_pd['Start_Date'] = None
            gs_output_pd['End_Date'] = None
            gs_output_pd['GS_Length'] = np.nan
            for year_i, (year, group) in enumerate(daily_output_pd.groupby(['Year'])):
                ##if year_i == 0:
                ##    logging.debug('  Skipping first year')
                ##    continue
                if not np.any(group['Season'].values):
                    logging.debug('  Skipping, season flag was never set to 1')
                    continue
                else:
                    season_diff = np.diff(group['Season'].values)
                    try:
                        start_i = np.where(season_diff == 1)[0][0] + 1
                        gs_output_pd.set_value(
                            group.index[0], 'Start_DOY', int(group.ix[start_i, 'DOY']))
                    except:
                        gs_output_pd.set_value(
                            group.index[0], 'Start_DOY', int(min(group['DOY'].values)))
                    try:
                        end_i = np.where(season_diff == -1)[0][0] + 1
                        gs_output_pd.set_value(
                            group.index[0], 'End_DOY', int(group.ix[end_i, 'DOY']))
                    except:
                        gs_output_pd.set_value(
                            group.index[0], 'End_DOY', int(max(group['DOY'].values)))
                    del season_diff
                gs_output_pd.set_value(
                    group.index[0], 'GS_Length', int(sum(group['Season'].values)))
         
        ## Write daily output
        if data.daily_output_flag:
            daily_output_pd['Year'] = daily_output_pd.index.year
            daily_output_pd['Month'] = daily_output_pd.index.month
            daily_output_pd['Day'] = daily_output_pd.index.day
            daily_output_pd['Year'] = daily_output_pd['Year'].map(lambda x: ' %4d' % x)
            daily_output_pd['Month'] = daily_output_pd['Month'].map(lambda x: ' %2d' % x)
            daily_output_pd['Day'] = daily_output_pd['Day'].map(lambda x: ' %2d' % x)
            daily_output_pd['DOY'] = daily_output_pd['DOY'].map(lambda x: ' %3d' % x)
            ## This will convert negative "zeros" to positive
            daily_output_pd['NIWR'] = np.round(daily_output_pd['NIWR'],6)
            daily_output_pd['Season'] = daily_output_pd['Season'].map(lambda x: ' %1d' % x)
            ##daily_output_pd['Irrigation'] = daily_output_pd['Irrigation'].map(lambda x: daily_flt_format % x)
            daily_output_path = os.path.join(
                data.daily_output_ws, '{0}_daily_crop_{1:02d}.csv'.format(
                    et_cell.cell_id, crop.class_number))
            ## Set the output column order
            daily_output_columns = [
                'Year', 'Month', 'Day', 'DOY', 
                'PMETo', 'ETact', 'ETpot', 'ETbas', 'Kc', 'Kcb', 
                'PPT', 'Irrigation', 'Runoff', 'DPerc', 'NIWR', 'Season']
            if not data.kc_flag:
                daily_output_columns.remove('Kc')
                daily_output_columns.remove('Kcb')
            if not data.niwr_flag:
                daily_output_columns.remove('NIWR')
            with open(daily_output_path, 'w') as daily_output_f:
                daily_output_f.write('# {0:2d} - {1}\n'.format(crop_num, crop.name))
                daily_output_pd.to_csv(
                    daily_output_f, sep=',', columns=daily_output_columns, 
                    float_format='%10.6f', date_format='%Y-%m-%d')
            del daily_output_pd, daily_output_path, daily_output_columns

        ## Write monthly statistics
        if data.monthly_output_flag:
            monthly_output_pd['Year'] = monthly_output_pd.index.year
            monthly_output_pd['Month'] = monthly_output_pd.index.month
            monthly_output_pd['Year'] = monthly_output_pd['Year'].map(lambda x: ' %4d' % x)
            monthly_output_pd['Month'] = monthly_output_pd['Month'].map(lambda x: ' %2d' % x)
            monthly_output_pd['Season'] = monthly_output_pd['Season'].map(lambda x: ' %2d' % x)
            monthly_output_path = os.path.join(
                data.monthly_output_ws, '{0}_monthly_crop_{1:02d}.csv'.format(
                    et_cell.cell_id, int(crop.class_number)))
            monthly_output_columns = [
                'Year', 'Month', 'PMETo', 'ETact', 'ETpot', 'ETbas', 'Kc', 'Kcb', 
                'PPT', 'Irrigation', 'Runoff', 'DPerc', 'NIWR', 'Season']
            with open(monthly_output_path, 'w') as monthly_output_f:
                monthly_output_f.write('# {0:2d} - {1}\n'.format(crop_num, crop.name))
                monthly_output_pd.to_csv(
                    monthly_output_f, sep=',', columns=monthly_output_columns, 
                    float_format=' %8.4f', date_format='%Y-%m')
            del monthly_output_pd, monthly_output_path, monthly_output_columns

        ## Write annual statistics
        if data.annual_output_flag:
            annual_output_pd['Year'] = annual_output_pd.index.year
            annual_output_pd['Season'] = annual_output_pd['Season'].map(lambda x: ' %3d' % x)
            annual_output_path = os.path.join(
                data.annual_output_ws, '{0}_annual_crop_{1:02d}.csv'.format(
                    et_cell.cell_id, int(crop.class_number)))
            annual_output_columns = [
                'Year', 'PMETo', 'ETact', 'ETpot', 'ETbas', 'Kc', 'Kcb', 
                'PPT', 'Irrigation', 'Runoff', 'DPerc', 'NIWR', 'Season']
            with open(annual_output_path, 'w') as annual_output_f:
                annual_output_f.write('# {0:2d} - {1}\n'.format(crop_num, crop.name))
                annual_output_pd.to_csv(
                    annual_output_f, sep=',', columns=annual_output_columns, 
                    float_format=' %9.4f', date_format='%Y', index = False)
            del annual_output_pd, annual_output_path, annual_output_columns
          
        ## Write growing season statistics
        if data.gs_output_flag:
            def doy_2_date(test_year, test_doy):
                try:
                    return datetime.datetime.strptime(
                        '{0}_{1}'.format(int(test_year), int(test_doy)), '%Y_%j').date().isoformat()
                except:
                    return 'None'
            gs_output_pd['Start_Date'] = gs_output_pd[['Year', 'Start_DOY']].apply(
                lambda s:doy_2_date(*s), axis = 1)
            gs_output_pd['End_Date'] = gs_output_pd[['Year', 'End_DOY']].apply(
                lambda s:doy_2_date(*s), axis = 1)
            ##gs_output_pd['Start_DOY'] = gs_output_pd['Start_DOY'].map(lambda x: ' %3d' % x)
            ##gs_output_pd['End_DOY'] = gs_output_pd['End_DOY'].map(lambda x: ' %3d' % x)
            ##gs_output_pd['GS_Length'] = gs_output_pd['GS_Length'].map(lambda x: ' %3d' % x)
            gs_output_path = os.path.join(
                data.gs_output_ws, '{0}_gs_crop_{1:02d}.csv'.format(
                    et_cell.cell_id, int(crop.class_number)))
            gs_output_columns = [
                'Year', 'Start_DOY', 'End_DOY', 'Start_Date', 'End_Date', 'GS_Length']
            with open(gs_output_path, 'w') as gs_output_f:
                gs_output_f.write('# {0:2d} - {1}\n'.format(crop_num, crop.name))
                gs_output_pd.to_csv(
                    gs_output_f, sep=',', columns=gs_output_columns, 
                    date_format='%Y', index = False)
            del gs_output_pd, gs_output_path, gs_output_columns
            

def crop_day_loop(data, et_cell, crop, foo, debug_flag=False, vb_flag=False):
    """Compute crop ET for each daily timestep

    Args:
        data ():
        et_cell ():
        crop ():
        foo ():
        debug_flag (bool): If True, write debug level comments to debug.txt
        vb_flag (bool): If True, mimic calculations in VB version of code

    Returns:
        None
    """ 
    foo_day = DayData()
    foo_day.sdays = 0
    foo_day.doy_prev = 0

    for step_dt, step_doy in foo.crop_pd[['doy']].iterrows():
        if debug_flag:
            logging.debug('\ncrop_day_loop(): DOY %d  Date %s' % (step_doy, step_dt.date())) 
            
            ## Log RefET values at time step 
            logging.debug(
                'crop_day_loop(): PPT %.6f  Wind %.6f  Tdew %.6f ETref %.6f' % 
                (et_cell.weather_pd.at[step_dt,'ppt'], et_cell.weather_pd.at[step_dt,'wind'], 
                 et_cell.weather_pd.at[step_dt,'tdew'], et_cell.refet_pd.at[step_dt,'etref']))
            ## Log climate values at time step         
            logging.debug(
                'crop_day_loop(): tmax %.6f  tmin %.6f  tmean %.6f  t30 %.6f' %
                (et_cell.climate_pd.at[step_dt,'tmax'], et_cell.climate_pd.at[step_dt,'tmin'], 
                 et_cell.climate_pd.at[step_dt,'tmean'], et_cell.climate_pd.at[step_dt,'t30']))

        ## At very start for crop, set up for next season
        if not foo.in_season and foo.crop_setup_flag:
            foo.setup_crop(crop)

        ## At end of season for each crop, set up for nongrowing and dormant season
        if not foo.in_season and foo.dormant_setup_flag:
            logging.debug(
                'crop_day_loop(): in_season[%r]  crop_setup[%r]  dormant_setup[%r]' % 
                (foo.in_season, foo.crop_setup_flag, foo.dormant_setup_flag))
            foo.setup_dormant(et_cell, crop)
        logging.debug(
            'crop_day_loop(): in_season[%r]  crop_setup[%r]  dormant_setup[%r]' % 
            (foo.in_season, foo.crop_setup_flag, foo.dormant_setup_flag))

        ## Track variables for each day
        ## For now, cast all values to native Python types
        foo_day.sdays += 1
        foo_day.doy = int(step_doy)
        foo_day.year = int(step_dt.year)
        foo_day.month = int(step_dt.month)
        foo_day.day = int(step_dt.day)
        foo_day.date = step_dt
        foo_day.tmax_orig = float(et_cell.weather_pd.at[step_dt, 'tmax'])
        foo_day.tdew = float(et_cell.weather_pd.at[step_dt, 'tdew'])
        foo_day.u2 = float(et_cell.weather_pd.at[step_dt, 'wind'])
        foo_day.precip = float(et_cell.weather_pd.at[step_dt, 'ppt'])
        foo_day.rh_min = float(et_cell.weather_pd.at[step_dt, 'rh_min'])
        foo_day.etref = float(et_cell.refet_pd.at[step_dt, 'etref'])
        foo_day.tmean = float(et_cell.climate_pd.at[step_dt, 'tmean'])
        foo_day.tmin = float(et_cell.climate_pd.at[step_dt, 'tmin'])
        foo_day.tmax = float(et_cell.climate_pd.at[step_dt, 'tmax'])
        foo_day.snow_depth = float(et_cell.climate_pd.at[step_dt, 'snow_depth'])
        foo_day.t30 = float(et_cell.climate_pd.at[step_dt, 't30'])
        ##foo_day.precip = float(et_cell.climate_pd.at[step_dt, 'precip'])

        ## DEADBEEF - Why make copies?
        foo_day.cgdd_0_lt = np.copy(et_cell.climate['main_cgdd_0_lt'])
        #foo_day.t30_lt = np.copy(et_cell.climate['main_t30_lt'])
                
        ## Compute crop growing degree days
        compute_crop_gdd.compute_crop_gdd(crop, foo, foo_day, debug_flag)

        ## Calculate height of vegetation.  Call was moved up to this point 12/26/07 for use in adj. Kcb and kc_max
        calculate_height.calculate_height(crop, foo, debug_flag)

        ## Interpolate Kcb and make climate adjustment (for ETo basis)
        kcb_daily.kcb_daily(
            data, et_cell, crop, foo, foo_day, debug_flag, vb_flag)

        ## Calculate Kcb, Ke, ETc
        compute_crop_et.compute_crop_et(
            data, et_cell, crop, foo, foo_day, debug_flag)

        ## Retrieve values from foo_day and write to output data frame
        ## Eventually let compute_crop_et() write directly to output df
        foo.crop_pd.at[step_dt, 'et_act'] = foo.etc_act
        foo.crop_pd.at[step_dt, 'et_pot'] = foo.etc_pot
        foo.crop_pd.at[step_dt, 'et_bas'] = foo.etc_bas
        foo.crop_pd.at[step_dt, 'kc_act'] = foo.kc_act
        foo.crop_pd.at[step_dt, 'kc_bas'] = foo.kc_bas
        foo.crop_pd.at[step_dt, 'irrigation'] = foo.irr_sim
        foo.crop_pd.at[step_dt, 'runoff'] = foo.sro
        foo.crop_pd.at[step_dt, 'dperc'] = foo.dperc
        foo.crop_pd.at[step_dt, 'niwr'] = foo.niwr + 0
        foo.crop_pd.at[step_dt, 'season'] = int(foo.in_season)
        
        ## Write final output file variables to DEBUG file
        if debug_flag:
            logging.debug(
                ('crop_day_loop(): ETref  %.6f  Precip %.6f  T30 %.6f') %
                (foo_day.etref, foo_day.precip, foo_day.t30))
            logging.debug(
                ('crop_day_loop(): ETact  %.6f  ETpot %.6f   ETbas %.6f') %
                (foo.etc_act, foo.etc_pot, foo.etc_bas))
            logging.debug(
                ('crop_day_loop(): Irrig  %.6f  Runoff %.6f  DPerc %.6f  NIWR %.6f') %
                (foo.irr_sim, foo.sro, foo.dperc, foo.niwr))

def main():
    """ """
    pass

if __name__ == '__main__':
    main()
