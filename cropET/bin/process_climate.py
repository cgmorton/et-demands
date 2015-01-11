#!/usr/bin/env python

from pprint import pprint
#import cropet_read
import sys
import cropet_data
import numpy as np
import math

VERBOSE = True
VERBOSE = False

#    Private Function ProcessClimate() As Boolean
def ProcessClimate(data, cell_id, nsteps):
    """ """
    '''
            ' compute long term averages (DAY LOOP)
                ' adjust and check temperature data
                ' process alternative TMax and TMin
            ' fill in missing data with long term doy average (DAY LOOP)
                ' Calculate an estimated depth of snow on ground using simple melt rate function))
                ' compute main cumGDD for period of record for various bases for constraining earliest/latest planting or GU
                ' only Tbase = 0 needs to be evaluated (used to est. GU for alfalfa, mint, hops)
            ' compute long term mean cumGDD0 from sums (JDOY LOOP)
    '''
    # AltTMaxArray, AltTMinArray in code has to do with when future climate
    # gets so much warmer that annuals are starting too soon, in this case,
    # they used the historical, ie, AltTMaxArray, AltTMinArray == historical,
    # so IGNORE   

    # Also lots of missing data substitution stuff going on, ignore, this
    # should be taken care of outside of process

    # vars used later
    # TMaxArray, TMinArray, TAvgArray, T30Array, cumGDD0LT(jdoy), T30LT(jdoy),
    # mainT30LT(DoY)

    if VERBOSE: pprint(data.refet)
    # print

    # keep refet values intact & return any 'modified' variables in new mapping 
    d = {}

    #Private aridity_adj() As Double = {0, 0, 0, 0, 1, 1.5, 2, 3.5, 4.5, 3, 0, 0, 0}
    aridity_adj = [0., 0., 0., 0., 1., 1.5, 2., 3.5, 4.5, 3., 0., 0., 0.]

    ############333 try with no loop
    '''
    TMax2 = np.copy(data.refet['TMax'])
    t = data.refet['ts']
    print t.shape
    #MoaFrac = monthOfCalcs + (dayOfCalcs - 15) / 30.4
    MoaFrac = t[:,1] + (t[:,2] - 15) / 30.4
    pprint(MoaFrac)
    #MoaFrac = min([max([MoaFrac, 1]), 11])
    m1 = np.where(MoaFrac < 1., 1., MoaFrac)
    MoaFrac2 = np.where(m1 > 11, 11, m1)
    pprint(MoaFrac2)
    pprint(MoaFrac2[:20])
    Moabase2 = MoaFrac2.astype('int')
    pprint(Moabase2[:20])

    #AridAdj = aridity_adj[Moabase] + (aridity_adj[Moabase + 1] - aridity_adj[Moabase]) * (MoaFrac - Moabase)
    '''
    ############333 try with no loop

    TMax = np.copy(data.refet['TMax'])
    TMin = np.copy(data.refet['TMin'])
    aridity_rating = data.et_cells[cell_id].aridity_rating

    # seems most/all of what goes on in day loop could be done with array math    
    # maybe change later after validating code
    #for i,ts in enumerate(data.refet['ts']):
    for i,ts in enumerate(data.refet['ts'][:nsteps]):
        if VERBOSE: print i,ts,type(ts),

        monthOfCalcs = ts[1]
        dayOfCalcs = ts[2]

        #' compute long term averages
        #' adjust and check temperature data

        #originalTMax(sdays - 1) = TMax ' hold onto original TMax value for computing RHmin later on (for Kco), 12/2007, Allen
        #If aridity_rating(ETCellCount) > 0 Then ' adjust T's downward if station is arid
        if aridity_rating > 0:
            #' interpolate value for aridity adjustment

            MoaFrac = monthOfCalcs + (dayOfCalcs - 15) / 30.4
            MoaFrac = min([max([MoaFrac, 1]), 11])
            #Moabase = Int(CDbl(MoaFrac))
            #Moabase, frac = math.modf(MoaFrac)
            Moabase = int(MoaFrac)
            AridAdj = aridity_adj[Moabase] + (aridity_adj[Moabase + 1] - aridity_adj[Moabase]) * (MoaFrac - Moabase)
            if VERBOSE: print TMax[i],
            TMax[i] = TMax[i] - aridity_rating / 100. * AridAdj
            TMin[i] = TMin[i] - aridity_rating / 100. * AridAdj


            if VERBOSE: print MoaFrac, TMax[i]
            #if VERBOSE: print MoaFrac, MoaFrac2[i], MoaFrac-MoaFrac2[i], Moabase, Moabase2[i]

            #' fill in missing data with long term doy average
            # this should be done in separate process, prior to any refet or cropet
            # calcs  (30 lines of code)

        #if i > 366:
        #    break
        #    sys.exit()

    # T30 stuff, done after temperature adjustments above
    TMean = (TMax+TMin)*0.5
    T30Array = np.zeros(len(TMax)) 
    nrecordmainT30 = np.zeros(367)
    mainT30LT = np.zeros(367)
    maincumGDD0LT = np.zeros(367)
    nrecordMainCumGDD = np.zeros(367)

    sdArray = np.copy(data.refet['SnowDepth'])
    sweArray = np.copy(data.refet['Snow'])

    ### need to do precip conversion to mm, from hundreths of inches
    precipArray = np.copy(data.refet['Precip']) * 25.4 / 100.

    mainT30 = 0.0
    Snowaccum = 0.0
    for i in range(len(data.refet['ts'][:nsteps])):
        if VERBOSE: print i,data.refet['ts'][i],
        DoY = data.refet['ts'][i][7] 

        # ' Calculate an estimated depth of snow on ground using simple melt rate function))
        if len(sdArray) > 0:
            Snow = sweArray[i]
            Snowdepth = sdArray[i]
            
            ### [140610] TP, the ETo file has snow in hundreths, not tenths????
            Snow = Snow / 10 * 25.4 #'tenths of inches to mm
            sweArray[i] = Snow
            #Snow = sweArray(sdays - 1)  # ???
            Snowdepth = Snowdepth * 25.4 #' inches to mm
            
            #' Calculate an estimated depth of snow on ground using simple melt rate function))
            
            Snowaccum = Snowaccum + Snow * 0.5 #' assume a settle rate of 2 to 1
            Snowmelt = 4 * TMax[i] #' 4 mm/day melt per degree C
            Snowmelt = max(Snowmelt, 0.0)
            Snowaccum = Snowaccum - Snowmelt
            Snowaccum = max(Snowaccum, 0.0)
            Snowdepth = min(Snowdepth, Snowaccum)
            sdArray[i] = Snowdepth


        if i > 29:
            mainT30 = sum(TMean[i-29:i+1])/30
        else:
            mainT30 = (mainT30 * (i) + TMean[i]) / (i+1)
        T30Array[i] = mainT30

        #' build cummulative over period of record
        nrecordmainT30[DoY] += 1
        mainT30LT[DoY] = (mainT30LT[DoY] * (nrecordmainT30[DoY] - 1) + mainT30) / nrecordmainT30[DoY] 

        if VERBOSE: print T30Array[i]

        #if i > 60:
        #    sys.exit()


        #' compute main cumGDD for period of record for various bases for constraining earliest/latest planting or GU
        #' only Tbase = 0 needs to be evaluated (used to est. GU for alfalfa, mint, hops)
        if i == 0 or DoY == 1: 
            mainGDD0 = 0.0

        # Tbase(ctCount) -- have no idea what ctCount value should be, since this
        # is before start of CropCycle & each crop has own Tbase value in
        # crop_parameters.py, use 0.0 for now, since appears may be ctCount
        #  Based on previous comment, assume Tbase = 0.0
        Tbase = 0.0
        if TMean[i] > 0: #' simple method for all other crops
            GDD = TMean[i] - Tbase
        else:
            GDD = 0.0

        mainGDD0 = mainGDD0 + GDD
        maincumGDD0LT[DoY] = maincumGDD0LT[DoY] + mainGDD0
        nrecordMainCumGDD[DoY] += 1

        #print i, DoY, TMean[i], TMax[i], TMin[i], maincumGDD0LT[DoY]

    #pprint(mainT30LT[:20])
    #print mainT30LT[365], len(mainT30LT)
    #pprint(nrecordMainCumGDD[:20])
    #pprint(TMean[:20])

    # ' compute long term mean cumGDD0 from sums
    for jdoy in range(1,367):
        if nrecordMainCumGDD[jdoy] > 0:
             maincumGDD0LT[jdoy] = maincumGDD0LT[jdoy] / nrecordMainCumGDD[jdoy]
        else:
             maincumGDD0LT[jdoy] = 0.0

    #pprint(T30Array)
    #pprint(mainT30LT)
    #sys.exit()

    # TMaxArray, TMinArray, TAvgArray, T30Array, cumGDD0LT, maincumGDD0LT, mainT30LT(DoY)
    d['TMaxArray'] = TMax
    d['TMinArray'] = TMin
    d['TAvgArray'] = TMean
    d['T30Array'] = T30Array
    d['mainT30LT'] = mainT30LT
    d['maincumGDD0LT'] = maincumGDD0LT
    d['SnowDepth'] = sdArray
    d['Snow'] = sweArray
    d['Precip'] = precipArray
    return d


def main():
    """ """
    # _test() loads the data for Klamath
    #data = cropet_data._test()
    #pprint(data.refet)


if __name__ == '__main__':
    main()
