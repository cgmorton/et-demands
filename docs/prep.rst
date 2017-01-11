Prep Tools
==========

Data Prep
---------
The basic data preparation workflow is to download ancillary data for large areas or the CONUS into the 'common\\gis' folder, and then clip/subset the data for the study area into the "example\\gis" folder.

Command Line Arguments
----------------------
To see what arguments are available for a script, and their default values, pass the "-h" argument to the script.

The following arguments are available in many of the scripts::

  -d, --debug           Enable debug level logging
  -o, --overwrite       Overwrite existing file
  --stats               Build raster statistics

**Note, many of the scripts will not do anything if the output file already exists and the "--overwrite" argument is not set.**

Cropland Data Layer (CDL)
-------------------------
If you don't already have a CONUS CDL raster, it can be downloaded from the `USDA FTP <ftp://ftp.nass.usda.gov/download/res>`_, or using the provided CDL download script.  Set the "cdl" parameter to the "common\\cdl" subfolder and set the "year" parameter. ::

    > python ..\et-demands\prep\download_cdl_raster.py --cdl ..\common\cdl --years 2010

Digital Elevation Model (DEM)
-----------------------------
Elevation data can be automatically set using the 30m (1 arc-second) or 10m (1/3 arc-second) National Elevation Dataset (NED) rasters.  They can also be downloaded using the provided DEM download script.  The download script can download either the 30 or 10m tiles, but will default to the 30m NED if the cellsize parameter is not set.  The 30m NED data is generally good enough since the CDL data is at 30m and the crop elevation is averaged to the ET cell.

If the download script doesn't work, the NED data can also be easily downloaded in 1x1 degree tiles for the CONUS from the `USGS FTP <ftp://rockyftp.cr.usgs.gov>`_ in the folder vdelivery/Datasets/Staged/Elevation.

Soil Properties
---------------
The available water capacity (AWC), percent clay, and percent sand data cannot (currently) be directly downloaded.  The easiest way to obtain these soils data is to download the `STATSGO <http://www.nrcs.usda.gov/wps/portal/nrcs/detail/soils/survey/geo/?cid=nrcs142p2_053629>`_ database for the target state(s) using the `USDA Geospatial Data Gateway <https://gdg.sc.egov.usda.gov/>`_.  Shapefiles of the soil properties can be extracted using the `NRCS Soil Data Viewer <http://www.nrcs.usda.gov/wps/portal/nrcs/detailfull/soils/home/?cid=nrcs142p2_053620>`_.  The `SSURGO <http://www.nrcs.usda.gov/wps/portal/nrcs/detail/soils/survey/geo/?cid=nrcs142p2_053627>`_ databases can also be used, but these typically cover a smaller area and may have areas of missing data.  It may also be possible to used the gridded SSRUGO data, but this has not been tested.

To build the soils rasters using the rasterize_soil_polygons.py prep tool, it is assumed that you already have shapefiles of the soils data downloaded in the common\\statsgo folder.  The names of the soil shapefiles are currently hard coded in the scripts as 'gsmsoilmu_a_us_%s_albers.shp' and the folders are hardcoded as 'gsmsoil_%s', with the four type options being: 'awc', 'clay', 'sand', or 'all'.  (see :doc:`structure` in the CropET Example)

Zonal Stats
-----------
The current implementation of the zonal stats script uses the ArcGIS ArcPy module, but this will eventually be modified to GDAL.  The "zone" parameter is used to tell the script the structure of the study area shapefile.  There are numerous other parameters that are currently hard coded in the script but may eventually be read from an INI file.

Static Text Files
-----------------
The static text files for each project can be built from the templates in "et-demands\\static".  Along with the parameters listed below, there are other parameters that are currently hard coded in the script but may eventually be read from the INI file.

-i, --ini
  Project input file (used to get )
  Project, gis, cropET, and template folder paths.
  ET cell and station shapefiles paths.

--acres
  Exclude crops that don't have at least N acres in the ET cell/unit (defaults to 10)

--type
  Set the station zone field name in the weather station shapefile.
  Choices: 'huc8'->'HUC8', 'huc10'->'HUC10', or 'county'->'COUNTYNAME' (defaults to 'huc8')

--beef
  Set the initial number of beef hay cuttings (defaults to 4)

--dairy
  Set the initial number of dairy hay cuttings (defaults to 5)

