#--------------------------------
# Name:         emprso_w_tr.py
# Purpose:      Thornton-Running clear sky and empirical solar radiation
# Author:       Charles Morton
# Created       2015-12-08
# Python:       2.7
#--------------------------------

from math import pi

import numpy as np


def emprso_w_tr(lat, p, ea, doy, deltaT, tmax_tmin,
                b0=0.031, b1=0.201, b2=-0.185):
                # b0=0.023, b1=0.1, b2=-0.2):
    """

    Args:
        lat: given lat at station [decimal deg]
        p: pressure at station [kPa]
        ea: actual vapor pressure [kPa]
        doy: day of year
        deltaT: mean monthly difference between climatological Tmax and Tmin
          i.e. 12 values
        tmax_tmin: []
        b0:
        b1:
        b2:

    Returns:
        Rso: NumPy array of theoretical clear sky solar radiation []
        Rs: NumPy array of empirical solar radiation
    """

    # Convert latitude to radians
    lat_rad = lat * pi / 180

    # Solar constant [MJ m-2 h-1]
    gsc = 4.92

    # Eqn 24
    sinb24 = np.sin(
        0.85 + 0.3 * lat_rad * np.sin((2 * pi / 365) * np.array(doy) - 1.39) -
        0.42 * lat_rad ** 2)

    # Eqn 22 Precipitable water
    w = 0.14 * np.array(ea) * p + 2.1

    # Atmospheric clearness coefficient ranges from 0-1 for clean air
    ktb = 0.9

    # Eqn 21 Index of atmospheric clearness for direct beam radiation
    kb = 0.98 * np.exp(((-0.00146 * p) / (ktb * sinb24)) - 0.075 * (w / sinb24) ** 0.4)

    # Eqn 51 Solar declination angle [radians]
    sda = 0.409 * np.sin(2 * pi * np.array(doy) / 365 - 1.39)

    # Eqn 23 Index of transmissivity for diffuse radiation
    kb_mask = kb[:] > 0.15
    kd = np.empty(kb.shape)
    kd[kb_mask] = -0.36 * kb[kb_mask] + 0.35
    kd[~kb_mask] = 0.82 * kb[~kb_mask] + 0.18

    # Eqn 20 Atmospheric transmissivity
    kt = kb + kd

    ws = np.arccos(-1 * np.tan(lat_rad) * np.tan(sda))

    # Eqn 18 Squared inverse relative distance factor
    dr = 1 + 0.033 * np.cos((2 * pi / 365) * doy)

    # Eqn 17 Exoatmospheric radiation
    ra = 24 / pi * gsc * dr * (
        ws * np.sin(lat_rad) * np.sin(sda) +
        np.cos(lat_rad) * np.cos(sda) * np.sin(ws))

    # Eqn 16 Theoretical solar radiation
    rso = kt * ra

    # Eqn 15 Empirical fitting coefficient
    # From Allen and Robison
    # b = 0.023 + 0.1 * np.exp(-0.2 * deltaT)
    # Original Thornton-Running coefficeints
    # b = 0.031 + 0.201 * np.exp(-0.185 * deltaT)
    b = b0 + b1 * np.exp(b2 * deltaT)

    # Eqn 14 Empirical solar radiation
    rs = rso * (1 - 0.9 * np.exp(-1 * b * tmax_tmin ** 1.5))

    return rso, rs
