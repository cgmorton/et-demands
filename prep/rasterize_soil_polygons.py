#--------------------------------
# Name:         rasterize_soil_polygons.py
# Purpose:      Convert soil polygons to raster
# Author:       Charles Morton
# Created       2015-12-08
# Python:       2.7
#--------------------------------

import argparse
import datetime as dt
import logging
import os
import subprocess
import sys

from osgeo import gdal, ogr, osr
import numpy as np

import gdal_common as gdc
import util


def main(gis_ws, input_soil_ws, prop_list=['all'], overwrite_flag=False,
         pyramids_flag=False, stats_flag=False):
    """Convert soil polygon shapefiles to raster

    Snap to latest CDL rasters (in CDL workspace) with an albers projection

    Args:
        gis_ws (str): Folder/workspace path of the GIS data for the project
        input_soil_ws (str): Folder/workspace path of the common soils data
        prop_list (list): String of the soil types to build
            (i.e. awc, clay, sand, all)
        overwrite_flag (bool): If True, overwrite output rasters
        pyramids_flag (bool): If True, build pyramids/overviews
            for the output rasters
        stats_flag (bool): If True, compute statistics for the output rasters

    Returns:
        None
    """
    logging.info('\nRasterizing Soil Polygons')

    folder_fmt = 'gsmsoil_{}'
    polygon_fmt = 'gsmsoilmu_a_{}_albers.shp'
    output_soil_ws = os.path.join(gis_ws, 'soils')

    scratch_ws = os.path.join(gis_ws, 'scratch')
    zone_raster_path = os.path.join(scratch_ws, 'zone_raster.img')

    # Soil polygons have a float and integer field
    field_fmt = '{}'
    # field_fmt = '{}_INT'

    raster_fmt = '{}_30m_albers.img'
    # raster_fmt = '{}_2010_30m_cdls.img'
    # raster_fmt = 'gsmsoil_{}_integer.img'

    output_format = 'HFA'
    output_type = 'Float32'
    output_nodata = float(np.finfo(np.float32).min)
    # output_type = 'Byte'
    # output_nodata = 255

    if pyramids_flag:
        levels = '2 4 8 16 32 64 128'
        # gdal.SetConfigOption('USE_RRD', 'YES')
        # gdal.SetConfigOption('HFA_USE_RRD', 'YES')

    logging.info('Soil Property:   {}'.format(', '.join(prop_list)))
    if prop_list == ['all']:
        prop_list = ['awc', 'clay', 'sand']

    # Check input folders
    if not os.path.isdir(gis_ws):
        logging.error('\nERROR: The GIS workspace {} ' +
                      'does not exist\n'.format(gis_ws))
        sys.exit()
    elif not os.path.isdir(input_soil_ws):
        logging.error(('\nERROR: The input soil workspace {} ' +
                       'does not exist').format(input_soil_ws))
        sys.exit()
    elif not os.path.isfile(zone_raster_path):
        logging.error(
            ('\nERROR: The zone raster {} does not exist' +
             '\n  Try re-running "build_study_area_raster.py"').format(
             zone_raster_path))
        sys.exit()
    if not os.path.isdir(output_soil_ws):
        os.makedirs(output_soil_ws)
    logging.info('\nGIS Workspace:   {}'.format(gis_ws))
    logging.info('Soil Workspace:  {}\n'.format(output_soil_ws))

    temp_polygon_path = os.path.join(output_soil_ws, 'temp_polygon.shp')
    if os.path.isfile(temp_polygon_path):
        util.remove_file(temp_polygon_path)
        # subprocess.call(
        #     ['gdalmanage', 'delete', '-f', '', temp_polygon_path])

    # Reference all output rasters zone raster
    zone_raster_ds = gdal.Open(zone_raster_path)
    output_osr = gdc.raster_ds_osr(zone_raster_ds)
    output_wkt = gdc.raster_ds_proj(zone_raster_ds)
    output_cs = gdc.raster_ds_cellsize(zone_raster_ds)[0]
    output_x, output_y = gdc.raster_ds_origin(zone_raster_ds)
    output_extent = gdc.raster_ds_extent(zone_raster_ds)
    zone_raster_ds = None
    logging.debug('\nStudy area properties')
    logging.debug('  Output OSR: {}'.format(output_osr))
    logging.debug('  Output Extent: {}'.format(output_extent))
    logging.debug('  Output cellsize: {}'.format(output_cs))

    # Process each soil property
    for prop_str in prop_list:
        input_polygon_path = os.path.join(
            input_soil_ws,
            folder_fmt.format(prop_str), polygon_fmt.format(prop_str))
        output_raster_path = os.path.join(
            output_soil_ws, raster_fmt.format(prop_str))

        if not os.path.isfile(input_polygon_path):
            logging.info('The soil polygon {} does not ' +
                         'exist'.format(input_polygon_path))
            continue
        elif os.path.isfile(output_raster_path) and overwrite_flag:
            subprocess.call(['gdalmanage', 'delete', output_raster_path])

        if not os.path.isfile(output_raster_path):
            soil_field = field_fmt.format(prop_str.upper())
            logging.info('Projecting shapefile')
            # Project study area extent to the input/soil spatial reference
            input_osr = gdc.feature_path_osr(input_polygon_path)
            input_extent = gdc.project_extent(
                output_extent, output_osr, input_osr)
            logging.debug('Input Extent: {}'.format(input_extent))
            subprocess.call(
                ['ogr2ogr', '-overwrite', '-preserve_fid',
                 '-t_srs', str(output_wkt),
                 '-spat', str(input_extent.xmin), str(input_extent.ymin),
                 str(input_extent.ymax), str(input_extent.ymax),
                 temp_polygon_path, input_polygon_path])

            logging.info('Rasterizing shapefile')
            subprocess.call(
                ['gdal_rasterize', '-of', output_format, '-a', soil_field,
                 '-a_nodata', str(output_nodata),
                 '-init', str(output_nodata), '-co', 'COMPRESSED=YES'] +
                ['-te'] + str(output_extent).split() +
                ['-tr', str(output_cs), str(output_cs), '-ot', output_type,
                 temp_polygon_path, output_raster_path])

        if os.path.isfile(temp_polygon_path):
            util.remove_file(temp_polygon_path)
            # subprocess.call(['gdalmanage', 'delete', temp_polygon_path])

        if stats_flag and os.path.isfile(output_raster_path):
            logging.info('Computing statistics')
            logging.debug('  {}'.format(output_raster_path))
            subprocess.call(
                ['gdalinfo', '-stats', '-nomd', output_raster_path])

        if pyramids_flag and os.path.isfile(output_raster_path):
            logging.info('Building pyramids')
            logging.debug('  {}'.format(output_raster_path))
            subprocess.call(
                ['gdaladdo', '-ro', output_raster_path] + levels.split())


def arg_parse():
    """"""
    parser = argparse.ArgumentParser(
        description='Rasterize Soil Polygons',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        '--gis', nargs='?', default=os.path.join(os.getcwd(), 'gis'),
        type=lambda x: util.is_valid_directory(parser, x),
        help='GIS workspace/folder', metavar='FOLDER')
    parser.add_argument(
        '--soil', required=True, metavar='FOLDER',
        type=lambda x: util.is_valid_directory(parser, x),
        help='Common soil workspace/folder')
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
        '--type', default=['all'], nargs='*', metavar='STR',
        choices=('all', 'awc', 'clay', 'sand'),
        help="Soil property type ('all', 'awc', 'clay', 'sand')")
    parser.add_argument(
        '--debug', default=logging.INFO, const=logging.DEBUG,
        help='Debug level logging', action="store_const", dest="loglevel")
    args = parser.parse_args()

    # Convert relative paths to absolute paths
    if args.gis and os.path.isdir(os.path.abspath(args.gis)):
        args.gis = os.path.abspath(args.gis)
    if args.soil and os.path.isdir(os.path.abspath(args.soil)):
        args.soil = os.path.abspath(args.soil)
    return args


if __name__ == '__main__':
    args = arg_parse()

    logging.basicConfig(level=args.loglevel, format='%(message)s')
    logging.info('\n{}'.format('#'*80))
    logging.info('{0:<20s} {1}'.format(
        'Run Time Stamp:', dt.datetime.now().isoformat(' ')))
    logging.info('{0:<20s} {1}'.format('Current Directory:', os.getcwd()))
    logging.info('{0:<20s} {1}'.format('Script:', os.path.basename(sys.argv[0])))

    main(gis_ws=args.gis, input_soil_ws=args.soil, prop_list=args.type,
         overwrite_flag=args.overwrite, pyramids_flag=args.pyramids,
         stats_flag=args.stats)
