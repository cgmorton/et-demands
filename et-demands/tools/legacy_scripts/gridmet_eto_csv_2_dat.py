#--------------------------------
# Name:         gridmet_eto_csv_2_dat.py
# Purpose:      Convert GRIDMET 4km datarods to RefET output format for CropET
# Author:       Charles Morton
# Created       2015-12-08
# Python:       2.7
#--------------------------------

import datetime as dt
import logging
import math
import os
import sys

import numpy as np
import pandas as pd


def main(project_ws):
    """Convert GRIDMET 4km datarods to RefET output format for CropET

    Args:
        project_ws (str):

    Returns:
        None
    """
    eto_ws = os.path.join(project_ws, 'pmdata', 'ETo')
    static_ws = os.path.join(project_ws, 'static')
    station_path = os.path.join(static_ws, 'ETCellsProperties.txt')

    station_field = 'Ref ET MET ID'
    elev_field = 'Met Elevation (feet)'

    # Check input folders
    if not os.path.isdir(eto_ws):
        logging.error(
            "\nERROR: The ETo workspace {} does not exist.\n".format(
                    eto_ws))
        sys.exit()
    elif not os.path.isdir(static_ws):
        logging.error(
            "\nERROR: The static workspace {} does not exist.\n".format(
                    static_ws))
        sys.exit()
    elif not os.path.isfile(station_path):
        logging.error(
            "\nERROR: The station file {} does not exist.\n".format(
                    station_path))
        sys.exit()

    # Get the station elevations
    station_array = np.loadtxt(station_path, delimiter='\t', dtype='str')
    header_list = list(station_array[0])
    station_i = header_list.index(station_field)
    elev_i = header_list.index(elev_field)
    station_elev_dict = dict()
    for row in station_array[1:]:
        station_elev_dict[row[station_i]] = float(row[elev_i]) * 0.3048

    # Process each ETo file
    for item in os.listdir(eto_ws):
        if not item.endswith('.csv'):
            continue
        print item

        # Get the GRIDMET cell ID
        station_id = item.split('.')[0].split('_')[1]

        input_csv = os.path.join(eto_ws, item)
        output_dat = os.path.join(eto_ws, '{0}.dat'.format(station_id))

        # Read input GRIDMET datarod CSV
        data_df = pd.read_csv(
            input_csv, sep=',', parse_dates=[[0, 1, 2]],
            date_parser=lambda *columns: dt.date(*map(int, columns)))

        # Remove extra columns
        data_df = data_df.drop('DOY', 1)

        # Add extra columns (using RefET column names)
        data_df['Snow'] = pd.Series(0, index=data_df.index)
        data_df['SDep'] = pd.Series(0, index=data_df.index)
        data_df['Penm48'] = pd.Series(0, index=data_df.index)
        data_df['PreTay'] = pd.Series(0, index=data_df.index)
        data_df['85Harg'] = pd.Series(0, index=data_df.index)

        # Year, Month, Day, DOY, Tmin(K), Tmax(K), Specific Humidity(kg kg-1),
        # Wind @ 10m (m s-1), Solar Radiation (W m-2), Precipitation (mm),
        # ETo @ 2m (mm day-1), ETr @ 2m(mm day-1)

        # Rename columns
        data_df.rename(columns={'Year_Month_Day':'Date'}, inplace=True)
        data_df.rename(columns={'Tmax(K)':'TMax'}, inplace=True)
        data_df.rename(columns={'Tmin(K)':'TMin'}, inplace=True)
        data_df.rename(columns={'Wind @ 10m (m s-1)':'EsWind'}, inplace=True)
        data_df.rename(columns={'Solar Radiation (W m-2)':'EstRs'}, inplace=True)
        data_df.rename(columns={'Precipitation (mm)':'Precip'}, inplace=True)
        data_df.rename(columns={'Specific Humidity(kg kg-1)':'EsTDew'}, inplace=True)
        data_df.rename(columns={'ETo @ 2m (mm day-1)':'ASCEg'}, inplace=True)
        data_df.rename(columns={'ETr @ 2m(mm day-1)':'ASCEr'}, inplace=True)

        # Reorder columns
        data_df = data_df.loc[:,['Date', 'TMax', 'TMin', 'Precip', 'Snow', 'SDep',
                                 'EstRs', 'EsWind', 'EsTDew', 'Penm48', 'PreTay',
                                 'ASCEr', 'ASCEg', '85Harg']]

        # Convert temperature from K to C
        data_df['TMax'] -= 273.15
        data_df['TMin'] -= 273.15

        # Convert W/m2 to MJ/m2
        data_df['EstRs'] *= 0.0864

        # Scale wind from 10m to 2m
        data_df['EsWind'] *= 4.87 / math.log(67.8 * 10 - 5.42)

        # Convert specific humidity to Tdew
        pair_array = pair_func(0.3048 * station_elev_dict[station_id])
        ea_array = ea_from_q(pair_array, data_df['EsTDew'])
        data_df['EsTDew'] = tdew_from_ea(ea_array)

        # Write to tab delimited file
        data_df.to_csv(output_dat, '\t', index=False)

def pair_func(elevation):
    """Calculates air pressure as a function of elevation

    Args:
        elevation: NumPy array of elevations [m]

    Returns:
        NumPy array of air pressures [kPa]
    """
    return 101.3 * np.power((293.0 - 0.0065 * elevation) / 293.0, 5.26)

def ea_from_q(p, q):
    """Calculates vapor pressure from pressure and specific humidity

    Args:
        p: NumPy array of pressures [kPa]
        q: NumPy array of specific humidities [kg / kg]

    Returns:
        NumPy array of vapor pressures [kPa]
    """
    return p * q / (0.622 + 0.378 * q)

def tdew_from_ea(ea):
    """Calculates vapor pressure at a given temperature

    Args:
        temperature: NumPy array of temperatures [C]

    Returns:
        NumPy array of vapor pressures [kPa]
    """
    return (237.3 * np.log(ea / 0.6108)) / (17.27 - np.log(ea / 0.6108))


if __name__ == '__main__':
    main(os.getcwd())
