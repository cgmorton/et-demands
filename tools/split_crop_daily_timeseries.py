#--------------------------------
# Name:         split_crop_daily_timeseries.py
# Purpose:      Split daily data timeseries into separate files for each crop
# Author:       Charles Morton
# Created       2015-07-23
# Python:       2.7
#--------------------------------

import argparse
import calendar
import datetime as dt
import logging
import math
import os
import re
import shutil
import sys

import numpy as np
import pandas as pd

################################################################################

def main(workspace, niwr_flag=False, overwrite_flag=True):
    """Split full daily data by crop

    Args:
        pmdata_ws (str):
        niwr_flag (bool): If True, compute daily NIWR
        overwrite_flag (bool): If True, overwrite existing files
        
    Returns:
        None
    """

    try:
        ## Input names
        pmdata_folder = 'pmdata'
        et_folder = 'ETc'

        ## Output names
        output_folder  = 'cet'

        ## These crops will not be processed (if set)
        crop_skip_list = []
        ## Only these crops will be processed (if set)
        crop_keep_list = []

        ## Range of data to plot
        year_start = 1950
        year_end   = 1999

        ## Field names
        year_field   = 'Year'
        doy_field    = 'DoY'
        month_field  = 'Mo'
        day_field    = 'Dy'
        pmeto_field  = 'PMETo'
        precip_field = 'Prmm'
        t30_field    = 'T30'

        etact_field  = 'ETact'
        etpot_field  = 'ETpot'
        etbas_field  = 'ETbas'
        irrig_field  = 'Irrn'
        season_field = 'Seasn'
        runoff_field = 'Runof'
        dperc_field = 'DPerc'

        ## Number of header lines in data file
        header_lines = 5
        delimiter = '\t'
        ##delimiter = ','

        ########################################################################

        logging.info('\nPlot mean daily data by crop')
        logging.info('  Workspace: {0}'.format(workspace))

        ## Input workspaces
        et_ws = os.path.join(workspace, pmdata_folder, et_folder)
        logging.debug('  ET Folder: {0}'.format(et_ws))

        ## Output workspaces
        output_ws = os.path.join(workspace, output_folder)
        logging.debug('  Output Folder: {0}'.format(output_ws))

        ## Check workspaces
        if not os.path.isdir(et_ws):
            logging.error(
                '\nERROR: The ET folder {0} could be found\n'.format(et_ws))
            raise SystemExit()
        if not os.path.isdir(output_ws):
            os.mkdir(output_ws)
   
        logging.info('\n  Start Year:  {0}'.format(year_start))
        logging.info('  End Year:    {0}'.format(year_end))

        ## Regular expressions
        def list_re_or(input_list):
            return '('+'|'.join(map(str,input_list))+')'
        data_re = re.compile('(?P<CELLID>\w+)ETc.dat$', re.I)

        ## Build crop name and index dictionaries as the files are processed
        crop_name_dict = dict()
        crop_index_dict = dict()

        ## Build list of all data files
        data_file_list = sorted(
            [os.path.join(et_ws, f_name) for f_name in os.listdir(et_ws)
             if data_re.match(f_name)])
        if not data_file_list:
            logging.error(
                '  ERROR: No daily ET files were found\n'+
                '  ERROR: Check the folder_name parameters\n')
            raise SystemExit()

        ## Build list of stations
        station_list = sorted(list(set([
            os.path.basename(f_path).split('ETc')[0]
            for f_path in data_file_list])))

        ## Process each file
        for file_path in data_file_list:
            file_name = os.path.basename(file_path)
            logging.debug('')
            logging.info('  {0}'.format(file_name))

            station = file_name.split('ETc')[0]
            logging.debug('    Station:         {0}'.format(station))
            if station == 'temp':
                logging.debug('      Skipping')
                continue

            ## Read in file header
            with open(file_path, 'r') as f:
                header_list = f.readlines()[:header_lines]
            f.close()

            ## Parse crop list (split on Crop:, remove white space)
            ## Split on "Crop:" but skip first item (number of crops)
            ## Remove white space and empty strings
            f_crop_list = header_list[header_lines - 2]
            f_crop_list = [item.strip() for item in f_crop_list.split('Crop:')[1:]]
            f_crop_list = [item for item in f_crop_list if item]
            num_crops = len(f_crop_list)
            logging.debug('    Number of Crops: {0}'.format(num_crops))

            ## These could be used to clean up crop names
            f_crop_list = [item.replace('--', '-') for item in f_crop_list]
            ##f_crop_list = [re.split('\(+', item)[0].strip()
            ##               for item in f_crop_list]
            f_crop_list = [re.split('(-|\()+', item)[0].strip()
                           for item in f_crop_list]

            ## Convert crop number to int for sorting
            ## Don't sort crop_list, it is identical to crop order in file
            f_crop_list = [
                (int(item.split(' ', 1)[0]), item.split(' ', 1)[-1])
                 for item in f_crop_list]
            logging.debug('\nCrops: \n{0}'.format(f_crop_list))
            
            ## Read data from file into record array (structured array)
            try:
                data = np.genfromtxt(
                    file_path, skip_header=(header_lines-1), names=True)
            except ValueError:
                data = np.genfromtxt(
                    file_path, skip_header=(header_lines-1), names=True,
                    delimiter=',')
            logging.debug('\nFields: \n{0}'.format(data.dtype.names))

            ## Build list of unique years
            year_sub_array = np.unique(data[year_field].astype(np.int))
            logging.debug('\nAll Years: \n{0}'.format(year_sub_array.tolist()))
            ## Only keep years between year_start and year_end
            year_sub_array = year_sub_array[
                (year_start <= year_sub_array) & (year_sub_array <= year_end)]
            logging.debug('\nPlot Years: \n{0}'.format(year_sub_array.tolist()))
            date_mask = np.in1d(data[year_field].astype(np.int), year_sub_array)

            ## Check year start and year end
            if year_start not in year_sub_array:
                logging.error('\n  ERROR: Start Year is invalid\n')
                raise SystemExit()
            if year_end not in year_sub_array:
                logging.error('\n  ERROR: End Year is invalid\n')
                raise SystemExit()
            if year_end <= year_start:
                logging.error('\n  ERROR: End Year must be >= Start Year\n')
                raise SystemExit()

            ## Build separate arrays for each field of non-crop specific data
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

            ## Remove leap days
            leap_array = (doy_array == 366)
            doy_sub_array = np.delete(doy_array, np.where(leap_array)[0])

            ## Process each crop
            ## f_crop_i is based on order of crops in the file
            ## crop_i is based on a sorted index of the user crop_list
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
                        crop_i = max(crop_index_dict.values())+1
                    else:
                        crop_i = 0
                    crop_index_dict[crop_num] = crop_i
                else:
                    crop_i = crop_index_dict[crop_num]
                
                ## Field names are built based on the crop i value
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

                ## Build separate arrays for each set of crop specific fields
                etact_array = data[etact_sub_field][date_mask]
                etpot_array = data[etpot_sub_field][date_mask]
                etbas_array = data[etbas_sub_field][date_mask]
                irrig_array = data[irrig_sub_field][date_mask]
                season_array = data[season_sub_field][date_mask]
                runoff_array = data[runoff_sub_field][date_mask]
                dperc_array = data[dperc_sub_field][date_mask]
                kc_array = etact_array / pmeto_array
                kcb_array = etbas_array / pmeto_array

                ## NIWR is ET - precip + runoff + deep percolation
                ## Don't include deep percolation when irrigating
                niwr_array = etact_array - (precip_array - runoff_array)
                niwr_array[irrig_array==0] += dperc_array[irrig_array == 0]

                ## Remove leap days
                ##etact_sub_array = np.delete(etact_array, np.where(leap_array)[0])
                ##niwr_sub_array = np.delete(niwr_array, np.where(leap_array)[0])

                ## Timeseries figures of daily data
                output_name = '{0}_{1}.dat'.format(
                    station, crop_num)
                output_path = os.path.join(output_ws, output_name)

                ##
                with open(output_path, 'w') as output_f:
                    fmt = '%10s %3s %9s %9s %9s %9s %9s %9s %9s %5s %9s %9s\n' 
                    header = ('#     Date', 'DOY', 'PMETo', 'Pr.mm', 'T30', 'ETact',
                              'ETpot', 'ETbas', 'Irrn', 'Seasn', 'Runof', 'DPerc')
                    if niwr_flag:
                        header = header + ('NIWR',)
                        fmt = fmt.replace('\n', ' %9s\n')
                    output_f.write(fmt % header)
                    for i in range(dt_array.size):
                        fmt = ('%10s %3s %9.3f %9.3f %9.3f %9.3f '+
                               '%9.3f %9.3f %9.3f %5d %9.3f %9.3f\n')
                        values = (dt_array[i].date().isoformat(), int(doy_array[i]),
                                  float(pmeto_array[i]), float(precip_array[i]),
                                  float(t30_array[i]), float(etact_array[i]),
                                  float(etpot_array[i]), float(etbas_array[i]),
                                  float(irrig_array[i]), float(season_array[i]),
                                  float(runoff_array[i]), float(dperc_array[i]))
                        if niwr_flag:
                            values = values + (float(niwr_array[i]),)
                            fmt = fmt.replace('\n', ' %9.3f\n')
                        output_f.write(fmt % values)

                ## Cleanup
                del etact_array, etact_sub_field
                del etpot_array, etpot_sub_field
                del etbas_array, etbas_sub_field
                del irrig_array, irrig_sub_field
                del season_array, season_sub_field
                del runoff_array, runoff_sub_field
                del dperc_array, dperc_sub_field
                del kc_array, kcb_array
                del niwr_array
                ##del etact_sub_array, niwr_sub_array
                ##break

            ## Cleanup
            del file_path, f_crop_list, data
            del doy_array, year_array, month_array, day_array
            del pmeto_array
            del precip_array
            ##del date_array
            ##del dt_array
            del date_mask
            ##break

    except:
        logging.exception('Unhandled Exception Error\n\n')
            
    finally:
        ##pass
        raw_input('\nPress ENTER to close')

################################################################################

def parse_args():
    parser = argparse.ArgumentParser(
        description='Split Crop Daily Timeseries',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        'workspace', nargs='?', default=os.getcwd(),
        help='PMData Folder', metavar='FOLDER')
    parser.add_argument(
        '--niwr', action="store_true", default=False,
        help="Compute/output net irrigation water requirement (NIWR)")
    parser.add_argument(
        '-o', '--overwrite', default=None, action="store_true", 
        help='Force overwrite of existing files')
    parser.add_argument(
        '--debug', default=logging.INFO, const=logging.DEBUG,
        help='Debug level logging', action="store_const", dest="loglevel")
    args = parser.parse_args()
    return args

################################################################################

if __name__ == '__main__':
    args = parse_args()
    
    ## Create Basic Logger
    logging.basicConfig(level=args.loglevel, format='%(message)s')

    ## Run Information    
    logging.info('\n{0}'.format('#'*80))
    log_f = '{0:<20s} {1}'
    logging.info(log_f.format('Run Time Stamp:', dt.datetime.now().isoformat(' ')))
    logging.info(log_f.format('Current Directory:', args.workspace))
    logging.info(log_f.format('Script:', os.path.basename(sys.argv[0])))

    main(workspace=args.workspace, niwr_flag=args.niwr,
         overwrite_flag=args.overwrite)
