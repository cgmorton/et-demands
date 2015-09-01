#--------------------------------
# Name:         et_demands_static_files.py
# Purpose:      Build static files for ET-Demands from zonal stats ETCells
# Author:       Charles Morton
# Created       2015-08-18
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

def main(gis_ws, area_threshold=1, dairy_cuttings=5, beef_cuttings=4, huc=8,
         overwrite_flag=False, cleanup_flag=False):
    """Build static text files needed to run ET-Demands model

    Args:
        gis_ws (str): Folder/workspace path of the GIS data for the project
        area_threshold (float): CDL area threshold [acres]
        dairy (int): Initial number of dairy hay cuttings
        beef (int): Initial number of beef hay cuttings
        huc (int): HUC level
        lat_lon_flag (bool): If True, calculate lat/lon values for each cell
        overwrite_flag (bool): If True, overwrite existing files
        cleanup_flag (bool): If True, remove temporary files

    Returns:
        None
    """
    logging.info('\nBuilding ET-Demands Static Files')

    ## Input units
    cell_elev_units = 'FEET'
    station_elev_units = 'FEET'

    ## Default values
    permeability = -999
    soil_depth = 60         ##inches
    aridity = 50
    irrigation = 1
    crops = 85

    ## Read data from geodatabase or shapefile
    ## This would need to have been set True in the zonal stats scripts
    gdb_flag = False
    if gdb_flag:
        gdb_path = os.path.join(os.path.dirname(gis_ws), 'et-demands_py\et_demands.gdb')
        ##gdb_path = r'D:\Projects\CAT_Basins\AltusOK\et-demands_py\et_demands.gdb'
        et_cells_path = os.path.join(gdb_path, 'et_cells')
    else:
        et_cells_path = os.path.join(gis_ws, 'ETCells.shp')

    ## Eventually set these from the INI file?
    station_ws = os.path.join(gis_ws, 'stations')
    project_ws = os.path.dirname(gis_ws)
    demands_ws = os.path.join(project_ws, 'et_demands_py')

    ## Sub folder names
    static_ws = os.path.join(demands_ws, 'static')
    pmdata_w = os.path.join(demands_ws, 'pmdata')

    ## Weather station shapefile
    ## Generate by selecting the target NLDAS 4km cell intersecting each HUC
    station_path = os.path.join(station_ws, 'nldas_4km_dd_pts_cat_basins.shp')
    station_id_field = 'NLDAS_ID'
    station_zone_field = 'HUC{}'.format(huc)
    station_lat_field = 'LAT'
    station_lon_field = 'LON'
    station_elev_field = 'ELEV_FT'

    ## Hardcode template workspace for now
    template_ws = r'Z:\USBR_Ag_Demands_Project\CAT_Basins\et-demands\static'

    ## Static file names
    cell_props_name = 'ETCellsProperties.txt'
    cell_crops_name = 'ETCellsCrops.txt'
    cell_cuttings_name = 'MeanCuttings.txt'
    crop_params_name = 'CropParams.txt'
    crop_coefs_name = 'CropCoefs.txt'
    static_list = [crop_params_name, crop_coefs_name, cell_props_name,
                   cell_crops_name, cell_cuttings_name]

    ## Field names
    cell_lat_field = 'LAT'
    cell_lon_field = 'LON'
    cell_elev_field = 'ELEV_FT'
    cell_id_field = 'CELL_ID'
    cell_name_field = 'CELL_NAME'
    awc_field = 'AWC'
    clay_field = 'CLAY'
    sand_field = 'SAND'
    awc_in_ft_field = 'AWC_IN_FT'
    hydgrp_num_field = 'HYDGRP_NUM'
    hydgrp_field = 'HYDGRP'
    ##station_id_field = 'STATION_ID'
    ##huc_field = 'HUC{}'.format(huc)
    ##permeability_field = 'PERMEABILITY' 
    ##soil_depth_field = 'SOIL_DEPTH' 
    ##aridity_field = 'ARIDITY'
    ##dairy_cutting_field = 'DAIRY_CUTTINGS'
    ##beef_cutting_field = 'BEEF_CUTTINGS'

    ## Check input folders
    if not os.path.isdir(gis_ws):
        logging.error(('\nERROR: The GIS workspace {0} '+
                       'does not exist\n').format(gis_ws))
        sys.exit()
    elif not os.path.isdir(station_ws):
        logging.error(('\nERROR: The station workspace {0} '+
                       'does not exist\n').format(station_ws))
        sys.exit()
    elif not os.path.isdir(project_ws):
        logging.error(('\nERROR: The project workspace {0} '+
                       'does not exist\n').format(project_ws))
        sys.exit()
    elif not os.path.isdir(template_ws):
        logging.error(('\nERROR: The static template workspace {0} '+
                       'does not exist\n').format(template_ws))
        sys.exit()
    ##if not os.path.isdir(demands_ws):
    ##    os.makedirs(demands_ws)
    ##if not os.path.isdir(pmdata_ws):
    ##    os.makedirs(pmdata_ws)
    logging.info('\nGIS Workspace:      {0}'.format(gis_ws))
    logging.debug('Station Workspace:  {0}'.format(station_ws))
    logging.info('Project Workspace:  {0}'.format(project_ws))
    logging.info('Demands Workspace:  {0}'.format(demands_ws))
    logging.info('Static Workspace:   {0}'.format(static_ws))
    logging.info('Template Workspace: {0}'.format(template_ws))

    ## Check input files
    if not arcpy.Exists(et_cells_path):
        logging.error('\nERROR: The ET Cell shapefile {} '+
                      'does not exist\n'.format(et_cells_path))
        sys.exit()
    elif not arcpy.Exists(station_path):
        logging.error('\nERROR: The station shapefile {} '+
                      'does not exist\n'.format(station_path))
        sys.exit()
    for static_name in static_list:
        if not os.path.isfile(os.path.join(template_ws, static_name)):
            logging.error(
                ('\nERROR: The static template {} does not '+
                 'exist\n').format(os.path.join(template_ws, static_name)))
            sys.exit()
    
    ## Build output table folder if necessary
    if not os.path.isdir(static_ws):
        os.makedirs(static_ws)

    ## Check units
    if station_elev_units.upper() not in ['FEET', 'FT', 'METERS', 'M']:
        logging.error(
            ('\nERROR: Station elevation units {} are invalid\n'+
             '  Units must be METERS or FEET').format(station_elev_units))
        sys.exit()
    elif cell_elev_units.upper() not in ['FEET', 'FT', 'METERS', 'M']:
        logging.error(
            ('\nERROR: ET Cell elevation units {} are invalid\n'+
             '  Units must be METERS or FEET').format(cell_elev_units))
        sys.exit()

    ## Read Weather station\NLDAS cell station data
    logging.info('\nReading station shapefile')
    logging.debug('  {}'.format(station_path))
    fields = [station_zone_field, station_id_field, station_elev_field,
              station_lat_field, station_lon_field]
    logging.debug('  Fields: {}'.format(fields))
    station_data_dict = defaultdict(dict)
    with arcpy.da.SearchCursor(station_path, fields) as s_cursor:
        for row in s_cursor:
            for field in fields[1:]:
                ## Key/match on strings even if ID is an integer
                station_data_dict[str(row[0])][field] = row[fields.index(field)]
    for k,v in station_data_dict.iteritems():
        logging.debug('  {0}: {1}'.format(k, v))

    ## ReadET Cell zonal stats
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
                ## Key/match on strings even if ID is an integer
                cell_data_dict[str(row[0])][field] = row[fields.index(field)]

    ## Covert elevation units if necessary
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
        ##if (overwrite_flag or
        ##    not os.path.isfile(os.path.join(static_ws, static_name))):
        logging.debug('  {}'.format(static_name))
        shutil.copy(os.path.join(template_ws, static_name), static_ws)
        ##shutil.copyfile(
        ##    os.path.join(template_ws, static_name),
        ##    os.path.join(static_ws, crop_params_name))

    logging.info('\nWriting static text files')
    cell_props_path = os.path.join(static_ws, cell_props_name)
    cell_crops_path = os.path.join(static_ws, cell_crops_name)
    cell_cuttings_path = os.path.join(static_ws, cell_cuttings_name)
    crop_params_path = os.path.join(static_ws, crop_params_name)
    crop_coefs_path = os.path.join(static_ws, crop_coefs_name)

    ## Write cell properties
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
                    ('    Cell_ID {} was not found in the '+
                     'station data').format(cell_id))
                station_id, lat, lon, elev = '', '', '', ''
            ## There is an extra/unused column in the template and excel files
            output_list = [
                cell_id, cell_data[cell_name_field],
                station_id, station_lat, station_lon, station_elev, permeability, 
                '{:.4f}'.format(cell_data[awc_in_ft_field]), soil_depth,
                cell_data[hydgrp_field], cell_data[hydgrp_num_field],
                aridity, '']
            output_f.write('\t'.join(map(str, output_list)) + '\n')
            del output_list
            del station_id, station_lat, station_lon, station_elev

    ## Write cell crops
    logging.debug('  {}'.format(cell_crops_path))
    with open(cell_crops_path, 'a') as output_f:
        for cell_id, cell_data in sorted(cell_data_dict.iteritems()):
            if cell_id in station_data_dict.keys():
                station_id = station_data_dict[cell_id][station_id_field]
            else:
                logging.debug(
                    ('    Cell_ID {} was not found in the '+
                     'station data').format(cell_id))
                station_id = ''
            output_list = [
                cell_id, cell_data[cell_name_field], station_id, irrigation]
            crop_list = ['CROP_{:02d}'.format(i) for i in range(1,crops+1)]
            crop_area_list = [
                cell_data[crop] if crop in cell_data.keys() else 0
                for crop in crop_list]
            crop_flag_list = [
                1 if area > area_threshold else 0 for area in crop_area_list]
            output_list = output_list + crop_flag_list
            output_f.write('\t'.join(map(str, output_list)) + '\n')
            del crop_list, crop_area_list, crop_flag_list, output_list

    ## Write cell cuttings
    logging.debug('  {}'.format(cell_cuttings_path))
    with open(cell_cuttings_path, 'a') as output_f:
        for cell_id, cell_data in sorted(cell_data_dict.iteritems()):
            output_list = [
                cell_id, cell_data[cell_name_field],
                '{:>9.4f}'.format(cell_data[cell_lat_field]),
                dairy_cuttings, beef_cuttings, 0, 0]
            output_f.write('\t'.join(map(str, output_list)) + '\n')
            del output_list

################################################################################

def arg_parse():
    parser = argparse.ArgumentParser(
        description='ET-Demands Static Files',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        '--gis', nargs='?', default=os.getcwd(), metavar='FOLDER',
        help='GIS workspace/folder')
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
        '--huc', default=8, metavar='INT', type=int,
        choices=(8, 10), help='HUC level')
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

    main(gis_ws=args.gis, area_threshold=args.acres,
         dairy_cuttings=args.dairy, beef_cuttings=args.beef, huc=args.huc,
         overwrite_flag=args.overwrite, cleanup_flag=args.clean)
