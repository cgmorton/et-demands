#!/usr/bin/env python
import datetime
import fileinput
import logging
import math
import os
import re
import sys

import numpy as np
import pandas as pd

import crop_et_data
import compute_crop_et
from initialize_crop_cycle import InitializeCropCycle
import util

class DayData:
    def __init__(self):
        """ """
        ## Used in compute_crop_gdd(), needs to be persistent during day loop
        self.etref_array = np.zeros(30)

def crop_cycle(data, et_cell):
    """

    Args:
        data (): 
        et_cell (): 
        
    Returns:

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
        if not et_cell.crop_flags[crop_num]:
            logging.debug('Crop %s %s' % (crop_num, crop))
            logging.debug('  NOT USED')
            continue
        else:
            logging.warning('Crop %2s %s' % (crop_num, crop))          
        logging.debug(
            'crop_day_loop():  Curve %s %s  Class %s  Flag %s' %
            (crop.curve_number, crop.curve_name,
             crop.class_number, et_cell.crop_flags[crop_num]))
        logging.debug('  GDD trigger DOY: {}'.format(crop.gdd_trigger_doy ))

        if crop_num <> 58:
            continue
        
        ## 'foo' is holder of all these global variables for now
        foo = InitializeCropCycle()

        ## First time through for crop, load basic crop parameters and process climate data
        foo.crop_load(et_cell, crop)
        
        ## Initialize crop data frame
        foo.setup_dataframe(et_cell)

        ## Run ET-Demands
        crop_day_loop(data, et_cell, crop, foo)
        
        ## Write output
        ## Merge the crop and weather data frames to form the output
        output_pd = pd.merge(
            foo.crop_pd, et_cell.weather_pd[['ppt']], 
            ##foo.crop_pd, et_cell.weather_pd[['ppt', 't30']], 
            left_index=True, right_index=True)
        ## Rename the output columns
        output_pd.index.rename('Date', inplace=True)
        output_pd = output_pd.rename(columns = {
            'doy':'DOY', 'ppt':'PPT', 'etref':'PMETo',
            'et_act':'ETact', 'et_pot':'ETpot', 'et_bas':'ETbas',
            'kc_act':'Kc', 'kc_bas':'Kcb',
            'niwr':'NIWR', 'irrigation':'Irrigation', 'runoff':'Runoff', 
            'dperc':'DPerc', 'season':'Season'}) 
            ##'t30':'T30', 
        output_path = os.path.join(
            data.output_ws, '%s_Crop_%s.csv' % (et_cell.cell_id, crop.class_number))
        ## Set the output column order
        output_columns = [
            'DOY', 'PMETo', 'ETact', 'ETpot', 'ETbas', 'Kc', 'Kcb', 
            'PPT', 'Irrigation', 'Runoff', 'DPerc', 'NIWR', 'Season']
        if not data.kc_flag:
            output_columns.remove('Kc')
            output_columns.remove('Kcb')
        if not data.niwr_flag:
            output_columns.remove('NIWR')
        ## Write the output file
        with open(output_path, 'w') as output_f:
            output_f.write('# {0:2d} - {1}\n'.format(crop_num, crop.name))
            output_pd.to_csv(
                output_f, sep=',', columns=output_columns, 
                float_format='%10.6f')
            output_f.close()

def crop_day_loop(data, et_cell, crop, foo):
    """

    Args:
        data ():
        et_cell ():
        crop ():
        foo ():

    Returns:
        None
    """
    ##logging.debug('crop_day_loop()')    
    foo_day = DayData()
    foo_day.sdays = 0

    for step_dt, step_doy in foo.crop_pd[['doy']].iterrows():
        logging.debug('\ncrop_day_loop(): DOY %s  Date %s' % (step_doy, step_dt.date)) 

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
                'crop_day_loop(): in_season[%s]  crop_setup[%s]  dormant_setup[%s]' % 
                (foo.in_season, foo.crop_setup_flag, foo.dormant_setup_flag))
            foo.setup_dormant(et_cell, crop)
        logging.debug(
            'crop_day_loop(): in_season[%s]  crop_setup[%s]  dormant_setup[%s]' % 
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
                
        ## Calculate Kcb, Ke, ETc
        compute_crop_et.compute_crop_et(data, et_cell, crop, foo, foo_day)

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
