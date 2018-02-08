#--------------------------------
# Name:         clip_cdl_raster.py
# Purpose:      Clip CDL rasters in order to build agland rasters
# Author:       Charles Morton
# Created       2017-01-11
# Python:       2.7
#--------------------------------

import argparse
import datetime as dt
import logging
import os
import shutil
import subprocess
import sys

from osgeo import gdal

import _gdal_common as gdc
import _util as util


def main(gis_ws, cdl_input_ws, cdl_year='', overwrite_flag=False,
         pyramids_flag=False, stats_flag=False):
    """Clip CDL rasters to a target extent and rebuild color table

    Args:
        gis_ws (str): Folder/workspace path of the GIS data for the project
        cdl_input_ws (str): Folder/workspace path of the GIS data for the project
        cdl_year (str): Comma separated list and/or range of years
        overwrite_flag (bool): If True, overwrite output rasters
        pyramids_flag (bool): If True, build pyramids/overviews
            for the output rasters

    Returns:
        None
    """

    cdl_format = '{0}_30m_cdls.img'
    cdl_output_ws = os.path.join(gis_ws, 'cdl')
    scratch_ws = os.path.join(gis_ws, 'scratch')
    zone_raster_path = os.path.join(scratch_ws, 'zone_raster.img')

    if pyramids_flag:
        levels = '2 4 8 16 32 64 128'
        # gdal.SetConfigOption('USE_RRD', 'YES')
        # gdal.SetConfigOption('HFA_USE_RRD', 'YES')

    # Check input folders
    if not os.path.isdir(gis_ws):
        logging.error(('\nERROR: The GIS workspace {} ' +
                       'does not exist').format(gis_ws))
        sys.exit()
    elif not os.path.isfile(zone_raster_path):
        logging.error(
            ('\nERROR: The zone raster {} does not exist' +
             '\n  Try re-running "build_study_area_raster.py"').format(
                zone_raster_path))
        sys.exit()
    if not os.path.isdir(cdl_output_ws):
        os.makedirs(cdl_output_ws)
    if not os.path.isdir(scratch_ws):
        os.makedirs(scratch_ws)
    logging.info('\nGIS Workspace:      {}'.format(gis_ws))
    logging.info('CDL Workspace:      {}'.format(cdl_output_ws))
    logging.info('Scratch Workspace:  {}'.format(scratch_ws))

    # Process each CDL year separately
    for cdl_year in list(util.parse_int_set(cdl_year)):
        logging.info('{0}'.format(cdl_year))
        cdl_input_path = os.path.join(
            cdl_input_ws, cdl_format.format(cdl_year))
        cdl_output_path = os.path.join(
            cdl_output_ws, cdl_format.format(cdl_year))
        if not os.path.isfile(cdl_input_path):
            logging.error(
                ('\nERROR: The input CDL raster {} ' +
                 'does not exist').format(cdl_input_path))
            continue

        # Reference all output rasters zone raster
        zone_raster_ds = gdal.Open(zone_raster_path)
        output_osr = gdc.raster_ds_osr(zone_raster_ds)
        # output_wkt = gdc.raster_ds_proj(zone_raster_ds)
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

        # Overwrite
        if os.path.isfile(cdl_output_path) or overwrite_flag:
            subprocess.call(['gdalmanage', 'delete', cdl_output_path])
            # remove_file(cdl_output_path)

        # Clip
        if not os.path.isfile(cdl_output_path):
            subprocess.call(
                ['gdal_translate', '-of', 'HFA', '-co', 'COMPRESSED=YES'] +
                ['-projwin'] + str(output_ullr).split() +
                ['-a_ullr'] + str(output_ullr).split() +
                [cdl_input_path, cdl_output_path])
                shutil.copyfile(
                )
            # , '-a_srs', 'output_proj'
            # subprocess.call(
            #     'gdalwarp', '-overwrite', '-of', 'HFA']+
            #     '-te'] + str(output_extent).split() +
            #     '-tr', '{}'.format(input_cs), '{}'.format(input_cs),
            #     _cdl_path, cdl_output_path])

            #Trying copying vat.dbf file from original cdl instead of copying class names during clip
            # # Get class names from CDL raster
            # logging.info('Read RAT')
            # input_ds = gdal.Open(cdl_input_path, 0)
            # input_band = input_ds.GetRasterBand(1)
            # input_rat = input_band.GetDefaultRAT()
            # classname_dict = dict()
            #
            # # input_name_list = [
            # #     input_rat.GetNameOfCol(col_i)
            # #     for col_i in range(input_rat.GetColumnCount())]
            # input_usage_list = [
            #     input_rat.GetUsageOfCol(col_i)
            #     for col_i in range(input_rat.GetColumnCount())]
            # logging.debug(input_usage_list)
            # #if 1 not in clip_usage_list:
            # #     _rat.CreateColumn('Count', 1, 1)
            # if 2 in input_usage_list:
            #     for row_i in range(input_rat.GetRowCount()):
            #         try:
            #             classname_dict[row_i] = input_rat.GetValueAsString(
            #                 row_i, input_rat.GetColOfUsage(2))
            #         except:
            #             pass
            # input_ds = None
            # del input_ds, input_band, input_rat
            #
            # # Set class names in the clipped CDL raster
            # logging.info('Write RAT',)
            # clip_ds = gdal.Open(cdl_output_path, 1)
            # clip_band = clip_ds.GetRasterBand(1)
            # clip_rat = clip_band.GetDefaultRAT()
            # clip_usage_list = [
            #     clip_rat.GetUsageOfCol(col_i)
            #     for col_i in range(clip_rat.GetColumnCount())]
            # logging.debug(clip_usage_list)
            # # if 1 not in clip_usage_list:
            # #     _rat.CreateColumn('Count', 1, 1)
            # if 2 not in clip_usage_list:
            #     clip_rat.CreateColumn('Class_Name', 2, 2)
            # for row_i in range(clip_rat.GetRowCount()):
            #     clip_rat.SetValueAsString(
            #         row_i, clip_rat.GetColOfUsage(2), classname_dict[row_i])
            # clip_band.SetDefaultRAT(clip_rat)
            # # Check that they were written to the RAT
            # # clip_rat = clip_band.GetDefaultRAT()
            # # for row_i in range(clip_rat.GetRowCount()):
            # #      clip_rat.GetValueAsString(row_i, clip_rat.GetColOfUsage(2))
            # clip_ds = None

        # Statistics
        if stats_flag and os.path.isfile(cdl_output_path):
            logging.info('Computing statistics')
            logging.debug('  {}'.format(cdl_output_path))
            subprocess.call(
                ['gdalinfo', '-stats', '-nomd', '-noct', '-norat',
                 cdl_output_path])

        # Pyramids
        if pyramids_flag and os.path.isfile(cdl_output_path):
            logging.info('Building statistics')
            logging.debug('  {}'.format(cdl_output_path))
            subprocess.call(
                ['gdaladdo', '-ro', cdl_output_path] + levels.split())


def arg_parse():
    """"""
    parser = argparse.ArgumentParser(
        description='Clip CDL Rasters',
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
        '-y', '--years', metavar='YEAR', required=True,
        help='Years, comma separate list and/or range')
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
    if args.cdl and os.path.isdir(os.path.abspath(args.cdl)):
        args.cdl = os.path.abspath(args.cdl)
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

    main(gis_ws=args.gis, cdl_input_ws=args.cdl, cdl_year=args.years,
         overwrite_flag=args.overwrite, pyramids_flag=args.pyramids,
         stats_flag=args.stats)
