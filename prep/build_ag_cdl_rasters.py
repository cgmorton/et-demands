#--------------------------------
# Name:         build_ag_cdl_rasters.py
# Purpose:      Build ag land and ag mask rasters from cropland rasters
# Author:       Charles Morton
# Created       2015-08-12
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
from osgeo import gdal, ogr, osr

import gdal_common as gdc

def main(gis_ws, block_size=16384, overwrite_flag=False,
         pyramids_flag=False, stats_flag=False,
         agland_nodata=0, agmask_nodata=0):
    """Mask CDL values for non-agricultural pixels

    Use CDL derived agmask (in CDL workspace) to define agricultural pixels

    Args:
        gis_ws (str): Folder/workspace path of the GIS data for the project
        block_size (int): Maximum block size to use for raster processing
        overwrite_flag (bool): If True, overwrite output rasters
        pyramids_flag (bool): If True, build pyramids/overviews
            for the output rasters 
        stats_flag (bool): If True, compute statistics for the output rasters
        agland_nodata: Integer of the nodata value in the agland raster
        agmask_nodata: Integer of the nodata value in the agmask raster
    Returns:
        None

    """

    agmask_fmt = 'agmask_{0}'
    agland_fmt = 'agland_{0}'

    cdl_ws = os.path.join(gis_ws, 'cdl')

    ## Ag landuses are 1, all others in state are 0, outside state is nodata
    ## Crop 61 is fallow/idle and was excluded from analysis
    ## Crops 176 is Grassland/Pasture in the new national CDL rasters
    ## Crops 181 was Pasture/Hay in the old state CDL rasters
    ## Crops 182 was Cultivated Crop in the old state CDL rasters
    agmask_remap = [
        [1, 60, 1], [61, 65, 0], 
        ##[1, 61, 1], [62, 65, 0],
        [66, 80, 1], [81, 92, 0],
        ##[93, 180, 0], [181, 182, 1], [183, 203, 0], [204, 254, 1]]
        ##[93, 180, 0], [176, 1], [183, 203, 0], [204, 254, 1]]
        [93, 203, 0], [204, 254, 1]]

    raster_list = ['2010_30m_cdls.img']
    ##raster_list = ['2013_30m_cdls.img']
    ##raster_list = ['2013_30m_cdls.img', '2012_30m_cdls.img',
    ##               '2011_30m_cdls.img', '2010_30m_cdls.img']
    raster_ext_list = ['.ige', '.img', '.rde', '.rrd']

    ## Check input folders
    if not os.path.isdir(gis_ws):
        logging.error('\nERROR: The GIS workspace {0} '+
                      'does not exist\n'.format(gis_ws))
        sys.exit()
    elif not os.path.isdir(cdl_ws):
        logging.error('\nERROR: The CDL workspace {0} '+
                      'does not exist\n'.format(cdl_ws))
        sys.exit()
    logging.info('\nGIS Workspace:   {0}'.format(gis_ws))
    logging.info('CDL Workspace:   {0}'.format(cdl_ws))
    
    if pyramids_flag:
        ##gdal.SetConfigOption('HFA_USE_RRD', 'YES')
        levels = '2 4 8 16 32 64 128'

    ## Process each soil raster
    for raster_name in sorted(raster_list):
        agmask_path = os.path.join(cdl_ws, agmask_fmt.format(raster_name))
        agland_path = os.path.join(cdl_ws, agland_fmt.format(raster_name))

        ## Get color table and spatial reference from CDL raster
        logging.info('\nReading CDL color table')
        cdl_path = os.path.join(cdl_ws, raster_name)
        if not os.path.isfile(cdl_path):
            logging.error('\nERROR: The CDL raster {0} '+
                          'does not exist\n'.format(cdl_path))
            sys.exit()
        cdl_raster_ds = gdal.Open(cdl_path, 0)
        cdl_geo = gdc.raster_ds_geo(cdl_raster_ds)
        cdl_rows, cdl_cols = gdc.raster_ds_shape(cdl_raster_ds)
        cdl_extent = gdc.geo_extent(cdl_geo, cdl_rows, cdl_cols)
        cdl_proj = gdc.raster_ds_proj(cdl_raster_ds)
        cdl_cs = 30
        cdl_band = cdl_raster_ds.GetRasterBand(1)
        cdl_rat = cdl_band.GetDefaultRAT()
        cdl_classname_dict = dict()
        for row_i in range(cdl_rat.GetRowCount()):
            cdl_classname_dict[row_i] = cdl_rat.GetValueAsString(
                row_i, cdl_rat.GetColOfUsage(2))
        cdl_raster_ds = None
        del cdl_raster_ds, cdl_band, cdl_rat

        ## Copy the input raster
        logging.debug('{0}'.format(agland_path))
        if os.path.isfile(agland_path) and overwrite_flag:
            subprocess.call(['gdalmanage', 'delete', agland_path])
        if not os.path.isfile(agland_path):
            logging.info('Copying CDL raster')
            logging.debug('{0}'.format(cdl_path))
            subprocess.call(
                ['gdal_translate', '-of', 'HFA', cdl_path, agland_path])
            ## '-a_nodata', agland_nodata
            ##subprocess.call([
            ##    'gdaladdo', '-ro', agland_path, '2 4 8 16 32 64 128'])
            
            ## Set the nodata value after copying
            ##agland_ds = gdal.Open(agland_path, 1)
            ##agland_band = agland_ds.GetRasterBand(1)
            ##agland_band.SetNoDataValue(agland_nodata)
            ##agland_ds = None

            ## Get the colormap from the input CDL raster
            logging.debug('Re-building raster attribute tables')
            agland_ds = gdal.Open(agland_path, 1)
            agland_band = agland_ds.GetRasterBand(1)
            agland_rat = agland_band.GetDefaultRAT()
            agland_usage_list = [
                agland_rat.GetUsageOfCol(col_i)
                for col_i in range(agland_rat.GetColumnCount())]
            ##if 1 not in agland_usage_list:
            ##    agland_rat.CreateColumn('Count', 1, 1)
            if 2 not in agland_usage_list:
                agland_rat.CreateColumn('Class_Name', 2, 2)
            for row_i in range(agland_rat.GetRowCount()):
                agland_rat.SetValueAsString(
                    row_i, agland_rat.GetColOfUsage(2),
                    cdl_classname_dict[row_i])
            agland_band.SetDefaultRAT(agland_rat)
            agland_ds = None

        ## Build an empty output raster to hold the data
        logging.info('\nBuilding empty ag mask raster')
        logging.debug('{0}'.format(agmask_path))
        if os.path.isfile(agmask_path) and overwrite_flag:
            subprocess.call(['gdalmanage', 'delete', agmask_path])
        if not os.path.isfile(agmask_path):
            gdc.build_empty_raster(
                agmask_path, band_cnt=1, output_dtype=np.uint8, 
                output_nodata=agmask_nodata, output_proj=cdl_proj,
                output_cs=cdl_cs, output_extent=cdl_extent)

            ## Set the nodata value after initializing
            agmask_ds = gdal.Open(agmask_path, 1)
            agmask_band = agmask_ds.GetRasterBand(1)
            agmask_band.SetNoDataValue(agmask_nodata)
            agmask_ds = None

        ## Set non-ag areas to nodata value
        logging.info('\nProcessing by block')
        logging.debug('  Input cols/rows: {0}/{1}'.format(cdl_cols, cdl_rows))
        for b_i, b_j in gdc.block_gen(cdl_rows, cdl_cols, block_size):
            logging.info('  Block  y: {0:5d}  x: {1:5d}'.format(b_i, b_j))

            ## Read in data for block
            cdl_array = gdc.raster_to_block(
                cdl_path, b_i, b_j, block_size,
                fill_value=0, return_nodata=False)
            logging.debug(cdl_array)
            cdl_mask = np.zeros(cdl_array.shape, dtype=np.bool)
            remap_mask = np.zeros(cdl_array.shape, dtype=np.bool)
            logging.debug(cdl_mask)

            ## Reclassify to 1 for ag and 0 for non-ag
            for [start, end, value] in agmask_remap:
                if value == 0:
                    continue
                logging.debug([start, end, value])
                remap_mask |= (cdl_array >= start) & (cdl_array <= end)
            cdl_mask[remap_mask] = True
            del remap_mask
            logging.debug(cdl_mask)

            ## Set non-ag areas in agmask to nodata
            cdl_mask[~cdl_mask] = agmask_nodata
            logging.debug(cdl_mask)

            ## Set non-ag areas in aglands to nodata
            cdl_array[~cdl_mask] = agland_nodata
            logging.debug(cdl_array)

            gdc.block_to_raster(cdl_array, agland_path, b_i, b_j, block_size)
            gdc.block_to_raster(
                cdl_mask.astype(np.uint8), agmask_path,
                b_i, b_j, block_size)
            del cdl_array, cdl_mask

        if stats_flag:
            logging.info('Computing statistics')
            if os.path.isfile(agland_path):
                logging.debug('{0}'.format(agland_path))
                subprocess.call(['gdalinfo', '-stats', '-nomd', agland_path])
            if os.path.isfile(agmask_path):
                logging.debug('{0}'.format(agmask_path))
                subprocess.call(['gdalinfo', '-stats', '-nomd', agmask_path])

        if pyramids_flag:
            logging.info('Building pyramids')
            if os.path.isfile(agland_path):
                logging.debug('{0}'.format(agland_path))
                subprocess.call(['gdaladdo', '-ro', agland_path] + levels.split())
            if os.path.isfile(agmask_path):
                logging.debug('{0}'.format(agmask_path))
                subprocess.call(['gdaladdo', '-ro', agmask_path] + levels.split())

################################################################################

def arg_parse():
    parser = argparse.ArgumentParser(
        description='Build CDL Ag Rasters',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        '--gis', nargs='?', default=os.getcwd(),
        help='GIS workspace/folder', metavar='FOLDER')
    parser.add_argument(
        '-bs', '--blocksize', default=16384, type=int, metavar='N',
        help='Block size')
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
        '--agland_nodata', default=0, type=int, metavar='N',
        help='Agland nodata value')
    parser.add_argument(
        '--agmask_nodata', default=0, type=int, metavar='N',
        help='Agmask nodata value')
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
    logging.info('\n%s' % ('#'*80))
    logging.info('%-20s %s' % ('Run Time Stamp:', dt.datetime.now().isoformat(' ')))
    logging.info('%-20s %s' % ('Current Directory:', os.getcwd()))
    logging.info('%-20s %s' % ('Script:', os.path.basename(sys.argv[0])))

    main(gis_ws=args.gis, block_size=args.blocksize,
         overwrite_flag=args.overwrite,
         pyramids_flag=args.pyramids, stats_flag=args.stats,
         agland_nodata=args.agland_nodata, agmask_nodata=args.agmask_nodata)