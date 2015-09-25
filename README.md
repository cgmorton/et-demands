# CropET
Crop ET Demands Model

#### Running the tools/scripts
Currently, the scripts should be run from the windows command prompt (or Linux terminal) so that the input file can be passed as an argument directly to the script.  It is possible to execute some scripts by double clicking, but this is still in development.

###### Help
To see what arguments are available for a script, and their default values, pass the "-h" argument.
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

###### Input file
The key parameters in the input file are the folder location of the current project and CropET scripts.  To set the input file, use the "-i" or "--ini" argument.
```
> python run_basin.py -i example.ini
```

###### Multiprocessing
The CropET scripts do support basic multiprocessing that can be enabled using the "-mp N" argument, where N is the number of cores to use.  If N is not set, the script will attempt to use all cores.  For each ET cell, N crops will be run in parallel.  Using multiprocessing will typically be must faster, but the speed improvement may not scale linearly with the number of cores because the processes are all trying to write to disk at the same time.
```
> python run_basin.py -i example.ini -mp
```
```

#### Plots
Plots of the ET, ETo, Kc, growing season, irrigation, precipitation, and NIWR can be generated using the plotting tool.  The plots are generated using [Bokeh](http://bokeh.pydata.org/en/latest/) and saved as HTML files.  The output folder for the plots is set in the input file, typically "daily_plots".
```
> python ..\et-demands\tools\plot_py_crop_daily_timeseries.py -i example.ini
