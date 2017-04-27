#!/usr/bin/env python

import sys
import os
import datetime
import logging
import pandas as pd
import numpy as np
import math

def valid_date(string_dt):
    """Check that date string is ISO format (YYYY-MM-DD)

    This function is used to check format of dates entered as command line arguments.

    Args:
        string_dt: input date string
    Returns:
        string_dt: output date string
    Raises:
        ArgParse ArgumentTypeError
    """
    try:
        input_dt = datetime.datetime.strptime(string_dt, "%Y-%m-%d")
        return string_dt
    except ValueError:
        msg = "Not valid date: '{0}'.".format(string_dt)
        raise argparse.ArgumentTypeError(msg)

def date_is_between(date_to_test, date_one, date_two):
    """Deterimines if a date is between two dates
    Args:
        date_to_test: date to test
        date_one: first date
        date_two: second date
    Returns:
        boolean: True or False
    """
    if date_to_test.to_julian_date() >= date_one.to_julian_date() and \
            date_to_test.to_julian_date() <= date_two.to_julian_date():
        return True
    else:
        return False

def crop_eff_precip(ngs_toggle, precip, season, crop_et, sim_irr, runoff, deep_perc):
    """ compute crop effective precipitation
    Args:
        ngs_toggle: non growing season toggle
        precip: precipitation
        season: crop season flag (0 or 1)
        crop_et: crop evapotranspiration
        sim_irr: simulated irrgation amount
        runoff: surface runoff
        deep_perc: deep percolation
    Returns:
        cep: crop effective precipitation
    """
    if ngs_toggle == 2 and season == 0:
        cep = 0
    else:
        if sim_irr > 0 and deep_perc > 0:
            cep = precip - runoff - max(0, deep_perc - sim_irr)
        else:
            if sim_irr > 0:
                cep = precip - runoff
            else:
                cep = precip - runoff - deep_perc
    return cep

def read_average_monthly_wb_data(wbname, wsname, skip_lines = 1):
    """read average monthly data from a workbook
    Args:
        wbname: workbook name
        wsname: worksheet name
        skip_lines: rows of file to skip
    Returns:
        boolean: sucess flag
        d: average monthly values by site
    """
    d = {}
    try:
        df = pd.read_excel(wbname, sheetname = wsname, index_col = 0, header = None, 
                skiprows = skip_lines, na_values = ['NaN'])
        df.drop(list(df.columns)[0], axis = 1, inplace = True)
        
        # move data into a dictionary    (Unable to get df.to_dict to work)
        
        for node_id, row in df.iterrows():
            d[node_id] = row.values.tolist()
        return True, d
    except: 
        logging.error('\nERROR: ' + sys.exc_info()[0] +  ' occurred reading average monthly data from worksheet ' +  wsname + ' of workbook ' +  wbname + '.\n')
        return False, d

def read_average_monthly_csv_data(fn, skip_lines = 1, delimiter = ","):
    """read average monthly data from a delimited text file
    Args:
        fn: file name
        skip_lines: rows of file to skip
        delimiter: values separator
    Returns:
        boolean: sucess flag
        d: average monthly values by site
    """
    d = {}
    try:
        df = pd.read_table(fn, engine = 'python', index_col = 0, header = None, 
                skiprows = skip_lines, sep = delimiter)
        df.drop(list(df.columns)[0], axis = 1, inplace = True)
        
        # move data into a dictionary    (Unable to get df.to_dict to work)
        
        for node_id, row in df.iterrows():
            d[node_id] = row.values.tolist()
        return True, d
    except: 
        logging.error('\nERROR: ' + sys.exc_info()[0] +  ' occurred reading average monthly delimited text data from ' +  fn + '\n')
        return False, d

def read_average_monthly__text_data(fn, skip_lines = 1, delimiter = ","):
    """read average monthly data from a delimited text file
    Args:
        fn: file name
        skip_lines: rows of file to skip
        delimiter: values separator
    Returns:
        boolean: sucess flag
        d: average monthly values by node_id
    """
    d = {}
    try:
        for i, line in enumerate(open(fn)):
            if i < skip_lines: continue
            line_values = line.split(delimiter)
            node_id = line_values[0]
            d[node_id] = [float(i) for i in line_values[2:14]]
        return True, d
    except: return False, d

def fill_from_avg_monthly(daily_value, avg_monthly_value):
    """file daily values from average monthly values
    Args:
        daily_value: existing daily value
        avg_monthly_value: average monthly value
    Returns:
        daily_value: filled daily value
    """
    if pd.isnull(daily_value):
        return avg_monthly_value
    else:
        return daily_value

def is_winter(et_cell, foo_day):
    """Determine if input day is in winter month

    Args:
        et_cell (): ETCell object
        foo_day (): Placeholder object
        
    Returns:
        boolean that is True if input day is in winter month
    """
    if et_cell.stn_lat > 0 and (foo_day.month < 4 or foo_day.month > 10):
        ## Northern hemisphere
        return True
    else:
        ## Southern hemisphere
        return False

def calculate_ratios(c1, c2):
    """Calculate ratios of two NumPy arrays or df columns

    Args:
        c1: column 1 values
        c2: column 2 values

    Returns:
        NumPy array of ratios
    """
    if c2 == 0.0:
        return 1.0
    else:
        return c1 / c2
    
def avg_two_arrays(c1, c2):
    """Computes average of two NumPy arrays or df columns

    Args:
        c1: column 1 values
        c2: column 2 values

    Returns:
        NumPy array of average values
    """
    return 0.5 * (c1 + c2)
    
def pair_from_elev(elevation):
    """Calculates air pressure as function of elevation using ASCE 2005 equation 3

    Args:
        elevation: NumPy array of elevations [m]

    Returns:
        NumPy array of air pressures [kPa]
    """
    return 101.3 * np.power((293.0 - 0.0065 * elevation) / 293.0, 5.26)

def tdew_from_ea(ea):
    """Calculates vapor pressure at given temperature

    Args:
        temperature: NumPy array of temperatures [C]

    Returns:
        NumPy array of vapor pressures [kPa]
    """
    return (237.3 * np.log(ea / 0.6108)) / (17.27 - np.log(ea / 0.6108))

def file_logger(logger = logging.getLogger(''), log_level = logging.DEBUG,
                output_ws = os.getcwd()):
    """Create file logger"""
    logger.setLevel(log_level)
    log_file = logging.FileHandler(
       os.path.join(output_ws, 'debug.txt'), mode='w')
    log_file.setLevel(log_level)
    log_file.setFormatter(logging.Formatter('%(message)s'))
    logger.addHandler(log_file)
    return logger

def console_logger(logger = logging.getLogger(''), log_level = logging.INFO):
    """Create console logger"""
    import sys
    logger.setLevel(log_level)
    log_console = logging.StreamHandler(stream = sys.stdout)
    log_console.setLevel(log_level)
    log_console.setFormatter(logging.Formatter('%(message)s'))
    logger.addHandler(log_console)
    return logger

def parse_int_set(nputstr = ""):
    """Return list of numbers given string of ranges

    http://thoughtsbyclayg.blogspot.com/2008/10/parsing-list-of-numbers-in-python.html
    """
    selection = set()
    invalid = set()
    # tokens are comma seperated values
    
    tokens = [x.strip() for x in nputstr.split(',')]
    for i in tokens:
        try:
            # typically tokens are plain old integers
            
            selection.add(int(i))
        except:
            # if not, then it might be range
            
            try:
                token = [int(k.strip()) for k in i.split('-')]
                if len(token) > 1:
                    token.sort()
                    # we have items seperated by dash
                    # try to build valid range
                    first = token[0]
                    last = token[len(token)-1]
                    for x in range(first, last+1):
                        selection.add(x)
            except:
                # not an int and not range...

                invalid.add(i)
    return selection
