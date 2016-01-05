#--------------------------------
# Name:         compute_growing_season.py
# Purpose:      Extract growing season data from daily output files
# Author:       Charles Morton
# Created       2015-10-07
# Python:       2.7
#--------------------------------

import argparse
import ConfigParser
import csv
import datetime as dt
import logging
import os
import re
import sys

import numpy as np
import pandas as pd

import util

################################################################################

def main(ini_path, start_date=None, end_date=None, crop_str='',
         overwrite_flag=False):
    """Compuate Growing Season Statistics

    Args:
        ini_path (str): file path of the project INI file
        start_date (str): ISO format date string (YYYY-MM-DD)
        end_date (str): ISO format date string (YYYY-MM-DD)
        crop_str (str): comma separate list or range of crops to compare
        overwrite_flag (bool): If True, overwrite existing files

    Returns:
        None
    """

    ## Field names
    date_field  = 'Date'
    doy_field   = 'DOY'
    year_field   = 'Year'
    ##month_field = 'Month'
    ##day_field   = 'Day'
    season_field = 'Season'

    ## Output file/folder names
    gs_summary_name = 'growing_season_full_summary.csv'
    gs_mean_annual_name = 'growing_season_mean_annual.csv'
    baddata_name = 'growing_season_bad_data.txt'

    ## Number of header lines in data file
    header_lines = 2

    ## Delimiter
    sep = ','
    ##sep = r"\s*"

    ########################################################################

    logging.info('\nComputing growing season statistics')
    logging.info('  INI: {}'.format(ini_path))

    ## Check that the INI file can be read
    crop_et_sec = 'CROP_ET'
    config = util.read_ini(ini_path, crop_et_sec)

    ## Get the project workspace and daily ET folder from the INI file
    def get_config_param(config, param_name, section):
        try:
            param_value = config.get(section, param_name)
        except:
            logging.error(('ERROR: The {} parameter is not set'+
                           ' in the INI file').format(param))
            sys.exit()
        return param_value
    project_ws = get_config_param(config, 'project_folder', crop_et_sec)
    daily_stats_ws = os.path.join(
        project_ws, get_config_param(config, 'daily_output_folder', crop_et_sec))
    gs_stats_ws = os.path.join(
        project_ws, get_config_param(config, 'gs_output_folder', crop_et_sec))

    ## Check workspaces
    if not os.path.isdir(daily_stats_ws):
        logging.error(('\nERROR: The daily ET stats folder {0} '+
                       'could be found\n').format(daily_stats_ws))
        sys.exit()
    if not os.path.isdir(gs_stats_ws):
        os.mkdir(gs_stats_ws)

    ## Range of data to plot
    try:
        year_start = dt.datetime.strptime(start_date, '%Y-%m-%d').year
        logging.info('  Start Year:  {0}'.format(year_start))
    except:
        year_start = None
    try:
        year_end = dt.datetime.strptime(end_date, '%Y-%m-%d').year
        logging.info('  End Year:    {0}'.format(year_end))
    except:
        year_end = None
    if year_start and year_end and year_end <= year_start:
        logging.error('\n  ERROR: End date must be after start date\n')
        sys.exit()

    ## Allow user to subset crops from INI
    try: 
        crop_skip_list = sorted(list(util.parse_int_set(
            config.get(crop_et_sec, 'crop_skip_list'))))
    except: 
        crop_skip_list = []
        ##crop_skip_list = [44, 45, 46, 55, 56, 57]
    try: 
        crop_test_list = sorted(list(util.parse_int_set(
            config.get(crop_et_sec, 'crop_test_list'))))
    except: 
        crop_test_list = []
    ## Overwrite INI crop list with user defined values
    ## Could also append to the INI crop list
    if crop_str:
        try: crop_test_list = list(util.parse_int_set(crop_str))
        ##try: crop_test_list = sorted(list(set(
        ##    crop_test_list + list(util.parse_int_set(crop_str)))
        except: pass
    logging.debug('\n  crop_test_list = {0}'.format(crop_test_list))
    logging.debug('  crop_skip_list = {0}'.format(crop_skip_list))
    
    ## Output file paths
    gs_summary_path = os.path.join(gs_stats_ws, gs_summary_name)
    gs_mean_annual_path = os.path.join(gs_stats_ws, gs_mean_annual_name)
    baddata_path = os.path.join(gs_stats_ws, baddata_name)

    ## Build list of site files
    ##site_file_re = '^RG\d{8}ETca.dat$'
    ##site_file_list = sorted([item for item in os.listdir(workspace)
    ##                         if re.match(site_file_re, item)])
    site_file_list = sorted([
        item for item in os.listdir(daily_stats_ws)
        if re.match('\w+_daily_crop_\d{2}.csv$', item)])

    ## Initialize output data arrays and open bad data log file
    gs_summary_data = []
    gs_mean_annual_data = []
    baddata_file = open(baddata_path, 'w')

    ## Regular expressions
    def list_re_or(input_list):
        return '('+'|'.join(map(str,input_list))+')'
    data_re = re.compile('(?P<CELLID>\w+)_daily_crop_(?P<CROP>\d+).csv$', re.I)

    ## Build list of all data files
    data_file_list = sorted(
        [os.path.join(daily_stats_ws, f_name) 
         for f_name in os.listdir(daily_stats_ws)
         if data_re.match(f_name)])
    if not data_file_list:
        logging.error(
            '  ERROR: No daily ET files were found\n'+
            '  ERROR: Check the folder_name parameters\n')
        sys.exit()

    ## Process each file
    for file_path in data_file_list:
        file_name = os.path.basename(file_path)
        logging.debug('')
        logging.info('  {0}'.format(file_name))

        station, crop_num = os.path.splitext(file_name)[0].split('_daily_crop_')
        crop_num = int(crop_num)
        logging.debug('    Station:         {0}'.format(station))
        logging.debug('    Crop Num:        {0}'.format(crop_num))
        if station == 'temp':
            logging.debug('      Skipping')
            continue

        ## Get crop name
        with open(file_path, 'r') as file_f:
            crop_name = file_f.readline().split('-',1)[1].strip()
            logging.debug('    Crop:            {0}'.format(crop_name))
        
        ## Read data from file into record array (structured array)
        daily_df = pd.read_table(file_path, header=0, comment='#', sep=sep)
        logging.debug('    Fields: {0}'.format(', '.join(daily_df.columns.values)))
        daily_df[date_field] = pd.to_datetime(daily_df[date_field])
        daily_df.set_index(date_field, inplace=True)
        daily_df[year_field] = daily_df.index.year
        ##daily_df[year_field] = daily_df[date_field].map(lambda x: x.year)

        ## Build list of unique years
        year_array = np.sort(np.unique(np.array(daily_df[year_field]).astype(np.int)))
        logging.debug('    All Years: {0}'.format(
            ', '.join(list(util.ranges(year_array.tolist())))))
        ##logging.debug('    All Years: {0}'.format(
        ##    ','.join(map(str, year_array.tolist()))))
        
        ## Don't include the first year in the stats
        crop_year_start = min(daily_df[year_field])
        logging.debug('    Skipping {}, first year'.format(crop_year_start))
        daily_df = daily_df[daily_df[year_field] > crop_year_start]
        
        ## Check if start and end years have >= 365 days
        crop_year_start = min(daily_df[year_field])
        crop_year_end = max(daily_df[year_field])
        if sum(daily_df[year_field] == crop_year_start) < 365:
            logging.debug('    Skipping {}, missing days'.format(crop_year_start))
            daily_df = daily_df[daily_df[year_field] > crop_year_start]
        if sum(daily_df[year_field] == crop_year_end) < 365:
            logging.debug('    Skipping {}, missing days'.format(crop_year_end))
            daily_df = daily_df[daily_df[year_field] < crop_year_end]
        del crop_year_start, crop_year_end             
                
        ## Only keep years between year_start and year_end
        if year_start:
            daily_df = daily_df[daily_df[year_field] >= year_start]
        if year_end:
            daily_df = daily_df[daily_df[year_field] <= year_end]
            
        year_sub_array = np.sort(np.unique(np.array(daily_df[year_field]).astype(np.int)))
        logging.debug('    Plot Years: {0}'.format(
            ', '.join(list(util.ranges(year_sub_array.tolist())))))
        ##logging.debug('    Plot Years: {0}'.format(
        ##    ','.join(map(str, year_sub_array.tolist()))))

        ## Get separate date related fields
        date_array = daily_df.index.date
        year_array = daily_df[year_field].values.astype(np.int)
        doy_array = daily_df[doy_field].values.astype(np.int)

        ## Remove leap days
        ##leap_array = (doy_array == 366)
        ##doy_sub_array = np.delete(doy_array, np.where(leap_array)[0])
        
        ## Build separate arrays for each set of crop specific fields
        season_array = np.array(daily_df[season_field])

        #### Original code from growing_season script
        ## Initialize mean annual growing season length variables
        gs_sum, gs_cnt, gs_mean = 0, 0, 0
        start_sum, start_cnt, start_mean = 0, 0, 0
        end_sum, end_cnt, end_mean = 0, 0, 0

        ## Process each year
        for year_i, year in enumerate(year_sub_array):
            year_crop_str = "Crop: {0:2d} {1:32s}  Year: {2}".format(
                crop_num, crop_name, year)
            logging.debug(year_crop_str)     

            ## Extract data for target year
            year_mask = (year_array==year)
            date_sub_array = date_array[year_mask]
            doy_sub_array = doy_array[year_mask]
            season_sub_mask = season_array[year_mask]

            ## Look for transitions in season value
            ## Start transitions up the day before the actual start
            ## End transitions down on the end date
            try:
                start_i = np.where(np.diff(season_sub_mask) == 1)[0][0] + 1
            except:
                start_i = None
            try:
                end_i = np.where(np.diff(season_sub_mask) == -1)[0][0]
            except:
                end_i = None
                
            ## If start transition is not found, season starts on DOY 1
            if start_i is None and end_i is not None:
                start_i = 0
            ## If end transition is not found, season ends on DOY 365/366
            elif start_i is not None and end_i is None:
                end_i = -1
            ## If neither transition is found, season is always on
            ##elif start_i is None and end_i is None:
            ##    start_i, end_i = 0, -1

            ## Calculate start and stop day of year
            ## Set start/end to 0 if season never gets set to 1
            if not np.any(season_sub_mask):
                skip_str = "  Skipping, season flag was never set to 1"
                logging.debug(skip_str)
                baddata_file.write(
                    '{0}  {1} {2}\n'.format(station, year_crop_str, skip_str))
                start_doy, end_doy = 0, 0
                start_date, end_date = "", ""
            elif np.all(season_sub_mask):
                start_doy, end_doy = doy_sub_array[0], doy_sub_array[-1]
                start_date = date_sub_array[0].isoformat()
                end_date = date_sub_array[-1].isoformat()
            else:
                start_doy, end_doy = doy_sub_array[start_i], doy_sub_array[end_i]
                start_date = date_sub_array[start_i].isoformat()
                end_date = date_sub_array[end_i].isoformat()
            gs_length = sum(season_sub_mask)
            logging.debug("Start: {0} ({1})  End: {2} ({3})".format(
                start_doy, start_date, end_doy, end_date))

            ## Track growing season length and mean annual g.s. length
            if start_doy > 0 and end_doy > 0 and year_i <> 0:
                start_sum += start_doy
                end_sum += end_doy
                gs_sum += gs_length
                start_cnt += 1
                end_cnt += 1
                gs_cnt += 1

            ## Append data to list
            gs_summary_data.append(
                [station, crop_num, crop_name, year,
                 start_doy, end_doy, start_date, end_date, gs_length])
            
            ## Cleanup
            del year_mask, doy_sub_array, season_sub_mask
            del start_doy, end_doy, start_date, end_date, gs_length
            
        ## Calculate mean annual growing season start/end/length
        if gs_cnt > 0:
            mean_start_doy = int(round(float(start_sum) / start_cnt))
            mean_end_doy = int(round(float(end_sum) / end_cnt))
            mean_length = int(round(float(gs_sum) / gs_cnt))
            mean_start_date = util.doy_2_date(year, mean_start_doy)
            mean_end_date = util.doy_2_date(year, mean_end_doy)
        else:
            mean_start_doy, mean_end_doy, mean_length = 0, 0, 0
            mean_start_date, mean_end_date = "", ""

        ## Append mean annual growing season data to list
        gs_mean_annual_data.append(
            [station, crop_num, crop_name,
             mean_start_doy, mean_end_doy,
             mean_start_date, mean_end_date, mean_length])

        ## Cleanup
        del season_array
        del gs_sum, gs_cnt, gs_mean
        del start_sum, start_cnt, start_mean
        del end_sum, end_cnt, end_mean
        del mean_start_doy, mean_end_doy, mean_length
        del mean_start_date, mean_end_date
        del year_array, year_sub_array, doy_array
        del daily_df
        logging.debug("")

    ## Close bad data file log
    baddata_file.close()

    ## Build output record array file
    gs_summary_csv = csv.writer(open(gs_summary_path, 'wb'))
    gs_summary_csv.writerow( 
        ['STATION', 'CROP_NUM', 'CROP_NAME', 'YEAR',
         'START_DOY', 'END_DOY', 'START_DATE', 'END_DATE', 'GS_LENGTH'])
    gs_summary_csv.writerows(gs_summary_data)

    ## Build output record array file
    gs_mean_annual_csv = csv.writer(open(gs_mean_annual_path, 'wb'))
    gs_mean_annual_csv.writerow( 
        ['STATION', 'CROP_NUM', 'CROP_NAME', 'MEAN_START_DOY', 'MEAN_END_DOY',
         'MEAN_START_DATE', 'MEAN_END_DATE', 'MEAN_GS_LENGTH'])
    gs_mean_annual_csv.writerows(gs_mean_annual_data)

    ## Cleanup
    del gs_summary_path, gs_summary_name
    del gs_summary_csv, gs_summary_data
    del gs_mean_annual_path, gs_mean_annual_name
    del gs_mean_annual_csv, gs_mean_annual_data

################################################################################

def parse_args():
    parser = argparse.ArgumentParser(
        description='Compute Growing Season Statistics',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        '-i', '--ini', metavar='PATH',
        type=lambda x: util.is_valid_file(parser, x), help='Input file')
    parser.add_argument(
        '--start', default=None, type=util.valid_date,
        help='Start date (format YYYY-MM-DD)', metavar='DATE')
    parser.add_argument(
        '--end', default=None, type=util.valid_date,
        help='End date (format YYYY-MM-DD)', metavar='DATE')
    parser.add_argument(
        '-c', '--crops', default='', type=str, 
        help='Comma separate list or range of crops to compare')
    parser.add_argument(
        '-o', '--overwrite', default=None, action="store_true", 
        help='Force overwrite of existing files')
    parser.add_argument(
        '--debug', default=logging.INFO, const=logging.DEBUG,
        help='Debug level logging', action="store_const", dest="loglevel")
    args = parser.parse_args()

    ## Convert relative paths to absolute paths
    if args.ini and os.path.isfile(os.path.abspath(args.ini)):
        args.ini = os.path.abspath(args.ini)
    return args

################################################################################
if __name__ == '__main__':
    args = parse_args()
    logging.basicConfig(level=args.loglevel, format='%(message)s')
    
    ## Try using the command line argument if it was set
    if args.ini:
        ini_path = args.ini
    ## If script was double clicked, set project folder with GUI
    elif not 'PROMPT' in os.environ:
        ini_path = util.get_path(os.getcwd(), 'Select the target INI file')
    ## Try using the current working directory if there is only one INI
    ## Could look for daily_stats folder, run_basin.py, and/or ini file
    elif len([x for x in os.listdir(os.getcwd()) if x.lower().endswith('.ini')]) == 1:
        ini_path = [
            os.path.join(os.getcwd(), x) for x in os.listdir(os.getcwd()) 
            if x.lower().endswith('.ini')][0]
    ## Eventually list available INI files and prompt the user to select one
    ## For now though, use the GUI
    else:
        ini_path = util.get_path(os.getcwd(), 'Select the target INI file')

    logging.basicConfig(level=args.loglevel, format='%(message)s')
    logging.info('\n{0}'.format('#'*80))
    logging.info('{0:<20s} {1}'.format("Run Time Stamp:", dt.datetime.now().isoformat(' ')))
    logging.info('{0:<20s} {1}'.format("Current Directory:", os.getcwd()))
    logging.info('{0:<20s} {1}'.format("Script:", os.path.basename(sys.argv[0])))

    main(ini_path, start_date=args.start, end_date=args.end,
         crop_str=args.crops, overwrite_flag=args.overwrite)
