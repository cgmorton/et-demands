#!/usr/bin/env python

from pprint import pprint
import sys

import numpy as np

## 
CGDDWinterDoy = 274
CGDDMainDoy = 1

class CropParameters:
    name = ''
    crop_class_num = 0   
    is_annual = False
    irrigation_flag = 0
    days_after_planting_irrigation = 0
    crop_fw = 0
    winter_surface_cover_class = 0
    crop_kc_max = 0.
    mad_initial = 0
    mad_midseason = 0
    initial_rooting_depth = 0.
    maximum_rooting_depth = 0.
    end_of_root_growth_fraction_time = 0.
    starting_crop_height = 0.
    maximum_crop_height = 0.
    crop_curve_number = 0
    crop_curve_name = ''
    crop_curve_type = 0
    flag_for_means_to_estimate_pl_or_gu = 0
    t30_for_pl_or_gu_or_cumgdd = 0.
    date_of_pl_or_gu = 0
    tbase = 0.0
    cumgdd_for_efc = 0
    cumgdd_for_termination = 0
    time_for_efc = 0
    time_for_harvest = 0
    killing_frost_temperature = 0
    invoke_Stress = 0
    curve_number_coarse = 0
    curve_number_medium = 0
    curve_number_fine = 0
    season = None

    def __init__(self, v):
        """ """
        self.name = v[0]
        self.crop_class_num = abs(int(v[1]))
        if int(v[1]) < 0:
            self.isAnnual = True
        self.irrigation_flag = int(v[2])
        self.days_after_planting_irrigation = int(v[3])
        self.crop_fw = int(v[4])
        self.winter_surface_cover_class = int(v[5])
        self.crop_kc_Max = float(v[6])
        self.mad_initial = int(v[7])
        self.mad_midseason = int(v[8])
        self.initial_rooting_depth = float(v[9])
        self.maximum_rooting_depth = float(v[10])
        self.end_of_root_growth_fraction_time = float(v[11])
        self.starting_fop_height = float(v[12])
        self.maximum_frop_height = float(v[13])
        ## [140822] changed for RioGrande
        self.crop_curve_number = int(v[14])
        self.crop_curve_name = v[15]
        self.crop_curve_type = int(v[16])
        self.flag_for_means_to_estimate_pl_or_gu = int(v[17])
        self.t30_for_pl_or_gu_or_cumgdd = float(v[18])
        self.date_of_pl_or_gu = float(v[19])
        self.tbase = float(v[20])
        self.cumgdd_for_efc = int(v[21])
        self.cumgdd_for_termination = int(v[22])
        self.time_for_efc = int(v[24])
        self.time_for_harvest = int(v[25])
        self.killing_frost_temperature = float(v[26])
        self.invoke_stress = int(v[27])
        self.curve_number_coarse_soil = int(v[29])
        self.curve_number_medium_soil = int(v[30])
        self.curve_number_fine_soil = int(v[31])

        # winter crop
        if self.crop_curve_name == 'Winter Wheat':
            self.crop_gdd_trigger_doy = CGDDWinterDoy
            self.season = 'winter'
        else:
            self.crop_gdd_trigger_doy = CGDDMainDoy
            self.season = 'non-winter'


    def __str__(self):
        """ """
        # add any info to help in debugging, etc
        s = '<%s>' % (self.name)
        return s

    def set_winter_soil(self, crops=[]):
        """ """
        #' setup curve number for antecedent II condition for winter covers
        #wscc = self.winter_surface_cover_class
        #self.Curve_Number_coarse_soil_winter = int(v[29])
        #self.Curve_Number_medium_soil_winter = int(v[30])
        #self.Curve_Number_fine_soil_winter   = int(v[31])


def read_crop_parameters(fn):
    """
    read_crop_parameters() Then
    ' #varies by geographic Area, ie, Klamath, 

    DATA/EX/ExampleData/Params/crop_parameters.csv    # problems with ',' in some fields
    DATA/EX/ExampleData/Params/Crop_Parameters.txt    # 
     Parameter     Explanation  Crop1    Crop2 ...
     'text name'   'text'      int|str

    Crops are indexed

    """
    #fn = 'static/Crop_Parameters.txt'
    a = np.loadtxt(fn, delimiter="\t", dtype='str', skiprows=3)
    a = a[0:32,:]
    # replace empty fields
    b = np.where(a == '', '0', a)

    crops = []
    for i,num in enumerate(b[1,2:]):
        #print i,num
        if num == '0':
            break
        #print type(b[:,i+2])
        #print b[:,i+2]
        crop_obj = CropParameters(b[:,i+2])
        #pprint(crop_obj.__dict__)
        crops.append(crop_obj)
        #sys.exit()

    #' setup curve number for antecedent II condition for winter covers
    #for i,crop in enumerate(crops, start=1):
    #    print i,crop
    #    crop.set_winter_soil(crops)
    #    sys.exit()
    return crops


if __name__ == '__main__':
    static_ws = os.path.join(os.getcwd(), 'static')
    fn = os.path.join(static_ws, 'Crop_Parameters.txt')
    crops = read_crop_parameters(fn)
    print 'Crops:',len(crops)
    pprint(crops[0])
    c = crops[0]
    pprint(vars(c))
    print c, 
