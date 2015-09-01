#--------------------------------
# Name:         plot_py_crop_daily_timeseries.py
# Purpose:      Plot full daily data timeseries
# Author:       Charles Morton
# Created       2015-09-01
# Python:       2.7
#--------------------------------

import argparse
import calendar
import datetime as dt
import gc
import logging
import math
import os
import re
import shutil
import sys

from bokeh.plotting import figure, output_file, save, show, vplot
from bokeh.models import Callback, ColumnDataSource, Range1d
##from bokeh.models import Slider, DateRangeSlider
import numpy as np
import pandas as pd

################################################################################

def main(project_ws, figure_show_flag=False, figure_save_flag=True,
         figure_size=(1000,300), start_date=None, end_date=None,
         crop_str='', overwrite_flag=False):
    """Plot full daily data by crop

    Args:
        project_ws (str): Project workspace
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

    ## Input names
    input_folder = 'daily_stats'

    ## Output names
    output_folder = 'daily_plots'

    ## Only process a subset of the crops
    crop_keep_list = list(parse_int_set(crop_str))
    ## These crops will not be processed (if set)
    crop_skip_list = [44, 45, 46]

    ## Field names
    date_field   = 'Date'
    doy_field    = 'DOY'
    ##year_field   = 'Year'
    ##month_field  = 'Month'
    ##day_field    = 'Day'
    pmeto_field  = 'PMETo'
    precip_field = 'PPT'
    t30_field    = 'T30'

    etact_field  = 'ETact'
    etpot_field  = 'ETpot'
    etbas_field  = 'ETbas'
    irrig_field  = 'Irrigation'
    season_field = 'Season'
    runoff_field = 'Runoff'
    dperc_field = 'DPerc'
    niwr_field = 'NIWR'

    ## Number of header lines in data file
    header_lines = 2

    ## Additional figure controls
    figure_dynamic_size = False
    figure_ylabel_size = '12pt'

    ## Delimiter
    sep = ','
    ##sep = r"\s*"

    ########################################################################

    try:
        logging.info('\nPlot mean daily data by crop')
        logging.info('  Project Folder: {0}'.format(project_ws))

        ## If save and show flags were not set, prompt user
        ##logging.info('')
        ##if figure_save_flag is None:
        ##    figure_save_flag = query_yes_no('Save Figures', 'yes')
        ##if figure_show_flag is None:
        ##    figure_show_flag = query_yes_no('Show Figures', 'no')

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

        ## Limit x_panning to a specified date range
        ## Doesn't currently work
        ##x_bounds = (
        ##    np.datetime64(dt.datetime(year_start,1,1), 's'),
        ##    np.datetime64(dt.datetime(year_end+1,1,1), 's'))
        ## Initial range of timeseries to show
        ## This is independent of what timeseries is in the data and is only 
        ##   based on the end year
        ## Need to add a check to see if this range is in the data
        ##x_range = (
        ##    np.datetime64(dt.datetime(year_end-9,1,1), 's'),
        ##    np.datetime64(dt.datetime(year_end+1,1,1), 's'))

        #### Windows only a
        ##if figure_dynamic_size:
        ##    try:
        ##        logging.info('Setting plots width/height dynamically')
        ##        from win32api import GetSystemMetrics
        ##        figure_width = int(0.92 * GetSystemMetrics(0))
        ##        figure_height = int(0.28 * GetSystemMetrics(1))
        ##        logging.info('  {0} {1}'.format(GetSystemMetrics(0), GetSystemMetrics(1)))
        ##        logging.info('  {0} {1}'.format(figure_width, figure_height))
        ##    except:
        ##        figure_width = 1200
        ##        figure_height = 300

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
            data_df['year'] = data_df[date_field].map(lambda x: x.year)

            ## Build list of unique years
            year_array = np.sort(np.unique(np.array(data_df['year']).astype(np.int)))
            logging.debug('\nAll Years: \n{0}'.format(year_array.tolist()))
            
            ## Only keep years between year_start and year_end
            if year_start:
                crop_year_start = year_start
                data_df = data_df.ix['year' >= year_start]
                crop_year_start = max(year_end, year_array[0])
            else:
                crop_year_start = year_array[0]
            if year_end:
                data_df = data_df.ix['year' <= year_end]
                crop_year_end = min(year_end, year_array[-1])
            else:
                crop_year_end = year_array[-1]
            year_sub_array = np.sort(np.unique(np.array(data_df['year']).astype(np.int)))
            logging.debug('\nPlot Years: \n{0}'.format(year_sub_array.tolist()))

            ## Build separate arrays for each field of non-crop specific data
            dt_array = np.array(data_df[date_field])
            doy_array = np.array(data_df[doy_field]).astype(np.int)
            pmeto_array = np.array(data_df[pmeto_field])
            precip_array = np.array(data_df[precip_field])

            ## Remove leap days
            leap_array = (doy_array == 366)
            doy_sub_array = np.delete(doy_array, np.where(leap_array)[0])

            if crop_skip_list and crop_num in crop_skip_list:
                logging.debug('    Skipping, crop number in crop_skip_list')
                continue
            elif crop_keep_list and crop_num not in crop_keep_list:
                logging.debug('    Skipping, crop number not in crop_keep_list')
                continue
            
            ## Build separate arrays for each set of crop specific fields
            etact_array = np.array(data_df[etact_field])
            etpot_array = np.array(data_df[etpot_field])
            etbas_array = np.array(data_df[etbas_field])
            irrig_array = np.array(data_df[irrig_field])
            season_array = np.array(data_df[season_field])
            runoff_array = np.array(data_df[runoff_field])
            dperc_array = np.array(data_df[dperc_field])
            kc_array = etact_array / pmeto_array
            kcb_array = etbas_array / pmeto_array

            ## NIWR is ET - precip + runoff + deep percolation
            ## Don't include deep percolation when irrigating
            ##niwr_array = etact_array - (precip_array - runoff_array)
            ##niwr_array[irrig_array==0] += dperc_array[irrig_array == 0]

            ## Remove leap days
            ##etact_sub_array = np.delete(etact_array, np.where(leap_array)[0])
            ##niwr_sub_array = np.delete(niwr_array, np.where(leap_array)[0])

            ## Timeseries figures of daily data
            output_name = '{0}_crop_{1:02d}_{2}-{3}'.format(
                station, int(crop_num), crop_year_start, crop_year_end)
            output_path = os.path.join(output_ws, output_name+'.html')
            if overwrite_flag and os.path.isfile(output_path):
                os.remove(output_path)
            f = output_file(output_path, title=output_name)
            TOOLS = 'xpan,xwheel_zoom,box_zoom,reset,save'

            f1 = figure(
                x_axis_type='datetime', 
                width=figure_size[0], height=figure_size[1], 
                tools=TOOLS, toolbar_location="right")
                ##title='Evapotranspiration', x_axis_type='datetime',
            f1.line(dt_array, etact_array, color='blue', legend='ETact')
            f1.line(dt_array, etbas_array, color='green', legend='ETbas')
            f1.line(dt_array, pmeto_array, color='black', legend='ETos',
                    line_dash="dotted")
                    ##line_dash="dashdot")
            ##f1.title = 'Evapotranspiration [mm]'
            f1.grid.grid_line_alpha=0.3
            f1.yaxis.axis_label = 'Evapotranspiration [mm]'
            f1.yaxis.axis_label_text_font_size = figure_ylabel_size
            ##f1.xaxis.bounds = x_bounds

            f2 = figure(
                x_axis_type = "datetime", x_range=f1.x_range, 
                width=figure_size[0], height=figure_size[1],
                tools=TOOLS, toolbar_location="right")
            f2.line(dt_array, kc_array, color='blue', legend='Kc')
            f2.line(dt_array, kcb_array, color='green', legend='Kcb')
            f2.line(dt_array, season_array, color='black', legend='Season',
                    line_dash="dashed")
            ##f2.title = 'Kc and Kcb (dimensionless)'
            f2.grid.grid_line_alpha=0.3
            f2.yaxis.axis_label = 'Kc and Kcb (dimensionless)'
            f2.yaxis.axis_label_text_font_size = figure_ylabel_size
            ##f2.xaxis.bounds = x_bounds

            f3 = figure(
                x_axis_type = "datetime", x_range=f1.x_range, 
                width=figure_size[0], height=figure_size[1],
                tools=TOOLS, toolbar_location="right")
            f3.line(dt_array, precip_array, color='blue', legend='PPT')
            f3.line(dt_array, irrig_array, color='black', legend='Irrigation',
                    line_dash="dotted")
            ##f3.title = 'PPT and Irrigation [mm]'
            f3.grid.grid_line_alpha=0.3
            ##f3.xaxis.axis_label = 'Date'
            f3.yaxis.axis_label = 'PPT and Irrigation [mm]'
            f3.yaxis.axis_label_text_font_size = figure_ylabel_size
            ##f3.xaxis.bounds = x_bounds

            if figure_show_flag:
                ## Open in a browser
                show(vplot(f1, f2, f3))
            if figure_save_flag:
                save(vplot(f1, f2, f3))
            del f1, f2, f3, f

            ## Cleanup
            del etact_array, etpot_array, etbas_array
            del irrig_array, season_array
            del runoff_array, dperc_array
            del kc_array, kcb_array
            ##del niwr_array
            ##del etact_sub_array, niwr_sub_array

            ## Cleanup
            del file_path, data_df
            del dt_array, year_array, year_sub_array, doy_array
            del pmeto_array
            del precip_array
            gc.collect()

    except:
        logging.exception('Unhandled Exception Error\n\n')
            
    finally:
        pass
        ##raw_input('\nPress ENTER to close')

################################################################################

def get_project_directory(workspace):
    import Tkinter, tkFileDialog
    root = Tkinter.Tk()
    user_ws = tkFileDialog.askdirectory(
        initialdir=workspace, parent=root,
        title='Select the project directory', mustexist=True)
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
        description='Plot Crop Daily Timeseries',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        '--project', metavar='FOLDER', help='Project Folder')
    parser.add_argument(
        '--size', default=(1000, 300), type=int,
        nargs=2, metavar=('WIDTH','HEIGHT'),
        help='Figure size in pixels')
    parser.add_argument(
        '--no_save', default=True, action='store_false',
        help='Don\'t save timeseries figures in browser')
    parser.add_argument(
        '--show', default=False, action='store_true',
        help='Show timeseries figures to disk')
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
    logging.info('{0:<20s} {1}'.format('Run Time Stamp:', dt.datetime.now().isoformat(' ')))
    logging.info('{0:<20s} {1}'.format('Current Directory:', project_ws))
    logging.info('{0:<20s} {1}'.format('Script:', os.path.basename(sys.argv[0])))

    main(project_ws, figure_show_flag=args.show, 
         figure_save_flag=args.no_save, figure_size=args.size,
         start_date=args.start, end_date=args.end, crop_str=args.crops,
         overwrite_flag=args.overwrite)
