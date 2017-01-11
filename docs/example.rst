CropET Prep Example
===================

Clone the repository
--------------------
If you already have a local copy of the et-demands repository, make sure to pull the latest version from GitHub.  If you don't already have a local copy of the repository, either clone the repository locally or download a zip file of the scripts from Github.  For this example, the repository will be cloned directly to the D: drive (i.e. D:\\et-demands).

Command prompt
--------------
All of the ET-Demands scripts should be run from the command prompt or terminal window.  In Windows, to open the command prompt, press the "windows" key and "r" or click the "Start" button, "Accessories", and then "Command Prompt".

Within the command prompt or terminal, change to the target drive if necessary::

    > D:

Then change directory to the et-demands folder::

    > cd D:\et-demands

You may need to build the common folder if it doesn't exist::

    > mkdir common

Building the Example
--------------------
**For this example, all scripts and tools will be executed from the "example" folder.**

Build the example folder if it doesn't exist::

    > mkdir example

Change directory into the example folder::

    > cd example

Cropland Data Layer (CDL)
-------------------------
Download the CONUS CDL raster.  For this example we will be using the 2010 CDL raster. ::

    > python ..\et-demands\prep\download_cdl_raster.py --cdl ..\common\cdl --years 2010

If the download script doesn't work, please try downloading the `2010_30m_cdls.zip <ftp://ftp.nass.usda.gov/download/res/2010_30m_cdls.zip>`_ file directly from your browser or using a dedicated FTP program.

Study Area
----------
For the included example, the study area is a single HUC 8 watershed `12090105 <http://water.usgs.gov/lookup/getwatershed?12090105/www/cgi-bin/lookup/getwatershed>`_ in Texas.  The feature was extracted from the full `USGS Watershed Boundary Dataset <http://nhd.usgs.gov/wbd.html>`_ (WBD) geodatabase.  A subset of the WBD HUC polygons can downloaded using the `USDA Geospatial Data Gateway <https://gdg.sc.egov.usda.gov/>`_ or the full dataset can be downloaded using the `USGS FTP <ftp://rockyftp.cr.usgs.gov/vdelivery/Datasets/Staged/WBD/>`_.

The study area shapefile then needs to be projected to the CDL spatial reference, and converted to a raster that all of the other prep scripts will reference.  The following will buffer the study area extent by 300m.  The "cdl" parameter is needed to get the CDL spatial reference and grid size. ::

    > python ..\et-demands\prep\build_study_area_raster.py -shp gis\huc8\wbdhu8_albers.shp --cdl ..\common\cdl --year 2010 --buffer 300 --stats -o

Weather Stations
----------------
The example station is the centroid of a single 4km cell from the `University of Idaho Gridded Surface Meteorological Data <http://metdata.northwestknowledge.net/>`_ that is located in the study area.

Cropland Data Layer (CDL)
-------------------------
Clip the CDL raster to the study area::

    > python ..\et-demands\prep\clip_cdl_raster.py --cdl ..\common\cdl --years 2010 --stats -o

Mask the non-agricultural CDL pixels::

    > python ..\et-demands\prep\build_ag_cdl_rasters.py --years 2010 --mask -o --stats

Elevation
---------
Download the 30m National Elevation Dataset (NED) rasters that intersect the study area::

    > python ..\et-demands\prep\download_dem_rasters.py --tiles ..\common\dem\tiles --cellsize 30

Merge and clip the DEM tiles to the study area::

    > python ..\et-demands\prep\merge_dem_rasters.py --tiles ..\common\dem\tiles -o --stats

Mask the non-agricultural DEM pixels (based on CDL)::

    > python ..\et-demands\prep\build_ag_dem_rasters.py --years 2010 --mask -o --stats

Soils
-----
**For this example, the soils shapefiles have already been converted to raster and are located in the example\\gis\\statsgo folder.  It is not necessary to run the "rasterize_soil_polygons.py step below.**

Rasterize the soil shapefiles to match the CDL grid size and spatial reference::

    > python ..\et-demands\prep\rasterize_soil_polygons.py --soil ..\common\statsgo -o --stats

Extract the soil values for each CDL ag pixel::

    > python ..\et-demands\prep\build_ag_soil_rasters.py --years 2010 --mask -o --stats

Zonal Stats
-----------
Compute the mean elevation, soil properties, and crop acreages for each feature/polygon. ::

    > python ..\et-demands\prep\et_demands_zonal_stats_arcpy.py --year 2010 -o --zone huc8

Static Text Files
-----------------
Build the static text files from the templates in "et-demands\\static". ::

    > python ..\et-demands\prep\build_static_files_arcpy.py --ini example.ini --zone huc8 --acres 10 -o
