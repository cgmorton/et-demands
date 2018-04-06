#!/usr/bin/env python

import numpy as np
import xlrd

curve_descs = {'1': '1=NCGDD', '2': '2=%PL-EC', '3': '3=%PL-EC+daysafter', '4': '4=%PL-Term'}

class CropCoeff:
    """Crop coefficient container

    Attributes:
        curve_no (): Crop curve number (1-60)
        curve_type_no (): Crop curve type (1-4)
        curve_type (): Crop curve type number
            (NCGDD, %PL-EC, %PL-EC+daysafter, %PL-Term)
        name (str): Crop name
        data (numpy array): Crop coefficient curve values
    """

    def __init__(self):
        """ """
        self.name = None
        self.gdd_type_name = ''

    def __str__(self):
        """ """
        return '<%s, type %s>' % (self.name, self.curve_types)

    def init_from_column(self, curve_no, curve_type_no, curve_name,  data_col):
        """ Parse column of data

        Args:
            data_col - string of data column
        """
        # Info
        
        self.curve_no = curve_no.replace('.0', '')
        self.curve_type_no = curve_type_no.replace('.0', '')
        self.curve_types = curve_descs[self.curve_type_no]
        self.name = curve_name

        # Data table
        
        values = data_col[0:35]    # this version's data_col already has header lines removed
        values = np.where(values == '', '0', values)
        self.data = values.astype(float)
        self.lentry = len(np.where(self.data > 0.0)[0]) - 1

def read_crop_coefs_txt(data):
    """ Read crop coefficients from text file"""
    a = np.loadtxt(data.crop_coefs_path, delimiter = data.crop_coefs_delimiter, dtype = 'str')
    curve_numbers = a[2, 2:]
    curve_type_numbs = a[3, 2:]    # repaired from 'a[2, 2:]' - dlk - 05/07/2016
    curve_names = a[4, 2:]
    coeffs_dict = {}
    for i, num in enumerate(curve_type_numbs):
        data_col = a[6:, 2 + i]
        if not curve_numbers[0]: continue
        coeff_obj = CropCoeff()
        coeff_obj.init_from_column(curve_numbers[i], curve_type_numbs[i], curve_names[i], data_col)
        coeffs_dict[int(coeff_obj.curve_no)] = coeff_obj
    return coeffs_dict

def read_crop_coefs_xls_xlrd(data):
    """ Read crop coefficients from workbook using xlrd"""
    coeffs_dict = {}
    wb = xlrd.open_workbook(data.crop_coefs_path)
    ws = wb.sheet_by_name(data.crop_coefs_ws)
    curve_numbers= np.asarray(ws.row_values(data.crop_coefs_names_line - 2, 2), dtype = np.str)
    curve_type_numbs = np.asarray(ws.row_values(data.crop_coefs_names_line - 1, 2), dtype = np.str)
    curve_names= np.asarray(ws.row_values(data.crop_coefs_names_line, 2), dtype = np.str)
    for i, num in enumerate(curve_type_numbs):
        if curve_type_numbs[i] == '3':
            data_col = np.asarray(ws.col_values(i + 2, data.crop_coefs_header_lines, data.crop_coefs_header_lines + 31), dtype = np.str)
        else:
            data_col = np.asarray(ws.col_values(i + 2, data.crop_coefs_header_lines, data.crop_coefs_header_lines  + 35), dtype = np.str)
        coeff_obj = CropCoeff()
        coeff_obj.init_from_column(curve_numbers[i], curve_type_numbs[i], curve_names[i], data_col)
        coeffs_dict[int(coeff_obj.curve_no)] = coeff_obj
    return coeffs_dict

if __name__ == '__main__':
    pass
