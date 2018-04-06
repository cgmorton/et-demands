#!/usr/bin/env python

import argparse
import multiprocessing as mp
import os
import subprocess
import sys

def main(ini_path, verbose_flag = False, mnid_to_run = 'ALL', 
        debug_flag = False, mp_procs = 1):
    """Wrapper for running reference ET model

    Args:
        ini_path (str): file path of the project INI file
        verbose_flag (bool): If True, print info level comments
        mnid_to_run: Met node id to run in lieu of 'ALL'
        debug_flag (bool): If True, write debug level comments to debug.txt
        mp_procs (int): number of cores to use

    Returns:
        None
    """
    # print ini_path

    bin_ws = r'..\et-demands\refET\bin'

    # Reference et python function

    script_path = os.path.join(bin_ws, 'mod_ref_et.py')
    print script_path

    # Check input folder/path
    
    if not os.path.isfile(ini_path):
        print('Reference ET configuration file does not exist\n  %s' % (ini_path))
        sys.exit()
    elif not os.path.isdir(bin_ws):
        print('Code workspace does not exist\n  %s' % (bin_ws))
        sys.exit()
    elif not os.path.isfile(script_path):
        print('Referemce ET main script does not exist\n  %s' % (script_path))
        sys.exit()

    # Run Area ET Demands Model
    
    args_list = ['python', script_path, '-i', ini_path]
    args_list.append('-m')
    args_list.append(mnid_to_run)
    if debug_flag:
        args_list.append('-d')
    if verbose_flag:
        args_list.append('-v')
    if mp_procs > 1:
        args_list.extend(['-mp', str(mp_procs)])
    # print "command line is "
    print args_list
    subprocess.call(args_list)

def parse_args():  
    parser = argparse.ArgumentParser(
        description='Reference ET',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        '-i', '--ini', metavar='PATH',
        type = lambda x: is_valid_file(parser, x), help = 'Input file')
    parser.add_argument(
        '-d', '--debug', action = "store_true", default = False,
        help = "Save debug level comments to debug.txt")
    parser.add_argument(
        '-m', '--metid', metavar='mnid_to_run', default = 'ALL',
        help = "User specified met id to run")
    parser.add_argument(
        '-v', '--verbose', action = "store_true", default = False,
        help = "Print info level comments")
    parser.add_argument(
        '-mp', '--multiprocessing', default=1, type=int, 
        metavar = 'N', nargs = '?', const = mp.cpu_count(),
        help = 'Number of processers to use')
    args = parser.parse_args()

    # Convert INI path to an absolute path if necessary
    
    if args.ini and os.path.isfile(os.path.abspath(args.ini)):
        args.ini = os.path.abspath(args.ini)
    # print "\nargs are\n", args, "\n"
    return args

def get_ini_path(workspace):
    import Tkinter, tkFileDialog
    root = Tkinter.Tk()
    ini_path = tkFileDialog.askopenfilename(
        initialdir = workspace, parent=root, filetypes=[('INI files', '.ini')],
        title='Select INI file')
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
    main(ini_path, verbose_flag = args.verbose, mnid_to_run = args.metid, 
        debug_flag = args.debug, mp_procs = args.multiprocessing)
