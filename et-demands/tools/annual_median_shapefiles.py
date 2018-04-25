import numpy as np
import pandas as pd    
import os
import re
import logging
import sys


#This should eventually come from the .ini
annual_ws = r"D:\upper_co\annual_stats"

# Regular expressions
data_re = re.compile('(?P<CELLID>\w+)_crop_(?P<CROP>\d+).csv$', re.I)
# data_re = re.compile('(?P<CELLID>\w+)_daily_crop_(?P<CROP>\d+).csv$', re.I)

# Build list of all data files
data_file_list = sorted(
    [os.path.join(annual_ws, f_name) for f_name in os.listdir(annual_ws)
     if data_re.match(f_name)])
if not data_file_list:
    logging.error(
        '  ERROR: No daily ET files were found\n' +
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
    
    # station, crop_num = os.path.splitext(file_name)[0].split('_daily_crop_')
    station, crop_num = os.path.splitext(file_name)[0].split('_crop_')
    stations.append(station)
    crop_num = int(crop_num)
    crop_nums.append(crop_num)
    
#Find unique crops and station ids    
unique_crop_nums = list(set(crop_nums))
unique_stations = list(set(stations))


import arcpy
#Set file overwrite 
overwrite_flag = True
arcpy.env.overwriteOutput = overwrite_flag
#Set qualifiedFieldNames environment to falst to preserve fieldnames in output
arcpy.env.qualifiedFieldNames = False

#Set arcpy workspace (should come from the .ini)
arcpy.env.workspace = r"D:\upper_co\annual_stats"

##Set file paths
#out_path = os.path.join(annual_ws, 'Summary_Shapefiles')

#Loop through each crop and station list to build summary dataframes for
#variables to include in output (if not in .csv skip)
#Should PMETo/ETr come from the .ini?
var_list = ['PMETo','PMETr', 'ETact',	'ETpot',	'ETbas',	'Kc',	'Kcb',	'PPT',	'Irrigation',	'Runoff',	'DPerc',	'NIWR',	'Season']

#Testing (should this be an input option)
#unique_crop_nums = [3,4]

#%%
 
for crop in unique_crop_nums:
    #create output dataframe
    output_df = pd.DataFrame(index = unique_stations)
    
    for var in var_list:
        for i, station in enumerate(unique_stations):
#            print(i)
            #Build File Path
            file_path = os.path.join(annual_ws,
                                     '{}_crop_{:02d}.csv').format(station, crop)
            #Read file into df
            annual_df = pd.read_csv(file_path, skiprows=1)
            #Check to see if variable is in .csv (ETr vs ETo SHOULD THIS Come FROM THE .ini?)
            if var not in annual_df.columns:
                continue
            #If first pass build dataframes
            if i==0:
               year_list = list(map(str,annual_df['Year']))
               year_fieldnames =  ['Year_' + y for y in year_list]
               df = pd.DataFrame(index = unique_stations,
                                 columns = year_fieldnames)
            #Write data to each station row   
            df.loc[station] = list(annual_df[var])
    
        #Add Column of Mean and Median of All Years
        #Check to see if variablie in .csv (ETr vs ETo SHOULD THIS Come FROM THE .ini?)
        if var not in annual_df.columns:
                continue
        col_name =var
        output_df[col_name]=df.median(axis=1)
        
    #Move station ID to column instead of index
    output_df['Station'] =df.index
            
    out_name = "Crop_{:02d}_annual_medians.shp".format(crop)
    temp_name = "temp_annual.shp"
    
    #this should come from .ini
    gis_ws = "D:\upper_co\gis"
    et_cells_path = os.path.join(gis_ws, 'ETCells.shp')
    
    #Copy ETCell.shp
    arcpy.CopyFeatures_management(et_cells_path, temp_name)
    
    #List all fieldnames
    field_names =[f.name for f in arcpy.ListFields(temp_name)]
    
    #Remove desired fields from list
    field_names.remove('FID')
    field_names.remove('GRIDMET_ID')
    field_names.remove('LAT')
    field_names.remove('LON')
    field_names.remove('Shape')
    
    #Delete All but Desired Fields Above
    arcpy.DeleteField_management(temp_name, field_names)
    
    #Delete and Create data.dbf
    if arcpy.Exists(os.path.join(annual_ws,'data.dbf')):
        arcpy.Delete_management(os.path.join(annual_ws,'data.dbf'))
    arcpy.CreateTable_management(annual_ws, "data.dbf")
    
    #Add Fields to data.dbf
    for field in map(str,output_df.columns):
        arcpy.AddField_management(os.path.join(annual_ws, "data.dbf"),
                                  field, "DOUBLE")
    
    #write dataframe data to .dbf
    rows_to_write = [tuple(r[1:]) for r in output_df.itertuples()] 
    with arcpy.da.InsertCursor(os.path.join(annual_ws,'data.dbf'),
                               map(str,output_df.columns)) as ins_cur:
        for row in rows_to_write:
            ins_cur.insertRow(row)                
    del ins_cur        
            
    #Create a feature layer from featureclass (shapefile)
    arcpy.management.MakeFeatureLayer(temp_name,"temp_layer")
    
    #Join the feature layer to table
    arcpy.AddJoin_management("temp_layer",'GRIDMET_ID',
                             os.path.join(annual_ws,'data.dbf'), 'Station')
    
    #Copy the layer to a new permanent feature class
    arcpy.CopyFeatures_management("temp_layer", out_name)
    
    #Remove redundant fields (Where is 'Field1' coming from?)
    arcpy.DeleteField_management(out_name, ['OID_','Station', 'Field1'])

#Cleanup temporary files (HOW DO I GET RID OF LOCKS?)        
if arcpy.Exists(os.path.join(annual_ws, temp_name)):
    arcpy.Delete_management(os.path.join(annual_ws, temp_name))
if arcpy.Exists(os.path.join(annual_ws,'data.dbf')):
    arcpy.Delete_management(os.path.join(annual_ws,'data.dbf'))
    
    















