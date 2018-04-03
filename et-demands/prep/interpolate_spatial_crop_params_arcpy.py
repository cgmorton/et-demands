import argparse
import datetime as dt
import logging
import os
import sys
import arcpy
import _util as util
import re


def main(ini_path, zone_type='gridmet', overwrite_flag=False, cleanup_flag=True):
    """Interpolate Preliminary Calibration Zones to All Zones

    Args:
        ini_path (str): file path of the project INI file
        zone_type (str): Zone type (huc8, huc10, county, gridmet)
        overwrite_flag (bool): If True (default), overwrite existing files
        cleanup_flag (bool): If True, remove temporary files

    Returns:
        None
    """
    logging.info('\nInterpolating Calibration Data from Subset Point Data')
    #  INI path
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
            'et_cells_path parameter must be set in the INI file, exiting')
        return False
    try:
        calibration_ws = config.get(crop_et_sec, 'spatial_cal_folder')
    except:
        calibration_ws = os.path.join(project_ws, 'calibration')

    # Sub folder names
    static_ws = os.path.join(project_ws, 'static')
    crop_params_path = os.path.join(static_ws, 'CropParams.txt')
    crop_et_sec = 'CROP_ET'
    crop_et_ws = config.get(crop_et_sec, 'crop_et_folder')
    bin_ws = os.path.join(crop_et_ws, 'bin')

    # Check input folders
    if not os.path.exists(calibration_ws):
        logging.critical('ERROR: The calibration folder does not exist. Run build_spatial_crop_params_arcpy.py, exiting')
        sys.exit()

    # Check input folders
    if not os.path.isdir(project_ws):
        logging.critical(('ERROR: The project folder ' +
                          'does not exist\n  {}').format(project_ws))
        sys.exit()
    elif not os.path.isdir(gis_ws):
        logging.critical(('ERROR: The GIS folder ' +
                          'does not exist\n  {}').format(gis_ws))
        sys.exit()
    logging.info('\nGIS Workspace:      {0}'.format(gis_ws))


    # Check input zone type (GRIDMET ONLY FOR NOW!!!!)
    if zone_type == 'gridmet':
        station_zone_field = 'GRIDMET_ID'
        station_id_field = 'GRIDMET_ID'
    else: 
        print('FUNCTION ONLY SUPPORTS GRIDMET ZONE TYPE AT THIS TIME')
        sys.exit()

    arcpy.env.overwriteOutput = overwrite_flag
    arcpy.CheckOutExtension('Spatial')
    
    cells_dd_path = os.path.join(gis_ws, 'ETCells_dd.shp')
    cells_ras_path = os.path.join(gis_ws, 'ETCells_ras.img')
    arcpy.Project_management(et_cells_path, cells_dd_path, arcpy.SpatialReference('WGS 1984'))

    temp_path = os.path.join(calibration_ws, 'temp')
    if not os.path.exists(temp_path):
        os.makedirs(temp_path)
    temp_pt_file = os.path.join(temp_path, 'temp_pt_file.shp')

    # Read crop parameters using ET Demands functions/methods
    logging.info('\nReading Default Crop Parameters')
    sys.path.append(bin_ws)
    import crop_parameters
    crop_param_dict = crop_parameters.read_crop_parameters(crop_params_path)

    # Get list of crops specified in ET cells
    crop_field_list = [
        field.name for field in arcpy.ListFields(et_cells_path)
        if re.match('CROP_\d{2}', field.name)]
    logging.debug('Cell crop fields: {}'.format(', '.join(crop_field_list)))
    crop_number_list = [
        int(f_name.split('_')[1]) for f_name in crop_field_list]

    crop_number_list = [crop_num for crop_num in crop_number_list]
    logging.info('Cell crop numbers: {}'.format(
        ', '.join(list(util.ranges(crop_number_list)))))

    # Get Crop Names for each Crop in crop_number_list
    crop_name_list = []
    logging.info('\nBuilding Crop Name List')
    for crop_num in crop_number_list:
        try:
            crop_param = crop_param_dict[crop_num]
        except:
            continue
        logging.info('{0:>2d} {1}'.format(crop_num, crop_param))
        # Replace other characters with spaces, then remove multiple spaces
        crop_name = re.sub('[-"().,/~]', ' ', str(crop_param.name).lower())
        crop_name = ' '.join(crop_name.strip().split()).replace(' ', '_')
        crop_name_list.append(crop_name)

    # Set arcpy environmental parameters
    arcpy.env.extent = cells_dd_path
    arcpy.env.outputCoordinateSystem = cells_dd_path
    
    # Convert cells_dd to cells_ras (0.041666667 taken from GEE GRIDMET tiff) HARDCODED FOR NOW
    arcpy.FeatureToRaster_conversion(cells_dd_path, station_id_field, cells_ras_path, 0.041666667)

    # Location of preliminary calibration .shp files (ADD AS INPUT ARG?)
    prelim_calibration_ws = os.path.join(calibration_ws, 'preliminary_calibration')

    for crop_num, crop_name in zip(crop_number_list, crop_name_list):
        # Preliminary calibration .shp
        subset_cal_file = os.path.join(prelim_calibration_ws, 'crop_{0:02d}_{1}{2}').format(crop_num, crop_name, '.shp')
        final_cal_file = os.path.join(calibration_ws, 'crop_{0:02d}_{1}{2}').format(crop_num, crop_name, '.shp')

        if not arcpy.Exists(subset_cal_file):
            print('\nCrop No: {} Preliminary Calibration File Not Found. Skipping.').format(crop_num)
            continue
        print('\nInterpolating Crop: {0:02d}').format(crop_num)
        # Polygon to Point
        arcpy.FeatureToPoint_management(subset_cal_file, temp_pt_file, "CENTROID")

        # Change Processing Extent to match final calibration file
        # arcpy.env.extent = cells_dd_path
        # arcpy.env.outputCoordinateSystem = cells_dd_path
        arcpy.env.snapRaster = cells_ras_path
        cell_size = arcpy.Raster(cells_ras_path).meanCellHeight

        # Params to Interpolate
        # Full list
        # param_list = ['MAD_Init', 'MAD_Mid', 'T30_CGDD',
        #     'PL_GU_Date', 'CGDD_Tbase', 'CGDD_EFC',
        #     'CGDD_Term', 'Time_EFC', 'Time_Harv', 'KillFrostC']

        # Short list
        param_list = ['T30_CGDD', 'CGDD_EFC', 'CGDD_TERM', 'KillFrostC']

        # Create final pt file based on cells raster for ExtractMultiValuesToPoints
        final_pt_path = os.path.join(temp_path, 'final_pt.shp')
        arcpy.RasterToPoint_conversion(cells_ras_path, final_pt_path, 'VALUE')

        # Empty list to fill with idw raster paths
        ras_list = []
        for param in param_list:
            outIDW_ras = arcpy.sa.Idw(temp_pt_file, param, cell_size)
            outIDW_ras_path = os.path.join(temp_path, '{}{}').format(param, '.img')
            outIDW_ras.save(outIDW_ras_path)
            ras_list.append(outIDW_ras_path)

        # Extract all idw raster values to point .shp
        arcpy.sa.ExtractMultiValuesToPoints(final_pt_path, ras_list, 'NONE')

        # Read Interpolated Point Attribute table into dictionary ('GRID_CODE' is key)
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

        # Overwrite values in calibration .shp with values from interpolated dictionary
        fields = ['CELL_ID'] + param_list
        with arcpy.da.UpdateCursor(final_cal_file, fields) as cursor:
            for row in cursor:
                for param_i, param in enumerate(param_list):
                    row[param_i+1] = round(cal_dict[int(row[0])][fields[param_i+1]], 1)
                cursor.updateRow(row)

def arg_parse():
    """"""
    parser = argparse.ArgumentParser(
        description='ET-Demands Interpolate Spatial Crop Parameters',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        '-i', '--ini', metavar='PATH',
        type=lambda x: util.is_valid_file(parser, x), help='Input file')
    parser.add_argument(
        '--zone', default='county', metavar='', type=str,
        choices=('huc8', 'huc10', 'county', 'gridmet'),
        help='Zone type [{}]'.format(', '.join(['huc8', 'huc10', 'county', 'gridmet'])))
    parser.add_argument(
        '-o', '--overwrite', default=False, action='store_true',
        help='Overwrite existing file')
    parser.add_argument(
        '--clean', default=False, action='store_true',
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

    main(ini_path=args.ini, zone_type=args.zone,
         overwrite_flag=args.overwrite, cleanup_flag=args.clean)