CropET Prep Tools
=================

Data Prep
---------
The basic data preparation workflow is to download ancillary data for large areas or the CONUS into the 'common\\gis' folder, and then clip/subset the data for the study area into the "example\\gis" folder.  All of the prep scripts will assume there is a "gis" sub-folder within the main project folder.

For this example, all scripts will be be run from the project folder.  For example, the following command will call the download CDL script from the example project folder.  The "..\" notation indicates that you will go up one folder to the main et-demands folder, and then go into the "et-demands\\prep" folder.::

    > python ..\et-demands\prep\download_cdl_raster.py

Command Line Arguments
----------------------
To see what arguments are available for a script (and their default values) pass the "-h" argument to the script.::

    > python ..\et-demands\prep\download_cdl_raster.py -h

The following arguments are available in many of the scripts

-d, --debug
  Enable debug level logging
-o, --overwrite
  Overwrite existing files
--stats
  Build raster statistics

.. note::
   Note, many of the scripts will not do anything if the output file already exists and the "--overwrite" argument is not set.

download_cdl_raster.py
----------------------
If you don't already have a CONUS Cropland Data Layer (CDL) raster, it can be downloaded using the provided CDL download script or downloaded manually from the `USDA FTP <ftp://ftp.nass.usda.gov/download/res>`_.  The CONUS CDL rasters shoule be downloaded into the "common" folder so they can be used for other project.  The following parameters must both be set.

--cdl
  | Common CDL workspace/folder
  | This can be a relative or absolute path.
  | Using the default folder structure, this can be set as "--cdl ..\common\cdl".
-y, --years
  | Comma separated list or range of years to process.
  | The download script can download multiple CDL years even though only a single year can be used.
  | Usage examples: "-y 2010", "--years 2010-2012", or "-y 2010, 2011, 2012-2015"

build_ag_cdl_rasters.py
-----------------------
The CDL raster is used to generate a mask of irrigated agricultural areas.

--gis
  Project GIS workspace/folder (default is ".\\gis")
-y, --years
  Comma separated list or range of years to process.
--blocksize
  Decrease raster block size if Python raises memory errors (default is 16384)
--mask
  Mask CDL pixels outside extent shapefile

The following agricultural CDL classes are currently hardcoded in the script: 1-60, 66-80, and 204-254.  These values may need to be adjusted depending on the CDL year and the project.  The following non-irrigated CDL classes may need to be included.

-  Crop 61 is fallow/idle and is not included as an agricultural class
-  Crop 176 is Grassland/Pasture in the new national CDL rasters
-  Crop 181 was Pasture/Hay in the old state CDL rasters
-  Crop 182 was Cultivated Crop in the old state CDL rasters

build_study_area_raster.py
--------------------------
The study area shapefile is projected to the CDL spatial reference and then converted to a raster.  Currently, this raster is saved in the "scratch" folder and is referenced by the other scripts in order to maintain a consistent cellsize, extent, projection, and shape.

--cdl
  Common CDL workspace/folder
--buffer
  Buffer the study area by N meters before converting to raster
-y, --years
  Comma separated list or range of years to process

rasterize_soil_polygons.py
--------------------------
To build the soils rasters, it is assumed that you already have correctly named and formatted shapefiles of the soils data downloaded in the common\\soils folder (see :ref:`data-soils` and :ref:`structure`).

--gis
  Project GIS workspace/folder (default is ".\\gis")
--soil
  Common soils workspace/folder

build_ag_soil_rasters.py
------------------------
The average soil conditions for the agricultural areas can then be extracted from the soil rasters.

--gis
  Project GIS workspace/folder (default is ".\\gis")
--soil
  Project soil workspace/folder (default is ".\\gis\\soils")
-y, --years
  Comma separated list or range of years to process
--blocksize
  Decrease raster block size if Python raises memory errors (default is 16384)
--mask
  Mask CDL pixels outside extent shapefile
--type
  Soil property types: 'all', 'awc', 'clay', 'sand' (default is 'all')

et_demands_zonal_stats_arcpy.py
-------------------------------
The zonal stats tool is used to average the crop and soil data to the ET cells/units.  The current implementation of the zonal stats script uses the ArcGIS ArcPy module, but this will eventually be modified to GDAL.  The output field names and sub-folder paths are all hardcoded in the script.  The cellsize of the CDL raster is assumed to be 30m.

--gis
  Project GIS workspace/folder (default is ".\\gis")
--soil
  Project Soil workspace/folder (default is ".\\gis\\soils")
-y, --year
  Single CDL year to process
--zone
  ET cell/unit zone type can be 'huc8', 'huc10' or 'county' (default is 'huc8')

The zone type parameter

build_static_files_arcpy.py
---------------------------
The static text files for each project can be built from the templates in "et-demands\\static".  A year parameter is not set since the ET cell/unit zonal stats values were only computed for a single year.

-i, --ini
  Project input file (used to get folder and file paths)
--acres
  Exclude crops that don't have at least N acres in the ET cell/unit (default is 10)
--zone
  ET cell/unit zone type can be 'huc8', 'huc10' or 'county' (default is 'huc8')
--beef
  Set the initial number of beef hay cuttings (default is 4)
--dairy
  Set the initial number of dairy hay cuttings (default is 5)

Along with the parameters listed above, there are other hardcoded parameters in the script that may eventually be read from the INI file.  These include the station elevation units (feet), soil_depth (60), aridity (50), permeability (-999), and the number of supported crops (85).

Unused scripts
--------------
The gdal_common.py and util.py python scripts are not run by the user.  These scripts are called by the other scripts.

The download_dem_rasters.py, build_ag_dem_rasters.py, and merge_dem_rasters.py are not used anymore since the cell elevation is not needed.  These will eventually be moved or removed.
