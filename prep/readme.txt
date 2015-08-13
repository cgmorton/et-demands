General order to run scripts
Run all scripts from the gis folder

CDL
    Clip the CDL raster on the network drive to the study area extent
    Make sure to set/adjust the extent path and buffer arguments
    The buffer units are the same as the extent shapefile (decimal degrees)
        python ..\..\et-demands\prep\clip_cdl_rasters.py --extent huc8\HUC8s.shp --buffer 10000 -o
    Mask all pixels that are not ag
        python ..\..\et-demands\prep\build_ag_cdl_rasters.py --mask -o --stats

DEM
    Tiles can be downloaded using the download script or a tiles folder can be set on the merged script
        python ..\..\et-demands\prep\download_dem_rasters.py --extent huc8\wbdhu8_albers.shp --buffer 10000 --overwrite
    Merge the tiles, project to the CDL spatial reference, and clip to the study area extent
        python ..\..\et-demands\prep\merge_dem_rasters.py --extent huc8\wbdhu8_albers.shp --buffer 10000 -o --stats
    To set the tiles folder/workspace, pass a "--tiles" argument to the merge script
        python ..\..\et-demands\prep\merge_dem_rasters.py --extent huc8\wbdhu8_albers.shp --buffer 10000 -o --stats --tiles U:\GIS-DATA\usa30mdem_1x1deg
    Extract the elevation value for each CDL ag pixel
        python ..\..\et-demands\prep\build_ag_dem_rasters.py --mask -o --stats

Soils
    Make sure to set/adjust the extent path and buffer arguments
        python ..\..\et-demands\prep\rasterize_soil_polygons.py -o --extent huc8\wbdhu8_albers.shp --buffer 10000
    Extract the soil values for each CDL ag pixel
        python ..\..\et-demands\prep\build_ag_soils_rasters.py -o

Zonal stats currently uses ArcPy/ArcGIS, this could be changed to GDAL 
    python ..\..\et-demands\prep\et_demands_zonal_stats.py --mask -o --stats