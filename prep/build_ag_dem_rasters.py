#--------------------------------
# Name:         build_ag_dem_rasters.py
# Purpose:      Extract DEM data for agricultural CDL pixels
# Author:       Charles Morton
# Created       2015-09-25
# Python:       2.7
#--------------------------------

import argparse
import datetime as dt
import logging
import os
import shutil
import subprocess
import sys

import numpy as np
from osgeo import gdal

import gdal_common as gdc
import util

################################################################################

def main(gis_ws, cdl_year='', block_size=16384, mask_flag=False, 
         overwrite_flag=False, pyramids_flag=False, stats_flag=False):
    """Mask DEM values for non-agricultural pixels

    Use CDL derived agmask (in CDL workspace) to define agricultural pixels

    Args:
        gis_ws (str): Folder/workspace path of the GIS data for the project
        cdl_year (str): Cropland Data Layer year comma separated list and/or range
        block_size (int): Maximum block size to use for raster processing
        mask_flag (bool): If True, mask pixels outside extent shapefile
        overwrite_flag (bool): If True, overwrite existing files
        pyramids_flag (bool): If True, build pyramids/overviews
            for the output rasters 
        stats_flag (bool): If True, compute statistics for the output rasters
    Returns:
        None
    """
    logging.info('\nExtracting Agriculatural DEM Values')
    
    input_dem_name = 'ned_30m_albers.img'
    cdl_format = '{0}_30m_cdls.img'
    dem_ws = os.path.join(gis_ws, 'dem')
    cdl_ws = os.path.join(gis_ws, 'cdl')
    scratch_ws = os.path.join(gis_ws, 'scratch')  
    zone_raster_path = os.path.join(scratch_ws, 'zone_raster.img')         

    ## Check input folders
    if not os.path.isdir(gis_ws):
        logging.error(('\nERROR: The GIS workspace {} '+
                       'does not exist\n').format(gis_ws))
        sys.exit()
    elif not os.path.isdir(cdl_ws):
        logging.error(('\nERROR: The CDL workspace {} '+
                       'does not exist\n').format(cdl_ws))
        sys.exit()
    elif not os.path.isdir(dem_ws):
        logging.error(('\nERROR: The DEM workspace {} '+
                       'does not exist\n').format(dem_ws))
        sys.exit()
    elif mask_flag and not os.path.isfile(zone_raster_path):
        logging.error(
            ('\nERROR: The zone raster {} does not exist\n'+
             '  Try re-running "clip_cdl_raster.py"').format(zone_raster_path))
        sys.exit()
    logging.info('\nGIS Workspace:   {}'.format(gis_ws))
    logging.info('CDL Workspace:   {}'.format(cdl_ws))
    logging.info('DEM Workspace:   {}\n'.format(dem_ws))

    ## Check input files
    input_dem_path = os.path.join(dem_ws, input_dem_name)
    if not os.path.isfile(input_dem_path):
        logging.error('\nERROR: The raster {} does not exist'.format(
            input_dem_path))
        sys.exit()

    if pyramids_flag:
        levels = '2 4 8 16 32 64 128'
        ##gdal.SetConfigOption('USE_RRD', 'YES')
        ##gdal.SetConfigOption('HFA_USE_RRD', 'YES')

    ## Process existing dem rasters (from merge_dems.py)
    input_rows, input_cols = gdc.raster_path_shape(input_dem_path)

    ## Process each CDL year separately
    for cdl_year in list(util.parse_int_set(cdl_year)):
        logging.info('\n{0}'.format(cdl_year))
        cdl_path = os.path.join(cdl_ws, cdl_format.format(cdl_year))
        output_dem_path = os.path.join(dem_ws, 'dem_{}_30m_cdls.img'.format(cdl_year))
        agland_path = os.path.join(cdl_ws, 'agland_{}_30m_cdls.img'.format(cdl_year))
        agmask_path = os.path.join(cdl_ws, 'agmask_{}_30m_cdls.img'.format(cdl_year))
        if not os.path.isfile(agmask_path):
            logging.error(
                ('\nERROR: The ag-mask raster {} does not exist\n'+
                 '  Try re-running "build_ag_cdl_rasters.py"').format(agmask_path))
            continue
    
        ## Copy input DEM
        if overwrite_flag and os.path.isfile(output_dem_path):
            subprocess.call(['gdalmanage', 'delete', output_dem_path])
        if os.path.isfile(input_dem_path) and not os.path.isfile(output_dem_path):
            logging.info('\nCopying DEM raster')
            logging.debug('{}'.format(input_dem_path))
            subprocess.call(
                ['gdal_translate', '-of', 'HFA', '-co', 'COMPRESSED=YES',
                 input_dem_path, output_dem_path])
        
        ## Set non-ag areas to nodata value
        logging.debug('Processing by block')
        logging.debug('  Input cols/rows: {0}/{1}'.format(
            input_cols, input_rows))
        for b_i, b_j in gdc.block_gen(input_rows, input_cols, block_size):
            logging.debug('  Block  y: {0:5d}  x: {1:5d}'.format(b_i, b_j))
            ## Read in data for block
            agmask_array = gdc.raster_to_block(
                agmask_path, b_i, b_j, block_size, return_nodata=False)
            dem_array, dem_nodata = gdc.raster_to_block(
                input_dem_path, b_i, b_j, block_size, return_nodata=True)
                            
            ## Mask CDL values outside extent shapefile
            if mask_flag and os.path.isfile(zone_raster_path):
                zone_array = gdc.raster_to_block(
                    zone_raster_path, b_i, b_j, block_size)
                dem_array[zone_array == 0] = dem_nodata           
        
            ## Set dem values for non-ag pixels to nodata
            dem_array[~agmask_array.astype(np.bool)] = dem_nodata
        
            gdc.block_to_raster(dem_array, output_dem_path, b_i, b_j, block_size)
            del agmask_array, dem_array, dem_nodata
        
        if stats_flag and os.path.isfile(output_dem_path):
            logging.info('Computing statistics')
            logging.debug('  {}'.format(output_dem_path))
            subprocess.call(['gdalinfo', '-stats', '-nomd', output_dem_path])
        
        if pyramids_flag and os.path.isfile(output_dem_path):
            logging.info('Building pyramids')
            logging.debug('  {}'.format(output_dem_path))
            subprocess.call(['gdaladdo', '-ro', output_dem_path] + levels.split())
       
################################################################################

def arg_parse():
    parser = argparse.ArgumentParser(
        description='Build Ag Dem Rasters',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        '--gis', nargs='?', default=os.path.join(os.getcwd(), 'gis'),
        type=lambda x: util.is_valid_directory(parser, x), 
        help='GIS workspace/folder', metavar='FOLDER')
    parser.add_argument(
        '-y', '--years', metavar='YEAR', required=True,
        help='CDL years, comma separate list and/or range')
    parser.add_argument(
        '-bs', '--blocksize', default=16384, type=int, metavar='N',
        help='Block size')
    parser.add_argument(
        '--mask', default=None, action='store_true', 
        help='Mask pixels outside extent shapefile')
    parser.add_argument(
        '-o', '--overwrite', default=None, action='store_true', 
        help='Overwrite existing file')
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
    return args

################################################################################
if __name__ == '__main__':
    args = arg_parse()

    logging.basicConfig(level=args.loglevel, format='%(message)s')    
    logging.info('\n{}'.format('#'*80))
    logging.info('{0:<20s} {1}'.format('Run Time Stamp:', dt.datetime.now().isoformat(' ')))
    logging.info('{0:<20s} {1}'.format('Current Directory:', os.getcwd()))
    logging.info('{0:<20s} {1}'.format('Script:', os.path.basename(sys.argv[0])))

    main(gis_ws=args.gis, cdl_year=args.years, block_size=args.blocksize, 
         mask_flag=args.mask, overwrite_flag=args.overwrite,
         pyramids_flag=args.pyramids, stats_flag=args.stats)
