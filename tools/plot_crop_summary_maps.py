#--------------------------------
# Name:         plot_crop_summary_maps.py
# Purpose:      Plot crop summary maps from daily data
# Author:       Charles Morton
# Created       2016-08-16
# Python:       2.7
#--------------------------------

import argparse
from collections import defaultdict
import datetime as dt
import gc
import logging
import os
import re
import sys

from descartes import PolygonPatch
import fiona
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.colors as colors
# from matplotlib.collections import PatchCollection
import numpy as np
import pandas as pd
from shapely.geometry import MultiPolygon, Polygon, shape

import util

# import geojson
# import json
# import cartopy.crs as ccrs
# import cartopy.io.shapereader as shpreader
# from fiona.crs import to_string
# from mpl_toolkits.basemap import Basemap, maskoceans
# from pyproj import Proj, transform
# import shapefile
# import vincent

matplotlib.rc('font', family='sans-serif')
# matplotlib.rc('font', family='cursive')
# matplotlib.rc('font', family='monospace')


def main(ini_path, show_flag=False, save_flag=True, label_flag=False,
         figure_size=(12, 12), figure_dpi=300, start_date=None, end_date=None,
         crop_str='', simplify_tol=None, area_threshold=0):
    """Plot crop summary maps using daily output files

    Args:
        ini_path (str): file path of the project INI file
        show_flag (bool): if True, show maps
        save_flag (bool): if True, save maps to disk
        label_flag (bool): if True, label maps with cell values
        figure_size (tuple): width, height tuple [inches]
        start_date (str): ISO format date string (YYYY-MM-DD)
        end_date (str): ISO format date string (YYYY-MM-DD)
        crop_str (str): comma separate list or range of crops to compare
        simplify_tol (float): simplify tolerance [in the units of ET Cells]
        area_threshold (float): CDL area threshold [acres]

    Returns:
        None
    """

    # ET Cells field names
    cell_id_field = 'CELL_ID'
    crop_area_field = 'AG_ACRES'

    # Input field names
    date_field = 'Date'
    doy_field = 'DOY'
    year_field = 'Year'
    # month_field = 'Month'
    # day_field = 'Day'
    # pmeto_field = 'PMETo'
    # precip_field = 'PPT'
    # t30_field = 'T30'
    etact_field = 'ETact'
    # etpot_field = 'ETpot'
    # etbas_field = 'ETbas'
    # irrig_field = 'Irrigation'
    season_field = 'Season'
    cutting_field = 'Cutting'
    # runoff_field = 'Runoff'
    # dperc_field = 'DPerc'
    # niwr_field = 'NIWR'
    # kc_field = 'Kc'
    # kcb_field = 'Kcb'

    # Output field names
    annual_et_field = 'Annual_ET'
    seasonal_et_field = 'Seasonal_ET'
    gs_start_doy_field = 'Start_DOY'
    gs_end_doy_field = 'End_DOY'
    gs_length_field = 'GS_Length'

    # Number of header lines in data file
    # header_lines = 2

    # Additional figure controls
    # figure_dynamic_size = False
    # figure_ylabel_size = '12pt'

    # Delimiter
    sep = ','
    # sep = r"\s*"

    daily_input_re = re.compile(
        '(?P<cell_id>\w+)_daily_crop_(?P<crop_num>\d{2}).csv', re.I)
    # gs_input_re = re.compile(
    #     '(?P<cell_id>\w+)_gs_crop_(?P<crop_num>\d{2}).csv', re.I)

    logging.info('\nGenerate crop summary maps from daily data')
    logging.info('  INI: {}'.format(ini_path))

    # Check that the INI file can be read
    crop_et_sec = 'CROP_ET'
    config = util.read_ini(ini_path, crop_et_sec)

    # Get the project workspace and daily ET folder from the INI file
    def get_config_param(config, param_name, section):
        """"""
        try:
            param_value = config.get(section, param_name)
        except:
            logging.error(('ERROR: The {} parameter is not set' +
                           ' in the INI file').format(param_name))
            sys.exit()
        return param_value
    cells_path = get_config_param(config, 'cells_path', crop_et_sec)
    project_ws = get_config_param(config, 'project_folder', crop_et_sec)
    daily_stats_ws = os.path.join(
        project_ws, get_config_param(
            config, 'daily_output_folder', crop_et_sec))

    try:
        output_ws = os.path.join(
            project_ws, config.get(crop_et_sec, 'summary_maps_folder'))
    except:
        if 'stats' in daily_stats_ws:
            output_ws = daily_stats_ws.replace('stats', 'maps')
        else:
            output_ws = os.path.join(project_ws, 'summary_maps_folder')

    # Check workspaces
    if not os.path.isdir(daily_stats_ws):
        logging.error(('\nERROR: The daily ET stats folder {0} ' +
                       'could be found\n').format(daily_stats_ws))
        sys.exit()
    if not os.path.isfile(cells_path):
        logging.error(('\nERROR: The cells shapefile {0} ' +
                       'could be found\n').format(cells_path))
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

    # Allow user to subset crops from INI
    try:
        crop_skip_list = sorted(list(util.parse_int_set(
            config.get(crop_et_sec, 'crop_skip_list'))))
    except:
        crop_skip_list = []
        # crop_skip_list = [44, 45, 46]
    try:
        crop_test_list = sorted(list(util.parse_int_set(
            config.get(crop_et_sec, 'crop_test_list'))))
    except:
        crop_test_list = []

    # Allow user to subset cells from INI
    try:
        cell_skip_list = config.get(crop_et_sec, 'cell_skip_list').split(',')
        cell_skip_list = sorted([c.strip() for c in cell_skip_list])
    except:
        cell_skip_list = []
    try:
        cell_test_list = config.get(crop_et_sec, 'cell_test_list').split(',')
        cell_test_list = sorted([c.strip() for c in cell_test_list])
    except:
        cell_test_list = []

    # Overwrite INI crop list with user defined values
    # Could also append to the INI crop list
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
    logging.debug('  cell_test_list = {0}'.format(cell_test_list))
    logging.debug('  cell_test_list = {0}'.format(cell_test_list))

    # Build list of all daily ET files
    daily_path_dict = defaultdict(dict)
    for f_name in os.listdir(daily_stats_ws):
        f_match = daily_input_re.match(os.path.basename(f_name))
        if not f_match:
            continue
        cell_id = f_match.group('cell_id')
        crop_num = int(f_match.group('crop_num'))
        if f_match.group('cell_id') == 'test':
            continue
        elif crop_skip_list and crop_num in crop_skip_list:
            continue
        elif crop_test_list and crop_num not in crop_test_list:
            continue
        elif cell_skip_list and cell_id in cell_skip_list:
            continue
        elif cell_test_list and cell_id not in cell_test_list:
            continue
        else:
            daily_path_dict[crop_num][cell_id] = os.path.join(
                daily_stats_ws, f_name)
    if not daily_path_dict:
        logging.error(
            '  ERROR: No daily ET files were found\n' +
            '  ERROR: Check the folder_name parameters\n')
        sys.exit()

    # Read ET Cells into memory with fiona and shapely
    # Convert multi-polygons to list of polygons
    cell_geom_dict = defaultdict(list)
    cell_data_dict = dict()
    cell_extent = []
    with fiona.open(cells_path, "r") as cell_f:
        cell_extent = cell_f.bounds[:]
        # Fiona is printing a debug statement here "Index: N"
        for item in cell_f:
            cell_id = item['properties'][cell_id_field]
            cell_data_dict[cell_id] = item['properties']

            # Simplify the geometry
            if simplify_tol is not None:
                item_geom = shape(item['geometry']).simplify(
                    simplify_tol, preserve_topology=False)
            else:
                item_geom = shape(item['geometry'])

            # Unpack multipolygons to lists of polygons
            if item_geom.is_empty:
                continue
            elif item_geom.geom_type == 'MultiPolygon':
                # Order the geometries from largest to smallest area
                item_geom_list = sorted(
                    [[g.area, g] for g in item_geom if not g.is_empty],
                    reverse=True)
                for item_area, item_poly in item_geom_list:
                    cell_geom_dict[cell_id].append(item_poly)
            elif item_geom.geom_type == 'Polygon':
                cell_geom_dict[cell_id].append(item_geom)
            else:
                logging.error('Invalid geometry type')
                continue
    if not cell_geom_dict:
        logging.error('ET Cell shapefile not read in')
        sys.exit()

    # Plot keyword arguments
    plot_kwargs = {
        'extent': cell_extent,
        'fig_size': figure_size,
        'fig_dpi': figure_dpi,
        'save_flag': save_flag,
        'show_flag': show_flag,
        'label_flag': label_flag,
    }

    # Plot CELL_ID
    logging.info('\nPlotting total crop acreage')
    cell_id_dict = {
        k: k.replace(' ', '\n') for k in cell_data_dict.iterkeys()}
    # cell_id_dict = {k:k for k in cell_data_dict.iterkeys()}
    cell_plot_func(
        os.path.join(output_ws, 'cell_id.png'),
        cell_geom_dict, cell_id_dict, cmap=None,
        title_str='CELL_ID', clabel_str='',
        label_size=6, **plot_kwargs)

    # Plot total CDL crop acreages
    logging.info('\nPlotting total crop acreage')
    crop_area_dict = {
        k: v[crop_area_field] for k, v in cell_data_dict.iteritems()}
    # crop_area_dict = {
    #     :v[crop_area_field] for k,v in cell_data_dict.iteritems()
    #      v[crop_area_field] > area_threshold}
    cell_plot_func(
        os.path.join(output_ws, 'total_crop_acreage.png'),
        cell_geom_dict, crop_area_dict, cmap=cm.YlGn,
        title_str='Total CDL Crop Area', clabel_str='acres',
        label_size=6, **plot_kwargs)

    # Plot PMETo
    # pmeto_dict = {
    #     :v[crop_area_field]
    #      k,v in cell_data_dict.iteritems()}
    # cell_plot_func(
    #     .path.join(output_ws, 'eto.png'),
    #     , pmeto_dict, cmap=cm.YlGn,
    #     ='Reference ET', clabel_str='mm',
    #     =8, **plot_kwargs)

    # Build an empty dataframe to write the total area weighted ET
    # columns_dict = {cell_id_field:sorted(cell_data_dict.keys())}
    columns_dict = {
        'CROP_{0:02d}'.format(k): None for k in daily_path_dict.keys()}
    columns_dict[cell_id_field] = sorted(cell_data_dict.keys())
    crop_area_df = pd.DataFrame(columns_dict).set_index(cell_id_field)
    annual_et_df = pd.DataFrame(columns_dict).set_index(cell_id_field)
    seasonal_et_df = pd.DataFrame(columns_dict).set_index(cell_id_field)

    # First process by crop
    logging.info('')
    for crop_num in sorted(daily_path_dict.keys()):
        crop_column = 'CROP_{0:02d}'.format(crop_num)
        logging.info('Crop Num: {0:2d}'.format(crop_num))

        # First threshold CDL crop areas
        # Check all cell_id's against crop_area_dict keys
        crop_area_dict = {
            k: v[crop_column] for k, v in cell_data_dict.iteritems()
            if (k in daily_path_dict[crop_num].keys() and
                v[crop_column] > area_threshold)}
        # crop_area_dict = {
        #     k: v[crop_column] for k,v in cell_data_dict.iteritems()
        #     if k in daily_path_dict[crop_num].keys()}

        # Build an empty dataframe to write to
        crop_output_df = pd.DataFrame({
            cell_id_field: sorted(list(
                set(daily_path_dict[crop_num].keys()) &
                set(crop_area_dict.keys()))),
            annual_et_field: None,
            seasonal_et_field: None,
            gs_start_doy_field: None,
            gs_end_doy_field: None,
            gs_length_field: None,
            cutting_field: None})
        crop_output_df.set_index(cell_id_field, inplace=True)

        # Process each cell
        for cell_id, input_path in sorted(daily_path_dict[crop_num].items()):
            logging.debug('  Cell ID:   {0}'.format(cell_id))

            # Skip if crop area is below threshold
            if cell_id not in crop_area_dict.keys():
                logging.debug('    Area below threshold, skipping')
                continue

            # Get crop name from the first line of the output file
            # DEADBEEF - This may not exist in the output file...
            with open(input_path, 'r') as file_f:
                crop_name = file_f.readline().split('-', 1)[1].strip()
                crop_name = crop_name.replace('--', ' - ')
                crop_name = crop_name.replace(' (', ' - ').replace(')', '')
                logging.debug('  Crop:      {0}'.format(crop_name))
            logging.debug('    {0}'.format(os.path.basename(input_path)))

            # Read data from file into record array (structured array)
            daily_df = pd.read_table(
                input_path, header=0, comment='#', sep=sep)
            logging.debug(
                '    Fields: {0}'.format(', '.join(daily_df.columns.values)))
            daily_df[date_field] = pd.to_datetime(daily_df[date_field])
            daily_df.set_index(date_field, inplace=True)

            # Build list of unique years
            year_array = np.sort(
                np.unique(np.array(daily_df[year_field]).astype(np.int)))
            logging.debug('    All Years: {0}'.format(
                ', '.join(list(util.ranges(year_array.tolist())))))
            # logging.debug('    All Years: {0}'.format(
            #    ','.join(map(str, year_array.tolist()))))

            # Don't include the first year in the stats
            crop_year_start = min(daily_df[year_field])
            logging.debug(
                '    Skipping {}, first year'.format(crop_year_start))
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
            del crop_year_start, crop_year_end

            # Only keep years between year_start and year_end
            if year_start:
                daily_df = daily_df[daily_df[year_field] >= year_start]
            if year_end:
                daily_df = daily_df[daily_df[year_field] <= year_end]

            year_sub_array = np.sort(
                np.unique(np.array(daily_df[year_field]).astype(np.int)))
            logging.debug('    Plot Years: {0}'.format(
                ', '.join(list(util.ranges(year_sub_array.tolist())))))
            # logging.debug('    Plot Years: {0}'.format(
            #    ','.join(map(str, year_sub_array.tolist()))))

            # Seasonal/Annual ET
            crop_seasonal_et_df = daily_df[daily_df[season_field] > 0].resample(
                'AS', how={etact_field: np.sum})
            crop_annual_et_df = daily_df.resample(
                'AS', how={etact_field: np.sum})

            crop_output_df.set_value(
                cell_id, seasonal_et_field, float(crop_seasonal_et_df.mean()))
            crop_output_df.set_value(
                cell_id, annual_et_field, float(crop_annual_et_df.mean()))
            del crop_seasonal_et_df, crop_annual_et_df

            # Compute growing season start and end DOY from dailies
            crop_gs_df = daily_df[[year_field, season_field]].resample(
                'AS', how={year_field: np.mean})
            crop_gs_df[gs_start_doy_field] = None
            crop_gs_df[gs_end_doy_field] = None

            crop_gs_fields = [year_field, doy_field, season_field]
            crop_gs_groupby = daily_df[crop_gs_fields].groupby([year_field])
            for year, group in crop_gs_groupby:
                if not np.any(group[season_field].values):
                    logging.debug('  Skipping, season flag was never set to 1')
                    continue

                # Identify "changes" in season flag
                season_diff = np.diff(group[season_field].values)

                # Growing season start
                try:
                    start_i = np.where(season_diff == 1)[0][0] + 1
                    gs_start_doy = float(group.ix[start_i, doy_field])
                except:
                    gs_start_doy = float(min(group[doy_field].values))
                crop_gs_df.set_value(
                    group.index[0], gs_start_doy_field, gs_start_doy)

                # Growing season end
                try:
                    end_i = np.where(season_diff == -1)[0][0] + 1
                    gs_end_doy = float(group.ix[end_i, doy_field])
                except:
                    gs_end_doy = float(max(group[doy_field].values))
                crop_gs_df.set_value(
                    group.index[0], gs_end_doy_field, gs_end_doy)
                del season_diff

            # Write mean growing season start and end DOY
            crop_output_df.set_value(
                cell_id, gs_start_doy_field,
                int(round(crop_gs_df[gs_start_doy_field].mean(), 0)))
            crop_output_df.set_value(
                cell_id, gs_end_doy_field,
                int(round(crop_gs_df[gs_end_doy_field].mean(), 0)))

            # Growing season length
            crop_output_df.set_value(
                cell_id, gs_length_field,
                int(round(crop_gs_groupby[season_field].sum().mean(), 0)))

            # Crop cuttings
            # Maybe only sum cuttings that are in season
            if (cutting_field in list(daily_df.columns.values) and
                np.any(daily_df[cutting_field].values)):
                gs_input_fields = [year_field, cutting_field]
                crop_gs_groupby = daily_df[gs_input_fields].groupby([year_field])
                crop_output_df.set_value(
                    cell_id, cutting_field,
                    int(round(crop_gs_groupby[cutting_field].sum().mean(), 0)))

            # Cleanup
            del crop_gs_groupby, crop_gs_df, crop_gs_fields

        # Make the maps
        logging.debug('')
        title_fmt = 'Crop {0:02d} - {1} - {2}'.format(
            crop_num, crop_name, '{}')

        # Crop acreages
        cell_plot_func(
            os.path.join(
                output_ws, 'crop_{0:02d}_cdl_acreage.png'.format(crop_num)),
            cell_geom_dict, crop_area_dict, cmap=cm.YlGn, clabel_str='acres',
            title_str=title_fmt.format('CDL Area'), **plot_kwargs)

        # Annual/Seasonal ET
        cell_plot_func(
            os.path.join(
                output_ws, 'crop_{0:02d}_et_actual.png'.format(crop_num)),
            cell_geom_dict, crop_output_df[annual_et_field].to_dict(),
            cmap=cm.YlGn, clabel_str='mm',
            title_str=title_fmt.format('Annual Evapotranspiration'),
            **plot_kwargs)
        cell_plot_func(
            os.path.join(
                output_ws, 'crop_{0:02d}_et_seasonal.png'.format(crop_num)),
            cell_geom_dict, crop_output_df[seasonal_et_field].to_dict(),
            cmap=cm.YlGn, clabel_str='mm',
            title_str=title_fmt.format('Seasonal Evapotranspiration'),
            **plot_kwargs)

        # Growing Season Start/End/Length
        cell_plot_func(
            os.path.join(
                output_ws, 'crop_{0:02d}_gs_start_doy.png'.format(crop_num)),
            cell_geom_dict, crop_output_df[gs_start_doy_field].to_dict(),
            cmap=cm.RdYlBu, clabel_str='Day of Year',
            title_str=title_fmt.format('Growing Season Start'),
            **plot_kwargs)
        cell_plot_func(
            os.path.join(
                output_ws, 'crop_{0:02d}_gs_end_doy.png'.format(crop_num)),
            cell_geom_dict, crop_output_df[gs_end_doy_field].to_dict(),
            cmap=cm.RdYlBu_r, clabel_str='Day of Year',
            title_str=title_fmt.format('Growing Season End'),
            **plot_kwargs)
        cell_plot_func(
            os.path.join(
                output_ws, 'crop_{0:02d}_gs_length.png'.format(crop_num)),
            cell_geom_dict, crop_output_df[gs_length_field].to_dict(),
            cmap=cm.RdYlBu_r, clabel_str='Days',
            title_str=title_fmt.format('Growing Season Length'),
            **plot_kwargs)

        # Crop cuttings
        if np.any(crop_output_df[cutting_field].values):
            cell_plot_func(
                os.path.join(
                    output_ws, 'crop_{0:02d}_cuttings.png'.format(crop_num)),
                cell_geom_dict, crop_output_df[cutting_field].to_dict(),
                cmap=cm.RdYlBu_r, clabel_str='Cuttings',
                title_str=title_fmt.format('Crop Cuttings'), **plot_kwargs)

        # Crop area weighted ET
        crop_area_df[crop_column] = pd.Series(crop_area_dict)
        annual_et_df[crop_column] = crop_output_df[annual_et_field]
        seasonal_et_df[crop_column] = crop_output_df[seasonal_et_field]

        # Compute and plot crop weighted average ET
        annual_et = (
            (annual_et_df * crop_area_df).sum(axis=1) /
            crop_area_df.sum(axis=1))
        seasonal_et = (
            (seasonal_et_df * crop_area_df).sum(axis=1) /
            crop_area_df.sum(axis=1))
        cell_plot_func(
            os.path.join(output_ws, 'et_actual.png'),
            cell_geom_dict, annual_et[annual_et.notnull()].to_dict(),
            cmap=cm.YlGn, clabel_str='mm',
            title_str='Crop Area Weighted Annual Evapotranspiration',
            **plot_kwargs)
        cell_plot_func(
            os.path.join(output_ws, 'et_seasonal.png'),
            cell_geom_dict, seasonal_et[seasonal_et.notnull()].to_dict(),
            cmap=cm.YlGn, clabel_str='mm',
            title_str='Crop Area Weighted Seasonal Evapotranspiration',
            **plot_kwargs)
        del annual_et, seasonal_et

        # Cleanup
        del crop_output_df
        gc.collect()

    # Compute and plot crop weighted average ET
    annual_et_df *= crop_area_df
    seasonal_et_df *= crop_area_df
    annual_et_df = annual_et_df.sum(axis=1) / crop_area_df.sum(axis=1)
    seasonal_et_df = seasonal_et_df.sum(axis=1) / crop_area_df.sum(axis=1)
    annual_et_df = annual_et_df[annual_et_df.notnull()]
    seasonal_et_df = seasonal_et_df[seasonal_et_df.notnull()]
    cell_plot_func(
        os.path.join(output_ws, 'et_actual.png'),
        cell_geom_dict, annual_et_df.to_dict(), cmap=cm.YlGn, clabel_str='mm',
        title_str='Crop Area Weighted Annual Evapotranspiration',
        **plot_kwargs)
    cell_plot_func(
        os.path.join(output_ws, 'et_seasonal.png'),
        cell_geom_dict, seasonal_et_df.to_dict(),
        cmap=cm.YlGn, clabel_str='mm',
        title_str='Crop Area Weighted Seasonal Evapotranspiration',
        **plot_kwargs)

    # Cleanup
    del crop_area_df, annual_et_df, seasonal_et_df


def cell_plot_func(output_path, geom_dict, data_dict, title_str, clabel_str,
                   extent=None, cmap=None, v_min=None, v_max=None,
                   fig_size=(12, 12), fig_dpi=150, label_flag=False,
                   save_flag=True, show_flag=False, label_size=8):
    """Plot a cell values for a single field with descartes and matplotlib

    Args:
        output_path (str): output file path
        geom_dict (dict): id, shapely geometry object
        data_dict (dict): id, map value
        title_str (str): Text at the top of the figure/map
        clabel_str (str): Text to display next to the colorbar
        extent (list): extent of all geometry objects [minx, miny, maxx, maxy]
        cmap (): colormap
        v_min ():
        v_max ():
        fig_size (tuple): figure size in inches (width, height)
        fig_dpi (int): Figure dots per square inch
        label_flag (bool): If True, label figures with id
        save_flag (bool): If True, save the figure
        show_flag (bool): If True, show the figure
        label_size (int): Label text font size
    """
    logging.info('  {}'.format(output_path))
    # font = matplotlib.font_manager.FontProperties(
    #     ='Comic Sans MS', weight='semibold', size=8)
    font = matplotlib.font_manager.FontProperties(
        family='Tahoma', weight='semibold', size=label_size)
    # font = matplotlib.font_manager.FontProperties(
    #     ='Consolas', weight='semibold', size=7)

    fig = plt.figure(figsize=fig_size)
    ax = fig.add_axes([0.05, 0.05, 0.9, 0.9])
    plt.title(title_str)

    # Assume extent was saved when geometries were read in
    # It could be recomputed from the individual geometries also
    if extent is not None:
        minx, miny, maxx, maxy = extent
        w, h = maxx - minx, maxy - miny
        ax.set_xlim(minx - 0.05 * w, maxx + 0.05 * w)
        ax.set_ylim(miny - 0.05 * h, maxy + 0.05 * h)
        ax.set_aspect(1)
    else:
        logging.debug('  extent not set')
        return False

    # Build colormap
    if cmap:
        if v_min is None:
            v_min = min(data_dict.values())
            logging.debug('    v_min={}'.format(v_min))
        if v_max is None:
            v_max = max(data_dict.values())
            logging.debug('    v_max={}'.format(v_max))
        norm = colors.Normalize(vmin=v_min, vmax=v_max)
        m = cm.ScalarMappable(norm=norm, cmap=cmap)

        # If all values are the same
        #   don't color the patches or draw a colorbar
        # DEADBEEF - If the colorbar values were normalized for all crops
        #   this wouldn't be applicable
        if abs(v_max - v_min) <= 1.:
            cmap, m = None, None

    # Draw patches
    for id, geom_list in geom_dict.items():
        value_str = ''
        hatch = ''
        color = '#EFEFEF'
        try:
            value_str = '{}'.format(int(round(data_dict[id], 0)))
            color = m.to_rgba(data_dict[id])
        except KeyError:
            # Key (CELL_ID) is not in data dictionary
            pass
            # hatch = '/'
        # except ValueError:
        #      Value is NaN
        #
        except TypeError:
            # Value is a string (not a float/int)
            value_str = data_dict[id]
        except AttributeError:
            # Min and max values are identical
            value_str = '{}'.format(int(round(data_dict[id], 0)))
            color = (1.0, 1.0, 0.745, 1.0)
            # color = '#CCCCCC'
            # Display "yellow" color at middle of RdYlBu_r
            # print cm.ScalarMappable(
            #     norm=colors.Normalize(vmin=-1, vmax=1),
            #     cmap=cm.RdYlBu_r).to_rgba(0)
        except:
            print 'Unknown error'
            print id, data_dict[id], '{}'.format(int(round(data_dict[id], 0)))
            print m.to_rgba(data_dict[id])
            continue

        # Write the geometry to the map/figure
        for geom_i, geom in enumerate(geom_list):
            p = ax.add_patch(PolygonPatch(
                geom, fc=color, ec='#808080', lw=0.7, hatch=hatch))

            # Label the patch with the value
            if geom_i == 0 and label_flag and value_str:
                cx, cy = list(geom.centroid.coords)[0]
                ax.annotate(
                    value_str, xy=(cx, cy), ha='center', va='center',
                    color='#262626', fontproperties=font)
    ax.set_xticks([])
    ax.set_yticks([])

    # Colorbar
    if cmap:
        plt.imshow(np.array([[v_min, v_max]]), cmap=cmap)
        cbax = plt.axes([0.085, 0.09, 0.03, 0.30])
        cbar = plt.colorbar(cax=cbax, orientation='vertical')
        cbar.ax.tick_params(labelsize=10)
        cbar.locator = matplotlib.ticker.MaxNLocator(integer=True)
        cbar.update_ticks()
        # cbar.ax.set_major_locator(MaxNLocator(integer=True))
        cbar.set_label(clabel_str)

    if save_flag:
        plt.savefig(output_path, dpi=fig_dpi)
    if show_flag:
        plt.show()

    fig.clf()
    plt.close()
    gc.collect()

    # Plot with shapely/fiona/matplotlib
    # https://gist.github.com/urschrei/6442846
    # cells_mp = MultiPolygon(
    #     'geometry']) for pol in fiona.open(cells_path)])
    #      if pol['properties']['AREA_CODE'] == 'LBO'])
    # fig = plt.figure(1, figsize=(10, 10))
    # ax = fig.add_axes([0.05, 0.05, 0.9, 0.9])
    # # ax = fig.add_subplot(111)
    # minx, miny, maxx, maxy = cells_mp.bounds
    # w, h = maxx - minx, maxy - miny
    # ax.set_xlim(minx - 0.05 * w, maxx + 0.05 * w)
    # ax.set_ylim(miny - 0.05 * h, maxy + 0.05 * h)
    # ax.set_aspect(1)
    # patches = []
    # cm = plt.get_cmap('RdBu')
    # num_colours = len(cells_mp)
    # for idx, p in enumerate(cells_mp):
    #      = cm(1. * idx / num_colours)
    #     .append(PolygonPatch(p, fc='#6699cc', ec='#555555', alpha=1., zorder=1))
    # #     .append(PolygonPatch(p, fc=colour, ec='#555555', alpha=1., zorder=1))
    # ax.add_collection(PatchCollection(patches, match_original=True))
    # ax.set_xticks([])
    # ax.set_yticks([])
    # plt.title("Shapefile polygons rendered using Shapely")
    # # plt.savefig(os.path.join(output_ws, 'plot_test.png'), alpha=True, dpi=300)
    # plt.show()

    # # CartoPy
    # # http://scitools.org.uk/cartopy/docs/latest/matplotlib/intro.html
    # print(cells_path)
    # # cells_shp = shpreader.Reader(cells_path)
    # fig = plt.figure(figsize=(10,10))
    # ax = fig.add_axes([0.05, 0.05, 0.9, 0.9], projection=ccrs.LambertConformal())
    # # ax = plt.axes([0, 0, 1, 1],
    # #              projection=ccrs.LambertConformal())
    # # ax.set_extent([-125, -66.5, 20, 50], ccrs.Geodetic())
    # # ax.background_patch.set_visible(False)
    # # ax.outline_patch.set_visible(False)
    # for cell_geom in shpreader.Reader(cells_path).geometries():
    #      = [0.9375, 0.9375, 0.859375]
    #      = 'black'
    #     .add_geometries([cell_geom], ccrs.PlateCarree(),
    #                      facecolor=facecolor, edgecolor=edgecolor)
    # # ax = plt.axes(projection=ccrs.PlateCarree())
    # # ax.coastlines()
    # plt.show()

    # # Using pyshp to convert the shapefile to geojson
    # # http://geospatialpython.com/2013/07/shapefile-to-geojson.html
    # reader = shapefile.Reader(cells_path)
    # fields = reader.fields[1:]
    # field_names = [field[0] for field in fields]
    # buffer = []
    # for sr in reader.shapeRecords():
    #      = dict(zip(field_names, sr.record))
    #      = sr.shape.__geo_interface__
    #     .append(dict(type="Feature", geometry=geom, properties=atr))
    # # Write the GeoJSON file
    # geojson = open(os.path.join(output_ws, "etcells.json"), "w")
    # geojson.write(dumps({
    #     "type": "FeatureCollection", "features": buffer}, indent=2) + "\n")
    # geojson.close()

    # Using pyshp to convert the shapefile to geojson
    # http://geospatialpython.com/2013/07/shapefile-to-geojson.html
    # fig = plt.figure(figsize=(10,10))
    # ax = fig.add_axes([0.05, 0.05, 0.9, 0.9])
    # reader = shapefile.Reader(cells_path)
    # fields = reader.fields[1:]
    # field_names = [field[0] for field in fields]
    # for item in reader.shapeRecords():
    #      = dict(zip(field_names, item.record))
    #      = item.shape.__geo_interface__
    #      print '\n', item_atr
    #      print item_geom['type']
    #      print len(item_geom['coordinates'])
    #      item_geom['type'] == 'MultiPolygon':
    #        for item_poly in item_geom['coordinates']:
    #            print type(item_poly)
    #            raw_input('ENTER')
    #            ax.add_patch(PolygonPatch(item_poly, fc='#6699cc', ec='#0000ff', alpha=0.5))
    #      item_geom['type'] == 'Polygon':
    #        print type(item_geom)
    #        raw_input('ENTER')
    #        ax.add_patch(PolygonPatch(item_geom, fc='#6699cc', ec='#0000ff', alpha=0.5))
    #     :
    #        logging.error('Invalid geometry type')
    #        continue
    # # ax.set_aspect(1)
    # ax.axis('scaled')
    # plt.show()

    # # Vincent
    # vis = vincent.Map(width=1000, height=1000)
    # #Add the US county data and a new line color
    # vis.geo_data(projection='albersUsa', scale=1000, counties=county_geo)
    # vis + ('2B4ECF', 'marks', 0, 'properties', 'enter', 'stroke', 'value')
    #
    # #Add the state data, remove the fill, write Vega spec output to JSON
    # vis.geo_data(states=state_geo)
    # vis - ('fill', 'marks', 1, 'properties', 'enter')
    # vis.to_json(path)

    # # Plot with basemape
    # map = Basemap(llcrnrlon=-0.5,llcrnrlat=39.8,urcrnrlon=4.,urcrnrlat=43.,
    #             resolution='i', projection='tmerc', lat_0 = 39.5, lon_0 = 1)
    # map.drawmapboundary(fill_color='aqua')
    # map.fillcontinents(color='#ddaa66',lake_color='aqua')
    # map.drawcoastlines()
    # cells_sr = Proj(init='epsg:2227', preserve_units=True)
    # map_sr = Proj(init='EPSG:4326', preserve_units=True)
    # # transform(cells_sr, map_sr, x, y)
    # # Can't read shapefile directly because it is projected
    # map.readshapefile(os.path.splitext(cells_path)[0], 'cells')
    # # Read using fiona and project coordinates
    # with fiona.open(cells_path, "r") as cells_f:
    #      item in cells_f:
    #        item_geom = item['geometry']
    #        for point in item_geom:
    #            x,y = point['geometry']['coordinates']
    #            point['geometry']['coordinates'] = transform(cells_sr, map_sr, x, y)
    #        # print shape(item['geometry'])
    #        print item['properties']
    #        break
    # plt.show()

def parse_args():
    """"""
    parser = argparse.ArgumentParser(
        description='Plot Crop Summary Maps',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        '-i', '--ini', metavar='PATH',
        type=lambda x: util.is_valid_file(parser, x), help='Input file')
    parser.add_argument(
        '--size', default=(12, 12), type=float,
        nargs=2, metavar=('WIDTH', 'HEIGHT'),
        help='Figure size in inches')
    parser.add_argument(
        '--dpi', default=300, type=int, metavar='PIXELS',
        help='Figure dots per square inch')
    parser.add_argument(
        '--no_save', default=True, action='store_false',
        help='Don\'t save maps to disk')
    parser.add_argument(
        '--show', default=False, action='store_true',
        help='Display maps as they are generated')
    parser.add_argument(
        '--label', default=False, action='store_true',
        help='Label maps with zone values')
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
        '--simp', default=None, type=float,
        help='Shapely simplify tolerance (units same as ET Cell)')
    parser.add_argument(
        '--area', default=None, type=float,
        help='Crop area threshold [acres]')
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
    log_f = '{0:<20s} {1}'
    logging.info(log_f.format(
        'Run Time Stamp:', dt.datetime.now().isoformat(' ')))
    logging.info(log_f.format('Current Directory:', os.getcwd()))
    logging.info(log_f.format('Script:', os.path.basename(sys.argv[0])))

    main(ini_path, show_flag=args.show, save_flag=args.no_save,
         figure_size=args.size, figure_dpi=args.dpi, label_flag=args.label,
         start_date=args.start, end_date=args.end, crop_str=args.crops,
         simplify_tol=args.simp, area_threshold=args.area)
