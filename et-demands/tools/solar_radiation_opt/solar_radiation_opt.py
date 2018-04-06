#--------------------------------
# Name:         solar_radiation_opt.py
# Purpose:      Thornton-Running Monte Carlo Optimization
# Author:       Charles Morton
# Created       2015-12-08
# Python:       2.7
#--------------------------------

import argparse
import logging
import os
import datetime
from time import clock

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import emprso_w_tr

import solar_config

def main(ts_ini_name = None, sheet_delim = None, missing_data_value = 'NaN', 
        elevation = None, latitude = None, longitude = None,
        comparison_flag = False, save_temp_flag = False,
        mc_iterations = None, debug_flag = True):
    """Solar Radiation Calibration

    Args:
        file_name (str): file_name to process
        cfg.elevation (float): station elevation [m]
        cfg.latitude (float): station longitude [decimal degrees]
        cfg.longitude (float): station longitude [decimal degrees]
        comparison_flag (bool): if True,
        save_temp_flag: boolean
        mc_iterations (int):
        debug_flag (bool): if True, enable debug level logging

    Returns:
        None
    """
    
    # determine if ts_ini_name is a time series file or an ini file

    if ts_ini_name is None:
        file_name = None
    else:
        ext = os.path.splitext(ts_ini_name)[1][1:]
        if ext != 'ini' and ext != 'cfg':
            file_name = ts_ini_name
            ts_ini_name = None
    if ts_ini_name is None:
        file_path, sheet_delim = get_tsfile_path(file_name, sheet_delim)

        # set configuration with hard wired attributes
        
        cfg = solar_config.SolarConfig()
        cfg.set_solar_ini(sheet_delim, elevation, latitude, longitude, missing_data_value)
        cfg.file_path = file_path
        cfg.sheet_delim = sheet_delim
        if '.xls' in file_path: cfg.file_type = 'xls'
    else:
        # read ini file

        cfg = solar_config.SolarConfig()
        cfg.read_solar_ini(ts_ini_name, debug_flag)
    ext = '.' + os.path.splitext(cfg.file_path)[1][1:]
    if comparison_flag:
        file_name = cfg.file_path.replace(ext, '_Processed_Comparison')
    else:
        file_name = cfg.file_path.replace(ext, '_Processed_Optimazation')
    if debug_flag:
        # File Logger

        logging.basicConfig(level = logging.DEBUG, 
            format='%(message)s', filemode = 'w', 
            filename = file_name + '_log.txt')
                
        # Display Logger
        
        log_console = logging.StreamHandler()
        log_console.setLevel(logging.DEBUG)
        log_console.setFormatter(logging.Formatter('%(message)s'))
        logging.getLogger('').addHandler(log_console)
    else:
        logging.basicConfig(level=logging.INFO, format='%(message)s')
    logging.info('\nOptimizing Thornton-Running Coefficients\n')

    # computed column names

    doy_col = 'DOY'    
    tdelta_col = 'Tdelta'
    tmonth_col = 'Tmonth'
    rs_month_col = 'Rs_month'

    # USER VARIABLES

    rs_watts_flag = False

    # parse meta data

    if cfg.elevation is None:
        cfg.elevation = float(raw_input(
            'Specify station elevation [meters]: '))
    if cfg.latitude is None:
        cfg.latitude = float(raw_input(
            'Specify station latitude [decimal degrees (N)]: '))
    if cfg.longitude is None:
        cfg.longitude = float(raw_input(
            'Specify station longitude [decimal degrees (W)]: '))
    if mc_iterations is None:
        mc_iterations = float(raw_input(
            'Specify number of Monte Carlo iterations: '))

    # Read data

    # Get list of 0 based line numbers to skip
    # Ignore header but assume header was set as 1's based index
    data_skip = [i for i in range(cfg.header_lines) if i + 1 <> cfg.names_line]
    if cfg.file_type == 'xls':
        data_df = pd.read_excel(cfg.file_path,  sheetname = cfg.sheet_delim, 
            header = cfg.names_line - 1, skip_rows = data_skip, 
            na_values = cfg.missing_data_value)
    else:
        data_df = pd.read_table(cfg.file_path, sep = cfg.sheet_delim, 
            engine = 'python', header = cfg.names_line - 1, 
            skiprows = data_skip, na_values = cfg.missing_data_value)

    # Convert date strings to datetimes and index on date
    
    if cfg.input_met['fields']['date'] is not None:
        if cfg.input_met['fields']['date'] in data_df.columns:
            data_df['Date'] = pd.to_datetime(data_df[cfg.input_met['fields']['date']])
        else:    # this for case where YMD an ini is not used with YMD
            data_df['Date'] = data_df[[cfg.input_met['fields']['year'], \
                cfg.input_met['fields']['month'], cfg.input_met['fields']['day']]].apply(
                lambda s : datetime.datetime(*s),axis = 1)
    else:
        data_df['Date'] = data_df[[cfg.input_met['fields']['year'], \
            cfg.input_met['fields']['month'], cfg.input_met['fields']['day']]].apply(
            lambda s : datetime.datetime(*s),axis = 1)
    data_df.set_index('Date', inplace = True)
    if not cfg.start_dt is None and not cfg.end_dt is None:
        # truncate data to user period
        
        data_df = data_df.truncate(before = cfg.start_dt, after = cfg.end_dt)
    
    # print "index\n", data_df.index
    # print data_df.head(2)
    # print data_df.tail(2)
    num_lines = len(data_df.index)
        
    # Check/modify units
        
    for field_key, field_units in cfg.input_met['units'].items():
        # print "units for", field_key, "are", field_units
        if field_units is None:
            continue
        elif field_units.lower() in ['c', 'mj/m2', 'mj/m^2', 'mj/m2/day', 'mj/m^2/day', 'mj/m2/d', 'mj/m^2/d']:
            continue
        elif field_units.lower() == 'f':
            data_df[cfg.input_met['fields'][field_key]] -= 32
            data_df[cfg.input_met['fields'][field_key]] /= 1.8
        elif field_units.lower() in ['w/m2', 'w/m^2']:
            data_df[cfg.input_met['fields'][field_key]] *= 0.0864
        elif field_units.lower() in ['cal/cm2', 'cal/cm2/d', 'cal/cm2/day', 'cal/cm^2/d', 'cal/cm^2/day', 'langley']:
            data_df[cfg.input_met['fields'][field_key]] *= 0.041868
        else:
            logging.error('\n ERROR: Unknown {0} units {1}'.format(field_key, field_units) + ' input met data')
            return false

    # Assign month and DOY columns to data frame

    data_df[cfg.input_met['fields']['year']] = data_df.index.year
    data_df[cfg.input_met['fields']['month']] = data_df.index.month
    data_df[cfg.input_met['fields']['day']] = data_df.index.day
    data_df[doy_col] = data_df.index.dayofyear
    print data_df.head(5)
    print data_df.tail(5)

    # Compute pressure kPa
    
    # 5.26 changed to 5.255114352 to improve vb.net to py comparisons

    # p = (2.406 - 0.0000534 * cfg.elevation) ** 5.26
    # p = (2.406 - 0.0000534 * cfg.elevation) ** 5.255114352
    p = (2.406 - 0.0000534 * cfg.elevation) ** 5.255114352

    # FAO converting watts into mj m2 d
    
    if rs_watts_flag: data_df[cfg.input_met['fields']['rs']] *= 0.0864

    # Mean monthly difference between Tmax and Tmin for T-R
    
    data_df[tdelta_col] = data_df[cfg.input_met['fields']['tmax']] - data_df[cfg.input_met['fields']['tmin']]
    tdelta_monthly = data_df[[cfg.input_met['fields']['month'], tdelta_col]].groupby(cfg.input_met['fields']['month']).mean()
    tdelta_monthly.rename(columns = {tdelta_col:tmonth_col}, inplace = True)
    tdelta_monthly.reset_index(level = 0, inplace = True)
    
    # Join mean monthly tdelta back to main table
    # Date index is dropped by merge, so save it before merging
    
    data_df = data_df.reset_index()
    data_df = pd.merge(data_df, tdelta_monthly, on = cfg.input_met['fields']['month'])
    data_df = data_df.set_index('Date')

    # Apply Limits on Variables, rhmax, rhmin, tmax, tmin, rs, wind, rh

    data_df[data_df[cfg.input_met['fields']['tmax']] < -40] = np.nan
    data_df[data_df[cfg.input_met['fields']['tmax']] > 60] = np.nan
    data_df[data_df[cfg.input_met['fields']['tmin']] < -40] = np.nan
    data_df[data_df[cfg.input_met['fields']['tmin']] > 60] = np.nan

    # Calculate all secondary variables as separate arrays
    
    eo_tmax = 0.6108 * np.exp((17.27 * data_df[cfg.input_met['fields']['tmax']]) / (data_df[cfg.input_met['fields']['tmax']] + 237.3))
    eo_tmin = 0.6108 * np.exp((17.27 * data_df[cfg.input_met['fields']['tmin']]) / (data_df[cfg.input_met['fields']['tmin']] + 237.3))
    ea = 0.6108 * np.exp((17.27 * data_df[cfg.input_met['fields']['tdew']]) / (data_df[cfg.input_met['fields']['tdew']] + 237.3))
    tdew = (116.91 + 237.3 * np.log(ea)) / (16.78 - np.log(ea))
    tmin_tdew = data_df[cfg.input_met['fields']['tmin']] - data_df[cfg.input_met['fields']['tdew']]
    # print "eo_tmax, eo_tmin, ea, tdew, tmin_tdew"
    # print eo_tmax, eo_tmin, ea, tdew, tmin_tdew

    # MJ m-2 d-1
    
    if comparison_flag:
        rso_d, rs_custom_tr = emprso_w_tr.emprso_w_tr(
            cfg.latitude, p, ea, data_df[doy_col].values,
            data_df[cfg.input_met['fields']['month']].values, data_df[tdelta_col].values,
            b0 = 0.015690, b1 = 0.207780, b2 = -0.174350)
            # b0 = 0.029805, b1 = 0.178585, b2 = -0.24383)
    rso_d, rs_standard_tr = emprso_w_tr.emprso_w_tr(
        cfg.latitude, p, ea, data_df[doy_col].values,
        data_df[cfg.input_met['fields']['month']].values, data_df[tdelta_col].values,
        b0 = 0.031, b1 = 0.201, b2 = -0.185)

    # Pull out numpy array of measured solar from data frame
    
    rs_meas = data_df[cfg.input_met['fields']['rs']].values
    rs_mask = np.isfinite(rs_meas) & np.isfinite(rs_standard_tr)
    rs_max = max(rs_meas[rs_mask])

    # Calculate monthly means for rs and standard param rs_tr
    
    rs_monthly = data_df[[cfg.input_met['fields']['month'], cfg.input_met['fields']['rs']]].groupby(cfg.input_met['fields']['month']).mean()
    rs_monthly.rename(columns = {cfg.input_met['fields']['rs']: rs_month_col}, inplace = True)
    rs_monthly.reset_index(level = 0, inplace = True)

    # Join mean monthly Rs back to main table
    
    data_df = data_df.reset_index()
    data_df = pd.merge(data_df, rs_monthly, on = cfg.input_met['fields']['month'])
    data_df = data_df.set_index('Date')
    rs_tr_standard_monthly = np.zeros(12)
    rs_tr_custom_monthly = np.zeros(12)
    for month_i, month in enumerate(range(1,13)):
        month_mask = (data_df[cfg.input_met['fields']['month']].values == month)
        rs_tr_standard_monthly[month_i] = np.nanmean(rs_standard_tr[month_mask])
        if comparison_flag:
            rs_tr_custom_monthly[month_i] = np.nanmean(rs_custom_tr[month_mask])

    # Save updated data to a new workbook
    
    # save_temp_flag = False
    if save_temp_flag:
        temp_df = data_df.copy().sort_index()
        temp_df = temp_df.reset_index()
        ext = '.' + os.path.splitext(cfg.file_path)[1][1:]
        output_path = cfg.file_path.replace(ext, '_temp' + ext)
        if '.xls' in cfg.file_path.lower():
            writer = pd.ExcelWriter(output_path, datetime_format = 'yyyy-mm-dd')
            temp_df.to_excel(writer, sheet_name = cfg.sheet_delim, index = False)
            writer.save()
            del writer
        else:
            temp_df.to_csv(output_path, sep = cfg.sheet_delim, index = False)
        del temp_df

    # Compute statistics
    # Correlation of monthly values?
    
    tr_standard_corr = np.corrcoef(rs_monthly[rs_month_col].values, rs_tr_standard_monthly)[0,1]
    tr_standard_rmse = rmse(rs_standard_tr, data_df[cfg.input_met['fields']['rs']].values)
    tr_standard_perct_bias = pct_bias(rs_standard_tr, data_df[cfg.input_met['fields']['rs']].values)

    logging.info(
        ('\nStandard parameter RMSE is {0:.6f} and has a correlation ' +
         'of {1:.6f}').format(tr_standard_rmse, tr_standard_corr))

    if comparison_flag:
        # Correlation of monthly values?
        tr_custom_corr = np.corrcoef(
            rs_monthly[rs_month_col].values, rs_tr_custom_monthly)[0, 1]
        tr_custom_rmse = rmse(rs_custom_tr, data_df[cfg.input_met['fields']['rs']].values)
        tr_custom_perct_bias = pct_bias(rs_custom_tr, data_df[cfg.input_met['fields']['rs']].values)
        logging.info(
            ('Custom parameter RMSE is {0:.6f} and has a correlation ' +
             'of {1:.6f}').format(tr_custom_rmse, tr_custom_corr))

        # DISPLAY OUTPUT IN PLOTS
        
        f, axarr = plt.subplots(2, 2, figsize = (10, 10))
        months = range(1, 13)

        # Mean Monthly Standard vs Measured
        
        axarr[0, 0].plot(months, rs_monthly[rs_month_col].values, 'b', label = 'Measured')
        axarr[0, 0].plot(months, rs_tr_standard_monthly, 'r', label = 'TR Standard')
        axarr[0, 0].set_ylabel('Rs (MJ/m2/d)')
        axarr[0, 0].set_xlabel('Month')
        axarr[0, 0].set_title('Mean Monthly Standard vs Measured')
        axarr[0, 0].legend(loc=3)
        axarr[0, 0].set_xlim([1, 12])

        # Daily Standard vs Measured
        
        axarr[0, 1].scatter(rs_meas, rs_standard_tr, s = 2, c = 'b', alpha = 0.3)
        axarr[0, 1].set_ylabel('Estimated (MJ/m2/d)')
        axarr[0, 1].set_xlabel('Observed (MJ/m2/d)')
        axarr[0, 1].set_title('Daily Standard vs Measured')
        lsrl_standard_eqn = np.polyfit(rs_meas[rs_mask], rs_standard_tr[rs_mask], deg = 1)
        axarr[0, 1].plot(
            rs_meas[rs_mask],
            lsrl_standard_eqn[0] * rs_meas[rs_mask] + lsrl_standard_eqn[1],
            color='red')
        axarr[0, 1].plot([0, rs_max], [0, rs_max], 'k--')

        # Mean Monthly Standard vs Custom

        axarr[1,0].plot(months, rs_monthly[rs_month_col].values, 'b', label = 'Measured')
        axarr[1,0].plot(months, rs_tr_custom_monthly, 'r', label = 'TR Custom')
        axarr[1, 0].set_ylabel('Rs (w/m2)')
        axarr[1, 0].set_xlabel('Month')
        axarr[1, 0].set_title('Mean Monthly Optimized vs Measured')
        axarr[1, 0].legend(loc=3)
        axarr[1, 0].set_xlim([1, 12])

        # Daily Custom vs Measured
        
        axarr[1,1].scatter(rs_meas, rs_custom_tr, s = 2, c = 'b', alpha = 0.3)
        axarr[1, 1].set_ylabel('Estimated (MJ/m2/d)')
        axarr[1, 1].set_xlabel('Observed (MJ/m2/d)')
        axarr[1, 1].set_title('Daily Optimized vs Measured')
        lsrl_custom_eqn = np.polyfit(
            rs_meas[rs_mask], rs_custom_tr[rs_mask], deg=1)
        axarr[1, 1].plot(
            rs_meas[rs_mask],
            lsrl_custom_eqn[0] * rs_meas[rs_mask] + lsrl_custom_eqn[1],
            color = 'red')
        axarr[1, 1].plot([0, rs_max], [0, rs_max], 'k--')
        avg_diff_standard = np.nanmean(rs_standard_tr / rs_meas)
        avg_diff_opt = np.nanmean(rs_custom_tr / rs_meas)
        logging.info(
            ('The average of (standard/observed) on a daily basis ' +
             'is {0:.6f}').format(avg_diff_standard))
        logging.info(
            ('The average of (optimized/observed) on a daily basis ' +
             'is {0:.6f}').format(avg_diff_opt))

        # Print line equation
        
        logging.info(
            'For standard LSRL: y = {0:>.4f}x + {1:0.4f}'.format(
                lsrl_standard_eqn[0], lsrl_standard_eqn[1]))
        logging.info(
            'For custom LSRL: y = {0:>.4f}x + {1:0.4f}'.format(
                lsrl_custom_eqn[0], lsrl_custom_eqn[1]))
        logging.info('\n')
        plt.savefig(file_name + '.jpg')
        plt.show()
        plt.close()
        del f, axarr
    else:
        # Monte Carlo Analysis
        
        b0 =  0.031 + (0.031 * 0.2) * np.random.randn(mc_iterations)
        b1 = 0.201 + (0.201 * 0.2) * np.random.randn(mc_iterations)
        b2 = -0.185 + (-0.185 * 0.2) * np.random.randn(mc_iterations)
        mc_tr_matrix = np.zeros((mc_iterations, num_lines))
        mc_tr_monthly = np.zeros((mc_iterations, 12))
        mc_corr_vector = np.zeros(mc_iterations)
        mc_rmse_vector = np.zeros(mc_iterations)
        mc_pct_bias_vector = np.zeros(mc_iterations)
        logging.info('\nMonte Carlo Iterations: {0}'.format(mc_iterations))
        mc_clock = clock()
        rmse_min = 1000
        mc_width = len(str(mc_iterations))
        logging.debug(
            ('  {0:>{width}s}  {1:>8s}  {2:>8s} {3:>8s} {4:>8s}').format(
             'MC', 'RMSE', 'B0', 'B1', 'B2', width=mc_width))
        for mc_i in range(mc_iterations):
            if mc_i % 1000 == 0: logging.info('  {0:>{width}d}'.format(mc_i, width=mc_width))
            
            # Eqn 15 Empirical fitting coefficient
            
            b = b0[mc_i] + b1[mc_i] * np.exp(b2[mc_i] * data_df[tdelta_col].values)
            
            # Eqn 14 Empirical solar radiation [watts]
            
            rs_tr = rso_d * (1 - 0.9 * np.exp(-1 * b * data_df[tdelta_col].values ** 1.5))
            mc_tr_matrix[mc_i,:] = rs_tr
            for month_i, month in enumerate(range(1, 13)):
                month_mask = data_df[cfg.input_met['fields']['month']].values == month
                mc_tr_monthly[mc_i, month_i] = np.nanmean(
                    mc_tr_matrix[mc_i][month_mask])
            mc_corr_vector[mc_i] = np.corrcoef(
                rs_monthly[rs_month_col].values, mc_tr_monthly[mc_i, :])[0, 1]
            mc_rmse_vector[mc_i] = rmse(rs_meas, mc_tr_matrix[mc_i, :])
            mc_pct_bias_vector[mc_i] = pct_bias(mc_tr_matrix[mc_i, :], rs_meas)
            if mc_rmse_vector[mc_i] < rmse_min:
                rmse_min = float(mc_rmse_vector[mc_i])
                logging.debug(
                    '  {0:>{width}d}  {1:.6f}  {2:.6f} {3:.6f} {4:.6f}'.format(
                        mc_i, rmse_min, b0[mc_i], b1[mc_i], b2[mc_i],
                        width=mc_width))
        logging.debug('  {0} seconds\n'.format(clock() - mc_clock))

        # FIND OPTIMIZED VALUES
        
        mc_max_corr_index = np.nanargmax(mc_corr_vector)
        mc_min_rmse_index = np.nanargmin(mc_rmse_vector)
        mc_corr_ratio_vector = mc_tr_matrix[mc_max_corr_index, :]
        mc_rmse_ratio_vector = mc_tr_matrix[mc_min_rmse_index, :]
        avg_diff_standard = np.nanmean(rs_standard_tr / rs_meas)
        avg_diff_corr_opt = np.nanmean(mc_corr_ratio_vector / rs_meas)
        avg_diff_rmse_opt = np.nanmean(mc_rmse_ratio_vector / rs_meas)

        # Check if indexes share common values

        if mc_max_corr_index == mc_min_rmse_index:
            logging.info(
                ('Values b0 = {0:.6f}, b1 = {1:.6f}, b2 = {2:.6f} ' +
                 'found at index {3}').format(
                    b0[mc_max_corr_index], b1[mc_max_corr_index],
                    b2[mc_max_corr_index], mc_max_corr_index))
            logging.info(
                ('  provide a minimized rmse of {0:.6f} and a ' +
                'maximized correlation of {1}').format(
                    mc_rmse_vector[mc_max_corr_index],
                    mc_corr_vector[mc_max_corr_index]))
            logging.info(
                ('Standard parameter rmse is {0:.6f} and has a ' +
                 'correlation of {1:.6f}').format(
                tr_standard_rmse, tr_standard_corr))
            logging.info(
                'Average of (standard/observed) on a daily basis is {0:.6f}'.format(
                avg_diff_standard))
            logging.info(
                'Average of (optimized/observed) on a daily basis is {0:.6f}'.format(
                avg_diff_rmse_opt))
        else:
            logging.info(
                ('Values b0 = {0:.6f}, b1 = {1:.6f}, b2 = {2:.6f} '+
                 'found at index {3}').format(
                b0[mc_min_rmse_index], b1[mc_min_rmse_index],
                b2[mc_min_rmse_index], mc_min_rmse_index))
            logging.info(
                '  provide a minimized rmse of {0:.6f}'.format(
                    mc_rmse_vector[mc_min_rmse_index]))
            logging.info(
                ('Values b0 = {0:.6f}, b1 = {1:.6f}, b2 = {2:.6f} '+
                 'found at index {3}').format(
                    b0[mc_max_corr_index], b1[mc_max_corr_index],
                    b2[mc_max_corr_index], mc_max_corr_index))
            logging.info('  provide a maximized correlation of {0}'.format(
                mc_corr_vector[mc_max_corr_index]))
            logging.info(
                ('Standard parameter rmse is {0:.6f} and has a ' +
                 'correlation of {1:.6f}').format(
                    tr_standard_rmse, tr_standard_corr))
            logging.info(
                ('Average of (standard/observed) on a daily basis ' +
                 'is {0:.6f}').format(avg_diff_standard))
            logging.info(
                ('Average of (optimized/observed) for maximized R^2 ' +
                 'on a daily basis is {0:.6f}').format(avg_diff_corr_opt))
            logging.info(
                ('Average of (optimized/observed) for minimized rmse ' +
                 'on a daily basis is {0:.6f}').format(avg_diff_rmse_opt))

        # DISPLAY OUTPUT IN PLOTS
        
        f, axarr = plt.subplots(2, 2, figsize=(10,10))
        months = range(1,13)

        # Mean Monthly Standard vs Measured
        
        axarr[0, 0].plot(
            months, rs_monthly[rs_month_col].values, 'b', label = 'Measured')
        axarr[0, 0].plot(
            months, rs_tr_standard_monthly, 'r', label = 'TR Standard')
        axarr[0, 0].set_ylabel('Rs (w/m2)')
        axarr[0, 0].set_xlabel('Month')
        axarr[0, 0].set_title('Mean Monthly Standard vs Measured')
        axarr[0, 0].legend(loc=3)
        axarr[0, 0].set_xlim([1, 12])

        # Daily Standard vs Measured
        
        axarr[0, 1].scatter(rs_meas, rs_standard_tr, s = 2, c = 'b', alpha = 0.3)
        axarr[0, 1].set_ylabel('Estimated (MJ/m2/d)')
        axarr[0, 1].set_xlabel('Observed (MJ/m2/d)')
        axarr[0, 1].set_title('Daily Standard vs Measured')
        lsrl_standard_eqn = np.polyfit(
            rs_meas[rs_mask], rs_standard_tr[rs_mask], deg = 1)
        axarr[0, 1].plot(
            rs_meas[rs_mask],
            lsrl_standard_eqn[0] * rs_meas[rs_mask] + lsrl_standard_eqn[1],
            color='red')
        axarr[0, 1].plot([0, rs_max], [0, rs_max], 'k--')

        # Mean Monthly Standard vs Optimized
        
        axarr[1, 0].plot(
            months, rs_monthly[rs_month_col].values, 'b', label='Measured')
        axarr[1, 0].plot(
            months, mc_tr_monthly[mc_min_rmse_index, :], 'r',
            label='TR Optimized')
        axarr[1, 0].set_ylabel('Rs (w/m2)')
        axarr[1, 0].set_xlabel('Month')
        axarr[1, 0].set_title('Mean Monthly Optimized vs Measured')
        axarr[1, 0].legend(loc=3)
        axarr[1, 0].set_xlim([1, 12])

        # Daily Optimized vs Measured
        
        axarr[1, 1].scatter(
            rs_meas, mc_tr_matrix[mc_min_rmse_index, :],
            s = 2, c = 'b', alpha = 0.3)
        axarr[1, 1].set_ylabel('Estimated (MJ/m2/d)')
        axarr[1, 1].set_xlabel('Observed (MJ/m2/d)')
        axarr[1, 1].set_title('Daily Optimized vs Measured')
        lsrl_optimized_eqn = np.polyfit(
            rs_meas[rs_mask], mc_tr_matrix[mc_min_rmse_index, :][rs_mask],
            deg=1)
        axarr[1, 1].plot(
            rs_meas[rs_mask],
            lsrl_optimized_eqn[0] * rs_meas[rs_mask] + lsrl_optimized_eqn[1],
            color='red')
        axarr[1, 1].plot([0, rs_max], [0, rs_max], 'k--')

        # Print line equation
        
        logging.info('For standard LSRL: y = {0:.4f} x + {1:0.4f}'.format(
            lsrl_standard_eqn[0], lsrl_standard_eqn[1]))
        logging.info('For optimized LSRL: y = {0:.4f} x + {1:0.4f}'.format(
            lsrl_optimized_eqn[0], lsrl_optimized_eqn[1]))
        plt.savefig(file_name + '.jpg')
        plt.show()
        plt.close()
        del f, axarr
    raw_input('Press ENTER to close')

def rmse(data, estimate):
    """Function to calculate root mean square error from a data vector or matrix
      and corresponding estimates.

    Usage: r = rmse(data,estimate)
    Note: data and estimates have to be of same size
    Example: r = rmse(randn(100,100), randn(100, 100));

    delete records with NaNs in both datasets first
    """
    mask = np.isfinite(data) & np.isfinite(estimate)
    return np.sqrt(np.sum((data[mask] - estimate[mask]) ** 2) / np.sum(data[mask]))

def log10_bias(a_array, b_array):
    """"""
    b_log10 = np.log10(b_array)
    return 100 * np.nansum(a_array - b_log10) / np.nansum(b_log10)

def pct_bias(a_array, b_array):
    """"""
    return 100 * np.nansum(a_array - b_array) / np.nansum(b_array)

def get_tsfile_path(file_name, sheet_delim):
    workspace = os.getcwd()
    while True:
        if file_name is None: file_name = raw_input('Specify station file name: ')
        if os.sep in file_name:
            file_path = file_name
        else:
	    file_path = os.path.join(workspace, file_name)
        if sheet_delim is None:
            if '.xls' in file_path.lower():
                sheet_delim = "Sheet1"
            else:
                if 'csv' in sheet_delim:
                    sheet_delim = ","
                else:
                    sheet_delim = "\t"
        if not os.path.isfile(file_path):
            print 'File', file_name, 'doesn\'t exist in user workspace'
            
            # prompt for file name/path
            
            if '.xls' in file_path.lower():
                # Display available Excel files
            
                print 'Following Excel files exist in', workspace
                for item in os.listdir(workspace):
                    if item.lower().endswith('.xlsx') or item.lower().endswith('.xls'):
                        print item
            else:
                # Display suspected text files
            
                print 'Following text files exist in', workspace
                for item in os.listdir(workspace):
                    if item.lower().endswith('.txt') or item.lower().endswith('.csv') or item.lower().endswith('.dat'):
                        print item
            file_name = None
        else:
            break
    return file_path, sheet_delim

def parse_args():
    parser = argparse.ArgumentParser(
        description = 'Thornton-Running Monte Carlo Optimization')
    parser.add_argument(
        '-f', '--file', metavar = 'PATH', help = 'INI or Weather Data File Name')
    parser.add_argument(
        '-sd', '--sheet_delim', metavar = 'SHEET_DELIM', help = 'Weather Data Worksheet or Delimiter')
    parser.add_argument(
        '--elev', type = float, metavar = 'ELEVATION', default = None, 
        help = 'Station elevation [m]')
    parser.add_argument(
        '--lat', type = float, metavar = 'LATITUDE', default = None, 
        help = 'Station latitude [decimal degrees (N)]')
    parser.add_argument(
        '--lon', type = float, metavar = 'LONGITUDE', default = None, 
        help = 'Station longitude [decimal degrees (W)]')
    parser.add_argument(
        '-mv', '--mdv', type = float, metavar = 'MISSING_DATA_VALUE', default = 'NaN', 
        help = 'Missing data value [NaN]')
    parser.add_argument(
        '-mc', '--iter', type = int, metavar = 'N', default = 20000, 
        help = 'Number Monte Carlo iterations')
    parser.add_argument(
        '-c', '--compare', default = False, action = "store_true",
        help = 'Comparison Flag')
    parser.add_argument(
        '-s', '--save', default = False, action = "store_true", 
        help = 'Save Temp Excel Flag')
    parser.add_argument(
        '-d', '--debug', default = False, action = "store_true",
        help = 'Debug level logging')
    args = parser.parse_args()

    # Convert relative paths to absolute paths
    
    if args.file and os.path.isfile(os.path.abspath(args.file)):
        args.file = os.path.abspath(args.file)
    return args

if __name__ == '__main__':
    args = parse_args()
    if args.debug: print "args\n", args
    main(ts_ini_name = args.file, sheet_delim = args.sheet_delim, 
         missing_data_value = args.mdv, elevation = args.elev, 
         latitude = args.lat, longitude = args.lon, 
         comparison_flag = args.compare, save_temp_flag = args.save, 
         mc_iterations = args.iter, debug_flag = args.debug)
