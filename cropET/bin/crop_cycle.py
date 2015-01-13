#!/usr/bin/env python

import math
from pprint import pprint
import sys

import numpy as np

import crop_et_data
import compute_crop_et
from initialize_crop_cycle import InitializeCropCycle
#import setup_crop
##import util

VERBOSE = True
VERBOSE = False
COMPARE = False
COMPARE = True

def crop_cycle(data, cell_id, nsteps, basin_id, OUT, odir=''):
    """ """
    #        ' following is for one crop grown back to back over entire ETr sequence

    # do bare soil first, before looping through crops
    # current curve file has 60 curves, so 44 is not correct relative to coefficients
    '''
       ' start with crop type 44 (bare soil, winter mulch) and run through last crop first '<------ specific value for crop number
       ' this is done to compute 'winter covers', which are bare soil, mulch and dormant turf,
       ' before any crops are processed.  Bare soil is "crop" no. 44.
    '''
    # parameters in PMControl, these values are for klamath
    # currently used to populate cropGDDTriggerDoy & cropGDDTriggerDoy in
    # data.ctrl[] dictionary, so probably not needed here
    #CGDDWinterDoy = 274
    #CGDDMainDoy = 1

    et_cell = data.et_cells[cell_id]
    #print et_cell
    #pprint(vars(et_cell))
    #sys.exit()

    '''
    ## no curve for bare soil
    ctCount = 43  # bare soil
    ctCount = 1  # bare soil
    crop = data.crop_parameters[ctCount] 
    print crop
    pprint(vars(crop))
    '''

    #pprint(data.refet)
    pprint(vars(et_cell))

    ## crop loop through all crops, doesn't include bare soil??
    for i,crop in enumerate(data.crop_parameters):
        #print i, crop, crop.curve_name, et_cell.crop_flags[i]

        #pprint(vars(crop))
        # ' check to see if crop/landuse is at station
        # If cropFlags(ETCellCount, ctCount) > 0 Then
        if not et_cell.crop_flags[i]:
            if VERBOSE: print 'NOT USED: ', i+1, crop, crop.class_number, crop.curve_name, et_cell.crop_flags[i]
            continue
        if VERBOSE: print i+1,crop, crop.curve_name, crop.crop_gdd_trigger_doy
        ### for klamath_1:  3,4,11,13,16,17,21,30,44,45,46
        ### other  6,7,10,19,22,23,25,27,29,33,61,62,63,64
        #if i+1 not in (6,7,10,19,22,23,25,27,29,33,61,62,63,64):
        #if i+1 not in (46,):
        #    continue

        # for Klamath_1, output file (Klamath_pmdata/ET/Klamath_1ETc_KL_2020S0GDD_S0.dat)
        # shows 11 crops, but (txt_KlamathMetAndDepletionNodes/ETCellsCrops.txt) only flags 10

        # InitializeCropCycle()
        # 'foo' is holder of all these global variables for now
        foo = InitializeCropCycle()

        ## original has tons of i/o setup in here, we will write at end.
        #pprint(vars(data.crop_coeffs[19]))

        ##### TP04 try to access directly or rename locally
        ##### this reassigns data to simpler names, etc
        #' first time through for crop, load basic crop parameters and process climate data
        #setup_crop.crop_load(data, crop, foo)
        foo.crop_load(data, et_cell, crop)

        # write data for crop
        cropnn = crop.name.replace(' ','_').replace('/','_').replace('-','_')[:32]
        if COMPARE: 
            if not odir:
                ofn = 'cet/%s/py/%s_%s.%s' % (
                    basin_id, cell_id, crop.class_number, cropnn)
            else:
                ofn = '%s/%s_%s.%s' % (
                    odir, cell_id, crop.class_number, cropnn)
            ofp = open(ofn, 'w')
            fmt = '%8s %3s %9s %9s %9s %9s %9s %9s %9s %5s %9s %9s\n' 
            header = ('#   Date','doy','PMETo','Pr.mm','T30','ETact','ETpot','ETbas','Irrn','Seasn','Runof','DPerc')
            ofp.write(fmt % header)

        #print 'ET:: %11s %3s %8.5f %8.5f %8.5f %8.5f %8.5f %8.5f %2d %8.5f %8.5f %8.5f' % tup
        crop_day_loop(data, et_cell, crop, foo, ofp, nsteps, OUT)


class DayData:
    def __init__(self):
        """ """

def crop_day_loop(data, et_cell, crop, foo, ofp, nsteps, OUT):
    """ """
    ## day loop
    foo_day = DayData()
    # used  in ComputeCropGDD(), needs to be persistant during day loop
    foo_day.etref_array = np.zeros(30)  

    # originally in ProcessClimate() in vb code
    if data.ctrl['refETType'] > 0:
        refet_array = data.refet['ASCEPMStdETr']
    else:
        refet_array = data.refet['ASCEPMStdETo']

    #for i,ts in enumerate(data.refet['ts'][:730]):
    #for i,ts in enumerate(data.refet['ts'][:18]):
    #for i,ts in enumerate(data.refet['ts'][:365]):
    for i,ts in enumerate(data.refet['ts'][:nsteps]):
        if VERBOSE: print i, data.refet['Dates'][i]
        doy = ts[7]
        year = ts[0]
        month = ts[1]
        day = ts[2]

        precip = data.refet['Precip'][i]
        wind = data.refet['Wind'][i]
        tdew = data.refet['TDew'][i]
        #ETr = data.refet['ASCEPMStdETr'][i]
        eto = data.refet['ASCEPMStdETo'][i]
        etref = refet_array[i]

        if VERBOSE: print doy, year, month, day, precip, wind, tdew,
        if VERBOSE: print eto, etref

        # in original there was 80 lines of alternative Tmax/Tmin for climate change scenarios
        '''
         ' set TMax, TMin, TMean, T30, long-term T30, and long-term cumGDD
         ' as a function of alternative TMax TMin option
         ' blank of zero is no use of alternative TMax and TMin data
         ' 1 is use of alternative TMax and TMin for annual crops only
         ' 2 is use of alternative TMax and TMin for perennial crops only
         ' 3 is use of alternative TMax and TMin for all crops 
        '''
        # ' default is no use of alternative TMax and TMin
        tmax = data.climate['tmax_array'][i]
        tmin = data.climate['tmin_array'][i]
        tmean = data.climate['tmean_array'][i]
        t30 = data.climate['t30_array'][i]
        # Precip converted to mm in process_climate()
        precip = data.climate['precip'][i]        
        if VERBOSE: print tmax, tmin, tmean, t30

        # copies of these were made using loop
        cumgdd_0lt = np.copy(data.climate['maincumGDD0LT'])
        t30_lt = np.copy(data.climate['mainT30LT'])

        #' this is done before calling ETc
        #' determine if this is a valid day (for use in assessing alfalfa cuttings in that file)
        #' use ETref to determine

        # some stuff here left out
        ### TP05 this has to do with printing output or mysterious shit I don't understand....skip for now
        # variables set validDaysPerYear & expectedYear, but seem unused
        # except for printing ???

        if VERBOSE: print crop, crop.curve_name, crop.curve_number

        # ' at very start for crop, set up for next season
        if not foo.in_season and foo.crop_setup_flag:
            foo.setup_crop(crop)

        # ' at end of season for each crop, set up for nongrowing and dormant season
        #foo.dormant_setup_flag = True   # for testing SetupDormant()
        if not foo.in_season and foo.dormant_setup_flag:
            OUT.debug('CropCycle():  in_season %s dormant_setup_flag %s\n' % (
                foo.in_season, foo.dormant_setup_flag))
            foo.setup_dormant(data, et_cell, crop)

        if VERBOSE: print 'in_season[%s], crop_setup_flag[%s], dormant_setup_flag[%s]' % (
            foo.in_season, foo.crop_setup_flag, foo.dormant_setup_flag)

        foo_day.sdays = i+1
        foo_day.doy = doy
        foo_day.year = year
        foo_day.month = month
        foo_day.day = day
        foo_day.date = data.refet['Dates'][i]
        foo_day.tmax_original = data.refet['TMax'][i]
        foo_day.tdew = tdew
        foo_day.wind = wind
        foo_day.etref = etref
        foo_day.tmean = tmean
        foo_day.tmin = tmin
        foo_day.tmax = tmax
        foo_day.snow_depth = data.climate['snow_depth'][i]
        foo_day.cumgdd_0lt = cumgdd_0lt
        #foo_day.t30_lt = t30_lt
        foo_day.t30 = t30
        foo_day.precip = precip
        #pprint(vars(foo_day))

        #print data.climate.keys()
        # ' calculate Kcb, Ke, ETc, etc.
        #If Not ComputeCropET(T30) Then Return False
        compute_crop_et.compute_crop_et(
            t30, data, crop, et_cell, foo, foo_day, OUT)

        ## Write vb-like output file for comparison
        if COMPARE: 
            #   ' print to final daily file
            #   ' print date and ETref information first, if first crop in cycle
            #print 'ET:: ',data.refet['Dates'][i], doy, ETref, Precip, T30, foo.ETcact, foo.ETcpot, foo.ETcbas
            m,d,y = data.refet['Dates'][i].split('/')
            date = '%4s%02d%02d' % (y, int(m), int(d))
            tup = (date, doy, etref, precip, t30, foo.etc_act, foo.etc_pot,
                   foo.etc_bas, foo.irr_simulated, foo.in_season, foo.SRO,
                   foo.Dpr)
            fmt = '%8s %3s %9.3f %9.3f %9.3f %9.3f %9.3f %9.3f %9.3f %5d %9.3f %9.3f\n'
            ofp.write(fmt % tup)


        # write final output file variables to DEBUG file
        m,d,y = data.refet['Dates'][i].split('/')
        date = '%4s%02d%02d' % (y, int(m), int(d))
        tup = (etref, precip, t30, foo.etc_act, foo.etc_pot, foo.etc_bas, 
               foo.irr_simulated, foo.in_season, foo.SRO, foo.Dpr)
        s = ('zcrop_cycle(): 0ETref %s  1Precip %s 2T30 %s  3ETact %s'+
             '4ETpot %s  5ETbas %s  6Irrn %s  7Season %s  8Runoff %s '+
             '9DPerc %s\n')
        OUT.debug(s % tup)

        #pprint(vars(foo_day))
        #print len(foo_day.T30LT)
        #pprint(data.climate['mainT30LT'])
        #pprint(data.climate['maincumGDD0LT'])
        #pprint(vars(foo))

        if VERBOSE: print 'ZZZ', i, data.refet['Dates'][i]

    #print et_cell.num_crop_sequence
    #pprint(vars(data))


def main():
    """ """
    # _test() loads the data for Klamath
    #data = cropet_data._test()
    #pprint(data.refet)

if __name__ == '__main__':
    main()
