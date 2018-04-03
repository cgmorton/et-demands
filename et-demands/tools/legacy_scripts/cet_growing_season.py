#--------------------------------
# Name:         cet_growing_season.py
# Purpose:      Extract growing season data from Python ET-Demands output files
# Python:       2.7
#--------------------------------

import argparse
import csv
import datetime as dt
import logging
import os
import sys
from time import clock

import numpy as np


def main(output_ws):
    """"""

    # Input Field names
    date_field = 'Date'
    doy_field = 'doy'
    pmeto_field = 'PMETo'
    precip_field = 'Prmm'

    etact_field = 'ETact'
    etact_field = 'ETpot'
    etbas_field = 'ETbas'
    irrig_field = 'Irrn'
    seasn_field = 'Seasn'
    runof_field = 'Runof'
    dperc_field = 'DPerc'

    # Build list of station/crop files
    # input_re = re.compile('[a-zA-Z]+_\d+_\d+.[a-zA-Z_]+')
    # input_path_list = sorted([
    #     .path.join(output_ws, item) for item in os.listdir(output_ws)
    #      (os.path.isfile(os.path.join(output_ws, item)) and
    #        input_re.match(item))])
    input_path_list = sorted([
        os.path.join(output_ws, item) for item in os.listdir(output_ws)
        if (os.path.isfile(os.path.join(output_ws, item)) and
            os.path.splitext(item)[-1] not in ['.py', '.txt'])])

    # Crops will be skipped that are listed here
    #   (list crop # as int, not string)
    # crop_name_skip_list = [
    #    'Bare soil', 'Mulched soil / wheat stubble',
    #    'Dormant turf/sod (winter time)',
    #    'Open water - Shallow', 'Open water - Deep', 'Open water - Stock']
    # crop_num_skip_list = [44, 45, 46, 55]
    crop_num_skip_list = [44, 45, 46, 55, 56, 57]

    # Output file/folder names
    gs_summary_name = 'growing_season_full_summary.csv'
    gs_mean_annual_name = 'growing_season_mean_annual.csv'
    baddata_name = 'growing_season_bad_data.txt'
    kc_name = 'kc_files'
    gs_name = 'growing_season_files'

    # Output folders
    kc_ws = os.path.join(output_ws, kc_name)
    gs_ws = os.path.join(output_ws, gs_name)
    if not os.path.isdir(kc_ws):
        os.mkdir(kc_ws)
    if not os.path.isdir(gs_ws):
        os.mkdir(gs_ws)

    # Output file paths
    gs_summary_path = os.path.join(gs_ws, gs_summary_name)
    gs_mean_annual_path = os.path.join(gs_ws, gs_mean_annual_name)
    baddata_path = os.path.join(gs_ws, baddata_name)

    # Initialize output data arrays and open bad data log file
    total_clock = clock()
    gs_summary_data = []
    gs_mean_annual_data = []
    baddata_f = open(baddata_path, 'w')

    # Process each input file
    for input_path in input_path_list:
        site_clock = clock()
        input_name = os.path.basename(input_path)
        logging.info("{0}".format(input_name))

        # Process each crop
        station, crop_num = os.path.splitext(input_name)[0].rsplit('_', 1)
        crop_num = int(crop_num)
        crop_name = os.path.splitext(input_name)[-1]
        crop_name = crop_name.replace('.', ' ').replace('_', ' ')
        crop_name = ' '.join(crop_name.split())
        logging.debug("  Station: {0}".format(station))
        logging.debug("  Crop: {0} {1}".format(crop_num, crop_name))
        if crop_num in crop_num_skip_list:
            logging.debug("  Skipping, crop number in skip list")
            continue
        # if crop_name in crop_name_skip_list:
        #     .debug("  Skipping, crop name in skip list")
        #

        # Read in file to memory
        input_f = open(input_path, 'r')
        input_lines = input_f.readlines()
        input_header = input_lines.pop(0)
        input_f.close()
        del input_f

        # Read data from file into record array (structured array)
        data = np.genfromtxt(input_path, names=True)
        logging.debug("  Fields: {0}".format(', '.join(data.dtype.names)))

        # Build separate arrays for each field of non-crop specific data
        date_list = [
            dt.datetime.strptime(str(int(date_flt)), '%Y%m%d')
            for date_flt in data[date_field]]
        date_array = np.array(date_list)
        doy_array = data[doy_field].astype(np.int)
        year_array = np.array([int(item.year) for item in date_list])
        month_array = np.array([int(item.month) for item in date_list])
        day_array = np.array([int(item.day) for item in date_list])
        pmeto_array = data[pmeto_field]
        precip_array = data[precip_field]
        # date_array = np.array([
        #     "{0}/{1}/{2}".format(year, int(month), int(day))
        #      year, month, day in zip(year_array, month_array, day_array)])

        # Build list of unique years
        year_list = sorted(map(int, list(set(year_array))))
        logging.debug("  Years: {0}".format(', '.join(map(str, year_list))))

        # Build separate arrays for each set of crop specific fields
        etact_array = data[etact_field]
        etbas_array = data[etbas_field]
        irrig_array = data[irrig_field]
        season_array = data[seasn_field]
        kc_array = etact_array / pmeto_array
        kcb_array = etbas_array / pmeto_array

        # Open a new Kc file for each station/crop
        kc_name = 'Kc_{0}_Crop_{1:02d}.csv'.format(station, crop_num)
        kc_csv = csv.writer(open(os.path.join(kc_ws, kc_name), 'wb'))
        kc_csv.writerow(
            ['Date', 'Year', 'Month', 'Day', 'DOY',
             pmeto_field, 'PPT', etact_field, etbas_field,
             'Kc', 'Kcb', 'Season', 'Irrigation'])

        # Save Kc data to file then cleanup kc specific arrays
        temp_array = np.transpose(np.vstack(
            [date_array, year_array, month_array, day_array, doy_array,
             pmeto_array, precip_array, etact_array, etbas_array,
             kc_array, kcb_array, season_array, irrig_array]))
        kc_csv.writerows(temp_array)
        del kc_csv, kc_name
        del etact_array, etbas_array, irrig_array,
        del kc_array, kcb_array, temp_array

        # Initialize mean annual growing season length variables
        length_sum, length_cnt, length_mean = 0, 0, 0
        start_sum, start_cnt, start_mean = 0, 0, 0
        end_sum, end_cnt, end_mean = 0, 0, 0

        # Process each year
        for year in year_list:
            year_crop_str = "  Crop: {0:2d} {1:32s}  Year: {2}".format(
                crop_num, crop_name, year)
            logging.debug(year_crop_str)

            # Extract data for target year
            year_mask = (year_array == year)
            doy_sub_array = doy_array[year_mask]
            season_index = np.where(season_array[year_mask] == 1)[0]

            # Calculate start and stop day of year
            # Set start/end to 0 if season never gets set to 1
            if not np.any(season_index):
                skip_str = "    Skipping, season flag was never set to 1"
                logging.debug(skip_str)
                baddata_f.write('{0}  {1} {2}\n'.format(
                    input_name, year_crop_str, skip_str))
                start_doy, end_doy = 0, 0
                start_date, end_date = "", ""
                end_date = ""
            else:
                start_doy = int(doy_sub_array[season_index[0]])
                end_doy = int(doy_sub_array[season_index[-1]])
                start_date = doy_2_date(year, start_doy)
                end_date = doy_2_date(year, end_doy)
            logging.debug("  Start: {0} ({1})  End: {2} ({3})".format(
                start_doy, start_date, end_doy, end_date))

            # Track growing season length and mean annual g.s. length
            if end_doy >= start_doy > 0:
                start_sum += start_doy
                end_sum += end_doy
                gs_length = (end_doy - start_doy + 1)
                length_sum += gs_length
                start_cnt += 1
                end_cnt += 1
                length_cnt += 1
            else:
                gs_length = 0

            # Append data to list
            gs_summary_data.append(
                [input_name, crop_num, crop_name, year,
                 start_doy, end_doy, start_date, end_date, gs_length])

            # Cleanup
            del year_mask, doy_sub_array, season_index
            del start_doy, end_doy, gs_length

        # Calculate mean annual growing season start/end/length
        if length_cnt > 0:
            mean_start_doy = int(round(float(start_sum) / start_cnt))
            mean_end_doy = int(round(float(end_sum) / end_cnt))
            mean_length = int(round(float(length_sum) / length_cnt))
            mean_start_date = doy_2_date(year, mean_start_doy)
            mean_end_date = doy_2_date(year, mean_end_doy)
        else:
            mean_start_doy, mean_end_doy, mean_length = 0, 0, 0
            mean_start_date, mean_end_date = "", ""

        # Append mean annual growing season data to list
        gs_mean_annual_data.append(
            [input_name, crop_num, crop_name,
             mean_start_doy, mean_end_doy,
             mean_start_date, mean_end_date, mean_length])

        # Cleanup
        del season_array
        del length_sum, length_cnt, length_mean
        del start_sum, start_cnt, start_mean
        del end_sum, end_cnt, end_mean
        del mean_start_doy, mean_end_doy, mean_length
        del mean_start_date, mean_end_date

        del year_array, month_array, day_array, doy_array,
        del date_array, date_list
        del pmeto_array, precip_array
        del data, year_list
        del input_name
        logging.debug("  SITE TIME: {0}".format(clock()-site_clock))
        logging.debug("")
        # break

    # Close bad data file log
    baddata_f.close()

    # Build output record array file
    if gs_summary_data:
        gs_summary_csv = csv.writer(open(gs_summary_path, 'wb'))
        gs_summary_csv.writerow(
            ['FILE', 'CROP_NUM', 'CROP_NAME', 'YEAR',
             'START_DOY', 'END_DOY', 'START_DATE', 'END_DATE',
             'GS_LENGTH'])
        gs_summary_csv.writerows(gs_summary_data)
        del gs_summary_csv, gs_summary_data

    # Build output record array file
    if gs_mean_annual_data:
        gs_mean_annual_csv = csv.writer(open(gs_mean_annual_path, 'wb'))
        gs_mean_annual_csv.writerow(
            ['FILE', 'CROP_NUM', 'CROP_NAME',
             'MEAN_START_DOY', 'MEAN_END_DOY',
             'MEAN_START_DATE', 'MEAN_END_DATE', 'MEAN_GS_LENGTH'])
        gs_mean_annual_csv.writerows(gs_mean_annual_data)
        del gs_mean_annual_csv, gs_mean_annual_data

    # Cleanup
    del gs_summary_path, gs_summary_name
    del gs_mean_annual_path, gs_mean_annual_name
    logging.debug("\nTOTAL TIME: {0}".format(clock()-total_clock))


def doy_2_date(test_year, test_doy):
    """"""
    test_date = dt.datetime.strptime(
        '{0} {1}'.format(test_year, test_doy), '%Y %j').strftime('%Y/%m/%d')
    return test_date


def parse_args():
    """"""
    parser = argparse.ArgumentParser(
        description='Extract growing season data from ET-Demands output')
    parser.add_argument(
        'workspace', nargs='?', default=os.path.join(os.getcwd(), 'cet'),
        help='ET-Demands output folder', metavar='FOLDER')
    parser.add_argument(
        '--debug', default=logging.INFO, const=logging.DEBUG,
        help='Debug level logging', action="store_const", dest="loglevel")
    args = parser.parse_args()

    # Convert PMData folder to an absolute path if necessary
    if args.workspace and os.path.isdir(os.path.abspath(args.workspace)):
        args.workspace = os.path.abspath(args.workspace)
    return args


if __name__ == '__main__':
    args = parse_args()

    logging.basicConfig(level=logging.INFO, format='%(message)s')
    logging.info('\n{0}'.format('#'*80))
    log_f = '{0:<20s} {1}'
    logging.info(log_f.format(
        'Run Time Stamp:', dt.datetime.now().isoformat(' ')))
    logging.info(log_f.format('Current Directory:', args.workspace))
    logging.info(log_f.format('Script:', os.path.basename(sys.argv[0])))

    main(output_ws=args.workspace)
