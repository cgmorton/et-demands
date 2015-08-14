#--------------------------------
# Name:         et_demands_static_files.py
# Purpose:      Build static files for ET-Demands from zonal stats ETCells
# Author:       Charles Morton
# Created       2015-08-14
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

def main(gis_ws, area_threshold=1, dairy=5, beef=4,
         overwrite_flag=False, cleanup_flag=False):
    """Build static text files needed to run ET-Demands model

    Args:
        gis_ws (str): Folder/workspace path of the GIS data for the project
        area_threshold (float): CDL area threshold [acres]
        dairy (int): Initial number of dairy hay cuttings
        beef (int): Initial number of beef hay cuttings
        lat_lon_flag (bool): If True, calculate lat/lon values for each cell
        overwrite_flag (bool): If True, overwrite existing files
        cleanup_flag (bool): If True, remove temporary files

    Returns:
        None
    """
    logging.info('\nBuilding ET-Demands Static Files')

    ## Default values
    permeability = -999
    soil_depth = 60         ##inches
    aridity = 50
    irrigation = 1
    crops = 85

    ## Read data from geodatabase
    ## This would need to have been set True in the zonal stats scripts
    gdb_flag = False
    if gdb_flag:
        gdb_path = os.path.join(os.path.dirname(gis_ws), 'et-demands_py\et_demands.gdb')
        ##gdb_path = r'D:\Projects\CAT_Basins\AltusOK\et-demands_py\et_demands.gdb'
        et_cells_path = os.path.join(gdb_path, 'et_cells')
    else:
        et_cells_path = os.path.join(gis_ws, 'ETCells.shp')

    ## Eventually set these from the INI file?
    project_ws = os.path.dirname(gis_ws)
    demands_ws = os.path.join(project_ws, 'et_demands_py')

    ## Sub folder names
    static_ws = os.path.join(demands_ws, 'static')
    pmdata_w = os.path.join(demands_ws, 'pmdata')

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
    lat_field = 'LAT'
    lon_field = 'LON'
    elev_field = 'ELEV'
    cell_id_field = 'CELL_ID'
    cell_name_field = 'CELL_NAME'
    station_id_field = 'STATION_ID'
    huc_field = 'HUC{}'.format(huc)

    awc_field = 'AWC'
    clay_field = 'CLAY'
    sand_field = 'SAND'
    awc_in_ft_field = 'AWC_IN_FT'
    hydgrp_num_field = 'HYDGRP_NUM'
    hydgrp_field = 'HYDGRP'
    ##permeability_field = 'PERMEABILITY' 
    ##soil_depth_field = 'SOIL_DEPTH' 
    ##aridity_field = 'ARIDITY'
    ##dairy_cutting_field = 'DAIRY_CUTTINGS'
    ##beef_cutting_field = 'BEEF_CUTTINGS'

    ## Check input folders
    if not os.path.isdir(gis_ws):
        logging.error('\nERROR: The GIS workspace {0} '+
                      'does not exist\n'.format(gis_ws))
        sys.exit()
    elif not os.path.isdir(project_ws):
        logging.error('\nERROR: The project workspace {0} '+
                      'does not exist\n'.format(project_ws))
        sys.exit()
    elif not os.path.isdir(template_ws):
        logging.error('\nERROR: The static template workspace {0} '+
                      'does not exist\n'.format(template_ws))
        sys.exit()
    ##if not os.path.isdir(demands_ws):
    ##    os.makedirs(demands_ws)
    ##if not os.path.isdir(pmdata_ws):
    ##    os.makedirs(pmdata_ws)
    logging.info('\nGIS Workspace:      {0}'.format(gis_ws))
    logging.info('Project Workspace:  {0}'.format(project_ws))
    logging.info('Demands Workspace:  {0}'.format(demands_ws))
    logging.info('Static Workspace:   {0}'.format(static_ws))
    logging.info('Template Workspace: {0}'.format(template_ws))

    ## Check input files
    if not arcpy.Exists(et_cells_path):
        logging.error('\nERROR: The ET Cell shapefile {} '+
                      'does not exist\n'.format(et_cells_path))
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

    ##
    ##arcpy.CheckOutExtension('Spatial')
    ##arcpy.env.pyramid = 'NONE 0'
    ##arcpy.env.overwriteOutput = overwrite_flag
    ##arcpy.env.parallelProcessingFactor = 8

    logging.info('\nCopying template static files')
    for static_name in static_list:
        ##if (overwrite_flag or
        ##    not os.path.isfile(os.path.join(static_ws, static_name))):
        logging.debug('  {}'.format(static_name))
        shutil.copy(os.path.join(template_ws, static_name), static_ws)
        ##shutil.copyfile(
        ##    os.path.join(template_ws, static_name),
        ##    os.path.join(static_ws, crop_params_name))

    logging.info('\nReading ET Cell Zonal Stats')
    logging.debug('  {}'.format(et_cells_path))
    crop_field_list = sorted([
        f.name for f in arcpy.ListFields(et_cells_path)
        if re.match('CROP_\d{2}', f.name)])
    fields = [cell_id_field, cell_name_field, lat_field,
              awc_in_ft_field, clay_field, sand_field,
              hydgrp_num_field, hydgrp_field]
    fields = fields + crop_field_list
    logging.debug('  Fields: {}'.format(fields))
    data_dict = defaultdict(dict)
    with arcpy.da.SearchCursor(et_cells_path, fields) as s_cursor:
        for row in s_cursor:
            for field in fields[1:]:
                data_dict[row[0]][field] = row[fields.index(field)]

    logging.info('\nWriting static text files')
    cell_props_path = os.path.join(static_ws, cell_props_name)
    cell_crops_path = os.path.join(static_ws, cell_crops_name)
    cell_cuttings_path = os.path.join(static_ws, cell_cuttings_name)
    crop_params_path = os.path.join(static_ws, crop_params_name)
    crop_coefs_path = os.path.join(static_ws, crop_coefs_name)

    ## Write cell properties
    logging.info('  {}'.format(cell_props_path))
    with open(cell_props_path, 'a') as output_f:
        for cell_id, cell_data in sorted(data_dict.iteritems()):
            output_list = [
                cell_id, cell_data[cell_name_field], '', '', '', '',
                permeability, cell_data[awc_in_ft_field], soil_depth,
                cell_data[hydgrp_field], cell_data[hydgrp_num_field],
                aridity]
            output_f.write('\t'.join(map(str, output_list)) + '\n')
            del output_list

    ## Write cell crops
    logging.info('  {}'.format(cell_crops_path))
    with open(cell_crops_path, 'a') as output_f:
        for cell_id, cell_data in sorted(data_dict.iteritems()):
            output_list = [cell_id, cell_data[cell_name_field], '', irrigation]
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
    logging.info('  {}'.format(cell_cuttings_path))
    with open(cell_cuttings_path, 'a') as output_f:
        for cell_id, cell_data in sorted(data_dict.iteritems()):
            output_list = [
                cell_id, cell_data[cell_name_field], cell_data[lat_field],
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
        '--acres', default=1, type=float, 
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
         dairy=args.dairy, beef=args.beef,
         overwrite_flag=args.overwrite, cleanup_flag=args.clean)
