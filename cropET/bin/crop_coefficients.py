#!/usr/bin/env python
import numpy as np


class CropCoeff:
    """Crop coefficient container

    Attributes:
        curve_no (): Crop curve number (1-60)
        curve_type_no (): Crop curve type (1-4)
        curve_type (): Crop curve type number
            (NCGDD, %PL-EC, %PL-EC+daysafter, %PL-Term)
        name (str): Crop name
        percents (numpy array): crop coefficient percents
        data (numpy array): Crop coefficient curve values

    """

    def __init__(self):
        self.name = None
        self.gdd_type_name = ''

    def __str__(self):
        return '<%s, type %s>' % (self.name, self.curve_type)

    def init_from_column(self, dc):
        """Parse the column of data from the static crop coefficients file

        This functionality could be moved into the init function above

        Args:
            percents (numpy array): percents column from static file
            dc (numpy array): crop data column from static file
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
        # Percents values are not being used anywhere in the code
        # self.percents = percents.astype(float)
        values = dc[6:41]
        mask = values == ''
        values = np.where(mask, '0', values)
        self.data = values.astype(float)
        self.lentry = np.where(~mask)[0][-1]

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


def read_crop_coefs(fn):
    """Load the crop coefficients from the static file

    Assume crop coefficients are constant for all cells

    Args:
        fn (str): file path

    Returns:
        A dict mapping crop curve numbers to the crop coefficients
    """

    a = np.loadtxt(fn, delimiter="\t", dtype='str')
    curve_type = a[3, 2:]

    coeffs_dict = {}
    for i, num in enumerate(curve_type):
        # Percents values are not being used anywhere in the code
        # if curve_type[i] == '3':
        #     percents = a[6:41, 1]
        # else:
        #     percents = a[6:37, 0]

        data_col = a[:41, 2+i]
        if not data_col[2]:
            continue
        coeff_obj = CropCoeff()
        coeff_obj.init_from_column(data_col)
        # coeff_obj.init_from_column(percents, data_col)

        coeffs_dict[int(coeff_obj.curve_no)] = coeff_obj
    return coeffs_dict

if __name__ == '__main__':
    pass
