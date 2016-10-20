CropET Example
==============

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

Folder Structure
----------------
The ET-Demands scripts and tools are assuming that the user will use a folder structure similar to the one below.  The exact folder paths can generally be adjusted by either changing the INI file or explicitly setting the folder using the script command line arguments.  Most of the GIS sub-folders can be built and populated using the "prep" scripts. ::

    Project
    |
    +---common
    |   +---cdl
    |   |       2010_30m_cdls.img
    |   |       2010_30m_cdls.zip
    |   +---dem
    |   |   +---tiles
    |   +---huc8
    |   |       wbdhu8_albers.shp
    |   +---nldas_4km
    |   \---statsgo
    |       +---gsmsoil_awc
    |       |       gsmsoilmu_a_us_awc_albers.shp
    |       +---gsmsoil_clay
    |       |       gsmsoilmu_a_us_clay_albers.shp
    |       +---gsmsoil_sand
    |       |       gsmsoilmu_a_us_sand_albers.shp
    |       \---gsmsoil_silt
    |               gsmsoilmu_a_us_silt_albers.shp
    |
    +---et-demands
    |   +---cropET
    |   |   \---bin
    |   +---prep
    |   +---refET
    |   +---static
    |   |      CropCoefs.txt
    |   |      CropParams.txt
    |   |      ETCellsCrops.txt
    |   |      ETCellsProperties.txt
    |   |      MeanCuttings.txt
    |   |      TemplateMetAndDepletionNodes.xlsx
    |   \---tools
    |
    \---example
        |       example.ini
        +---annual_stats
        +---daily_baseline
        +---daily_plots
        +---daily_stats
        +---gis
        |   +---dem
        |   +---huc8
        |   |       wbdhu8_albers.shp
        |   \---stations
        |           nldas_4km_dd_pts.shp
        +---monthly_stats
        \---static

Data Prep
---------
The basic data preparation workflow is to download ancillary data for the the CONUS into the "common\\gis" folder, and then clip/subset the data for the study area into the "example\\gis" folder.

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
The CDL raster is used to determine which crops will be simulated and the acreage of each crop.  The CDL raster is also used as the "snap raster" or reference raster for all subsequent operations.  If you don't already have a CONUS CDL raster, it can be downloaded from the `USDA FTP <ftp://ftp.nass.usda.gov/download/res>`_, or using the provided CDL download script.  Set the "cdl" parameter to the "common\\cdl" subfolder and set the "year" parameter. ::

    > python ..\et-demands\prep\download_cdl_raster.py --cdl ..\common\cdl --years 2010

If the download script doesn't work, please try downloading the `2010_30m_cdls.zip <ftp://ftp.nass.usda.gov/download/res/2010_30m_cdls.zip>`_ file directly from your browser or using a dedicated FTP program.

Study Area
----------
In order to prep the ET-Demands data, the user must provide a study area polygon shapefile with at least one feature.  Typically the features will be HUC 8 or 10 watersheds or counties.

For the included example, the study area is a single HUC 8 watershed `12090105 <http://water.usgs.gov/lookup/getwatershed?12090105/www/cgi-bin/lookup/getwatershed>`_ in Texas.  The feature was extracted from the full `USGS Watershed Boundary Dataset <http://nhd.usgs.gov/wbd.html>`_ (WBD) geodatabase.  A subset of the WBD HUC polygons can downloaded using the `USDA Geospatial Data Gateway <https://gdg.sc.egov.usda.gov/>`_ or the full dataset can be downloaded using the `USGS FTP <ftp://rockyftp.cr.usgs.gov/vdelivery/Datasets/Staged/WBD/>`_.

The study area shapefile then needs to be projected to the CDL spatial reference, and converted to a raster that all of the other prep scripts will reference.  The following will buffer the study area extent by 300m.  The "cdl" parameter is needed to get the CDL spatial reference and grid size. ::

    > python ..\et-demands\prep\build_study_area_raster.py -shp gis\huc8\wbdhu8_albers.shp --cdl ..\common\cdl --year 2010 --buffer 300 --stats -o

Weather Stations
----------------
In order to generate the ET-Demands static input files, the user must provide a weather station point shapefile with at least one feature.  The shapefile must have columns/fields of the station ID, the corresponding zone ID, and the station latitude, longitude, and elevation (in feet).  Currently these fields must be named NLDAS_ID, [HUC8, HUC10, or COUNTYNAME], LAT, LON, and ELEV_FT respectively.  These fields are hard coded into the scripts, but they may eventually be set and modified using an INI file.

The example station is the centroid of a single 4km cell from the `University of Idaho Gridded Surface Meteorological Data <http://metdata.northwestknowledge.net/>`_ that is located in the study area. ::

Cropland Data Layer (CDL)
-------------------------
The CDL raster can then be clipped to the study area::

    > python ..\et-demands\prep\clip_cdl_raster.py --cdl ..\common\cdl --years 2010 --stats -o

Mask the non-agricultural CDL pixels::

    > python ..\et-demands\prep\build_ag_cdl_rasters.py --years 2010 --mask -o --stats

Elevation
---------
Elevation data is set using the 30m (1 arc-second) or 10m (1/3 arc-second) National Elevation Dataset (NED) rasters.  These can be easily downloaded in 1x1 degree tiles for the CONUS from the `USGS FTP <ftp://rockyftp.cr.usgs.gov>`_ in the folder vdelivery/Datasets/Staged/Elevation.  They can also be downloaded using the provided DEM download script. ::

    > python ..\et-demands\prep\download_dem_rasters.py --tiles ..\common\dem\tiles

Merge and clip the DEM tiles to the study area::

    > python ..\et-demands\prep\merge_dem_rasters.py --tiles ..\common\dem\tiles -o --stats

Mask the non-agricultural DEM pixels (based on CDL)::

    > python ..\et-demands\prep\build_ag_dem_rasters.py --years 2010 --mask -o --stats

Soils
-----
**For this example, the soils shapefiles have already been converted to raster and are in the example\\gis\\statsgo folder.  It is not necessary to run the "rasterize_soil_polygons.py script explained below.**

The available water capacity (AWC), percent clay, and percent sand data cannot (currently) be directly downloaded.  The easiest way to obtain these soils data is to download the `STATSGO <http://www.nrcs.usda.gov/wps/portal/nrcs/detail/soils/survey/geo/?cid=nrcs142p2_053629>`_ database for the target state(s) using the `USDA Geospatial Data Gateway <https://gdg.sc.egov.usda.gov/>`_.  Shapefiles of the soil properties can be extracted using the `NRCS Soil Data Viewer <http://www.nrcs.usda.gov/wps/portal/nrcs/detailfull/soils/home/?cid=nrcs142p2_053620>`_.  The `SSURGO <http://www.nrcs.usda.gov/wps/portal/nrcs/detail/soils/survey/geo/?cid=nrcs142p2_053627>`_ databases can also be used, but these typically cover a smaller area and may have areas of missing data.  It may also be possible to used the gridded SSRUGO data, but this has not been tested.

To build the soils rasters, it is assumed that you already have shapefiles of the soils data downloaded in the common\\statsgo folder.  The names of the soil shapefiles are currently hard coded in the scripts as 'gsmsoilmu_a_us_%s_albers.shp' and the folders are hardcoded as 'gsmsoil_%s', with the four type options being: 'awc', 'clay', 'sand', or 'all'.  (see folder structure section above)

Rasterize the soil shapefiles to match the CDL grid size and spatial reference::

    > python ..\et-demands\prep\rasterize_soil_polygons.py --soil ..\common\statsgo -o --stats

Extract the soil values for each CDL ag pixel::

    > python ..\et-demands\prep\build_ag_soil_rasters.py --years 2010 --mask -o --stats

Zonal Stats
-----------
Compute the mean elevation, soil properties, and crop acreages for each feature/polygon.  The current implementation of this script uses the ArcGIS ArcPy module, but this will eventually be modified to GDAL.  The "huc" parameter is used to tell the script the structure of the study area shapefile.  There are numerous other parameters that are currently hard coded in the script but may eventually be read from an INI file. ::

    > python ..\et-demands\prep\et_demands_zonal_stats_arcpy.py --year 2010 -o --zone huc8

Static Text Files
-----------------
Build the static text files from the templates in "et-demands\\static".  The "acres" parameter can be used to only include crops that have at least N acres.  The "type" parameter is used to set the station zone field name (i.e 'huc8'->'HUC8', 'huc10'->'HUC10', or 'county'->'COUNTYNAME']).  There are numerous other parameters that are currently hard coded in the script but may eventually be read from an INI file. ::

    > python ..\et-demands\prep\build_static_files_arcpy.py --ini example.ini --zone huc8 --acres 10 -o
