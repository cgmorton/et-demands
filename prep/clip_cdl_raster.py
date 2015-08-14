#--------------------------------
# Name:         clip_cdl_raster.py
# Purpose:      Clip CDL rasters in order to build agland rasters
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

import gdal_common as gdc

def main(gis_ws, cdl_year=2010, overwrite_flag=False, 
         pyramids_flag=False, stats_flag=False):
    """Clip CDL rasters to a target extent and rebuild color table

    Args:
        gis_ws (str): Folder/workspace path of the GIS data for the project
        cdl_year (int): Cropland Data Layer year
        overwrite_flag (bool): If True, overwrite output rasters
        pyramids_flag (bool): If True, build pyramids/overviews
            for the output rasters 
    Returns:
        None
    """

    input_cdl_path = r'Z:\USBR_Ag_Demands_Project\CAT_Basins\common\gis\cdl\{}_30m_cdls.img'.format(cdl_year)
    ##input_cdl_path = r'U:\GIS-DATA\Cropland_Data_Layer\{}_30m_cdls.img'.format(cdl_year)
    ##input_cdl_path = r'D:\Projects\NLDAS_Demands\common\gis\cdl\{}_30m_cdls.img'.format(cdl_year)
    ##input_cdl_path = r'N:\Texas\ETDemands\common\gis\cdl\{}_30m_cdls.img'.format(cdl_year)

    cdl_ws = os.path.join(gis_ws, 'cdl')
    clip_path = os.path.join(cdl_ws, '{}_30m_cdls.img'.format(cdl_year))

    scratch_ws = os.path.join(gis_ws, 'scratch')
    zone_raster_path = os.path.join(scratch_ws, 'zone_raster.img')

    if pyramids_flag:
        levels = '2 4 8 16 32 64 128'

    ## Check input folders
    if not os.path.isdir(gis_ws):
        logging.error('\nERROR: The GIS workspace {} '+
                      'does not exist'.format(gis_ws))
        sys.exit()
    elif not os.path.isfile(input_cdl_path):
        logging.error(
            ('\nERROR: The input CDL raster {} '+
             'does not exist').format(input_cdl_path))
        sys.exit()
    elif not os.path.isfile(zone_raster_path):
        logging.error(
            ('\nERROR: The zone raster {} does not exist'+
             '\n  Try re-running "build_study_area_raster.py"').format(
             zone_raster_path))
        sys.exit()
    if not os.path.isdir(cdl_ws):
        os.makedirs(cdl_ws)
    if not os.path.isdir(scratch_ws):
        os.makedirs(scratch_ws)
    logging.info('\nGIS Workspace:      {}'.format(gis_ws))
    logging.info('CDL Workspace:      {}'.format(cdl_ws))
    logging.info('Scratch Workspace:  {}'.format(scratch_ws))

    ## Reference all output rasters zone raster
    zone_raster_ds = gdal.Open(zone_raster_path)
    output_osr = gdc.raster_ds_osr(zone_raster_ds)
    output_wkt = gdc.raster_ds_proj(zone_raster_ds)
    output_cs = gdc.raster_ds_cellsize(zone_raster_ds)[0]
    output_x, output_y = gdc.raster_ds_origin(zone_raster_ds)
    output_extent = gdc.raster_ds_extent(zone_raster_ds)
    output_ullr = output_extent.ul_lr_swap()
    zone_raster_ds = None
    logging.debug('\nStudy area properties')
    logging.debug('  Output OSR: {}'.format(output_osr))
    logging.debug('  Output Extent: {}'.format(output_extent))   
    logging.debug('  Output cellsize: {}'.format(output_cs))
    logging.debug('  Output UL/LR: {}'.format(output_ullr))

    ## Overwrite
    if os.path.isfile(clip_path) or overwrite_flag:
        subprocess.call(['gdalmanage', 'delete', clip_path])
        ##remove_file(clip_path)

    ## Clip
    if not os.path.isfile(clip_path):     
        subprocess.call(
            ['gdal_translate', '-of', 'HFA', '-co', 'COMPRESSED=YES']+
            ['-projwin'] + str(output_ullr).split() +
            ['-a_ullr'] + str(output_ullr).split() + 
            [input_cdl_path, clip_path])
        ## , '-a_srs', 'output_proj'
        ##subprocess.call(
        ##    ['gdalwarp', '-overwrite', '-of', 'HFA']+
        ##    ['-te'] + str(output_extent).split() +
        ##    ['-tr', '{}'.format(input_cs), '{}'.format(input_cs),
        ##    [input_cdl_path, clip_path])

        ## Get class names from CDL raster
        logging.info('Read RAT')
        input_ds = gdal.Open(input_cdl_path, 0)
        input_band = input_ds.GetRasterBand(1)
        input_rat = input_band.GetDefaultRAT()
        classname_dict = dict()
        for row_i in range(input_rat.GetRowCount()):
            classname_dict[row_i] = input_rat.GetValueAsString(
                row_i, input_rat.GetColOfUsage(2))
        input_ds = None
        del input_ds, input_band, input_rat
    
        ## Set class names in the clipped CDL raster
        logging.info('Write RAT',)
        clip_ds = gdal.Open(clip_path, 1)
        clip_band = clip_ds.GetRasterBand(1)
        clip_rat = clip_band.GetDefaultRAT()
        clip_usage_list = [
            clip_rat.GetUsageOfCol(col_i)
            for col_i in range(clip_rat.GetColumnCount())]
        logging.debug(clip_usage_list)
        ##if 1 not in clip_usage_list:
        ##    clip_rat.CreateColumn('Count', 1, 1)
        if 2 not in clip_usage_list:
            clip_rat.CreateColumn('Class_Name', 2, 2)
        for row_i in range(clip_rat.GetRowCount()):
            clip_rat.SetValueAsString(
                row_i, clip_rat.GetColOfUsage(2), classname_dict[row_i])
        clip_band.SetDefaultRAT(clip_rat)
        ## Check that they were written to the RAT
        ##clip_rat = clip_band.GetDefaultRAT()
        ##for row_i in range(clip_rat.GetRowCount()):
        ##    print clip_rat.GetValueAsString(row_i, clip_rat.GetColOfUsage(2))
        clip_ds = None

    ## Statistics
    if stats_flag and os.path.isfile(clip_path):
        logging.info('Computing statistics')
        logging.debug('  {}'.format(clip_path))
        subprocess.call(
            ['gdalinfo', '-stats', '-nomd', '-noct', '-norat', clip_path])

    ## Pyramids
    if pyramids_flag and os.path.isfile(clip_path):
        logging.info('Building statistics')
        logging.debug('  {}'.format(clip_path))
        subprocess.call(['gdaladdo', '-ro', clip_path] + levels.split())

################################################################################

def remove_file(file_path):
    """Remove a feature/raster and all of its anciallary files"""
    file_ws = os.path.dirname(file_path)
    for file_name in glob.glob(os.path.splitext(file_path)[0]+".*"):
        os.remove(os.path.join(file_ws, file_name))

def arg_parse():
    parser = argparse.ArgumentParser(
        description='Clip CDL Rasters',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        '--gis', nargs='?', default=os.getcwd(), metavar='FOLDER',
        help='GIS workspace/folder')
    parser.add_argument(
        '--year', default=2010, metavar='INT', type=int,
        choices=(2010, 2011, 2012, 2013, 2014), help='CDL year')
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

    main(gis_ws=args.gis, cdl_year=args.year,
         overwrite_flag=args.overwrite, pyramids_flag=args.pyramids,
         stats_flag=args.stats)
