#--------------------------------
# Name:         build_study_area_raster.py
# Purpose:      Build study area raster
# Author:       Charles Morton
# Created       2016-07-22
# Python:       2.7
#--------------------------------

import argparse
import datetime as dt
import glob
import logging
import os
import subprocess
import sys

import gdal_common as gdc
import util


def main(gis_ws, cdl_ws, cdl_year, study_area_path, study_area_buffer=None,
         overwrite_flag=False, pyramids_flag=False, stats_flag=False):
    """Build study area raster from a target extent and rebuild color table

    Args:
        gis_ws (str): Folder/workspace path of the GIS data for the project
        cdl_ws (str): Folder/workspace path of the GIS data for the project
        cdl_year (str): Cropland Data Layer year
        zone_path (str): File path to study area shapefile
        zone_buffer (float): Distance to buffer input extent
            Units will be the same as the extent spatial reference
        overwrite_flag (bool): If True, overwrite output raster
        pyramids_flag (bool): If True, build pyramids/overviews
            for the output raster
        stats_flag (bool): If True, compute statistics for the output raster

    Returns:
        None
    """

    scratch_ws = os.path.join(gis_ws, 'scratch')
    zone_raster_path = os.path.join(scratch_ws, 'zone_raster.img')
    zone_polygon_path = os.path.join(scratch_ws, 'zone_polygon.shp')

    # If multiple years were passed in, only use the first one
    cdl_year = list(util.parse_int_set(cdl_year))[0]

    cdl_format = '{0}_30m_cdls.img'
    cdl_path = os.path.join(cdl_ws, cdl_format.format(cdl_year))

    # Check input folders
    if not os.path.isdir(gis_ws):
        logging.error(('\nERROR: The GIS workspace {} ' +
                       'does not exist').format(gis_ws))
        sys.exit()
    elif not os.path.isfile(cdl_path):
        logging.error(
            ('\nERROR: The input CDL raster {} ' +
             'does not exist').format(cdl_path))
        sys.exit()
    elif not os.path.isfile(study_area_path):
        logging.error(
            ('\nERROR: The extent shapefile {} ' +
             'does not exist').format(study_area_path))
        sys.exit()
    if not os.path.isdir(scratch_ws):
        os.makedirs(scratch_ws)
    logging.info('\nGIS Workspace:      {}'.format(gis_ws))
    logging.info('Scratch Workspace:  {}'.format(scratch_ws))

    # Reference all output rasters to CDL
    # output_osr = gdc.raster_path_osr(cdl_path)
    output_proj = gdc.raster_path_proj(cdl_path)
    output_cs = gdc.raster_path_cellsize(cdl_path)[0]
    output_x, output_y = gdc.raster_path_origin(cdl_path)
    # output_osr = gdc.proj4_osr(
    #     "+proj=aea +lat_1=29.5 +lat_2=45.5 +lat_0=23 +lon_0=-96 "+
    #     "+x_0=0 +y_0=0 +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=m "+
    #     "+no_defs")
    # output_cs = 30
    # output_x, output_y = 15, 15

    if pyramids_flag:
        levels = '2 4 8 16 32 64 128'
        # gdal.SetConfigOption('USE_RRD', 'YES')
        # gdal.SetConfigOption('HFA_USE_RRD', 'YES')

    # Overwrite
    if os.path.isfile(zone_raster_path) and overwrite_flag:
        subprocess.call(['gdalmanage', 'delete', zone_raster_path])
    if os.path.isfile(zone_polygon_path) and overwrite_flag:
        remove_file(zone_polygon_path)
        # subprocess.call(['gdalmanage', 'delete', zone_polygon_path])

    # Project extent shapefile to CDL spatial reference
    if not os.path.isfile(zone_polygon_path):
        # Project study area extent to the input/CDL spatial reference
        logging.info('Projecting extent shapefile')
        subprocess.call(
            ['ogr2ogr', '-overwrite', '-preserve_fid',
             '-t_srs', str(output_proj),
             zone_polygon_path, study_area_path])

    # Get the study area extent from the projected shapefile
    clip_extent = gdc.feature_path_extent(zone_polygon_path)
    logging.debug('Clip Extent: {}'.format(clip_extent))

    # This will buffer in the CDL spatial reference & units
    if study_area_buffer is not None:
        logging.debug('Buffering: {}'.format(study_area_buffer))
        clip_extent.buffer_extent(study_area_buffer)
        logging.debug('Clip Extent: {}'.format(clip_extent))
    clip_extent.adjust_to_snap('EXPAND', output_x, output_y, output_cs)
    logging.debug('Clip Extent: {}'.format(clip_extent))

    # gdal_translate uses ul/lr corners, not extent
    clip_ullr = clip_extent.ul_lr_swap()
    logging.debug('Clip UL/LR:  {}'.format(clip_ullr))

    # Rasterize extent shapefile for masking in other scripts
    if (not os.path.isfile(zone_raster_path) and
        os.path.isfile(zone_polygon_path)):
        logging.info('Rasterizing shapefile')
        subprocess.call(
            ['gdal_rasterize', '-of', 'HFA', '-ot', 'Byte', '-burn', '1',
             '-init', '0', '-a_nodata', '255', '-co', 'COMPRESSED=YES'] +
            ['-te'] + str(clip_extent).split() +
            ['-tr', str(output_cs), str(output_cs),
             zone_polygon_path, zone_raster_path])
        # remove_file(zonse_polygon_path)

    # Statistics
    if stats_flag and os.path.isfile(zone_raster_path):
        logging.info('Computing statistics')
        logging.debug('  {}'.format(zone_raster_path))
        subprocess.call(
            ['gdalinfo', '-stats', '-nomd', '-noct', '-norat',
             zone_raster_path])

    # Pyramids
    if pyramids_flag and os.path.isfile(zone_raster_path):
        logging.info('Building statistics')
        logging.debug('  {}'.format(zone_raster_path))
        subprocess.call(['gdaladdo', '-ro', zone_raster_path] + levels.split())


def remove_file(file_path):
    """Remove a feature/raster and all of its ancillary files"""
    file_ws = os.path.dirname(file_path)
    for file_name in glob.glob(os.path.splitext(file_path)[0] + ".*"):
        os.remove(os.path.join(file_ws, file_name))


def arg_parse():
    """"""
    parser = argparse.ArgumentParser(
        description='Build Study Area Raster',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        '--gis', nargs='?', default=os.path.join(os.getcwd(), 'gis'),
        type=lambda x: util.is_valid_directory(parser, x),
        help='GIS workspace/folder', metavar='FOLDER')
    parser.add_argument(
        '--cdl', metavar='FOLDER', required=True,
        type=lambda x: util.is_valid_directory(parser, x),
        help='Common CDL workspace/folder')
    parser.add_argument(
        '-y', '--years', metavar='YEAR', required=True, help='CDL Year')
    parser.add_argument(
        '-shp', '--shapefile', required=True, metavar='FILE',
        help='Study area shapefile')
    parser.add_argument(
        '--buffer', default=None, metavar='FLOAT', type=float,
        help='Study area buffer')
    parser.add_argument(
        '-o', '--overwrite', default=None, action='store_true',
        help='Overwrite existing files')
    parser.add_argument(
        '--pyramids', default=None, action='store_true',
        help='Build pyramids')
    parser.add_argument(
        '--stats', default=None, action='store_true',
        help='Build statistics')
    parser.add_argument(
        '--debug', default=logging.INFO, const=logging.DEBUG,
        help='Debug level logging', action="store_const", dest="loglevel")
    args = parser.parse_args()

    # Convert relative paths to absolute paths
    if args.gis and os.path.isdir(os.path.abspath(args.gis)):
        args.gis = os.path.abspath(args.gis)
    if args.cdl and os.path.isfile(os.path.abspath(args.cdl)):
        args.cdl = os.path.abspath(args.cdl)
    if args.shapefile and os.path.isfile(os.path.abspath(args.shapefile)):
        args.shapefile = os.path.abspath(args.shapefile)
    return args

if __name__ == '__main__':
    args = arg_parse()

    logging.basicConfig(level=args.loglevel, format='%(message)s')
    logging.info('\n{}'.format('#' * 80))
    logging.info('{0:<20s} {1}'.format(
        'Run Time Stamp:', dt.datetime.now().isoformat(' ')))
    logging.info('{0:<20s} {1}'.format('Current Directory:', os.getcwd()))
    logging.info('{0:<20s} {1}'.format(
        'Script:', os.path.basename(sys.argv[0])))

    main(gis_ws=args.gis, cdl_ws=args.cdl, cdl_year=args.years,
         study_area_path=args.shapefile, study_area_buffer=args.buffer,
         overwrite_flag=args.overwrite, pyramids_flag=args.pyramids,
         stats_flag=args.stats)
