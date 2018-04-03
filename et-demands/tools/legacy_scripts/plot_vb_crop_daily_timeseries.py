#--------------------------------
# Name:         plot_vb_crop_daily_timeseries.py
# Purpose:      Plot full daily data timeseries
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

from bokeh.plotting import figure, output_file, save, show, vplot
import numpy as np
# import pandas as pd


def main(pmdata_ws, figure_show_flag=None, figure_save_flag=None,
         figure_size=(1000, 300), start_date=None, end_date=None):
    """Plot full daily data by crop

    Args:
        pmdata_ws (str):
        figure_show_flag (bool):
        figure_save_flag (bool):
        figure_size (tuple):
        start_date (str): ISO format date string (YYYY-MM-DD)
        end_date (str): ISO format date string (YYYY-MM-DD)

    Returns:
        None
    """

    # Input names
    et_folder = 'ET'
    # et_folder    = 'ETc'
    # stats_folder = 'stats'

    # Output names
    figure_folder = 'plots'

    # These crops will not be processed (if set)
    crop_skip_list = [44, 45, 46]
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

    # Additional figure controls
    figure_dynamic_size = False
    figure_ylabel_size = '12pt'

    # Delimiter
    if et_folder == 'ETc':
        sep = r'\s*'
    else:
        sep = ','

    logging.info('\nPlot mean daily data by crop')
    logging.info('  PMData Folder: {0}'.format(pmdata_ws))

    # If save and show flags were not set, prompt user
    logging.info('')
    if figure_save_flag is None:
        figure_save_flag = query_yes_no('Save Figures', 'yes')
    if figure_show_flag is None:
        figure_show_flag = query_yes_no('Show Figures', 'no')

    # Input workspaces
    et_ws = os.path.join(pmdata_ws, et_folder)
    # stats_ws = os.path.join(pmdata_ws, stats_folder)

    # Output workspaces
    figure_ws = os.path.join(pmdata_ws, figure_folder)

    # Check workspaces
    if not os.path.isdir(pmdata_ws):
        logging.error(
            '\nERROR: The pmdata folder {0} could be found\n'.format(
                pmdata_ws))
        sys.exit()
    if not os.path.isdir(et_ws):
        logging.error(
            '\nERROR: The ET folder {0} could be found\n'.format(et_ws))
        sys.exit()
    # if not os.path.isdir(stats_ws):
    #     .error(
    #        '\nERROR: The stats folder {0} could be found\n'.format(stats_ws))
    #     .exit()
    if not os.path.isdir(figure_ws):
        os.mkdir(figure_ws)

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

    # Limit x_panning to a specified date range
    # Doesn't currently work
    # x_bounds = (
    #     .datetime64(dt.datetime(year_start,1,1), 's'),
    #     .datetime64(dt.datetime(year_end+1,1,1), 's'))
    # Initial range of timeseries to show
    # This is independent of what timeseries is in the data and is only
    #   based on the end year
    # Need to add a check to see if this range is in the data
    # x_range = (
    #     .datetime64(dt.datetime(year_end-9,1,1), 's'),
    #     .datetime64(dt.datetime(year_end+1,1,1), 's'))

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
    data_re = re.compile('(?P<CELLID>\w+)ETc.dat$', re.I)

    # Build crop name and index dictionaries as the files are processed
    crop_name_dict = dict()
    crop_index_dict = dict()

    # Build list of all data files
    data_file_list = sorted(
        [os.path.join(et_ws, f_name) for f_name in os.listdir(et_ws)
         if data_re.match(f_name)])
    if not data_file_list:
        logging.error(
            '  ERROR: No daily ET files were found\n' +
            '  ERROR: Check the folder_name parameters\n')
        sys.exit()

    # Build list of stations
    station_list = sorted(list(set([
        os.path.basename(f_path).split('ETc')[0]
        for f_path in data_file_list])))

    # Process each file
    for file_path in data_file_list:
        file_name = os.path.basename(file_path)
        logging.debug('')
        logging.info('  {0}'.format(file_name))

        station = file_name.split('ETc')[0]
        logging.debug('    Station:         {0}'.format(station))
        if station == 'temp':
            logging.debug('      Skipping')
            continue

        # Read in file header
        with open(file_path, 'r') as f:
            header_list = f.readlines()[:header_lines]
        f.close()

        # Parse crop list
        # Split on "Crop:" but skip first item (number of crops)
        # Remove white space and empty strings
        f_crop_list = header_list[header_lines - 2]
        f_crop_list = [item.strip() for item in f_crop_list.split('Crop:')[1:]]
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
        data = np.genfromtxt(
            file_path, skip_header=(header_lines - 1), names=True,
            delimiter=sep)
        logging.debug('\nFields: \n{0}'.format(data.dtype.names))

        # Build list of unique years
        year_array = data[year_field].astype(np.int)
        year_sub_array = np.sort(np.unique(year_array))
        logging.debug('\nAll Years: \n{0}'.format(year_sub_array.tolist()))

        # Only keep years between year_start and year_end
        if year_start:
            crop_year_start = year_start
            year_sub_array = year_sub_array[year_sub_array >= year_start]
            crop_year_start = max(year_end, year_sub_array[0])
        else:
            crop_year_start = year_array[0]
        if year_end:
            year_sub_array = year_sub_array[year_sub_array <= year_end]
            crop_year_end = min(year_end, year_sub_array[-1])
        else:
            crop_year_end = year_array[-1]
        date_mask = np.in1d(year_array, year_sub_array)
        logging.debug('\nPlot Years: \n{0}'.format(year_sub_array.tolist()))

        # # Build list of unique years
        # year_sub_array = np.unique(data[year_field].astype(np.int))
        # logging.debug('\nAll Years: \n{0}'.format(year_sub_array.tolist()))
        # # Only keep years between year_start and year_end
        # if year_start:
        #      = year_sub_array[(year_start <= year_sub_array)]
        # if year_end:
        #      = year_sub_array[(year_sub_array <= year_end)]
        # logging.debug('\nPlot Years: \n{0}'.format(year_sub_array.tolist()))
        #
        # # Check year start and year end
        # if year_start not in year_sub_array:
        #     .error('\n  ERROR: Start Year is invalid\n')
        #      SystemExit()
        # if year_end not in year_sub_array:
        #     .error('\n  ERROR: End Year is invalid\n')
        #      SystemExit()
        # if year_end <= year_start:
        #     .error('\n  ERROR: End Year must be >= Start Year\n')
        #      SystemExit()

        # Build separate arrays for each field of non-crop specific data
        doy_array = data[doy_field][date_mask].astype(np.int)
        year_array = data[year_field][date_mask].astype(np.int)
        month_array = data[month_field][date_mask].astype(np.int)
        day_array = data[day_field][date_mask].astype(np.int)
        pmeto_array = data[pmeto_field][date_mask]
        precip_array = data[precip_field][date_mask]
        dt_array = np.array([
            dt.datetime(int(year), int(month), int(day))
            for year, month, day in zip(year_array, month_array, day_array)])

        # Remove leap days
        # leap_array = (doy_array == 366)
        # doy_sub_array = np.delete(doy_array, np.where(leap_array)[0])

        # Process each crop
        # f_crop_i is based on order of crops in the file
        # crop_i is based on a sorted index of the user crop_list
        for f_crop_i, (crop_num, crop_name) in enumerate(f_crop_list):
            logging.debug('  Crop: {0} ({1})'.format(crop_name, crop_num))
            if crop_num in crop_skip_list:
                logging.debug(
                    '    Skipping, crop number not in crop_skip_list')
                continue
            if crop_keep_list and crop_num not in crop_keep_list:
                logging.debug(
                    '    Skipping, crop number not in crop_keep_list')
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

            # Field names are built based on the crop i value
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

            # Build separate arrays for each set of crop specific fields
            etact_array = data[etact_sub_field][date_mask]
            etpot_array = data[etpot_sub_field][date_mask]
            etbas_array = data[etbas_sub_field][date_mask]
            irrig_array = data[irrig_sub_field][date_mask]
            season_array = data[season_sub_field][date_mask]
            runoff_array = data[runoff_sub_field][date_mask]
            dperc_array = data[dperc_sub_field][date_mask]
            kc_array = etact_array / pmeto_array
            kcb_array = etbas_array / pmeto_array

            # NIWR is ET - precip + runoff + deep percolation
            # Don't include deep percolation when irrigating
            # niwr_array = etact_array - (precip_array - runoff_array)
            # niwr_array[irrig_array==0] += dperc_array[irrig_array == 0]

            # Remove leap days
            # etact_sub_array = np.delete(etact_array, np.where(leap_array)[0])
            # niwr_sub_array = np.delete(niwr_array, np.where(leap_array)[0])

            # Timeseries figures of daily data
            output_name = '{0}_Crop_{1}_{2}-{3}'.format(
                station, crop_num, crop_year_start, crop_year_end)
            output_file(os.path.join(figure_ws, output_name+'.html'),
                        title=output_name)
            TOOLS = 'xpan,xwheel_zoom,box_zoom,reset,save'

            f1 = figure(
                x_axis_type='datetime',
                width=figure_size[0], height=figure_size[1],
                tools=TOOLS, toolbar_location="right")
                # title='Evapotranspiration', x_axis_type='datetime',
            f1.line(dt_array, etact_array, color='blue', legend='ETact')
            f1.line(dt_array, etbas_array, color='green', legend='ETbas')
            f1.line(dt_array, pmeto_array, color='black', legend='ETos',
                    line_dash="dotted")
                    # line_dash="dashdot")
            # f1.title = 'Evapotranspiration [mm]'
            f1.grid.grid_line_alpha = 0.3
            f1.yaxis.axis_label = 'Evapotranspiration [mm]'
            f1.yaxis.axis_label_text_font_size = figure_ylabel_size
            # f1.xaxis.bounds = x_bounds

            f2 = figure(
                x_axis_type="datetime", x_range=f1.x_range,
                width=figure_size[0], height=figure_size[1],
                tools=TOOLS, toolbar_location="right")
            f2.line(dt_array, kc_array, color='blue', legend='Kc')
            f2.line(dt_array, kcb_array, color='green', legend='Kcb')
            f2.line(dt_array, season_array, color='black', legend='Season',
                    line_dash="dashed")
            # f2.title = 'Kc and Kcb (dimensionless)'
            f2.grid.grid_line_alpha = 0.3
            f2.yaxis.axis_label = 'Kc and Kcb (dimensionless)'
            f2.yaxis.axis_label_text_font_size = figure_ylabel_size
            # f2.xaxis.bounds = x_bounds

            f3 = figure(
                x_axis_type="datetime", x_range=f1.x_range,
                width=figure_size[0], height=figure_size[1],
                tools=TOOLS, toolbar_location="right")
            f3.line(dt_array, precip_array, color='blue', legend='PPT')
            f3.line(dt_array, irrig_array, color='black', legend='Irrigation',
                    line_dash="dotted")
            # f3.title = 'PPT and Irrigation [mm]'
            f3.grid.grid_line_alph = 0.3
            # f3.xaxis.axis_label = 'Date'
            f3.yaxis.axis_label = 'PPT and Irrigation [mm]'
            f3.yaxis.axis_label_text_font_size = figure_ylabel_size
            # f3.xaxis.bounds = x_bounds

            if figure_show_flag:
                # Open in a browser
                show(vplot(f1, f2, f3))
            if figure_save_flag:
                save(vplot(f1, f2, f3))

            # Cleanup
            del etact_array, etact_sub_field
            del etpot_array, etpot_sub_field
            del etbas_array, etbas_sub_field
            del irrig_array, irrig_sub_field
            del season_array, season_sub_field
            del runoff_array, runoff_sub_field
            del dperc_array, dperc_sub_field
            del kc_array, kcb_array
            # del niwr_array
            # del etact_sub_array, niwr_sub_array
            # break

        # Cleanup
        del file_path, f_crop_list, data
        del doy_array, year_array, month_array, day_array
        del pmeto_array
        del precip_array
        # del date_array
        # del dt_array
        del date_mask


def get_pmdata_workspace(workspace):
    """"""
    import Tkinter, tkFileDialog
    root = Tkinter.Tk()
    user_ws = tkFileDialog.askdirectory(
        initialdir=workspace, parent=root,
        title='Select the target PMData directory', mustexist=True)
    root.destroy()
    return user_ws


def query_yes_no(question, default="yes"):
    """Ask a yes/no question via raw_input() and return their answer.

    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
        It must be "yes" (the default), "no" or None (meaning
        an answer is required of the user).

    The "answer" return value is True for "yes" or False for "no".

    From: http://stackoverflow.com/questions/3041986/python-command-line-yes-no-input
    """
    valid = {"yes": True, "y": True, "ye": True,
             "no": False, "n": False}
    if default is None:
        prompt = " [y/n]: "
    elif default == "yes":
        prompt = " [Y/n]: "
    elif default == "no":
        prompt = " [y/N]: "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while True:
        sys.stdout.write(question + prompt)
        choice = raw_input().lower()
        if default is not None and choice == '':
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' "
                             "(or 'y' or 'n').\n")


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
        input_dt = dt.datetime.strptime(input_date, "%Y-%m-%d")
        return input_date
    except ValueError:
        msg = "Not a valid date: '{0}'.".format(input_date)
        raise argparse.ArgumentTypeError(msg)


def parse_args():
    """"""
    parser = argparse.ArgumentParser(
        description='Plot Crop Daily Timeseries',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        'workspace', nargs='?', default=get_pmdata_workspace(os.getcwd()),
        # 'workspace', nargs='?', default=os.path.join(os.getcwd(), 'PMData'),
        help='PMData Folder', metavar='FOLDER')
    parser.add_argument(
        '--size', default=(1000, 300), type=int,
        nargs=2, metavar=('WIDTH', 'HEIGHT'),
        help='Figure size in pixels')
    parser.add_argument(
        '--save', default=None, action='store_true',
        help='Show timeseries figures in browser')
    parser.add_argument(
        '--show', default=None, action='store_true',
        help='Save timeseries figures to disk')
    parser.add_argument(
        '--start', default=None, type=valid_date,
        help='Start date (format YYYY-MM-DD)', metavar='DATE')
    parser.add_argument(
        '--end', default=None, type=valid_date,
        help='End date (format YYYY-MM-DD)', metavar='DATE')
    # parser.add_argument(
    #    '-o', '--overwrite', default=None, action="store_true",
    #     ='Force overwrite of existing files')
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

    logging.basicConfig(level=args.loglevel, format='%(message)s')
    logging.info('\n{0}'.format('#' * 80))
    log_f = '{0:<20s} {1}'
    logging.info(log_f.format(
        'Run Time Stamp:', dt.datetime.now().isoformat(' ')))
    logging.info(log_f.format('Current Directory:', args.workspace))
    logging.info(log_f.format('Script:', os.path.basename(sys.argv[0])))

    main(pmdata_ws=args.workspace, figure_show_flag=args.show,
         figure_save_flag=args.save, figure_size=args.size,
         start_date=args.start, end_date=args.end)
