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
            data.output_ws, '%s_%s.dat' % (et_cell.cell_id, crop.class_number))
        fmt = '%10s %3s %9s %9s %9s %9s %9s %9s %9s %5s %9s %9s\n'
        header = (
            '#     Date', 'DOY', 'PMETo', 'Pr.mm', 'T30', 'ETact',
            'ETpot', 'ETbas', 'Irrn', 'Seasn', 'Runof', 'DPerc')
        if data.niwr_flag:
            header = header + ('NIWR',)
            fmt = fmt.replace('\n', ' %9s\n')
        output_f = open(output_path, 'w')
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

    ## Build a mask of valid dates
    ## DEADBEEF - This should be computed once instead of by crop
    date_mask = np.array([
        isinstance(dt, datetime.date) for dt in et_cell.refet['dates']])
    if data.start_dt:
        date_mask[et_cell.refet['dates'] < data.start_dt] = False
    if data.end_dt:
        date_mask[et_cell.refet['dates'] > data.end_dt] = False
 
    for i, step_dt in enumerate(et_cell.refet['dates']):
        step_doy = int(step_dt.strftime('%j'))
        logging.debug('\ncrop_day_loop(): DOY %s  Date %s' % (step_doy, step_dt))
        if not date_mask[i]:
            continue
        ##if start_dt is not None and step_dt < start_dt:
        ##    continue
        ##elif end_dt is not None and step_dt > end_dt:
        ##    continue

        ## Log RefET values at time step 
        logging.debug(
            'crop_day_loop(): PPT %.6f  Wind %.6f  Tdew %.6f ETref %.6f' % 
            (et_cell.weather['precip'][i], et_cell.weather['wind'][i], 
             et_cell.weather['tdew'][i], et_cell.refet['etref'][i]))
        ## Log climate values at time step         
        logging.debug(
            'crop_day_loop(): tmax %.6f  tmin %.6f  tmean %.6f  t30 %.6f' %
            (et_cell.climate['tmax_array'][i], et_cell.climate['tmin_array'][i], 
             et_cell.climate['tmean_array'][i], et_cell.climate['t30_array'][i]))

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
        foo_day.sdays = i + 1
        foo_day.doy = step_doy
        foo_day.year = step_dt.year
        foo_day.month = step_dt.month
        foo_day.day = step_dt.day
        foo_day.date = et_cell.refet['dates'][i]
        foo_day.tmax_orig = et_cell.weather['tmax'][i]
        foo_day.tdew = et_cell.weather['tdew'][i]
        foo_day.u2 = et_cell.weather['wind'][i]
        foo_day.precip = et_cell.weather['precip'][i]
        foo_day.etref = et_cell.refet['etref'][i]
        foo_day.tmean = et_cell.climate['tmean_array'][i]
        foo_day.tmin = et_cell.climate['tmin_array'][i]
        foo_day.tmax = et_cell.climate['tmax_array'][i]
        foo_day.snow_depth = et_cell.climate['snow_depth_array'][i]
        foo_day.t30 = et_cell.climate['t30_array'][i]
        ##foo_day.precip = et_cell.climate['precip_array'][i]


        ## DEADBEEF - Why make copies?
        foo_day.cgdd_0_lt = np.copy(et_cell.climate['main_cgdd_0_lt'])
        #foo_day.t30_lt = np.copy(et_cell.climate['main_t30_lt'])

        ## Compute RH from Tdew
        ## DEADBEEF - Why would tdew or tmax_original be < -90?
        ## DEADBEEF - This could be done in et_cell.set_daily_nldas_data() and
        ##   et_cell.set_daily_refet_data()
        if foo_day.tdew < -90 or foo_day.tmax_orig < -90:
            foo_day.rh_min = 30.0
        else:
            ## For now do not consider SVP over ice
            ## (it was not used in ETr or ETo computations, anyway)
            es_tdew = util.aFNEs(foo_day.tdew)
            es_tmax = util.aFNEs(foo_day.tmax_orig) 
            foo_day.rh_min = max(min(es_tdew / es_tmax * 100, 100), 0)
                
        ## Calculate Kcb, Ke, ETc
        compute_crop_et.compute_crop_et(data, et_cell, crop, foo, foo_day)

        ## Write vb-like output file for comparison
        if output_f:
            fmt = ('%10s %3s %9.3f %9.3f %9.3f %9.3f %9.3f '+
                   '%9.3f %9.3f %5d %9.3f %9.3f\n')
            values = (step_dt, step_doy, foo_day.etref, foo_day.precip, 
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
