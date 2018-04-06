#Chris Test Change



# CropET
Crop ET Demands Model

## Documentation
ET-Demands [Manual and Documentation](http://et-demands.readthedocs.io/en/latest/)

## Running tools/scripts
Currently, scripts should be run from windows command prompt (or Linux terminal) so that configuration file can be passed as an argument directly to script.  It is possible to execute some scripts by double clicking, but this is still in development.

#### Help
To see what arguments are available for a script and their default values, pass "-h" argument to script.
```
> python run_ret.py -h
usage: run_ret.py [-h] [-i PATH] [-d] [-v] [-m [M]] [-mp [N]]

Reference ET

optional arguments:
  -h, --help            show this help message and exit
  -i PATH, --ini PATH   Configuration (initialization) file (default: None)
  -d, --debug           Save debug level comments to debug.txt (default:
                        False)
  -v, --verbose         Print info level comments (default: False)
  -m, --metid		Met node id to run (default 'ALL')
  -mp [N], --multiprocessing [N]
                        Number of processers to use (default: 1)

> python run_cet.py -h
usage: run_cet.py [-h] [-i PATH] [-d] [-v] [-c [C]] [-mp [N]]

Crop ET-Demands

optional arguments:
  -h, --help            show this help message and exit
  -i PATH, --ini PATH   Configuration (initialization) file (default: None)
                        False)
  -d, --debug           Save debug level comments to debug.txt (default:
                        False)
  -v, --verbose         Print info level comments (default: False)
  -c, --etcid		ET cell to run (default 'ALL')
  -mp [N], --multiprocessing [N]
                        Number of processers to use (default: 1)

> python run_aet.py -h
usage: run_aet.py [-h] [-i PATH] [-d] [-v] [-c [C]] [-mp [N]]

Area ET

optional arguments:
  -h, --help            show this help message and exit
  -i PATH, --ini PATH   Configuration (initialization) file (default: None)
  -d, --debug           Save debug level comments to debug.txt (default:
                        False)
  -v, --verbose         Print info level comments (default: False)
  -c, --etcid		ET cell to run (default 'ALL')
  -mp [N], --multiprocessing [N]
                        Number of processers to use (default: 1)
```

#### User manual

[View or download](docs/PythonETApplications.pdf)

#### Configuration files
Key parameters in configuration files are folder location of current project, static (meta) data file specifcatins and time series data specifications.  To set configuration file, use "-i" or "--ini" argument.
```
> python run_cet.py -i cet_example.ini
> python run_ret.py -i csv_ret_dri.ini
> python run_cet.py -i csv_cet_dri.ini
> python run_aet.py -i dri_aet_csv.ini
```

#### Multiprocessing
The ET scripts support basic multiprocessing that can be enabled using "-mp N" argument, where N is number of cores to use.  If N is not set, script will attempt to use all cores.  For each ET cell, N crops will be run in parallel.  Using multiprocessing will typically be must faster, but speed improvement may not scale linearly with number of cores because processes are all trying to write to disk at same time.
Multiprocessing is not available for single met node reference et runs or for single et cell area et runs.
Multiprocessing is not available for some output formats.
```
> python run_cet.py -i example.ini -mp
```

#### Plots
Plots of Crop ET-Demands paramters ET, ETo, Kc, growing season, irrigation, precipitation, and NIWR can be generated using plotting tool.  plots are generated using [Bokeh](http://bokeh.pydata.org/en/latest/) and saved as HTML files.  output folder for plots is set in configuration file, typically "daily_plots".
```
> python ..\et-demands\tools\plot_py_crop_daily_timeseries.py -i example.ini
```

## Dependencies
The ET-Demands tools have only been tested using Python 2.7 but they may work with Python 3.X.

Please see requirements.txt file for details on versioning requirements.  Older versions of modules may work but have not been extensively tested.

#### RefET
+ [NumPy](http://www.numpy.org)
+ [Pandas](http://pandas.pydata.org)
+ [openpyxl](https://pypi.python.org/pypi/openpyxl/2.4.7)

#### CropET
+ [NumPy](http://www.numpy.org)
+ [Pandas](http://pandas.pydata.org)
+ [openpyxl](https://pypi.python.org/pypi/openpyxl/2.4.7)

#### AreaET
+ [NumPy](http://www.numpy.org)
+ [Pandas](http://pandas.pydata.org)
+ [openpyxl](https://pypi.python.org/pypi/openpyxl/2.4.7)

#### Lib
+ [NumPy](http://www.numpy.org)
+ [Pandas](http://pandas.pydata.org)
+ [openpyxl](https://pypi.python.org/pypi/openpyxl/2.4.7)

#### Prep tools
A combination of GDAL and ArcPy are currently used in data prep scripts.  Eventually all of ArcPy/ArcGIS dependent scripts will be converted to GDAL.
+ [GDAL](http://gdal.org/)
+ ArcPy (ArcGIS)

#### Spatial crop parameters
+ [PyShp](https://github.com/GeospatialPython/pyshp)

#### Time series figures
+ [Bokeh](http://bokeh.pydata.org/en/latest/) is only needed if generating daily time series figures (tools/plot_crop_daily_timeseries.py).  Must be version 0.12.0 to support new responsive plot features.

#### Summary maps
Following modules are only needed if making summary maps (tools/plot_crop_summary_maps.py)

+ [Matplotlib](http://matplotlib.org)
+ [Fiona](https://github.com/Toblerity/Fiona)
+ [Descartes](https://bitbucket.org/sgillies/descartes)
+ [Shapely](https://github.com/Toblerity/Shapely)

## Anaconda

Easiest way to install required external Python modules is to use [Anaconda](https://www.continuum.io/downloads)

It is important to double check that you are calling Anaconda version, especially if you have two or more version of Python installed (e.g. Anaconda and ArcGIS).

+ Windows: "where python"
+ Linux/Mac: "which python"

#### ArcPy (Windows only)

ArcPy is only needed for two of prep scripts, which will eventually be modified to use GDAL instead. Until ArcPy dependency is removed, it is important to install a version of Anaconda that will work with ArcGIS/ArcPy.  If you have standard 32-bit version of ArcGIS installed, make sure to download 32-bit Python 2.7 version of Anaconda.  You should install 64-bit Python 2.7 version of Anaconda if you have installed ArcGIS 64-bit background geoprocessing add-on.

To access ArcPy modules from Anaconda, it is necessary to copy following file from ArcGIS Python site-packages folder into Anaconda site-packages folder. (the paths and file names may be slightly different depending on your installation of ArcGIS and Anaconda)

From:
+ (*32-bit*) C:\Python27\ArcGIS10.3\Lib\site-packages\Desktop10.3.pth
+ (*64-bit*) C:\Python27\ArcGISx6410.3\Lib\site-packages\DTBGGP64.pth

To:
+ C:\Anaconda2\Lib\site-packages

ArcPy can be imported if no errors are returned by following command:
```
> python -c "import arcpy"
```

#### Conda Forge

After installing Anaconda, add [conda-forge](https://conda-forge.github.io/) channel by entering following in command prompt or terminal:
```
> conda config --add channels conda-forge
```

#### Installing Modules

External modules can installed all at once (this is preferred approach):
```
> conda install numpy scipy pandas gdal bokeh
```

or one at a time:
```
> conda install numpy
> conda install pandas
> conda install bokeh
```

#### Out of date module

Required openpylx (at least 2.4.7) is not yet installed with Anaconda. Install it as:
```
> pip install --upgrade openpyxl>=2.4.7
```

#### GDAL_DATA

After installing GDAL, you may need to manually set GDAL_DATA user environmental variable.

###### Windows
You can check current value of variable by typing following in command prompt:
```
echo %GDAL_DATA%
```
If GDAL_DATA is set, this will return a folder path (something similar to C:\Anaconda2\Library\share\gdal)

If GDAL_DATA is not set, type following in command prompt (note, your path may vary):
```
> setx GDAL_DATA "C:\Anaconda2\Library\share\gdal"
```

The GDAL_DATA environment variable can also be set through Windows Control Panel (System -> Advanced system settings -> Environment Variables).
