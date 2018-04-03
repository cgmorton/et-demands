#Chris Test Change



# CropET
Crop ET Demands Model

## Documentation
ET-Demands [Manual and Documentation](http://et-demands.readthedocs.io/en/latest/)

## Running the tools/scripts
Currently, the scripts should be run from the windows command prompt (or Linux terminal) so that the input file can be passed as an argument directly to the script.  It is possible to execute some scripts by double clicking, but this is still in development.

#### Help
To see what arguments are available for a script, and their default values, pass the "-h" argument to the script.
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

#### Input file
The key parameters in the input file are the folder location of the current project and CropET scripts.  To set the input file, use the "-i" or "--ini" argument.
```
> python run_basin.py -i example.ini
```

#### Multiprocessing
The CropET scripts do support basic multiprocessing that can be enabled using the "-mp N" argument, where N is the number of cores to use.  If N is not set, the script will attempt to use all cores.  For each ET cell, N crops will be run in parallel.  Using multiprocessing will typically be must faster, but the speed improvement may not scale linearly with the number of cores because the processes are all trying to write to disk at the same time.
```
> python run_basin.py -i example.ini -mp
```

#### Plots
Plots of the ET, ETo, Kc, growing season, irrigation, precipitation, and NIWR can be generated using the plotting tool.  The plots are generated using [Bokeh](http://bokeh.pydata.org/en/latest/) and saved as HTML files.  The output folder for the plots is set in the input file, typically "daily_plots".
```
> python ..\et-demands\tools\plot_py_crop_daily_timeseries.py -i example.ini
```

## Dependencies
The ET-Demands tools have only been tested using Python 2.7 but they may work with Python 3.X.

Please see the requirements.txt file for details on the versioning requirements.  Older versions of the modules may work but have not been extensively tested.

#### CropET
+ [NumPy](http://www.numpy.org)
+ [Pandas](http://pandas.pydata.org)

#### Prep tools
A combination of GDAL and ArcPy are currently used in the data prep scripts.  Eventually all of the ArcPy/ArcGIS dependent scripts will be converted to GDAL.
+ [GDAL](http://gdal.org/)
+ ArcPy (ArcGIS)

#### Spatial crop parameters
+ [PyShp](https://github.com/GeospatialPython/pyshp)

#### Time series figures
+ [Bokeh](http://bokeh.pydata.org/en/latest/) is only needed if generating daily time series figures (tools/plot_crop_daily_timeseries.py).  Must be version 0.12.0 to support new responsive plot features.

#### Summary maps
The following modules are only needed if making summary maps (tools/plot_crop_summary_maps.py)

+ [Matplotlib](http://matplotlib.org)
+ [Fiona](https://github.com/Toblerity/Fiona)
+ [Descartes](https://bitbucket.org/sgillies/descartes)
+ [Shapely](https://github.com/Toblerity/Shapely)

## Anaconda

The easiest way to install the required external Python modules is to use [Anaconda](https://www.continuum.io/downloads)

It is important to double check that you are calling the Anaconda version, especially if you have two or more version of Python installed (e.g. Anaconda and ArcGIS).

+ Windows: "where python"
+ Linux/Mac: "which python"

#### ArcPy (Windows only)

ArcPy is only needed for two of the prep scripts, which will eventually be modified to use GDAL instead. Until the ArcPy dependency is removed, it is important to install a version of Anaconda that will work with ArcGIS/ArcPy.  If you have the standard 32-bit version of ArcGIS installed, make sure to download the 32-bit Python 2.7 version of Anaconda.  You should install the 64-bit Python 2.7 version of Anaconda if you have installed the ArcGIS 64-bit background geoprocessing add-on.

To access the ArcPy modules from Anaconda, it is necessary to copy the following file from the ArcGIS Python site-packages folder into the Anaconda site-packages folder. (the paths and file names may be slightly different depending on your installation of ArcGIS and Anaconda)

From:
+ (*32-bit*) C:\Python27\ArcGIS10.3\Lib\site-packages\Desktop10.3.pth
+ (*64-bit*) C:\Python27\ArcGISx6410.3\Lib\site-packages\DTBGGP64.pth

To:
+ C:\Anaconda2\Lib\site-packages

ArcPy can be imported if no errors are returned by the following command:
```
> python -c "import arcpy"
```

#### Conda Forge

After installing Anaconda, add the [conda-forge](https://conda-forge.github.io/) channel by entering the following in the command prompt or terminal:
```
> conda config --add channels conda-forge
```

#### Installing Modules

External modules can installed all at once (this is the preferred approach):
```
> conda install numpy scipy pandas gdal bokeh
```

or one at a time:
```
> conda install numpy
> conda install pandas
> conda install bokeh
```

#### GDAL_DATA

After installing GDAL, you may need to manually set the GDAL_DATA user environmental variable.

###### Windows
You can check the current value of the variable by typing the following in the command prompt:
```
echo %GDAL_DATA%
```
If GDAL_DATA is set, this will return a folder path (something similar to C:\Anaconda2\Library\share\gdal)

If GDAL_DATA is not set, type the following in the command prompt (note, your path may vary):
```
> setx GDAL_DATA "C:\Anaconda2\Library\share\gdal"
```

The GDAL_DATA environment variable can also be set through the Windows Control Panel (System -> Advanced system settings -> Environment Variables).
