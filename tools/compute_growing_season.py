#--------------------------------
# Name:         compute_growing_season.py
# Purpose:      Extract growing season data from daily output files
# Author:       Charles Morton
# Created       2015-09-01
# Python:       2.7
#--------------------------------

import argparse
import csv
import datetime as dt
import logging
import os
import re
import sys

import numpy as np
import pandas as pd

def main(project_ws, start_date=None, end_date=None, crop_str='',
         overwrite_flag=False):
    """Compuate Growing Season Statistics

    Args:
        project_ws (str): Project workspace
        start_date (str): ISO format date string (YYYY-MM-DD)
        end_date (str): ISO format date string (YYYY-MM-DD)
        crop_str (str): comma separate list or range of crops to compare
        overwrite_flag (bool): If True, overwrite existing files

    Returns:
        None
    """

    ## Input names
    input_folder = 'daily_stats'

    ## Output names
    output_folder = 'growing_season_stats'

    ## Field names
    date_field  = 'Date'
    doy_field   = 'DOY'
    ##year_field   = 'Year'
    ##month_field = 'Month'
    ##day_field   = 'Day'
    season_field = 'Season'

    ## Only process a subset of the crops
    crop_keep_list = list(parse_int_set(crop_str))
    ## Crops will be skipped that are listed here
    ##   (list crop # as int, not string)
    crop_skip_list = [44, 45, 46, 55]

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

    try:
        logging.info('\nComputing growing season statistics')
        logging.info('  Project Folder: {0}'.format(project_ws))

        ## Input workspaces
        input_ws = os.path.join(project_ws, input_folder)

        ## Output workspaces
        output_ws = os.path.join(project_ws, output_folder)

        ## Check workspaces
        if not os.path.isdir(project_ws):
            logging.error(
                '\nERROR: The project folder {0} could be found\n'.format(project_ws))
            sys.exit()
        if not os.path.isdir(input_ws):
            logging.error(
                '\nERROR: The daily ET folder {0} could be found\n'.format(input_ws))
            sys.exit()
        if not os.path.isdir(output_ws):
            os.mkdir(output_ws)

        ## Range of data to plot
        try:
            year_start = datetime.strptime(start_date, '%Y-%m-%d').year
            logging.info('  Start Year:  {0}'.format(year_start))
        except:
            year_start = None
        try:
            year_end = datetime.datetime.strptime(end_date, '%Y-%m-%d').year
            logging.info('  End Year:    {0}'.format(year_end))
        except:
            year_end = None
        if year_start and year_end and year_end <= year_start:
            logging.error('\n  ERROR: End date must be after start date\n')
            sys.exit()

        ## Output file paths
        gs_summary_path = os.path.join(output_ws, gs_summary_name)
        gs_mean_annual_path = os.path.join(output_ws, gs_mean_annual_name)
        baddata_path = os.path.join(output_ws, baddata_name)

        ## Build list of site files
        ##site_file_re = '^RG\d{8}ETca.dat$'
        ##site_file_list = sorted([item for item in os.listdir(workspace)
        ##                         if re.match(site_file_re, item)])
        site_file_list = sorted([
            item for item in os.listdir(input_ws)
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
            [os.path.join(input_ws, f_name) for f_name in os.listdir(input_ws)
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
            data_df = pd.read_table(
                file_path, header=0, comment='#', sep=sep, engine='python')
            logging.debug('\nFields: \n{0}'.format(data_df.columns.values))
            data_df[date_field] = pd.to_datetime(data_df[date_field])
            data_df.set_index(date_field, inplace=True)
            data_df['year'] = data_df.index.year
            ##data_df['year'] = data_df[date_field].map(lambda x: x.year)

            ## Build list of unique years
            year_sub_array = np.sort(np.unique(data_df['year'].values.astype(np.int)))
            logging.debug('\nAll Years: \n{0}'.format(year_sub_array))

            ## Only keep years between year_start and year_end
            if year_start:
                crop_year_start = year_start
                data_df = data_df.ix['year' >= year_start]
                crop_year_start = max(year_end, min(year_sub_array))
            else:
                crop_year_start = min(year_sub_array)
            if year_end:
                data_df = data_df.ix['year' <= year_end]
                crop_year_end = min(year_end, max(year_sub_array))
            else:
                crop_year_end = max(year_sub_array)
            year_sub_array = np.sort(np.unique(data_df['year'].values.astype(np.int)))
            logging.debug('\nCalc Years: \n{0}'.format(year_sub_array))

            ## Get separate date related fields
            date_array = data_df.index.date
            year_array = data_df['year'].values.astype(np.int)
            doy_array = data_df[doy_field].values.astype(np.int)

            ## Remove leap days
            ##leap_array = (doy_array == 366)
            ##doy_sub_array = np.delete(doy_array, np.where(leap_array)[0])

            if crop_skip_list and crop_num in crop_skip_list:
                logging.debug('    Skipping, crop number in crop_skip_list')
                continue
            elif crop_keep_list and crop_num not in crop_keep_list:
                logging.debug('    Skipping, crop number not in crop_keep_list')
                continue
            
            ## Build separate arrays for each set of crop specific fields
            season_array = np.array(data_df[season_field])

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
                mean_start_date = doy_2_date(year, mean_start_doy)
                mean_end_date = doy_2_date(year, mean_end_doy)
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
            del data_df
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

    except:
        logging.exception("Unhandled Exception Error\n\n")
        raw_input("Press ENTER to close")

################################################################################

def get_project_directory(workspace):
    import Tkinter, tkFileDialog
    root = Tkinter.Tk()
    user_ws = tkFileDialog.askdirectory(
        initialdir=workspace, parent=root,
        title='Select the project directory', mustexist=True)
    root.destroy()
    return user_ws

def doy_2_date(test_year, test_doy):
    return dt.datetime.strptime('{0:04d}_{1:03d}'.format(
        int(test_year), int(test_doy)), '%Y_%j').strftime('%Y-%m-%d')

def valid_date(input_date):
    """Check that a date string is ISO format (YYYY-MM-DD)

    This function is used to check the format of dates entered as command
      line arguments.
    DEADBEEF - It would probably make more sense to have this function 
      parse the date using dateutil parser (http://labix.org/python-dateutil)
      and return the ISO format string

    Args:
        input_date: string
    Returns:
        string 
    Raises:
        ArgParse ArgumentTypeError
    """
    try:
        input_dt = datetime.datetime.strptime(input_date, "%Y-%m-%d")
        return input_date
    except ValueError:
        msg = "Not a valid date: '{0}'.".format(input_date)
        raise argparse.ArgumentTypeError(msg)

def parse_int_set(nputstr=""):
    """Return list of numbers given a string of ranges

    http://thoughtsbyclayg.blogspot.com/2008/10/parsing-list-of-numbers-in-python.html
    """
    selection = set()
    invalid = set()
    # tokens are comma seperated values
    tokens = [x.strip() for x in nputstr.split(',')]
    for i in tokens:
        try:
            # typically tokens are plain old integers
            selection.add(int(i))
        except:
            # if not, then it might be a range
            try:
                token = [int(k.strip()) for k in i.split('-')]
                if len(token) > 1:
                    token.sort()
                    # we have items seperated by a dash
                    # try to build a valid range
                    first = token[0]
                    last = token[len(token)-1]
                    for x in range(first, last+1):
                        selection.add(x)
            except:
                # not an int and not a range...
                invalid.add(i)
    # Report invalid tokens before returning valid selection
    ##print "Invalid set: " + str(invalid)
    return selection

def parse_args():
    parser = argparse.ArgumentParser(
        description='Compute Growing Season Statistics',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        '--project', metavar='FOLDER', help='Project Folder')
    parser.add_argument(
        '--start', default=None, type=valid_date,
        help='Start date (format YYYY-MM-DD)', metavar='DATE')
    parser.add_argument(
        '--end', default=None, type=valid_date,
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

    ## Convert project folder to an absolute path if necessary
    if args.project and os.path.isdir(os.path.abspath(args.project)):
        args.project = os.path.abspath(args.project)
    return args

################################################################################
if __name__ == '__main__':
    args = parse_args()
    
    ## Try using the command line argument if it was set
    if args.project:
        project_ws = args.project
    ## If script was double clicked, set project folder with GUI
    elif not 'PROMPT' in os.environ:
        project_ws = get_project_directory(os.getcwd())
    ## Try using the current working directory
    ## Could look for daily_stats folder, run_basin.py, and/or ini file
    elif (os.path.isdir(os.path.join(os.getcwd(), 'daily_stats')) and
          os.path.isfile(os.path.join(os.getcwd(), 'run_basin.py'))):
        project_ws = os.getcwd()
    else:
        project_ws = get_project_directory(os.getcwd())

    logging.basicConfig(level=args.loglevel, format='%(message)s')
    logging.info('\n{0}'.format('#'*80))
    logging.info('{0:<20s} {1}'.format("Run Time Stamp:", dt.datetime.now().isoformat(' ')))
    logging.info('{0:<20s} {1}'.format("Current Directory:", project_ws))
    logging.info('{0:<20s} {1}'.format("Script:", os.path.basename(sys.argv[0])))

    main(project_ws, start_date=args.start, end_date=args.end,
         crop_str=args.crops, overwrite_flag=args.overwrite)
