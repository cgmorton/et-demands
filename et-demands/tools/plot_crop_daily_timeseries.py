#--------------------------------
# Name:         plot_crop_daily_timeseries.py
# Purpose:      Plot full daily data timeseries
# Author:       Charles Morton
# Created       2016-07-19
# Python:       2.7
#--------------------------------

import argparse
import datetime as dt
import gc
import logging
import os
import sys

from bokeh.plotting import figure, output_file, save, show
from bokeh.layouts import column
from bokeh.models import Range1d
import numpy as np
import pandas as pd

import util

def main(ini_path, figure_show_flag = False, figure_save_flag = True,
        figure_size = (1000, 300), start_date = None, end_date = None,
        crop_str = '', overwrite_flag = False):
    """Plot full daily data by crop

    Args:
        ini_path (str): file path ofproject INI file
        figure_show_flag (bool): if True, show figures
        figure_save_flag (bool): if True, save figures
        figure_size (tuple): width, height of figure in pixels
        start_date (str): ISO format date string (YYYY-MM-DD)
        end_date (str): ISO format date string (YYYY-MM-DD)
        crop_str (str): comma separate list or range of crops to compare
        overwrite_flag (bool): If True, overwrite existing files

    Returns:
        None
    """

    # Input/output names
    # input_folder = 'daily_stats'
    # output_folder = 'daily_plots'

    # Only process subset of crops
    
    crop_keep_list = list(util.parse_int_set(crop_str))
    # These crops will not be processed (if set)
    crop_skip_list = [44, 45, 46]

    # Input field names
    date_field = 'Date'
    doy_field = 'DOY'
    year_field = 'Year'
    # month_field = 'Month'
    # day_field = 'Day'
    pmeto_field = 'PMETo'
    precip_field = 'PPT'
    # t30_field = 'T30'

    etact_field = 'ETact'
    etpot_field = 'ETpot'
    etbas_field = 'ETbas'
    irrig_field = 'Irrigation'
    season_field = 'Season'
    runoff_field = 'Runoff'
    dperc_field = 'DPerc'
    # niwr_field = 'NIWR'

    # Number of header lines in data file
    # header_lines = 2

    # Additional figure controls
    # figure_dynamic_size = False

    figure_ylabel_size = '12pt'

    # Delimiter

    sep = ','
    # sep = r"\s*"

    sub_x_range_flag = True

    logging.info('\nPlot mean daily data by crop')
    logging.info('  INI: {}'.format(ini_path))

    # Check that INI file can be read

    crop_et_sec = 'CROP_ET'
    config = util.read_ini(ini_path, crop_et_sec)

    # Get to get project workspace and daily ET folder from INI file
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
    try:
        input_ws = os.path.join(
            project_ws, config.get(crop_et_sec, 'daily_output_folder'))
    except:
        logging.error(
            'ERROR:daily_output_folder ' +
            'parameter is not set inINI file')
        sys.exit()
    try:
        output_ws = os.path.join(
            project_ws, config.get(crop_et_sec, 'daily_plots_folder'))
    except:
        if 'stats' in input_ws:
            output_ws = input_ws.replace('stats', 'plots')
        else:
            output_ws = os.path.join(project_ws, 'daily_stats_folder')

    # Check workspaces
    
    if not os.path.isdir(input_ws):
        logging.error(('\nERROR:input ET folder {0} ' +
                       'could be found\n').format(input_ws))
        sys.exit()
    if not os.path.isdir(output_ws):
        os.mkdir(output_ws)
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

    # Range of data to plot

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

    # # Windows only a
    # if figure_dynamic_size:
    #     :
    #        logging.info('Setting plots width/height dynamically')
    #        from win32api import GetSystemMetrics
    #        figure_width = int(0.92 * GetSystemMetrics(0))
    #        figure_height = int(0.28 * GetSystemMetrics(1))
    #        logging.info('  {0} {1}'.format(GetSystemMetrics(0), GetSystemMetrics(1)))
    #        logging.info('  {0} {1}'.format(figure_width, figure_height))
    #     :
    #        figure_width = 1200
    #        figure_height = 300

    # make used file list using name_format attributes
    
    data_file_list = []
    for item in os.listdir(input_ws):
        if prefix in item and suffix in item:
            if not item in data_file_list:
                data_file_list.append(os.path.join(input_ws, item))
    if len(data_file_list) < 1:
        logging.info('No files found')
        sys.exit()
    data_file_list = sorted(data_file_list)

    # Process each file

    for file_count, file_path in enumerate(data_file_list):
        file_name = os.path.basename(file_path)
        logging.debug('')
        logging.info('  Processing {0}'.format(file_name))
        station, crop_num = os.path.splitext(file_name)[0].split(prefix)
        crop_num = int(crop_num[:crop_num.index(suf_no_ext)])
        logging.debug('    Station:         {0}'.format(station))
        logging.debug('    Crop Num:        {0}'.format(crop_num))
        if station == 'temp':
            logging.debug('      Skipping')
            continue
        elif crop_skip_list and crop_num in crop_skip_list:
            logging.debug('    Skipping, crop number in crop_skip_list')
            continue
        elif crop_keep_list and crop_num not in crop_keep_list:
            logging.debug('    Skipping, crop number not in crop_keep_list')
            continue

        # Get crop name
        
        with open(file_path, 'r') as file_f:
            crop_name = file_f.readline().split('-', 1)[1].strip()
            logging.debug('    Crop:            {0}'.format(crop_name))

        # Read data from file into record array (structured array)
        
        daily_df = pd.read_table(file_path, header = 0, comment = '#', sep = sep)
        logging.debug('    Fields: {0}'.format(
            ', '.join(daily_df.columns.values)))
        daily_df[date_field] = pd.to_datetime(daily_df[date_field])
        
        # workaround for data before 1970 on a pc

        if not year_start or year_start < 1970:

            # test if a pc
        
            if os.getenv('OS') is not None and os.getenv('OS') == 'Windows_NT':
                # check if data exist before 1970
        
                data_sy = daily_df[date_field][0].year
                if data_sy < 1970:
                    # add multiple of 4 years to actual dates
                
                    years_to_add = 1970 - data_sy + ((1970 - data_sy) % 4)
                    daily_df[date_field] = daily_df[date_field] + pd.Timedelta(days = int(years_to_add * 365.25))
                    if file_count == 0: 
                        logging.info('  Added {0} years to input dates'.format(years_to_add))
                    if year_start and file_count == 0:
                        year_start += years_to_add
                    if year_end and file_count == 0:
                        year_end += years_to_add
                    del years_to_add
                del data_sy
        daily_df.set_index(date_field, inplace = True)
        daily_df[year_field] = daily_df.index.year

        # Build list of unique years
        
        year_array = np.sort(np.unique(
            np.array(daily_df[year_field]).astype(np.int)))
        logging.debug('    All Years: {0}'.format(
            ', '.join(list(util.ranges(year_array.tolist())))))

        # Don't include first year in plots
        
        crop_year_start = min(daily_df[year_field])
        logging.debug('    Skipping {}, first year'.format(crop_year_start))
        daily_df = daily_df[daily_df[year_field] > crop_year_start]

        # Check if start and end years have >= 365 days
        
        crop_year_start = min(daily_df[year_field])
        crop_year_end = max(daily_df[year_field])
        if sum(daily_df[year_field] == crop_year_start) < 365:
            logging.debug(
                '    Skipping {}, missing days'.format(crop_year_start))
            daily_df = daily_df[daily_df[year_field] > crop_year_start]
        if sum(daily_df[year_field] == crop_year_end) < 365:
            logging.debug(
                '    Skipping {}, missing days'.format(crop_year_end))
            daily_df = daily_df[daily_df[year_field] < crop_year_end]

        # Only keep years between year_start and year_end
        # Adjust crop years
        
        if year_start:
            daily_df = daily_df[daily_df[year_field] >= year_start]
            crop_year_start = max(year_start, crop_year_start)
        if year_end:
            daily_df = daily_df[daily_df[year_field] <= year_end]
            crop_year_end = min(year_end, crop_year_end)

        year_sub_array = np.sort(
            np.unique(np.array(daily_df[year_field]).astype(np.int)))
        logging.debug('    Plot Years: {0}'.format(
            ', '.join(list(util.ranges(year_sub_array.tolist())))))

        # Initial range of time series to show
        # For now default to last ~8 year
        
        if sub_x_range_flag:
            x_range = Range1d(
                np.datetime64(dt.datetime(
                    max(crop_year_end - 9, crop_year_start), 1, 1), 's'),
                np.datetime64(dt.datetime(crop_year_end + 1, 1, 1), 's'),
                bounds = (
                    np.datetime64(dt.datetime(crop_year_start, 1, 1), 's'),
                    np.datetime64(dt.datetime(crop_year_end + 1, 1, 1), 's')))
        else:
            x_range = Range1d(
                np.datetime64(dt.datetime(crop_year_start, 1, 1), 's'),
                np.datetime64(dt.datetime(crop_year_end + 1, 1, 1), 's'))

        # Build separate arrays for each field of non-crop specific data

        dt_array = daily_df.index.date
        doy_array = daily_df[doy_field].values.astype(np.int)
        pmeto_array = daily_df[pmeto_field].values
        precip_array = daily_df[precip_field].values

        # Remove leap days
        # leap_array = (doy_array == 366)
        # doy_sub_array = np.delete(doy_array, np.where(leap_array)[0])

        # Build separate arrays for each set of crop specific fields

        etact_array = daily_df[etact_field].values
        etpot_array = daily_df[etpot_field].values
        etbas_array = daily_df[etbas_field].values
        irrig_array = daily_df[irrig_field].values
        season_array = daily_df[season_field].values
        runoff_array = daily_df[runoff_field].values
        dperc_array = daily_df[dperc_field].values
        del daily_df
        kc_array = etact_array / pmeto_array
        kcb_array = etbas_array / pmeto_array

        # NIWR is ET - precip + runoff + deep percolation
        # Don't include deep percolation when irrigating
        # niwr_array = etact_array - (precip_array - runoff_array)
        # niwr_array[irrig_array==0] += dperc_array[irrig_array == 0]

        # Remove leap days
        # etact_sub_array = np.delete(etact_array, np.where(leap_array)[0])
        # niwr_sub_array = np.delete(niwr_array, np.where(leap_array)[0])

        # Time series figures of daily data

        output_name = '{0}_crop_{1:02d}_{2}-{3}'.format(
            station, int(crop_num), crop_year_start, crop_year_end)
        output_path = os.path.join(output_ws, output_name + '.html')
        if overwrite_flag and os.path.isfile(output_path):
            os.remove(output_path)
        f = output_file(output_path, title = output_name)
        TOOLS = 'xpan,xwheel_zoom,box_zoom,reset,save'
        f1 = figure(
            x_axis_type = 'datetime', x_range = x_range,
            width = figure_size[0], height = figure_size[1],
            tools = TOOLS, toolbar_location = "right",
            active_scroll = "xwheel_zoom")
        f1.line(dt_array, etact_array, color = 'blue', legend = 'ETact')
        f1.line(dt_array, etbas_array, color = 'green', legend = 'ETbas')
        f1.line(dt_array, pmeto_array, color = 'black', legend = 'ETos',
                line_dash = "dotted")
        f1.grid.grid_line_alpha = 0.3
        f1.yaxis.axis_label = 'Evapotranspiration [mm]'
        f1.yaxis.axis_label_text_font_size = figure_ylabel_size

        f2 = figure(
            x_axis_type = "datetime", x_range = f1.x_range,
            width = figure_size[0], height = figure_size[1],
            tools = TOOLS, toolbar_location = "right",
            active_scroll = "xwheel_zoom")
        f2.line(dt_array, kc_array, color = 'blue', legend = 'Kc')
        f2.line(dt_array, kcb_array, color = 'green', legend = 'Kcb')
        f2.line(dt_array, season_array, color = 'black', legend = 'Season',
                line_dash = "dashed")
        f2.grid.grid_line_alpha = 0.3
        f2.yaxis.axis_label = 'Kc and Kcb (dimensionless)'
        f2.yaxis.axis_label_text_font_size = figure_ylabel_size

        f3 = figure(
            x_axis_type = "datetime", x_range = f1.x_range,
            width = figure_size[0], height = figure_size[1],
            tools = TOOLS, toolbar_location = "right",
            active_scroll = "xwheel_zoom")
        f3.line(dt_array, precip_array, color = 'blue', legend = 'PPT')
        f3.line(dt_array, irrig_array, color = 'black', legend = 'Irrigation',
                line_dash = "dotted")
        f3.grid.grid_line_alpha = 0.3
        f3.yaxis.axis_label = 'PPT and Irrigation [mm]'
        f3.yaxis.axis_label_text_font_size = figure_ylabel_size

        if figure_save_flag:
            # save(column([f1, f2, f3], sizing_mode = 'stretch_both'))
            save(column([f1, f2, f3], sizing_mode = 'stretch_both'), validate = True)
        if figure_show_flag:
            # Open in browser
            show(column([f1, f2, f3], sizing_mode = 'stretch_both'))

        # Cleanup

        del f1, f2, f3, f
        del etact_array, etpot_array, etbas_array
        del irrig_array, season_array
        del runoff_array, dperc_array
        del kc_array, kcb_array
        del file_path
        del dt_array, year_array, year_sub_array, doy_array
        del pmeto_array
        del precip_array
        gc.collect()

def parse_args():
    """"""
    parser = argparse.ArgumentParser(
        description = 'Plot Crop Daily Timeseries',
        formatter_class = argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        '-i', '--ini', metavar = 'PATH',
        type = lambda x: util.is_valid_file(parser, x), help = 'Input file')
    parser.add_argument(
        '--size', default = (1000, 300), type = int,
        nargs = 2, metavar = ('WIDTH', 'HEIGHT'),
        help = 'Figure size in pixels')
    parser.add_argument(
        '--no_save', default = True, action = 'store_false',
        help = 'Don\'t save timeseries figures in browser')
    parser.add_argument(
        '--show', default = False, action = 'store_true',
        help = 'Show timeseries figures to disk')
    parser.add_argument(
        '--start', default = None, type = util.valid_date,
        help = 'Start date (format YYYY-MM-DD)', metavar = 'DATE')
    parser.add_argument(
        '--end', default = None, type = util.valid_date,
        help = 'End date (format YYYY-MM-DD)', metavar = 'DATE')
    parser.add_argument(
        '-c', '--crops', default = '', type = str,
        help = 'Comma separate list or range of crops to compare')
    parser.add_argument(
        '-o', '--overwrite', default = None, action = "store_true",
        help = 'Force overwrite of existing files')
    parser.add_argument(
        '--debug', default = logging.INFO, const = logging.DEBUG,
        help = 'Debug level logging', action = "store_const", dest = "loglevel")
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
        ini_path = util.get_path(os.getcwd(), 'Selecttarget INI file')
        
    # Try using current working directory if there is only one INI
    # Could look for daily_stats folder, run_basin.py, and/or ini file
    
    elif len([x for x in os.listdir(os.getcwd()) if x.lower().endswith('.ini')]) == 1:
        ini_path = [
            os.path.join(os.getcwd(), x) for x in os.listdir(os.getcwd())
            if x.lower().endswith('.ini')][0]
            
    # Eventually list available INI files and promp tuser to select one
    # For now though, use GUI
    
    else:
        ini_path = util.get_path(os.getcwd(), 'Selecttarget INI file')

    logging.basicConfig(level = args.loglevel, format = '%(message)s')
    logging.info('\n{0}'.format('#' * 80))
    logging.info('{0:<20s} {1}'.format(
        'Run Time Stamp:', dt.datetime.now().isoformat(' ')))
    logging.info('{0:<20s} {1}'.format('Current Directory:', os.getcwd()))
    logging.info('{0:<20s} {1}'.format('Script:', os.path.basename(sys.argv[0])))

    main(ini_path, figure_show_flag = args.show,
         figure_save_flag = args.no_save, figure_size = args.size,
         start_date = args.start, end_date = args.end, crop_str = args.crops,
         overwrite_flag = args.overwrite)
