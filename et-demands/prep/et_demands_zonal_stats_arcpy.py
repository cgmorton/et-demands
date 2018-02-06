#--------------------------------
# Name:         et_demands_zonal_stats_arcpy.py
# Purpose:      Calculate zonal stats for all rasters
# Author:       Charles Morton
# Created       2017-01-11
# Python:       2.7
#--------------------------------

import argparse
from collections import defaultdict
import datetime as dt
import logging
import os
import sys

import arcpy

import _util as util


def main(gis_ws, input_soil_ws, cdl_year, zone_type='huc8',
         overwrite_flag=False, cleanup_flag=False):
    """Calculate zonal statistics needed to run ET-Demands model

    Args:
        gis_ws (str): Folder/workspace path of the GIS data for the project
        input_soil_ws (str): Folder/workspace path of the common soils data
        cdl_year (int): Cropland Data Layer year
        zone_type (str): Zone type (huc8, huc10, county)
        overwrite_flag (bool): If True, overwrite existing files
        cleanup_flag (bool): If True, remove temporary files

    Returns:
        None
    """
    logging.info('\nCalculating ET-Demands Zonal Stats')

    # DEADBEEF - Hard code for now
    if zone_type == 'huc10':
        zone_path = os.path.join(gis_ws, 'huc10', 'wbdhu10_albers.shp')
        zone_id_field = 'HUC10'
        zone_name_field = 'HUC10'
        zone_name_str = 'HUC10 '
    elif zone_type == 'huc8':
        zone_path = os.path.join(gis_ws, 'huc8', 'wbdhu8_albers.shp')
        zone_id_field = 'HUC8'
        zone_name_field = 'HUC8'
        zone_name_str = 'HUC8 '    
    elif zone_type == 'county':
        zone_path = os.path.join(
            gis_ws, 'counties', 'county_nrcs_a_mbr_albers.shp')
        zone_id_field = 'COUNTYNAME'
        # zone_id_field = 'FIPSCO'
        zone_name_field = 'COUNTYNAME'
        zone_name_str = ''
    elif zone_type == 'gridmet':
        zone_path = os.path.join(gis_ws, 'gridmet', 'gridmet_4km_cells_albers.shp')
        zone_id_field = 'GRIDMET_ID'
        zone_name_field = 'GRIDMET_ID'
        zone_name_str = 'GRIDMET_ID '    
    # elif zone_type == 'nldas':
    #     _path = os.path.join(
    #        gis_ws, 'counties', 'county_nrcs_a_mbr_albers.shp')
    #     _id_field = 'NLDAS_ID'
    #     _name_field = 'NLDAS_ID'
    #     _name_str = 'NLDAS_4km_'

    # station_id_field = 'NLDAS_ID'

    et_cells_path = os.path.join(gis_ws, 'ETCells.shp')
    # if gdb_flag:
    #     _path = os.path.join(
    #        os.path.dirname(gis_ws), 'et-demands_py\et_demands.gdb')
    #     _cells_path = os.path.join(gdb_path, 'et_cells')
    # else:
    #     _cells_path = os.path.join(gis_ws, 'ETCells.shp')

    cdl_ws = os.path.join(gis_ws, 'cdl')
    soil_ws = os.path.join(gis_ws, 'soils')
    zone_ws = os.path.dirname(zone_path)

    agland_path = os.path.join(
        cdl_ws, 'agland_{}_30m_cdls.img'.format(cdl_year))
    agmask_path = os.path.join(
        cdl_ws, 'agmask_{}_30m_cdls.img'.format(cdl_year))
    table_fmt = 'zone_{0}.dbf'

    # Field names
    cell_lat_field = 'LAT'
    cell_lon_field = 'LON'
    cell_id_field = 'CELL_ID'
    cell_name_field = 'CELL_NAME'
    met_id_field = 'STATION_ID'
    awc_field = 'AWC'
    clay_field = 'CLAY'
    sand_field = 'SAND'
    awc_in_ft_field = 'AWC_IN_FT'
    hydgrp_num_field = 'HYDGRP_NUM'
    hydgrp_field = 'HYDGRP'

    # active_flag_field = 'ACTIVE_FLAG'
    # irrig_flag_field = 'IRRIGATION_FLAG'
    # permeability_field = 'PERMEABILITY'
    # soil_depth_field = 'SOIL_DEPTH'
    # aridity_field = 'ARIDITY'
    # dairy_cutting_field = 'DAIRY_CUTTINGS'
    # beef_cutting_field = 'BEEF_CUTTINGS'

    # active_flag_default = 1
    # irrig_flag_default = 1
    # permeability_default = -999
    # soil_depth_default = 60         # inches
    # aridity_default = 50
    # dairy_cutting_default = 3
    # beef_cutting_default = 2

    # Output names/paths
    zone_proj_name = 'zone_proj.shp'
    zone_raster_name = 'zone_raster.img'
    table_ws = os.path.join(gis_ws, 'zone_tables')

    #
    snap_raster = os.path.join(cdl_ws, '{}_30m_cdls.img'.format(cdl_year))
    # snap_cs = 30
    sqm_2_acres = 0.000247105381        # From google

    # Link ET demands crop number (1-84) with CDL values (1-255)
    # Key is CDL number, value is crop number, comment is CDL class name
    crop_num_dict = dict()
    crop_num_dict[1] = [7]     # Corn -> Field Corn
    crop_num_dict[2] = [58]    # Cotton -> Cotton
    crop_num_dict[3] = [65]    # Rice -> Rice
    crop_num_dict[4] = [60]    # Sorghum -> Sorghum
    crop_num_dict[5] = [66]    # Soybeans -> Soybeans
    crop_num_dict[6] = [36]    # Sunflower -> Sunflower -irrigated
    crop_num_dict[10] = [67]   ## Peanuts -> Peanuts
    crop_num_dict[11] = [36]   ## Tobacco -> Sunflower -irrigated
    crop_num_dict[12] = [9]    # Sweet Corn -> Sweet Corn Early Plant
    crop_num_dict[13] = [7]     # Pop or Orn Corn -> Field Corn
    crop_num_dict[14] = [33]    # Mint -> Mint
    crop_num_dict[21] = [11]    # Barley -> Spring Grain - irrigated
    crop_num_dict[22] = [11]    # Durum Wheat -> Spring Grain - irrigated
    crop_num_dict[23] = [11]    # Spring Wheat -> Spring Grain - irrigated
    crop_num_dict[24] = [13]    # Winter Wheat -> Winter Grain - irrigated
    crop_num_dict[25] = [11]    # Other Small Grains -> Spring Grain - irrigated
    crop_num_dict[26] = [13, 85]    # Dbl Crop WinWht/Soybeans -> Soybeans After Another Crop
    crop_num_dict[27] = [11]    # Rye -> Spring Grain - irrigated
    crop_num_dict[28] = [11]    # Oats -> Spring Grain - irrigated
    crop_num_dict[29] = [68]    # Millet -> Millet
    crop_num_dict[30] = [11]    # Speltz -> Spring Grain - irrigated
    crop_num_dict[31] = [40]    # Canola -> Canola
    crop_num_dict[32] = [11]    # Flaxseed -> Spring Grain - irrigated
    crop_num_dict[33] = [38]    # Safflower -> Safflower -irrigated
    crop_num_dict[34] = [41]    # Rape Seed -> Mustard
    crop_num_dict[35] = [41]    # Mustard -> Mustard
    crop_num_dict[36] = [3]     # Alfalfa -> Alfalfa - Beef Style
    crop_num_dict[37] = [4]     # Other Hay/Non Alfalfa -> Grass Hay
    crop_num_dict[38] = [41]    # Camelina -> Mustard
    crop_num_dict[39] = [41]    # Buckwheat -> Mustard
    crop_num_dict[41] = [31]    # Sugarbeets -> Sugar beets
    crop_num_dict[42] = [5]     # Dry Beans -> Snap and Dry Beans - fresh
    crop_num_dict[43] = [30]    # Potatoes -> Potatoes
    crop_num_dict[44] = [11]    # Other Crops -> Spring Grain - irrigated
    crop_num_dict[45] = [76]    # Sugarcane -> Sugarcane
    crop_num_dict[46] = [30]    # Sweet Potatoes -> Potatoes
    crop_num_dict[47] = [21]    # Misc Vegs & Fruits -> Garden Vegetables  - general
    crop_num_dict[48] = [24]    # Watermelons -> Melons
    crop_num_dict[49] = [23]    # Onions -> Onions
    crop_num_dict[50] = [21]    # Cucumbers -> Garden Vegetables  - general
    crop_num_dict[51] = [5]     # Chick Peas -> Snap and Dry Beans - fresh
    crop_num_dict[52] = [5]     # Lentils -> Snap and Dry Beans - fresh
    crop_num_dict[53] = [27]    # Peas -> Peas--fresh
    crop_num_dict[54] = [69]    # Tomatoes -> Tomatoes
    crop_num_dict[55] = [75]    # Caneberries -> Cranberries
    crop_num_dict[56] = [32]    # Hops -> Hops
    crop_num_dict[57] = [21]    # Herbs -> Garden Vegetables  - general
    crop_num_dict[58] = [41]    # Clover/Wildflowers -> Mustard
    crop_num_dict[59] = [17]    # Sod/Grass Seed -> Grass - Turf (lawns) -irrigated
    crop_num_dict[60] = [81]    # Switchgrass -> Sudan
    crop_num_dict[66] = [19]    # Cherries -> Orchards - Apples and Cherries w/ground cover
    crop_num_dict[67] = [19]    # Peaches -> Orchards - Apples and Cherries w/ground cover
    crop_num_dict[68] = [19]    # Apples -> Orchards - Apples and Cherries w/ground cover
    crop_num_dict[69] = [25]    # Grapes -> Grapes
    crop_num_dict[70] = [82]    # Christmas Trees -> Christmas Trees
    crop_num_dict[71] = [19]    # Other Tree Crops -> Orchards - Apples and Cherries w/ground cover
    crop_num_dict[72] = [70]    # Citrus -> Oranges
    crop_num_dict[74] = [74]    # Pecans -> Nuts
    crop_num_dict[75] = [74]    # Almonds -> Nuts
    crop_num_dict[76] = [74]    # Walnuts -> Nuts
    crop_num_dict[77] = [19]    # Pears -> Orchards - Apples and Cherries w/ground cover
    crop_num_dict[176] = [15]    # Grassland/Pasture -> Grass Pasture - high management
    crop_num_dict[204] = [74]    # Pistachios -> Nuts
    crop_num_dict[205] = [11]    # Triticale -> Spring Grain - irrigated
    crop_num_dict[206] = [22]    # Carrots -> Carrots
    crop_num_dict[207] = [21]    # Asparagus -> Aparagus
    crop_num_dict[208] = [43]    # Garlic -> Garlic
    crop_num_dict[209] = [24]    # Cantaloupes -> Melons
    crop_num_dict[210] = [19]    # Prunes -> Orchards - Apples and Cherries w/ground cover
    crop_num_dict[211] = [61]    # Olives -> Olives
    crop_num_dict[212] = [70]    # Oranges -> Oranges
    crop_num_dict[213] = [24]    # Honeydew Melons -> Melons
    crop_num_dict[214] = [21]    # Broccoli -> Garden Vegetables  - general
    crop_num_dict[216] = [59]    # Peppers -> Peppers
    crop_num_dict[217] = [19]    # Pomegranates -> Orchards - Apples and Cherries w/ground cover
    crop_num_dict[218] = [19]    # Nectarines -> Orchards - Apples and Cherries w/ground cover
    crop_num_dict[219] = [21]    # Greens -> Garden Vegetables  - general
    crop_num_dict[220] = [19]    # Plums -> Orchards - Apples and Cherries w/ground cover
    crop_num_dict[221] = [62]    # Strawberries -> Strawberries
    crop_num_dict[222] = [21]    # Squash -> Garden Vegetables  - general
    crop_num_dict[223] = [19]    # Apricots -> Orchards - Apples and Cherries w/ground cover
    crop_num_dict[224] = [6]     # Vetch -> Snap and Dry Beans - seed
    crop_num_dict[225] = [77]    # Dbl Crop WinWht/Corn -> Field Corn After Another Crop
    crop_num_dict[226] = [77]    # Dbl Crop Oats/Corn -> Field Corn After Another Crop
    crop_num_dict[227] = [71]    # Lettuce -> Lettuce (Single Crop)
    crop_num_dict[229] = [21]    # Pumpkins -> Garden Vegetables  - general
    crop_num_dict[230] = [71, 84]    # Dbl Crop Lettuce/Durum Wht -> Grain After Another Crop
    crop_num_dict[231] = [71, 83]    # Dbl Crop Lettuce/Cantaloupe -> Melons After Another Crop
    crop_num_dict[232] = [71, 79]    # Dbl Crop Lettuce/Cotton -> Cotton After Another Crop
    crop_num_dict[233] = [71, 84]    # Dbl Crop Lettuce/Barley -> Grain After Another Crop
    crop_num_dict[234] = [71, 78]    # Dbl Crop Durum Wht/Sorghum -> Sorghum After Another Crop
    crop_num_dict[235] = [71, 78]    # Dbl Crop Barley/Sorghum -> Sorghum After Another Crop
    crop_num_dict[236] = [13, 78]    # Dbl Crop WinWht/Sorghum -> Sorghum After Another Crop
    crop_num_dict[237] = [11, 77]    # Dbl Crop Barley/Corn -> Field Corn After Another Crop
    crop_num_dict[238] = [13, 79]    # Dbl Crop WinWht/Cotton -> Cotton After Another Crop
    crop_num_dict[239] = [66, 79]    # Dbl Crop Soybeans/Cotton -> Cotton After Another Crop
    crop_num_dict[240] = [66, 84]    # Dbl Crop Soybeans/Oats -> Grain After Another Crop
    crop_num_dict[241] = [7, 85]    # Dbl Crop Corn/Soybeans -> Soybeans After Another Crop
    crop_num_dict[242] = [63]    # Blueberries -> Blueberries
    crop_num_dict[243] = [80]    # Cabbage -> Cabbage
    crop_num_dict[244] = [21]    # Cauliflower -> Garden Vegetables  - general
    crop_num_dict[245] = [21]    # Celery -> Garden Vegetables  - general
    crop_num_dict[246] = [21]    # Radishes -> Garden Vegetables  - general
    crop_num_dict[247] = [21]    # Turnips -> Garden Vegetables  - general
    crop_num_dict[248] = [21]    # Eggplants -> Garden Vegetables  - general
    crop_num_dict[249] = [21]    # Gourds -> Garden Vegetables  - general
    crop_num_dict[250] = [75]    # Cranberries -> Cranberries
    crop_num_dict[254] = [11, 85]    # Dbl Crop Barley/Soybeans -> Soybeans After Another Crop
    crop_num_dict[99] = [20]    #Empty CDL Placeholder for Orchards without Cover
    crop_num_dict[98] = [85]    #Empty CDL Placeholder for AgriMet based "Grass Pasture- Mid Management"
    crop_num_dict[97] = [16]    #Empty CDL Placeholder for "Grass Pasture- Low Management"

    # Check input folders
    if not os.path.isdir(gis_ws):
        logging.error(('\nERROR: The GIS workspace {0} ' +
                       'does not exist\n').format(gis_ws))
        sys.exit()
    elif not os.path.isdir(cdl_ws):
        logging.error(('\nERROR: The CDL workspace {0} ' +
                       'does not exist\n').format(cdl_ws))
        sys.exit()
    elif not os.path.isdir(soil_ws):
        logging.error(('\nERROR: The soil workspace {0} ' +
                       'does not exist\n').format(soil_ws))
        sys.exit()
    elif input_soil_ws != soil_ws and not os.path.isdir(input_soil_ws):
        logging.error(('\nERROR: The input soil folder {} ' +
                       'does not exist\n').format(input_soil_ws))
        sys.exit()
    elif not os.path.isdir(zone_ws):
        logging.error(('\nERROR: The zone workspace {0} ' +
                       'does not exist\n').format(zone_ws))
        sys.exit()
    logging.info('\nGIS Workspace:   {0}'.format(gis_ws))
    logging.info('CDL Workspace:   {0}'.format(cdl_ws))
    logging.info('Soil Workspace:  {0}'.format(soil_ws))
    if input_soil_ws != soil_ws:
        logging.info('Soil Workspace:  {0}'.format(input_soil_ws))
    logging.info('Zone Workspace:  {0}'.format(zone_ws))

    # Check input files
    if not os.path.isfile(snap_raster):
        logging.error('\nERROR: The snap raster {} ' +
                      'does not exist\n'.format(snap_raster))
        sys.exit()
    elif not os.path.isfile(agland_path):
        logging.error('\nERROR: The agland raster {0} ' +
                      'does not exist\n'.format(agland_path))
        sys.exit()
    elif not os.path.isfile(agland_path):
        logging.error('\nERROR: The agmask raster {0} ' +
                      'does not exist\n'.format(agland_path))
        sys.exit()
    elif not os.path.isfile(zone_path):
        logging.error('\nERROR: The zone shapefile {0} ' +
                      'does not exist\n'.format(zone_path))
        sys.exit()

    arcpy.CheckOutExtension('Spatial')
    arcpy.env.pyramid = 'NONE 0'
    arcpy.env.overwriteOutput = overwrite_flag
    arcpy.env.parallelProcessingFactor = 8

    # Build output table folder if necessary
    if not os.path.isdir(table_ws):
        os.makedirs(table_ws)
    # if gdb_flag and not os.path.isdir(os.path.dirname(gdb_path)):
    #     os.makedirs(os.path.dirname(gdb_path))

    # Remove existing data if overwrite
    # if overwrite_flag and arcpy.Exists(et_cells_path):
    #     arcpy.Delete_management(et_cells_path)
    # if overwrite_flag and gdb_flag and arcpy.Exists(gdb_path):
    #     shutil.rmtree(gdb_path)

    # # Build output geodatabase if necessary
    # if gdb_flag and not arcpy.Exists(gdb_path):
    #     arcpy.CreateFileGDB_management(
    #         os.path.dirname(gdb_path), os.path.basename(gdb_path))

    raster_list = [
        [awc_field, 'MEAN', os.path.join(input_soil_ws, 'AWC_30m_albers.img')],
        [clay_field, 'MEAN', os.path.join(input_soil_ws, 'CLAY_30m_albers.img')],
        [sand_field, 'MEAN', os.path.join(input_soil_ws, 'SAND_30m_albers.img')],
        ['AG_COUNT', 'SUM', agmask_path],
        ['AG_ACRES', 'SUM', agmask_path],
        ['AG_' + awc_field, 'MEAN', os.path.join(
            soil_ws, 'AWC_{}_30m_cdls.img'.format(cdl_year))],
        ['AG_' + clay_field, 'MEAN', os.path.join(
            soil_ws, 'CLAY_{}_30m_cdls.img'.format(cdl_year))],
        ['AG_' + sand_field, 'MEAN', os.path.join(
            soil_ws, 'SAND_{}_30m_cdls.img'.format(cdl_year))]
    ]

    # The zone field must be defined
    if len(arcpy.ListFields(zone_path, zone_id_field)) == 0:
        logging.error('\nERROR: The zone ID field {} does not exist\n'.format(
            zone_id_field))
        sys.exit()
    elif len(arcpy.ListFields(zone_path, zone_name_field)) == 0:
        logging.error(
            '\nERROR: The zone name field {} does not exist\n'.format(
                zone_name_field))
        sys.exit()

    # The built in ArcPy zonal stats function fails if count >= 65536
    zone_count = int(
        arcpy.GetCount_management(zone_path).getOutput(0))
    logging.info('\nZone count: {0}'.format(zone_count))
    if zone_count >= 65536:
        logging.error(
            ('\nERROR: Zonal stats cannot be calculated since there ' +
             'are more than 65536 unique features\n').format(zone_field))
        sys.exit()

    # Copy the zone_path
    if overwrite_flag and arcpy.Exists(et_cells_path):
        arcpy.Delete_management(et_cells_path)
    # Just copy the input shapefile
    if not arcpy.Exists(et_cells_path):
        arcpy.Copy_management(zone_path, et_cells_path)
    # Join the stations to the zones and read in the matches
    # if not arcpy.Exists(et_cells_path):
    #     _field_list = [f.name for f in arcpy.ListFields(zone_path)]
    #     _field_list.append(met_id_field)
    #      zone_field_list.append('OBJECTID_1')
    #     .SpatialJoin_analysis(zone_path, station_path, et_cells_path)
    #      arcpy.SpatialJoin_analysis(station_path, zone_path, et_cells_path)
    #     _field_list = [f.name for f in arcpy.ListFields(et_cells_path)
    #                         if f.name not in zone_field_list]
    #     .info('Deleting Fields')
    #      field_name in delete_field_list:
    #        logging.debug('  {0}'.format(field_name))
    #        try: arcpy.DeleteField_management(et_cells_path, field_name)
    #        except: pass


    # Get spatial reference
    output_sr = arcpy.Describe(et_cells_path).spatialReference
    snap_sr = arcpy.Raster(snap_raster).spatialReference
    snap_cs = arcpy.Raster(snap_raster).meanCellHeight
    logging.debug('  Zone SR: {0}'.format(output_sr.name))
    logging.debug('  Snap SR: {0}'.format(snap_sr.name))
    logging.debug('  Snap Cellsize: {0}'.format(snap_cs))

    # Add lat/lon fields
    logging.info('Adding Fields')
    field_list = [f.name for f in arcpy.ListFields(et_cells_path)]
    if cell_lat_field not in field_list:
        logging.debug('  {0}'.format(cell_lat_field))
        arcpy.AddField_management(et_cells_path, cell_lat_field, 'DOUBLE')
        lat_lon_flag = True
    if cell_lon_field not in field_list:
        logging.debug('  {0}'.format(cell_lon_field))
        arcpy.AddField_management(et_cells_path, cell_lon_field, 'DOUBLE')
        lat_lon_flag = True
    # Cell/station ID
    if cell_id_field not in field_list:
        logging.debug('  {0}'.format(cell_id_field))
        arcpy.AddField_management(
            et_cells_path, cell_id_field, 'TEXT', '', '', 24)
    if cell_name_field not in field_list:
        logging.debug('  {0}'.format(cell_name_field))
        arcpy.AddField_management(
            et_cells_path, cell_name_field, 'TEXT', '', '', 48)
    if met_id_field not in field_list:
        logging.debug('  {0}'.format(met_id_field))
        arcpy.AddField_management(
            et_cells_path, met_id_field, 'TEXT', '', '', 24)
    if zone_id_field not in field_list:
        logging.debug('  {0}'.format(zone_id_field))
        arcpy.AddField_management(
            et_cells_path, zone_id_field, 'TEXT', '', '', 8)

    # Status flags
    # if active_flag_field not in field_list:
    #     .debug('  {0}'.format(active_flag_field))
    #     .AddField_management(et_cells_path, active_flag_field, 'SHORT')
    # if irrig_flag_field not in field_list:
    #     .debug('  {0}'.format(irrig_flag_field))
    #     .AddField_management(et_cells_path, irrig_flag_field, 'SHORT')
    # Add zonal stats fields
    for field_name, stat, raster_path in raster_list:
        if field_name not in field_list:
            logging.debug('  {0}'.format(field_name))
            arcpy.AddField_management(et_cells_path, field_name, 'FLOAT')

    # Other soil fields
    if awc_in_ft_field not in field_list:
        logging.debug('  {0}'.format(awc_in_ft_field))
        arcpy.AddField_management(
            et_cells_path, awc_in_ft_field, 'FLOAT', 8, 4)
    if hydgrp_num_field not in field_list:
        logging.debug('  {0}'.format(hydgrp_num_field))
        arcpy.AddField_management(et_cells_path, hydgrp_num_field, 'SHORT')
    if hydgrp_field not in field_list:
        logging.debug('  {0}'.format(hydgrp_field))
        arcpy.AddField_management(
            et_cells_path, hydgrp_field, 'TEXT', '', '', 1)
    # if permeability_field not in field_list:
    #     .debug('  {0}'.format(permeability_field))
    #     .AddField_management(et_cells_path, permeability_field, 'FLOAT')
    # if soil_depth_field not in field_list:
    #     .debug('  {0}'.format(soil_depth_field))
    #     .AddField_management(et_cells_path, soil_depth_field, 'FLOAT')
    # if aridity_field not in field_list:
    #     .debug('  {0}'.format(aridity_field))
    #     .AddField_management(et_cells_path, aridity_field, 'FLOAT')

    # Cuttings
    # if dairy_cutting_field not in field_list:
    #     .debug('  {0}'.format(dairy_cutting_field))
    #     .AddField_management(et_cells_path, dairy_cutting_field, 'SHORT')
    # if beef_cutting_field not in field_list:
    #     .debug('  {0}'.format(beef_cutting_field))
    #     .AddField_management(et_cells_path, beef_cutting_field, 'SHORT')

    # Crop fields are only added for needed crops (after zonal histogram)
    # for crop_num in crop_num_list:
    #     _name = 'CROP_{0:02d}'.format(crop_num)
    #      field_name not in field_list:
    #        logging.debug('  {0}'.format(field_name))
    #        arcpy.AddField_management(et_cells_path, field_name, 'LONG')

    # Calculate lat/lon
    logging.info('Calculating lat/lon')
    cell_lat_lon_func(et_cells_path, 'LAT', 'LON', output_sr.GCS)

    # Set CELL_ID and CELL_NAME
    #zone_id_field must be a string
    arcpy.CalculateField_management(
        et_cells_path, cell_id_field,
        'str(!{0}!)'.format(zone_id_field), 'PYTHON')
    arcpy.CalculateField_management(
        et_cells_path, cell_name_field,
        '"{0}" + str(!{1}!)'.format(zone_name_str, zone_name_field), 'PYTHON')
    # Set MET_ID (STATION_ID) to NLDAS_ID
    # arcpy.CalculateField_management(
    #     et_cells_path, met_id_field,
    #     'str(!{0}!)'.format(station_id_field), 'PYTHON')

    # Remove existing (could use overwrite instead)
    zone_proj_path = os.path.join(table_ws, zone_proj_name)
    zone_raster_path = os.path.join(table_ws, zone_raster_name)
    if overwrite_flag and arcpy.Exists(zone_proj_path):
        arcpy.Delete_management(zone_proj_path)
    if overwrite_flag and arcpy.Exists(zone_raster_path):
        arcpy.Delete_management(zone_raster_path)

    # Project zones to match CDL/snap coordinate system
    logging.info('Projecting zones')
    if (arcpy.Exists(et_cells_path) and not arcpy.Exists(zone_proj_path)):
        arcpy.Project_management(et_cells_path, zone_proj_path, snap_sr)

    # Convert the zones polygon to raster
    logging.info('Converting zones to raster')
    if (arcpy.Exists(zone_proj_path) and not arcpy.Exists(zone_raster_path)):
        arcpy.env.snapRaster = snap_raster
        # arcpy.env.extent = arcpy.Describe(snap_raster).extent
        arcpy.FeatureToRaster_conversion(
            zone_proj_path, cell_id_field, zone_raster_path, snap_cs)
        arcpy.ClearEnvironment('snapRaster')
        # arcpy.ClearEnvironment('extent')
    # Link zone raster Value to zone field
    #zone_id_field must be a string
    fields = ('Value', cell_id_field)
    print(fields)
    print(zone_raster_path)
    zone_value_dict = {
        row[0]: row[1]
        for row in arcpy.da.SearchCursor(zone_raster_path, fields)}
    # Calculate zonal stats
    logging.info('\nProcessing soil rasters')
    for field_name, stat, raster_path in raster_list:
        logging.info('  {0} {1}'.format(field_name, stat))
        table_path = os.path.join(
            table_ws, table_fmt.format(field_name.lower()))
        if overwrite_flag and os.path.isfile(table_path):
            arcpy.Delete_management(table_path)
        if not os.path.isfile(table_path) and os.path.isfile(zone_raster_path):
            table_obj = arcpy.sa.ZonalStatisticsAsTable(
                zone_raster_path, 'VALUE', raster_path,
                table_path, 'DATA', stat)
            del table_obj

        # Read in zonal stats values from table
        # Value is the Value in zone_raster_path (not the zone
        zs_dict = {
            zone_value_dict[row[0]]: row[1]
            for row in arcpy.da.SearchCursor(table_path, ('Value', stat))}
        # zs_dict = dict()
        # fields = ('Value', stat)
        # with arcpy.da.SearchCursor(table_path, fields) as s_cursor:
        #      row in s_cursor:
        #        zs_dict[row[0]] = row[1]

        # Write zonal stats values to zone polygon shapefile
        fields = (cell_id_field, field_name)
        with arcpy.da.UpdateCursor(et_cells_path, fields) as u_cursor:
            for row in u_cursor:
                row[1] = zs_dict.pop(row[0], 0)
                u_cursor.updateRow(row)

    # Calculate agricultural area in acres
    logging.info('\nCalculating agricultural acreage')
    arcpy.CalculateField_management(
        et_cells_path, 'AG_ACRES',
        '!AG_COUNT! * {0} * {1} * {1}'.format(sqm_2_acres, snap_cs), 'PYTHON')

    # Calculate AWC in in/feet
    logging.info('Calculating AWC in in/ft')
    arcpy.CalculateField_management(
        et_cells_path, awc_in_ft_field,
        '!{0}! * 12'.format(awc_field), 'PYTHON')

    # Calculate hydrologic group
    logging.info('Calculating hydrologic group')
    fields = (clay_field, sand_field, hydgrp_num_field, hydgrp_field)
    with arcpy.da.UpdateCursor(et_cells_path, fields) as u_cursor:
        for row in u_cursor:
            if row[1] > 50:
                row[2], row[3] = 1, 'A'
            elif row[0] > 40:
                row[2], row[3] = 3, 'C'
            else:
                row[2], row[3] = 2, 'B'
            u_cursor.updateRow(row)

    # Calculate default values
    # logging.info('\nCalculating default values')
    # logging.info('  {0:10s}: {1}'.format(active_flag_field, active_flag_default))
    # arcpy.CalculateField_management(
    #     _cells_path, active_flag_field, active_flag_default, 'PYTHON')
    # logging.info('  {0:10s}: {1}'.format(irrig_flag_field, irrig_flag_default))
    # arcpy.CalculateField_management(
    #     _cells_path, irrig_flag_field, irrig_flag_default, 'PYTHON')

    # logging.info('  {0:10s}: {1}'.format(permeability_field, permeability_default))
    # arcpy.CalculateField_management(
    #     _cells_path, permeability_field, permeability_default, 'PYTHON')
    # logging.info('  {0:10s}: {1}'.format(soil_depth_field, soil_depth_default))
    # arcpy.CalculateField_management(
    #     _cells_path, soil_depth_field, soil_depth_default, 'PYTHON')
    # logging.info('  {0:10s}: {1}'.format(aridity_field, aridity_default))
    # arcpy.CalculateField_management(
    #     _cells_path, aridity_field, aridity_default, 'PYTHON')

    # logging.info('  {0:10s}: {1}'.format(dairy_cutting_field, dairy_cutting_default))
    # arcpy.CalculateField_management(
    #     _cells_path, dairy_cutting_field, dairy_cutting_default, 'PYTHON')
    # logging.info('  {0:10s}: {1}'.format(beef_cutting_field, beef_cutting_default))
    # arcpy.CalculateField_management(
    #     _cells_path, beef_cutting_field, beef_cutting_default, 'PYTHON')

    # Calculate crop zonal stats
    logging.info('\nCalculating crop zonal stats')
    table_path = os.path.join(table_ws, 'crops_table')
    if arcpy.Exists(table_path):
        arcpy.Delete_management(table_path)
    table_obj = arcpy.sa.ZonalHistogram(
        zone_raster_path, 'VALUE', agland_path, table_path)
    del table_obj

    # Read in zonal stats values from table
    logging.info('Reading crop zonal stats')
    zone_crop_dict = defaultdict(dict)
    field_name_list = [f.name for f in arcpy.ListFields(table_path)]
    value_list = [f.split('_')[-1] for f in field_name_list]
    logging.debug('  Crop histogram field list:\n    {0}'.format(
        ', '.join(field_name_list)))
    with arcpy.da.SearchCursor(table_path, '*') as s_cursor:
        for i, row in enumerate(s_cursor):
            # Row id is 1 based, but FID/CDL is 0 based?
            cdl_number = int(row[0] - 1)
            # Only 'crops' have a crop number (no shrub, water, urban, etc.)
            if cdl_number not in crop_num_dict.keys():
                logging.debug('  Skipping CDL {}'.format(cdl_number))
                continue
            # Crop number can be an integer or list of integers (double crops)
            crop_number = crop_num_dict[cdl_number]
            # Crop numbers of -1 are for crops that haven't been linked
            #   to a CDL number
            if not crop_number or crop_number == -1:
                logging.warning('  Missing CDL {}'.format(cdl_number))
                continue
            # Get values
            for j, cell in enumerate(row):
                if j > 0 and row[j] != 0:
                    # Save acreage twice for double crops
                    for c in crop_number:
                        zone_str = zone_value_dict[int(value_list[j])]
                        zone_crop_dict[zone_str][c] = row[j]
    if cleanup_flag and arcpy.Exists(table_path):
        arcpy.Delete_management(table_path)

    # Get unique crop number values and field names
    crop_number_list = sorted(list(set([
        crop_num for crop_dict in zone_crop_dict.values()
        for crop_num in crop_dict.keys()])))
    logging.debug('Crop number list: ' + ', '.join(map(str, crop_number_list)))
    crop_field_list = sorted([
        'CROP_{0:02d}'.format(crop_num) for crop_num in crop_number_list])
    logging.debug('Crop field list: ' + ', '.join(crop_field_list))

    # Add fields for CDL values
    logging.info('Writing crop zonal stats')
    for field_name in crop_field_list:
        if field_name not in field_list:
            logging.debug('  {0}'.format(field_name))
            arcpy.AddField_management(et_cells_path, field_name, 'FLOAT')

    # Write zonal stats values to zone polygon shapefile
    # DEADBEEF - This is intenionally writing every cell
    #   0's are written for cells with nodata
    fields = crop_field_list + [cell_id_field]
    with arcpy.da.UpdateCursor(et_cells_path, fields) as u_cursor:
        for row in u_cursor:
            crop_dict = zone_crop_dict.pop(row[-1], dict())
            for crop_i, crop_number in enumerate(crop_number_list):
                # Convert pixel counts to acreage
                crop_pixels = crop_dict.pop(crop_number, 0)
                row[crop_i] = crop_pixels * sqm_2_acres * snap_cs ** 2
            u_cursor.updateRow(row)

    if cleanup_flag and arcpy.Exists(zone_proj_path):
        arcpy.Delete_management(zone_proj_path)
    if cleanup_flag and arcpy.Exists(zone_raster_path):
        arcpy.Delete_management(zone_raster_path)


def cell_lat_lon_func(hru_param_path, lat_field, lon_field, gcs_sr):
    """"""
    fields = ('SHAPE@XY', lon_field, lat_field)
    with arcpy.da.UpdateCursor(hru_param_path, fields, '', gcs_sr) as u_cursor:
        for row in u_cursor:
            row[1], row[2] = row[0]
            u_cursor.updateRow(row)
            del row


def arg_parse():
    """"""
    parser = argparse.ArgumentParser(
        description='ET-Demands Zonal Stats',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        '--gis', nargs='?', default=os.path.join(os.getcwd(), 'gis'),
        type=lambda x: util.is_valid_directory(parser, x),
        help='GIS workspace/folder', metavar='FOLDER')
    parser.add_argument(
        '--zone', default='huc8', metavar='', type=str,
        choices=('huc8', 'huc10', 'county','gridmet'),
        help='Zone type [{}]'.format(', '.join(['huc8', 'huc10', 'county','gridmet'])))
    parser.add_argument(
        '-y', '--year', metavar='YEAR', required=True, type=int,
        help='CDL year')
    parser.add_argument(
        '--soil', metavar='FOLDER',
        nargs='?', default=os.path.join(os.getcwd(), 'gis', 'soils'),
        type=lambda x: util.is_valid_directory(parser, x),
        help='Common soil workspace/folder')
    parser.add_argument(
        '-o', '--overwrite', default=None, action='store_true',
        help='Overwrite existing file')
    parser.add_argument(
        '--clean', default=None, action='store_true',
        help='Remove temporary datasets')
    parser.add_argument(
        '--debug', default=logging.INFO, const=logging.DEBUG,
        help='Debug level logging', action="store_const", dest="loglevel")
    # parser.add_argument(
    #    '--station', nargs='?', required=True,
    #     =lambda x: util.is_valid_file(parser, x),
    #     ='Weather station shapefile', metavar='FILE')
    # parser.add_argument(
    #    '--gdb', default=None, action='store_true',
    #     ='Write ETCells to a geodatabase')
    args = parser.parse_args()

    # Convert relative paths to absolute paths
    if args.gis and os.path.isdir(os.path.abspath(args.gis)):
        args.gis = os.path.abspath(args.gis)
    # if args.station and os.path.isfile(os.path.abspath(args.station)):
    #     .station = os.path.abspath(args.station)
    if args.soil and os.path.isdir(os.path.abspath(args.soil)):
        args.soil = os.path.abspath(args.soil)
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

    main(gis_ws=args.gis, input_soil_ws=args.soil,
         cdl_year=args.year, zone_type=args.zone,
         overwrite_flag=args.overwrite, cleanup_flag=args.clean)
