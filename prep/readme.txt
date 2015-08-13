General order to run scripts
Run all scripts from the gis folder

CDL
    Clip the CDL raster on the network drive to the study area extent
    Make sure to set/adjust the extent path and buffer arguments
    The buffer units are the same as the extent shapefile (decimal degrees)
        python bin\clip_cdl_rasters.py --extent huc8\HUC8s.shp --buffer 10000 --overwrite
    Mask all pixels that are not ag
        python bin\build_ag_cdl_rasters.py --overwrite

DEM
    Tiles can be downloaded using the download script or a tiles folder can be set on the merged script
        python bin\download_dem_rasters.py --extent huc8\wbdhu8_albers.shp --buffer 10000 --overwrite
    Merge the tiles, project to the CDL spatial reference, and clip to the study area extent
        python bin\merge_dem_rasters.py --extent huc8\wbdhu8_albers.shp --buffer 10000 --overwrite --stats
    To set the tiles folder/workspace, pass a "--tiles" argument to the merge script
        python bin\merge_dem_rasters.py --extent huc8\wbdhu8_albers.shp --buffer 10000 --overwrite --stats --tiles U:\GIS-DATA\usa30mdem_1x1deg
    Extract the elevation value for each CDL ag pixel
        python bin\build_ag_dem_rasters.py --overwrite

Soils
    Make sure to set/adjust the extent path and buffer arguments
        python bin\rasterize_soil_polygons.py --overwrite --extent huc8\wbdhu8_albers.shp --buffer 10000
    Extract the soil values for each CDL ag pixel
        python bin\build_ag_soils_rasters.py --overwrite

Zonal stats currently uses ArcPy/ArcGIS, this could be changed to GDAL 
    python bin\et_demands_zonal_stats.py --overwrite