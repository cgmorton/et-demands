#--------------------------------
# Name:         plot_crop_daily_timeseries.py
# Purpose:      Plot full daily data timeseries
# Author:       Charles Morton, modified by C. Pearson for groupstat output
# Created       2016-07-19, 2017-12-14
# Python:       2.7
#--------------------------------

import argparse
# import ConfigParser
import datetime as dt
import gc
import logging
import os
import re
import sys

from bokeh.models.formatters import DatetimeTickFormatter
from bokeh.plotting import figure, output_file, save, show
from bokeh.layouts import column
from bokeh.models import Range1d
import numpy as np
import pandas as pd

import util


def main(ini_path, figure_show_flag=False, figure_save_flag=True,
         figure_size=(1000, 300), start_date=None, end_date=None,
         crop_str=''):
    """Plot full daily data by crop

    Args:
        ini_path (str): file path of the project INI file
        figure_show_flag (bool): if True, show figures
        figure_save_flag (bool): if True, save figures
        figure_size (tuple): width, height of figure in pixels
        start_date (str): ISO format date string (YYYY-MM-DD)
        end_date (str): ISO format date string (YYYY-MM-DD)
        crop_str (str): comma separate list or range of crops to compare

    Returns:
        None
    """

    # Input/output names
    # input_folder = 'daily_stats'
    # output_folder = 'daily_plots'

    # Only process a subset of the crops
    crop_keep_list = list(util.parse_int_set(crop_str))
    # These crops will not be processed (if set)
    crop_skip_list = [44, 45, 46]

    # Input field names
    date_field = 'Date'
    doy_field = 'DOY'
    year_field = 'Year'
    # month_field = 'Month'
    # day_field = 'Day'
#    pmeto_field = 'PMETo'
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

#    sub_x_range_flag = True

    logging.info('\nPlot mean daily data by crop')
    logging.info('  INI: {}'.format(ini_path))

    # Check that the INI file can be read
    crop_et_sec = 'CROP_ET'
    config = util.read_ini(ini_path, crop_et_sec)

    # Get the project workspace and daily ET folder from the INI file
    try:
        project_ws = config.get(crop_et_sec, 'project_folder')
    except:
        logging.error(
            'ERROR: The project_folder ' +
            'parameter is not set in the INI file')
        sys.exit()
    try:
        input_ws = os.path.join(
            project_ws, config.get(crop_et_sec, 'daily_output_folder'))
    except:
        logging.error(
            'ERROR: The daily_output_folder ' +
            'parameter is not set in the INI file')
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
        logging.error(('\nERROR: The input ET folder {0} ' +
                       'could be found\n').format(input_ws))
        sys.exit()
    if not os.path.isdir(output_ws):
        os.mkdir(output_ws)

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

    # Regular expressions
    data_re = re.compile('(?P<CELLID>\w+)_crop_(?P<CROP>\d+).csv$', re.I)
    # data_re = re.compile('(?P<CELLID>\w+)_daily_crop_(?P<CROP>\d+).csv$', re.I)

    # Build list of all data files
    data_file_list = sorted(
        [os.path.join(input_ws, f_name) for f_name in os.listdir(input_ws)
         if data_re.match(f_name)])
    if not data_file_list:
        logging.error(
            '  ERROR: No daily ET files were found\n' +
            '  ERROR: Check the folder_name parameters\n')
        sys.exit()

    # Process each file
    for file_path in data_file_list:
        file_name = os.path.basename(file_path)
        logging.debug('')
        logging.info('  {0}'.format(file_name))

        # station, crop_num = os.path.splitext(file_name)[0].split('_daily_crop_')
        station, crop_num = os.path.splitext(file_name)[0].split('_crop_')
        crop_num = int(crop_num)
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
        daily_df = pd.read_table(file_path, header=0, comment='#', sep=sep)
        logging.debug('    Fields: {0}'.format(
            ', '.join(daily_df.columns.values)))
        daily_df[date_field] = pd.to_datetime(daily_df[date_field])
        daily_df.set_index(date_field, inplace=True)
        daily_df[year_field] = daily_df.index.year
        # daily_df[year_field] = daily_df[date_field].map(lambda x: x.year)

        #Get PMET type from fieldnames in daily .csv
        field_names=daily_df.columns
        PMET_str=field_names[4]
#        if 'PMETr' in field_names:
#            PMET_str='PMETr'
#        else:
#            PMET_str='PMETo'
        

        # Build list of unique years
        year_array = np.sort(np.unique(
            np.array(daily_df[year_field]).astype(np.int)))
        logging.debug('    All Years: {0}'.format(
            ', '.join(list(util.ranges(year_array.tolist())))))
        # logging.debug('    All Years: {0}'.format(
        #    ','.join(map(str, year_array.tolist()))))

        # Don't include the first year in the stats
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
        # logging.debug('    Plot Years: {0}'.format(
        #    ','.join(map(str, year_sub_array.tolist()))))

        # Initial range of timeseries to show
        # For now default to last ~8 year
#        if sub_x_range_flag:
#            x_range = Range1d(
#                np.datetime64(dt.datetime(
#                    max(crop_year_end - 9, crop_year_start), 1, 1), 's'),
#                np.datetime64(dt.datetime(crop_year_end + 1, 1, 1), 's'),
#                bounds=(
#                    np.datetime64(dt.datetime(crop_year_start, 1, 1), 's'),
#                    np.datetime64(dt.datetime(crop_year_end + 1, 1, 1), 's')))
#        else:
#            x_range = Range1d(
#                np.datetime64(dt.datetime(crop_year_start, 1, 1), 's'),
#                np.datetime64(dt.datetime(crop_year_end + 1, 1, 1), 's'))

        # Build separate arrays for each field of non-crop specific data
        dt_array = daily_df.index.date
        doy_array = daily_df[doy_field].values.astype(np.int)
        pmet_array = daily_df[PMET_str].values
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
        kc_array = etact_array / pmet_array
        kcb_array = etbas_array / pmet_array
        
        #build dataframes for grouby input        
        doy_df=pd.DataFrame(doy_array)
        pmet_df=pd.DataFrame(pmet_array.transpose())        
        etact_df=pd.DataFrame(etact_array.transpose())
#        etpot_df=pd.DataFrame(etpot_array.transpose())
#        etbas_df=pd.DataFrame(etbas_array.transpose())
#        irrig_df=pd.DataFrame(irrig_array.transpose())
        season_df=pd.DataFrame(season_array.transpose())
#        runoff_df=pd.DataFrame(runoff_array.transpose())
#        dperc_df=pd.DataFrame(dperc_array.transpose())
        kc_df=pd.DataFrame(kc_array.transpose())
        kcb_df=pd.DataFrame(kcb_array.transpose())
        
   
        # groupby stats
#        doy_mean= doy_df[0].groupby(doy_df[0]).mean().as_matrix()
        season_median= season_df[0].groupby(doy_df[0]).median().as_matrix()
        kc_median=kc_df[0].groupby(doy_df[0]).median().as_matrix()
        kcb_median=kcb_df[0].groupby(doy_df[0]).median().as_matrix()
#        etbas_median=etbas_df[0].groupby(doy_df[0]).median().as_matrix()
        pmet_median=pmet_df[0].groupby(doy_df[0]).median().as_matrix()
#        etpot_median=etpot_df[0].groupby(doy_df[0]).median().as_matrix()
        etact_median=etact_df[0].groupby(doy_df[0]).median().as_matrix()
        # 25% and 75% Percentiles of all years
        kc_q25=kc_df[0].groupby(doy_df[0]).quantile(0.25).as_matrix()
        kcb_q25=kcb_df[0].groupby(doy_df[0]).quantile(0.25).as_matrix()
#        etbas_q25=etbas_df[0].groupby(doy_df[0]).quantile(0.25).as_matrix()
#        pmet_q25=pmet_df[0].groupby(doy_df[0]).quantile(0.25).as_matrix()
#        etpot_q25=etpot_df[0].groupby(doy_df[0]).quantile(0.25).as_matrix()
        etact_q25=etact_df[0].groupby(doy_df[0]).quantile(0.25).as_matrix()
        kc_q75=kc_df[0].groupby(doy_df[0]).quantile(0.75).as_matrix()
        kcb_q75=kcb_df[0].groupby(doy_df[0]).quantile(0.75).as_matrix()
#        etbas_q75=etbas_df[0].groupby(doy_df[0]).quantile(0.75).as_matrix()
#        etpot_q75=etpot_df[0].groupby(doy_df[0]).quantile(0.75).as_matrix()
        etact_q75=etact_df[0].groupby(doy_df[0]).quantile(0.75).as_matrix()
#        pmet_q75=pmet_df[0].groupby(doy_df[0]).quantile(0.75).as_matrix()
        
        
        

        # NIWR is ET - precip + runoff + deep percolation
        # Don't include deep percolation when irrigating
        # niwr_array = etact_array - (precip_array - runoff_array)
        # niwr_array[irrig_array==0] += dperc_array[irrig_array == 0]

        # Remove leap days
        # etact_sub_array = np.delete(etact_array, np.where(leap_array)[0])
        # niwr_sub_array = np.delete(niwr_array, np.where(leap_array)[0])
        
        #Manually create date range array for display of month/day on x-axis
        x_range = Range1d(dt.datetime(2000,1,1), dt.datetime(2000,12,31))
        np_x_range= np.arange(dt.datetime(2000,1,1), dt.datetime(2001,1,1), dt.timedelta(days=1)).astype(dt.datetime)

        # Timeseries figures of daily data
        output_name = '{0}_crop_{1:02d}_avg'.format(
            station, int(crop_num), crop_year_start, crop_year_end)
        output_path = os.path.join(output_ws, output_name + '.html')

        f = output_file(output_path, title=output_name)
        TOOLS = 'xpan,xwheel_zoom,box_zoom,reset,save'

        f1 = figure(x_axis_type='datetime',x_range=x_range,
            width=figure_size[0], height=figure_size[1],
            tools=TOOLS, toolbar_location="right",
            active_scroll="xwheel_zoom")
            # title='Evapotranspiration', x_axis_type='datetime',
#        if refet_type == 'ETo':    
        f1.line(np_x_range, etact_median, color='blue', legend='ETact Median')
        f1.line(np_x_range, etact_q75, color='red', legend='ETact 75th percentile')
        f1.line(np_x_range, etact_q25, color='green', legend='ETact 25th percentile')
        f1.line(np_x_range, pmet_median, color='black', legend=PMET_str+' Median', line_dash="dashed")
#        else:
#            f1.line(np_x_range, et_median, color='blue', legend='ETr Median')
#            f1.line(np_x_range, etbas_q75, color='red', legend='ETr 75th percentile')
#            f1.line(np_x_range, etpot_q25, color='green', legend='ETr 25th percentile')
#                # line_dash="dashdot")
        # f1.title = 'Evapotranspiration [mm]'
        f1.grid.grid_line_alpha = 0.3
        f1.yaxis.axis_label = 'Evapotranspiration [mm]'
        f1.yaxis.axis_label_text_font_size = figure_ylabel_size
        f1.xaxis.formatter=DatetimeTickFormatter(years=['%m/%d'], months=['%m/%d'], days=['%m/%d'])
        # f1.xaxis.bounds = x_bounds
        

        f2 = figure(x_axis_type='datetime',x_range=x_range,
            width=figure_size[0], height=figure_size[1],
            tools=TOOLS, toolbar_location="right",
            active_scroll="xwheel_zoom")
        f2.line(np_x_range, kc_median, color='blue', legend='Kc Median')
        f2.line(np_x_range, kc_q75, color='red', legend='Kc 75th percentile')
        f2.line(np_x_range, kc_q25, color='green', legend='Kc 25th percentile')
        f2.line(np_x_range, season_median, color='black', legend='Season Median',
                line_dash="dashed")
#         f2.title = 'Kc and Kcb (dimensionless)'
        f2.grid.grid_line_alpha = 0.3
        f2.yaxis.axis_label = 'Kc (dimensionless)'
        f2.yaxis.axis_label_text_font_size = figure_ylabel_size
        f2.xaxis.formatter=DatetimeTickFormatter(years=['%m/%d'], months=['%m/%d'], days=['%m/%d'])

        f3 = figure(x_axis_type='datetime',x_range=x_range,
            width=figure_size[0], height=figure_size[1],
            tools=TOOLS, toolbar_location="right",
            active_scroll="xwheel_zoom")
        f3.line(np_x_range, kcb_median, color='blue', legend='Kcb Median')
        f3.line(np_x_range, kcb_q75, color='red', legend='Kcb 75th percentile')
        f3.line(np_x_range, kcb_q25, color='green', legend='Kcb 25th percentile')
        f3.line(np_x_range, season_median, color='black', legend='Season Median',
                line_dash="dashed")
        # f3.title = 'PPT and Irrigation [mm]'
        f3.grid.grid_line_alpha = 0.3
#        f3.xaxis.axis_label = 'Day of Year'
        f3.xaxis.axis_label_text_font_size = figure_ylabel_size
        f3.yaxis.axis_label = 'Kcb (dimensionless)'
        f3.yaxis.axis_label_text_font_size = figure_ylabel_size
        f3.xaxis.formatter=DatetimeTickFormatter(years=['%m/%d'], months=['%m/%d'], days=['%m/%d'])

        if figure_show_flag:
            # Open in a browser
            show(column([f1, f2, f3], sizing_mode='stretch_both'))
            # show(vplot(f1, f2, f3))
        if figure_save_flag:
            save(column([f1, f2, f3], sizing_mode='stretch_both'))
            # save(vplot(f1, f2, f3))
        del f1, f2, f3, f

        # Cleanup
        del etact_array, etpot_array, etbas_array
        del irrig_array, season_array
        del runoff_array, dperc_array
        del kc_array, kcb_array
        # del niwr_array
        # del etact_sub_array, niwr_sub_array

        # Cleanup
        del file_path, daily_df
        del dt_array, year_array, year_sub_array, doy_array
        del pmet_array
        del precip_array
        gc.collect()


def parse_args():
    """"""
    parser = argparse.ArgumentParser(
        description='Plot Crop Daily Timeseries',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        '-i', '--ini', metavar='PATH',
        type=lambda x: util.is_valid_file(parser, x), help='Input file')
    parser.add_argument(
        '--size', default=(1000, 300), type=int,
        nargs=2, metavar=('WIDTH', 'HEIGHT'),
        help='Figure size in pixels')
    parser.add_argument(
        '--no_save', default=True, action='store_false',
        help='Don\'t save timeseries figures in browser')
    parser.add_argument(
        '--show', default=False, action='store_true',
        help='Show timeseries figures to disk')
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
        '--debug', default=logging.INFO, const=logging.DEBUG,
        help='Debug level logging', action="store_const", dest="loglevel")
    args = parser.parse_args()

    # Convert relative paths to absolute paths
    if args.ini and os.path.isfile(os.path.abspath(args.ini)):
        args.ini = os.path.abspath(args.ini)
    return args


if __name__ == '__main__':
    args = parse_args()

    # Try using the command line argument if it was set
    if args.ini:
        ini_path = args.ini
    # If script was double clicked, set project folder with GUI
    elif 'PROMPT' not in os.environ:
        ini_path = util.get_path(os.getcwd(), 'Select the target INI file')
    # Try using the current working directory if there is only one INI
    # Could look for daily_stats folder, run_basin.py, and/or ini file
    elif len([x for x in os.listdir(os.getcwd()) if x.lower().endswith('.ini')]) == 1:
        ini_path = [
            os.path.join(os.getcwd(), x) for x in os.listdir(os.getcwd())
            if x.lower().endswith('.ini')][0]
    # Eventually list available INI files and prompt the user to select one
    # For now though, use the GUI
    else:
        ini_path = util.get_path(os.getcwd(), 'Select the target INI file')

    logging.basicConfig(level=args.loglevel, format='%(message)s')
    logging.info('\n{0}'.format('#' * 80))
    logging.info('{0:<20s} {1}'.format(
        'Run Time Stamp:', dt.datetime.now().isoformat(' ')))
    logging.info('{0:<20s} {1}'.format('Current Directory:', os.getcwd()))
    logging.info('{0:<20s} {1}'.format('Script:', os.path.basename(sys.argv[0])))

    main(ini_path, figure_show_flag=args.show,
         figure_save_flag=args.no_save, figure_size=args.size,
         start_date=args.start, end_date=args.end, crop_str=args.crops)
