#--------------------------------
# Name:         merge_dem_rasters.py
# Purpose:      Prepare NED DEM rasters
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

import numpy as np
from osgeo import gdal, ogr, osr

import gdal_common as gdc
import util


def main(gis_ws, tile_ws, dem_cs, overwrite_flag=False,
         pyramids_flag=False, stats_flag=False):
    """Merge, project, and clip NED tiles

    Args:
        gis_ws (str): Folder/workspace path of the GIS data for the project
        tile_ws (str): Folder/workspace path of the DEM tiles
        dem_cs (int): DEM cellsize (10 or 30m)
        overwrite_flag (bool): If True, overwrite existing files
        pyramids_flag (bool): If True, build pyramids/overviews
            for the output rasters
        stats_flag (bool): If True, compute statistics for the output rasters

    Returns:
        None
    """
    logging.info('\nPrepare DEM tiles')

    # Inputs
    output_units = 'METERS'
    dem_ws = os.path.join(gis_ws, 'dem')

    scratch_ws = os.path.join(gis_ws, 'scratch')
    zone_raster_path = os.path.join(scratch_ws, 'zone_raster.img')

    # Use 1 degree snap point and "cellsize" to get 1x1 degree tiles
    tile_osr = gdc.epsg_osr(4269)
    tile_buffer = 0.5
    tile_x, tile_y, tile_cs = 0, 0, 1

    # Input error checking
    if not os.path.isdir(gis_ws):
        logging.error(('\nERROR: The GIS workspace {} ' +
                       'does not exist').format(gis_ws))
        sys.exit()
    elif not os.path.isdir(tile_ws):
        logging.error(('\nERROR: The DEM tile workspace {} ' +
                       'does not exist').format(tile_ws))
        sys.exit()
    elif not os.path.isfile(zone_raster_path):
        logging.error(
            ('\nERROR: The zone raster {} does not exist' +
             '\n  Try re-running "build_study_area_raster.py"').format(
             zone_raster_path))
        sys.exit()
    elif output_units not in ['FEET', 'METERS']:
        logging.error('\nERROR: The output units must be FEET or METERS\n')
        sys.exit()
    logging.info('\nGIS Workspace:   {}'.format(gis_ws))
    logging.info('DEM Workspace:   {}'.format(dem_ws))
    logging.info('Tile Workspace:  {}\n'.format(tile_ws))

    # Input folder/files
    if dem_cs == 10:
        tile_fmt = 'imgn{0:02d}w{1:03d}_13.img'
    elif dem_cs == 30:
        tile_fmt = 'imgn{0:02d}w{1:03d}_1.img'

    # Output folder/files
    if not os.path.isdir(dem_ws):
        os.makedirs(dem_ws)

    # Output file names
    dem_fmt = 'ned_{0}m{1}.img'
    # dem_gcs = dem_fmt.format(dem_cs, '_nad83_meters')
    # dem_feet = dem_fmt.format(dem_cs, '_nad83_feet')
    # dem_proj = dem_fmt.format(dem_cs, '_albers')
    # dem_hs = dem_fmt.format(dem_cs, '_hs')
    dem_gcs_path = os.path.join(dem_ws, dem_fmt.format(dem_cs, '_nad83_meters'))
    dem_feet_path = os.path.join(dem_ws, dem_fmt.format(dem_cs, '_nad83_feet'))
    dem_proj_path = os.path.join(dem_ws, dem_fmt.format(dem_cs, '_albers'))
    dem_hs_path = os.path.join(dem_ws, dem_fmt.format(dem_cs, '_hs'))

    #
    f32_nodata = float(np.finfo(np.float32).min)

    if pyramids_flag:
        levels = '2 4 8 16 32 64 128'
        # gdal.SetConfigOption('USE_RRD', 'YES')
        # gdal.SetConfigOption('HFA_USE_RRD', 'YES')

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

    # Project study area extent to DEM tile coordinate system
    tile_extent = gdc.project_extent(output_extent, output_osr, tile_osr)
    logging.debug('Output Extent: {}'.format(tile_extent))

    # Extent needed to select 1x1 degree tiles
    tile_extent.buffer_extent(tile_buffer)
    tile_extent.adjust_to_snap('EXPAND', tile_x, tile_y, tile_cs)
    logging.debug('Tile Extent: {}'.format(tile_extent))

    # Get list of available tiles that intersect the extent
    input_path_list = sorted(list(set([
        tile_fmt.format(lat, -lon)
        # os.path.join(tile_ws, tile_fmt.format(lat, -lon))
        for lon in range(int(tile_extent.xmin), int(tile_extent.xmax))
        for lat in range(int(tile_extent.ymax), int(tile_extent.ymin), -1)
        if os.path.isfile(os.path.join(tile_ws, tile_fmt.format(lat, -lon)))])))
    logging.debug('Tiles')
    # for input_path in input_path_list:
    #     .debug('  {}'.format(input_path))

    # Calculate using GDAL utilities
    if input_path_list:
        logging.info('Merging tiles')
        if os.path.isfile(dem_gcs_path) and overwrite_flag:
            util.remove_file(dem_gcs_path)
            # subprocess.call(
            #     'gdalmanage', 'delete', '-f', 'HFA', dem_gcs_path])
        if not os.path.isfile(dem_gcs_path):
            # gdal_merge.py was only working if shell=True
            # It would also work to add the scripts folder to the path (in Pythong)
            # Or the scripts folder could be added to the system PYTHONPATH?
            args_list = [
                 'python', '{}\scripts\gdal_merge.py'.format(sys.exec_prefix),
                 '-o', dem_gcs_path, '-of', 'HFA',
                 '-co', 'COMPRESSED=YES', '-a_nodata',
                 str(f32_nodata)] + input_path_list
            logging.debug(args_list)
            logging.debug('command length: {}'.format(len(' '.join(args_list))))
            subprocess.call(args_list, cwd=tile_ws)
            # subprocess.call(
            #     'set', 'GDAL_DATA={}\Lib\site-packages\osgeo\data\gdal'.format(sys.exec_prefix)],
            #     =True)
            # subprocess.call(
            #     'gdal_merge.py', '-o', dem_gcs_path, '-of', 'HFA',
            #     '-co', 'COMPRESSED=YES', '-a_nodata',
            #     str(f32_nodata)] + input_path_list,
            #     =True)

    # Convert DEM from meters to feet
    if output_units == 'FEET':
        # DEADBEEF - This won't run when called through subprocess?
        # subprocess.call(
        #     'gdal_calc.py', '-A', dem_gcs_path,
        #     '--outfile={}'.format(dem_feet_path), '--calc="0.3048*A"',
        #     '--format', 'HFA', '--co', 'COMPRESSED=YES',
        #     '--NoDataValue={}'.format(str(f32_nodata)),
        #     '--type', 'Float32', '--overwrite'],
        #     =dem_ws, shell=True)
        # dem_gcs_path = dem_feet_path
        # Scale the values using custom function
        m2ft_func(dem_gcs_path)

    if os.path.isfile(dem_proj_path) and overwrite_flag:
        subprocess.call(['gdalmanage', 'delete', '-f', 'HFA', dem_proj_path])
    if os.path.isfile(dem_hs_path) and overwrite_flag:
        subprocess.call(['gdalmanage', 'delete', '-f', 'HFA', dem_hs_path])

    if (not os.path.isfile(dem_proj_path) and
        os.path.isfile(dem_gcs_path)):
        subprocess.call(
            ['gdalwarp', '-r', 'bilinear',
             '-tr', str(output_cs), str(output_cs),
             '-s_srs', 'EPSG:4269', '-t_srs', output_wkt, '-ot', 'Float32'] +
            ['-te'] + str(output_extent).split() +
            # ['-srcnodata', 'None', '-dstnodata', str(f32_nodata),
            ['-of', 'HFA', '-co', 'COMPRESSED=YES', '-overwrite',
             '-multi', '-wm', '1024', '-wo', 'NUM_THREADS=ALL_CPUS',
             dem_gcs_path, dem_proj_path])
    if (not os.path.isfile(dem_hs_path) and
        os.path.isfile(dem_proj_path)):
        subprocess.call(
            ['gdaldem', 'hillshade', dem_proj_path, dem_hs_path,
             '-of', 'HFA', '-co', 'COMPRESSED=YES'])

    if stats_flag:
        logging.info('Computing statistics')
        if os.path.isfile(dem_proj_path):
            logging.debug('  {}'.format(dem_proj_path))
            subprocess.call(['gdalinfo', '-stats', '-nomd', dem_proj_path])
        if os.path.isfile(dem_hs_path):
            logging.debug('  {}'.format(dem_hs_path))
            subprocess.call(['gdalinfo', '-stats', '-nomd', dem_hs_path])

    if pyramids_flag:
        logging.info('\nBuilding pyramids')
        if os.path.isfile(dem_proj_path):
            logging.debug('  {}'.format(dem_proj_path))
            subprocess.call(['gdaladdo', '-ro', dem_proj_path] + levels.split())
        if os.path.isfile(dem_hs_path):
            logging.debug('  {}'.format(dem_hs_path))
            subprocess.call(['gdaladdo', '-ro', dem_hs_path] + levels.split())
        # subprocess.call(
        #     'gdaladdo', '-ro', '--config', 'USE_RRD', 'YES',
        #     '--config', 'HFA_USE_RRD', 'YES', dem_proj_path] + levels.split()])
        # subprocess.call(
        #     'gdaladdo', '-ro', '--config', 'USE_RRD', 'YES',
        #     '--config', 'HFA_USE_RRD', 'YES', dem_hs_path] + levels.split()])

    if os.path.isfile(os.path.join(dem_ws, dem_gcs_path)):
        subprocess.call(['gdalmanage', 'delete', '-f', 'HFA', dem_gcs_path])


def m2ft_func(input_raster):
    """Scale the input raster from meters to feet"""
    input_ds = gdal.Open(input_raster, 1)
    input_band = input_ds.GetRasterBand(1)
    input_nodata = input_band.GetNoDataValue()
    input_array = input_band.ReadAsArray(
        0, 0, input_ds.RasterXSize, input_ds.RasterYSize)
    input_array[~np.isnan(input_array)] /= 0.3048
    input_band.WriteArray(input_array, 0, 0)
    input_ds = None


def arg_parse():
    """"""
    parser = argparse.ArgumentParser(
        description='Merge, project, and clip NED tiles',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        '--gis', nargs='?', default=os.path.join(os.getcwd(), 'gis'),
        type=lambda x: util.is_valid_directory(parser, x),
        help='GIS workspace/folder', metavar='FOLDER')
    parser.add_argument(
        '--tiles', metavar='FOLDER', required=True,
        type=lambda x: util.is_valid_directory(parser, x),
        help='Coommon DEM tiles workspace/folder')
    parser.add_argument(
        '-cs', '--cellsize', default=30, metavar='INT', type=int,
        choices=(10, 30), help='DEM cellsize (10 or 30m)')
    parser.add_argument(
        '-o', '--overwrite', default=None, action="store_true",
        help='Force overwrite of existing files')
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

    # Convert input file to an absolute path
    if args.gis and os.path.isdir(os.path.abspath(args.gis)):
        args.gis = os.path.abspath(args.gis)
    if args.tiles and os.path.isdir(os.path.abspath(args.tiles)):
        args.tiles = os.path.abspath(args.tiles)
    return args


if __name__ == '__main__':
    args = arg_parse()

    logging.basicConfig(level=args.loglevel, format='%(message)s')
    logging.info('\n{}'.format('#'*80))
    logging.info('{0:<20s} {1}'.format(
        'Run Time Stamp:', dt.datetime.now().isoformat(' ')))
    logging.info('{0:<20s} {1}'.format('Current Directory:', os.getcwd()))
    logging.info('{0:<20s} {1}'.format('Script:', os.path.basename(sys.argv[0])))

    main(gis_ws=args.gis, tile_ws=args.tiles,
         dem_cs=args.cellsize, overwrite_flag=args.overwrite,
         pyramids_flag=args.pyramids, stats_flag=args.stats)
