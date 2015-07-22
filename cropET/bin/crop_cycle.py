#!/usr/bin/env python
import datetime
import logging
import math
import pprint
import os
import re
import sys

import numpy as np

import crop_et_data
import compute_crop_et
from initialize_crop_cycle import InitializeCropCycle
##import setup_crop

##COMPARE = False
COMPARE = True

def crop_cycle(data, et_cell, nsteps, basin_id, output_ws=''):
    """ """
    ## Following is for one crop grown back to back over entire ETr sequence
    ##
    ## do bare soil first, before looping through crops
    ## current curve file has 60 curves, so 44 is not correct relative to coefficients
    ##'''
    ##   ' start with crop type 44 (bare soil, winter mulch) and run through last crop first '<------ specific value for crop number
    ##   ' this is done to compute 'winter covers', which are bare soil, mulch and dormant turf,
    ##   ' before any crops are processed.  Bare soil is "crop" no. 44.
    ##'''
    ### parameters in PMControl, these values are for klamath
    ### currently used to populate crop_gdd_trigger_doy in
    ### data.ctrl[] dictionary, so probably not needed here
    ###cgdd_winter_doy = 274
    ###cgdd_main_doy = 1
    ##
    ##'''
    #### no curve for bare soil
    ##ctCount = 43  # bare soil
    ##ctCount = 1  # bare soil
    ##crop = et_cell.crop_params[ctCount] 
    ##print crop
    ##pprint(vars(crop))
    ##'''
    
    ##logging.debug('in crop_cycle()')

    ## crop loop through all crops, doesn't include bare soil??
    for crop_num, crop in sorted(et_cell.crop_params.items()):
        logging.debug('crop_day_loop():  Crop %s %s' % (crop_num, crop))
        logging.debug(
            'crop_day_loop():  Curve %s %s  Class %s  Flag %s' %
            (crop.curve_number, crop.curve_name,
             crop.class_number, et_cell.crop_flags[crop_num]))
        ##logging.debug('  Crop:  {0} {1}'.format(crop_num, crop))
        ##logging.debug('  Curve: {0} {1}'.format(
        ##    crop.curve_number, crop.curve_name))
        ##logging.debug('  Class: {}'.format(crop.class_number))
        ##logging.debug('  Flag:  {}'.format(et_cell.crop_flags[crop_num]))

        ## Check to see if crop/landuse is at station
        if not et_cell.crop_flags[crop_num]:
            logging.debug('    NOT USED')
            continue
        logging.debug('  GDD trigger DOY: {}'.format(crop.crop_gdd_trigger_doy))

        # 'foo' is holder of all these global variables for now
        foo = InitializeCropCycle()

        ##### TP04 try to access directly or rename locally
        ##### this reassigns data to simpler names, etc
        ## First time through for crop, load basic crop parameters and process climate data
        foo.crop_load(data, et_cell, crop)

        ## Write data for crop
        if COMPARE: 
            ## DEADBEEF - Don't include crop name in file name
            ##crop_nn = re.sub('[-"().,/~]', ' ', crop.name.lower())
            ##crop_nn = ' '.join(crop_nn.strip().split()).replace(' ', '_')
            ####crop_nn = crop.name.replace(' ','_').replace('/','_').replace('-','_')[:32]
            ##output_name = '%s_%s.%s' % (et_cell.cell_id, crop.class_number, crop_nn)

            output_name = '%s_%s.dat' % (et_cell.cell_id, crop.class_number)
            if output_ws:
                output_path = os.path.join(output_ws, output_name)
            else:
                output_path = os.path.join('cet', basin_id, 'py', output_name)
            fmt = '%10s %3s %9s %9s %9s %9s %9s %9s %9s %5s %9s %9s\n' 
            header = (
                '#     Date','DOY','PMETo','Pr.mm','T30','ETact',
                'ETpot','ETbas', 'Irrn','Seasn','Runof','DPerc')
            ## DEADBEEF - Should the file be kept open and the file object
            ##   passed to crop_day_loop() instead?
            with open(output_path, 'w') as output_f:
                output_f.write(fmt % header)
        else:
            output_path = None

        ##        
        crop_day_loop(data, et_cell, crop, foo, nsteps, output_path)


class DayData:
    def __init__(self):
        """ """
        ## Used in compute_crop_gdd(), needs to be persistant during day loop
        self.etref_array = np.zeros(30)

def crop_day_loop(data, et_cell, crop, foo, nsteps, output_path):
    """

    Args:
        data ():
        et_cell ():
        crop ():
        foo ():
        nsteps (int):
        output_path (str): file path

    Returns:
        None
    """
    ##logging.debug('crop_day_loop()')
    foo_day = DayData()

    ## Originally in ProcessClimate() in vb code
    if data.refet_type > 0:
        refet_array = et_cell.refet['ASCEPMStdETr']
    else:
        refet_array = et_cell.refet['ASCEPMStdETo']

    for i, ts in enumerate(et_cell.refet['Dates'][:nsteps]):
        ts_date = datetime.date(*ts[:3])
        ts_doy = int(ts_date.strftime('%j'))
        ##doy = ts[7]
        logging.debug('\ncrop_day_loop(): DOY %s  Date %s' % (ts_doy, ts_date))

        precip = et_cell.refet['Precip'][i]
        wind = et_cell.refet['Wind'][i]
        tdew = et_cell.refet['TDew'][i]
        #etr = et_cell.refet['ASCEPMStdETr'][i]
        eto = et_cell.refet['ASCEPMStdETo'][i]
        etref = refet_array[i]
        logging.debug(
            'crop_day_loop(): PPT %.6f  Wind %.6f  Tdew %.6f' % (precip, wind, tdew))
        logging.debug(
            'crop_day_loop(): ETo %.6f  ETref %.6f' % (eto, etref))

        # in original there was 80 lines of alternative Tmax/Tmin for climate change scenarios
        '''
         ' set TMax, TMin, TMean, T30, long-term T30, and long-term CGDD
         ' as a function of alternative TMax TMin option
         ' blank of zero is no use of alternative TMax and TMin data
         ' 1 is use of alternative TMax and TMin for annual crops only
         ' 2 is use of alternative TMax and TMin for perennial crops only
         ' 3 is use of alternative TMax and TMin for all crops 
        '''
        # ' default is no use of alternative TMax and TMin
        tmax = et_cell.climate['tmax_array'][i]
        tmin = et_cell.climate['tmin_array'][i]
        tmean = et_cell.climate['tmean_array'][i]
        t30 = et_cell.climate['t30_array'][i]
        # Precip converted to mm in process_climate()
        precip = et_cell.climate['precip'][i]        
        logging.debug(
            'crop_day_loop(): tmax %.6f  tmin %.6f  tmean %.6f  t30 %.6f' %
            (tmax, tmin, tmean, t30))

        ## Copies of these were made using loop
        cgdd_0_lt = np.copy(et_cell.climate['main_cgdd_0_lt'])
        t30_lt = np.copy(et_cell.climate['main_t30_lt'])

        #' this is done before calling ETc
        #' determine if this is a valid day (for use in assessing alfalfa cuttings in that file)
        #' use ETref to determine

        # some stuff here left out
        ### TP05 this has to do with printing output or mysterious shit I don't understand....skip for now
        # variables set validDaysPerYear & expectedYear, but seem unused
        # except for printing ???

        ## At very start for crop, set up for next season
        if not foo.in_season and foo.crop_setup_flag:
            foo.setup_crop(crop)

        ## At end of season for each crop, set up for nongrowing and dormant season
        #foo.dormant_setup_flag = True   # for testing SetupDormant()
        if not foo.in_season and foo.dormant_setup_flag:
            logging.debug(
                'crop_day_loop(): in_season[%s] dormant_setup_flag[%s]' % (
                foo.in_season, foo.dormant_setup_flag))
            foo.setup_dormant(data, et_cell, crop)
        logging.debug(
            'crop_day_loop(): in_season[%s]  crop_setup_flag[%s]  dormant_setup_flag[%s]' % (
            foo.in_season, foo.crop_setup_flag, foo.dormant_setup_flag))

        foo_day.sdays = i+1
        foo_day.doy = ts_doy
        foo_day.year = ts_date.year
        foo_day.month = ts_date.month
        foo_day.day = ts_date.day
        foo_day.date = et_cell.refet['Dates'][i]
        foo_day.tmax_original = et_cell.refet['TMax'][i]
        foo_day.tdew = tdew
        foo_day.wind = wind
        foo_day.etref = etref
        foo_day.tmean = tmean
        foo_day.tmin = tmin
        foo_day.tmax = tmax
        foo_day.snow_depth = et_cell.climate['snow_depth'][i]
        foo_day.cgdd_0_lt = cgdd_0_lt
        #foo_day.t30_lt = t30_lt
        foo_day.t30 = t30
        foo_day.precip = precip
        #print et_cell.climate.keys()

        ## Calculate Kcb, Ke, ETc
        #If Not compute_crop_et(T30) Then Return False
        compute_crop_et.compute_crop_et(
            t30, data, et_cell, crop, foo, foo_day)

        ## Write vb-like output file for comparison
        if COMPARE: 
            tup = (ts_date, ts_doy, etref, precip, t30, foo.etc_act, foo.etc_pot,
                   foo.etc_bas, foo.irr_simulated, foo.in_season, foo.sro,
                   foo.Dpr)
            fmt = '%10s %3s %9.3f %9.3f %9.3f %9.3f %9.3f %9.3f %9.3f %5d %9.3f %9.3f\n'
            with open(output_path, 'a') as output_f:
                output_f.write(fmt % tup)

        ## Write final output file variables to DEBUG file
        logging.debug(
            ('crop_day_loop(): ETref  %.6f  Precip %.6f  T30 %.6f') %
            (etref, precip, t30))
        logging.debug(
            ('crop_day_loop(): ETact  %.6f  ETpot %.6f   ETbas %.6f') %
            (foo.etc_act, foo.etc_pot, foo.etc_bas))
        logging.debug(
            ('crop_day_loop(): Runoff %.6f  DPerc %.6f') %
            (foo.sro, foo.Dpr))

def main():
    """ """
    pass
    # _test() loads the data for Klamath
    #data = cropet_data._test()
    #pprint(data.refet)

if __name__ == '__main__':
    main()
