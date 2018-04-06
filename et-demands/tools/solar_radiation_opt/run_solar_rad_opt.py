#!/usr/bin/env python

# script to DRI solar radiation optimation program with an Excel workbook for input met data

import sys
import os
import subprocess

binDir = os.getcwd()
# print "bin directory is " + binDir
file_name = 'RecordedMetData.xlsx'
sheet_delim = "Sheet1"
# sheet_delim = "csv"
station_elev = 422
station_lat = 35.14887
station_lon = 98.46607
# debug_flag = False
debug_flag = True
comparison_flag = False
# comparison_flag = True
# save_temp_flag = False
save_temp_flag = True
mc_iterations = 20000

line = "python \"" + binDir + os.sep + "solar_radiation_opt.py\"" + " --file " + file_name
line = line + " --elev " + str(station_elev) + " --lat " + str(station_lat) + " --lon " + str(station_lon)
line = line + " -mc " + str(mc_iterations)
line = line + " -sd " + sheet_delim
if debug_flag: line = line + " -d"
if comparison_flag: line = line + " -c"
if save_temp_flag: line = line + " -s"
print "command line is " + line

# '''
proc = subprocess.Popen(line)
proc.wait()
if proc.returncode == 0:
    print "Run was sucessful.\n"
else:
    print "Run exited with error code ", proc.returncode, ".\n"
# '''
