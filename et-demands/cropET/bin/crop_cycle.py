#!/usr/bin/env python

import datetime
import logging
import multiprocessing as mp
import os

import numpy as np
import pandas as pd

import calculate_height
import compute_crop_et
import compute_crop_gdd
from initialize_crop_cycle import InitializeCropCycle
import kcb_daily
import sys

class DayData:
    def __init__(self):
        """ """

        # Used in compute_crop_gdd(), needs to be persistent during day loop
        
        self.etref_array = np.zeros(30)

def crop_cycle_mp(data, et_cell, mp_procs = 1):
    """Compute crop ET for all crops using multiprocessing

    crop_day_loop_mp() will unpack arguments and call crop_day_loop

    Args:
        data ():
        et_cell ():
        mp_procs (int): number of cores to use for multiprocessing
    """
    crop_count = 0
    crop_mp_list = []
    for crop_num, crop in sorted(et_cell.crop_params.items()):
        if et_cell.crop_flags[crop_num] != 0:

            # Force debug_flag false when multiprocessing
            crop_count += 1
            crop_mp_list.append([crop_count, data, et_cell, crop, False, mp_procs])
    results = []
    if crop_mp_list:
        pool = mp.Pool(mp_procs)
        results = pool.imap(crop_day_loop_mp, crop_mp_list, chunksize=1)
        pool.close()
        pool.join()
        del pool, results

def crop_cycle(data, et_cell, debug_flag = False, mp_procs = 1):
    """Compute crop ET for all crops

    Args:
        data ():
        et_cell ():
        debug_flag (bool): If True, write debug level comments to debug.txt

    Returns:
        None
    """
    crop_count = 0
    for crop_num, crop in sorted(et_cell.crop_params.items()):
        if et_cell.crop_flags[crop_num] == 0:
            if debug_flag:
                logging.debug('Crop %2d %s' % (crop_num, crop.name))
                logging.debug('  NOT USED')
            continue
        crop_count += 1
        crop_day_loop(crop_count, data, et_cell, crop, debug_flag, mp_procs)

def crop_day_loop_mp(tup):
    """Pool multiprocessing friendly crop_day_loop function

    mp.Pool needs all inputs are packed into single tuple
    Tuple is unpacked and and single processing version of function is called

    Args:
        crop_count: count of crop being computed
        data ():
        et_cell ():
        crop ():
        debug_flag (bool): If True, write debug level comments to debug.txt
        mp_procs (int):

    Returns:

    """
    return crop_day_loop(*tup)

def crop_day_loop(crop_count, data, et_cell, crop, debug_flag = False, mp_procs = 1):
    """Compute crop ET for each daily timestep

    Args:
        crop_count: count of crop being computed
        data ():
        et_cell ():
        crop ():
        debug_flag (bool): If True, write debug level comments to debug.txt
        mp_procs (int):

    Returns
        Bool
    """
    func_str = 'crop_day_loop()'
    if mp_procs == 1:
        logging.warning('Crop {} - {}'.format(crop.class_number, crop.name))
    if debug_flag:
        logging.debug(
            '{}:  Curve {} {}  Class {}  Flag {}'.format(
                func_str, crop.curve_number, crop.curve_name,
                crop.class_number, et_cell.crop_flags[crop.class_number]))
        logging.debug('  GDD trigger DOY: {}'.format(crop.gdd_trigger_doy))

    # 'foo' is holder of all these global variables for now
    
    foo = InitializeCropCycle()

    # First time through for crop, load basic crop parameters and process climate data

    foo.crop_load(data, et_cell, crop)

    # GetCO2 correction factors for each crop
    
    if data.co2_flag: foo.setup_co2(et_cell, crop)

    # Initialize crop data frame

    foo.setup_dataframe(et_cell)
    foo_day = DayData()
    foo_day.sdays = 0
    foo_day.doy_prev = 0

    # At very start for crop, set up for next season
        
    if not foo.in_season and foo.crop_setup_flag: foo.setup_crop(crop)

    for step_dt, step_doy in foo.crop_df[['doy']].iterrows():
        if debug_flag:
            logging.debug(
                '\n{}: DOY {}  Date {}'.format(
                    func_str, int(step_doy), step_dt.date()))

            # Log RefET values at time step

            logging.debug(('{}: PPT {:.6f}  Wind {:.6f}  ' +
                 'Tdew {:.6f} ETref {:.6f}').format(func_str, 
                    et_cell.climate_df.at[step_dt, 'ppt'],
                    et_cell.climate_df.at[step_dt, 'wind'],
                    et_cell.climate_df.at[step_dt, 'tdew'],
                    et_cell.refet_df.at[step_dt, 'etref']))

            # Log climate values at time step
            
            logging.debug(('{}: tmax {:.6f}  tmin {:.6f}  ' +
                 'tmean {:.6f}  t30 {:.6f}').format(func_str, 
                    et_cell.climate_df.at[step_dt, 'tmax'],
                    et_cell.climate_df.at[step_dt, 'tmin'],
                    et_cell.climate_df.at[step_dt, 'tmean'],
                    et_cell.climate_df.at[step_dt, 't30']))

        # At end of season for each crop, set up for non-growing and dormant season
        
        if not foo.in_season and foo.dormant_setup_flag:
            foo.setup_dormant(et_cell, crop)
        if debug_flag:
            logging.debug(
                '{}: in_season[{}]  crop_setup[{}]  dormant_setup[{}]'.format(
                    func_str, foo.in_season, foo.crop_setup_flag,
                    foo.dormant_setup_flag))

        # Track variables for each day
        # For now, cast all values to native Python types
        
        foo_day.sdays += 1
        foo_day.doy = int(step_doy)
        foo_day.year = int(step_dt.year)
        foo_day.month = int(step_dt.month)
        foo_day.day = int(step_dt.day)
        foo_day.date = step_dt
        foo_day.tdew = float(et_cell.climate_df.at[step_dt, 'tdew'])
        foo_day.u2 = float(et_cell.climate_df.at[step_dt, 'wind'])
        foo_day.precip = float(et_cell.climate_df.at[step_dt, 'ppt'])
        foo_day.rh_min = float(et_cell.climate_df.at[step_dt, 'rh_min'])
        foo_day.etref = float(et_cell.climate_df.at[step_dt, 'etref'])
        foo_day.snow_depth = float(et_cell.climate_df.at[step_dt, 'snow_depth'])
        if data.phenology_option == 0:
            foo_day.tmean = float(et_cell.climate_df.at[step_dt, 'tmean'])
            foo_day.tmin = float(et_cell.climate_df.at[step_dt, 'tmin'])
            foo_day.tmax = float(et_cell.climate_df.at[step_dt, 'tmax'])
            foo_day.t30 = float(et_cell.climate_df.at[step_dt, 't30'])
        elif data.phenology_option == 1:    # annual crops only
            if crop.is_annual:
                foo_day.tmean = float(et_cell.climate_df.at[step_dt, 'meant'])
                foo_day.tmin = float(et_cell.climate_df.at[step_dt, 'mint'])
                foo_day.tmax = float(et_cell.climate_df.at[step_dt, 'maxt'])
                foo_day.t30 = float(et_cell.climate_df.at[step_dt, '30t'])
            else:
                foo_day.tmean = float(et_cell.climate_df.at[step_dt, 'tmean'])
                foo_day.tmin = float(et_cell.climate_df.at[step_dt, 'tmin'])
                foo_day.tmax = float(et_cell.climate_df.at[step_dt, 'tmax'])
                foo_day.t30 = float(et_cell.climate_df.at[step_dt, 't30'])
        elif data.phenology_option == 2:    # perennial crops only
            if not crop.is_annual:
                foo_day.tmean = float(et_cell.climate_df.at[step_dt, 'meant'])
                foo_day.tmin = float(et_cell.climate_df.at[step_dt, 'mint'])
                foo_day.tmax = float(et_cell.climate_df.at[step_dt, 'maxt'])
                foo_day.t30 = float(et_cell.climate_df.at[step_dt, '30t'])
            else:
                foo_day.tmean = float(et_cell.climate_df.at[step_dt, 'tmean'])
                foo_day.tmin = float(et_cell.climate_df.at[step_dt, 'tmin'])
                foo_day.tmax = float(et_cell.climate_df.at[step_dt, 'tmax'])
                foo_day.t30 = float(et_cell.climate_df.at[step_dt, 't30'])
        else:    # both annual and perennial
            foo_day.tmean = float(et_cell.climate_df.at[step_dt, 'meant'])
            foo_day.tmin = float(et_cell.climate_df.at[step_dt, 'mint'])
            foo_day.tmax = float(et_cell.climate_df.at[step_dt, 'maxt'])
            foo_day.t30 = float(et_cell.climate_df.at[step_dt, '30t'])

        # Get CO2 correction factor for each day
        
        if data.co2_flag: foo_day.co2 = float(foo.co2.at[step_dt])

        # Compute crop growing degree days
        
        compute_crop_gdd.compute_crop_gdd(crop, foo, foo_day)

        # Calculate height of vegetation.  
        # Call was moved up to this point 12/26/07 for use in adj. Kcb and kc_max
        
        calculate_height.calculate_height(crop, foo, debug_flag)

        # Interpolate Kcb and make climate adjustment (for ETo basis)
        
        kcb_daily.kcb_daily(data, et_cell, crop, foo, foo_day, debug_flag)

        # Calculate Kcb, Ke, ETc
        
        compute_crop_et.compute_crop_et(data, et_cell, crop, foo, foo_day, debug_flag)

        # Retrieve values from foo_day and write to output data frame
        # Eventually let compute_crop_et() write directly to output df
        
        foo.crop_df.at[step_dt, 'et_act'] = foo.etc_act
        foo.crop_df.at[step_dt, 'et_pot'] = foo.etc_pot
        foo.crop_df.at[step_dt, 'et_bas'] = foo.etc_bas
        foo.crop_df.at[step_dt, 'kc_act'] = foo.kc_act
        foo.crop_df.at[step_dt, 'kc_bas'] = foo.kc_bas
        foo.crop_df.at[step_dt, 'irrigation'] = foo.irr_sim
        foo.crop_df.at[step_dt, 'runoff'] = foo.sro
        foo.crop_df.at[step_dt, 'dperc'] = foo.dperc
        foo.crop_df.at[step_dt, 'niwr'] = foo.niwr + 0
        foo.crop_df.at[step_dt, 'season'] = int(foo.in_season)
        foo.crop_df.at[step_dt, 'cutting'] = int(foo.cutting)

        # Write final output file variables to DEBUG file

        if debug_flag:
            logging.debug(
                ('{}: ETref  {:.6f}  Precip {:.6f}  T30 {:.6f}').format(
                    func_str, foo_day.etref, foo_day.precip, foo_day.t30))
            logging.debug(
                ('{}: ETact  {:.6f}  ETpot {:.6f}   ETbas {:.6f}').format(
                    func_str, foo.etc_act, foo.etc_pot, foo.etc_bas))
            logging.debug(
                ('{}: Irrig  {:.6f}  Runoff {:.6f}  ' +
                 'DPerc {:.6f}  NIWR {:.6f}').format(
                    func_str, foo.irr_sim, foo.sro, foo.dperc, foo.niwr))

        # Check that season started

        if foo_day.month == 12 and foo_day.day == 31:
            season_count = foo.crop_df.loc[
                str(foo_day.year):str(foo_day.year), 'season'].sum()
            if season_count == 0:
                logging.warning(
                    '  Crop {} - {} growing season never started'.format(
                        crop.class_number, foo_day.year))
            elif season_count == 1:
                logging.warning(
                    '  Crop {} - {} growing season active for 1 day'.format(
                        crop.class_number, foo_day.year))

    # Write output files
    
    if (data.cet_out['daily_output_flag'] or 
            data.cet_out['monthly_output_flag'] or
            data.cet_out['annual_output_flag'] or 
            data.gs_output_flag):
        write_crop_output(crop_count, data, et_cell, crop, foo)
    return True

def write_crop_output(crop_count, data, et_cell, crop, foo):
    """Write ET-Demands output files for each cell and crop

    Args:
        crop_count: count of crop being computed
        data ():
        et_cell ():
        crop ():
        foo ():
    """
    year_field = 'Year'
    month_field = 'Month'
    day_field = 'Day'
    doy_field = 'DOY'
    # print(dir(data))
    # print(dir(data.refet))

    #Build PMET type fieldname from input data (Eto or ETr)
    et_type=data.refet['fields']['etref']
    pmet_field='PM'+et_type

    precip_field = 'PPT'
    etact_field = 'ETact'
    etpot_field = 'ETpot'
    etbas_field = 'ETbas'
    irrig_field = 'Irrigation'
    season_field = 'Season'
    cutting_field = 'Cutting'
    runoff_field = 'Runoff'
    dperc_field = 'DPerc'
    niwr_field = 'NIWR'
    kc_field = 'Kc'
    kcb_field = 'Kcb'
    gs_start_doy_field = 'Start_DOY'
    gs_end_doy_field = 'End_DOY'
    gs_start_date_field = 'Start_Date'
    gs_end_date_field = 'End_Date'
    gs_length_field = 'GS_Length'

    # Merge crop and weather data frames to form daily output

    if (data.cet_out['daily_output_flag'] or 
            data.cet_out['monthly_output_flag'] or
            data.cet_out['annual_output_flag'] or 
            data.gs_output_flag):
        daily_output_df = pd.merge(
            foo.crop_df, et_cell.climate_df[['ppt']],
            # foo.crop_df, et_cell.climate_df[['ppt', 't30']],
            left_index=True, right_index=True)

        # Rename output columns
        
        daily_output_df.index.rename('Date', inplace=True)
        daily_output_df[year_field] = daily_output_df.index.year
        daily_output_df = daily_output_df.rename(columns={
            'doy': doy_field, 'ppt': precip_field, 'etref': pmet_field,
            'et_act': etact_field, 'et_pot': etpot_field,
            'et_bas': etbas_field, 'kc_act': kc_field, 'kc_bas': kcb_field,
            'niwr': niwr_field, 'irrigation': irrig_field,
            'runoff': runoff_field, 'dperc': dperc_field,
            'season': season_field, 'cutting': cutting_field})
            
    # Compute monthly and annual stats before modifying daily format below
    
    if data.cet_out['monthly_output_flag']:
        monthly_resample_func = {
            pmet_field: np.sum, etact_field: np.sum, etpot_field: np.sum,
            etbas_field: np.sum, kc_field: np.mean, kcb_field: np.mean,
            niwr_field: np.sum, precip_field: np.sum, irrig_field: np.sum,
            runoff_field: np.sum, dperc_field: np.sum, season_field: np.sum,
            cutting_field: np.sum}
        # dri dm approach produces 'TypeError: ("'dict' object is not callable", 
        # a u'occurred at index DOY')
        monthly_output_df = daily_output_df.resample('MS').apply(monthly_resample_func)
    if data.cet_out['annual_output_flag']:
        annual_resample_func = {
            pmet_field: np.sum, etact_field: np.sum, etpot_field: np.sum,
            etbas_field: np.sum, kc_field: np.mean, kcb_field: np.mean,
            niwr_field: np.sum, precip_field: np.sum, irrig_field: np.sum,
            runoff_field: np.sum, dperc_field: np.sum, season_field: np.sum,
            cutting_field: np.sum}
        # dri dm approach produces 'TypeError: ("'dict' object is not callable", 
        # a u'occurred at index DOY')
        annual_output_df = daily_output_df.resample('AS').apply(annual_resample_func)
            
    # Get growing season start and end DOY for each year
    # Compute growing season length for each year
    
    if data.gs_output_flag:
        # dri dm approach produces 'TypeError: ("'dict' object is not callable", 
        # a u'occurred at index DOY')
        gs_output_df = daily_output_df.resample('AS').apply({year_field: np.mean})
        gs_output_df[gs_start_doy_field] = np.nan
        gs_output_df[gs_end_doy_field] = np.nan
        gs_output_df[gs_start_date_field] = None
        gs_output_df[gs_end_date_field] = None
        gs_output_df[gs_length_field] = np.nan
        for year_i, (year, group) in enumerate(daily_output_df.groupby([year_field])):
            if not np.any(group[season_field].values):
                logging.debug('  Skipping, season flag was never set to 1')
                continue
            else:
                season_diff = np.diff(group[season_field].values)
                try:
                    start_i = np.where(season_diff == 1)[0][0] + 1
                    # gs_output_pd.set_value(
                    #     group.index[0], gs_start_doy_field,
                    #     int(group.ix[start_i, doy_field]))
                    # Replacement for set_value Future Warning
                    gs_output_df.at[group.index[0], gs_start_doy_field] = int(group.ix[start_i, doy_field])
                except:
                    # gs_output_pd.set_value(
                    #     group.index[0], gs_start_doy_field,
                    #     int(min(group[doy_field].values)))
                    #Replacement for set_value Future Warning
                    gs_output_df.at[group.index[0], gs_start_doy_field] = int(min(group[doy_field].values))
                try:
                    end_i = np.where(season_diff == -1)[0][0] + 1
                    # gs_output_pd.set_value(
                    #     group.index[0], gs_end_doy_field,
                    #     int(group.ix[end_i, doy_field]))
                    # Replacement for set_value Future Warning
                    gs_output_df.at[group.index[0], gs_end_doy_field] = int(group.ix[end_i, doy_field])
                except:
                    # gs_output_pd.set_value(
                    #     group.index[0], gs_end_doy_field,
                    #     int(max(group[doy_field].values)))
                    # Replacement for set_value Future Warning
                    gs_output_df.at[group.index[0], gs_end_doy_field] = int(max(group[doy_field].values))
                del season_diff
            # gs_output_pd.set_value(
            #     group.index[0], gs_length_field,
            #     int(sum(group[season_field].values)))
            # Replacement for set_value Future Warning
            gs_output_df.at[group.index[0], gs_length_field] = int(sum(group[season_field].values))

    if data.cet_out['data_structure_type'].upper() == 'DRI':
        base_columns = []
        open_mode = 'w'
        print_index = True
        print_header = True
    else:    # RDB
        base_columns = ['Crop Num', 'Crop Name', 'Date']
        if crop_count == 1:
            open_mode = 'w'
            print_header = True
        else:
            open_mode = 'a'
            print_header = False
        print_index = False

    # Write daily cet
    
    if data.cet_out['daily_output_flag']:
        daily_output_df[year_field] = daily_output_df.index.year
        daily_output_df[month_field] = daily_output_df.index.month
        daily_output_df[day_field] = daily_output_df.index.day
        
        # format date attributes if values are formatted
                    
        if data.cet_out['daily_float_format'] is not None:
            daily_output_df[year_field] = daily_output_df[year_field].map(lambda x: ' %4d' % x)
            daily_output_df[month_field] = daily_output_df[month_field].map(lambda x: ' %2d' % x)
            daily_output_df[day_field] = daily_output_df[day_field].map(lambda x: ' %2d' % x)
            daily_output_df[doy_field] = daily_output_df[doy_field].map(lambda x: ' %3d' % x)

        # This will convert negative "zeros" to positive
        
        daily_output_df[niwr_field] = np.round(daily_output_df[niwr_field], 6)
        # daily_output_df[niwr_field] = np.round(daily_output_df[niwr_field].values, 6)
        daily_output_df[season_field] = daily_output_df[season_field].map(lambda x: ' %1d' % x)
        if data.cet_out['data_structure_type'].upper() == 'DRI':
            daily_output_path = os.path.join(data.cet_out['daily_output_ws'], 
                 data.cet_out['name_format'].replace('%c', '%02d' % int(crop.class_number)) % et_cell.cell_id)
        else:    # RDB
            daily_output_path = os.path.join(data.cet_out['daily_output_ws'], 
                data.cet_out['name_format'].replace('%c', '').replace('__', '_') % et_cell.cell_id)
            daily_output_df['Crop Num'] = crop.class_number
            daily_output_df['Crop Name'] = crop.name

        # Set output column order

        daily_output_columns = base_columns + \
            [year_field, month_field, day_field, doy_field, pmet_field,
            etact_field, etpot_field, etbas_field, kc_field, kcb_field,
            precip_field, irrig_field, runoff_field, dperc_field,
            niwr_field, season_field]
            
        # Remove these (instead of appending) to preserve column order
        
        if not data.kc_flag:
            daily_output_columns.remove(kc_field)
            daily_output_columns.remove(kcb_field)
        if not data.niwr_flag:
            daily_output_columns.remove(niwr_field)
            
        # Most crops do not have cuttings, so append if needed
        
        if data.cutting_flag and crop.cutting_crop:
            daily_output_df[cutting_field] = daily_output_df[cutting_field].map(
                lambda x: ' %1d' % x)
            daily_output_columns.append(cutting_field)
            
        with open(daily_output_path, open_mode) as daily_output_f:
            if data.cet_out['data_structure_type'].upper() == 'DRI': 
                daily_output_f.write('# {0:2d} - {1}\n'.format(crop.class_number, crop.name))
            else:    # RDB
                daily_output_df.reset_index(inplace = True)
            daily_output_df.to_csv(daily_output_f, header = print_header, 
                index = print_index, sep = ',', columns = daily_output_columns,
                float_format = data.cet_out['daily_float_format'], 
                date_format = data.cet_out['daily_date_format'])
        del daily_output_df, daily_output_path, daily_output_columns

    # Write monthly cet

    if data.cet_out['monthly_output_flag']:
        monthly_output_df[year_field] = monthly_output_df.index.year
        monthly_output_df[month_field] = monthly_output_df.index.month
        
        # format date attributes if values are formatted
                    
        if data.cet_out['monthly_float_format'] is not None:
            monthly_output_df[year_field] = monthly_output_df[year_field].map(lambda x: ' %4d' % x)
            monthly_output_df[month_field] = monthly_output_df[month_field].map(lambda x: ' %2d' % x)
            monthly_output_df[season_field] = monthly_output_df[season_field].map(lambda x: ' %2d' % x)
        if data.cet_out['data_structure_type'].upper() == 'DRI':
            monthly_output_path = os.path.join(data.cet_out['monthly_output_ws'], data.cet_out['name_format'].replace('%c', '%02d' % int(crop.class_number)) % et_cell.cell_id)
        else:    # RDB
            monthly_output_path = os.path.join(data.cet_out['monthly_output_ws'], data.cet_out['name_format'].replace('%c', '').replace('__', '_') % et_cell.cell_id)
            monthly_output_df['Crop Num'] = crop.class_number
            monthly_output_df['Crop Name'] = crop.name
        monthly_output_columns = base_columns + \
            [year_field, month_field, pmet_field, etact_field, etpot_field,
            etbas_field, kc_field, kcb_field, precip_field, irrig_field,
            runoff_field, dperc_field, niwr_field,
            season_field]
        if data.cutting_flag and crop.cutting_crop:
            monthly_output_df[cutting_field] = monthly_output_df[cutting_field].map(
                lambda x: ' %1d' % x)
            monthly_output_columns.append(cutting_field)
        with open(monthly_output_path, open_mode) as monthly_output_f:
            if data.cet_out['data_structure_type'].upper() == 'DRI': 
                monthly_output_f.write('# {0:2d} - {1}\n'.format(crop.class_number, crop.name))
            else:    # RDB
                monthly_output_df.reset_index(inplace = True)
            monthly_output_df.to_csv(monthly_output_f, header = print_header, 
                index = print_index, sep = ',', columns = monthly_output_columns,
                float_format = data.cet_out['monthly_float_format'], date_format = data.cet_out['monthly_date_format'])
        del monthly_output_df, monthly_output_path, monthly_output_columns

    # Write annual cet
    
    if data.cet_out['annual_output_flag']:
        annual_output_df[year_field] = annual_output_df.index.year
        annual_output_df[season_field] = annual_output_df[season_field].map(lambda x: ' %3d' % x)
        if data.cet_out['data_structure_type'].upper() == 'DRI':
            annual_output_path = os.path.join(data.cet_out['annual_output_ws'], data.cet_out['name_format'].replace('%c', '%02d' % int(crop.class_number)) % et_cell.cell_id)
        else:    # RDB
            annual_output_path = os.path.join(data.cet_out['annual_output_ws'], data.cet_out['name_format'].replace('%c', '').replace('__', '_') % et_cell.cell_id)
            annual_output_df['Crop Num'] = crop.class_number
            annual_output_df['Crop Name'] = crop.name
        annual_output_columns = base_columns + \
            [year_field, pmet_field, etact_field, etpot_field, etbas_field,
            kc_field, kcb_field, precip_field, irrig_field, runoff_field,
            dperc_field, niwr_field, season_field]
        try: annual_output_columns.remove('Date')
        except: pass
        if data.cutting_flag and crop.cutting_crop:
            annual_output_df[cutting_field] = annual_output_df[cutting_field].map(
                lambda x: ' %2d' % x)
            annual_output_columns.append(cutting_field)
        with open(annual_output_path, open_mode) as annual_output_f:
            if data.cet_out['data_structure_type'].upper() == 'DRI': 
                annual_output_f.write('# {0:2d} - {1}\n'.format(crop.class_number, crop.name))
            else:    # RDB
                annual_output_df.reset_index(inplace = True)
            annual_output_df.to_csv(annual_output_f, header = print_header, 
                index = False, sep = ',', columns = annual_output_columns,
                float_format = data.cet_out['annual_float_format'], date_format = data.cet_out['annual_date_format'])
        del annual_output_df, annual_output_path, annual_output_columns

    # Write growing season statistics
    
    if data.gs_output_flag:
        def doy_2_date(test_year, test_doy):
            try:
                return datetime.datetime.strptime(
                    '{0}_{1}'.format(int(test_year),
                    int(test_doy)), '%Y_%j').date().isoformat()
            except:
                return 'None'
        gs_output_df[gs_start_date_field] = gs_output_df[
            [year_field, gs_start_doy_field]].apply(
                lambda s: doy_2_date(*s), axis=1)
        gs_output_df[gs_end_date_field] = gs_output_df[
            [year_field, gs_end_doy_field]].apply(
                lambda s: doy_2_date(*s), axis=1)
        if data.gs_name_format is None:
            # default filename spec

            gs_output_path = os.path.join(
                data.gs_output_ws, '{0}_gs_crop_{1:02d}.csv'.format(
                    et_cell.cell_id, int(crop.class_number)))
        else:
            # user filename spec or function of cet name spec

            gs_output_path = os.path.join(data.gs_output_ws, 
                data.gs_name_format.replace('%c', '%02d' % int(crop.class_number)) % et_cell.cell_id)
        gs_output_columns = [
            year_field, gs_start_doy_field, gs_end_doy_field,
            gs_start_date_field, gs_end_date_field, gs_length_field]
        with open(gs_output_path, 'w') as gs_output_f:
            gs_output_f.write(
                '# {0:2d} - {1}\n'.format(crop.class_number, crop.name))
            gs_start_doy = int(round(gs_output_df[gs_start_doy_field].mean()))
            gs_end_doy = int(round(gs_output_df[gs_end_doy_field].mean()))
            gs_start_dt = datetime.datetime.strptime(
                '2001_{:03d}'. format(gs_start_doy), '%Y_%j')
            gs_end_dt = datetime.datetime.strptime(
                '2001_{:03d}'. format(gs_end_doy), '%Y_%j')
            gs_output_f.write(
                '# Mean Start Date: {dt.month}/{dt.day}  ({doy})\n'.format(
                    dt=gs_start_dt, doy=gs_start_doy))
            gs_output_f.write(
                '# Mean End Date:   {dt.month}/{dt.day}  ({doy})\n'.format(
                    dt=gs_end_dt, doy = gs_end_doy))
            gs_output_df.to_csv(
                gs_output_f, sep = ',', columns = gs_output_columns,
                date_format = '%Y', index = False)
        del gs_output_df, gs_output_path, gs_output_columns

if __name__ == '__main__':
    pass
