import datetime as dt
import logging
import os

import pandas as pd
import numpy as np

def es_from_t(t):
    """ Tetens (1930) equation for sat. vap pressure, kPa, (T in C)

    Args:
        t (float): temperature [C]

    Returns:
        A float ofsaturated vapor pressure [kPa]
    """
    return 0.6108 * np.exp((17.27 * t) / (t + 237.3))

def es_ice_from_t(t):
    """ Murray (1967) equation for sat. vap pressure over ice, kPa, (T in C)

    Args:
        t (float): temperature [C]

    Returns:
        A float ofsaturated vapor pressure over ice [kPa]
    """
    return 0.6108 * np.exp((21.87 * t) / (t + 265.5))

def is_winter(et_cell, foo_day):
    """Determine ifinput day is in a winter month

    Args:
        et_cell (): ?
        foo_day (): ?

    Returns:
        A boolean that is True ifinput day is in a winter month
    """
    if et_cell.latitude > 0 and (foo_day.month < 4 or foo_day.month > 10):
    # if et_cell.cell_lat > 0 and (foo_day.month < 4 or foo_day.month > 10):
        # Northern hemisphere
        return True
    else:
        # Southern hemisphere
        return False

def pair_from_elev(elevation):
    """Calculates air pressure as a function of elevation

    Args:
        elevation: NumPy array of elevations [m]

    Returns:
        NumPy array of air pressures [kPa]
    """
    # version converted from vb.net
    
    # return 101.3 * ((293. - 0.0065 * elevm) / 293.) ** (9.8 / (0.0065 * 286.9)) # kPa ' standardized by ASCE 2005
    
    # version from from DRI
    
    # return 101.3 * np.power((293.0 - 0.0065 * elevation) / 293.0, 5.26)

    # version extended to better match vb.net version
    # 5.255114352 = 9.8 / (0.0065 * 286.9
    
    return 101.3 * np.power((293.0 - 0.0065 * elevation) / 293.0, 5.255114352)

def ea_from_q(p, q):
    """Calculates vapor pressure from pressure and specific humidity

    Args:
        p: NumPy array of pressures [kPa]
        q: NumPy array of specific humidities [kg / kg]

    Returns:
        NumPy array of vapor pressures [kPa]
    """
    return p * q / (0.622 + 0.378 * q)

def q_from_ea(ea, p):
    """Calculates specific humidity from vapor pressure and pressure

    Args:
        ea: NumPy array of vapor pressures [kPa]
        p: NumPy array of pressures [kPa]

    Returns:
        NumPy array of ]specific humidities [kg / kg]
    """
    return 0.622 * ea / (p - 0.378 * ea)

def tdew_from_ea(ea):
    """Calculates vapor pressure at a given temperature

    Args:
        temperature: NumPy array of temperatures [C]

    Returns:
        NumPy array of vapor pressures [kPa]
    """
    return (237.3 * np.log(ea / 0.6108)) / (17.27 - np.log(ea / 0.6108))

def valid_date(input_date):
    """Check that a date string is ISO format (YYYY-MM-DD)

    This function is used to checkformat of dates entered as command
      line arguments.
    DEADBEEF - It would probably make more sense to have this function
      parsedate using dateutil parser (http://labix.org/python-dateutil)
      and returnISO format string

    Args:
        input_date: string
    Returns:
        string
    Raises:
        ArgParse ArgumentTypeError
    """
    try:
        input_dt = dt.datetime.strptime(input_date, "%Y-%m-%d")
        return input_date
    except ValueError:
        msg = "Not a valid date: '{0}'.".format(input_date)
        raise argparse.ArgumentTypeError(msg)

def wind_adjust_func(uz_array, zw):
    """Adjust wind speed to 2m"""
    return uz_array * 4.87 / np.log(67.8 * zw - 5.42)

def file_logger(logger=logging.getLogger(''), log_level=logging.DEBUG,
                output_ws=os.getcwd()):
    """Create file logger"""
    logger.setLevel(log_level)
    log_file = logging.FileHandler(
       os.path.join(output_ws, 'debug.txt'), mode='w')
    log_file.setLevel(log_level)
    log_file.setFormatter(logging.Formatter('%(message)s'))
    logger.addHandler(log_file)
    return logger

def console_logger(logger=logging.getLogger(''), log_level=logging.INFO):
    """Create console logger"""
    import sys
    logger.setLevel(log_level)
    log_console = logging.StreamHandler(stream=sys.stdout)
    log_console.setLevel(log_level)
    log_console.setFormatter(logging.Formatter('%(message)s'))
    logger.addHandler(log_console)
    return logger

def parse_int_set(nputstr=""):
    """Return list of numbers given a string of ranges

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
            # if not, then it might be a range
            try:
                token = [int(k.strip()) for k in i.split('-')]
                if len(token) > 1:
                    token.sort()
                    # we have items seperated by a dash
                    # try to build a valid range
                    first = token[0]
                    last = token[len(token)-1]
                    for x in range(first, last+1):
                        selection.add(x)
            except:
                # not an int and not a range...
                invalid.add(i)
    # Report invalid tokens before returning valid selection
    # print "Invalid set: " + str(invalid)
    return selection
