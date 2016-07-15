#!/usr/bin/env python
import argparse
import datetime
import logging
import multiprocessing as mp
import os
import sys
from time import clock

import numpy as np
import pandas as pd

import crop_et_data
import crop_cycle
import et_cell
import util


def main(ini_path, log_level=logging.WARNING,
         debug_flag=False, cal_flag=False, vb_flag=False, mp_procs=1):
    """ Main function for running the Crop ET model

    Args:
        ini_path (str): file path of the project INI file
        log_level (logging.lvl):
        debug_flag (bool): If True, write debug level comments to debug.txt
        vb_flag (bool): If True, mimic calculations in VB version of code
        mp_procs (int): number of cores to use for multiprocessing

    Returns:
        None
    """
    clock_start = clock()
    # Start console logging immediately
    logger = util.console_logger(log_level=log_level)

    logging.warning('\nPython ET-Demands')
    if vb_flag:
        logging.warning('  Mimicking VB calculations')
    if debug_flag and mp_procs > 1:
        logging.warning('  Debug mode, disabling multiprocessing')
        mp_procs = 1
    if mp_procs > 1:
        logging.warning('  Multiprocessing mode, {0} cores'.format(mp_procs))
    if cal_flag:
        logging.warning('  Displaying additional calibration information')

    # All general data will be handled in this class
    data = crop_et_data.CropETData()

    # Read in the INI file
    # DEADBEEF - This could be called directly from the CropETData class
    data.read_ini(ini_path)

    # Start file logging once the INI file has been read in
    if debug_flag:
        logger = util.file_logger(
            logger, log_level=logging.DEBUG, output_ws=data.project_ws)

    # Growing season summary CSV files must be written
    if cal_flag:
        logging.warning('  Setting growing_season_stats_flag = True')
        data.gs_output_flag = True

    # Read in common crop specific parameters and coefficients
    # File paths are read in from INI
    data.set_crop_params()
    data.set_crop_coeffs()
    if data.co2_flag:
        data.set_crop_co2()

    # Read in cell properties, crops and cuttings
    # Could  these be called directly from the CropETData class
    cells = et_cell.ETCellData()
    cells.set_cell_properties(data.cell_properties_path)
    cells.set_cell_crops(data.cell_crops_path)
    cells.set_cell_cuttings(data.cell_cuttings_path)

    # Allow user to run only annual/perennial crops
    if data.annual_skip_flag:
        cells.filter_annual_crops(data.crop_params)
    if data.perennial_skip_flag:
        cells.filter_perennial_crops(data.crop_params)

    # Filter cells if all crops are "off"
    # This could also be done in set_cell_crops() (when they are read in)
    if data.crop_skip_list or data.crop_test_list:
        cells.filter_crops(data.crop_skip_list, data.crop_test_list)
    if data.cell_skip_list or data.cell_test_list:
        cells.filter_cells(data.cell_skip_list, data.cell_test_list)

    # First apply the static crop parameters to all cells
    # Could the "cell" just inherit the "data" values instead
    cells.set_static_crop_params(data.crop_params)
    cells.set_static_crop_coeffs(data.crop_coeffs)

    # Read in spatially varying crop parameters
    if data.spatial_cal_flag:
        cells.set_spatial_crop_params(data.spatial_cal_ws)

    # Multiprocessing logic
    # If cell count is low, process crops in parallel
    # If cell count is high, process cells in parallel (crops in serial)
    cell_mp_list, cell_mp_flag, crop_mp_flag = [], False, False
    if mp_procs > 1:
        logging.warning("\nSetting multiprocessing logic")
        cell_count = len(cells.et_cells_dict.keys())
        crop_count = len(cells.crop_num_list)
        logging.warning('  Cell count: {}'.format(cell_count))
        logging.warning('  Crop count: {}'.format(crop_count))
        # The 0.5 multiplier is to prefer multiprocessing by cell
        # because of 1 CPU time spent loading/processing weather data
        # when multiprocessing by crop
        if (0.5 * cell_count) > crop_count:
            logging.warning("  Multiprocessing by cell")
            cell_mp_flag = True
        else:
            logging.warning("  Multiprocessing by crop")
            crop_mp_flag = True

    # Process each cell/station
    logging.warning("")
    for cell_id, cell in sorted(cells.et_cells_dict.items()):
        if cell_mp_flag:
            # Multiprocessing by cell
            cell_mp_list.append([data, cell, vb_flag, mp_procs])
        elif crop_mp_flag:
            # Multiprocessing by crop
            logging.warning('CellID: {}'.format(cell_id))
            cell.initialize_weather(data)
            crop_cycle.crop_cycle_mp(data, cell, vb_flag=vb_flag,
                                     mp_procs=mp_procs)
        else:
            logging.warning('CellID: {}'.format(cell_id))
            cell.initialize_weather(data)
            crop_cycle.crop_cycle(data, cell, debug_flag=debug_flag,
                                  vb_flag=vb_flag)

    # Process all cells
    results = []
    if cell_mp_list:
        pool = mp.Pool(mp_procs)
        results = pool.imap(cell_mp, cell_mp_list, chunksize=1)
        pool.close()
        pool.join()
        del pool, results

    logging.info('\n{} seconds'.format(clock()-clock_start))


    # Print summary stats to the screen
    # This should be moved to a separate function or module
    #   or maybe into a separate tool
    if cal_flag and data.gs_output_flag:
        logging.warning('\nMean Annual growing season start/end dates')

        for cell_id, cell in sorted(cells.et_cells_dict.items()):
            logging.warning('CellID: {}'.format(cell_id))
            for crop_num, crop in sorted(cell.crop_params.items()):
                if cell.crop_flags[crop_num] == 0:
                    continue
                # logging.warning('Crop %2d %s' % (crop_num, crop))

                gs_output_path = os.path.join(
                    data.gs_output_ws, '{0}_gs_crop_{1:02d}.csv'.format(
                        cell_id, int(crop.class_number)))

                gs_df = pd.read_table(gs_output_path, header=0, comment='#', sep=',')

                gs_start_doy = int(round(gs_df['Start_DOY'].mean()))
                gs_end_doy = int(round(gs_df['End_DOY'].mean()))
                gs_start_dt = datetime.datetime.strptime(
                    '2001_{:03d}'.format(gs_start_doy), '%Y_%j')
                gs_end_dt = datetime.datetime.strptime(
                    '2001_{:03d}'.format(gs_end_doy), '%Y_%j')
                logging.warning(
                    ('  Crop {crop:2d}:' +
                     '  {start_dt.month}/{start_dt.day} - {end_dt.month}/{end_dt.day}').format(
                        crop=crop_num, start_dt=gs_start_dt, end_dt=gs_end_dt))


def cell_mp(tup):
    """Pool multiprocessing friendly function

    mp.Pool needs all inputs are packed into a single tuple
    Tuple is unpacked and and single processing version of function is called

    Args:
        data ():
        et_cell ():
        vb_flag (bool): If True, mimic calculations in VB version of code
    """
    return cell_sp(*tup)

def cell_sp(data, cell, vb_flag, mp_procs=1):
    """Compute crop cycle for each cell"""
    if mp_procs == 1:
        logging.warning('CellID: {}'.format(cell.cell_id))
    else:
        print('CellID: {}'.format(cell.cell_id))
    cell.initialize_weather(data)
    # Force debug_flag false when multiprocessing
    crop_cycle.crop_cycle(data, cell, debug_flag=False, vb_flag=vb_flag,
                          mp_procs=mp_procs)


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


def parse_args():
    """"""
    parser = argparse.ArgumentParser(
        description='Crop ET-Demands',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        '-i', '--ini', required=True, metavar='PATH',
        type=lambda x: is_valid_file(parser, x), help='Input file')
    parser.add_argument(
        '-vb', '--vb', action="store_true", default=False,
        help="Mimic calculations in VB version of code")
    parser.add_argument(
        '-d', '--debug', action="store_true", default=False,
        help="Save debug level comments to debug.txt")
    parser.add_argument(
        '-v', '--verbose', action="store_const",
        dest='log_level', const=logging.INFO, default=logging.WARNING,
        help="Print info level comments")
    parser.add_argument(
        '-mp', '--multiprocessing', default=1, type=int,
        metavar='N', nargs='?', const=mp.cpu_count(),
        help='Number of processers to use')
    parser.add_argument(
        '--cal', action='store_true', default=False,
        help="Display mean annual start/end dates to screen")
    args = parser.parse_args()

    # Convert INI path to an absolute path if necessary
    if args.ini and os.path.isfile(os.path.abspath(args.ini)):
        args.ini = os.path.abspath(args.ini)
    return args


if __name__ == '__main__':
    args = parse_args()

    main(ini_path=args.ini, log_level=args.log_level, debug_flag=args.debug,
         cal_flag=args.cal, vb_flag=args.vb, mp_procs=args.multiprocessing)
