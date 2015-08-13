#--------------------------------
# Name:         merge_dem_rasters.py
# Purpose:      Prepare NED DEM rasters
# Author:       Charles Morton
# Created       2015-08-12
# Python:       2.7
#--------------------------------

import argparse
import datetime as dt
import itertools
import logging
import os
import subprocess
import sys

import numpy as np
from osgeo import gdal, ogr, osr

import gdal_common as gdc

################################################################################

def main(gis_ws, tile_ws, dem_cs, extent_path, extent_buffer,
         overwrite_flag=False, pyramids_flag=False, stats_flag=False):
    """Merge, project, and clip NED tiles

    Args:
        gis_ws (str): Folder/workspace path of the GIS data for the project
        tile_ws (str): Folder/workspace path of the DEM tiles
        dem_cs (int): DEM cellsize (10 or 30m)
        extent_path (str): file path to study area shapefile
        extent_buffer (float): distance to buffer input extent
            Units will be the same as the extent spatial reference
        overwrite_flag (bool): If True, overwrite existing files
        pyramids_flag (bool): If True, build pyramids/overviews
            for the output rasters 
        stats_flag (bool): If True, compute statistics for the output rasters
        
    Returns:
        None
    """
    logging.info('\nPrepare DEM tiles')
    
    ## Inputs
    output_units = 'METERS'
    dem_ws = os.path.join(gis_ws, 'dem')

    ## Use 1 degree snap point and "cellsize" to get 1x1 degree tiles
    tile_osr = gdc.epsg_osr(4269)
    tile_x, tile_y, tile_cs = 0, 0, 1

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
    
    ## Input error checking
    if not os.path.isdir(gis_ws):
        logging.error('\nERROR: The GIS workspace {} '+
                      'does not exist'.format(gis_ws))
        sys.exit()
    elif not os.path.isdir(tile_ws):
        logging.error('\nERROR: The DEM tile workspace {} '+
                      'does not exist'.format(tile_ws))
        sys.exit()
    elif not os.path.isfile(extent_path):
        logging.error(('\nERROR: The extent shapefile {} '+
                       'does not exist').format(extent_path))
        sys.exit()
    elif output_units not in ['FEET', 'METERS']:
        logging.error('\nERROR: The output units must be FEET or METERS\n')
        sys.exit()
    logging.info('\nGIS Workspace:   {}'.format(gis_ws))
    logging.info('DEM Workspace:   {}'.format(dem_ws))
    logging.info('Tile Workspace:  {}\n'.format(tile_ws))

    ## Input folder/files
    if dem_cs == 10:
        tile_fmt = 'imgn{0:02d}w{1:03d}_13.img'
    elif dem_cs == 30:
        tile_fmt = 'imgn{0:02d}w{1:03d}_1.img'

    ## Output folder/files
    if not os.path.isdir(dem_ws):
        os.makedirs(dem_ws)

    ## Output file names
    dem_fmt = 'ned_{0}m{1}.img'
    ##dem_gcs = dem_fmt.format(dem_cs, '_nad83_meters')
    ##dem_feet = dem_fmt.format(dem_cs, '_nad83_feet')
    ##dem_proj = dem_fmt.format(dem_cs, '_albers')
    ##dem_hs = dem_fmt.format(dem_cs, '_hs')
    dem_gcs_path = os.path.join(dem_ws, dem_fmt.format(dem_cs, '_nad83_meters'))
    dem_feet_path = os.path.join(dem_ws, dem_fmt.format(dem_cs, '_nad83_feet'))
    dem_proj_path = os.path.join(dem_ws, dem_fmt.format(dem_cs, '_albers'))
    dem_hs_path = os.path.join(dem_ws, dem_fmt.format(dem_cs, '_hs'))

    ##
    f32_nodata = float(np.finfo(np.float32).min)

    if pyramids_flag:
        levels = '2 4 8 16 32 64 128'
        ##gdal.SetConfigOption('HFA_USE_RRD', 'YES')

    ## Get the extent of each feature
    ## DEADBEEF - Why is this being done for each feature separately?
    input_list = []
    shp_driver = ogr.GetDriverByName('ESRI Shapefile')
    input_ds = shp_driver.Open(extent_path, 1)
    input_osr = gdc.feature_ds_osr(input_ds)
    input_layer = input_ds.GetLayer()
    input_ftr = input_layer.GetNextFeature()
    while input_ftr:
        input_geom = input_ftr.GetGeometryRef()
        input_extent = gdc.extent(input_geom.GetEnvelope())
        input_extent = input_extent.ogrenv_swap()
        input_extent.buffer_extent(extent_buffer)
        input_ftr = input_layer.GetNextFeature()    
        logging.debug('Input Extent: {0}'.format(input_extent))

        ## Project study area extent to input raster coordinate system
        tile_extent = gdc.project_extent(
            input_extent, input_osr, tile_osr)
        logging.debug('GCS Extent: {0}'.format(tile_extent))

        ## Extent needed to select 1x1 degree tiles
        tile_extent.adjust_to_snap('EXPAND', tile_x, tile_y, tile_cs)
        ##tile_extent.buffer_extent(0.1)
        logging.debug('GCS Extent: {0}'.format(tile_extent))

        ## Get list of avaiable tiles that intersect the extent
        input_list.extend([
            os.path.join(tile_ws, tile_fmt.format(lat, -lon))
            for lon in range(int(tile_extent.xmin), int(tile_extent.xmax)) 
            for lat in range(int(tile_extent.ymax), int(tile_extent.ymin), -1)])
    input_list = sorted(list(set(input_list)))
    logging.debug('Tiles')
    for item in input_list:
        logging.debug('  {0}'.format(item))

    ## Get the study area extent from a shapefile
    clip_osr = gdc.feature_path_osr(extent_path)
    logging.debug('\nClip OSR: {}'.format(clip_osr))
    clip_extent = gdc.path_extent(extent_path)
    logging.debug('Clip Extent: {}'.format(clip_extent))
    if extent_buffer is not None:
        logging.debug('Buffering: {}'.format(extent_buffer))
        clip_extent.buffer_extent(extent_buffer)
        logging.debug('Clip Extent: {}'.format(clip_extent))

    ## Project study area extent to the output/CDL spatial reference
    output_extent = gdc.project_extent(clip_extent, clip_osr, output_osr)
    output_extent.adjust_to_snap('EXPAND', output_x, output_y, output_cs)
    logging.debug('Output Extent: {0}'.format(output_extent))
   
    ## Calculate using GDAL utilities
    if input_list:
        logging.info('Merging tiles')
        if os.path.isfile(dem_gcs_path) and overwrite_flag:
            subprocess.call(
                ['gdalmanage', 'delete', '-f', 'HFA', dem_gcs_path])
        if not os.path.isfile(dem_gcs_path):
            subprocess.call(
                ['set', 'GDAL_DATA={0}\Lib\site-packages\osgeo\data\gdal'.format(sys.exec_prefix)],
                shell=True)
            subprocess.call(
                ['gdal_merge.py', '-o', dem_gcs_path, '-of', 'HFA',
                 '-co', 'COMPRESSED=YES', '-a_nodata', str(f32_nodata)] + input_list,
                shell=True)

    ## Convert DEM from meters to feet
    if output_units == 'FEET':
        ## DEADBEEF - This won't run when called through subprocess?
        ##subprocess.call(
        ##    ['gdal_calc.py', '-A', dem_gcs_path,
        ##     '--outfile={0}'.format(dem_feet_path), '--calc="0.3048*A"',
        ##     '--format', 'HFA', '--co', 'COMPRESSED=YES',
        ##     '--NoDataValue={0}'.format(str(f32_nodata)),
        ##     '--type', 'Float32', '--overwrite'],
        ##    cwd=dem_ws, shell=True)
        ##dem_gcs_path = dem_feet_path
        ## Scale the values using custom function
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
            ##['-srcnodata', 'None', '-dstnodata', str(f32_nodata), 
            ['-of', 'HFA', '-co', 'COMPRESSED=YES', '-overwrite',
             '-multi', '-wm', '1024',
             dem_gcs_path, dem_proj_path])
    if (not os.path.isfile(dem_hs_path) and
        os.path.isfile(dem_proj_path)):
        subprocess.call(
            ['gdaldem', 'hillshade', dem_proj_path, dem_hs_path,
             '-of', 'HFA', '-co', 'COMPRESSED=YES'])
    
    if stats_flag:
        logging.info('Computing statistics')
        if os.path.isfile(dem_proj_path):
            logging.debug('  {0}'.format(dem_proj_path))
            subprocess.call(['gdalinfo', '-stats', '-nomd', dem_proj_path])
        if os.path.isfile(dem_hs_path):
            logging.debug('  {0}'.format(dem_hs_path))
            subprocess.call(['gdalinfo', '-stats', '-nomd', dem_hs_path])

    if pyramids_flag:
        logging.info('\nBuilding pyramids')
        if os.path.isfile(dem_proj_path):
            logging.debug('  {0}'.format(dem_proj_path))
            subprocess.call(['gdaladdo', '-ro', dem_proj_path] + levels.split())
        if os.path.isfile(dem_hs_path):
            logging.debug('  {0}'.format(dem_hs_path))
            subprocess.call(['gdaladdo', '-ro', dem_hs_path] + levels.split())
        ##subprocess.call(
        ##    ['gdaladdo', '-ro', '--config', 'USE_RRD', 'YES',
        ##     '--config', 'HFA_USE_RRD', 'YES', dem_proj_path] + levels.split()])
        ##subprocess.call(
        ##    ['gdaladdo', '-ro', '--config', 'USE_RRD', 'YES',
        ##     '--config', 'HFA_USE_RRD', 'YES', dem_hs_path] + levels.split()])
        
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
    parser = argparse.ArgumentParser(
        description='Merge, project, and clip NED tiles',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        '--gis', nargs='?', default=os.getcwd(), metavar='FOLDER',
        help='GIS workspace/folder')
    parser.add_argument(
        '--tiles', nargs='?',  metavar='FOLDER', 
        default=os.path.join(os.getcwd(), 'dem', 'tiles'),
        help='GIS workspace/folder')
    parser.add_argument(
        '--extent', required=True, metavar='FILE',
        help='Study area shapefile')
    parser.add_argument(
        '--buffer', default=10000, metavar='FLOAT', type=float,
        help='Extent buffer')
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
 
    ## Convert input file to an absolute path
    if args.gis and os.path.isdir(os.path.abspath(args.gis)):
        args.gis = os.path.abspath(args.gis)
    if args.tiles and os.path.isdir(os.path.abspath(args.tiles)):
        args.tiles = os.path.abspath(args.tiles)
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

    main(gis_ws=args.gis, tile_ws=args.tiles,
         extent_path=args.extent, extent_buffer=args.buffer, 
         dem_cs=args.cellsize, overwrite_flag=args.overwrite,
         pyramids_flag=args.pyramids, stats_flag=args.stats)
