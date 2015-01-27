#!/usr/bin/env python

import math
from pprint import pprint
import sys

import numpy as np

import crop_et_data

VERBOSE = True
VERBOSE = False

def process_climate(cell, nsteps):
    """ 
    
    compute long term averages (DAY LOOP)
        adjust and check temperature data
        process alternative TMax and TMin
    fill in missing data with long term doy average (DAY LOOP)
        Calculate an estimated depth of snow on ground using simple melt rate function))
        compute main cumGDD for period of record for various bases for constraining earliest/latest planting or GU
        only Tbase = 0 needs to be evaluated (used to est. GU for alfalfa, mint, hops)
    compute long term mean cumGDD0 from sums (JDOY LOOP)

    AltTMaxArray, AltTMinArray in code has to do with when future climate
    gets so much warmer that annuals are starting too soon, in this case,
    they used the historical, ie, AltTMaxArray, AltTMinArray == historical,
    so IGNORE   

    Also lots of missing data substitution stuff going on, ignore, this
    should be taken care of outside of process
    """

    if VERBOSE: pprint(cell.refet)

    aridity_adj = [0., 0., 0., 0., 1., 1.5, 2., 3.5, 4.5, 3., 0., 0., 0.]

    tmax = np.copy(cell.refet['TMax'])
    tmin = np.copy(cell.refet['TMin'])
    aridity_rating = cell.aridity_rating

    ## Seems most/all of what goes on in day loop could be done with array math    
    ## Maybe change later after validating code
    #for i,ts in enumerate(cell.refet['ts']):
    for i,ts in enumerate(cell.refet['Dates'][:nsteps]):
        if VERBOSE: print i,ts,type(ts),

        month = ts[1]
        day = ts[2]

        ## Compute long term averages
        ## Adjust and check temperature data

        ##originalTMax(sdays - 1) = TMax ' hold onto original TMax value for computing RHmin later on (for Kco), 12/2007, Allen
        ##If aridity_rating(ETCellCount) > 0 Then ' adjust T's downward if station is arid
        if aridity_rating > 0:
            # Interpolate value for aridity adjustment
            moa_frac = month + (day - 15) / 30.4
            moa_frac = min([max([moa_frac, 1]), 11])
            #moa_base = Int(CDbl(moa_frac))
            #moa_base, frac = math.modf(moa_frac)
            moa_base = int(moa_frac)
            arid_adj = (
                aridity_adj[moa_base] +
                (aridity_adj[moa_base + 1] - aridity_adj[moa_base]) *
                (moa_frac - moa_base))
            if VERBOSE: print tmax[i],
            tmax[i] = tmax[i] - aridity_rating / 100. * arid_adj
            tmin[i] = tmin[i] - aridity_rating / 100. * arid_adj

            if VERBOSE: print moa_frac, tmax[i]

            # Fill in missing data with long term doy average
            # This should be done in separate process,
            #   prior to any refet or cropet calcs (30 lines of code)

        #if i > 366:
        #    break
        #    sys.exit()

    # T30 stuff, done after temperature adjustments above
    tmean = (tmax + tmin) * 0.5
    t30_array = np.zeros(len(tmax)) 
    nrecordmainT30 = np.zeros(367)
    mainT30LT = np.zeros(367)
    maincumGDD0LT = np.zeros(367)
    nrecordMainCumGDD = np.zeros(367)

    sd_array = np.copy(cell.refet['SnowDepth'])
    swe_array = np.copy(cell.refet['Snow'])

    ## Need to do precip conversion to mm, from hundreths of inches
    precip_array = np.copy(cell.refet['Precip']) * 25.4 / 100.

    mainT30 = 0.0
    snow_accum = 0.0
    for i in range(len(cell.refet['Dates'][:nsteps])):
        if VERBOSE: print i,cell.refet['Dates'][i],
        doy = cell.refet['Dates'][i][7] 

        # ' Calculate an estimated depth of snow on ground using simple melt rate function))
        if len(sd_array) > 0:
            snow = swe_array[i]
            snow_depth = sd_array[i]
            
            ### [140610] TP, the ETo file has snow in hundreths, not tenths????
            snow = snow / 10 * 25.4 #'tenths of inches to mm
            swe_array[i] = snow
            #snow = swe_array(sdays - 1)  # ???
            snow_depth = snow_depth * 25.4 #' inches to mm
            
            # Calculate an estimated depth of snow on ground using simple melt rate function))
            snow_accum += snow * 0.5 #' assume a settle rate of 2 to 1
            snow_melt = 4 * tmax[i] #' 4 mm/day melt per degree C
            snow_melt = max(snow_melt, 0.0)
            snow_accum = snow_accum - snow_melt
            snow_accum = max(snow_accum, 0.0)
            snow_depth = min(snow_depth, snow_accum)
            sd_array[i] = snow_depth

        if i > 29:
            mainT30 = sum(tmean[i-29:i+1]) / 30
        else:
            mainT30 = (mainT30 * (i) + tmean[i]) / (i+1)
        t30_array[i] = mainT30

        # Build cummulative over period of record
        nrecordmainT30[doy] += 1
        mainT30LT[doy] = (mainT30LT[doy] * (nrecordmainT30[doy] - 1) + mainT30) / nrecordmainT30[doy] 

        if VERBOSE: print t30_array[i]

        ## Compute main cumgdd for period of record for various bases for
        ##   constraining earliest/latest planting or GU
        ## Only Tbase = 0 needs to be evaluated
        ##   (used to est. GU for alfalfa, mint, hops)
        if i == 0 or doy == 1: 
            mainGDD0 = 0.0

        ## Tbase(ctCount) -- have no idea what ctCount value should be, since this
        ## is before start of CropCycle & each crop has own Tbase value in
        ## crop_parameters.py, use 0.0 for now, since appears may be ctCount
        ##  Based on previous comment, assume Tbase = 0.0
        tbase = 0.0
        if tmean[i] > 0: #' simple method for all other crops
            gdd = tmean[i] - tbase
        else:
            gdd = 0.0

        mainGDD0 = mainGDD0 + gdd
        maincumGDD0LT[doy] = maincumGDD0LT[doy] + mainGDD0
        nrecordMainCumGDD[doy] += 1

    ## Compute long term mean cumGDD0 from sums
    for doy in range(1,367):
        if nrecordMainCumGDD[doy] > 0:
             maincumGDD0LT[doy] = maincumGDD0LT[doy] / nrecordMainCumGDD[doy]
        else:
             maincumGDD0LT[doy] = 0.0

    ## Keep refet values intact & return any 'modified' variables in new mapping 
    d = {}
    d['tmax_array'] = tmax
    d['tmin_array'] = tmin
    d['tmean_array'] = tmean
    d['t30_array'] = t30_array
    d['mainT30LT'] = mainT30LT
    d['maincumGDD0LT'] = maincumGDD0LT
    d['snow_depth'] = sd_array
    d['snow'] = swe_array
    d['precip'] = precip_array
    return d


def main():
    """ """
    pass
    # _test() loads the data for Klamath
    #data = cropet_cell._test()
    #pprint(data.refet)

if __name__ == '__main__':
    main()
