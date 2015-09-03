# CropET
Crop ET Demands Model

####Clone the repository
If you already have a local copy of the et-demands repository, make sure to pull the latest version from GitHub.  If you don't already have a local repository, either clone the repository locally or download a zip file of the scripts from Github.  For this example, the local copy will be cloned directly into the project folder (i.e. D:\Project\et-demands).  The repository will include an "example" sub-folder, but please create a separate "example" folder in the project folder (as indicated below in the Folder Structure section).  The example folder in "et-demands" is only used to provide copies of the example input data.

#### Folder Structure
The ET-Demands scripts and tools are assuming that the user will use a folder structure similar to the one below.  The exact folder paths can generally be adjusted by either changing the INI file or explicitly setting the folder using the script command line arguments.  Most of the GIS sub-folders can be built and populated using the "prep" scripts.
```
Project
|  
+---common
|   +---cdl
|   +---dem
|   +---huc8
|   |       wbdhu8_albers.shp
|   +---nldas_4km
|   \---statsgo
|
+---et-demands 
|   +---cropET
|   |   \---bin         
|   +---prep
|   +---refET       
|   +---static
|   \---tools
|
\---example
    +---daily_baseline
    +---gis
    |   +---dem
    |   \---huc8
    |           wbdhu8_albers.shp
    \---static
```

#### Running the tools/scripts
Currently, the scripts must be run from the windows command prompt (or Linux terminal) so that the input file can be passed as an argument directly to the script.  To see what arguments are available for a script, and their default values, pass the "-h" argument.
```
> python run_basin.py -h
usage: run_basin.py [-h] [-i PATH] [-vb] [-d] [-v] [-mp [N]]

Crop ET-Demands

optional arguments:
  -h, --help            show this help message and exit
  -i PATH, --ini PATH   Input file (default: None)
  -vb, --vb             Mimic calculations in VB version of code (default:
                        False)
  -d, --debug           Save debug level comments to debug.txt (default:
                        False)
  -v, --verbose         Print info level comments (default: False)
  -mp [N], --multiprocessing [N]
                        Number of processers to use (default: 1)
```
In Windows, to open the command prompt, press the "windows" key and "r" or click the "Start" button, "Accessories", and then "Command Prompt".

Within the command prompt or terminal, change to the target drive if necessary:
```
> D:
```

Change directory to the project folder:
```
> cd D:\Project
```

Build the example folder if it doesn't exist:
```
> mkdir example
```

# Example
For this example, all scripts and tools will be executed from the "example" folder.  Change directory to the example folder if necessary:
```
> cd example
```

#### Data Prep
The basic data preparation workflow is to download ancillary data for the the CONUS into the "common\gis" folder, and then clip/subset the data for the study area into the "example\gis" folder.

###### Cropland Data Layer (CDL)
The CDL raster is used to determine which crops will be simulated and the acreage of each crop.  The CDL raster is also used as the "snap raster" or reference raster for all subsequent operations.  If you don't already have a CONUS CDL raster, it can be downloaded from the [USDA FTP](ftp://ftp.nass.usda.gov/download/res), or using the provided CDL download script.  Set the "gis" parameter to the common\GIS subfolder and set the "year" parameter.
```
> python ..\et-demands\prep\download_cdl_raster.py --cdl ..\common\cdl --year 2010
```

###### Study Area
The minimum input data needed to run ET-Demands is a study area polygon shapefile with at least one feature.  Typically the features will be HUC 8 or 10 watersheds or counties.  

For the included example, the study area is a single HUC 8 watershed [12090105](http://water.usgs.gov/lookup/getwatershed?12090105/www/cgi-bin/lookup/getwatershed) in Texas.  The feature was extracted from the full [USGS Watershed Boundary Dataset (WBD)](http://nhd.usgs.gov/wbd.html) geodatabase.  A subset of the WBD HUC polygons can downloaded using the [USDA Geospatial Data Gateway](https://gdg.sc.egov.usda.gov/) or the full dataset can be downloaded using the [USGS FTP](ftp://rockyftp.cr.usgs.gov/vdelivery/Datasets/Staged/WBD/).  

To use the example study area, make a "gis\huc8" subfolder and then copy all of the files in the example study area shapefile from the github repository example folder:
```
> mkdir gis\huc8\
> copy ..\et-demands\example\huc8\wbdhu8_albers.* gis\huc8\
```

The study area shapefile then needs to be projected to the CDL spatial reference, and converted to a raster that all of the other prep scripts will reference.  The following will buffer the study area extent by 300m.  The "cdl" and "year" parameters are needed to get the CDL spatial reference information.
```
> python ..\et-demands\prep\build_study_area_raster.py -shp gis\huc8\wbdhu8_albers.shp --cdl ..\common\cdl\2010_30m_cdls.img --buffer 300 --stats -o
```

###### Cropland Data Layer (CDL)
The CDL raster can then be clipped to the study area:
```
> python ..\et-demands\prep\clip_cdl_raster.py --cdl ..\common\cdl\2010_30m_cdls.img --stats -o
```

###### Elevation
Elevation data is set using the 30m (1 arc-second) or 10m (1/3 arc-second) National Elevation Dataset (NED) rasters.  These can be easily downloaded in 1x1 degree tiles for the CONUS from the [USGS FTP](rockyftp.cr.usgs.gov) in the folder vdelivery/Datasets/Staged/Elevation.  They can also be downloaded using the provided DEM download script. 
```
> python ..\et-demands\prep\download_dem_raster.py --tiles ..\common\dem\tiles
```

Merge and clip the DEM tiles to the study area:
```
> python ..\et-demands\prep\merge_dem_rasters.py --tiles ..\common\dem\tiles -o --stats
```

Mask the non-agricultural DEM pixels (based on CDL)
```
> python ..\et-demands\prep\build_ag_dem_rasters.py --mask -o --stats
```

###### Soils
```
> python ..\et-demands\prep\rasterize_soil_polygons.py -o --stats
```

```
> python ..\et-demands\prep\build_ag_soils_rasters.py -o
```
