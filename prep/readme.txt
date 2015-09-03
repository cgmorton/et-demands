General order to run scripts
Run all scripts from the project folder
    Scripts will look for a "gis" sub-folder

Study Area
    Project the study area shapefile to the CDL spatial reference
    Convert the study area shapefile to a raster that all other scripts will reference
    Make sure to set/adjust the shapefile path and buffer arguments
    The buffer units are the same as the CDL raster (meters)
        python ..\et-demands\prep\build_study_area_raster.py -shp gis\huc8\wbdhu8_albers.shp --cdl ..\common\cdl --years 2010 --buffer 300 -o --stats

CDL
    Clip the CDL raster on the network drive to the study area extent
        python ..\et-demands\prep\clip_cdl_raster.py --cdl ..\common\cdl --years 2010 -o --stats
    Mask all pixels that are not ag
        python ..\et-demands\prep\build_ag_cdl_rasters.py --years 2010 --mask -o --stats

DEM
    Tiles can be downloaded using the download script or a tiles folder can be set on the merged script
        python ..\et-demands\prep\download_dem_rasters.py --tiles ..\common\dem\tiles -cs 30 -o
    Merge the tiles, project to the CDL spatial reference, and clip to the study area extent
        python ..\et-demands\prep\merge_dem_rasters.py --tiles ..\common\dem\tiles -o --stats
    Extract the elevation value for each CDL ag pixel
        python ..\et-demands\prep\build_ag_dem_rasters.py --years 2010 --mask -o --stats

Soils
    Make sure to set/adjust the extent path and buffer arguments
        python ..\et-demands\prep\rasterize_soil_polygons.py --soil ..\common\statsgo -o --stats
    Extract the soil values for each CDL ag pixel
        python ..\et-demands\prep\build_ag_soil_rasters.py --years 2010 --mask -o --stats

Zonal Stats     
    Zonal stats currently uses ArcPy/ArcGIS, this could be changed to GDAL 
    "huc" argument can be set to 10 if reference HUC10 zones
        python ..\et-demands\prep\et_demands_zonal_stats_arcpy.py --years 2010 -o --huc 8
        
Static
    Build static text files from templates
    "acres" argument sets the area threshold acres for turning on the crop flag
    "huc" argument can be set to 10 if reference HUC10 zones
    A lot of parameters are currently hardcoded in this script but could eventually be read from an INI file
        python ..\et-demands\prep\build_static_files.py --station gis\stations\nldas_4km_dd_pts_cat_basins.shp --huc 8 --acres 10 -o