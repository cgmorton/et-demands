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

def make_datetime_from_string(string_dt):
    """Makes datetime object from string

    This function is used to make datetime date from string of unknown format

    Args:
        string_dt: date string
    Returns:
        datetime
    """
    clean_string = string_dt.replace("-","").replace("/","").replace(" ","").replace("T","").strip()
    date_string = string_dt.replace("/","-").strip()
    if len(clean_string) < 7:
        try:
            the_date = datetime.datetime.strptime(date_string, '%Y-%m')
        except:
            try:
                the_date = datetime.datetime.strptime(date_string, '%m-%Y')
            except:
                the_date = None
    elif len(clean_string) < 9:
        try:
            the_date = datetime.datetime.strptime(date_string, '%Y-%m-%d')
        except:
            try:
                the_date = datetime.datetime.strptime(date_string, '%d-%m-%Y')
            except:
                the_date = None
    elif len(clean_string) < 11:
        try:
            the_date = datetime.datetime.strptime(date_string, '%Y-%m-%d-%H')
        except:
            try:
                the_date = datetime.datetime.strptime(date_string, '%d-%m-%Y-%H')
            except:
                try:
                    the_date = datetime.datetime.strptime(date_string, '%Y-%m-%d %H')
                except:
                    try:
                        the_date = datetime.datetime.strptime(date_string, '%d-%m-%Y %H')
                    except:
                        the_date = None
    else:
        the_date = None
    return the_date

def get_periods_given_dates_timedelta(start_dt, end_dt, time_delta):
    """ computes periods in date range

    Args:
        start_dt: starting datetime
        end_dt: ending datetime
        time_step: time_delta datetime.timedelta object
    Returns:
        np: integer number of periods
    """
    if time_delta.total_seconds() > 2678400:
        np = end_dt.year - start_dt.year
    else:
        if time_delta.total_seconds() > 86400:
            np = 12 * (end_dt.year - start_dt.year - 1) + end_dt.month - start_dt.month + 12
        else:
            np =  int((end_dt - start_dt).total_seconds() / time_delta.total_seconds())
    return np

def get_periods_given_dates_timestep(start_dt, end_dt, timestep, ts_quantity = 1):
    """ computes periods in date range

    Args:
        start_dt: starting datetime
        end_dt: ending datetime
        timestep: text DMI timestep as minute, hour, day, week, month, year
        ts_quantity: quantity of timestep - 15 for 15 minutes; 6 hour for 6 hours; 12 for 12 hours; otherwise 1
    Returns:
        np: integer number of periods
    """
    if 'year' in timestep.lower():
        np = end_dt.year - start_dt.year
    elif 'month' in timestep.lower():
            np = 12 * (end_dt.year - start_dt.year - 1) + end_dt.month - start_dt.month + 12
    elif 'day' in timestep.lower():
        time_delta = datetime.timedelta(days = 1)
        np =  int((end_dt - start_dt).total_seconds() / time_delta.total_seconds())
    elif 'hour' in timestep.lower():
        time_delta = datetime.timedelta(hours = 1) * ts_quantity
        np =  int((end_dt - start_dt).total_seconds() / time_delta.total_seconds())
    elif 'minute' in timestep.lower():
        time_delta = datetime.timedelta(days = 1) * ts_quantity
        np =  int((end_dt - start_dt).total_seconds() / time_delta.total_seconds())
    elif 'week' in timestep.lower():
        time_delta = datetime.timedelta(weeks = 1)
        np =  int((end_dt - start_dt).total_seconds() / time_delta.total_seconds())
    elif 'day' in timestep.lower():
        time_delta = datetime.timedelta(days = 1)
        np =  int((end_dt - start_dt).total_seconds() / time_delta.total_seconds())
    else:
        np = end_dt.year - start_dt.year
    return np

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
        logging.error('\nERROR: ' + str(sys.exc_info()[0]) + ' occurred reading average monthly data from worksheet ' +  wsname + ' of workbook ' + wbname + '\n')
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
        logging.error('\nERROR: ' + str(sys.exc_info()[0]) + ' occurred reading average delimited text data from ' + fn + '\n')
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

def wind_adjust_func(uz_array, zw):
    """Adjust wind speed to 2m"""
    return uz_array * 4.87 / np.log(67.8 * zw - 5.42)

def max_max_temp(max_temp):
    """Adjust maximum temperature to be less than 120F"""
    return min(max_temp, (120.0 - 32.0) * 5.0 / 9.0)

def max_min_temp(min_temp):
    """Adjust minimum temperature to be less than 90F"""
    return min(min_temp, (90.0 - 32.0) * 5.0 / 9.0)

def avg_two_arrays(c1, c2):
    """Computes average of two NumPy arrays or df columns

    Args:
        c1: column 1 values
        c2: column 2 values

    Returns:
        NumPy array of average values
    """
    return 0.5 * (c1 + c2)
    
def compute_rs(doy, TMax, TMin, TDew, elevm, latitude, avgTMax, avgTMin, TR_b0, TR_b1, TR_b2): 
    """ Compute estimated incident solar radiation

    Args:
        doy: day of year
        TMax: maximum temperature
        TMin: minimum temperature
        elevm: elevation in meters
        latitude: latitude
        avgTMax: average monthly maximum temperature
        avgTMin: average monthly minimum temperature
        TR_b0: Thronton and Running b0 coefficient
        TR_b1: Thronton and Running b1 coefficient
        TR_b2: Thronton and Running b2 coefficient

    Returns:
        Rs: incident solar radiation
    """
    TAvg = 0.5 * (TMax + TMin)

    # compute extraterrestial radiation and other data needed to compute incident solar radiation

    Ra = extraterrestrial_radiation(doy, latitude)
    ed = es_from_t(TDew)
    pressure = pair_from_elev(elevm)

    # Estimate clear sky radiation (Rso)
        
    Rso = 0.0
    Rso = estimate_clear_sky_radiation(Ra, pressure, ed, latitude, doy)
    Rs = estimate_incident_radiation(Rso, TMax, TMin, avgTMax, avgTMin, TR_b0, TR_b1, TR_b2)
    return Rs

def extraterrestrial_radiation(doy, lat):
    """ Compute extraterresttrial radiaton in MG/M2/day
        
    Args:
        doy: day of year
        lat: latitude
        
    Returns:
        etr: extraterresttrial radiaton
    """
    Gsc = 0.08202 # MJ/m2/min
    latRad = lat * math.pi / 180.0  # Lat is station latitude in degrees
    decl = 0.4093 * math.sin(2.0 * math.pi * (284.0 + doy) / 365.0)
    omega = 0.5 * math.pi - math.atan((-math.tan(latRad) * math.tan(decl)) / 
            (1.0 - math.tan(decl) * math.tan(decl) * math.tan(latRad) * math.tan(latRad)) ** 0.5)
    Dr = 1.0 + 0.033 * math.cos(2.0 * math.pi * doy / 365.0)
    etr = (24.0 * 60.0 / math.pi) * Gsc * Dr * (omega * math.sin(latRad) * math.sin(decl) + 
            math.cos(latRad) * math.cos(decl) * math.sin(omega))
    return etr

def estimate_clear_sky_radiation(extRa, pressure, ed, latDeg, doy):
    """ Estimate clear sky radiation (Rso) using Appendix D method of ASCE-EWRI (2005)
        
    Args:
        extRa: extraterresttrial radiaton
        pressure: air pressure
        ed: saturation vapor pressure
        latDeg: latitude
        doy: day of year
        
    Returns:
        csRSo: clear sky radiaton
    """
    waterInAtm = 0.14 * ed * pressure + 2.1 # mm as of 9/2000 (was cm)
    latRad = latDeg * math.pi / 180
    kturb = 1.0
    sinphi24 = math.sin(0.85 + 0.3 * latRad * math.sin(2 * math.pi / 365 * doy - 1.39) - 0.42 * latRad * latRad)
    kbeam = 0.98 * math.exp((-0.00146 * pressure) / (kturb * sinphi24) - 0.075 * (waterInAtm / sinphi24) ** 0.4) # modified 9/25/2000
    if kbeam < 0.15:
        kdiffuse = 0.18 + 0.82 * kbeam
    else:
        kdiffuse = 0.35 - 0.36 * kbeam
    csRSo = (kbeam + kdiffuse) * extRa
    return csRSo

def estimate_incident_radiation(csRSo, maxT, minT, monMaxT, monMinT, TR_b0, TR_b1, TR_b2):
    """ Estimate incident radiation using equation 14
        
    Args:
        csRSo: clear sky radiaton
        maxT: maximum temperature
        minT: maximum temperature
        monMaxT: average monthly maximum temperature
        monMinT: average monthly minimum temperature
        TR_b0: Thronton and Running b0 coefficient
        TR_b1: Thronton and Running b1 coefficient
        TR_b2: Thronton and Running b2 coefficient
        
    Returns:
        incRs: incident radiaton
    """
    dt = maxT - minT          # temp difference in C
    dtMon = monMaxT - monMinT # long term monthly temp difference in C
    dt = max(0.1, dt)
    dtMon = max(0.1, dtMon)

    # Orginally used UI determined function for coefficient B based on arid stations in T-R paper
    # BTR = 0.023 + 0.1 * System.Math.Exp(-0.2 * dtMon)
    # Changed to use user specified values 11/21/2012.
    # Changed input of third Thorton and Running coefficient to include sign 08/22/2013.
    # Enabled TR coefficients to be node specific - dlk - 01/20/2016.

    BTR = TR_b0 + TR_b1 * math.exp(TR_b2 * dtMon)

    # estimate daily Rs using Thornton and Running method (added Nov. 1, 2006)
    # incRs = csRSo * (1 - 0.9 * math.exp(-BTR * dt ** 1.5)) rom Eq. 14
    incRs = csRSo * (1 - 0.9 * math.exp(-BTR * dt ** 1.5))
    return incRs

def pair_from_elev(elevation):
    """Calculates air pressure as function of elevation using ASCE 2005 equation 3

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

def tdew_from_avg_monthly_Ko(daily_tdew, daily_tmin, avg_monthly_Ko):
    """Computes dewpoint temperature from daily minimum temperature and average monthly Ko (dew point depression)

    Args:
        daily_tdew: existing daily tdew
        daily_tmin: daily tmin
        avg_monthly_Ko: average monthly Ko

    Returns:
        daily_value: filled daily tdew
    """
    if pd.isnull(daily_tdew):
        return daily_tmin - avg_monthly_Ko
    else:
        return daily_tdew

def tdew_from_ea(ea):
    """Calculates vapor pressure at given temperature

    Args:
        temperature: NumPy array of temperatures [C]

    Returns:
        NumPy array of vapor pressures [kPa]
    """
    return (237.3 * np.log(ea / 0.6108)) / (17.27 - np.log(ea / 0.6108))

def q_from_ea(ea, pressure):
    """Calculates specific humidity from vapor pressure and pressure

    Args:
        ea: NumPy array of vapor pressures [kPa]
        pressure: NumPy array of pressures [kPa]

    Returns:
        NumPy array of ]specific humidities [kg / kg]
    """
    return 0.622 * ea / (pressure - 0.378 * ea)

def tdew_from_ea(ea):
    """Calculates vapor pressure at given temperature

    Args:
        temperature: NumPy array of temperatures [C]

    Returns:
        NumPy array of vapor pressures [kPa]
    """
    return (237.3 * np.log(ea / 0.6108)) / (17.27 - np.log(ea / 0.6108))

def es_from_t(t):
    """ Tetens (1930) equation for sat. vap pressure, kPa, (T in C)
        Eq. 7 for saturation vapor pressure from dewpoint temperature
        
    Args:
        t (float): temperature [C]
        
    Returns:
        float of saturated vapor pressure [kPa]
    """
    return 0.6108 * np.exp((17.27 * t) / (t + 237.3)) 

def es_ice_from_t(t):
    """ Murray (1967) equation for sat. vap pressure over ice, kPa, (T in C)

    Args:
        t (float): temperature [C]
        
    Returns:
        float of saturated vapor pressure over ice [kPa]
    """
    return 0.6108 * np.exp((21.87 * t) / (t + 265.5)) 

def file_logger(logger = logging.getLogger(''), log_level = logging.DEBUG,
                output_ws = os.getcwd()):
    """Create file logger"""
    logger.setLevel(log_level)
    log_file = logging.FileHandler(
       os.path.join(output_ws, 'debug.txt'), mode = 'w')
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

def is_leap_year(year_to_test):
    """Test if year is a leap year
    
        Args:
            year_to_test: year to test

        Returns:
            boolean: True or False
        """
    if year_to_test % 4 == 0 and year_to_test %100 != 0 or year_to_test % 400 == 0:
        return True
    else:
        return False

def get_ts_freq(time_step, ts_quantity, wyem = 12):
    """ Get pandas time frequency given time_step and ts_quantity
    
     Args:
        time_step: RiverWare style string timestep
        ts_quantity: Interger number of time_steps's in interval

    Returns:
        ts_freq: pandas time frequency
    """
    ts_freq = None
    if time_step == 'day':
        ts_freq = "D"
    elif time_step == 'year':
        ts_freq = water_year_agg_func(wyem)
    elif time_step == 'month':
        ts_freq = "M"
    elif time_step == 'hour':
        if ts_quantity == 1:
            ts_freq = "H"
        else:
            ts_freq = str(ts_quantity) + "H"
    elif time_step == 'minute':
        if ts_quantity == 1:
            ts_freq = "T"
        else:
            ts_freq = str(ts_quantity) + "T"
    elif time_step == 'week':
        ts_freq = "W"
    else:
        logging.error('\nERROR: Timestep {} and ts quantity {} are an invalid combination', format(time_step, ts_quantity))
    return ts_freq

def water_year_agg_func(wyem):
    """Sets annual aggregation function for water year end month
    Args:
        wyem: Water Year End Month
    Return; Water year aggregation function
    """
    ann_freqs = ['A-JAN', 'A-FEB', 'A-MAR', 'A-APR', 'A-MAY', 'A-JUN'] + \
                ['A-JUL', 'A-AUG', 'A-SEP', 'A-OCT', 'A-NOV', 'A-DEC']
    return ann_freqs[wyem - 1]

def make_dt_index(time_step, ts_quantity, start_dt, end_dt, wyem = 12):
    """ Make a pandas DatetimeIndex from specified dates, time_step and ts_quantity
    
     Args:
        time_step: RiverWare style string timestep
        ts_quantity: Interger number of time_steps's in interval
        start_dt: starting date time
        end_dt: ending date time
        wyem: Water Year End Month

    Returns:
        dt_index:pandas DatetimeIndex
    """
    dt_index = None
    if time_step == 'day':
        dt_index =pd.date_range(start_dt, end_dt, freq = "D", name = "date")
    elif time_step == 'year':
        dt_index = pd.date_range(start_dt, end_dt, freq = water_year_agg_func(wyem), name = "date")
    elif time_step == 'month':
        dt_index = pd.date_range(start_dt, end_dt, freq = "M", name = "date")
    elif time_step == 'hour':
        if ts_quantity == 1:
            dt_index =pd.date_range(start_dt, end_dt, freq = "H", name = "date")
        else:
            dt_index = pd.date_range(start_dt, end_dt, freq = str(ts_quantity) + "H", name = "date")
    elif time_step == 'minute':
        if ts_quantity == 1:
            dt_index = pd.date_range(start_dt, end_dt, freq = "T", name = "date")
        else:
            dt_index = pd.date_range(start_dt, end_dt, freq = str(ts_quantity) + "T", name = "date")
    elif time_step == 'week':
        dt_index = pd.date_range(start_dt, end_dt, freq = "W", name = "date")
    else:
        logging.error('\nERROR: Timestep {} and ts quantity {} are an invalid combination', format(time_step, ts_quantity))
    return dt_index

def make_ts_dataframe(time_step, ts_quantity, start_dt, end_dt, wyem = 12):
    """ Make a pandas dataframe from specified dates, time_step and ts_quantity
    
     Args:
        time_step: RiverWare style string timestep
        ts_quantity: Interger number of time_steps's in interval
        start_dt: starting date time
        end_dt: ending date time
        wyem: Water Year End Month

    Returns:
        Empty pandas datafame wihh indexed dates
    """
    ts_dataframe = None
    if time_step == 'day':
        ts_dataframe = pd.DataFrame(index = pd.date_range(start_dt, end_dt, freq = "D", name = "date"))
    elif time_step == 'year':
        ts_dataframe = pd.DataFrame(index = pd.date_range(start_dt, end_dt, freq = water_year_agg_func(wyem), name = "date"))
    elif time_step == 'month':
        ts_dataframe = pd.DataFrame(index = pd.date_range(start_dt, end_dt, freq = "M", name = "date"))
    elif time_step == 'hour':
        if ts_quantity == 1:
            ts_dataframe = pd.DataFrame(index = pd.date_range(start_dt, end_dt, freq = "H", name = "date"))
        else:
            ts_dataframe = pd.DataFrame(index = pd.date_range(start_dt, end_dt, freq = str(ts_quantity) + "H", name = "date"))
    elif time_step == 'minute':
        if ts_quantity == 1:
            ts_dataframe = pd.DataFrame(index = pd.date_range(start_dt, end_dt, freq = "T", name = "date"))
        else:
            ts_dataframe = pd.DataFrame(index = pd.date_range(start_dt, end_dt, freq = str(ts_quantity) + "T", name = "date"))
    elif time_step == 'week':
        ts_dataframe = pd.DataFrame(index = pd.date_range(start_dt, end_dt, freq = "W", name = "date"))
    else:
        logging.error('\nERROR: Timestep {} and ts quantity {} are an invalid combination', format(time_step, ts_quantity))
    return ts_dataframe

