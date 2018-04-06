#--------------------------------
# Name:         util.py
# Purpose:      Utilitiy functions for ET-Demands prep scripts
# Author:       Charles Morton
# Created       2016-09-14
# Python:       2.7
#--------------------------------

import ConfigParser
import glob
from itertools import groupby
import logging
import os
import sys


def remove_file(file_path):
    """Remove a feature/raster and all of its anciallary files"""
    file_ws = os.path.dirname(file_path)
    for file_name in glob.glob(os.path.splitext(file_path)[0] + ".*"):
        logging.debug('  Remove: {}'.format(os.path.join(file_ws, file_name)))
        os.remove(os.path.join(file_ws, file_name))


def is_valid_file(parser, arg):
    """"""
    if os.path.isfile(arg):
        return arg
    elif os.path.isfile(os.path.abspath(arg)):
        return os.path.abspath(arg)
    else:
        parser.error('\nThe file {} does not exist!'.format(arg))


def is_valid_directory(parser, arg):
    """"""
    if os.path.isdir(arg):
        return arg
    elif os.path.isdir(os.path.abspath(arg)):
        return os.path.abspath(arg)
    else:
        parser.error('\nThe directory {} does not exist!'.format(arg))


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
                    last = token[len(token) - 1]
                    for x in range(first, last + 1):
                        selection.add(x)
            except:
                # not an int and not a range...
                invalid.add(i)
    # Report invalid tokens before returning valid selection
    # print "Invalid set: " + str(invalid)
    return selection


def read_ini(ini_path, section='CROP_ET'):
    """Open the INI file and check for obvious errors"""
    logging.info('  INI: {}'.format(os.path.basename(ini_path)))
    config = ConfigParser.ConfigParser()
    try:
        ini = config.readfp(open(ini_path))
    except:
        logging.error('\nERROR: Config file could not be read, ' +
                      'is not an input file, or does not exist\n')
        sys.exit()
    if section not in config.sections():
        logging.error(('\nERROR: The input file must have ' +
                       'a section: [{}]\n').format(section))
        sys.exit()
    return config


def ranges(i):
    """"""
    for a, b in groupby(enumerate(i), lambda (x, y): y - x):
        b = list(b)
        if b[0][1] == b[-1][1]:
            yield str(b[0][1])
        else:
            yield '{0}-{1}'.format(b[0][1], b[-1][1])
        # yield b[0][1], b[-1][1]
