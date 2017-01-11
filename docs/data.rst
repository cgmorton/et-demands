Input Data
==========

Weather Stations
~~~~~~~~~~~~~~~~
In order to generate the ET-Demands static input files, the user must provide a weather station point shapefile with at least one feature.  The shapefile must have columns/fields of the station ID, the corresponding zone ID, and the station latitude, longitude, and elevation (in feet).  Currently these fields must be named NLDAS_ID, [HUC8, HUC10, or COUNTYNAME], LAT, LON, and ELEV_FT respectively.  These fields are hard coded into the scripts, but they may eventually be set and modified using an INI file.

The weather station elevation is not currently used in the ET-Demands CropET module, but it is needed if running the RefET module.  The station elevation can also be set in meters in which case the field should be named ELEV_M.

Study Area
~~~~~~~~~~
In order to prep the ET-Demands data, the user must provide a study area polygon shapefile with at least one feature.  Each feature in the shapefile will become a separate ET cell/unit.  Typically the features will be HUC 8 or 10 watersheds or counties.

ET Cell Properties Data
-----------------------

The following ancillary data sets are used to populate the ETCellsCrops.txt and ETCellsProperties.txt static input files.

Cropland Data Layer (CDL)
~~~~~~~~~~~~~~~~~~~~~~~~~
The CDL raster is used to determine which crops will be simulated and the acreage of each crop.  The CDL crop acreage is only used in the zonal stats prep tool to remove CDL classes with very low acreages that were likely misclassified.  A single CDL raster is used since the CropET module can only be run for a static set of crops.

The CDL raster is also used to mask out non-agricultural areas when computing the average elevation and soil conditions.  The CDL raster is used as the "snap raster" or reference raster for all subsequent operations.  This means that the prep tools will project, clip and align the elevation and soils rasters to the CDL raster.

Elevation
~~~~~~~~~
**The ET cell elevation is not currently being used in the CropET module (other than for computing open water evaporation) and will likely be removed in the future unless it is needed for computing RefET**

Soils
~~~~~
The CropET module of ET-Demands  dependent on three soil properties, the