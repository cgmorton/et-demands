#!/usr/bin/env python

import argparse
import multiprocessing as mp
import os
import subprocess
import sys


def main(ini_path, verbose_flag=False, debug_flag=False, vb_flag=False,
         mp_procs=1):
    """Wrapper for running ET-Demands on a basin

    This serves the same purpose as the runBasinLinux.sh script in the
    original vb to python conversion data package.

    Args:
        ini_path (str): file path of the project INI file
        verbose_flag (bool): If True, print info level comments
        debug_flag (bool): If True, write debug level comments to debug.txt
        vb_flag (bool): If True, mimic calculations in VB version of code
        mp_procs (int): number of cores to use

    Returns:
        None
    """

    # Folder containing the ET Demands python code
    bin_ws = r'..\et-demands\cropET\bin'
    # bin_ws = os.path.join(os.path.realpath('..'), r'cropET\bin')

    # Main ET Demands python function
    script_path = os.path.join(bin_ws, 'mod_crop_et.py')

    # Check the input folder/path
    if not os.path.isfile(ini_path):
        print('The ET-Demands input file does not exist\n  %s' % (ini_path))
        sys.exit()
    elif not os.path.isdir(bin_ws):
        print('The code workspace does not exist\n  %s' % (bin_ws))
        sys.exit()
    elif not os.path.isfile(script_path):
        print('The ET-Demands main script does not exist\n  %s' % (script_path))
        sys.exit()

    # Run ET Demands Model
    args_list = ['python', script_path, '-i', ini_path]
    if debug_flag:
        args_list.append('--debug')
    if verbose_flag:
        args_list.append('--verbose')
    if vb_flag:
        args_list.append('--vb')
    if mp_procs > 1:
        args_list.extend(['-mp', str(mp_procs)])
    subprocess.call(args_list)


def parse_args():
    parser = argparse.ArgumentParser(
        description='Crop ET-Demands',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        '-i', '--ini', metavar='PATH',
        type=lambda x: is_valid_file(parser, x), help='Input file')
    parser.add_argument(
        '-vb', '--vb', action='store_true', default=False,
        help='Mimic calculations in VB version of code')
    parser.add_argument(
        '-d', '--debug', action='store_true', default=False,
        help='Save debug level comments to debug.txt')
    parser.add_argument(
        '-v', '--verbose', action='store_true', default=False,
        help='Print info level comments')
    # parser.add_argument(
    #     '-q', '--quiet', action="store_true", default=False,
    #     help="Print info level comments")
    parser.add_argument(
        '-mp', '--multiprocessing', default=1, type=int,
        metavar='N', nargs='?', const=mp.cpu_count(),
        help='Number of processers to use')
    args = parser.parse_args()

    # Convert INI path to an absolute path if necessary
    if args.ini and os.path.isfile(os.path.abspath(args.ini)):
        args.ini = os.path.abspath(args.ini)
    return args


def get_ini_path(workspace):
    import Tkinter, tkFileDialog
    root = Tkinter.Tk()
    ini_path = tkFileDialog.askopenfilename(
        initialdir=workspace, parent=root, filetypes=[('INI files', '.ini')],
        title='Select the target INI file')
    root.destroy()
    return ini_path


def is_valid_file(parser, arg):
    if not os.path.isfile(arg):
        parser.error('The file {} does not exist!'.format(arg))
    else:
        return arg


def is_valid_directory(parser, arg):
    if not os.path.isdir(arg):
        parser.error('The directory {} does not exist!'.format(arg))
    else:
        return arg


if __name__ == '__main__':
    args = parse_args()
    if args.ini:
        ini_path = args.ini
    else:
        ini_path = get_ini_path(os.getcwd())

    main(ini_path, verbose_flag=args.verbose, debug_flag=args.debug,
         vb_flag=args.vb, mp_procs=args.multiprocessing)
