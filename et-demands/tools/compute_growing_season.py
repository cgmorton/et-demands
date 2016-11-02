#--------------------------------
# Name:         compute_growing_season.py
# Purpose:      Extract growing season data from daily output files
# Author:       Charles Morton
# Created       2015-12-08
# Python:       2.7
#--------------------------------

import argparse
import csv
import datetime as dt
import logging
import os
import sys

import numpy as np
import pandas as pd

import util

def main(ini_path, start_date = None, end_date = None, crop_str = ''):
    """Compuate Growing Season Statistics

    Args:
        ini_path (str): file path of project INI file
        start_date (str): ISO format date string (YYYY-MM-DD)
        end_date (str): ISO format date string (YYYY-MM-DD)
        crop_str (str): comma separate list or range of crops to compare

    Returns:
        None
    """

    # Field names

    date_field = 'Date'
    doy_field = 'DOY'
    year_field = 'Year'
    # month_field = 'Month'
    # day_field   = 'Day'
    season_field = 'Season'

    # Output file/folder names

    gs_summary_name = 'growing_season_full_summary.csv'
    gs_mean_annual_name = 'growing_season_mean_annual.csv'
    baddata_name = 'growing_season_bad_data.txt'

    # Delimiter

    sep = ','
    # sep = r"\s*"

    logging.info('\nComputing growing season statistics')
    logging.info('  INI: {}'.format(ini_path))

    # Check that INI file can be read
    
    crop_et_sec = 'CROP_ET'
    config = util.read_ini(ini_path, crop_et_sec)

    # Get project workspace and daily ET folder from INI file
    # project workspace can use old or new ini file
    
    try:
        project_ws = config.get('PROJECT', 'project_folder')
    except:
        try:
            project_ws = config.get(crop_et_sec, 'project_folder')
        except:
            logging.error(
                'ERROR: project_folder ' +
                'parameter is not set in INI file')
            sys.exit()

    def get_config_param(config, param_name, section):
        """"""
        try:
            param_value = config.get(section, param_name)
        except:
            logging.error(('ERROR: {} parameter is not set' +
                           ' in INI file').format(param_name))
            sys.exit()
        return param_value

    daily_stats_ws = os.path.join(
            project_ws, get_config_param(
            config, 'daily_output_folder', crop_et_sec))
    gs_stats_ws = os.path.join(
        project_ws, get_config_param(config, 'gs_output_folder', crop_et_sec))
    try:
        name_format = config.get(crop_et_sec, 'name_format')
        if name_format is None or name_format == 'None': 
            name_format = '%s_daily_crop_%c.csv'
    except:
        name_format = '%s_daily_crop_%c.csv'
    if '%s' not in name_format or '%c' not in name_format:
        logging.error("crop et file name format requires '%s' and '%c' wildcards.")
        sys.exit()
    swl = name_format.index('%s')
    cwl = name_format.index('%c')
    prefix = name_format[(swl + 2):cwl]
    suffix = name_format[(cwl + 2):len(name_format)]
    suf_no_ext = suffix[:(suffix.index('.'))]

    # Check workspaces

    if not os.path.isdir(daily_stats_ws):
        logging.error(('\nERROR: daily ET stats folder {0} ' +
                       'could be found\n').format(daily_stats_ws))
        sys.exit()
    if not os.path.isdir(gs_stats_ws):
        os.mkdir(gs_stats_ws)

    # Range of data to use

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

    # Allow user to subset crops from INI

    try:
        crop_skip_list = sorted(list(util.parse_int_set(
            config.get(crop_et_sec, 'crop_skip_list'))))
    except:
        crop_skip_list = []
        # crop_skip_list = [44, 45, 46, 55, 56, 57]
    try:
        crop_test_list = sorted(list(util.parse_int_set(
            config.get(crop_et_sec, 'crop_test_list'))))
    except:
        crop_test_list = []

    # Overwrite INI crop list with user defined values
    # Could also append to INI crop list

    if crop_str:
        try:
            crop_test_list = list(util.parse_int_set(crop_str))
        # try:
        #     crop_test_list = sorted(list(set(
        #         crop_test_list + list(util.parse_int_set(crop_str)))
        except:
            pass
    logging.debug('\n  crop_test_list = {0}'.format(crop_test_list))
    logging.debug('  crop_skip_list = {0}'.format(crop_skip_list))

    # Output file paths

    gs_summary_path = os.path.join(gs_stats_ws, gs_summary_name)
    gs_mean_annual_path = os.path.join(gs_stats_ws, gs_mean_annual_name)
    baddata_path = os.path.join(gs_stats_ws, baddata_name)

    # Initialize output data arrays and open bad data log file

    gs_summary_data = []
    gs_mean_annual_data = []
    baddata_file = open(baddata_path, 'w')

    # make used file list using name_format attributes
    
    data_file_list = []
    for item in os.listdir(daily_stats_ws):
        if prefix in item and suffix in item:
            if not item in data_file_list:
                data_file_list.append(os.path.join(daily_stats_ws, item))
    if len(data_file_list) < 1:
        logging.info('No files found')
        sys.exit()
    data_file_list = sorted(data_file_list)

    # Process each file
    
    for file_path in data_file_list:
        file_name = os.path.basename(file_path)
        logging.debug('')
        logging.info('  Processing {0}'.format(file_name))
        station, crop_num = os.path.splitext(file_name)[0].split(prefix)
        crop_num = int(crop_num[:crop_num.index(suf_no_ext)])
        logging.debug('    Station:         {0}'.format(station))
        logging.debug('    Crop Num:        {0}'.format(crop_num))
        if station == 'temp': continue

        # Get crop name

        with open(file_path, 'r') as file_f:
            crop_name = file_f.readline().split('-', 1)[1].strip()
            logging.debug('    Crop:            {0}'.format(crop_name))

        # Read data from file into record array (structured array)

        daily_df = pd.read_table(file_path, header = 0, comment = '#', sep = sep)
        logging.debug('    Fields: {0}'.format(
            ', '.join(daily_df.columns.values)))
        daily_df[date_field] = pd.to_datetime(daily_df[date_field])
        daily_df.set_index(date_field, inplace = True)
        daily_df[year_field] = daily_df.index.year
        # daily_df[year_field] = daily_df[date_field].map(lambda x: x.year)

        # Build list of unique years

        year_array = np.sort(np.unique(
            np.array(daily_df[year_field]).astype(np.int)))
        logging.debug('    All Years: {0}'.format(
            ', '.join(list(util.ranges(year_array.tolist())))))
        # logging.debug('    All Years: {0}'.format(
        #    ','.join(map(str, year_array.tolist()))))

        # Don't include first year in stats

        crop_year_start = min(daily_df[year_field])
        logging.debug('    Skipping {}, first year'.format(crop_year_start))
        daily_df = daily_df[daily_df[year_field] > crop_year_start]

        # Check if start and end years have >= 365 days

        crop_year_start = min(daily_df[year_field])
        crop_year_end = max(daily_df[year_field])
        if sum(daily_df[year_field] == crop_year_start) < 365:
            logging.debug('    Skipping {}, missing days'.format(
                crop_year_start))
            daily_df = daily_df[daily_df[year_field] > crop_year_start]
        if sum(daily_df[year_field] == crop_year_end) < 365:
            logging.debug('    Skipping {}, missing days'.format(
                crop_year_end))
            daily_df = daily_df[daily_df[year_field] < crop_year_end]
        del crop_year_start, crop_year_end

        # Only keep years between year_start and year_end
        
        if year_start:
            daily_df = daily_df[daily_df[year_field] >= year_start]
        if year_end:
            daily_df = daily_df[daily_df[year_field] <= year_end]

        year_sub_array = np.sort(np.unique(np.array(daily_df[year_field]).astype(np.int)))
        logging.debug('    Data Years: {0}'.format(
            ', '.join(list(util.ranges(year_sub_array.tolist())))))
        # logging.debug('    Data Years: {0}'.format(
        #    ','.join(map(str, year_sub_array.tolist()))))

        # Get separate date related fields

        date_array = daily_df.index.date
        year_array = daily_df[year_field].values.astype(np.int)
        doy_array = daily_df[doy_field].values.astype(np.int)

        # Remove leap days
        # leap_array = (doy_array == 366)
        # doy_sub_array = np.delete(doy_array, np.where(leap_array)[0])

        # Build separate arrays for each set of crop specific fields

        season_array = np.array(daily_df[season_field])

        # # Original code from growing_season script
        # Initialize mean annual growing season length variables

        gs_sum, gs_cnt, gs_mean = 0, 0, 0
        start_sum, start_cnt, start_mean = 0, 0, 0
        end_sum, end_cnt, end_mean = 0, 0, 0

        # Process each year

        for year_i, year in enumerate(year_sub_array):
            year_crop_str = "Crop: {0:2d} {1:32s}  Year: {2}".format(
                crop_num, crop_name, year)
            logging.debug(year_crop_str)

            # Extract data for target year

            year_mask = (year_array == year)
            date_sub_array = date_array[year_mask]
            doy_sub_array = doy_array[year_mask]
            season_sub_mask = season_array[year_mask]

            # Look for transitions in season value
            # Start transitions up day before actual start
            # End transitions down on end date

            try:
                start_i = np.where(np.diff(season_sub_mask) == 1)[0][0] + 1
            except:
                start_i = None
            try:
                end_i = np.where(np.diff(season_sub_mask) == -1)[0][0]
            except:
                end_i = None

            # If start transition is not found, season starts on DOY 1

            if start_i is None and end_i is not None:
                start_i = 0
            # If end transition is not found, season ends on DOY 365/366

            elif start_i is not None and end_i is None:
                end_i = -1

            # If neither transition is found, season is always on
            # elif start_i is None and end_i is None:
            #     , end_i = 0, -1

            # Calculate start and stop day of year
            # Set start/end to 0 if season never gets set to 1

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

            # Track growing season length and mean annual g.s. length

            if start_doy > 0 and end_doy > 0 and year_i != 0:
                start_sum += start_doy
                end_sum += end_doy
                gs_sum += gs_length
                start_cnt += 1
                end_cnt += 1
                gs_cnt += 1

            # Append data to list

            gs_summary_data.append(
                [station, crop_num, crop_name, year,
                 start_doy, end_doy, start_date, end_date, gs_length])

            # Cleanup
            del year_mask, doy_sub_array, season_sub_mask
            del start_doy, end_doy, start_date, end_date, gs_length

        # Calculate mean annual growing season start/end/length

        if gs_cnt > 0:
            mean_start_doy = int(round(float(start_sum) / start_cnt))
            mean_end_doy = int(round(float(end_sum) / end_cnt))
            mean_length = int(round(float(gs_sum) / gs_cnt))
            mean_start_date = util.doy_2_date(year, mean_start_doy)
            mean_end_date = util.doy_2_date(year, mean_end_doy)
        else:
            mean_start_doy, mean_end_doy, mean_length = 0, 0, 0
            mean_start_date, mean_end_date = "", ""

        # Append mean annual growing season data to list

        gs_mean_annual_data.append(
            [station, crop_num, crop_name,
             mean_start_doy, mean_end_doy,
             mean_start_date, mean_end_date, mean_length])

        # Cleanup

        del season_array
        del gs_sum, gs_cnt, gs_mean
        del start_sum, start_cnt, start_mean
        del end_sum, end_cnt, end_mean
        del mean_start_doy, mean_end_doy, mean_length
        del mean_start_date, mean_end_date
        del year_array, year_sub_array, doy_array
        del daily_df
        logging.debug("")

    # Close bad data file log

    baddata_file.close()

    # Build output record array file

    gs_summary_csv = csv.writer(open(gs_summary_path, 'wb'))
    gs_summary_csv.writerow(
        ['STATION', 'CROP_NUM', 'CROP_NAME', 'YEAR',
         'START_DOY', 'END_DOY', 'START_DATE', 'END_DATE', 'GS_LENGTH'])
    gs_summary_csv.writerows(gs_summary_data)

    # Build output record array file

    gs_mean_annual_csv = csv.writer(open(gs_mean_annual_path, 'wb'))
    gs_mean_annual_csv.writerow(
        ['STATION', 'CROP_NUM', 'CROP_NAME', 'MEAN_START_DOY', 'MEAN_END_DOY',
         'MEAN_START_DATE', 'MEAN_END_DATE', 'MEAN_GS_LENGTH'])
    gs_mean_annual_csv.writerows(gs_mean_annual_data)

    # Cleanup

    del gs_summary_path, gs_summary_name
    del gs_summary_csv, gs_summary_data
    del gs_mean_annual_path, gs_mean_annual_name
    del gs_mean_annual_csv, gs_mean_annual_data

def parse_args():
    """"""
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
        '--debug', default = logging.INFO, const = logging.DEBUG,
        help='Debug level logging', action = "store_const", dest = "loglevel")
    args = parser.parse_args()

    # Convert relative paths to absolute paths
    
    if args.ini and os.path.isfile(os.path.abspath(args.ini)):
        args.ini = os.path.abspath(args.ini)
    return args

if __name__ == '__main__':
    args = parse_args()

    # Try using command line argument if it was set
    
    if args.ini:
        ini_path = args.ini
        
    # If script was double clicked, set project folder with GUI
    
    elif 'PROMPT' not in os.environ:
        ini_path = util.get_path(os.getcwd(), 'Select target INI file')

    # Try using current working directory if there is only one INI
    # Could look for daily_stats folder, run_basin.py, and/or ini file

    elif len([x for x in os.listdir(os.getcwd()) if x.lower().endswith('.ini')]) == 1:
        ini_path = [
            os.path.join(os.getcwd(), x) for x in os.listdir(os.getcwd())
            if x.lower().endswith('.ini')][0]

    # Eventually list available INI files and prompt user to select one
    # For now though, use GUI

    else:
        ini_path = util.get_path(os.getcwd(), 'Select target INI file')
    logging.basicConfig(level = args.loglevel, format = '%(message)s')
    logging.info('\n{0}'.format('#' * 80))
    log_f = '{0:<20s} {1}'
    logging.info(log_f.format(
        'Run Time Stamp:', dt.datetime.now().isoformat(' ')))
    logging.info(log_f.format('Current Directory:', os.getcwd()))
    logging.info(log_f.format('Script:', os.path.basename(sys.argv[0])))

    main(ini_path, start_date = args.start, end_date = args.end,
         crop_str = args.crops)
