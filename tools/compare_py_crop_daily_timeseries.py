#--------------------------------
# Name:         compare_py_crop_daily_timeseries.py
# Purpose:      Compare daily data timeseries to baseline files
# Author:       Charles Morton
# Created       2015-12-08
# Python:       2.7
#--------------------------------

import argparse
import datetime as dt
import logging
import os
import sys

import numpy as np
import pandas as pd


def main(project_ws, crop_str=''):
    """Compare ET-Demands output to baseline files

    For now, scipt will assume it is run in the project/basin folder and will
        look for a PMData sub-folder

    Args:
        project_ws (str): Project workspace
        crop_str (str): comma separate list or range of crops to compare

    Returns:
        None
    """
    logging.info('\nCompare ET-Demands output to test files')

    # Dataframe parameters
    test_sep = ','
    test_header = 0
    test_comment = '#'
    test_date_field = 'Date'
    test_ext = '.csv'

    # Dataframe parameters
    base_sep = ','
    # base_sep = r'\s*'
    base_header = 0
    base_comment = '#'
    base_date_field = 'Date'
    base_ext = '.csv'

    # Only process a subset of the crops
    crop_list = list(parse_int_set(crop_str))

    # Input workspaces
    test_ws = os.path.join(project_ws, 'daily_stats')
    base_ws = os.path.join(project_ws, 'daily_baseline')
    logging.info('  Test Folder: {0}'.format(test_ws))
    logging.info('  Base Folder: {0}'.format(base_ws))

    # Check workspaces
    if not os.path.isdir(test_ws):
        logging.error(
            '\nERROR: The test folder {0} could be found\n'.format(test_ws))
        sys.exit()
    elif not os.path.isdir(base_ws):
        logging.error(
            '\nERROR: The base folder {0} could be found\n'.format(base_ws))
        sys.exit()

    # Get list of available files
    test_name_list = [
        item for item in os.listdir(test_ws)
        if (os.path.isfile(os.path.join(test_ws, item)) and
            item.endswith(test_ext.lower()))]
    base_name_list = [
        item for item in os.listdir(base_ws)
        if (os.path.isfile(os.path.join(base_ws, item)) and
            item.endswith(base_ext.lower()))]

    # For each file in etc, try to find a baseline one
    for test_name in test_name_list:
        # Get crop number from file
        test_crop = int(os.path.splitext(test_name)[0].split('crop_')[-1])
        if crop_list and test_crop not in crop_list:
            logging.debug('File: {}\n  Skipping crop...'.format(test_name))
            continue
        else:
            logging.warning('File: {}'.format(test_name))
            logging.debug('  Crop: {}'.format(test_crop))

        # Try to find a matching file
        base_name = os.path.splitext(test_name)[0] + base_ext
        logging.debug('  {}'.format(base_name))
        if base_name not in base_name_list:
            logging.warning('  No matching files in {}'.format(base_ws))
            continue

        # Try to open both of the files
        test_path = os.path.join(test_ws, test_name)
        base_path = os.path.join(base_ws, base_name)
        try:
            test_df = pd.read_table(
                test_path, engine='python', sep=test_sep, header=test_header,
                comment=test_comment)
        except:
            logging.warning('  Pandas could not open the test file')
            continue
        try:
            base_df = pd.read_table(
                base_path, engine='python', sep=base_sep, header=base_header,
                comment=base_comment)
        except:
            logging.warning('  Pandas could not open the base file')
            continue

        # Check the columns
        # Remove columns that are not common to both dataframes
        test_fields = test_df.columns.values
        base_fields = base_df.columns.values
        missing_test_fields = list(
            set(test_fields).difference(set(base_fields)))
        missing_base_fields = list(
            set(base_fields).difference(set(test_fields)))
        for field in missing_test_fields:
            logging.warning(
                '  {} is not in the base file, skipping'.format(field))
            del test_df[field]
        for field in missing_base_fields:
            logging.warning(
                '  {} is not in the ETc file, skipping'.format(field))
            del base_df[field]

        # Convert the dates to datetimes
        test_df[test_date_field] = pd.to_datetime(test_df[test_date_field])
        base_df[base_date_field] = pd.to_datetime(base_df[base_date_field])

        # Check the dateranges
        missing_base_dates = list(
            set(test_df[test_date_field]) - set(base_df[base_date_field]))
        missing_test_dates = list(
            set(base_df[base_date_field]) - set(test_df[test_date_field]))

        if missing_base_dates:
            logging.warning('  {} dates are not in the base file'.format(
                len(missing_base_dates)))
            missing_base_mask = ~test_df[test_date_field].isin(pd.Series(missing_base_dates))
            test_df = test_df[missing_base_mask].reindex()
            for missing_date in missing_base_dates:
                logging.debug('    {}'.format(missing_date.date()))
        if missing_test_dates:
            logging.warning('  {} dates are not in the test file'.format(
                len(missing_test_dates)))
            missing_test_mask = ~base_df[base_date_field].isin(pd.Series(missing_test_dates))
            base_df = base_df[missing_test_dates].reindex()
            for missing_date in missing_test_dates:
                logging.debug('    {}'.format(missing_date.date()))

        # For each column, count the number of values that are exactly the same
        diff_values = [0.0001, 0.001, 0.01, 0.1, 1]
        log_str = '{0:>10s} {1}\n'.format(
            '', ' '.join(['{0:>8}'.format(x) for x in diff_values]))
        # logging.info('{0:>10s} {1}'.format(
        #    '', ' '.join(['{0:>8}'.format(x) for x in diff_values])))
        log_list = []
        for field in test_df.columns.values:
            if field.upper() in [test_date_field.upper(), 'DOY', 'YEAR', 'MONTH', 'DAY']:
                continue
            diff_array = np.abs(test_df[field].values - base_df[field].values)
            diff_list = [np.sum(diff_array <= v) for v in diff_values]
            log_list += diff_list
            log_str += '{0:>10s} {1}\n'.format(
                field, ' '.join(['{0:>8}'.format(x) for x in diff_list]))
            # logging.info('{0:>10s} {1}'.format(
            #     , ' '.join(['{0:>8}'.format(x) for x in diff_list])))
        if len(set(log_list)) <= 1:
            logging.debug(log_str)
        else:
            logging.info(log_str)


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


def parse_args():
    """"""
    parser = argparse.ArgumentParser(
        description='Compare ET-Demands Output Files',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        'workspace', nargs='?', default=os.path.join(os.getcwd()),
        # 'workspace', nargs='?', default=get_pmdata_workspace(os.getcwd()),
        help='Project Folder', metavar='FOLDER')
    parser.add_argument(
        '-c', '--crops', default='', type=str,
        help='Comma separate list or range of crops to compare')
    parser.add_argument(
        '--debug', default=logging.INFO, const=logging.DEBUG,
        help='Debug level logging', action="store_const", dest="loglevel")
    args = parser.parse_args()

    # Convert project folder to an absolute path if necessary
    if args.workspace and os.path.isdir(os.path.abspath(args.workspace)):
        args.workspace = os.path.abspath(args.workspace)
    return args


if __name__ == '__main__':
    args = parse_args()

    logging.basicConfig(level=logging.INFO, format='%(message)s')
    logging.info('\n{0}'.format('#'*80))
    log_f = '{0:<20s} {1}'
    logging.info(log_f.format(
        'Run Time Stamp:', dt.datetime.now().isoformat(' ')))
    logging.info(log_f.format('Current Directory:', args.workspace))
    logging.info(log_f.format('Script:', os.path.basename(sys.argv[0])))

    main(project_ws=args.workspace, crop_str=args.crops)
