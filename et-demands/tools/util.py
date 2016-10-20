#--------------------------------
# Name:         util.py
# Purpose:      Utilitiy functions for ET-Demands tools
# Author:       Charles Morton
# Created       2016-09-14
# Python:       2.7
#--------------------------------

import argparse
import ConfigParser
import datetime as dt
from itertools import groupby
import logging
import os
import Tkinter
import tkFileDialog
import sys


def get_path(workspace, title_str, file_types=[('INI files', '.ini')]):
    """"""
    root = Tkinter.Tk()
    path = tkFileDialog.askopenfilename(
        initialdir=workspace, parent=root, filetypes=file_types,
        title=title_str)
    root.destroy()
    return path


# def get_directory(workspace, title_str):
#     """"""
#      Tkinter, tkFileDialog
#      = Tkinter.Tk()
#      = tkFileDialog.askdirectory(
#        initialdir=workspace, parent=root, title=title_str, mustexist=True)
#     .destroy()
#      user_ws


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


def valid_date(input_date):
    """Check that a date string is ISO format (YYYY-MM-DD)

    This function is used to check the format of dates entered as command
      line arguments.
    DEADBEEF - It would probably make more sense to have this function
      parse the date using dateutil parser (http://labix.org/python-dateutil)
      and return the ISO format string

    Args:
        input_date: string
    Returns:
        string
    Raises:
        ArgParse ArgumentTypeError
    """
    try:
        input_dt = dt.datetime.strptime(input_date, "%Y-%m-%d")
        return input_date
    except ValueError:
        msg = "Not a valid date: '{0}'.".format(input_date)
        raise argparse.ArgumentTypeError(msg)


def parse_int_set(nputstr=""):
    """Return list of numbers given a string of ranges

    http://thoughtsbyclayg.blogspot.com/2008/10/parsing-list-of-numbers-in-python.html
    """
    selection = set()
    invalid = set()
    # tokens are comma separated values
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


def doy_2_date(test_year, test_doy):
    """"""
    return dt.datetime.strptime('{0:04d}_{1:03d}'.format(
        int(test_year), int(test_doy)), '%Y_%j').strftime('%Y-%m-%d')


def list_re_or(input_list):
    """"""
    return '(' + '|'.join(map(str, input_list)) + ')'
