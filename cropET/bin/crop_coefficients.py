#!/usr/bin/env python

from pprint import pprint

import numpy as np

class CropCoeff:
    name = None
    gdd_type_name = ''

    def __init__(self, fn=''):
        """ """
        self.fn = fn
        if fn:
            self.read(fn)

    def __str__(self):
        """ """
        # add any info to help in debugging, etc
        s = '<%s, type %s>' % (self.name, self.curve_type)
        return s

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
        """
        #' Find maximum Kcb in array for this crop (used later in height calc)$
        #' Kcbmid is the maximum Kcb found in the Kcb table read into program$
        #' Following code was repaired to properly parse crop curve arrays on 7/31/2012.  dlk$

        ## from Sub CropLoad(), line ~1032 
        #For kCount = 0 To maxLinesInCropCurveTable #' <----- no. entries for crop coefficient curve
        #    If Kcbmid < cropco_val(cCurveNo, kCount) Then Kcbmid = cropco_val(cCurveNo, kCount)
        #Next kCount
        for i in range(self.lentry):
            if val < self.data[i]:
                val = self.data[i]
        return val

    def init_from_column(self, percents, dc):
        """ Parse the column of data
            pc == percent column
            dc == data column
        """

        #  info
        t2d = { '1':'1=NCGDD', '2':'2=%PL-EC', '3':'3=%PL-EC+daysafter', '4':'4=%PL-Term' }
        self.curve_no = dc[2]
        self.curve_type_no = dc[3]
        self.curve_type = t2d[dc[3]]
        self.name = dc[4]

        t2n = { '1':'simple', '2':'corn'}
        self.gdd_base_c = dc[41]
        self.gdd_type = dc[42]
        if dc[42] in t2n:
            self.gdd_type_name = t2n[dc[42]]
        self.cgdd_planting_to_fc = dc[43]
        self.cgdd_planting_to_terminate = dc[44]
        self.cgdd_planting_to_terminate_alt = dc[45]

        self.comment1 = dc[46]
        self.comment2 = dc[47]

        #  data table
        self.percents = percents.astype(float)
        v = dc[6:41]
        #v = np.where(v == '', 'nan', v)
        v = np.where(v == '', '0', v)
        self.data = v.astype(float)

        # from CropCycle() in vb code, 
        i = np.where(self.data > 0.0)
        self.lentry = len(np.where(self.data > 0.0)[0]) - 1

        #print len(v[0,2:])

        #self.curve_no = curve_no
        #self.curve_type = curve_type
        #self.percents = percents
        #self.vals = vals

    def read(self):
        """ Read from crop coefficient file 
            Eventually each crop stored in own text file...maybe.
        """
        print 'not implemented'

    def write(self, fn=''):
        """ Write individual crop coefficient file 
        """
        print 'not implemented'


def read_crop_coefs(fn):
    """ Load the crop coefficients 

    # these are same for all areas
    DATA/EX/ExampleData/Params/GrassCropCoefficients.csv
    # a table where lookups may be done 
    Percent.. Percent2.. crop1 crop2 crop3
    0   0   0.18    0.14    0.14
    10  10  0.18    0.14    0.17 
    20  20  0.24    0.18    0.18

    # crops vary in number of records, so None for sparse areas
    # used vars
    cropco_num           # not used
    cropco_type          # not used
    cropco_name          # not used
    cropco_scale1        # not used
    cropco_scale2        # not used
    cropco_val           # 2d table
    cropco_GDD_base      # 
    cropco_GDD_type      # not used?
    cropco_GDD_PLtoEC    # not used?
    cropco_GDD_PLtoTerm1 # not used?
    cropco_GDD_PLtoTerm2 # not used?

    """
    '''
    a = np.loadtxt(fn, delimiter="\t", dtype='str', skiprows=6)
    a = a[:35,2:]
    a = np.where(a == '', 'nan', a)
    a = a.astype(float)
    '''

    a = np.loadtxt(fn, delimiter="\t", dtype='str')
    curve_type = a[2,2:]
    #pprint(curve_type)

    #coeffs = []
    coeffs = {}
    for i,num in enumerate(curve_type):
        #print i,num

        if curve_type[i] == '3':
            percents = a[6:36,0]
        else:
            percents = a[6:41,1]
        data_col = a[:,2+i]
        if not data_col[2]:
            continue
        #print percents
        #print data_col

        coeff_obj = CropCoeff()
        coeff_obj.init_from_column(percents, data_col)
        #pprint(coeff_obj.__dict__)
        #print coeff_obj

        #coeffs.append(coeff_obj)
        coeffs[int(coeff_obj.curve_no)] = coeff_obj
    return coeffs


if __name__ == '__main__':
    # import from text table of all coefficients
    static_ws = os.path.join(os.getcwd(), 'static')
    fn = os.path.join(static_ws, 'CropCoefs.txt')
    coeff = read_crop_coefs(fn)
    c = coeff[0]
    pprint(vars(c))
    print c

