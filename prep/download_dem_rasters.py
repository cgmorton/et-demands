#--------------------------------
# Name:         download_dem_rasters.py
# Purpose:      Download NED tiles
# Author:       Charles Morton
# Created       2015-08-12
# Python:       2.7
#--------------------------------

import argparse
import datetime as dt
import logging
import os
import subprocess
import sys
import urllib
import zipfile

from osgeo import ogr

import gdal_common as gdc

################################################################################

def main(gis_ws, tile_ws, dem_cs, extent_path, extent_buffer,
         overwrite_flag=False):
    """Download NED tiles that intersect the study_area

    Script assumes DEM data is in 1x1 WGS84 degree tiles
    Download 10m (1/3 arc-second) or 30m (1 arc-second) versions from:
        10m: rockyftp.cr.usgs.gov/vdelivery/Datasets/Staged/Elevation/13/IMG
        30m: rockyftp.cr.usgs.gov/vdelivery/Datasets/Staged/Elevation/1/IMG
    For this example, only download 30m DEM

    Args:
        gis_ws (str): Folder/workspace path of the GIS data for the project
        tile_ws (str): Folder/workspace path of the DEM tiles
        dem_cs (int): DEM cellsize (10 or 30m)
        extent_path (str): file path to study area shapefile
        extent_buffer (float): distance to buffer input extent
            Units will be the same as the extent spatial reference
        overwrite_flag (bool): If True, overwrite existing files
        
    Returns:
        None
    """
    logging.info('\nDownload DEM tiles')

    zip_fmt = 'n{0:02d}w{1:03d}.zip'
    if dem_cs == 10:
        site_url = 'ftp://rockyftp.cr.usgs.gov/vdelivery/Datasets/Staged/Elevation/13/IMG'
        tile_fmt = 'imgn{0:02d}w{1:03d}_13.img'
    elif dem_cs == 30:
        site_url = 'ftp://rockyftp.cr.usgs.gov/vdelivery/Datasets/Staged/Elevation/1/IMG'
        tile_fmt = 'imgn{0:02d}w{1:03d}_1.img'
    else:
        logging.error('\nERROR: The input cellsize must be 10 or 30\n')
        sys.exit()
        

    ## Use 1 degree snap point and "cellsize" to get 1x1 degree tiles
    tile_osr = gdc.epsg_osr(4269)
    tile_x, tile_y, tile_cs = 0, 0, 1

    ## Output folders
    dem_ws = os.path.join(gis_ws, 'dem')
    tile_ws = os.path.join(dem_ws, 'tiles')

    ## Error checking
    if not os.path.isdir(gis_ws):
        logging.error('\nERROR: The GIS workspace {} '+
                      'does not exist'.format(gis_ws))
        sys.exit()
    elif not os.path.isfile(extent_path):
        logging.error(('\nERROR: The extent shapefile {} '+
                       'does not exist').format(extent_path))
        sys.exit()
    if not os.path.isdir(tile_ws):
        os.makedirs(tile_ws)

    ## Get the extent of each feature
    lat_lon_list = []
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
        output_extent = gdc.project_extent(
            input_extent, input_osr, tile_osr)
        logging.debug('Output Extent: {0}'.format(output_extent))

        ## Extent needed to select 1x1 degree tiles
        tile_extent = output_extent.copy()
        tile_extent.buffer_extent(0.1)
        tile_extent.adjust_to_snap('EXPAND', tile_x, tile_y, tile_cs)
        logging.debug('Tile Extent: {0}'.format(tile_extent))

        ## Get list of avaiable tiles that intersect the extent
        lat_lon_list.extend([
            (lat, -lon)
            for lon in range(int(tile_extent.xmin), int(tile_extent.xmax)) 
            for lat in range(int(tile_extent.ymax), int(tile_extent.ymin), -1)])
    lat_lon_list = sorted(list(set(lat_lon_list)))

    ## Attempt to download the tiles
    logging.info('Downloading')
    for lat_lon in lat_lon_list:
        logging.info(lat_lon)
        zip_name = zip_fmt.format(*lat_lon)
        zip_url = site_url+'/'+zip_name
        zip_path = os.path.join(tile_ws, zip_name)
        tile_name = tile_fmt.format(*lat_lon)
        tile_path = os.path.join(tile_ws, tile_name)
        
        logging.debug(zip_url)
        logging.debug(zip_path)
        if not os.path.isfile(tile_path) or overwrite_flag:
            try:
                urllib.urlretrieve(zip_url, zip_path)
                zip_f = zipfile.ZipFile(zip_path)
                zip_f.extract(tile_name, tile_ws)
                zip_f.close()
            except IOError:
                logging.debug('  IOError, skipping')
        try: os.remove(zip_path)
        except: pass

################################################################################

def arg_parse():
    parser = argparse.ArgumentParser(
        description='Download NED tiles',
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
         dem_cs=args.cellsize, overwrite_flag=args.overwrite)