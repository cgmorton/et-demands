#--------------------------------
# Name:         split_vb_crop_daily_timeseries.py
# Purpose:      Split daily data timeseries into separate files for each crop
# Author:       Charles Morton
# Created       2016-07-19
# Python:       2.7
#--------------------------------

import argparse
import datetime as dt
import logging
import os
import re
import sys

import numpy as np
import pandas as pd

def main(workspace, start_date = None, end_date = None, 
         input_ws = None, input_name_format = None, 
         output_ws = None, output_name_format = None,
         niwr_flag = False,  kc_flag = False, 
         crop_name_flag = False):
    """Split full daily data by crop

    Args:
        workspace (str): mother workspace
        start_date (str): ISO format date string (YYYY-MM-DD)
        end_date (str): ISO format date string (YYYY-MM-DD)
        input_ws (str): Input data workspace (location of of vb.net horizontal format files)
        input_name_format (str): file name format of vb.net horizontal format files
        output_ws (str): Output data workspace (location to post DRI format files)
        output_name_format (str): file name format of DIR format files
        niwr_flag (bool): If True, compute daily NIWR
        kc_flag (bool): If True, compute daily Kc
        crop_name_flag (bool): If True, include crop name as first line in file

    Returns:
        None
    """
    
    # set up data folders
    
    if not workspace: workspace = os.getcwd()
    if not input_ws: 
        input_ws = 'pmdata' + os.sep + 'ET'
    # print "input_ws", input_ws
    if not output_ws: 
        output_ws = 'pmdata' + os.sep + 'ET'
    # print "output_ws", output_ws
    
    # file name formats
    
    if not input_name_format:
        input_name_format = '%sETc.dat'
    swl = input_name_format.index('%s') + 2
    input_suffix = input_name_format[(swl):len(input_name_format)]
    if not output_name_format:
        output_name_format = '%s_daily_crop_%c.csv'
    if '%s' not in output_name_format or '%c' not in output_name_format:
        logging.error("output crop et file name format requires '%s' and '%c' wildcards.")
        sys.exit()

    # These crops will not be processed (if set)

    crop_skip_list = []

    # Only these crops will be processed (if set)

    crop_keep_list = []

    # Field names

    year_field = 'Year'
    doy_field = 'DoY'
    month_field = 'Mo'
    day_field = 'Dy'
    pmeto_field = 'PMETo'
    precip_field = 'Prmm'
    t30_field = 'T30'
    etact_field = 'ETact'
    etpot_field = 'ETpot'
    etbas_field = 'ETbas'
    irrig_field = 'Irrn'
    season_field = 'Seasn'
    runoff_field = 'Runof'
    dperc_field = 'DPerc'

    # Number of header lines in data file
    
    header_lines = 5
    logging.info('\nMother workspace: {0}'.format(workspace))

    # Input folder
    
    input_folder = os.path.join(workspace, input_ws)
    logging.info('  Input ET Folder: {0}'.format(input_folder))

    # Output folder
    
    output_folder = os.path.join(workspace, output_ws)
    logging.info('  Output ET Folder: {0}'.format(output_folder))

    # Check workspaces
    
    if not os.path.isdir(input_folder):
        logging.error(
            '\nERROR: Input ET folder {0} could be found\n'.format(input_folder))
        sys.exit()
    if not os.path.isdir(output_folder):
        os.mkdir(output_folder)

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
    if year_start and year_end and year_end < year_start:
        logging.error('\n  ERROR: End date must be after start date\n')
        sys.exit()

    # Build crop name and index dictionaries as files are processed

    crop_name_dict = dict()
    crop_index_dict = dict()

    # make used file list using name_format attributes
    
    data_file_list = []
    for item in os.listdir(input_folder):
        if input_suffix in item:
            if not item in data_file_list:
                data_file_list.append(os.path.join(input_folder, item))
    if len(data_file_list) < 1:
        logging.info('No files found')
        sys.exit()
    data_file_list = sorted(data_file_list)

    # Process each file

    for file_path in data_file_list:
        file_name = os.path.basename(file_path)
        logging.debug('')
        logging.info('Processing {0}'.format(file_name))
        station = file_name.split(input_suffix)[0]
        if station == 'temp': continue
        print station
        logging.debug('    Station:         {0}'.format(station))

        # Read file header

        with open(file_path, 'r') as f:
            header_list = f.readlines()[:header_lines]
        f.close()

        # Parse crop list (split on Crop:, remove white space)
        # Split on "Crop:" but skip first item (number of crops)
        # Remove white space and empty strings

        f_crop_list = header_list[header_lines - 2]
        f_crop_list = [
            item.strip() for item in f_crop_list.split('Crop:')[1:]]
        f_crop_list = [item for item in f_crop_list if item]
        num_crops = len(f_crop_list)
        logging.debug('    Number of Crops: {0}'.format(num_crops))

        # These could be used to clean up crop names
        f_crop_list = [item.replace('--', '-') for item in f_crop_list]
        # f_crop_list = [re.split('\(+', item)[0].strip()
        #               for item in f_crop_list]
        f_crop_list = [re.split('(-|\()+', item)[0].strip()
                       for item in f_crop_list]

        # Convert crop number to int for sorting
        # Don't sort crop_list, it is identical to crop order in file
        f_crop_list = [
            (int(item.split(' ', 1)[0]), item.split(' ', 1)[-1])
            for item in f_crop_list]
        logging.debug('\nCrops: \n{0}'.format(f_crop_list))

        # Read data from file into record array (structured array)

        try:
            data = np.genfromtxt(
                file_path, skip_header=(header_lines - 1), names=True)
        except ValueError:
            data = np.genfromtxt(
                file_path, skip_header=(header_lines - 1), names=True,
                delimiter=',')
        logging.debug('\nFields: \n{0}'.format(data.dtype.names))

        # Build list of unique years

        year_sub_array = np.unique(data[year_field].astype(np.int))
        logging.debug('\nAll Years: \n{0}'.format(year_sub_array.tolist()))

        # Only keep years between year_start and year_end

        if year_start:
            year_sub_array = year_sub_array[(year_start <= year_sub_array)]
        if year_end:
            year_sub_array = year_sub_array[(year_sub_array <= year_end)]
        logging.debug(
            '\nPlot Years: \n{0}'.format(year_sub_array.tolist()))
        date_mask = np.in1d(
            data[year_field].astype(np.int), year_sub_array)

        # Build separate arrays for each field of non-crop specific data

        doy_array = data[doy_field][date_mask].astype(np.int)
        year_array = data[year_field][date_mask].astype(np.int)
        month_array = data[month_field][date_mask].astype(np.int)
        day_array = data[day_field][date_mask].astype(np.int)
        pmeto_array = data[pmeto_field][date_mask]
        precip_array = data[precip_field][date_mask]
        t30_array = data[t30_field][date_mask]
        dt_array = np.array([
            dt.datetime(int(year), int(month), int(day))
            for year, month, day in zip(year_array, month_array, day_array)])

        # Process each crop
        # f_crop_i is based on order of crops in file
        # crop_i is based on a sorted index of user crop_list

        for f_crop_i, (crop_num, crop_name) in enumerate(f_crop_list):
            logging.debug('  Crop: {0} ({1})'.format(crop_name, crop_num))
            if crop_num in crop_skip_list:
                logging.debug('    Skipping, crop number not in crop_skip_list')
                continue
            if crop_keep_list and crop_num not in crop_keep_list:
                logging.debug('    Skipping, crop number not in crop_keep_list')
                continue
            if crop_num not in crop_name_dict.keys():
                crop_name_dict[crop_num] = crop_name
            if crop_num not in crop_index_dict.keys():
                if crop_index_dict.keys():
                    crop_i = max(crop_index_dict.values()) + 1
                else:
                    crop_i = 0
                crop_index_dict[crop_num] = crop_i
            else:
                crop_i = crop_index_dict[crop_num]

            # Field names are built based on crop i value
            
            if f_crop_i == 0:
                etact_sub_field = etact_field
                etpot_sub_field = etpot_field
                etbas_sub_field = etbas_field
                irrig_sub_field = irrig_field
                season_sub_field = season_field
                runoff_sub_field = runoff_field
                dperc_sub_field = dperc_field
            else:
                etact_sub_field = '{0}_{1}'.format(etact_field, f_crop_i)
                etpot_sub_field = '{0}_{1}'.format(etpot_field, f_crop_i)
                etbas_sub_field = '{0}_{1}'.format(etbas_field, f_crop_i)
                irrig_sub_field = '{0}_{1}'.format(irrig_field, f_crop_i)
                season_sub_field = '{0}_{1}'.format(season_field, f_crop_i)
                runoff_sub_field = '{0}_{1}'.format(runoff_field, f_crop_i)
                dperc_sub_field = '{0}_{1}'.format(dperc_field, f_crop_i)

            # Remove leap days
            # etact_sub_array = np.delete(etact_array, np.where(leap_array)[0])
            # niwr_sub_array = np.delete(niwr_array, np.where(leap_array)[0])

            # Timeseries figures of daily data
            
            """
            output_name = '{0}_daily_crop_{1:02d}.csv'.format(
                station, int(crop_num))
            data.cet_out['name_format'].replace('%c', '%02d' % int(crop.class_number)) % et_cell.cell_id)
            """
            output_name = output_name_format.replace('%c', '%02d' % int(crop_num)) % station
            output_path = os.path.join(output_folder, output_name)

            # Build an output data frame

            output_dict = {
                'Date': dt_array, 'DOY': doy_array,
                # 'T30':t30_array,
                'PMETo': pmeto_array,
                'ETact': data[etact_sub_field][date_mask],
                'ETpot': data[etpot_sub_field][date_mask],
                'ETbas': data[etbas_sub_field][date_mask],
                'PPT': precip_array,
                'Irrigation': data[irrig_sub_field][date_mask],
                'Runoff': data[runoff_sub_field][date_mask],
                'DPerc': data[dperc_sub_field][date_mask],
                'Season': data[season_sub_field][date_mask].astype(np.int)}
            output_df = pd.DataFrame(output_dict)
            output_df.set_index('Date', inplace=True)

            # NIWR is ET - precip + runoff + deep percolation

            output_df['NIWR'] = output_df['ETact'] - (precip_array - output_df['Runoff'])

            # Only include deep percolation when not irrigating

            irrig_mask = output_df['Irrigation'] == 0
            output_df.loc[irrig_mask, 'NIWR'] += output_df.loc[irrig_mask, 'DPerc']
            del irrig_mask

            # Crop coefficients

            output_df['Kc'] = output_df['ETact'] / pmeto_array
            output_df['Kcb'] = output_df['ETbas'] / pmeto_array

            # Format output columns

            output_df['Year'] = output_df.index.year
            output_df['Month'] = output_df.index.month
            output_df['Day'] = output_df.index.day
            output_df['Year'] = output_df['Year'].map(lambda x: ' %4d' % x)
            output_df['Month'] = output_df['Month'].map(lambda x: ' %2d' % x)
            output_df['Day'] = output_df['Day'].map(lambda x: ' %2d' % x)
            output_df['DOY'] = output_df['DOY'].map(lambda x: ' %3d' % x)
            
            # This will convert negative "zeros" to positive
            
            output_df['NIWR'] = np.round(output_df['NIWR'], 6)
            output_df['Season'] = output_df['Season'].map(lambda x: ' %1d' % x)

            # Order output columns
            
            output_columns = [
                'Year', 'Month', 'Day', 'DOY',
                'PMETo', 'ETact', 'ETpot', 'ETbas',
                'Kc', 'Kcb', 'PPT', 'Irrigation', 'Runoff',
                'DPerc', 'NIWR', 'Season']
            if not kc_flag:
                output_columns.remove('Kc')
                output_columns.remove('Kcb')
            if not niwr_flag:
                output_columns.remove('NIWR')
            # output_df =  output_df[output_columns]

            # Write output dataframe to file
            
            with open(output_path, 'w') as output_f:
                if crop_name_flag:
                    output_f.write(
                        '# {0:2d} - {1}\n'.format(crop_num, crop_name))
                output_df.to_csv(
                    output_f, sep=',', columns=output_columns,
                    float_format='%10.6f', date_format='%Y-%m-%d')
            del output_df

        # Cleanup
        
        del file_path, f_crop_list, data
        del doy_array, year_array, month_array, day_array
        del pmeto_array, precip_array, t30_array
        del date_mask, dt_array

def valid_date(input_date):
    """Check that a date string is ISO format (YYYY-MM-DD)

    This function is used to check format of dates entered as command
      line arguments.
    DEADBEEF - It would probably make more sense to have this function
      parse date using dateutil parser (http://labix.org/python-dateutil)
      and return ISO format string

    Args:
        input_date: string
    Returns:
        string
    Raises:
        ArgParse ArgumentTypeError
    """
    try:
        input_dt = dt.datetime.strptime(input_date, "%Y-%m-%d")
        return input_date
    except ValueError:
        msg = "Not a valid date: '{0}'.".format(input_date)
        raise argparse.ArgumentTypeError(msg)

def parse_args():
    """"""
    parser = argparse.ArgumentParser(
        description = 'Split Crop Daily Timeseries',
        formatter_class = argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        '-ws', '--workspace', nargs = '?', default = None,
        help = 'Input ET Folder', metavar = 'workspace')
    parser.add_argument(
        '-iw', '--inputws', metavar = 'input_ws', 
        default = None, help = "Input data workspace")
    parser.add_argument(
        '--inf', default = None,
        help = "Input file name format")
    parser.add_argument(
        '-ow', '--outputws', metavar = 'output_ws', 
        default = None, help = "Output data workspace")
    parser.add_argument(
        '--onf', default = None,
        help = "Output file name format")
    parser.add_argument(
        '--start', default = None, type = valid_date,
        help = 'Start date (format YYYY-MM-DD)', metavar = 'DATE')
    parser.add_argument(
        '--end', default = None, type = valid_date,
        help='End date (format YYYY-MM-DD)', metavar = 'DATE')
    parser.add_argument(
        '--niwr', action = "store_true", default = False,
        help = "Compute/output net irrigation water requirement (NIWR)")
    parser.add_argument(
        '--kc', action = "store_true", default = False,
        help = "Compute/output crop coefficient (Kc)")
    parser.add_argument(
        '--crop_name', action = "store_true", default = False,
        help = "Write crop name as first line in file")
    parser.add_argument(
        '--debug', default=logging.INFO, const = logging.DEBUG,
        help = 'Debug level logging', action = "store_const", dest = "loglevel")
    args = parser.parse_args()

    # Convert workspace to an absolute path if necessary

    if args.workspace and os.path.isdir(os.path.abspath(args.workspace)):
        args.workspace = os.path.abspath(args.workspace)
    return args

if __name__ == '__main__':
    args = parse_args()
    print args

    logging.basicConfig(level = logging.INFO, format='%(message)s')
    logging.info('\n{0}'.format('#' * 80))
    log_f = '{0:<20s} {1}'
    logging.info(log_f.format(
        'Run Time Stamp:', dt.datetime.now().isoformat(' ')))
    logging.info(log_f.format('Current Directory:', args.workspace))
    logging.info(log_f.format('Script:', os.path.basename(sys.argv[0])))

    main(workspace = args.workspace, 
         input_ws = args.inputws, input_name_format = args.inf,
         output_ws = args.outputws, output_name_format = args.onf,
         start_date = args.start, end_date = args.end,
         niwr_flag = args.niwr, kc_flag = args.kc, 
         crop_name_flag = args.crop_name)
