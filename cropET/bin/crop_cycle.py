#!/usr/bin/env python
import datetime
import logging
import math
import os
import re
import sys

import numpy as np

import crop_et_data
import compute_crop_et
from initialize_crop_cycle import InitializeCropCycle
import util

class DayData:
    def __init__(self):
        """ """
        ## Used in compute_crop_gdd(), needs to be persistant during day loop
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
        ##logging.debug('  Crop:  {0} {1}'.format(crop_num, crop))
        ##logging.debug('  Curve: {0} {1}'.format(
        ##    crop.curve_number, crop.curve_name))
        ##logging.debug('  Class: {}'.format(crop.class_number))
        ##logging.debug('  Flag:  {}'.format(et_cell.crop_flags[crop_num]))

        logging.debug('  GDD trigger DOY: {}'.format(crop.gdd_trigger_doy ))

        ## 'foo' is holder of all these global variables for now
        foo = InitializeCropCycle()

        ## First time through for crop, load basic crop parameters and process climate data
        foo.crop_load(data, et_cell, crop)

        ## Open output file for each crop and write header
        output_path = os.path.join(
            data.output_ws, '%s_Crop_%s.dat' % (et_cell.cell_id, crop.class_number))
        fmt = '%10s %3s %9s %9s %9s %9s %9s %9s %9s %5s %9s %9s\n'
        header = (
            '      Date', 'DOY', 'PMETo', 'Pr.mm', 'T30', 'ETact',
            'ETpot', 'ETbas', 'Irrn', 'Seasn', 'Runof', 'DPerc')
        if data.niwr_flag:
            header = header + ('NIWR',)
            fmt = fmt.replace('\n', ' %9s\n')
        output_f = open(output_path, 'w')
        output_f.write('# {0:2d} - {1}\n'.format(crop_num, crop.name))
        output_f.write(fmt % header)

        ## 
        crop_day_loop(data, et_cell, crop, foo, output_f)

        ## Close output file
        output_f.close()

def crop_day_loop(data, et_cell, crop, foo, output_f=None):
    """

    Args:
        data ():
        et_cell ():
        crop ():
        foo ():
        output_f ():

    Returns:
        None
    """
    ##logging.debug('crop_day_loop()')
    foo_day = DayData()

    for i, (step_dt, step_doy) in et_cell.refet_pd[['date','doy']].iterrows():
        logging.debug('\ncrop_day_loop(): DOY %s  Date %s' % (step_doy, step_dt))

        ## Log RefET values at time step 
        logging.debug(
            'crop_day_loop(): PPT %.6f  Wind %.6f  Tdew %.6f ETref %.6f' % 
            (et_cell.weather_pd['ppt'][i], et_cell.weather_pd['wind'][i], 
             et_cell.weather_pd['tdew'][i], et_cell.refet_pd['etref'][i]))
        ## Log climate values at time step         
        logging.debug(
            'crop_day_loop(): tmax %.6f  tmin %.6f  tmean %.6f  t30 %.6f' %
            (et_cell.climate_pd['tmax'][i], et_cell.climate_pd['tmin'][i], 
             et_cell.climate_pd['tmean'][i], et_cell.climate_pd['t30'][i]))

        ## At very start for crop, set up for next season
        if not foo.in_season and foo.crop_setup_flag:
            foo.setup_crop(crop)

        ## At end of season for each crop, set up for nongrowing and dormant season
        if not foo.in_season and foo.dormant_setup_flag:
            logging.debug(
                'crop_day_loop(): in_season[%s]  crop_setup[%s]  dormant_setup[%s]' % 
                (foo.in_season, foo.crop_setup_flag, foo.dormant_setup_flag))
            foo.setup_dormant(data, et_cell, crop)
        logging.debug(
            'crop_day_loop(): in_season[%s]  crop_setup[%s]  dormant_setup[%s]' % 
            (foo.in_season, foo.crop_setup_flag, foo.dormant_setup_flag))

        ## Track variables for each day
        ## For now, cast all values to native Python types
        foo_day.sdays = i + 1
        foo_day.doy = int(step_doy)
        foo_day.year = int(step_dt.year)
        foo_day.month = int(step_dt.month)
        foo_day.day = int(step_dt.day)
        foo_day.date = et_cell.refet_pd.at[i, 'date'].to_datetime()
        foo_day.tmax_orig = float(et_cell.weather_pd.at[i, 'tmax'])
        foo_day.tdew = float(et_cell.weather_pd.at[i, 'tdew'])
        foo_day.u2 = float(et_cell.weather_pd.at[i, 'wind'])
        foo_day.precip = float(et_cell.weather_pd.at[i, 'ppt'])
        foo_day.rh_min = float(et_cell.weather_pd.at[i, 'rh_min'])
        foo_day.etref = float(et_cell.refet_pd.at[i, 'etref'])
        foo_day.tmean = float(et_cell.climate_pd.at[i, 'tmean'])
        foo_day.tmin = float(et_cell.climate_pd.at[i, 'tmin'])
        foo_day.tmax = float(et_cell.climate_pd.at[i, 'tmax'])
        foo_day.snow_depth = float(et_cell.climate_pd.at[i, 'snow_depth'])
        foo_day.t30 = float(et_cell.climate_pd.at[i, 't30'])
        ##foo_day.precip = float(et_cell.climate_pd.at[i, 'precip'])


        ## DEADBEEF - Why make copies?
        foo_day.cgdd_0_lt = np.copy(et_cell.climate['main_cgdd_0_lt'])
        #foo_day.t30_lt = np.copy(et_cell.climate['main_t30_lt'])
                
        ## Calculate Kcb, Ke, ETc
        compute_crop_et.compute_crop_et(data, et_cell, crop, foo, foo_day)

        ## Write vb-like output file for comparison
        if output_f:
            fmt = ('%10s %3s %9.3f %9.3f %9.3f %9.3f %9.3f '+
                   '%9.3f %9.3f %5d %9.3f %9.3f\n')
            values = (step_dt.date(), step_doy, foo_day.etref, foo_day.precip, 
                      foo_day.t30, foo.etc_act, foo.etc_pot, foo.etc_bas,
                      foo.irr_sim, foo.in_season, foo.sro, foo.dperc)
            if data.niwr_flag:
                values = values + (foo.niwr + 0,)
                fmt = fmt.replace('\n', ' %9.3f\n')
            output_f.write(fmt % values)

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
