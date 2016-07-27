# plot_future_stats_maps.py
import argparse
from collections import defaultdict
import datetime as dt
import logging
import math
import os
# import re
import sys

from descartes import PolygonPatch
import fiona
# import matplotlib
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.colors as colors
import matplotlib.ticker as ticker
import numpy as np
import pandas as pd
from shapely.geometry import MultiPolygon, Polygon, shape

import util


def main(ini_path, show_flag=False, save_flag=True,
         figure_size=(6.0, 7.5), figure_dpi=600, simplify_tol=None):
    """Plot future statistic maps

    For now, data is stored in excel files in stats_tables folder

    Args:
        ini_path (str): file path of the project INI file

    Returns:
        None
    """

    period_list = [2020, 2050, 2080]
    scenario_list = [5, 25, 50, 75, 95]

    full_value_list = ['et', 'eto', 'niwr', 'ppt', 'rs', 'tmean', 'u']
    sub_value_list = ['et', 'eto', 'niwr', 'ppt', 'tmean']
    # sub_delta_list = ['et', 'eto', 'niwr', 'ppt', 'tmean']
    sub_delta_list = []

    delta_type = {
        'et': 'percent',
        'eto': 'percent',
        'niwr': 'percent',
        'ppt': 'percent',
        'q': 'percent',
        'rs': 'percent',
        'tmean': 'delta',
        'u': 'percent'
    }

    # Adjust data type names in output files
    output_var = {
        'et': 'et',
        'eto': 'eto',
        'niwr': 'niwr',
        'ppt': 'ppt',
        'q': 'tdew',
        'rs': 'rs',
        'tmean': 'tmean',
        'u': 'wind'
    }

    # Figure caption text
    value_text = {
        'et': 'Evapotranspiration [mm]',
        'eto': 'Reference ET [mm/year]',
        'niwr': 'Net Irrigation Water\nRequirement [mm]',
        'ppt': 'Precipitation [mm]',
        'q': 'Specific Humidity [kg/kg]',
        'rs': 'Solar Radiation [W/m^2]',
        'tmean': 'Mean Temperature [C]',
        'u': 'Wind speed [m/s]'
    }
    delta_text = {
        'et': 'Evapotranspiration\nPercent Change [%]',
        'eto': 'Reference ET\nPercent Change [%]',
        'niwr': 'NIWR\nPercent Change [%]',
        'ppt': 'Precipitation\nPercent Change [%]',
        # 'q': 'Specific Humidity\nPercent Change [%]',
        # 'rs': 'Solar Radiation\nPercent Change [%]',
        'tmean': 'Mean Temperature\nDelta [C]'
        # 'u': 'Wind speed\nPercent Change [%]'
    }

    # Colormap
    cmap = {
        'et': {
            'value': 'blue_red',
            'delta': ['red_white', 'white_blue']},
        'eto': {
            'value': 'blue_red',
            'delta': ['red_white', 'white_blue']},
        'niwr': {
            'value': 'blue_red',
            'delta': ['blue_white', 'white_red']},
        'ppt': {
            'value': 'red_blue',
            'delta': ['red_white', 'white_blue']},
        'q': {
            'value': 'blue_red',
            'delta': ['red_white', 'white_blue']},
        'rs': {
            'value': 'blue_red',
            'delta': ['red_white', 'white_blue']},
        'tmean': {
            'value': 'blue_red',
            'delta': ['red_white', 'white_blue']},
        'u': {
            'value': 'blue_red',
            'delta': ['red_white', 'white_blue']}
    }
    color_dict = colordicts_func()
    colormap_dict = colormaps_func(color_dict)

    # Round values/deltas to next multiple of this amount
    base = {
        'et': {'value': 1, 'delta': 1},
        'eto': {'value': 1, 'delta': 1},
        'niwr': {'value': 1, 'delta': 1},
        'ppt': {'value': 1, 'delta': 1},
        'q': {'value': 1, 'delta': 1},
        'rs': {'value': 1, 'delta': 1},
        'tmean': {'value': 1, 'delta': 1},
        'u': {'value': 5, 'delta': 1}
    }

    # ET Cells field names
    cell_id_field = 'CELL_ID'

    # Excel file parameters
    # BasinID should not be in the file name
    full_table_fmt = '{basin_id}_base_{var}.xlsx'
    full_value_tab = 'Sheet1'
    sub_table_fmt = '{basin_id}_future_{var}.xlsx'
    sub_value_tab = 'Values'
    sub_delta_tabs = {
        'delta': 'Difference',
        'percent': 'Percent Difference'
    }
    table_id_field = 'HUC'
    period_field = 'Period'
    scenario_fields = {
        5: '5th percentile',
        25: '25th percentile',
        50: 'Median',
        75: '75th percentile',
        95: '95th percentile'
    }

    # full_table_re = re.compile(
    #     '(?P<basin_id>\w+)_base_(?P<var>\w+).xlsx', re.I)
    # sub_table_re = re.compile(
    #     '(?P<basin_id>\w+)_future_(?P<var>\w+).xlsx', re.I)

    # font = matplotlib.font_manager.FontProperties(
    #     ='Comic Sans MS', weight='semibold', size=8)
    # font = matplotlib.font_manager.FontProperties(
    #     family='Tahoma', weight='semibold', size=label_size)
    # font = matplotlib.font_manager.FontProperties(
    #     ='Consolas', weight='semibold', size=7)


    # Check that the INI file can be read
    logging.info('\nGenerate crop summary maps from daily data')
    logging.info('  INI: {}'.format(ini_path))
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
    basin_id = get_config_param(config, 'basin_id', crop_et_sec)
    project_ws = get_config_param(config, 'project_folder', crop_et_sec)
    cells_path = get_config_param(config, 'cells_path', crop_et_sec)

    stats_ws = os.path.join(project_ws, 'stats_tables')
    output_ws = os.path.join(project_ws, 'stats_maps')

    # Check workspaces
    if not os.path.isdir(stats_ws):
        logging.error(('\nERROR: The stats tables folder {0} ' +
                       'could be found\n').format(stats_ws))
        sys.exit()
    if not os.path.isfile(cells_path):
        logging.error(('\nERROR: The cells shapefile {0} ' +
                       'could be found\n').format(cells_path))
        sys.exit()
    if not os.path.isdir(output_ws):
        os.makedirs(output_ws)


    # Read ET Cells into memory with fiona and shapely
    # Convert multi-polygons to list of polygons
    logging.info('\nReading ET cells shapefile')
    cell_geom_dict = read_cell_geometries(
        cells_path, cell_id_field, simplify_tol)
    cell_extent = read_cell_extent(cells_path)
    if not cell_geom_dict:
        logging.error('  ET Cell shapefile not read in, exiting')
        return False

    # Build master type list
    type_list = sorted(set(full_value_list + sub_value_list + sub_delta_list))

    # Read in all tables
    for var in type_list:
        logging.info('\nVariable: {}'.format(var))
        full_table_name = full_table_fmt.format(
            basin_id=basin_id, var=var)
        logging.info('  {}'.format(full_table_name))
        full_value_df = pd.read_excel(
            os.path.join(stats_ws, full_table_name),
            sheetname=full_value_tab, skiprows=1)
        full_value_df[table_id_field] = full_value_df[table_id_field].astype('str')
        logging.debug('  {}'.format(full_value_tab))
        logging.debug(str(full_value_df.head()) + '\n')

        sub_table_name = sub_table_fmt.format(
            basin_id=basin_id, var=var)
        logging.info('  {}'.format(sub_table_name))
        sub_value_df = pd.read_excel(
            os.path.join(stats_ws, sub_table_name),
            sheetname=sub_value_tab, skiprows=1)
        sub_value_df[table_id_field] = sub_value_df[table_id_field].astype('str')
        logging.debug('  {}'.format(sub_value_tab))
        logging.debug(str(sub_value_df.head()) + '\n')

        # Switch tabs
        sub_delta_df = pd.read_excel(
            os.path.join(stats_ws, sub_table_name),
            sheetname=sub_delta_tabs[delta_type[var]], skiprows=1)
        sub_delta_df[table_id_field] = sub_delta_df[table_id_field].astype('str')
        logging.debug('  {}'.format(sub_delta_tabs[delta_type[var]]))
        logging.debug(str(sub_delta_df.head()) + '\n')

        # Build colorbar ranges
        logging.info('\n  Computing colorbar ranges')

        # Calculate min/max value
        # DEADBEEF - Make this a separate function
        f = scenario_fields.values()
        full_value_min = min(full_value_df[f].values.flatten())
        full_value_max = max(full_value_df[f].values.flatten())
        sub_value_min = min(sub_value_df[f].values.flatten())
        sub_value_max = max(sub_value_df[f].values.flatten())
        sub_delta_min = min(sub_delta_df[f].values.flatten())
        sub_delta_max = max(sub_delta_df[f].values.flatten())

        # Adjust very small negative min deltas
        # if delta_min_negative_override < sub_delta_min < 0:
        #     sub_delta_min = delta_min_negative_override

        # Calculate min/max for value and delta
        full_value_round_min = myround(
            full_value_min, 'floor', base[var]['value'])
        full_value_round_max = myround(
            full_value_max, 'ceil', base[var]['value'])
        sub_value_round_min = myround(
            sub_value_min, 'floor', base[var]['value'])
        sub_value_round_max = myround(
            sub_value_max, 'ceil', base[var]['value'])
        sub_delta_round_min = myround(
            sub_delta_min, 'floor', base[var]['delta'])
        sub_delta_round_max = myround(
            sub_delta_max, 'ceil', base[var]['delta'])

        # Print min/max value
        logging.info('    Full Value Min: {0:>10.2f} {1:>10}'.format(
            full_value_min, full_value_round_min))
        logging.info('    Full Value Max: {0:>10.2f} {1:>10}'.format(
            full_value_max, full_value_round_max))
        logging.info('    Sub Value Min:  {0:>10.2f} {1:>10}'.format(
            sub_value_min, sub_value_round_min))
        logging.info('    Sub Value Max:  {0:>10.2f} {1:>10}'.format(
            sub_value_max, sub_value_round_max))
        logging.info('    Sub Delta Min:  {0:>10.2f} {1:>10}'.format(
            sub_delta_min, sub_delta_round_min))
        logging.info('    Sub Delta Max:  {0:>10.2f} {1:>10}'.format(
            sub_delta_max, sub_delta_round_max))

        # Min/Max values will be the same across fullplots and subplots
        match_colorbar_flag = True
        if match_colorbar_flag:
            full_value_round_min = min(
                full_value_round_min, sub_value_round_min)
            full_value_round_max = max(
                full_value_round_max, sub_value_round_max)
            sub_value_round_min = min(
                full_value_round_min, sub_value_round_min)
            sub_value_round_max = max(
                full_value_round_max, sub_value_round_max)

        # Adjust min/max for subplot delta colorbars
        # This is so transition rate is the same for neg./pos.
        sub_delta_mod_min = min(
            sub_delta_round_min, -sub_delta_round_max)
        sub_delta_mod_max = max(
            -sub_delta_round_min, sub_delta_round_max)
        logging.info('    Sub Delta Mod Min: {0:>7.2f} {1:>10}'.format(
            sub_delta_min, sub_delta_mod_min))
        logging.info('    Sub Delta Mod Max: {0:>7.2f} {1:>10}'.format(
            sub_delta_max, sub_delta_mod_max))
        zero_pct = percent_func(
            sub_delta_round_min, sub_delta_round_max, 0)
        min_pct = percent_func(
            0, -sub_delta_mod_min, -sub_delta_round_min)
        max_pct = percent_func(
            0, sub_delta_mod_max, sub_delta_round_max)
        logging.info('    0%: {0:4.2f}  Min%: {1:4.2f}  Max%: {2:4.2f}'.format(
            zero_pct, min_pct, max_pct))

        # Keyword arguments to plotting functions
        full_kwargs = {
            'table_id_field': table_id_field,
            'scenario_field': scenario_fields[50],
            'cell_geom_dict': cell_geom_dict,
            'cell_extent': cell_extent,
            'figure_size': figure_size,
            'figure_dpi': figure_dpi,
            'save_flag': save_flag,
            'show_flag': show_flag
        }
        sub_kwargs = {
            'period_list': period_list,
            'scenario_list': scenario_list,
            'table_id_field': table_id_field,
            'period_field': period_field,
            'scenario_fields': scenario_fields,
            'cell_geom_dict': cell_geom_dict,
            'cell_extent': cell_extent,
            'figure_size': figure_size,
            'figure_dpi': figure_dpi,
            'save_flag': save_flag,
            'show_flag': show_flag
        }

        # Build full value plots
        if var in full_value_list:
            output_name = 'fullplot_{}_value.jpg'.format(output_var[var])
            output_path = os.path.join(output_ws, output_name)
            full_plot(
                output_path, full_value_df, caption=value_text[var],
                cmap=colormap_dict[cmap[var]['value']],
                v_min=full_value_round_min, v_max=full_value_round_max,
                **full_kwargs)

        # Build sub value plots
        if var in sub_value_list:
            output_name = 'subplot_{}_value.jpg'.format(output_var[var])
            output_path = os.path.join(output_ws, output_name)
            sub_plot(
                output_path, sub_value_df, caption=value_text[var],
                cmap=colormap_dict[cmap[var]['value']],
                v_min=sub_value_round_min, v_max=sub_value_round_max,
                **sub_kwargs)

        # Build sub delta plots
        if var in sub_delta_list:
            output_name = 'subplot_{}_delta.jpg'.format(output_var[var])
            output_path = os.path.join(output_ws, output_name)
            sub_plot(
                output_path, sub_delta_df, caption=delta_text[var],
                cmap=colormap_dict[cmap[var]['delta']],
                v_min=sub_delta_mod_min, v_max=sub_delta_mod_max,
                **sub_kwargs)


def full_plot(output_path, data_df, caption, cmap, v_min, v_max,
              cell_geom_dict, cell_extent,
              table_id_field, scenario_field,
              figure_size, figure_dpi, show_flag, save_flag):
    # Build the figure and subplots
    fig, axes = plt.subplots(1, 1, figsize=figure_size)

    # Position the subplots in the figure
    plt.subplots_adjust(
        left=0.02, bottom=0.08, right=0.99, top=0.97,
        wspace=0.001, hspace=0.001)

    # Remove all ticks and ticklabels
    plt.setp(axes, xticks=[], yticks=[])

    # Adjust cell extent to match axes aspect ratio
    # Assume all subplots are the same size
    minx, miny, maxx, maxy = adjust_extent_to_axes(
        cell_extent, axes, pad=0.02)
    plt.setp(axes, xlim=[minx, maxx], ylim=[miny, maxy])

    # Draw subplots
    cell_data_dict = dict(zip(
        data_df[table_id_field], data_df[scenario_field]))
    plot_cells_func(
        axes, cell_geom_dict, cell_data_dict,
        cmap=cm.jet, v_min=v_min, v_max=v_max)

    # Add caption text
    plt.figtext(0.65, 0.07, caption, size=11, ha='left', va='top')

    # Add a basic colorbar
    ax = fig.add_axes([0.1, 0.1, 0.8, 0.8])
    plt.imshow(np.array([[v_min, v_max]]), cmap=cmap)
    ax.set_visible(False)
    cax = plt.axes([0.02, 0.04, 0.55, 0.03])
    cbar = plt.colorbar(
        cax=cax, orientation='horizontal', ticks=None)
    cbar.locator = ticker.MaxNLocator(nbins=8, integer=True)
    cbar.update_ticks()
    cbar.ax.tick_params(labelsize=8)
    # cbar.set_label(units_label)

    if save_flag:
        plt.savefig(output_path, dpi=figure_dpi)
    if show_flag:
        plt.show()

    fig.clf()
    plt.close()
    # gc.collect()


def sub_plot(output_path, data_df, caption, cmap, v_min, v_max,
             cell_geom_dict, cell_extent, period_list, scenario_list,
             table_id_field, period_field, scenario_fields,
             figure_size, figure_dpi, show_flag, save_flag):
    # Build the figure and subplots
    fig, axes = plt.subplots(
        len(scenario_list), len(period_list), figsize=figure_size)

    # Position the subplots in the figure
    plt.subplots_adjust(
        left=0.05, bottom=0.08, right=0.99, top=0.97,
        wspace=0.001, hspace=0.001)

    # Remove all ticks and ticklabels
    plt.setp(axes, xticks=[], yticks=[])

    # Adjust cell extent to match axes aspect ratio
    # Assume all subplots are the same size
    minx, miny, maxx, maxy = adjust_extent_to_axes(
        cell_extent, axes[0, 0], pad=0.02)
    plt.setp(axes, xlim=[minx, maxx], ylim=[miny, maxy])

    # Set common row and column titles/labels
    for ax, period in zip(axes[0], period_list):
        ax.set_title(period, size='12')
    for ax, scenario in zip(axes[:, 0], scenario_list):
        ax.set_ylabel(scenario, ha='right', rotation=0, size='12')

    # Draw subplots
    for i, scenario in enumerate(scenario_list):
        for j, period in enumerate(period_list):
            sub_df = data_df[data_df[period_field] == period]
            cell_data_dict = dict(zip(
                sub_df[table_id_field],
                sub_df[scenario_fields[scenario]]))
            plot_cells_func(
                axes[i, j], cell_geom_dict, cell_data_dict,
                cmap=cm.jet, v_min=v_min, v_max=v_max)

    # Add caption text
    plt.figtext(0.65, 0.07, caption, size=11, ha='left', va='top')

    # Add a basic colorbar
    ax = fig.add_axes([0.1, 0.1, 0.8, 0.8])
    plt.imshow(np.array([[v_min, v_max]]), cmap=cmap)
    ax.set_visible(False)
    cax = plt.axes([0.05, 0.04, 0.55, 0.03])
    cbar = plt.colorbar(
        cax=cax, orientation='horizontal', ticks=None)
    cbar.locator = ticker.MaxNLocator(nbins=8, integer=True)
    cbar.update_ticks()
    cbar.ax.tick_params(labelsize=8)
    # cbar.set_label(units_label)

    if save_flag:
        plt.savefig(output_path, dpi=figure_dpi)
    if show_flag:
        plt.show()

    fig.clf()
    plt.close()
    # gc.collect()


def colordicts_func():
    color_dict = {}
    color_dict['green_red'] = {
        'red': ((0.0, 0.22, 0.22), (0.5, 1.0, 1.0), (1.0, 1.0, 1.0)),
        'green': ((0.0, 0.66, 0.66), (0.5, 1.0, 1.0), (1.0, 0.0, 0.0)),
        'blue': ((0.0, 0.0, 0.0), (0.5, 0.0, 0.0), (1.0, 0.0, 0.0))}
    color_dict['red_green'] = {
        'red': ((0.0, 1.0, 1.0), (0.5, 1.0, 1.0), (1.0, 0.22, 0.2)),
        'green': ((0.0, 0.0, 0.0), (0.5, 1.0, 1.0), (1.0, 0.66, 0.65)),
        'blue': ((0.0, 0.0, 0.0), (0.5, 0.0, 0.0), (1.0, 0.0, 0.0))}
    color_dict['blue_red'] = {
        'red': ((0., 0., 0.), (0.333, 0., 0.), (0.667, 1., 1.), (1., 1., 1.)),
        'green': ((0., 0., 0.), (0.333, 1., 1.), (0.667, 1., 1.), (1., 0., 0.)),
        'blue': ((0., 1., 1.), (0.333, 1., 1.), (0.667, 0., 0.), (1., 0., 0.))}
    color_dict['red_blue'] = {
        'red': ((0., 1., 1.), (0.333, 1., 1.), (0.667, 0., 0.), (1., 0., 0.)),
        'green': ((0., 0., 0.), (0.333, 1., 1.), (0.667, 1., 1.), (1., 0., 0.)),
        'blue': ((0., 0., 0.), (0.333, 0., 0.), (0.667, 1., 1.), (1., 1., 1.))}
    color_dict['white_blue'] = {
        'red': ((0., 1., 1.), (1., 0., 0.)),
        'green': ((0., 1., 1.), (1., 0., 0.)),
        'blue': ((0., 1., 1.), (1., 1., 1.))}
    color_dict['white_red'] = {
        'red': ((0., 1., 1.), (1., 1., 1.)),
        'green': ((0., 1., 1.), (1., 0., 0.)),
        'blue': ((0., 1., 1.), (1., 0., 0.))}
    color_dict['blue_white'] = {
        'red': ((0., 0., 0.), (1., 1., 1.)),
        'green': ((0., 0., 0.), (1., 1., 1.)),
        'blue': ((0., 1., 1.), (1., 1., 1.))}
    color_dict['red_white'] = {
        'red': ((0., 1., 1.), (1., 1., 1.)),
        'green': ((0., 0., 0.), (1., 1., 1.)),
        'blue': ((0., 0., 0.), (1., 1., 1.))}
    return color_dict


def colormaps_func(color_dict):
    return {
        name: colors.LinearSegmentedColormap(
            name, color, 256)
        for name, color in color_dict.items()
    }


def myround(x, direction='round', base=5):
    if direction == 'floor':
        return base * math.floor(float(x) / base)
    elif direction == 'ceil':
        return base * math.ceil(float(x) / base)
    else:
        return base * round(float(x) / base)


def percent_func(min_value, max_value, test_value=0):
    """Return the percent of a test value between a min and max"""
    if min_value > max_value:
        logging.error('Min less than max, exiting')
        sys.exit()
    elif test_value <= min_value:
        return 0.
    elif test_value >= max_value:
        return 1.
    else:
        return (float(test_value - min_value) / (max_value - min_value))


def read_cell_geometries(cells_path, cell_id_field, simplify_tol=None):
    """"""
    cell_geom_dict = defaultdict(list)
    # cell_data_dict = dict()
    with fiona.open(cells_path, "r") as cell_f:
        # Fiona is printing a debug statement here "Index: N"
        for item in cell_f:
            cell_id = item['properties'][cell_id_field]
            # cell_data_dict[cell_id] = item['properties']

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
    return cell_geom_dict


def read_cell_extent(cells_path):
    """"""
    cell_extent = []
    with fiona.open(cells_path, "r") as cell_f:
        cell_extent = cell_f.bounds[:]
    return cell_extent


def adjust_extent_to_axes(cell_extent, ax, pad=0):
    """Adjust cell extent to match axes aspect ratio"""
    # Get axes extent and aspect ratio
    ax_bbox = ax.get_window_extent()
    ax_width, ax_height = ax_bbox.width, ax_bbox.height
    ax_aspect = float(ax_width) / ax_height

    # Adjust extent to the axes aspect ratio
    # This will keep the units the same in the x and y
    minx, miny, maxx, maxy = cell_extent
    w, h = maxx - minx, maxy - miny
    if (float(w) / h) < ax_aspect:
        # Increase cell width
        minx = minx + 0.5 * w - 0.5 * h * ax_aspect
        maxx = maxx - 0.5 * w + 0.5 * h * ax_aspect
    else:
        # Increase cell height
        miny = miny + 0.5 * h - 0.5 * w / ax_aspect
        maxy = maxy - 0.5 * h + 0.5 * w / ax_aspect
    # Pad a percentage of the maximum dimension
    if pad:
        minx -= pad * max(w, h)
        maxx += pad * max(w, h)
        miny -= pad * max(w, h)
        maxy += pad * max(w, h)
    return minx, miny, maxx, maxy


def plot_cells_func(ax, geom_dict, data_dict,
                    cmap=None, v_min=None, v_max=None,
                    label_flag=False, label_size=8):
    """Plot a cell values for a single field with descartes and matplotlib

    Args:
        ax:
        geom_dict (dict): id, shapely geometry object
        data_dict (dict): id, map value
        cmap (): colormap
        v_min ():
        v_max ():
        label_flag (bool): If True, label figures with id
        label_size (int): Label text font size
    """

    # Set colormap
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
    return True


def parse_args():
    """"""
    parser = argparse.ArgumentParser(
        description='Plot Future Stats Maps',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        '-i', '--ini', metavar='PATH',
        type=lambda x: util.is_valid_file(parser, x), help='Input file')
    parser.add_argument(
        '--size', default=(6.0, 7.5), type=float,
        nargs=2, metavar=('WIDTH', 'HEIGHT'),
        help='Figure size in inches')
    parser.add_argument(
        '--dpi', default=600, type=int, metavar='PIXELS',
        help='Figure dots per square inch')
    parser.add_argument(
        '--no_save', default=True, action='store_false',
        help='Don\'t save maps to disk')
    parser.add_argument(
        '--show', default=False, action='store_true',
        help='Display maps as they are generated')
    # parser.add_argument(
    #     '--label', default=False, action='store_true',
    #     help='Label maps with zone values')
    # parser.add_argument(
    #     '--start', default=None, type=util.valid_date,
    #     help='Start date (format YYYY-MM-DD)', metavar='DATE')
    # parser.add_argument(
    #     '--end', default=None, type=util.valid_date,
    #     help='End date (format YYYY-MM-DD)', metavar='DATE')
    # parser.add_argument(
    #     '-c', '--crops', default='', type=str,
    #     help='Comma separate list or range of crops to compare')
    parser.add_argument(
        '--simp', default=None, type=float,
        help='Shapely simplify tolerance (units same as ET Cell)')
    # parser.add_argument(
    #     '--area', default=None, type=float,
    #     help='Crop area threshold [acres]')
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
         figure_size=args.size, figure_dpi=args.dpi, simplify_tol=args.simp)
