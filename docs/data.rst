CropET Input Data
=================

Weather Station Points
----------------------
To generate the ET-Demands static input files, the user must provide a weather station point shapefile with at least one feature.  The shapefile must have columns/fields of the station ID, the corresponding zone ID, and the station latitude, longitude, and elevation (in feet).  Currently these fields must be named NLDAS_ID, [HUC8, HUC10, or COUNTYNAME], LAT, LON, and ELEV_FT respectively.  These fields are hard coded into the scripts, but they may eventually be set and modified using an INI file.

The weather station elevation is not currently used in the ET-Demands CropET module, but it is needed if running the RefET module.  The station elevation can also be set in meters in which case the field should be named ELEV_M.

Weather Data
------------
The user must provide weather and reference ET data for each weather station.

Study Area
----------
The user must provide a study area polygon shapefile with at least one feature.  Each feature in the study area shapefile will become a separate ET cell/unit.  Currently, only HUC8, HUC10, and county shapefiles are fully supported by the prep tools.

HUC8 and HUC10 features can be extracted from the full `USGS Watershed Boundary Dataset <http://nhd.usgs.gov/wbd.html>`_ (WBD) geodatabase.  A subset of the WBD HUC polygons can downloaded using the `USDA Geospatial Data Gateway <https://gdg.sc.egov.usda.gov/>`_ or the full dataset can be downloaded using the `USGS FTP <ftp://rockyftp.cr.usgs.gov/vdelivery/Datasets/Staged/WBD/>`_.

County features can be downloaded from the `USDA Geospatial Data Gateway <https://gdg.sc.egov.usda.gov/>`_.  For the zonal stats prep tool to work, the shapefile must have a field called "COUNTYNAME".  Other county features (such as the `US Census Cartographic Boundary Shapefiles <https://www.census.gov/geo/maps-data/data/tiger-cart-boundary.html>`_) could eventually be supported (or the name field could be manually changed to COUNTYNAME).

Cropland Data Layer (CDL)
-------------------------
The CDL raster is used to determine the acreage of crops in each ET cell/unit.  Crops with very low acreages (that were likely misclassified) can be excluded in the zonal stats prep tool.  A single CDL raster is used since the CropET module can only be run for a static set of crops.  Active crops will be set to 1 in the ETCellsCrops.txt static input file.

The CDL raster is also used to mask out non-agricultural areas when computing the average soil conditions.  The CDL raster is used as the "snap raster" or reference raster for all subsequent operations.  This means that the prep tools will project, clip and align the study area raster and soil rasters to the CDL raster.

.. _data-soils:

Soils
-----
The average agricultural area available water capacity (AWC) and hydrologic soils group are needed for each ET cell/unit.  The hydrologic soils group can be estimated based on the percent sand and clay for each ET cell/unit.

The AWC, percent clay, and percent sand data cannot (currently) be directly downloaded.  The easiest way to obtain these soils data is to download the `STATSGO <http://www.nrcs.usda.gov/wps/portal/nrcs/detail/soils/survey/geo/?cid=nrcs142p2_053629>`_ database for the target state(s) using the `USDA Geospatial Data Gateway <https://gdg.sc.egov.usda.gov/>`_.  Shapefiles of the soil properties can be extracted using the `NRCS Soil Data Viewer <http://www.nrcs.usda.gov/wps/portal/nrcs/detailfull/soils/home/?cid=nrcs142p2_053620>`_.  The `SSURGO <http://www.nrcs.usda.gov/wps/portal/nrcs/detail/soils/survey/geo/?cid=nrcs142p2_053627>`_ databases can also be used, but these typically cover a smaller area and may have areas of missing data.  It may also be possible to used the gridded SSRUGO data, but this has not been tested.

*Add additional details about which options were used in the Soil Data Viewer*

The soils data must be provided as separate shapefiles for each product.  The names of the soil shapefiles are hard coded in the scripts as "gsmsoilmu_a_us_{}_albers.shp", the folders are hardcoded as "gsmsoil_{}", where {} can be "awc", "clay", or "sand" (see :doc:`structure`).  For each shapefile, the value field name is hardcoded as the upper case of the property (i.e. "AWC", "CLAY", or "SAND").
