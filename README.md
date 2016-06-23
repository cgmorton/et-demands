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

The easiest way to install the following modules is to use [Anaconda](https://www.continuum.io/downloads).
+ [NumPy](http://www.numpy.org)
+ [Pandas](http://pandas.pydata.org)

#### Prep tools
A combination of GDAL and ArcPy are currently used in the data prep scripts.  Eventually all of the ArcPy/ArcGIS dependent scripts will be converted to GDAL.
+ [GDAL](http://gdal.org/)
+ ArcPy (ArcGIS)

#### Spatial crop parameters
+ [PyShp](https://github.com/GeospatialPython/pyshp)

#### Time series figures
+ [Bokeh](http://bokeh.pydata.org/en/latest/) is only needed if generating daily time series figures (tools/plot_crop_daily_timeseries.py)

#### Summary maps
The following modules are only needed if making summary maps (tools/plot_crop_summary_maps.py)

+ [Matplotlib](http://matplotlib.org)
+ [Fiona](https://github.com/Toblerity/Fiona)
+ [Descartes](https://bitbucket.org/sgillies/descartes)
+ [Shapely](https://github.com/Toblerity/Shapely)