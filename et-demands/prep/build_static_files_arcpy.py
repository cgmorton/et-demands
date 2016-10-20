#--------------------------------
# Name:         build_static_files.py
# Purpose:      Build static files for ET-Demands from zonal stats ETCells
# Author:       Charles Morton
# Created       2016-09-14
# Python:       2.7
#--------------------------------

import argparse
from collections import defaultdict
import datetime as dt
import logging
import os
import re
import shutil
import sys

import arcpy

import util


def main(ini_path, zone_type='huc8', area_threshold=10,
         dairy_cuttings=5, beef_cuttings=4,
         overwrite_flag=False, cleanup_flag=False):
    """Build static text files needed to run ET-Demands model

    Args:
        ini_path (str): file path of the project INI file
        zone_type (str): Zone type (huc8, huc10, county)
        area_threshold (float): CDL area threshold [acres]
        dairy_cuttings (int): Initial number of dairy hay cuttings
        beef_cuttings (int): Initial number of beef hay cuttings
        overwrite_flag (bool): If True, overwrite existing files
        cleanup_flag (bool): If True, remove temporary files

    Returns:
        None
    """
    logging.info('\nBuilding ET-Demands Static Files')

    # Input units
    cell_elev_units = 'FEET'
    station_elev_units = 'FEET'

    # Default values
    permeability = -999
    soil_depth = 60         # inches
    aridity = 50
    irrigation = 1
    crops = 85

    # Input paths
    # DEADBEEF - For now, get cropET folder from INI file
    # This function may eventually be moved into the main cropET code
    config = util.read_ini(ini_path, section='CROP_ET')
    try:
        project_ws = config.get('CROP_ET', 'project_folder')
    except:
        logging.error(
            'project_folder parameter must be set in the INI file, exiting')
        return False
    try:
        gis_ws = config.get('CROP_ET', 'gis_folder')
    except:
        logging.error(
            'gis_folder parameter must be set in the INI file, exiting')
        return False
    try:
        et_cells_path = config.get('CROP_ET', 'cells_path')
    except:
        logging.error(
            'cells_path parameter must be set in the INI file, exiting')
        return False
    try:
        stations_path = config.get('CROP_ET', 'stations_path')
    except:
        logging.error(
            'stations_path parameter must be set in the INI file, exiting')
        return False
    try:
        crop_et_ws = config.get('CROP_ET', 'crop_et_folder')
    except:
        logging.error(
            'crop_et_ws parameter must be set in the INI file, exiting')
        return False
    try:
        template_ws = config.get('CROP_ET', 'template_folder')
    except:
        template_ws = os.path.join(os.path.dirname(crop_et_ws), 'static')
        logging.info(
            ('\nStatic text file "template_folder" parameter was not set ' +
             'in the INI\n  Defaulting to: {}').format(template_ws))

    # Read data from geodatabase or shapefile
    # if '.gdb' in et_cells_path and not et_cells_path.endswith('.shp'):
    #     _flag = False
    #     _path = os.path.dirname(et_cells_path)
    #      gdb_path = r'D:\Projects\CAT_Basins\AltusOK\et-demands_py\et_demands.gdb'
    #     _cells_path = os.path.join(gdb_path, 'et_cells')

    # Output sub-folder names
    static_ws = os.path.join(project_ws, 'static')

    # Weather station shapefile
    # Generate by selecting the target NLDAS 4km cell intersecting each HUC
    station_id_field = 'NLDAS_ID'
    if zone_type == 'huc8':
        station_zone_field = 'HUC8'
    elif zone_type == 'huc10':
        station_zone_field = 'HUC10'
    elif zone_type == 'county':
        station_zone_field = 'COUNTYNAME'
        # station_zone_field = 'FIPS_C'
    station_lat_field = 'LAT'
    station_lon_field = 'LON'
    if station_elev_units.upper() in ['FT', 'FEET']:
        station_elev_field = 'ELEV_FT'
    elif station_elev_units.upper() in ['M', 'METERS']:
        station_elev_field = 'ELEV_M'
    # station_elev_field = 'ELEV_FT'

    # Field names
    cell_lat_field = 'LAT'
    # cell_lon_field = 'LON'
    if cell_elev_units.upper() in ['FT', 'FEET']:
        cell_elev_field = 'ELEV_FT'
    elif cell_elev_units.upper() in ['M', 'METERS']:
        cell_elev_field = 'ELEV_M'
    # cell_elev_field = 'ELEV_FT'
    cell_id_field = 'CELL_ID'
    cell_name_field = 'CELL_NAME'
    met_id_field = 'STATION_ID'
    # awc_field = 'AWC'
    clay_field = 'CLAY'
    sand_field = 'SAND'
    awc_in_ft_field = 'AWC_IN_FT'
    hydgrp_num_field = 'HYDGRP_NUM'
    hydgrp_field = 'HYDGRP'
    # huc_field = 'HUC{}'.format(huc)
    # permeability_field = 'PERMEABILITY'
    # soil_depth_field = 'SOIL_DEPTH'
    # aridity_field = 'ARIDITY'
    # dairy_cutting_field = 'DAIRY_CUTTINGS'
    # beef_cutting_field = 'BEEF_CUTTINGS'

    # Static file names
    cell_props_name = 'ETCellsProperties.txt'
    cell_crops_name = 'ETCellsCrops.txt'
    cell_cuttings_name = 'MeanCuttings.txt'
    crop_params_name = 'CropParams.txt'
    crop_coefs_name = 'CropCoefs.txt'
    eto_ratio_name = 'EToRatiosMon.txt'
    static_list = [crop_params_name, crop_coefs_name, cell_props_name,
                   cell_crops_name, cell_cuttings_name, eto_ratio_name]

    # Check input folders
    if not os.path.isdir(crop_et_ws):
        logging.critical(('ERROR: The INI cropET folder ' +
                          'does not exist\n  {}').format(crop_et_ws))
        sys.exit()
    elif not os.path.isdir(project_ws):
        logging.critical(('ERROR: The project folder ' +
                          'does not exist\n  {}').format(project_ws))
        sys.exit()
    elif not os.path.isdir(gis_ws):
        logging.critical(('ERROR: The GIS folder ' +
                          'does not exist\n  {}').format(gis_ws))
        sys.exit()
    logging.info('\nGIS Workspace:      {0}'.format(gis_ws))
    logging.info('Project Workspace:  {0}'.format(project_ws))
    logging.info('CropET Workspace:   {0}'.format(crop_et_ws))
    logging.info('Template Workspace: {0}'.format(template_ws))

    # Check input files
    if not arcpy.Exists(et_cells_path):
        logging.error(('\nERROR: The ET Cell shapefile {} ' +
                       'does not exist\n').format(et_cells_path))
        sys.exit()
    elif not os.path.isfile(stations_path) or not arcpy.Exists(stations_path):
        logging.critical(('ERROR: The NLDAS station shapefile does ' +
                          'not exist\n  %s').format(stations_path))
        sys.exit()
    for static_name in static_list:
        if not os.path.isfile(os.path.join(template_ws, static_name)):
            logging.error(
                ('\nERROR: The static template {} does not ' +
                 'exist\n').format(os.path.join(template_ws, static_name)))
            sys.exit()
    logging.debug('ET Cells Path: {0}'.format(et_cells_path))
    logging.debug('Stations Path: {0}'.format(stations_path))

    # Check units
    if cell_elev_units.upper() not in ['FEET', 'FT', 'METERS', 'M']:
        logging.error(
            ('\nERROR: ET Cell elevation units {} are invalid\n' +
             '  Units must be METERS or FEET').format(cell_elev_units))
        sys.exit()
    elif station_elev_units.upper() not in ['FEET', 'FT', 'METERS', 'M']:
        logging.error(
            ('\nERROR: Station elevation units {} are invalid\n' +
             '  Units must be METERS or FEET').format(station_elev_units))
        sys.exit()

    # Build output table folder if necessary
    if not os.path.isdir(static_ws):
        os.makedirs(static_ws)

    # Read Weather station\NLDAS cell station data
    logging.info('\nReading station shapefile')
    logging.debug('  {}'.format(stations_path))
    fields = [station_zone_field, station_id_field, station_elev_field,
              station_lat_field, station_lon_field]
    logging.debug('  Fields: {}'.format(fields))
    station_data_dict = defaultdict(dict)
    with arcpy.da.SearchCursor(stations_path, fields) as s_cursor:
        for row in s_cursor:
            for field in fields[1:]:
                # Key/match on strings even if ID is an integer
                station_data_dict[str(row[0])][field] = row[fields.index(field)]
    for k, v in station_data_dict.iteritems():
        logging.debug('  {0}: {1}'.format(k, v))

    # Read ET Cell zonal stats
    logging.info('\nReading ET Cell Zonal Stats')
    logging.debug('  {}'.format(et_cells_path))
    crop_field_list = sorted([
        f.name for f in arcpy.ListFields(et_cells_path)
        if re.match('CROP_\d{2}', f.name)])
    fields = [cell_id_field, cell_name_field, cell_lat_field, cell_elev_field,
              awc_in_ft_field, clay_field, sand_field,
              hydgrp_num_field, hydgrp_field]
    fields = fields + crop_field_list
    logging.debug('  Fields: {}'.format(fields))
    cell_data_dict = defaultdict(dict)
    with arcpy.da.SearchCursor(et_cells_path, fields) as s_cursor:
        for row in s_cursor:
            for field in fields[1:]:
                # Key/match on strings even if ID is an integer
                cell_data_dict[str(row[0])][field] = row[fields.index(field)]

    # Update ET Cell MET_ID/STATION_ID value
    fields = [cell_id_field, met_id_field]
    with arcpy.da.UpdateCursor(et_cells_path, fields) as u_cursor:
        for row in u_cursor:
            try:
                row[1] = station_data_dict[row[0]][station_id_field]
                u_cursor.updateRow(row)
            except KeyError:
                pass

    # Covert elevation units if necessary
    if station_elev_units.upper() in ['METERS', 'M']:
        logging.debug('  Convert station elevation from meters to feet')
        for k in station_data_dict.iterkeys():
            station_data_dict[k][station_elev_field] /= 0.3048
    if cell_elev_units.upper() in ['METERS', 'M']:
        logging.debug('  Convert et cell elevation from meters to feet')
        for k in cell_data_dict.iterkeys():
            cell_data_dict[k][cell_elev_field] /= 0.3048

    logging.info('\nCopying template static files')
    for static_name in static_list:
        # if (overwrite_flag or
        #      os.path.isfile(os.path.join(static_ws, static_name))):
        logging.debug('  {}'.format(static_name))
        shutil.copy(os.path.join(template_ws, static_name), static_ws)
        # shutil.copyfile(
        #     .path.join(template_ws, static_name),
        #     .path.join(static_ws, crop_params_name))

    logging.info('\nWriting static text files')
    cell_props_path = os.path.join(static_ws, cell_props_name)
    cell_crops_path = os.path.join(static_ws, cell_crops_name)
    cell_cuttings_path = os.path.join(static_ws, cell_cuttings_name)
    # crop_params_path = os.path.join(static_ws, crop_params_name)
    # crop_coefs_path = os.path.join(static_ws, crop_coefs_name)
    eto_ratio_path = os.path.join(static_ws, eto_ratio_name)

    # Write cell properties
    logging.debug('  {}'.format(cell_props_path))
    with open(cell_props_path, 'a') as output_f:
        for cell_id, cell_data in sorted(cell_data_dict.iteritems()):
            if cell_id in station_data_dict.keys():
                station_data = station_data_dict[cell_id]
                station_id = station_data[station_id_field]
                station_lat = '{:>9.4f}'.format(station_data[station_lat_field])
                station_lon = '{:>9.4f}'.format(station_data[station_lon_field])
                station_elev = '{:.2f}'.format(station_data[station_elev_field])
            else:
                logging.debug(
                    ('    Cell_ID {} was not found in the ' +
                     'station data').format(cell_id))
                station_id, lat, lon, elev = '', '', '', ''
            # There is an extra/unused column in the template and excel files
            output_list = [
                cell_id, cell_data[cell_name_field],
                station_id, station_lat, station_lon,
                station_elev, permeability,
                '{:.4f}'.format(cell_data[awc_in_ft_field]), soil_depth,
                cell_data[hydgrp_field], cell_data[hydgrp_num_field],
                aridity, '']
            output_f.write('\t'.join(map(str, output_list)) + '\n')
            del output_list
            del station_id, station_lat, station_lon, station_elev

    # Write cell crops
    logging.debug('  {}'.format(cell_crops_path))
    with open(cell_crops_path, 'a') as output_f:
        for cell_id, cell_data in sorted(cell_data_dict.iteritems()):
            if cell_id in station_data_dict.keys():
                station_id = station_data_dict[cell_id][station_id_field]
            else:
                logging.debug(
                    ('    Cell_ID {} was not found in the ' +
                     'station data').format(cell_id))
                station_id = ''
            output_list = [
                cell_id, cell_data[cell_name_field], station_id, irrigation]
            crop_list = ['CROP_{:02d}'.format(i) for i in range(1, crops + 1)]
            crop_area_list = [
                cell_data[crop] if crop in cell_data.keys() else 0
                for crop in crop_list]
            crop_flag_list = [
                1 if area > area_threshold else 0 for area in crop_area_list]
            output_list = output_list + crop_flag_list
            output_f.write('\t'.join(map(str, output_list)) + '\n')
            del crop_list, crop_area_list, crop_flag_list, output_list

    # Write cell cuttings
    logging.debug('  {}'.format(cell_cuttings_path))
    with open(cell_cuttings_path, 'a') as output_f:
        for cell_id, cell_data in sorted(cell_data_dict.iteritems()):
            output_list = [
                cell_id, cell_data[cell_name_field],
                '{:>9.4f}'.format(cell_data[cell_lat_field]),
                dairy_cuttings, beef_cuttings]
            output_f.write('\t'.join(map(str, output_list)) + '\n')
            del output_list

    # Write monthly ETo ratios
    logging.debug('  {}'.format(eto_ratio_path))
    with open(eto_ratio_path, 'a') as output_f:
        for cell_id, cell_data in sorted(cell_data_dict.iteritems()):
            if cell_id in station_data_dict.keys():
                station_data = station_data_dict[cell_id]
                station_id = station_data[station_id_field]
                # station_lat = '{:>9.4f}'.format(station_data[station_lat_field])
                # station_lon = '{:>9.4f}'.format(station_data[station_lon_field])
                # station_elev = '{:.2f}'.format(station_data[station_elev_field])
            else:
                logging.debug(
                    ('    Cell_ID {} was not found in the ' +
                     'station data').format(cell_id))
                # station_id, lat, lon, elev = '', '', '', ''
                continue
            output_list = [station_id, ''] + [1.0] * 12
            output_f.write('\t'.join(map(str, output_list)) + '\n')
            del output_list


def arg_parse():
    """"""
    parser = argparse.ArgumentParser(
        description='ET-Demands Static Files',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        '-i', '--ini', metavar='PATH',
        type=lambda x: util.is_valid_file(parser, x), help='Input file')
    parser.add_argument(
        '--zone', default='huc8', metavar='STR', type=str,
        choices=('huc8', 'huc10', 'county'),
        help='Zone type [{}]'.format(', '.join(['huc8', 'huc10', 'county'])))
    parser.add_argument(
        '--acres', default=10, type=float,
        help='Crop area threshold')
    parser.add_argument(
        '--dairy', default=5, type=int,
        help='Number of dairy hay cuttings')
    parser.add_argument(
        '--beef', default=4, type=int,
        help='Number of beef hay cuttings')
    parser.add_argument(
        '-o', '--overwrite', default=None, action='store_true',
        help='Overwrite existing file')
    parser.add_argument(
        '--clean', default=None, action='store_true',
        help='Remove temporary datasets')
    parser.add_argument(
        '--debug', default=logging.INFO, const=logging.DEBUG,
        help='Debug level logging', action="store_const", dest="loglevel")
    args = parser.parse_args()
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

    main(ini_path=args.ini, area_threshold=args.acres, zone_type=args.zone,
         dairy_cuttings=args.dairy, beef_cuttings=args.beef,
         overwrite_flag=args.overwrite, cleanup_flag=args.clean)
