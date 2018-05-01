import argparse
import pandas as pd
import os
import re
import logging
import sys
import arcpy
#Eventually rename util.py to _util.py
import util as util
import datetime as dt

def main(ini_path, overwrite_flag=True, cleanup_flag=True):
    """Create Median NIWR Shapefiles from annual_stat files

    Args:
        ini_path (str): file path of the project INI file
        overwrite_flag (bool): If True (default), overwrite existing files
        cleanup_flag (bool): If True, remove temporary files

    Returns:
        None
    """
    logging.info('\nCreating Annual Stat Shapefiles')
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
    annual_ws = os.path.join(project_ws, 'annual_stats')

    # Check input folders
    if not os.path.exists(annual_ws):
        logging.critical('ERROR: The annual_stat folder does not exist.'
                         ' Check .ini settings')
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

    #output folder
    output_folder_path = os.path.join(annual_ws, 'Summary_Shapefiles')
    if not os.path.exists(output_folder_path):
        os.makedirs(output_folder_path)

    # Regular expressions
    data_re = re.compile('(?P<CELLID>\w+)_crop_(?P<CROP>\d+).csv$', re.I)
    #data_re = re.compile('(?P<CELLID>\w+)_daily_crop_(?P<CROP>\d+).csv$', re.I)
    
    #testing
#    annual_ws = r"D:\upper_co_full\annual_stats"
#    et_cells_path = os.path.join('D:\upper_co_full\gis','ETCells.shp')
    # Build list of all data files
    data_file_list = sorted(
        [os.path.join(annual_ws, f_name) for f_name in os.listdir(annual_ws)
         if data_re.match(f_name)])
    if not data_file_list:
        logging.error(
            '  ERROR: No annual ET files were found\n' +
            '  ERROR: Check the folder_name parameters\n')
        sys.exit()

    #make sure lists are empty
    stations = []
    crop_nums = []

    # Process each file
    for file_path in data_file_list:
        file_name = os.path.basename(file_path)
        logging.debug('')
        logging.info('  {0}'.format(file_name))

        #station, crop_num = os.path.splitext(file_name)[0].split('_daily_crop_')
        station, crop_num = os.path.splitext(file_name)[0].split('_crop_')
        stations.append(station)
        crop_num = int(crop_num)
        crop_nums.append(crop_num)

    #Find unique crops and station ids
    unique_crop_nums = list(set(crop_nums))
    unique_stations = list(set(stations))

    #Set arcpy file overwrite
    overwrite_flag = True
    arcpy.env.overwriteOutput = overwrite_flag
    #Set qualifiedFieldNames environment to false to preserve fieldnames
    arcpy.env.qualifiedFieldNames = False

    #Set arcpy workspace
    arcpy.env.workspace = output_folder_path

    ##Set file paths
    #out_path = os.path.join(annual_ws, 'Summary_Shapefiles')

    #Loop through each crop and station list to build summary dataframes for
    #variables to include in output (if not in .csv skip)
    #Should PMETo/ETr come from the .ini?
    var_list = ['PMETr_ASCE','PMETo','PMETr', 'ETact', 'ETpot', 'ETbas', 'Kc',
                'Kcb', 'PPT', 'Irrigation', 'Runoff', 'DPerc', 'NIWR', 'Season']

    #Testing (should this be an input option)
    #unique_crop_nums = [3]
    print('\n Creating Summary Shapefiles')
    for crop in unique_crop_nums:
        print('\n Processing Crop: {:02d}').format(crop)
        #create output dataframe
        output_df = pd.DataFrame(index=unique_stations)

        for var in var_list:
            #Initialize df variable to check if pandas df needs to be created
            df = None
            for station in unique_stations:
                #Build File Path
                file_path = os.path.join(annual_ws,
                                         '{}_crop_{:02d}.csv').format(station,
                                                                      crop)
                #Only process files that exists (crop/cell combinations)
                if not os.path.exists(file_path):
                    continue
                #Read file into df
                annual_df = pd.read_csv(file_path, skiprows=1)
                #Check to see if variable is in .csv (ETr vs ETo)
                #SHOULD THIS Come FROM THE .ini?)
                if var not in annual_df.columns:
                    continue
                #Create Dataframe if it doesn't exist
                if df is None:
                   year_list = list(map(str,annual_df['Year']))
                   year_fieldnames =  ['Year_' + y for y in year_list]
                   df = pd.DataFrame(index=unique_stations,
                                     columns=year_fieldnames)
                #Write data to each station row
                df.loc[station] = list(annual_df[var])

            #Add Column of Mean and Median of All Years
            #Check to see if variablie in .csv  ETr vs ETo
            # SHOULD THIS Come FROM THE .ini?
            if var not in annual_df.columns:
                    continue
            col_name =var
            output_df[col_name]=df.median(axis=1)

        #Create station ID column from index
        output_df['Station'] =df.index
        #Remove rows with Na (Is this the best option???)
        #Write all stations to index and then remove empty
        output_df = output_df.dropna()

        #Output file name
        out_name = "Crop_{:02d}_annual_medians.shp".format(crop)
        temp_name = "temp_annual.shp"

        #Copy ETCell.shp
        arcpy.CopyFeatures_management(et_cells_path, temp_name)

        #List all fieldnames
        field_names =[f.name for f in arcpy.ListFields(temp_name)]

        #Remove desired fields from list
        field_names.remove('FID')
        field_names.remove('GRIDMET_ID')
        field_names.remove('LAT')
        field_names.remove('LON')
        field_names.remove('ELEV_M')
        field_names.remove('ELEV_FT')
        field_names.remove('Shape')

        #Delete All but Desired Fields Above
        arcpy.DeleteField_management(temp_name, field_names)

        #Delete and Create data.dbf
        if arcpy.Exists(os.path.join(output_folder_path,'data.dbf')):
            arcpy.Delete_management(os.path.join(output_folder_path,
                                                 'data.dbf'))
        arcpy.CreateTable_management(output_folder_path, "data.dbf")

        #Add Fields to data.dbf
        for field in map(str,output_df.columns):
            arcpy.AddField_management(os.path.join(output_folder_path,
                                                   "data.dbf"), field, "DOUBLE")

        #write dataframe data to .dbf
        rows_to_write = [tuple(r[1:]) for r in output_df.itertuples()]
        with arcpy.da.InsertCursor(os.path.join(output_folder_path, 'data.dbf'),
                                   map(str, output_df.columns)) as ins_cur:
            for row in rows_to_write:
                ins_cur.insertRow(row)
        del ins_cur

        #Create a feature layer from featureclass (shapefile)
        arcpy.management.MakeFeatureLayer(temp_name, "temp_layer")

        #Join the feature layer to table
        arcpy.AddJoin_management("temp_layer",'GRIDMET_ID',
                                 os.path.join(output_folder_path, 'data.dbf'),
                                 'Station')

        #Copy the layer to a new permanent feature class
        arcpy.CopyFeatures_management("temp_layer", out_name)

        #Remove redundant fields (Where is 'Field1' coming from?)
        arcpy.DeleteField_management(out_name, ['OID_', 'Station', 'Field1'])
        
        #Remove rows with no ET data (leftover from ETCells join)
        with arcpy.da.UpdateCursor(out_name, "Season") as cursor:
            for row in cursor:
                if row[0] == 0:
                    cursor.deleteRow()
        del cursor

    #Cleanup temporary files
    if arcpy.Exists(os.path.join(output_folder_path, temp_name)):
        arcpy.Delete_management(os.path.join(output_folder_path, temp_name))
    if arcpy.Exists(os.path.join(output_folder_path, 'data.dbf')):
        arcpy.Delete_management(os.path.join(output_folder_path, 'data.dbf'))
    
    
def arg_parse():
    """"""
    parser = argparse.ArgumentParser(
        description='ET-Demands Annual Stat Shapefiles',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        '-i', '--ini', metavar='PATH',
        type=lambda x: util.is_valid_file(parser, x), help='Input file')
    parser.add_argument(
        '-o', '--overwrite', default=True, action='store_true',
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

    main(ini_path=args.ini, overwrite_flag=args.overwrite,
         cleanup_flag=args.clean)














