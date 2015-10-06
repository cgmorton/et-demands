#--------------------------------
# Name:         plot_crop_summary_maps.py
# Purpose:      Plot crop summary maps
# Author:       Charles Morton
# Created       2015-10-05
# Python:       2.7
#--------------------------------

import argparse
import calendar
from collections import defaultdict
import datetime as dt
import gc
import logging
import math
import os
import re
import sys
from time import clock

from descartes import PolygonPatch
import fiona
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.colors as colors
from matplotlib.collections import PatchCollection
import numpy as np
import pandas as pd
from shapely.geometry import MultiPolygon, Polygon, shape

import util

##import geojson
##import json
##import cartopy.crs as ccrs
##import cartopy.io.shapereader as shpreader
##from fiona.crs import to_string
##from mpl_toolkits.basemap import Basemap, maskoceans
##from pyproj import Proj, transform
##import shapefile
##import vincent

matplotlib.rc('font', family='sans-serif')
##matplotlib.rc('font', family='cursive')
##matplotlib.rc('font', family='monospace') 

################################################################################

def main(ini_path, show_flag=False, save_flag=True, label_flag=False,
         figure_size=(12,12), figure_dpi=150, start_date=None, end_date=None,
         crop_str='', simplify_tol=None, overwrite_flag=False):
    """Plot full daily data by crop

    Args:
        ini_path (str): file path of the project INI file
        show_flag (bool): if True, show maps
        save_flag (bool): if True, save maps to disk
        label_flag (bool): if True, label maps with cell values
        figure_size (tuple): width, height of figure in pixels
        start_date (str): ISO format date string (YYYY-MM-DD)
        end_date (str): ISO format date string (YYYY-MM-DD)
        crop_str (str): comma separate list or range of crops to compare
        simplify_tol (float): simplify tolerance (in the units of ET Cells?)
        overwrite_flag (bool): If True, overwrite existing files

    Returns:
        None
    """

    ## Input/output names
    ##input_folder = 'daily_stats'
    ##output_folder = 'daily_plots'

    ## Only process a subset of the crops
    crop_keep_list = list(util.parse_int_set(crop_str))
    ## These crops will not be processed (if set)
    crop_skip_list = [44, 45, 46]

    ## ET Cells field names
    cell_id_field = 'CELL_ID'
    crop_area_field = 'AG_ACRES'
    
    ## Input field names
    date_field   = 'Date'
    doy_field    = 'DOY'
    year_field   = 'Year'
    ##month_field  = 'Month'
    ##day_field    = 'Day'
    ##pmeto_field  = 'PMETo'
    ##precip_field = 'PPT'
    ##t30_field    = 'T30'
    etact_field  = 'ETact'
    ##etpot_field  = 'ETpot'
    ##etbas_field  = 'ETbas'
    ##irrig_field  = 'Irrigation'
    season_field = 'Season'
    ##runoff_field = 'Runoff'
    ##dperc_field = 'DPerc'
    ##niwr_field = 'NIWR'
    ##kc_field = 'Kc'
    ##kcb_field = 'Kcb'
    
    ## Output field names
    annual_et_field = 'Annual_ET'
    seasonal_et_field = 'Seasonal_ET'
    gs_start_doy_field = 'Start_DOY'
    gs_end_doy_field = 'End_DOY'
    gs_length_field = 'GS_Length'

    ## Number of header lines in data file
    header_lines = 2

    ## Additional figure controls
    ##figure_dynamic_size = False
    ##figure_ylabel_size = '12pt'

    ## Delimiter
    sep = ','
    ##sep = r"\s*"
    
    daily_input_re = re.compile(
        '(?P<cell_id>\w+)_daily_crop_(?P<crop_num>\d{2}).csv', re.I)
    gs_input_re = re.compile(
        '(?P<cell_id>\w+)_gs_crop_(?P<crop_num>\d{2}).csv', re.I)

    ########################################################################

    logging.info('\nPlot mean daily data by crop')        
    logging.info('  INI: {}'.format(ini_path))

    ## Check that the INI file can be read
    crop_et_sec = 'CROP_ET'
    config = util.read_ini(ini_path, crop_et_sec)
    
    ## Get the project workspace and daily ET folder from the INI file
    try:
        et_cells_path = config.get(crop_et_sec, 'et_cells_path')
    except:
        logging.error(
            'ERROR: The et_cells_path '+
            'parameter is not set in the INI file')
        sys.exit()
        
    try:
        project_ws = config.get(crop_et_sec, 'project_folder')
    except:
        logging.error(
            'ERROR: The project_folder '+
            'parameter is not set in the INI file')
        sys.exit()
        
    try:
        daily_stats_ws = os.path.join(
            project_ws, config.get(crop_et_sec, 'daily_output_folder'))
    except:
        logging.error(
            'ERROR: The daily_output_folder '+
            'parameter is not set in the INI file')
        sys.exit()
        
    ##try:
    ##    gs_stats_ws = os.path.join(
    ##        project_ws, config.get(crop_et_sec, 'gs_output_folder'))
    ##except:
    ##    logging.info(
    ##        '  The gs_output_folder parameter is not set in the INI file\n'+
    ##        '  Growing season stats will be computed from the dailies\n')
    ##    gs_stats_ws = None
        
    try:
        output_ws = os.path.join(
            project_ws, config.get(crop_et_sec, 'summary_maps_folder'))
    except:
        if 'stats' in input_ws:
            output_ws = input_ws.replace('stats', 'maps')
        else:
            output_ws = os.path.join(project_ws, 'summary_maps_folder')

    ## Check workspaces
    if not os.path.isdir(daily_stats_ws):
        logging.error(('\nERROR: The daily ET stats folder {0} '+
                       'could be found\n').format(daily_stats_ws))
        sys.exit()
    if not os.path.isfile(et_cells_path):
        logging.error(('\nERROR: The et_cells shapefile {0} '+
                       'could be found\n').format(et_cells_path))
        sys.exit()
    ##if gs_stats_ws and not os.path.isdir(gs_stats_ws):
    ##    logging.info(
    ##        ('  The growing seasons stats folder {0} could be found\n'+
    ##         '  Growing season stats will be computed '+
    ##         'from the dailies\n').format(gs_stats_ws))
    ##    gs_stats_ws = None
    if not os.path.isdir(output_ws):
        os.mkdir(output_ws)

    ## Range of data to plot
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
    if year_start and year_end and year_end <= year_start:
        logging.error('\n  ERROR: End date must be after start date\n')
        sys.exit()

    ## Build list of all daily ET files
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
        elif crop_keep_list and crop_num not in crop_keep_list:
            continue
        else:
            daily_path_dict[crop_num][cell_id] = os.path.join(daily_stats_ws, f_name)   
    if not daily_path_dict:
        logging.error(
            '  ERROR: No daily ET files were found\n'+
            '  ERROR: Check the folder_name parameters\n')
        sys.exit()

        
    ## Read ET Cells into memory with fiona and shapely
    ## Convert multi-polygons to list of polygons
    cell_geom_dict = defaultdict(list)
    cell_data_dict = dict()
    cell_extent = []
    with fiona.open(et_cells_path, "r") as cell_f:
        cell_extent = cell_f.bounds[:]
        for item in cell_f:
            cell_id = item['properties'][cell_id_field]
            cell_data_dict[cell_id] = item['properties']
            
            ## Simplify the geometry
            if simplify_tol is not None:
                item_geom = shape(item['geometry']).simplify(
                    simplify_tol, preserve_topology=False)
            else:
                item_geom = shape(item['geometry'])
                
            ## Unpack multipolygons to lists of polygons
            if item_geom.is_empty:
                continue
            elif item_geom.geom_type == 'MultiPolygon':
                for item_poly in item_geom:
                    if item_poly.is_empty:
                        continue
                    cell_geom_dict[cell_id].append(item_poly)
            elif item_geom.geom_type == 'Polygon':
                cell_geom_dict[cell_id].append(item_geom)
            else:
                logging.error('Invalid geometry type')
                continue
    if not cell_geom_dict:
        logging.error('ET Cell shapefile not read in')
        sys.exit()

    
    ## Plot total CDL crop acreages
    logging.info('\nPlotting total crop acreage')
    crop_area_dict = {k:v[crop_area_field] for k,v in cell_data_dict.iteritems()}
    cell_plot_func(
        os.path.join(output_ws, 'total_crop_acreage.png'),
        cell_geom_dict, crop_area_dict, extent=cell_extent,
        cmap=cm.YlGn, title_str='Total CDL Crop Area', clabel_str='acres',
        fig_size=figure_size, fig_dpi=figure_dpi,
        save_flag=save_flag, show_flag=show_flag, label_flag=False)

        
    ## First process by crop
    logging.debug('')
    for crop_num in sorted(daily_path_dict.keys()):
        logging.info('Crop Num: {0:2d}'.format(crop_num))
                
        ## Build an empty dataframe to write to
        output_df = pd.DataFrame({
            cell_id_field:sorted(daily_path_dict[crop_num].keys()), 
            annual_et_field:None, 
            seasonal_et_field:None, 
            gs_start_doy_field:None, 
            gs_end_doy_field:None, 
            gs_length_field:None})
        output_df.set_index(cell_id_field, inplace=True)
        
        test_clock = clock()
        for cell_id, input_path in sorted(daily_path_dict[crop_num].items()):
            logging.debug('  Cell ID:   {0}'.format(cell_id))
 
            ## Get crop name
            with open(input_path, 'r') as file_f:
                crop_name = file_f.readline().split('-',1)[1].strip()
                logging.debug('  Crop:      {0}'.format(crop_name))
            logging.debug('  {0}'.format(os.path.basename(input_path)))
            
            ## Read data from file into record array (structured array)
            daily_df = pd.read_table(input_path, header=0, comment='#', sep=sep)  
            logging.debug('\nFields: \n{0}'.format(daily_df.columns.values))
            daily_df[date_field] = pd.to_datetime(daily_df[date_field])
            daily_df.set_index('Date', inplace=True)
            
            ## Build list of unique years
            year_array = np.sort(np.unique(np.array(daily_df[year_field]).astype(np.int)))
            logging.debug('\nAll Years: \n{0}'.format(year_array.tolist()))
            
            ## Only keep years between year_start and year_end
            if year_start:
                crop_year_start = year_start
                daily_df = daily_df[daily_df[year_field] >= year_start]
                crop_year_start = max(year_end, year_array[0])
            else:
                crop_year_start = year_array[0]
            if year_end:
                daily_df = daily_df[daily_df[year_field] <= year_end]
                crop_year_end = min(year_end, year_array[-1])
            else:
                crop_year_end = year_array[-1]
            year_sub_array = np.sort(np.unique(np.array(daily_df[year_field]).astype(np.int)))
            logging.debug('\nPlot Years: \n{0}'.format(year_sub_array.tolist()))
            
            ## Seasonal/Annual ET
            seasonal_df = daily_df[daily_df[season_field] > 0].resample(
                'AS', how={etact_field:np.sum})
            annual_df = daily_df.resample('AS', how={etact_field:np.sum})     
            
            ## Compute growing season start/end from dailies
            ## gs_path_dict is None:
            gs_df = daily_df.resample('AS', how={year_field:np.mean})
            gs_df[gs_start_doy_field] = None
            gs_df[gs_end_doy_field] = None
            gs_df[gs_length_field] = None
            for year_i, (year, group) in enumerate(daily_df.groupby([year_field])):
                ##if year_i == 0:
                ##    logging.debug('  Skipping first year')
                ##    continue
                if not np.any(group[season_field].values):
                    logging.debug('  Skipping, season flag was never set to 1')
                    continue
                else:
                    season_diff = np.diff(group[season_field].values)
                    try:
                        start_i = np.where(season_diff == 1)[0][0] + 1
                        gs_df.set_value(
                            group.index[0], gs_start_doy_field, int(group.ix[start_i, doy_field]))
                    except:
                        gs_df.set_value(
                            group.index[0], gs_start_doy_field, int(min(group[doy_field].values)))
                    try:
                        end_i = np.where(season_diff == -1)[0][0] + 1
                        gs_df.set_value(
                            group.index[0], gs_end_doy_field, int(group.ix[end_i, doy_field]))
                    except:
                        gs_df.set_value(
                            group.index[0], gs_end_doy_field, int(max(group[doy_field].values)))
                    del season_diff
                gs_df.set_value(
                    group.index[0], gs_length_field, int(sum(group[season_field].values)))

            output_df.set_value(cell_id, seasonal_et_field, float(seasonal_df.mean()))
            output_df.set_value(cell_id, annual_et_field, float(annual_df.mean()))
            output_df.set_value(cell_id, gs_start_doy_field, float(gs_df[gs_start_doy_field].mean()))
            output_df.set_value(cell_id, gs_end_doy_field, float(gs_df[gs_end_doy_field].mean()))
            output_df.set_value(cell_id, gs_length_field, float(gs_df[gs_length_field].mean()))
            
            ## Cleanup
            del daily_df, seasonal_df, annual_df

            
        ## Make the maps
        logging.debug('')
        title_base = 'Crop {0:02d} - {1} - '.format(crop_num, crop_name)

        ## Crop acreages
        crop_area_dict = {k:v['CROP_{0:02d}'.format(crop_num)] 
                          for k,v in cell_data_dict.iteritems()
                          if k in daily_path_dict[crop_num].keys()}
        cell_plot_func(
            os.path.join(output_ws, 'crop_{0:02d}_acreage.png'.format(crop_num)),
            cell_geom_dict, crop_area_dict, extent=cell_extent,
            cmap=cm.YlGn, title_str=title_base + 'CDL Area', 
            clabel_str='acres', fig_size=figure_size, fig_dpi=figure_dpi,
            save_flag=save_flag, show_flag=show_flag, label_flag=label_flag)

        ## Annual/Seasonal ET
        cell_plot_func(
            os.path.join(output_ws, 'crop_{0:02d}_et_actual.png'.format(crop_num)), 
            cell_geom_dict, output_df[annual_et_field].to_dict(), 
            extent=cell_extent, cmap=cm.YlGn, clabel_str='mm', 
            title_str=title_base + 'Annual Evapotranspiration'.format(crop_num, crop_name), 
            fig_size=figure_size, fig_dpi=figure_dpi, 
            save_flag=save_flag, show_flag=show_flag, label_flag=label_flag)
        cell_plot_func(
            os.path.join(output_ws, 'crop_{0:02d}_et_seasonal.png'.format(crop_num)), 
            cell_geom_dict, output_df[seasonal_et_field].to_dict(), 
            extent=cell_extent, cmap=cm.YlGn, clabel_str='mm', 
            title_str=title_base + 'Seasonal Evapotranspiration'.format(crop_num, crop_name), 
            fig_size=figure_size, fig_dpi=figure_dpi, 
            save_flag=save_flag, show_flag=show_flag, label_flag=label_flag)
            
        ## Growing Season Start/End/Length
        cell_plot_func(
            os.path.join(output_ws, 'crop_{0:02d}_gs_start_doy.png'.format(crop_num)), 
            cell_geom_dict, output_df[gs_start_doy_field].to_dict(), 
            extent=cell_extent, cmap=cm.RdYlBu, clabel_str='Day of Year', 
            title_str=title_base + 'Growing Season Start'.format(crop_num, crop_name), 
            fig_size=figure_size, fig_dpi=figure_dpi, 
            save_flag=save_flag, show_flag=show_flag, label_flag=label_flag)
        cell_plot_func(
            os.path.join(output_ws, 'crop_{0:02d}_gs_end_doy.png'.format(crop_num)), 
            cell_geom_dict, output_df[gs_end_doy_field].to_dict(), 
            extent=cell_extent, cmap=cm.RdYlBu_r, clabel_str='Day of Year', 
            title_str=title_base + 'Growing Season End'.format(crop_num, crop_name), 
            fig_size=figure_size, fig_dpi=figure_dpi, 
            save_flag=save_flag, show_flag=show_flag, label_flag=label_flag)
        cell_plot_func(
            os.path.join(output_ws, 'crop_{0:02d}_gs_length.png'.format(crop_num)), 
            cell_geom_dict, output_df[gs_length_field].to_dict(), 
            extent=cell_extent, cmap=cm.RdYlBu_r, clabel_str='Days', 
            title_str=title_base + 'Growing Season Length'.format(crop_num, crop_name), 
            fig_size=figure_size, fig_dpi=figure_dpi, 
            save_flag=save_flag, show_flag=show_flag, label_flag=label_flag)
        
        ## Cleanup
        del output_df
        gc.collect()
        

################################################################################

def cell_plot_func(output_path, geom_dict, data_dict, title_str, clabel_str, 
                   extent=None, cmap=cm.jet, v_min=None, v_max=None,
                   fig_size=(12,12), fig_dpi=150, label_flag=False,
                   save_flag=True, show_flag=False):
    """Plot a cell values for a single field with descartes and matplotlib
    
    Args:
        plot_path (str): output file path
        cell_geom_dict (dict): id, shapely geometry object
        cell_data_dict (dict): id, map value
        title_str (str): Text at the top of the figure/map
        clabel_str (str): Text to display next to the colorbar
        extent (list): extent of all geometry objects [minx, miny, maxx, maxy]
        cmap (): colormap
        fig_size (tuple): figure size in inches (width, height)
        fig_dpi (int): Figure dots per square inch
        save_flag (bool): If True, save the figure
        show_flag (bool): If True, show the figure
    """
    logging.info('  {}'.format(output_path))
    ##font = matplotlib.font_manager.FontProperties(
    ##    family='Comic Sans MS', weight='semibold', size=8)
    font = matplotlib.font_manager.FontProperties(
        family='Tahoma', weight='semibold', size=8)
    ##font = matplotlib.font_manager.FontProperties(
    ##    family='Consolas', weight='semibold', size=7)

    
    fig = plt.figure(figsize=fig_size)
    ax = fig.add_axes([0.05, 0.05, 0.9, 0.9])
    plt.title(title_str)

    ## Assume extent was saved when geometries were read in
    ## It could be recomputed from the individual geometries also
    if extent is not None:
        minx, miny, maxx, maxy = extent
        w, h = maxx - minx, maxy - miny
        ax.set_xlim(minx - 0.05 * w, maxx + 0.05 * w)
        ax.set_ylim(miny - 0.05 * h, maxy + 0.05 * h)
        ax.set_aspect(1)
    else:
        logging.debug('  extent not set')
        return False
    
    ## Build colormap
    if v_min is None:
        v_min = min(data_dict.values())
        logging.debug('    v_min={}'.format(v_min))
    if v_max is None:
        v_max = max(data_dict.values())
        logging.debug('    v_min={}'.format(v_max))
    norm = colors.Normalize(vmin=v_min, vmax=v_max)
    m = cm.ScalarMappable(norm=norm, cmap=cmap)
    
    ## Draw patches
    for id, geom_list in geom_dict.items():
        try: 
            value_str = '{}'.format(int(round(data_dict[id],0)))
            color = m.to_rgba(data_dict[id])
            hatch = ''
        except: 
            value_str = ''
            color = '#EFEFEF'
            hatch = ''
            ##hatch = '/'

        ## Write the geometry to the map/figure
        for geom_i, geom in enumerate(geom_list):
            p = ax.add_patch(PolygonPatch(
                geom, fc=color, ec='#808080', lw=0.8, hatch=hatch))
                
            ## Label the patch with the value
            if geom_i == 0 and label_flag and value_str:
                cx, cy = list(geom.centroid.coords)[0]
                ax.annotate(
                    value_str, xy=(cx, cy), ha='center', va='center',
                    color='#262626', fontproperties=font)
    ax.set_xticks([])
    ax.set_yticks([])

    ## Colorbar
    plt.imshow(np.array([[v_min, v_max]]), cmap=cmap)
    cbax = plt.axes([0.085, 0.09, 0.03, 0.30])
    cbar = plt.colorbar(cax=cbax, orientation='vertical')
    cbar.ax.tick_params(labelsize=10)
    cbar.set_label(clabel_str)
    
    if save_flag:
        plt.savefig(output_path, dpi=fig_dpi)
    if show_flag:
        plt.show()

        
    ## Plot with shapely/fiona/matplotlib
    ## https://gist.github.com/urschrei/6442846
    ##et_cells_mp = MultiPolygon(
    ##    [shape(pol['geometry']) for pol in fiona.open(et_cells_path)])
    ##    ##if pol['properties']['AREA_CODE'] == 'LBO'])
    ##fig = plt.figure(1, figsize=(10, 10))
    ##ax = fig.add_axes([0.05, 0.05, 0.9, 0.9])
    ####ax = fig.add_subplot(111)
    ##minx, miny, maxx, maxy = et_cells_mp.bounds
    ##w, h = maxx - minx, maxy - miny
    ##ax.set_xlim(minx - 0.05 * w, maxx + 0.05 * w)
    ##ax.set_ylim(miny - 0.05 * h, maxy + 0.05 * h)
    ##ax.set_aspect(1)
    ##patches = []
    ##cm = plt.get_cmap('RdBu')
    ##num_colours = len(et_cells_mp)
    ##for idx, p in enumerate(et_cells_mp):
    ##    colour = cm(1. * idx / num_colours)
    ##    patches.append(PolygonPatch(p, fc='#6699cc', ec='#555555', alpha=1., zorder=1))
    ####    patches.append(PolygonPatch(p, fc=colour, ec='#555555', alpha=1., zorder=1))
    ##ax.add_collection(PatchCollection(patches, match_original=True))
    ##ax.set_xticks([])
    ##ax.set_yticks([])
    ##plt.title("Shapefile polygons rendered using Shapely")
    ####plt.savefig(os.path.join(output_ws, 'plot_test.png'), alpha=True, dpi=300)
    ##plt.show()
        
    #### CartoPy
    ####http://scitools.org.uk/cartopy/docs/latest/matplotlib/intro.html
    ##print(et_cells_path)
    ####et_cells_shp = shpreader.Reader(et_cells_path)
    ##fig = plt.figure(figsize=(10,10))
    ##ax = fig.add_axes([0.05, 0.05, 0.9, 0.9], projection=ccrs.LambertConformal())
    ####ax = plt.axes([0, 0, 1, 1],
    ####              projection=ccrs.LambertConformal())
    ####ax.set_extent([-125, -66.5, 20, 50], ccrs.Geodetic())
    ####ax.background_patch.set_visible(False)
    ####ax.outline_patch.set_visible(False)
    ##for cell_geom in shpreader.Reader(et_cells_path).geometries():
    ##    facecolor = [0.9375, 0.9375, 0.859375]
    ##    edgecolor = 'black'
    ##    ax.add_geometries([cell_geom], ccrs.PlateCarree(),
    ##                      facecolor=facecolor, edgecolor=edgecolor)
    ####ax = plt.axes(projection=ccrs.PlateCarree())
    ####ax.coastlines()
    ##plt.show() 
    
    #### Using pyshp to convert the shapefile to geojson
    ####http://geospatialpython.com/2013/07/shapefile-to-geojson.html
    ##reader = shapefile.Reader(et_cells_path)
    ##fields = reader.fields[1:]
    ##field_names = [field[0] for field in fields]
    ##buffer = []
    ##for sr in reader.shapeRecords():
    ##    atr = dict(zip(field_names, sr.record))
    ##    geom = sr.shape.__geo_interface__
    ##    buffer.append(dict(type="Feature", geometry=geom, properties=atr)) 
    #### Write the GeoJSON file
    ##geojson = open(os.path.join(output_ws, "etcells.json"), "w")
    ##geojson.write(dumps({
    ##    "type": "FeatureCollection", "features": buffer}, indent=2) + "\n")
    ##geojson.close()
    
    ## Using pyshp to convert the shapefile to geojson
    ##http://geospatialpython.com/2013/07/shapefile-to-geojson.html
    ##fig = plt.figure(figsize=(10,10))
    ##ax = fig.add_axes([0.05, 0.05, 0.9, 0.9])
    ##reader = shapefile.Reader(et_cells_path)
    ##fields = reader.fields[1:]
    ##field_names = [field[0] for field in fields]
    ##for item in reader.shapeRecords():
    ##    item_atr = dict(zip(field_names, item.record))
    ##    item_geom = item.shape.__geo_interface__
    ##    ##print '\n', item_atr
    ##    ##print item_geom['type']
    ##    ##print len(item_geom['coordinates'])
    ##    if item_geom['type'] == 'MultiPolygon':
    ##        for item_poly in item_geom['coordinates']:
    ##            print type(item_poly)
    ##            raw_input('ENTER')
    ##            ax.add_patch(PolygonPatch(item_poly, fc='#6699cc', ec='#0000ff', alpha=0.5))
    ##    elif item_geom['type'] == 'Polygon':
    ##        print type(item_geom)
    ##        raw_input('ENTER')
    ##        ax.add_patch(PolygonPatch(item_geom, fc='#6699cc', ec='#0000ff', alpha=0.5))
    ##    else:
    ##        logging.error('Invalid geometry type')
    ##        continue
    ####ax.set_aspect(1)
    ##ax.axis('scaled')
    ##plt.show()

    #### Vincent
    ##vis = vincent.Map(width=1000, height=1000)
    ###Add the US county data and a new line color
    ##vis.geo_data(projection='albersUsa', scale=1000, counties=county_geo)
    ##vis + ('2B4ECF', 'marks', 0, 'properties', 'enter', 'stroke', 'value')
    ##
    ###Add the state data, remove the fill, write Vega spec output to JSON
    ##vis.geo_data(states=state_geo)
    ##vis - ('fill', 'marks', 1, 'properties', 'enter')
    ##vis.to_json(path)
    
    #### Plot with basemape    
    ##map = Basemap(llcrnrlon=-0.5,llcrnrlat=39.8,urcrnrlon=4.,urcrnrlat=43.,
    ##             resolution='i', projection='tmerc', lat_0 = 39.5, lon_0 = 1)
    ##map.drawmapboundary(fill_color='aqua')
    ##map.fillcontinents(color='#ddaa66',lake_color='aqua')
    ##map.drawcoastlines()
    ##et_cells_sr = Proj(init='epsg:2227', preserve_units=True) 
    ##map_sr = Proj(init='EPSG:4326', preserve_units=True)
    ####transform(et_cells_sr, map_sr, x, y)
    #### Can't read shapefile directly because it is projected
    ##map.readshapefile(os.path.splitext(et_cells_path)[0], 'et_cells')
    #### Read using fiona and project coordinates
    ##with fiona.open(et_cells_path, "r") as et_cells_f:
    ##    for item in et_cells_f:
    ##        item_geom = item['geometry']
    ##        for point in item_geom:
    ##            x,y = point['geometry']['coordinates']
    ##            point['geometry']['coordinates'] = transform(et_cells_sr, map_sr, x, y)
    ##        ##print shape(item['geometry'])
    ##        print item['properties']
    ##        break
    ##plt.show()


def parse_args():
    parser = argparse.ArgumentParser(
        description='Plot Crop Summary Maps',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        '-i', '--ini', metavar='PATH',
        type=lambda x: util.is_valid_file(parser, x), help='Input file')
    parser.add_argument(
        '--size', default=(12, 12), type=float,
        nargs=2, metavar=('WIDTH','HEIGHT'),
        help='Figure size in inches')
    parser.add_argument(
        '--dpi', default=150, type=int, metavar='PIXELS',
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
        '-simp', '--simplify', default=None, type=float, 
        help='Shapely simplify tolerance (units same as ET Cell)')
    parser.add_argument(
        '-o', '--overwrite', default=None, action="store_true", 
        help='Force overwrite of existing files')
    parser.add_argument(
        '--debug', default=logging.INFO, const=logging.DEBUG,
        help='Debug level logging', action="store_const", dest="loglevel")
    args = parser.parse_args()

    ## Convert relative paths to absolute paths
    if args.ini and os.path.isfile(os.path.abspath(args.ini)):
        args.ini = os.path.abspath(args.ini)
    return args

################################################################################

if __name__ == '__main__':
    args = parse_args()
    logging.basicConfig(level=args.loglevel, format='%(message)s')

    ## Try using the command line argument if it was set
    if args.ini:
        ini_path = args.ini
    ## If script was double clicked, set project folder with GUI
    elif not 'PROMPT' in os.environ:
        ini_path = util.get_path(os.getcwd(), 'Select the target INI file')
    ## Try using the current working directory if there is only one INI
    ## Could look for daily_stats folder, run_basin.py, and/or ini file
    elif len([x for x in os.listdir(os.getcwd()) if x.lower().endswith('.ini')]) == 1:
        ini_path = [
            os.path.join(os.getcwd(), x) for x in os.listdir(os.getcwd()) 
            if x.lower().endswith('.ini')][0]
    ## Eventually list available INI files and prompt the user to select one
    ## For now though, use the GUI
    else:
        ini_path = util.get_path(os.getcwd(), 'Select the target INI file')
    
    logging.info('\n{0}'.format('#'*80))
    logging.info('{0:<20s} {1}'.format(
        'Run Time Stamp:', dt.datetime.now().isoformat(' ')))
    logging.info('{0:<20s} {1}'.format('Current Directory:', os.getcwd()))
    logging.info('{0:<20s} {1}'.format('Script:', os.path.basename(sys.argv[0])))

    main(ini_path, show_flag=args.show, save_flag=args.no_save, 
         figure_size=args.size, figure_dpi=args.dpi, label_flag=args.label,
         start_date=args.start, end_date=args.end, crop_str=args.crops,
         simplify_tol=args.simplify, overwrite_flag=args.overwrite)
