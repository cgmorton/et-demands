import argparse
from collections import defaultdict
import datetime as dt
import logging
import os
import sys
import time
from collections import defaultdict
import arcpy

arcpy.CheckOutExtension('Spatial')



import pandas as pd
import numpy as np
import _util as util

# def main(ini_path, overwrite_flag=False, cleanup_flag=False):


# # Input paths
# # DEADBEEF - For now, get cropET folder from INI file
# # This function may eventually be moved into the main cropET code
# config = util.read_ini(ini_path, section='CROP_ET')
# crop_et_sec = 'CROP_ET'
# project_ws = config.get(crop_et_sec, 'project_folder')
# gis_ws = config.get(crop_et_sec, 'gis_folder')
# cells_path = config.get(crop_et_sec, 'cells_path')
# # try: cells_path = config.get(crop_et_sec, 'cells_path')
# # except: cells_path = os.path.join(gis_ws, 'ETCells.shp')
# stations_path = config.get(crop_et_sec, 'stations_path')
# crop_et_ws = config.get(crop_et_sec, 'crop_et_folder')
# bin_ws = os.path.join(crop_et_ws, 'bin')
#
# try:
#     template_ws = config.get(crop_et_sec, 'template_folder')
# except:
#     template_ws = os.path.join(os.path.dirname(crop_et_ws), 'static')
# try:
#     calibration_ws = config.get(crop_et_sec, 'spatial_cal_folder')
# except:
#     calibration_ws = os.path.join(project_ws, 'calibration')

arcpy.env.overwriteOutput = True

gis_ws = 'D:\et-demands\upper_co_full\gis'


cal_ws = 'D:\et-demands\upper_co_full\calibration'

prelim_cal_ws = os.path.join(cal_ws, 'preliminary_calibration')

cells_path = os.path.join(gis_ws, 'ETCells.shp')

cells_dd_path = os.path.join(gis_ws, 'ETCells_dd.shp')

cells_ras_path = os.path.join(gis_ws, 'ETCells_ras.img')

arcpy.Project_management(cells_path, cells_dd_path, arcpy.SpatialReference('WGS 1984'))


temp_path = os.path.join(cal_ws, 'temp')
if not os.path.exists(temp_path):
    os.makedirs(temp_path)

temp_pt_file = os.path.join(temp_path, 'temp_pt_file.shp')

crop_number_list = [03]
crop_name_list = ['alfalfa_hay']


arcpy.env.overwriteOutput = True
arcpy.env.extent = cells_dd_path
arcpy.env.outputCoordinateSystem = cells_dd_path
# arcpy.env.snapRaster = cells_ras_path
# cell_size = arcpy.Raster(cells_ras_path).meanCellHeight
#0.041666667 taken from GEE GRIDMET tiff
arcpy.FeatureToRaster_conversion(cells_dd_path, "GRIDMET_ID", cells_ras_path, 0.041666667)

# Get list of crops specified in ET cells
# Currently this may only be crops with CDL acreage
# crop_field_list = [
#     field.name for field in arcpy.ListFields(cells_path)
#     if re.match('CROP_\d{2}', field.name)]
# logging.debug('Cell crop fields: {}'.format(', '.join(crop_field_list)))
# crop_number_list = [
#     int(f_name.split('_')[1]) for f_name in crop_field_list]

for crop_num, crop_name in zip(crop_number_list, crop_name_list):
    # Preliminary Calibration Shapefile
    prelim_cal_file = os.path.join(prelim_cal_ws, 'crop_{:02d}_{}{}').format(crop_num, crop_name, '.shp')
    final_cal_file = os.path.join(cal_ws, 'crop_{:02d}_{}{}').format(crop_num, crop_name, '.shp')
    print(prelim_cal_file)
    print(final_cal_file)



    # Polygon to Point
    arcpy.FeatureToPoint_management(prelim_cal_file, temp_pt_file, "CENTROID")

    # Change Processing Extent to match final calibration file
    arcpy.env.extent = cells_dd_path
    arcpy.env.outputCoordinateSystem = cells_dd_path
    arcpy.env.snapRaster = cells_ras_path
    cell_size = arcpy.Raster(cells_ras_path).meanCellHeight
    # cell_size = 20000
    # IDW Point to Raster (Extent set to final calibration shapefile

    # Params to Interpolate
    # param_list = [
        # ['MAD_Init', 'mad_initial', 'LONG'],
        # ['MAD_Mid', 'mad_midseason', 'LONG'],
        # ['T30_CGDD', 't30_for_pl_or_gu_or_cgdd', 'FLOAT'],
        # ['PL_GU_Date', 'date_of_pl_or_gu', 'FLOAT'],
        # ['CGDD_Tbase', 'tbase', 'FLOAT'],
        # ['CGDD_EFC', 'cgdd_for_efc', 'LONG'],
        # ['CGDD_Term', 'cgdd_for_termination', 'LONG'],
        # ['Time_EFC', 'time_for_efc', 'LONG'],
        # ['Time_Harv', 'time_for_harvest', 'LONG'],
        # ['KillFrostC', 'killing_frost_temperature', 'Float'],
    # ]


    param_list = ['T30_CGDD', 'CGDD_EFC', 'CGDD_TERM', 'KillFrostC']
    # param_list = ['T30_CGDD']

    # Pt file to extract all rasters
    final_pt_path = os.path.join(temp_path, 'final_pt.shp')
    arcpy.RasterToPoint_conversion(cells_ras_path, final_pt_path, 'VALUE')
    # arcpy.AlterField_management(final_pt_path, 'GRID_CODE', 'GRIDMET_ID')

    # Empty List
    ras_list = []
    for param in param_list:
        outIDW_ras = arcpy.sa.Idw(temp_pt_file, param, cell_size)
        outIDW_ras_path = os.path.join(temp_path, '{}{}').format(param, '.img')
        outIDW_ras.save(outIDW_ras_path)

        ras_list.append(outIDW_ras_path)

        # out_pt_path = os.path.join(temp_path, '{}{}').format(param, '.shp')
        # arcpy.RasterToPoint_conversion(outIDW_ras, out_pt_path, 'VALUE')
        # arcpy.AlterField_management(out_pt_path, 'GRID_CODE', param)
    # print(ras_list)
    arcpy.sa.ExtractMultiValuesToPoints(final_pt_path, ras_list, 'NONE')


    # https://gist.github.com/tonjadwyer/0e4162b1423c404dc2a50188c3b3c2f5
    def make_attribute_dict(fc, key_field, attr_list=['*']):
        attdict = {}
        fc_field_objects = arcpy.ListFields(fc)
        fc_fields = [field.name for field in fc_field_objects if field.type != 'Geometry']
        if attr_list == ['*']:
            valid_fields = fc_fields
        else:
            valid_fields = [field for field in attr_list if field in fc_fields]
        # Ensure that key_field is always the first field in the field list
        cursor_fields = [key_field] + list(set(valid_fields) - set([key_field]))
        with arcpy.da.SearchCursor(fc, cursor_fields) as cursor:
            for row in cursor:
                attdict[row[0]] = dict(zip(cursor.fields, row))
        return attdict

    cal_dict = make_attribute_dict(final_pt_path, 'GRID_CODE', param_list)

    # print(cal_dict[608807])

    # out_feature_class = os.path.join(temp_path, 'join_test.shp')
    #
    # arcpy.SpatialJoin_analysis(final_cal_file, out_pt_path, out_feature_class)

















        # # Zonal Stats as Table
        # table_obj = arcpy.sa.ZonalStatisticsAsTable(
        #     cells_path, 'GRIDMET_ID', outIDW_ras,
        #     table_path, 'DATA', 'MEAN')
        # del table_obj
        #
        # sys.exit()
        # # Read in zonal stats values from table
        # # Value is the Value in zone_raster_path (not the zone
        # zs_dict = {
        #     zone_value_dict[row[0]]: row[1]
        #     for row in arcpy.da.SearchCursor(table_path, ('Value', 'MAJORITY'))}
        #
        # # Write zonal stats values to zone polygon shapefile
        # fields = (cell_id_field, field_name)
        # with arcpy.da.UpdateCursor(final_cal_file, param) as u_cursor:
        #     for row in u_cursor:
        #         row[1] = zs_dict.pop(row[0], 0)
        #         u_cursor.updateRow(row)









