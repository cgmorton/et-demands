import argparse
import datetime
import logging
import os
import sys

import numpy as np
import pandas as pd

def main(basin_ws):
    """Compare ET-Demands output to test files

    For now, assume script will be run as "python bin\runBasin.py"
    
    Args:
        basin_ws (str): Basin folder path
        
    Returns:
        None
    """
    logging.info('\nCompare ET-Demands output to test files')

    ## Dataframe parameters
    test_sep = r'\s*'
    test_header = 0
    test_comment = '#'
    test_date_field = 'Date'

    ## Dataframe parameters
    base_sep = r'\s*'
    base_header = 0
    base_comment = '#'
    base_date_field = 'Date'

    ## Input workspaces
    test_ws = os.path.join(basin_ws, 'pmdata', 'ETc')
    base_ws = os.path.join(basin_ws, 'pmdata', 'ETc_baseline')
    logging.info('  Test Folder: {0}'.format(test_ws))
    logging.info('  Base Folder: {0}'.format(base_ws))

    ## Check workspaces
    if not os.path.isdir(test_ws):
        logging.error(
            '\nERROR: The test folder {0} could be found\n'.format(test_ws))
        sys.exit()
    elif not os.path.isdir(base_ws):
        logging.error(
            '\nERROR: The base folder {0} could be found\n'.format(base_ws))
        sys.exit()

    ## Get list of available files
    test_name_list = [
        item for item in os.listdir(test_ws)
        if os.path.isfile(os.path.join(test_ws, item))]
    base_name_list = [
        item for item in os.listdir(base_ws)
        if os.path.isfile(os.path.join(base_ws, item))]

    ## For each file in etc, try to find a baseline one
    for test_name in test_name_list:
        logging.warning('\nFile: {}'.format(test_name))

        ## First, try to find a matching file
        if test_name not in base_name_list:
            logging.warning('  No matching files in {}'.format(base_ws))
            continue

        ## Try to open both of the files
        test_path = os.path.join(test_ws, test_name)
        base_path = os.path.join(base_ws, test_name)
        try:
            test_pd = pd.read_table(
                test_path, engine='python', sep=test_sep, header=test_header,
                comment=test_comment)
        except:
            logging.warning('  Pandas could not open the test file')
            continue
        try:
            base_pd = pd.read_table(
                base_path, engine='python', sep=base_sep, header=base_header, 
                comment=base_comment)
        except:
            logging.warning('  Pandas could not open the base file')
            continue

        ## Check the columns
        ## Remove columns that are not common to both dataframes
        test_fields = test_pd.columns.values
        base_fields = base_pd.columns.values
        missing_test_fields = list(set(test_fields).difference(set(base_fields)))
        missing_base_fields = list(set(base_fields).difference(set(test_fields)))
        for field in missing_test_fields:
            logging.warning('  {} is not in the base file, skipping'.format(field))
            del test_pd[field]
        for field in missing_base_fields:
            logging.warning('  {} is not in the ETc file, skipping'.format(field))
            del base_pd[field]

        ## Convert the dates to datetimes
        test_pd[test_date_field] = pd.to_datetime(test_pd[test_date_field])
        base_pd[base_date_field] = pd.to_datetime(base_pd[base_date_field])

        ## Check the dateranges
        missing_base_dates = list(
            set(test_pd[test_date_field]) - set(base_pd[base_date_field]))
        missing_test_dates = list(
            set(base_pd[base_date_field]) - set(test_pd[test_date_field]))

        if missing_base_dates:
            logging.warning('  {} dates are not in the base file'.format(
                len(missing_base_dates)))
            missing_base_mask = ~test_pd[test_date_field].isin(pd.Series(missing_base_dates))
            test_pd = test_pd[missing_base_mask].reindex()
            for missing_date in missing_base_dates:
                logging.debug('    {}'.format(missing_date.date()))        
        if missing_test_dates:
            logging.warning('  {} dates are not in the test file'.format(
                len(missing_test_dates)))
            missing_test_mask = ~base_pd[base_date_field].isin(pd.Series(missing_test_dates))
            base_pd = base_pd[missing_base_mask].reindex()
            for missing_date in missing_test_dates:
                logging.debug('    {}'.format(missing_date.date()))

        ## For each column, count the number of values that are exactly the same
        diff_values = [0, 0.0001, 0.001, 0.01, 0.1, 1]
        logging.info('{0:>10s} {1}'.format(
            '', ' '.join(['{0:>8}'.format(x) for x in diff_values])))
        for field in test_pd.columns.values:
            if field in [test_date_field, 'DOY']:
                continue
            diff_array = np.abs(test_pd[field].values - base_pd[field].values)
            diff_list = [np.sum(diff_array <= v) for v in diff_values]
            logging.info('{0:>10s} {1}'.format(
                field, ' '.join(['{0:>8}'.format(x) for x in diff_list])))
            
################################################################################

def parse_args():  
    parser = argparse.ArgumentParser(
        description='Compare ET-Demands Output Files',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        '--debug', default=logging.INFO, const=logging.DEBUG,
        help='Debug level logging', action="store_const", dest="loglevel")
    args = parser.parse_args()
    return args          

################################################################################
if __name__ == '__main__':
    args = parse_args()
    
    ## Create Basic Logger
    logging.basicConfig(level=args.loglevel, format='%(message)s')

    main(os.getcwd())
