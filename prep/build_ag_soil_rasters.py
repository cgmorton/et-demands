#--------------------------------
# Name:         build_ag_soil_rasters.py
# Purpose:      Extract soils data for agricultural CDL pixels
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
# from osgeo import gdal

import gdal_common as gdc
import util


def main(gis_ws, input_soil_ws, cdl_year='', prop_list=['all'],
         block_size=16384, mask_flag=False,
         overwrite_flag=False, pyramids_flag=False, stats_flag=False):
    """Mask DEM values for non-agricultural pixels

    Use CDL derived agmask (in CDL workspace) to define agricultural pixels

    Args:
        gis_ws (str): Folder/workspace path of the GIS data for the project
        input_soil_ws (str): Folder/workspace path of the common soils data
        cdl_year (str): Comma separated list and/or range of years
        prop_list (list): String of the soil types to build
            (i.e. awc, clay, sand, all)
        block_size (int): Maximum block size to use for raster processing
        mask_flag (bool): If True, mask pixels outside extent shapefile
        overwrite_flag (bool): If True, overwrite existing files
        pyramids_flag (bool): If True, build pyramids/overviews
            for the output rasters
        stats_flag (bool): If True, compute statistics for the output rasters

    Returns:
        None
    """
    logging.info('\nExtracting Agriculatural Soil Values')

    input_soil_fmt = '{}_30m_albers.img'
    cdl_format = '{0}_30m_cdls.img'
    cdl_ws = os.path.join(gis_ws, 'cdl')
    # input_soil_ws = os.path.join(gis_ws, 'statsgo')
    output_soil_ws = os.path.join(gis_ws, 'soils')

    scratch_ws = os.path.join(gis_ws, 'scratch')
    zone_raster_path = os.path.join(scratch_ws, 'zone_raster.img')

    # Check input folders
    if not os.path.isdir(gis_ws):
        logging.error(('\nERROR: The GIS folder {} ' +
                       'does not exist\n').format(gis_ws))
        sys.exit()
    elif not os.path.isdir(cdl_ws):
        logging.error(('\nERROR: The CDL folder {} ' +
                       'does not exist\n').format(cdl_ws))
        sys.exit()
    elif not os.path.isdir(input_soil_ws):
        logging.error(('\nERROR: The input soil folder {} ' +
                       'does not exist\n').format(input_soil_ws))
        sys.exit()
    elif mask_flag and not os.path.isfile(zone_raster_path):
        logging.error(
            ('\nERROR: The zone raster {} does not exist\n' +
             '  Try re-running "clip_cdl_raster.py"').format(zone_raster_path))
        sys.exit()
    logging.info('\nGIS Workspace:   {}'.format(gis_ws))
    logging.info('CDL Workspace:   {}'.format(cdl_ws))
    logging.info('Input Soil Workspace:  {}'.format(input_soil_ws))
    logging.info('Output Soil Workspace: {}'.format(output_soil_ws))

    if pyramids_flag:
        levels = '2 4 8 16 32 64 128'
        # gdal.SetConfigOption('USE_RRD', 'YES')
        # gdal.SetConfigOption('HFA_USE_RRD', 'YES')

    # Process each CDL year separately
    for cdl_year in list(util.parse_int_set(cdl_year)):
        logging.info('\n{0}'.format(cdl_year))
        cdl_path = os.path.join(cdl_ws, cdl_format.format(cdl_year))
        output_soil_fmt = '{0}_{1}_30m_cdls.img'.format('{}', cdl_year)
        agland_path = os.path.join(
            cdl_ws, 'agland_{}_30m_cdls.img'.format(cdl_year))
        agmask_path = os.path.join(
            cdl_ws, 'agmask_{}_30m_cdls.img'.format(cdl_year))
        if not os.path.isfile(agmask_path):
            logging.error(
                ('\nERROR: The ag-mask raster {} does not exist\n' +
                 '  Try re-running "build_ag_cdl_rasters.py"').format(
                    agmask_path))
            continue

        logging.info('Soil Property:   {}'.format(', '.join(prop_list)))
        if prop_list == ['all']:
            prop_list = ['awc', 'clay', 'sand']

        # Process existing soil rasters (from rasterize script)
        for prop_str in prop_list:
            logging.info('\nSoil: {}'.format(prop_str.upper()))
            input_soil_path = os.path.join(
                input_soil_ws, input_soil_fmt.format(prop_str))
            output_soil_path = os.path.join(
                output_soil_ws, output_soil_fmt.format(prop_str))
            if not os.path.isfile(input_soil_path):
                logging.error('\nERROR: The raster {} does not exist'.format(
                    input_soil_path))
                continue

            # Create a copy of the input raster to modify
            if overwrite_flag and os.path.isfile(output_soil_path):
                subprocess.call(['gdalmanage', 'delete', output_soil_path])
            if (os.path.isfile(input_soil_path) and
                not os.path.isfile(output_soil_path)):
                logging.info('\nCopying soil raster')
                logging.debug('{}'.format(input_soil_path))
                subprocess.call(
                    ['gdal_translate', '-of', 'HFA', '-co', 'COMPRESSED=YES',
                     input_soil_path, output_soil_path])

            # Get the size of the input raster
            input_rows, input_cols = gdc.raster_path_shape(input_soil_path)

            # Set non-ag areas to nodata value
            logging.debug('Processing by block')
            logging.debug('  Input cols/rows: {0}/{1}'.format(
                input_cols, input_rows))
            for b_i, b_j in gdc.block_gen(input_rows, input_cols, block_size):
                logging.debug('  Block  y: {0:5d}  x: {1:5d}'.format(b_i, b_j))

                # Read in data for block
                agmask_array = gdc.raster_to_block(
                    agmask_path, b_i, b_j, block_size, return_nodata=False)
                soil_array, soil_nodata = gdc.raster_to_block(
                    input_soil_path, b_i, b_j, block_size, return_nodata=True)

                # Mask CDL values outside extent shapefile
                if mask_flag and os.path.isfile(zone_raster_path):
                    zone_array = gdc.raster_to_block(
                        zone_raster_path, b_i, b_j, block_size)
                    soil_array[zone_array == 0] = soil_nodata

                # Set soil values for non-ag pixels to nodata
                soil_array[~agmask_array.astype(np.bool)] = soil_nodata

                gdc.block_to_raster(
                    soil_array, output_soil_path, b_i, b_j, block_size)
                del agmask_array, soil_array, soil_nodata

            if stats_flag and os.path.isfile(output_soil_path):
                logging.info('Computing statistics')
                logging.debug('  {}'.format(output_soil_path))
                subprocess.call(
                    ['gdalinfo', '-stats', '-nomd', output_soil_path])

            if pyramids_flag and os.path.isfile(output_soil_path):
                logging.info('Building pyramids')
                logging.debug('  {}'.format(output_soil_path))
                subprocess.call(
                    ['gdaladdo', '-ro', output_soil_path] + levels.split())


def arg_parse():
    """"""
    parser = argparse.ArgumentParser(
        description='Build Ag Soils Rasters',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        '--gis', metavar='FOLDER',
        nargs='?', default=os.path.join(os.getcwd(), 'gis'),
        type=lambda x: util.is_valid_directory(parser, x),
        help='GIS workspace/folder')
    parser.add_argument(
        '--soil', metavar='FOLDER',
        nargs='?', default=os.path.join(os.getcwd(), 'gis', 'soils'),
        type=lambda x: util.is_valid_directory(parser, x),
        help='Common soil workspace/folder')
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
        '--type', default=['all'], nargs='*', metavar='STR',
        choices=('all', 'awc', 'clay', 'sand'),
        help='Soil property type (all, awc, clay, sand)')
    parser.add_argument(
        '--debug', default=logging.INFO, const=logging.DEBUG,
        help='Debug level logging', action="store_const", dest="loglevel")
    args = parser.parse_args()

    # Convert input file to an absolute path
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

    main(gis_ws=args.gis, input_soil_ws=args.soil, cdl_year=args.years,
         prop_list=args.type, block_size=args.blocksize,
         mask_flag=args.mask, overwrite_flag=args.overwrite,
         pyramids_flag=args.pyramids, stats_flag=args.stats)
