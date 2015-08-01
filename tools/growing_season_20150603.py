#--------------------------------
# Name:         growing_season.py
# Purpose:      Extract growing season data from ETca files
# Author:       Charles Morton
# Created       2015-06-03
# Python:       2.7
#--------------------------------

import csv
import datetime as dt
import logging
import os
import re
##import shutil
import sys
from time import clock

import numpy as np

def main(workspace):
    try:
        ## Field names
        year_field   = 'Year'
        doy_field    = 'DoY'
        month_field  = 'Mo'
        day_field    = 'Dy'
        pmeto_field  = 'PMETo'
        precip_field = 'Prmm'

        etact_field  = 'ETact'
        etbas_field  = 'ETbas'
        irrig_field  = 'Irrn'
        season_field = 'Seasn'

        ## Build list of site files
        ##site_file_re = '^RG\d{8}ETca.dat$'
        ##site_file_list = sorted([item for item in os.listdir(workspace)
        ##                         if re.match(site_file_re, item)])
        site_file_list = sorted([item for item in os.listdir(workspace)
                                 if 'ETca.dat' in item])

        ## Crops will be skipped that are listed here
        ##   (list crop # as int, not string)
        crop_skip_list = [44, 45, 46, 55]

        ## Output file/folder names
        gs_summary_name = 'growing_season_full_summary.csv'
        gs_mean_annual_name = 'growing_season_mean_annual.csv'
        baddata_name = 'growing_season_bad_data.txt'
        kc_name = 'kc_files'

        ## Output file paths
        gs_summary_path = os.path.join(workspace, gs_summary_name)
        gs_mean_annual_path = os.path.join(workspace, gs_mean_annual_name)
        baddata_path = os.path.join(workspace, baddata_name)
        kc_path = os.path.join(workspace, kc_name)



        ## Build output folder
        if not os.path.isdir(kc_path): os.mkdir(kc_path)

        ## Initialize output data arrays and open bad data log file
        total_clock = clock()
        gs_summary_data = []
        gs_mean_annual_data = []
        baddata_file = open(baddata_path, 'w')

        ## Process each site file
        for site_file_name in site_file_list:
            site_clock = clock()
            logging.info("File: {0}".format(site_file_name))
            site_file_path = os.path.join(workspace, site_file_name)

            ## Read in file to memory
            site_file_open = open(site_file_path, 'r')
            site_header_list = site_file_open.readlines()[:4]
            site_file_open.close()
            del site_file_open

            ## Parse crop list (split on Crop:, remove white space)
            crop_list = site_header_list[3]
            crop_list = crop_list.replace('--', '-')
            crop_list = [item.strip() for item in crop_list.split('Crop:')]

            ## First item may be number of crops, but don't use
            del crop_list[0]
            num_crops =  len(crop_list)
            logging.debug("  Number of Crops: {0}\n".format(num_crops))

            ## These could be used to clean up crop names
            ##crop_list = [item.replace('--', '-') for item in crop_list]
            ##crop_list = [re.split('\(+', item)[0].strip()
            ##             for item in crop_list]
            ##crop_list = [re.split('(-|\()+', item)[0].strip()
            ##             for item in crop_list]

            ## Convert crop number to int for sorting
            ## Don't sort crop_list, it is identical to crop order in file
            crop_list = [
                (int(item.split(" ", 1)[0]), item.split(" ", 1)[-1])
                 for item in crop_list]
            logging.debug("Crops: \n{0}\n".format(crop_list))
            
            ## Read data from file into record array (structured array)
            data = np.genfromtxt(site_file_path, skip_header=4, names=True)
            logging.debug("Fields: \n{0}\n".format(data.dtype.names))

            ## Build list of unique years
            year_list = [int(year) for year in sorted(list(set(data['Year'])))]
            logging.debug("Years: \n{0}".format(year_list))

            ## Build separate arrays for each field of non-crop specific data
            doy_array = data[doy_field].astype(np.int)
            year_array = data[year_field].astype(np.int)
            month_array = data[month_field].astype(np.int)
            day_array = data[day_field].astype(np.int)
            pmeto_array = data[pmeto_field]
            precip_array = data[precip_field]
            date_array = np.array([
                "{0}/{1}/{2}".format(year, int(month), int(day))
                for year, month, day in zip(year_array, month_array, day_array)])

            ## Process each crop
            for crop_i, (crop_num, crop_name) in enumerate(crop_list):
                crop_clock = clock()
                if crop_num in crop_skip_list:
                    logging.debug("  Skipping, crop number in skip list")
                    continue
                
                ## Field names are built based on the crop i value
                if crop_i == 0:
                    etact_sub_field = etact_field
                    etbas_sub_field = etbas_field
                    irrig_sub_field = irrig_field
                    season_sub_field = season_field
                else:
                    etact_sub_field = '{0}_{1}'.format(etact_field, crop_i)
                    etbas_sub_field = '{0}_{1}'.format(etbas_field, crop_i)
                    irrig_sub_field = '{0}_{1}'.format(irrig_field, crop_i)
                    season_sub_field = '{0}_{1}'.format(season_field, crop_i)

                ## Build separate arrays for each set of crop specific fields
                etact_array = data[etact_sub_field]
                etbas_array = data[etbas_sub_field]
                irrig_array = data[irrig_sub_field]
                season_array = data[season_sub_field]
                kc_array = etact_array / pmeto_array
                kcb_array = etbas_array / pmeto_array

                ## Save a Kc file for each station/crop
                kc_name = 'Kc_{0}_Crop_{1:02d}.csv'.format(
                    os.path.splitext(site_file_name)[0], crop_num)
                kc_columns = [
                    'DATE', 'YEAR', 'MONTH', 'DAY', 'DOY',
                    pmeto_field, 'PPT', etact_field, etbas_field,
                    'Kc', 'Kcb', 'Season', 'Irrigation']
                kc_rec_array = np.rec.fromarrays(
                    (date_array, year_array, month_array, day_array, doy_array,
                     pmeto_array, precip_array, etact_array, etbas_array,
                     kc_array, kcb_array, season_array, irrig_array),
                    names=kc_columns)
                kc_fmt = [
                    '%s', '%d', '%d', '%d', '%03d',
                    '%.6f', '%.6f', '%.6f', '%.6f',
                    '%.6f', '%.6f', '%d', '%.6f']
                np.savetxt(
                    os.path.join(kc_path, kc_name), kc_rec_array, delimiter=",", 
                    fmt=kc_fmt, header=','.join(kc_columns), comments='')
                del kc_name, kc_columns, kc_rec_array, kc_fmt

                ## Open a new Kc file for each station/crop
                ##kc_name = 'Kc_{0}_Crop_{1:02d}.csv'.format(
                ##    os.path.splitext(site_file_name)[0], crop_num)
                ##kc_csv = csv.writer(open(os.path.join(kc_path, kc_name), 'wb'))
                ##kc_csv.writerow(
                ##    ['Date', 'Year', 'Month', 'Day', 'DOY',
                ##     pmeto_field, 'PPT', etact_field, etbas_field,
                ##     'Kc', 'Kcb', 'Season', 'Irrigation'])

                ## Save Kc data to file then cleanup kc specific arrays
                ## np.array([site_file_name]*len(doy_array))
                ## np.array([crop_num]*len(doy_array))
                ## DEADBEEF - This has problems converting/joining arrays of different types
                ## The exponential notation is not being handled correctly
                ##temp_array = np.transpose(np.vstack(
                ##    [date_array, year_array, month_array, day_array, doy_array,
                ##     pmeto_array, precip_array, etact_array, etbas_array,
                ##     kc_array, kcb_array, season_array, irrig_array]))
                ##kc_csv.writerows(temp_array)
                ##del kc_csv, kc_name
                ##del temp_array
                del etact_array, etbas_array, irrig_array, kc_array, kcb_array

                ## Initialize mean annual growing season length variables
                length_sum, length_cnt, length_mean = 0, 0, 0
                start_sum, start_cnt, start_mean = 0, 0, 0
                end_sum, end_cnt, end_mean = 0, 0, 0

                ## Process each year
                for year in year_list:                   
                    year_clock = clock()
                    year_crop_str = "Crop: {0:2d} {1:32s}  Year: {2}".format(
                        crop_num, crop_name, year)
                    logging.debug(year_crop_str)     

                    ## Extract data for target year
                    year_mask = (year_array==year)
                    doy_sub_array = doy_array[year_mask]
                    season_index = np.where(season_array[year_mask]==1)[0]

                    ## Calculate start and stop day of year
                    ## Set start/end to 0 if season never gets set to 1
                    if not np.any(season_index):
                        skip_str = "  Skipping, season flag was never set to 1"
                        logging.debug(skip_str)
                        baddata_file.write(
                            '{0}  {1} {2}\n'.format(site_file_name, year_crop_str, skip_str))
                        start_doy, end_doy = 0, 0
                        start_date, end_date = "", ""
                        end_date = ""
                    else:
                        start_doy = int(doy_sub_array[season_index[0]])
                        end_doy = int(doy_sub_array[season_index[-1]])
                        start_date = doy_2_date(year, start_doy)
                        end_date = doy_2_date(year, end_doy)
                    logging.debug("Start: {0} ({1})  End: {2} ({3})".format(
                        start_doy, start_date, end_doy, end_date))

                    ## Track growing season length and mean annual g.s. length
                    if end_doy >= start_doy > 0:
                        start_sum += start_doy
                        end_sum += end_doy
                        gs_length = (end_doy - start_doy + 1)
                        length_sum += gs_length
                        start_cnt += 1
                        end_cnt += 1
                        length_cnt += 1
                    else:
                        gs_length = 0

                    ## Append data to list
                    gs_summary_data.append(
                        [site_file_name, crop_num, crop_name, year,
                         start_doy, end_doy, start_date, end_date, gs_length])
                    
                    ## Cleanup
                    del year_mask, doy_sub_array, season_index
                    del start_doy, end_doy, gs_length
                    ##break
                    
                ## Calculate mean annual growing season start/end/length
                if length_cnt > 0:
                    mean_start_doy = int(round(float(start_sum) / start_cnt))
                    mean_end_doy = int(round(float(end_sum) / end_cnt))
                    mean_length = int(round(float(length_sum) / length_cnt))
                    mean_start_date = doy_2_date(year, mean_start_doy)
                    mean_end_date = doy_2_date(year, mean_end_doy)
                else:
                    mean_start_doy, mean_end_doy, mean_length = 0, 0, 0
                    mean_start_date, mean_end_date = "", ""

                ## Append mean annual growing season data to list
                gs_mean_annual_data.append(
                    [site_file_name, crop_num, crop_name,
                     mean_start_doy, mean_end_doy,
                     mean_start_date, mean_end_date, mean_length])

                ## Cleanup
                del season_array, season_sub_field
                del length_sum, length_cnt, length_mean
                del start_sum, start_cnt, start_mean
                del end_sum, end_cnt, end_mean
                del mean_start_doy, mean_end_doy, mean_length
                del mean_start_date, mean_end_date
                ##logging.info("    CROP TIME: {0}".format(clock()-crop_clock))
                ##break

            ## Cleanup
            del year_array, month_array, day_array, doy_array, date_array
            del pmeto_array, precip_array
            del data, year_list,
            del num_crops, crop_list
            del site_header_list
            del site_file_path, site_file_name
            ##logging.info("  SITE TIME: {0}".format(clock()-site_clock))
            logging.debug("")
            ##break

        ## Close bad data file log
        baddata_file.close()

        ## Build output record array file
        gs_summary_csv = csv.writer(open(gs_summary_path, 'wb'))
        gs_summary_csv.writerow( 
            ['FILE', 'CROP_NUM', 'CROP_NAME', 'YEAR',
             'START_DOY', 'END_DOY', 'START_DATE', 'END_DATE', 'GS_LENGTH'])
        gs_summary_csv.writerows(gs_summary_data)

        ## Build output record array file
        gs_mean_annual_csv = csv.writer(open(gs_mean_annual_path, 'wb'))
        gs_mean_annual_csv.writerow( 
            ['FILE', 'CROP_NUM', 'CROP_NAME', 'MEAN_START_DOY', 'MEAN_END_DOY',
             'MEAN_START_DATE', 'MEAN_END_DATE', 'MEAN_GS_LENGTH'])
        gs_mean_annual_csv.writerows(gs_mean_annual_data)

        ## Cleanup
        del gs_summary_path, gs_summary_name
        del gs_summary_csv, gs_summary_data
        del gs_mean_annual_path, gs_mean_annual_name
        del gs_mean_annual_csv, gs_mean_annual_data
        logging.info("\nTOTAL TIME: {0}".format(clock()-total_clock))

    except:
        logging.exception("Unhandled Exception Error\n\n")
        raw_input("Press ENTER to close")

def doy_2_date(test_year, test_doy):
    test_date = dt.datetime.strptime(
        '{0} {1}'.format(test_year, test_doy), '%Y %j').strftime('%Y/%m/%d')
    return test_date

################################################################################
if __name__ == '__main__':
    ## Create Basic Logger
    logging.basicConfig(level=logging.INFO, format='%(message)s')

    ## Run Information    
    logging.info("\n%s" % ("#"*80))
    logging.info("%-20s %s" % ("Run Time Stamp:", dt.datetime.now().isoformat(' ')))
    logging.info("%-20s %s" % ("Current Directory:", os.getcwd()))
    logging.info("%-20s %s\n" % ("Script:", os.path.basename(sys.argv[0])))

    main(os.getcwd())
