#--------------------------------
# Name:         et_demands_static_files.py
# Purpose:      Build static files for ET-Demands from zonal stats ETCells
# Author:       Charles Morton
# Created       2015-08-13
# Python:       2.7
#--------------------------------

import argparse
from collections import defaultdict
import datetime as dt
import logging
import os
import shutil
import sys

import arcpy

def main(gis_ws, cdl_year=2010, huc=8, latlon_flag=False,
         overwrite_flag=False, cleanup_flag=False):
    """Build static text files needed to run ET-Demands model

    Args:
        gis_ws (str): Folder/workspace path of the GIS data for the project
        cdl_year (int): Cropland Data Layer year
        huc_level (int): HUC level
        lat_lon_flag (bool): If True, calculate lat/lon values for each cell
        overwrite_flag (bool): If True, overwrite existing files
        cleanup_flag (bool): If True, remove temporary files

    Returns:
        None
    """
    logging.info('\nBuilding ET-Demands Static Files')

##    zone_path = os.path.join(gis_ws, 'huc8', 'wbdhu8_albers.shp')
##    zone_field = 'HUC8'
##    ##zone_path = os.path.join(gis_ws, 'nldas_4km', 'nldas_4km_albers_sub.shp')
##    ##zone_field = 'NLDAS_ID'
##    ##zone_path = os.path.join(gis_ws, 'nldas_4km', 'nldas_4km_albers.shp')
##    ##zone_field = 'NLDAS_ID'
##    ##zone_path = os.path.join(gis_ws, 'nldas_12km', 'nldas_12km_albers.shp')
##    ##zone_field = 'NLDAS_ID'
##    ##zone_path = os.path.join(
##    ##    gis_ws, 'counties', 'county_nrcs_a_mbr_albers.shp')
##    ##zone_field = 'FIPS_I'
##    ##zone_field = 'COUNTYNAME'
##
##    cell_name_fmt = 'HUC8 '
##    ##cell_name_fmt = 'NLDAS 4km '
##    ##cell_name_fmt = 'HUC8_{0}'
##    ##cell_name_fmt = 'NLDAS_4km_{0}'

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
    template_ws = r'Z:\USBR_Ag_Demands_Project\CAT_Basins\et-demands\cropET\static'

    ## Static file names
    cell_props_name = 'ETCellsProperties.txt'
    cell_crops_name = 'ETCellsCrops.txt'
    cell_cuttings_name = 'MeanCuttings.txt'
    crop_params_name = 'CropParams.txt'
    crop_coefs_name = 'CropCoefs.txt'
    cell_props_path = os.path.join(template_ws, cell_props_name)
    cell_crops_path = os.path.join(template_ws, cell_crops_name)
    cell_cuttings_path = os.path.join(template_ws, cell_cuttings_name)
    crop_params_path = os.path.join(template_ws, crop_params_name)
    crop_coefs_path = os.path.join(template_ws, crop_coefs_name)


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
    logging.info('Template Workspace: {0}\n'.format(template_ws))

    ## Check input files
    if not arcpy.Exists(et_cells_path):
        logging.error('\nERROR: The ET Cell shapefile {} '+
                      'does not exist\n'.format(et_cells_path))
        sys.exit()
    elif not os.path.isfile(cell_props_path):
        logging.error(
            ('\nERROR: The cell properties template {} '+
             'does not exist\n').format(cell_props_path))
        sys.exit()
    elif not os.path.isfile(cell_crops_path):
        logging.error(
            ('\nERROR: The cell crops template {} '+
             'does not exist\n').format(cell_properties_path))
        sys.exit()
    elif not os.path.isfile(cell_cuttings_path):
        logging.error(
            ('\nERROR: The cell cuttings template {} '+
             'does not exist\n').format(cell_cuttings_path))
        sys.exit()
    elif not os.path.isfile(crop_params_path):
        logging.error(
            ('\nERROR: The crop parameters template {} '+
             'does not exist\n').format(crop_params_path))
        sys.exit()
    elif not os.path.isfile(crop_coefs_path):
        logging.error(
            ('\nERROR: The crop coefficients template {} '+
             'does not exist\n').format(crop_coefs_path))
        sys.exit()
    
    ##
    arcpy.CheckOutExtension('Spatial')
    arcpy.env.pyramid = 'NONE 0'
    arcpy.env.overwriteOutput = overwrite_flag
    arcpy.env.parallelProcessingFactor = 8

    ## Build output table folder if necessary
    if not os.path.isdir(static_ws):
        os.makedirs(static_ws)

    ## Copy the crop coefficients and parameters since these are not modified
    logging.info('Copying crop parameters and coefficients files')
    if (overwrite_flag or
        not os.path.isfile(os.path.join(static_ws, crop_params_name))):
        logging.debug('  {}'.format(crop_params_name))
        shutil.copy(crop_params_path, static_ws)
        ##shutil.copyfile(crop_params_path, os.path.join(static_ws, crop_params_name))
    if (overwrite_flag or
        not os.path.isfile(os.path.join(static_ws, crop_coefs_name))):
        logging.debug('  {}'.format(crop_coefs_name))
        shutil.copy(crop_coefs_path, static_ws)
        ##shutil.copyfile(crop_coefs_path, os.path.join(static_ws, crop_coefs_name))


    ##
    logging.debug('Reading ET Cell Zonal Stats')
    logging.debug('  {}'.format(et_cells_path))
    field_list = [f.name for f in arcpy.ListFields(et_cells_path)]
    logging.debug('  Fields: {}'.format(field_list))
    with arcpy.da.SearchCursor(et_cells_path, '*') as s_cursor:
        for row in s_cursor:
            print row
            raw_input('ENTER')
##            crop_dict = zone_crop_dict.pop(row[-1], dict())
##            for crop_i, crop_number in enumerate(crop_number_list):
##                ## Convert pixel counts to acreage
##                crop_pixels = crop_dict.pop(crop_number, 0)
##                row[crop_i] = crop_pixels * sqm_2_acres * snap_cs ** 2
##            u_cursor.updateRow(row) 


    ## Write Cell Properties



##    raster_list = [
##        [elev_field, 'MEAN', os.path.join(dem_ws, 'ned_30m_albers.img')],
##        [awc_field, 'MEAN', os.path.join(soil_ws, 'awc_30m_albers.img')],
##        [clay_field, 'MEAN', os.path.join(soil_ws, 'clay_30m_albers.img')],
##        [sand_field, 'MEAN', os.path.join(soil_ws, 'sand_30m_albers.img')],
##        ['AG_COUNT', 'SUM', agmask_path],
##        ['AG_ACRES', 'SUM', agmask_path],
##        ['AG_'+elev_field, 'MEAN', os.path.join(
##            dem_ws, 'dem_{}_30m_cdls.img'.format(cdl_year))],
##        ['AG_'+awc_field, 'MEAN', os.path.join(
##            soil_ws, 'awc_{}_30m_cdls.img'.format(cdl_year))],
##        ['AG_'+clay_field, 'MEAN', os.path.join(
##            soil_ws, 'clay_{}_30m_cdls.img'.format(cdl_year))],
##        ['AG_'+sand_field, 'MEAN', os.path.join(
##            soil_ws, 'sand_{}_30m_cdls.img'.format(cdl_year))]
##    ]
##
##    ## The zone field must be defined
##    if len(arcpy.ListFields(zone_path, zone_field)) == 0:
##        logging.error('\nERROR: The zone field {} does not exist\n'.format(
##            zone_field))
##        raise SystemExit()
##
##    ## The built in ArcPy zonal stats function fails if count >= 65536
##    zone_count = int(
##        arcpy.GetCount_management(zone_path).getOutput(0))
##    logging.info('\nZone count: {0}'.format(zone_count))
##    if zone_count >= 65536:
##        logging.error(
##            ('\nERROR: Zonal stats cannot be calculated since there '+
##             'are more than 65536 unique features\n').format(zone_field))
##        raise SystemExit()
##
##
##
##    ## Copy the zone_path
##    if overwrite_flag and arcpy.Exists(et_cells_path):
##        arcpy.Delete_management(et_cells_path)
##    if not arcpy.Exists(et_cells_path):
##        ## Join the input shapefile to the HUC and read in the matches
##        zone_field_list = [f.name for f in arcpy.ListFields(zone_path)]
##        zone_field_list.append(huc_field)
##        ##zone_field_list.append('OBJECTID_1')
##        arcpy.SpatialJoin_analysis(zone_path, huc_path, et_cells_path)
##        delete_field_list = [f.name for f in arcpy.ListFields(et_cells_path)
##                             if f.name not in zone_field_list]
##        logging.info('Deleting Fields')
##        for field_name in delete_field_list:
##            logging.debug('  {0}'.format(field_name))
##            try: arcpy.DeleteField_management(et_cells_path, field_name)
##            except: pass
##        ## Just copy the input shapefile
##        ##arcpy.Copy_management(zone_path, et_cells_path)
##
##
##    ## Get spatial reference
##    output_sr = arcpy.Describe(et_cells_path).spatialReference
##    snap_sr = arcpy.Raster(snap_raster).spatialReference
##    logging.debug('  Zone SR: {0}'.format(output_sr.name))
##    logging.debug('  Snap SR: {0}'.format(snap_sr.name))
##
##    ## Add lat/lon fields
##    logging.info('Adding Fields')
##    field_list = [f.name for f in arcpy.ListFields(et_cells_path)]
##    if lat_field not in field_list:
##        logging.debug('  {0}'.format(lat_field))
##        arcpy.AddField_management(et_cells_path, lat_field, 'DOUBLE')
##        lat_lon_flag = True
##    if lon_field not in field_list:
##        logging.debug('  {0}'.format(lon_field))
##        arcpy.AddField_management(et_cells_path, lon_field, 'DOUBLE')
##        lat_lon_flag = True
##    ## Cell/station ID
##    if cell_id_field not in field_list:
##        logging.debug('  {0}'.format(cell_id_field))
##        arcpy.AddField_management(et_cells_path, cell_id_field, 'LONG')
##    if cell_name_field not in field_list:
##        logging.debug('  {0}'.format(cell_name_field))
##        arcpy.AddField_management(et_cells_path, cell_name_field, 'TEXT', '', '', 20)
##    if station_id_field not in field_list:
##        logging.debug('  {0}'.format(station_id_field))
##        arcpy.AddField_management(et_cells_path, station_id_field, 'LONG')
##    if huc_field not in field_list:
##        logging.debug('  {0}'.format(huc_field))
##        arcpy.AddField_management(et_cells_path, huc_field, 'TEXT', '', '', 8)
##
##    ## Add zonal stats fields
##    for field_name, stat, raster_path in raster_list:
##        if field_name not in field_list:
##            logging.debug('  {0}'.format(field_name))
##            arcpy.AddField_management(et_cells_path, field_name, 'FLOAT')
##
##    ## Other soil fields
##    if awc_in_ft_field not in field_list:
##        logging.debug('  {0}'.format(awc_in_ft_field))
##        arcpy.AddField_management(et_cells_path, awc_in_ft_field, 'FLOAT', 8, 4)
##    if hydgrp_num_field not in field_list:
##        logging.debug('  {0}'.format(hydgrp_num_field))
##        arcpy.AddField_management(et_cells_path, hydgrp_num_field, 'SHORT')
##    if hydgrp_field not in field_list:
##        logging.debug('  {0}'.format(hydgrp_field))
##        arcpy.AddField_management(et_cells_path, hydgrp_field, 'TEXT', '', '', 1)
##
##
##    ## Calculate lat/lon
##    if latlon_flag:
##        logging.info('Calculating lat/lon')
##        cell_lat_lon_func(et_cells_path, 'LAT', 'LON', output_sr.GCS)
##
##    ## Set CELL_ID and STATION_ID to NLDAS_ID
##    arcpy.CalculateField_management(
##        et_cells_path, cell_id_field, '!{0}!'.format(zone_field), 'PYTHON')
##    arcpy.CalculateField_management(
##        et_cells_path, cell_name_field,
##        '"{0}"+str(!{1}!)'.format(cell_name_fmt, zone_field), 'PYTHON')
##        ##'"NLDAS 4km "+str(!{0}!)'.format(zone_field), 'PYTHON')
##    arcpy.CalculateField_management(
##        et_cells_path, station_id_field, '!{0}!'.format(zone_field), 'PYTHON')
##
##    ## Remove existing (could use overwrite instead)
##    zone_proj_path = os.path.join(table_ws, zone_proj_name)
##    zone_raster_path = os.path.join(table_ws, zone_raster_name)
##    if overwrite_flag and arcpy.Exists(zone_proj_path):
##        arcpy.Delete_management(zone_proj_path)
##    if overwrite_flag and arcpy.Exists(zone_raster_path):
##        arcpy.Delete_management(zone_raster_path)
##
##    ## Project zones to match CDL/snap coordinate system
##    logging.info('Projecting zones')
##    if (arcpy.Exists(et_cells_path) and not arcpy.Exists(zone_proj_path)):
##        arcpy.Project_management(et_cells_path, zone_proj_path, snap_sr)
##
##    ## Convert the zones polygon to raster
##    logging.info('Converting zones to raster')
##    if (arcpy.Exists(zone_proj_path) and not arcpy.Exists(zone_raster_path)):
##        arcpy.env.snapRaster = snap_raster
##        ##arcpy.env.extent = arcpy.Describe(snap_raster).extent
##        arcpy.FeatureToRaster_conversion(
##            zone_proj_path, zone_field, zone_raster_path, snap_cs)
##        arcpy.ClearEnvironment('snapRaster')
##        ##arcpy.ClearEnvironment('extent')
##
##    ## Link zone raster Value to zone field
##    fields = ('Value', zone_field)
##    zone_value_dict = {
##        row[0]:row[1]
##        for row in arcpy.da.SearchCursor(zone_raster_path, fields)}
##
##    ## Calculate zonal stats
##    logging.info('\nProcessing DEM and soil rasters')
##    for field_name, stat, raster_path in raster_list:
##        logging.info('  {0} {1}'.format(field_name, stat))
##        table_path = os.path.join(
##            table_ws, table_fmt.format(field_name.lower()))
##        if overwrite_flag and os.path.isfile(table_path):
##            arcpy.Delete_management(table_path)
##        if not os.path.isfile(table_path) and os.path.isfile(zone_raster_path):
##            table_obj = arcpy.sa.ZonalStatisticsAsTable(
##                zone_raster_path, 'VALUE', raster_path, table_path, 'DATA', stat)
##            del table_obj
##
##        ## Read in zonal stats values from table
##        ## Value is the Value in zone_raster_path (not the zone
##        zs_dict = {
##            zone_value_dict[row[0]]:row[1]
##            for row in arcpy.da.SearchCursor(table_path, ('Value', stat))}
##        ##zs_dict = dict()
##        ##fields = ('Value', stat)
##        ##with arcpy.da.SearchCursor(table_path, fields) as s_cursor:
##        ##    for row in s_cursor:
##        ##        zs_dict[row[0]] = row[1]
##
##        ## Write zonal stats values to zone polygon shapefile
##        fields = (zone_field, field_name)
##        with arcpy.da.UpdateCursor(et_cells_path, fields) as u_cursor:
##            for row in u_cursor:
##                row[1] = zs_dict.pop(row[0], 0)
##                u_cursor.updateRow(row) 
##
##    ## Calculate AWC in in/feet
##    logging.info('\nCalculating agricultural acreage')
##    arcpy.CalculateField_management(
##        et_cells_path, 'AG_ACRES',
##        '!AG_COUNT! * {0} * {1} * {1}'.format(sqm_2_acres, snap_cs), 'PYTHON')
##
##    ## Calculate AWC in in/feet
##    logging.info('Calculating AWC in in/ft')
##    arcpy.CalculateField_management(
##        et_cells_path, awc_in_ft_field, '!{0}! * 12'.format(awc_field), 'PYTHON')
##
##    ## Calculate AWC in in/feet
##    logging.info('Calculating elevation in feet')
##    arcpy.CalculateField_management(
##        et_cells_path, elev_field, '!{0}! * 3.28084'.format(elev_field), 'PYTHON')
##    arcpy.CalculateField_management(
##        et_cells_path, 'AG_'+elev_field,
##        '!{0}! * 3.28084'.format('AG_'+elev_field), 'PYTHON')
##
##    ## Calculate hydrologic group
##    logging.info('Calculating hydrologic group')
##    fields = (clay_field, sand_field, hydgrp_num_field, hydgrp_field)
##    with arcpy.da.UpdateCursor(et_cells_path, fields) as u_cursor:
##        for row in u_cursor:
##            if row[1] > 50:
##                row[2], row[3] = 1, 'A'
##            elif row[0] > 40:
##                row[2], row[3] = 3, 'C'
##            else:
##                row[2], row[3] = 2, 'B'
##            u_cursor.updateRow(row) 
##
##    ## Calculate crop zonal stats
##    logging.info('\nCalculating crop zonal stats')
##    table_path = os.path.join(table_ws, 'crops_table')
##    if arcpy.Exists(table_path):
##        arcpy.Delete_management(table_path)
##    table_obj = arcpy.sa.ZonalHistogram(
##        zone_raster_path, 'VALUE', agland_path, table_path)
##    del table_obj
##
##    ## Read in zonal stats values from table
##    logging.info('Reading crop zonal stats')
##    zone_crop_dict = defaultdict(dict)
##    field_name_list = [f.name for f in arcpy.ListFields(table_path)]
##    value_list = [f.split('_')[-1] for f in field_name_list]
##    logging.debug('  Crop histogram field list:\n    {0}'.format(
##        ', '.join(field_name_list)))
##    with arcpy.da.SearchCursor(table_path, '*') as s_cursor:
##        for i, row in enumerate(s_cursor):
##            ## Row id is 1 based, but FID/CDL is 0 based?
##            cdl_number = int(row[0] - 1)
##            ## Only 'crops' have a crop number (no shrub, water, urban, etc.)
##            if cdl_number not in crop_num_dict.keys():
##                logging.debug('  Skipping CDL {}'.format(cdl_number))
##                continue
##            ## Crop number can be an integer or list of integers (double crops)
##            crop_number = crop_num_dict[cdl_number]
##            ## Crop numbers of -1 are for crops that haven't been linked 
##            ##   to a CDL number
##            if not crop_number or crop_number == -1:
##                logging.warning('  Missing CDL {}'.format(cdl_number))
##                continue
##            ## Get values
##            for j, cell in enumerate(row):
##                if j > 0 and row[j] <> 0:
##                    ## Save acreage twice for double crops
##                    for c in crop_number:
##                        zone_str = zone_value_dict[int(value_list[j])]
##                        zone_crop_dict[zone_str][c] = row[j]
##    if cleanup_flag and arcpy.Exists(table_path):
##        arcpy.Delete_management(table_path)
##
##    ## Get unique crop number values and field names
##    crop_number_list = sorted(list(set([
##        crop_num for crop_dict in zone_crop_dict.values()
##        for crop_num in crop_dict.keys()])))
##    logging.info('Crop number list: '+', '.join(map(str, crop_number_list)))
##    crop_field_list = sorted([
##        'CROP_{0:02d}'.format(crop_num) for crop_num in crop_number_list])
##    logging.info('Crop field list: '+', '.join(crop_field_list))
##
##    ## Add fields for CDL values
##    for field_name in crop_field_list:
##        if field_name not in field_list:
##            logging.debug('  {0}'.format(field_name))
##            arcpy.AddField_management(et_cells_path, field_name, 'FLOAT')
##
##    ## Write zonal stats values to zone polygon shapefile
##    ## DEADBEEF - This is intenionally writing every cell
##    ##   0's are written for cells with nodata
##    fields = crop_field_list + [zone_field]
##    with arcpy.da.UpdateCursor(et_cells_path, fields) as u_cursor:
##        for row in u_cursor:
##            crop_dict = zone_crop_dict.pop(row[-1], dict())
##            for crop_i, crop_number in enumerate(crop_number_list):
##                ## Convert pixel counts to acreage
##                crop_pixels = crop_dict.pop(crop_number, 0)
##                row[crop_i] = crop_pixels * sqm_2_acres * snap_cs ** 2
##            u_cursor.updateRow(row) 
##
##    if cleanup_flag and arcpy.Exists(zone_proj_path):
##        arcpy.Delete_management(zone_proj_path)
##    if cleanup_flag and arcpy.Exists(zone_raster_path):
##        arcpy.Delete_management(zone_raster_path)

################################################################################

##def cell_lat_lon_func(hru_param_path, lat_field, lon_field, gcs_sr):
##    fields = ('SHAPE@XY', lon_field, lat_field)
##    with arcpy.da.UpdateCursor(hru_param_path, fields, '', gcs_sr) as u_cursor:
##        for row in u_cursor:
##            row[1], row[2] = row[0]
##            u_cursor.updateRow(row)
##            del row

def arg_parse():
    parser = argparse.ArgumentParser(
        description='ET-Demands Static Files',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        '--gis', nargs='?', default=os.getcwd(), metavar='FOLDER',
        help='GIS workspace/folder')
    parser.add_argument(
        '--year', default=2010, metavar='INT', type=int,
        choices=(2010, 2011, 2012, 2013, 2014), help='CDL year')
    parser.add_argument(
        '--huc', default=8, metavar='INT', type=int,
        choices=(8, 10), help='HUC level')
    parser.add_argument(
        '-ll', '--latlon', default=None, action='store_true',
        help='Calculate lat/lon')
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

    main(gis_ws=args.gis, cdl_year=args.year,
         huc=args.huc, latlon_flag=args.latlon,
         overwrite_flag=args.overwrite, cleanup_flag=args.clean)
