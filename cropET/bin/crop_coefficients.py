#!/usr/bin/env python

import numpy as np


class CropCoeff:
    def __init__(self):
        """ """
        self.name = None
        self.gdd_type_name = ''

    # CGM 9/1/2015 - Not sure the point of this implementation of the init function
    # def __init__(self, fn=''):
    #     """ """
    #     self.fn = fn
    #     if fn:
    #         self.read(fn)

    def __str__(self):
        """ """
        return '<%s, type %s>' % (self.name, self.curve_type)

    def lookup(self, val=None):
        """ Lookup value from table
        """
        nval = 0.0
        for i in range(self.lentry):
            if val < self.data[i]:
                nval = self.data[i]
        return nval

    def max_value(self, val=None):
        """ Maximum value from table

        Find maximum Kcb in array for this crop (used later in height calc)
        Kcbmid is the maximum Kcb found in the Kcb table read into program
        Following code was repaired to properly parse crop curve arrays on 7/31/2012.  dlk

        """
        # from Sub CropLoad(), line ~1032
        # For kCount = 0 To maxLinesInCropCurveTable  # <----- no. entries for crop coefficient curve
        #     If Kcbmid < cropco_val(cCurveNo, kCount) Then Kcbmid = cropco_val(cCurveNo, kCount)
        # Next kCount
        for i in range(self.lentry):
            if val < self.data[i]:
                val = self.data[i]
        return val

    def init_from_column(self, percents, dc):
        """ Parse the column of data

        Args:
            pc - string of the percent column
            dc - string of the data column
        """

        # Info
        t2d = {'1': '1=NCGDD',
               '2': '2=%PL-EC',
               '3': '3=%PL-EC+daysafter',
               '4': '4=%PL-Term'}
        self.curve_no = dc[2]
        self.curve_type_no = dc[3]
        self.curve_type = t2d[dc[3]]
        self.name = dc[4]

        # Data table
        self.percents = percents.astype(float)
        v = dc[6:41]
        #v = np.where(v == '', 'nan', v)
        v = np.where(v == '', '0', v)
        self.data = v.astype(float)

        # # CGM 9/1/2015 - These aren't used anywhere else in the code
        # t2n = { '1':'simple', '2':'corn'}
        # self.gdd_base_c = dc[41]
        # self.gdd_type = dc[42]
        # if dc[42] in t2n:
        #     .gdd_type_name = t2n[dc[42]]

        # # CGM 9/1/2015 - These aren't used anywhere else in the code
        # self.cgdd_planting_to_fc = dc[43]
        # self.cgdd_planting_to_terminate = dc[44]
        # self.cgdd_planting_to_terminate_alt = dc[45]
        # self.comment1 = dc[46]
        # self.comment2 = dc[47]

        # From CropCycle() in vb code
        i = np.where(self.data > 0.0)
        self.lentry = len(np.where(self.data > 0.0)[0]) - 1

        #self.curve_no = curve_no
        #self.curve_type = curve_type
        #self.percents = percents
        #self.vals = vals

    # def read(self):
    #     """ Read from crop coefficient file
    #         Eventually each crop stored in own text file...maybe.
    #     """
    #     print 'not implemented'

    # def write(self, fn=''):
    #     """ Write individual crop coefficient file
    #     """
    #     print 'not implemented'


def read_crop_coefs(fn):
    """ Load the crop coefficients

    Crop coefficients are constant for all cells

    """

    a = np.loadtxt(fn, delimiter="\t", dtype='str')
    curve_type = a[3, 2:]

    coeffs_dict = {}
    for i, num in enumerate(curve_type):
        if curve_type[i] == '3':
            percents = a[6:41, 1]
        else:
            percents = a[6:37, 0]

        data_col = a[:41, 2+i]
        if not data_col[2]:
            continue
        coeff_obj = CropCoeff()
        coeff_obj.init_from_column(percents, data_col)

        coeffs_dict[int(coeff_obj.curve_no)] = coeff_obj
    return coeffs_dict

if __name__ == '__main__':
    pass
