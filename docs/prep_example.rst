CropET Prep Example
===================

.. note::
   The following example was written assuming the user is running Microsoft Windows.  The last two steps of the example will not run on Linux or Mac because they rely on the ArcGIS ArcPy module.

Clone the repository
--------------------
If you already have a local copy of the et-demands repository, make sure to pull the latest version from GitHub.  If you don't already have a local copy of the repository, either clone the repository locally or download a zip file of the scripts from Github.

.. note::
   For this example, it is assumed that the repository was cloned directly to the D: drive (i.e. D:\\et-demands).

Command prompt / Terminal
-------------------------
All of the CropET prep scripts should be run from the command prompt or terminal window.  In Windows, to open the command prompt, press the "windows" key and "r" or click the "Start" button, "Accessories", and then "Command Prompt".

Within the command prompt or terminal, change to the target drive if necessary::

    > D:

Then change directory to the et-demands folder::

    > cd D:\et-demands

You may need to build the common folder if it doesn't exist::

    > mkdir common

Building the Example
--------------------
.. note::
   For this example, all scripts and tools will be executed from the "example" folder.

Build the example folder if it doesn't exist::

    > mkdir example

Change directory into the example folder::

    > cd example

Cropland Data Layer (CDL)
-------------------------
Download the CONUS CDL raster.  The CONUS CDL rasters should be downloaded to the "common" folder so that they can be used for other projects.  For this example we will be using the 2010 CDL raster. ::

    > python ..\et-demands\prep\download_cdl_raster.py --cdl ..\common\cdl --years 2010

If the download script doesn't work, please try downloading the `2010_30m_cdls.zip <ftp://ftp.nass.usda.gov/download/res/2010_30m_cdls.zip>`_ file directly from your browser or using a dedicated FTP program.

Study Area
----------
For this example, the study area is a single HUC 8 watershed (12090105) in Texas that was extracted from the full `USGS Watershed Boundary Dataset <http://nhd.usgs.gov/wbd.html>`_ (WBD) geodatabase.

.. image:: https://cfpub.epa.gov/surf/images/hucs/12090105l.gif
   :target: https://cfpub.epa.gov/surf/huc.cfm?huc_code=12090105
.. image:: https://cfpub.epa.gov/surf/images/hucs/12090105.gif
   :target: https://cfpub.epa.gov/surf/huc.cfm?huc_code=12090105

Project the study area shapefile to the CDL spatial reference and then convert to a raster::

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

Soils
-----
.. note::
   For this example, the soils shapefiles have already been converted to raster and are located in the example\\gis\\soils folder.  It is not necessary to run the "rasterize_soil_polygons.py step below.

Rasterize the soil shapefiles to match the CDL grid size and spatial reference::

    > python ..\et-demands\prep\rasterize_soil_polygons.py --soil ..\common\statsgo -o --stats

Extract the soil values for each CDL ag pixel::

    > python ..\et-demands\prep\build_ag_soil_rasters.py --years 2010 --mask -o --stats

Zonal Stats
-----------
Compute the soil properties and crop acreages for each feature/polygon. ::

    > python ..\et-demands\prep\et_demands_zonal_stats_arcpy.py --year 2010 -o --zone huc8

Static Text Files
-----------------
Build the static text files from the templates in "et-demands\\static". ::

    > python ..\et-demands\prep\build_static_files_arcpy.py --ini example.ini --zone huc8 --acres 10 -o
