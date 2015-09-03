#--------------------------------
# Name:         download_cdl.py
# Purpose:      Download national CDL zips
# Author:       Charles Morton
# Created       2015-09-03
# Python:       2.7
#--------------------------------

import argparse
import datetime as dt
import logging
import os
import subprocess
import sys
import urllib
import zipfile

import util

################################################################################

def main(cdl_ws, cdl_year='', overwrite_flag=False):
    """Download national CDL zips

    Args:
        cdl_ws (str): Folder/workspace path of the GIS data for the project
        cdl_year (str): Cropland Data Layer year comma separated list and/or range
        overwrite_flag (bool): If True, overwrite existing files
        
    Returns:
        None
    """
    logging.info('\nDownload and extract CONUS CDL rasters')
    site_url = 'ftp://ftp.nass.usda.gov/download/res' 
    
    cdl_format = '{0}_30m_cdls.img'
   
    for cdl_year in list(util.parse_int_set(cdl_year)):
        logging.info('{0}'.format(cdl_year))
        zip_name = cdl_format.format(cdl_year)
        zip_url = site_url+'/'+zip_name
        zip_path = os.path.join(cdl_ws, zip_name)
        
        cdl_path = os.path.join(cdl_ws, zip_name.replace('.zip', '.img'))
        if not os.path.isdir(cdl_ws):
            os.makedirs(cdl_ws)
        
        if os.path.isfile(zip_path) and overwrite_flag:
             os.remove(zip_path)
        if not os.path.isfile(zip_path):
            logging.info('  Download CDL files')
            logging.debug('    {0}'.format(zip_url))
            logging.debug('    {0}'.format(zip_path))
            try:
                urllib.urlretrieve(zip_url, zip_path)
            except IOError:
                logging.error('    IOError, skipping')
        
        if os.path.isfile(cdl_path) and overwrite_flag:
             util.remove_file(cdl_path)
        if os.path.isfile(zip_path) and not os.path.isfile(cdl_path):
            logging.info('  Extracting CDL files')
            with zipfile.ZipFile(zip_path) as zf:
                zf.extractall(cdl_ws) 

################################################################################
   
def arg_parse():
    parser = argparse.ArgumentParser(
        description='Download CDL raster',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        '--cdl', metavar='FOLDER', required=True,
        type=lambda x: util.is_valid_directory(parser, x), 
        help='Common CDL workspace/folder')
    parser.add_argument(
        '-y', '--years', metavar='YEAR', required=True,
        help='Years, comma separate list and/or range')
    parser.add_argument(
        '-o', '--overwrite', default=None, action="store_true", 
        help='Force overwrite of existing files')
    parser.add_argument(
        '--debug', default=logging.INFO, const=logging.DEBUG,
        help='Debug level logging', action="store_const", dest="loglevel")
    args = parser.parse_args()

    ## Convert CDL folder to an absolute path
    if args.cdl and os.path.isdir(os.path.abspath(args.cdl)):
        args.cdl = os.path.abspath(args.cdl)
    return args

################################################################################

if __name__ == '__main__':
    args = arg_parse()

    logging.basicConfig(level=args.loglevel, format='%(message)s')
    logging.info('\n{0}'.format('#'*80))
    logging.info('{0:<20s} {1}'.format('Run Time Stamp:', dt.datetime.now().isoformat(' ')))
    logging.info('{0:<20s} {1}'.format('Script:', os.path.basename(sys.argv[0])))

    main(cdl_ws=args.cdl, cdl_year=args.years, overwrite_flag=args.overwrite)