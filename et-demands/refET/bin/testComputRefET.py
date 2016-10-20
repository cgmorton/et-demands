#!/usr/bin/env python

import sys
import datetime
import refET


def readMetaData(fn='exampleData_alan/KlamathMetNodesMet.csv'):
    """ """
    d = {}
    for i, line in enumerate(open(fn)):
        #print i, line
        line = line.strip().replace(' ','')
        if i < 1:
            continue
        l = line.split(',')
        site = l[1]
        d[site] = ( float(l[3]), float(l[5]), l[6], l[8] )
    return d



def readDailyCSV(fn='exampleData_alan/KL2020DailyCCTMax.csv', d={}):
    """ """
    #d = {}

    for i, line in enumerate(open(fn)):
        #print i, line
        line = line.strip().replace(' ','')
        if i == 0:
            keys = line.split(',')
            for key in keys:
                d[key] = []
            continue

        vals = line.split(',')
        for i,key in enumerate(keys):
            #if i > 0:
            #    val = float(i)
            d[key].append(vals[i])

        #sys.exit()
    return d


def readMon(fn, skip=1):
    """ """
    d = {}
    for i, line in enumerate(open(fn)):
        #print i, line
        line = line.strip().replace(' ','').replace(',,','')
        if i < skip:
            continue
        l = line.split(',')
        site = l[0]
        d[site] = [float(i) for i in l[2:]]
    return d


def getDailyTemps():
    """ """
    # read daily temperatures
    fn = 'exampleData_alan/KL2020DailyCCTMax.csv'
    temperatures = readDailyCSV(fn)

    fn = 'exampleData_alan/KL2020DailyCCTMin.csv'
    temperatures = readDailyCSV(fn, temperatures)

    #print temperatures.keys()
    #print temperatures['Date'][:10]
    #print temperatures['OR1571.MaximumTemperature'][:10]
    #print temperatures['CA9026.MaximumTemperature'][:10]
    #print temperatures['OR8007.MinimumTemperature'][:10]

    return temperatures


def getDateParams(date='1/1/1950'):
    """ """
    mo,da,yr = date.split('/')
    mo = int(mo)
    da = int(da)
    yr = int(yr)
    doy = datetime.datetime(yr,mo,da).timetuple().tm_yday
    return yr,mo,da,doy


"""
Required inputs:
TMean doy latitude elevm TDew TMax TMin avgTMax avgTMin da timeStep u242(wind?)
"""
def test_ComputeRefET():
    """ Test & compare against PC version """#

    temperatures = getDailyTemps()   # degrees F

    site = 'OR1571'
    fp = open('tmp/%s' % site, 'w')

    latitude, elev_ft, windStationId, KoStationId = readMetaData('exampleData_alan/KlamathMetNodesMeta.csv')[site]
    print site, windStationId, KoStationId, latitude, elev_ft

    #KoStationId = 'OR4511'
    staKo = readMon('exampleData_alan/KoMon.csv', 1)[KoStationId]    # degrees C
    staWind = readMon('exampleData_alan/AveWindMon.csv', 2)[windStationId]   
    #print 'staWind', staWind
    avgTMax = readMon('exampleData_alan/TMaxMon.csv', 1)[site]   
    avgTMin = readMon('exampleData_alan/TMinMon.csv', 1)[site]   

    elevm = elev_ft*.3048

    timeStep = 24  # 24 hour timestep
    sdays = 0      # used for debugging

    #def ComputeRefET(yr, mo, da, doy, timeStep, sdays, TMax, TMin, TMean, TDew, u24, elevm, latitude, sr, avgTMax, avgTMin, Resett): 
    o = refET.refET()

    Resett = 0
    for i,date in enumerate(temperatures['Date']):
        #if i > 0:
        #    sys.exit()

        yr,mo,da,doy = getDateParams(date)
        print date, yr,mo,da,doy,

        TMax = (float(temperatures[site+'.MaximumTemperature'][i]) - 32.)/1.8
        TMin = (float(temperatures[site+'.MinimumTemperature'][i]) - 32.)/1.8
        TMean = (TMax+TMin)/2.

        # estimate dew point
        ko = staKo[mo-1]
        TDew = TMin - ko

        print 'Tx:%.4f Tn:%.4f Tm:%.4f Td:%.4f Txm:%.4f Tnm:%.4f' % (TMax,TMin,TMean,TDew,avgTMax[mo-1],avgTMin[mo-1]),

        # wind
        u24 = staWind[mo-1]
        print 'W:%.4f' % u24,

        # solar radiation, flag to use Thornton & Running method
        sr = -999.0

        # this will always be zero based on the VB code, looks like the intent
        # was to change to 2 after the very first time-step, but was passed
        # byVal instead of byRef, so that change looks like it wouldn't
        # happen, to me at least
        #Resett = 0
        penman_results, Harg, Rs = o.ComputeRefET(yr, mo, da, doy, timeStep, sdays, TMax, TMin, TMean, TDew, 
                                        u24, elevm, latitude, sr, avgTMax[mo-1], avgTMin[mo-1], Resett)
        # this looks like it would honor intent, but not actual code
        #Resett = 2

        Penman, PreTay, KimbPeng, ASCEPMstdr, ASCEPMstdo, FAO56PM, KimbPen = penman_results
        print 'Alfalfa:%.4f Grass:%.4f' % (ASCEPMstdr, ASCEPMstdo)
        #print 'Rs ', Rs


        #fmt = '%s %9.6f %9.6f %.6f %.4f %.6f %12.10f %12.10f %12.10f %12.10f %12.10f\n'
        fmt = '%s %.6f %.6f %.14f %.14f %.14f %.14f %.14f %.14f %.14f %.14f\n'
        s = fmt % (date,TMax,TMin,Rs,u24,TDew,Penman,PreTay,ASCEPMstdr,ASCEPMstdo,Harg)
        fp.write(s)



################################################################################ 
if __name__ == '__main__':
    ### testing during development
    #do_tests()        


    test_ComputeRefET()
    

