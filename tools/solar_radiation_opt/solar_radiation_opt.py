#--------------------------------
# Name:         solar_radiation_opt.py
# Purpose:      Thornton-Running Monte Carlo Optimization
# Author:       Charles Morton
# Created       2015-07-01
# Python:       2.7
#--------------------------------

import argparse
import logging
import math
import os
from time import clock

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import emprso_w_tr

def main(file_name=None, station_elev=None,
         station_lat=None, station_lon=None,
         comparison_flag=False, mc_iterations=None, debug_flag=True):
    """

    Args:
        file_name: string of the file_name to process
        station_elev: float of the station elevation [m]
        station_lat: float of the station longitude [decimal degrees]
        station_lon: float of the station longitude [decimal degrees]
        comparison_flag: boolean
        mc_iterations: integer
        debug_flag: boolean, 
    Returns:
        None
    """
    
    ## Column names
    year_col = 'Year'
    month_col = 'Month'
    day_col = 'Day'
    doy_col = 'DOY'
    tdelta_col = 'Tdelta'
    tmonth_col = 'Tmonth'
    rs_month_col = 'Rs_month'

    tmax_col = 'TmaxC'
    tmin_col = 'TminC'
    tdew_col = 'TdewC'
    rs_col = 'Rs_MJ_m2'
    ##rs_col = 'Rs_w_m2'
    
    ##tmax_col = 0
    ##tmin_col = 1
    ##tdew_col = 2
    ##rs_col = 3 

    ###########################################################################
    #USER VARIABLES
    missing_data_value = -999
    rs_watts_flag = False
    
    ###########################################################################
    if debug_flag:
        ## File Logger
        logging.basicConfig(
            level = logging.DEBUG, format='%(message)s', filemode='w', 
            filename = os.path.join(workspace, file_name+'_input_log'+'.txt'))
        ## Display Logger
        log_console = logging.StreamHandler()
        log_console.setLevel(logging.DEBUG)
        log_console.setFormatter(logging.Formatter('%(message)s'))
        logging.getLogger('').addHandler(log_console)
    else:
        logging.basicConfig(level=logging.INFO, format='%(message)s')
    logging.info('\nOptimizing Thornton-Running Coefficients\n')

    workspace = os.getcwd()
    while True:
        file_name = raw_input('Specify the station file name: ')
        file_path = os.path.join(workspace, file_name)
        if not os.path.isfile(file_path):
            logging.info(
                ('  The file {0} doesn\'t exist in the current '+
                 'working directory').format(file_name))
            ## Display the available XLS files
            logging.info('  The following XLS files are {0}'.format(workspace))
            for item in os.listdir(workspace):
                if item.lower().endswith('.xls'):
                    logging.info('    {0}'.format(item))
            logging.info('')
        else:
            break
    ## Check input file
    ##file_name = 'FTCB_tr_opt_input.xls'
    ##file_path = os.path.join(workspace, file_name)
    ##if not os.path.isfile(file_path):
    ##    logging.error('\nERROR: Station file doesn\'t exist')
    ##    raise SystemExit()
    
    ## Use filename (without extensions)
    file_name = 'processed_' + os.path.splitext(file_name)[0]
    
    if comparison_flag:
        file_name = 'Comparison_' + file_name
    else:
        file_name = 'Optimization_' + file_name

    ## DEADBEEF - hardcode inputs for now
    if station_elev is None:
        station_elev = float(raw_input(
            'Specify the station elevation [meters]: '))
    if station_lat is None:
        station_lat = float(raw_input(
            'Specify the station latitude [decimal degrees (N)]: '))
    if station_lon is None:
        station_lon = float(raw_input(
            'Specify the station longitude [decimal degrees (W)]: '))
    ##station_elev = 422
    ##station_lat = 35.14887
    ##station_lon = 98.46607
    if mc_iterations is None:
        mc_iterations = float(raw_input(
            'Specify the number of Monte Carlo iterations: '))
    ##mc_iterations = int(raw_input('Specify how many iterations to run (Expect ~10 run time per 1000):

    ## Read the Excel file
    data_pd = pd.read_excel(
        file_path, sheetname='Sheet1', na_values=['-999'], 
        index_col=0, has_index_names=True,
        parse_dates={'Date': [2,0,1]},
        date_parser=lambda x: pd.datetime.strptime(x, '%Y %m %d'))
    ##print data_pd.ix['1997-11-20']
    num_lines = len(data_pd.index)

    ## Assign month and DOY columns to the data frame
    data_pd[year_col] = data_pd.index.year
    data_pd[month_col] = data_pd.index.month
    data_pd[day_col] = data_pd.index.day
    data_pd[doy_col] = data_pd.index.dayofyear

    ## Assigning dates
    ##month = data_pd[:,0]
    ##day = data_pd[:,1]
    ##year = data_pd[:,2]
    
    ## Read data by column name or column number
    ##data_pd[rs_col] = data_pd.ix[:,3]    # w/m2
    ##tmax = data_pd.ix[:,0]          # C
    ##tmin = data_pd.ix[:,1]          # C
    ##tdew = data_pd.ix[:,2]          # C
    #wind = data[:,12]        # m/s
    #rhmax = data[:,6]        #
    #rhmin = data[:,7]        #
    #precip = data[:,13]      # mm
    #uz = Wind                # change variable name for downhill code
    
    ## Compute pressure kPa
    p = (2.406 - 0.0000534 * station_elev) ** 5.26; 
    
    ## FAO converting watts into mj m2 d
    if rs_watts_flag:
        data_pd[rs_col] *= 0.0864

    ## Mean monthly difference between Tmax and Tmin for T-R
    data_pd[tdelta_col] = data_pd[tmax_col] - data_pd[tmin_col]
    tdelta_monthly = data_pd[[month_col,tdelta_col]].groupby(month_col).mean()
    tdelta_monthly.rename(columns={tdelta_col:tmonth_col}, inplace=True)
    tdelta_monthly.reset_index(level=0, inplace=True)
    ##tdelta_monthly[month_col] = df.index

    ## Join mean monthly tdelta back to main table
    ## Date index is dropped by merge, so save it before merging
    data_pd = data_pd.reset_index()
    data_pd = pd.merge(data_pd, tdelta_monthly, on=month_col)
    data_pd = data_pd.set_index('Date')


    ## Apply Limits on Variables, rhmax, rhmin, tmax, tmin, rs, wind, rh
    data_pd[data_pd[tmax_col] < -40] = np.nan
    data_pd[data_pd[tmax_col] > 60] = np.nan
    data_pd[data_pd[tmin_col] < -40] = np.nan
    data_pd[data_pd[tmin_col] > 60] = np.nan
    ##rhmax[rhmax < -40] = np.nan
    ##rhmax[rhmax >= 60] = np.nan
    ##rhmin[rhmin < -40] = np.nan
    ##rhmin[rhmin >= 60] = np.nan
    
    ## Calculate all secondary variables as separate arrays
    eo_tmax = 0.6108 * np.exp((17.27 * data_pd[tmax_col]) / (data_pd[tmax_col] + 237.3))
    eo_tmin = 0.6108 * np.exp((17.27 * data_pd[tmin_col]) / (data_pd[tmin_col] + 237.3))
    ea = 0.6108 * np.exp((17.27 * data_pd[tdew_col]) / (data_pd[tdew_col] + 237.3))
    #ea = ((eo_tmin * (rhmax / 100)) + (eo_tmax * (rhmin / 100))) / 2
    tdew = (116.91 + 237.3 * np.log(ea)) / (16.78 - np.log(ea))
    tmin_tdew = data_pd[tmin_col] - data_pd[tdew_col]

    ## MJ m-2 d-1
    if comparison_flag:
        rso_d, rs_custom_tr = emprso_w_tr.emprso_w_tr(
            station_lat, p, ea, data_pd[doy_col].values,
            data_pd[tmonth_col].values, data_pd[tdelta_col].values,
            b0=0.015690, b1=0.207780, b2=-0.174350)
            ##b0=0.029805, b1=0.178585, b2=-0.24383)
    rso_d, rs_standard_tr = emprso_w_tr.emprso_w_tr(
        station_lat, p, ea, data_pd[doy_col].values,
        data_pd[tmonth_col].values, data_pd[tdelta_col].values,
        b0=0.031, b1=0.201, b2=-0.185)

    ## Pull out numpy array of measured solar from data frame
    rs_meas = data_pd[rs_col].values
    rs_mask = np.isfinite(rs_meas) & np.isfinite(rs_standard_tr)
    rs_max = max(rs_meas[rs_mask])
        
    ## Calculate monthly means for rs and standard param rs_tr
    rs_monthly = data_pd[[month_col,rs_col]].groupby(month_col).mean()
    rs_monthly.rename(columns={rs_col:rs_month_col}, inplace=True)
    rs_monthly.reset_index(level=0, inplace=True)

    ## Join mean monthly Rs back to main table
    data_pd = data_pd.reset_index()
    data_pd = pd.merge(data_pd, rs_monthly, on=month_col)
    data_pd = data_pd.set_index('Date')

    ##
    rs_tr_standard_monthly = np.zeros(12)
    rs_tr_custom_monthly = np.zeros(12)
    for month_i, month in enumerate(range(1,13)):
        month_mask = (data_pd[month_col].values == month)
        ##rs_monthly[i] = np.nanmean[data_pd[rs_col][month_mask]]
        rs_tr_standard_monthly[month_i] = np.nanmean(rs_standard_tr[month_mask])
        if comparison_flag:
            rs_tr_custom_monthly[month_i] = np.nanmean(rs_custom_tr[month_mask])

     ## Save the updated data to a new excel file
    save_temp_flag = False
    if save_temp_flag:
        temp_pd = data_pd.copy().sort_index()
        temp_pd = temp_pd.reset_index()
        writer = pd.ExcelWriter(file_path.replace('.xls', '_temp.xls'),
                                datetime_format='yyyy-mm-dd')
        temp_pd.to_excel(writer, 'Sheet1', index=False)
        writer.save()
        del temp_pd, writer

    ## Compute statistics
    ## Correlation of monthly values?
    tr_standard_corr = np.corrcoef(
        rs_monthly[rs_month_col].values, rs_tr_standard_monthly)[0,1]
    ##tr_standard_corr = np.correlate(
    ##    np.array(rs_monthly[rs_month_col]), rs_tr_standard_monthly)
    ## RMSE and percent bias of all values
    tr_standard_rmse = rmse(rs_standard_tr, data_pd[rs_col].values)
    tr_standard_perct_bias = pct_bias(rs_standard_tr, data_pd[rs_col].values)
    ##tr_standard_log10_bias = log10_bias(rs_standard_tr, data_pd[rs_col].values)
    logging.info(
        ('\nThe standard parameter RMSE is {0:.6f} and has a correlation '+
         'of {1:.6f}').format(tr_standard_rmse, tr_standard_corr))
    
    if comparison_flag:
        ## Correlation of monthly values?
        tr_custom_corr = np.corrcoef(
            rs_monthly[rs_month_col].values, rs_tr_custom_monthly)[0,1]
        ##tr_custom_corr = np.correlate(
        ##    np.array(rs_monthly[rs_month_col]), rs_tr_custom_monthly)
        ## RMSE and percent bias of all values
        tr_custom_rmse = rmse(rs_custom_tr, data_pd[rs_col].values)
        tr_custom_perct_bias = pct_bias(rs_custom_tr, data_pd[rs_col].values)
        ##tr_custom_log10_bias = log10_bias(rs_custom_tr, data_pd[rs_col].values)
        logging.info(
            ('The custom parameter RMSE is {0:.6f} and has a correlation '+
             'of {1:.6f}').format(tr_custom_rmse, tr_custom_corr))       
    
    ###########################################################################
    if comparison_flag:
        ## DISPLAY OUTPUT IN PLOTS      
        f, axarr = plt.subplots(2, 2, figsize=(10,10))
        months = range(1,13)
        
        ## Mean Monthly Standard vs Measured
        axarr[0,0].plot(months, rs_monthly[rs_month_col].values, 'b',
                        label='Measured')
        axarr[0,0].plot(months, rs_tr_standard_monthly, 'r', label='TR Standard')
        axarr[0,0].set_ylabel('Rs (w/m2)')
        axarr[0,0].set_xlabel('Month')
        axarr[0,0].set_title('Mean Monthly Standard vs Measured')
        axarr[0,0].legend(loc=3)
        axarr[0,0].set_xlim([1,12])
        
        ## Daily Standard vs Measured
        axarr[0,1].scatter(rs_meas, rs_standard_tr, s=2, c='b', alpha=0.3)
        axarr[0,1].set_ylabel('Estimated (w/m2)')
        axarr[0,1].set_xlabel('Observed (w/m2)')
        axarr[0,1].set_title('Daily Standard vs Measured')
        lsrl_standard_eqn = np.polyfit(
            rs_meas[rs_mask], rs_standard_tr[rs_mask], deg=1)
        axarr[0,1].plot(
            rs_meas[rs_mask],
            lsrl_standard_eqn[0] * rs_meas[rs_mask] + lsrl_standard_eqn[1],
            color='red')
        axarr[0,1].plot([0,rs_max], [0,rs_max], 'k--')
        
        ## Mean Monthly Standard vs Custom
        axarr[1,0].plot(months, rs_monthly[rs_month_col].values, 'b',
                        label='Measured')
        axarr[1,0].plot(months, rs_tr_custom_monthly, 'r', label='TR Custom')
        axarr[1,0].set_ylabel('Rs (w/m2)')
        axarr[1,0].set_xlabel('Month')
        axarr[1,0].set_title('Mean Monthly Optimized vs Measured')
        axarr[1,0].legend(loc=3)
        axarr[1,0].set_xlim([1,12])
        
        ## Daily Custom vs Measured
        axarr[1,1].scatter(rs_meas, rs_custom_tr, s=2, c='b', alpha=0.3)
        axarr[1,1].set_ylabel('Estimated (w/m2)')
        axarr[1,1].set_xlabel('Observed (w/m2)')
        axarr[1,1].set_title('Daily Optimized vs Measured')
        lsrl_custom_eqn = np.polyfit(
            rs_meas[rs_mask], rs_custom_tr[rs_mask], deg=1)
        axarr[1,1].plot(
            rs_meas[rs_mask],
            lsrl_custom_eqn[0] * rs_meas[rs_mask] + lsrl_custom_eqn[1],
            color='red')
        axarr[1,1].plot([0,rs_max], [0,rs_max], 'k--')
        
        avg_diff_standard = np.nanmean(rs_standard_tr / rs_meas)
        avg_diff_opt = np.nanmean(rs_custom_tr / rs_meas)   
        logging.info(
            'The average of (standard/observed) on a daily basis is {0:.6f}'.format(
                avg_diff_standard))
        logging.info(
            'The average of (optimized/observed) on a daily basis is {0:.6f}'.format(
                avg_diff_opt))
        
        #Print out line equation
        logging.info(
            'For the standard LSRL: y = {0:>.4f}x + {1:0.4f}'.format(
                lsrl_standard_eqn[0], lsrl_standard_eqn[1]))
        logging.info(
            'For the custom LSRL: y = {0:>.4f}x + {1:0.4f}'.format(
                lsrl_custom_eqn[0], lsrl_custom_eqn[1]))
        logging.info('\n')
        
        plt.savefig(os.path.join(workspace, file_name+'.jpg'))
        plt.show()
        plt.close()
        del f, axarr
    
    ###########################################################################
    else:
        ## #Open Pool NOT USING PARFOR
        ##     poolSize = matlabpool('size')
        ##     if poolSize == 0
        ##         matlabpool open 4
        ##     else
        ##         matlabpool close force local
        ##         matlabpool open 4
        ##     end
        ##     fprintf('This program is running on #d MATLABPOOL workers.\n', matlabpool('size'));
        
        #Monte Carlo Analysis
        ##np.random.randint(0, mc_iterations, size=1)
        b0 =  0.031 + (0.031 * 0.2) * np.random.randn(mc_iterations)
        b1 = 0.201 + (0.201 * 0.2) * np.random.randn(mc_iterations)
        b2 = -0.185 + (-0.185 * 0.2) * np.random.randn(mc_iterations)
        ##b0 =  0.031 + (0.031 * 0.2) * randn(mc_iterations,1)
        ##b1 = 0.201 + (0.201 * 0.2) * randn(mc_iterations,1)
        ##b2 = -0.185 + (-0.185 * 0.2) * randn(mc_iterations,1)
        
        mc_tr_matrix = np.zeros((mc_iterations, num_lines))
        mc_tr_monthly = np.zeros((mc_iterations, 12))
        mc_corr_vector = np.zeros(mc_iterations)
        mc_rmse_vector = np.zeros(mc_iterations)
        mc_pct_bias_vector = np.zeros(mc_iterations)
        ##mc_log10_bias_vector = np.zeros(mc_iterations)

        logging.info('\nMonte Carlo Iterations: {0}'.format(mc_iterations))
        mc_clock = clock()
        rmse_min = 1000
        mc_width = len(str(mc_iterations))
        logging.debug(
            ('  {0:>{width}s}  {1:>8s}  {2:>8s} {3:>8s} {4:>8s}').format(
            'MC', 'RMSE', 'B0', 'B1', 'B2', width=mc_width))
        for mc_i in range(mc_iterations):
            if mc_i % 1000 == 0:
                 logging.info('  {0:>{width}d}'.format(mc_i, width=mc_width))
            ##logging.debug("{0} {1} {2}".format(b0[mc_i], b1[mc_i], b2[mc_i]))
            ## Eqn 15 Empirical fitting coefficient
            b = b0[mc_i] + b1[mc_i] * np.exp(b2[mc_i] * data_pd[tdelta_col].values)
            ## Eqn 14 Empirical solar radiation [watts]
            rs_tr = rso_d * (1 - 0.9 * np.exp(-1 * b * data_pd[tdelta_col].values ** 1.5))
            mc_tr_matrix[mc_i,:] = rs_tr
            for month_i, month in enumerate(range(1,13)):
                month_mask = data_pd[month_col].values == month
                mc_tr_monthly[mc_i, month_i] = np.nanmean(
                    mc_tr_matrix[mc_i][month_mask])
            mc_corr_vector[mc_i] = np.corrcoef(
                rs_monthly[rs_month_col].values, mc_tr_monthly[mc_i,:])[0,1]
            mc_rmse_vector[mc_i] = rmse(rs_meas, mc_tr_matrix[mc_i,:])
            mc_pct_bias_vector[mc_i] = pct_bias(mc_tr_matrix[mc_i,:], rs_meas)
            ##mc_log10_bias_vector[mc_i] = log10_bias(mc_tr_matrix[mc_i,:], rs_meas)

            if mc_rmse_vector[mc_i] < rmse_min:
                rmse_min = float(mc_rmse_vector[mc_i])
                logging.debug(
                    ('  {0:>{width}d}  {1:.6f}  {2:.6f} {3:.6f} {4:.6f}').format(
                    mc_i, rmse_min, b0[mc_i], b1[mc_i], b2[mc_i], width=mc_width))
            
        logging.debug('  {0} seconds\n'.format(clock() - mc_clock))
        
        ###########################################################################
        ## FIND OPTIMIZED VALUES
        mc_max_corr_index = np.nanargmax(mc_corr_vector)
        mc_min_rmse_index = np.nanargmin(mc_rmse_vector)
        ##mc_min_bias_index = np.nanargmin(mc_pct_bias_vector)
        
        mc_corr_ratio_vector = mc_tr_matrix[mc_max_corr_index,:]
        mc_rmse_ratio_vector = mc_tr_matrix[mc_min_rmse_index,:]
        
        avg_diff_standard = np.nanmean(rs_standard_tr / rs_meas)
        avg_diff_corr_opt = np.nanmean(mc_corr_ratio_vector / rs_meas)
        avg_diff_rmse_opt = np.nanmean(mc_rmse_ratio_vector / rs_meas)
        
        ## Check to see if indexes share common values
        if mc_max_corr_index == mc_min_rmse_index:
            logging.info(
                'The values b0 = {0:.6f}, b1 = {1:.6f}, b2 = {2:.6f} found at index {3}'.format(
                    b0[mc_max_corr_index], b1[mc_max_corr_index],
                    b2[mc_max_corr_index], mc_max_corr_index))
            logging.info(
                ('  provide a minimized rmse of {0:.6f} and a '+
                'maximized correlation of {1}').format(
                    mc_rmse_vector[mc_max_corr_index],
                    mc_corr_vector[mc_max_corr_index]))
            logging.info(
                ('The standard parameter rmse is {0:.6f} and has a '+
                 'correlation of {1:.6f}').format(
                tr_standard_rmse, tr_standard_corr))
            logging.info(
                'The average of (standard/observed) on a daily basis is {0:.6f}'.format(
                avg_diff_standard))
            logging.info(
                'The average of (optimized/observed) on a daily basis is {0:.6f}'.format(
                avg_diff_rmse_opt))
        else:
            logging.info(
                'The values b0 = {0:.6f}, b1 = {1:.6f}, b2 = {2:.6f} found at index {3}'.format(
                b0[mc_min_rmse_index], b1[mc_min_rmse_index],
                b2[mc_min_rmse_index], mc_min_rmse_index))
            logging.info(
                '  provide a minimized rmse of {0:.6f}'.format(
                    mc_rmse_vector[mc_min_rmse_index]))
            logging.info(
                'The values b0 = {0:.6f}, b1 = {1:.6f}, b2 = {2:.6f} found at index {3}'.format(
                    b0[mc_max_corr_index], b1[mc_max_corr_index],
                    b2[mc_max_corr_index], mc_max_corr_index))
            logging.info('  provide a maximized correlation of {0}'.format(
                mc_corr_vector[mc_max_corr_index]))
            logging.info(
                ('The standard parameter rmse is {0:.6f} and has a '+
                 'correlation of {1:.6f}').format(
                    tr_standard_rmse, tr_standard_corr))
            logging.info(
                'The average of (standard/observed) on a daily basis is {0:.6f}'.format(
                    avg_diff_standard))
            logging.info(
                ('The average of (optimized/observed) for maximized R^2 '+
                 'on a daily basis is {0:.6f}').format(avg_diff_corr_opt))
            logging.info(
                ('The average of (optimized/observed) for minimized rmse '+
                 'on a daily basis is {0:.6f}').format(avg_diff_rmse_opt))
        
        ###########################################################################
        ## DISPLAY OUTPUT IN PLOTS
        f, axarr = plt.subplots(2, 2, figsize=(10,10))
        months = range(1,13)

        ## Mean Monthly Standard vs Measured
        axarr[0,0].plot(months, rs_monthly[rs_month_col].values, 'b',
                        label='Measured')
        axarr[0,0].plot(months, rs_tr_standard_monthly, 'r', label='TR Standard')
        axarr[0,0].set_ylabel('Rs (w/m2)')
        axarr[0,0].set_xlabel('Month')
        axarr[0,0].set_title('Mean Monthly Standard vs Measured')
        axarr[0,0].legend(loc=3)
        axarr[0,0].set_xlim([1,12])
        
        ## Daily Standard vs Measured
        axarr[0,1].scatter(rs_meas, rs_standard_tr, s=2, c='b', alpha=0.3)
        axarr[0,1].set_ylabel('Estimated (w/m2)')
        axarr[0,1].set_xlabel('Observed (w/m2)')
        axarr[0,1].set_title('Daily Standard vs Measured')
        lsrl_standard_eqn = np.polyfit(
            rs_meas[rs_mask], rs_standard_tr[rs_mask], deg=1)
        axarr[0,1].plot(
            rs_meas[rs_mask],
            lsrl_standard_eqn[0] * rs_meas[rs_mask] + lsrl_standard_eqn[1],
            color='red')
        axarr[0,1].plot([0,rs_max], [0,rs_max], 'k--')
        
        ## Mean Monthly Standard vs Optimized
        axarr[1,0].plot(months, rs_monthly[rs_month_col].values, 'b',
                        label='Measured')
        axarr[1,0].plot(months, mc_tr_monthly[mc_min_rmse_index,:], 'r',
                        label='TR Optimized')
        axarr[1,0].set_ylabel('Rs (w/m2)')
        axarr[1,0].set_xlabel('Month')
        axarr[1,0].set_title('Mean Monthly Optimized vs Measured')
        axarr[1,0].legend(loc=3)
        axarr[1,0].set_xlim([1,12])
        
        ## Daily Optimized vs Measured
        axarr[1,1].scatter(rs_meas, mc_tr_matrix[mc_min_rmse_index,:],
                           s=2, c='b', alpha=0.3)
        axarr[1,1].set_ylabel('Estimated (w/m2)')
        axarr[1,1].set_xlabel('Observed (w/m2)')
        axarr[1,1].set_title('Daily Optimized vs Measured')
        lsrl_optimized_eqn = np.polyfit(
            rs_meas[rs_mask], mc_tr_matrix[mc_min_rmse_index,:][rs_mask], deg=1)
        axarr[1,1].plot(
            rs_meas[rs_mask],
            lsrl_optimized_eqn[0] * rs_meas[rs_mask] + lsrl_optimized_eqn[1],
            color='red')
        axarr[1,1].plot([0,rs_max], [0,rs_max], 'k--')
        
        ## Print out line equation
        logging.info('For the standard LSRL: y = {0:.4f} x + {1:0.4f}'.format(
            lsrl_standard_eqn[0], lsrl_standard_eqn[1]))
        logging.info('For the optimized LSRL: y = {0:.4f} x + {1:0.4f}'.format(
            lsrl_optimized_eqn[0], lsrl_optimized_eqn[1]))
        
        plt.savefig(os.path.join(workspace, file_name+'.jpg'))
        plt.show()
        plt.close()
        del f, axarr
    raw_input('Press ENTER to close')

def rmse(data, estimate):
    """Function to calculate root mean square error from a data vector or matrix 
      and the corresponding estimates.
      
    Usage: r = rmse(data,estimate)
    Note: data and estimates have to be of same size
    Example: r = rmse(randn(100,100), randn(100,100));
    
    delete records with NaNs in both datasets first
    """
    
    mask = np.isfinite(data) & np.isfinite(estimate)  
    return np.sqrt(np.sum((data[mask] - estimate[mask]) ** 2) / np.sum(data[mask]))

def log10_bias(a_array, b_array):
    """"""
    b_log10 = np.log10(b_array)
    return 100 * np.nansum(a_array - b_log10) / np.nansum(b_log10);
def pct_bias(a_array, b_array):
    """"""
    return 100 * np.nansum(a_array - b_array) / np.nansum(b_array);

################################################################################
if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Thornton-Running Monte Carlo Optimization')
    parser.add_argument(
        '--file', metavar='PATH', help='Weather Data')
    parser.add_argument(
        '--elev', type=float, metavar='ELEV',
        help='Station elevation [m]')
    parser.add_argument(
        '--lat', type=float, metavar='LAT',
        help='Station longitude [decimal degrees (N)]')
    parser.add_argument(
        '--lon', type=float, metavar='LON',
        help='Station longitude [decimal degrees (W)]')
    parser.add_argument(
        '-mc', '--iter', type=int, metavar='N',
        help='Monte Carlo iterations')
    parser.add_argument(
        '-c', '--compare', default=False, action="store_true", 
        help='Comparison Flag')
    parser.add_argument(
        '-d', '--debug', default=False, action="store_true", 
        help='Debug level logging')
    ##parser.add_argument(
    ##    'workspace', nargs='?', default=os.getcwd(),
    ##    help='Landsat scene folder', metavar='FOLDER')
    ##parser.add_argument(
    ##    '-o', '--overwrite', default=None, action="store_true", 
    ##    help='Force overwrite of existing files')
    ##parser.add_argument(
    ##    '--debug', default=logging.INFO, const=logging.DEBUG,
    ##    help='Debug level logging', action="store_const", dest="loglevel")
    args = parser.parse_args()
                
    main(file_name=args.file, station_elev=args.elev,
         station_lat=args.lat, station_lon=args.lon,
         comparison_flag=args.compare, mc_iterations=args.iter,
         debug_flag=args.debug)
