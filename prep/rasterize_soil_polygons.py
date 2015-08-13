#--------------------------------
# Name:         rasterize_soil_polygons.py
# Purpose:      Convert soil polygons to raster
# Author:       Charles Morton
# Created       2015-08-13
# Python:       2.7
#--------------------------------

import argparse
import datetime as dt
import glob
import logging
import os
import subprocess
import sys

from osgeo import gdal, ogr, osr
import numpy as np

import gdal_common as gdc

def main(gis_ws, extent_path, extent_buffer=None, prop_list=['all'], 
         overwrite_flag=False, pyramids_flag=False, stats_flag=False):
    """Convert soil polygon shapefiles to raster

    Snap to latest CDL rasters (in CDL workspace) with an albers projection

    Args:
        gis_ws (str): Folder/workspace path of the GIS data for the project
        prop_list (list): String of the soil types to build
            (i.e. awc, clay, sand, all)
        extent_path (str): file path to study area shapefile
        extent_buffer (float): distance to buffer input extent
            Units will be the same as the extent spatial reference
        overwrite_flag (bool): If True, overwrite output rasters
        pyramids_flag (bool): If True, build pyramids/overviews
            for the output rasters 
        stats_flag (bool): If True, compute statistics for the output rasters
    
    Returns:
        None
    """
    input_soil_ws = r'Z:\USBR_Ag_Demands_Project\CAT_Basins\common\gis\statsgo'
    folder_fmt = 'gsmsoil_{0}'
    polygon_fmt = 'gsmsoilmu_a_us_{0}_albers.shp'
    output_soil_ws = os.path.join(gis_ws, 'statsgo')

    ## Reference all output rasters to CDL
    input_cdl_path = r'Z:\USBR_Ag_Demands_Project\CAT_Basins\common\gis\cdl\2010_30m_cdls.img'
    output_osr = gdc.raster_path_osr(input_cdl_path)
    output_cs = gdc.raster_path_cellsize(input_cdl_path)[0]
    output_x, output_y = gdc.raster_path_origin(input_cdl_path)
    output_wkt = gdc.osr_proj(output_osr)
    ##output_osr = gdc.proj4_osr(
    ##    "+proj=aea +lat_1=29.5 +lat_2=45.5 +lat_0=23 +lon_0=-96 +x_0=0 +y_0=0 +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=m +no_defs")
    ##output_cs = 30
    ##output_x, output_y = 15, 15

    ## Soil polygons have a float and integer field
    field_fmt = '{0}'
    ##field_fmt = '{0}_INT'

    raster_fmt = '{0}_30m_albers.img'
    ##raster_fmt = '{0}_2013_30m_cdls.img'
    ##raster_fmt = 'gsmsoil_{0}_integer.img'

    output_format = 'HFA'
    output_type = 'Float32'
    output_nodata = float(np.finfo(np.float32).min)
    ##output_type = 'Byte'
    ##output_nodata = 255

    if pyramids_flag:
        levels = '2 4 8 16 32 64 128'
        ##gdal.SetConfigOption('HFA_USE_RRD', 'YES')
    logging.info('Soil Property:   {0}'.format(', '.join(prop_list)))
    if prop_list == ['all']:
        prop_list = ['awc', 'clay', 'sand']

    ## Check input folders
    if not os.path.isdir(gis_ws):
        logging.error('\nERROR: The GIS workspace {} '+
                      'does not exist\n'.format(gis_ws))
        sys.exit()
    elif not os.path.isdir(input_soil_ws):
        logging.error(('\nERROR: The input soil folder {} '+
                       'does not exist').format(input_soil_ws))
        sys.exit()
    elif not os.path.isfile(extent_path):
        logging.error(('\nERROR: The extent shapefile {} '+
                       'does not exist').format(extent_path))
        sys.exit()
    if not os.path.isdir(output_soil_ws):
        os.makedirs(output_soil_ws)
    logging.info('\nGIS Workspace:   {}'.format(gis_ws))
    logging.info('Soil Workspace:  {}\n'.format(output_soil_ws))

    temp_polygon_path = os.path.join(output_soil_ws, 'temp_polygon.shp')
    if os.path.isfile(temp_polygon_path):
        remove_file(temp_polygon_path)
        ##subprocess.call(['gdalmanage', 'delete', '-f', '', temp_polygon_path])


    ## Process each soil property
    for prop_str in prop_list:
        input_polygon_path = os.path.join(
            input_soil_ws,
            folder_fmt.format(prop_str), polygon_fmt.format(prop_str))
        output_raster_path = os.path.join(
            output_soil_ws, raster_fmt.format(prop_str))

        ## Get the extent from a raster/shapefile
        clip_osr = gdc.feature_path_osr(extent_path)
        logging.debug('Clip OSR: {}'.format(clip_osr))
        clip_extent = gdc.path_extent(extent_path)
        logging.debug('Clip Extent: {}'.format(clip_extent))
        if extent_buffer is not None:
            logging.debug('Buffering: {}'.format(extent_buffer))
            clip_extent.buffer_extent(extent_buffer)
            logging.debug('Clip Extent: {}'.format(clip_extent))

        if not os.path.isfile(input_polygon_path):
            logging.info('The soil polygon {} does not '+
                         'exist'.format(input_polygon_path))
            continue
        elif os.path.isfile(output_raster_path) and overwrite_flag:
            subprocess.call(['gdalmanage', 'delete', output_raster_path])

        if not os.path.isfile(output_raster_path):
            soil_field = field_fmt.format(prop_str.upper())
            logging.info('Projecting shapefile')
            ## Project study area extent to the input/soil spatial reference
            input_osr = gdc.feature_path_osr(input_polygon_path)
            input_extent = gdc.project_extent(clip_extent, clip_osr, input_osr)
            logging.debug('Input Extent: {}'.format(input_extent))
            subprocess.call(
                ['ogr2ogr', '-overwrite', '-preserve_fid',
                 '-t_srs', str(output_wkt),
                 '-spat', str(input_extent.xmin), str(input_extent.ymin),
                 str(input_extent.ymax), str(input_extent.ymax), 
                 temp_polygon_path, input_polygon_path])

            logging.info('Rasterizing shapefile')
            ## Project study area extent to the output/CDL spatial reference
            clip_extent = gdc.project_extent(clip_extent, clip_osr, output_osr)
            clip_extent.adjust_to_snap('EXPAND', output_x, output_y, output_cs)
            logging.debug('Clip Extent: {}'.format(clip_extent))
            subprocess.call(
                ['gdal_rasterize', '-of', output_format, '-a', soil_field,
                 '-a_nodata', str(output_nodata),
                 '-init', str(output_nodata)] +
                ['-te'] + str(clip_extent).split() + 
                ['-tr', str(output_cs), str(output_cs), '-ot', output_type,  
                 temp_polygon_path, output_raster_path])
            
        if os.path.isfile(temp_polygon_path):
            remove_file(temp_polygon_path)
            ##subprocess.call(['gdalmanage', 'delete', temp_polygon_path])
            
        if stats_flag and os.path.isfile(output_raster_path):
            logging.info('Computing statistics')
            logging.debug('  {0}'.format(output_raster_path))
            subprocess.call(['gdalinfo', '-stats', '-nomd', output_raster_path])

        if pyramids_flag and os.path.isfile(output_raster_path):
            logging.info('Building pyramids')
            logging.debug('  {0}'.format(output_raster_path))
            subprocess.call(['gdaladdo', '-ro', output_raster_path] + levels.split())

################################################################################

def remove_file(file_path):
    """Remove a feature/raster and all of its anciallary files"""
    file_ws = os.path.dirname(file_path)
    for file_name in glob.glob(os.path.splitext(file_path)[0]+".*"):
        os.remove(os.path.join(file_ws, file_name))

def arg_parse():
    parser = argparse.ArgumentParser(
        description='Rasterize Soil Polygons',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        '--gis', nargs='?', default=os.getcwd(), metavar='FOLDER',
        help='GIS workspace/folder')
    parser.add_argument(
        '--extent', required=True, metavar='FILE',
        help='Study area shapefile')
    parser.add_argument(
        '--buffer', default=None, metavar='FLOAT', type=float,
        help='Extent buffer')
    parser.add_argument(
        '-o', '--overwrite', default=None, action='store_true', 
        help='Force overwrite of existing files')
    parser.add_argument(
        '--pyramids', default=None, action='store_true', 
        help='Build pyramids')
    parser.add_argument(
        '--stats', default=None, action='store_true',
        help='Build statistics')
    parser.add_argument(
        '--soil', default=['all'], nargs='*', metavar='STR',
        choices=('all', 'awc', 'clay', 'sand'), 
        help='Soil property (all, awc, clay, sand)')
    parser.add_argument(
        '--debug', default=logging.INFO, const=logging.DEBUG,
        help='Debug level logging', action="store_const", dest="loglevel")
    args = parser.parse_args()

    ## Convert input file to an absolute path
    if args.gis and os.path.isdir(os.path.abspath(args.gis)):
        args.gis = os.path.abspath(args.gis)
    if args.extent and os.path.isfile(os.path.abspath(args.extent)):
        args.extent = os.path.abspath(args.extent)
    return args

################################################################################
if __name__ == '__main__':
    args = arg_parse()

    logging.basicConfig(level=args.loglevel, format='%(message)s') 
    logging.info('\n%s' % ('#'*80))
    logging.info('%-20s %s' % ('Run Time Stamp:', dt.datetime.now().isoformat(' ')))
    logging.info('%-20s %s' % ('Current Directory:', os.getcwd()))
    logging.info('%-20s %s' % ('Script:', os.path.basename(sys.argv[0])))

    main(gis_ws=args.gis, prop_list=args.soil,
         extent_path=args.extent, extent_buffer=args.buffer,
         overwrite_flag=args.overwrite, pyramids_flag=args.pyramids, 
         stats_flag=args.stats)
