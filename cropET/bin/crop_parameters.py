#!/usr/bin/env python

import sys
from pprint import pprint
import numpy as np

## 
CGDDWinterDoy = 274
CGDDMainDoy = 1


class CropParameters:

    name = ''
    cropclass_num = 0   
    isAnnual = False
    Irrigation_Flag = 0
    Days_after_planting_irrigation = 0
    crop_fw = 0
    winter_surface_cover_class = 0
    crop_Kc_Max = 0.
    MAD_initial = 0
    MAD_midseason = 0
    Initial_rooting_depth = 0.
    Maximum_rooting_depth = 0.
    End_of_Root_growth_fraction_time = 0.
    Starting_Crop_height = 0.
    Maximum_Crop_height = 0.
    Crop_curve_number = 0
    Crop_curve_name = ''
    Crop_curve_type = 0
    Flag_for_means_to_estimate_pl_or_gu = 0
    T30_for_pl_or_gu_or_cumGDD = 0.
    Date_of_pl_or_gu = 0
    Tbase = 0.0
    cumGDD_For_EFC = 0
    cumGDD_For_Termination = 0
    time_for_EFC = 0
    time_for_harvest = 0
    Killing_frost_temperature = 0
    Invoke_Stress = 0
    Curve_Number_coarse = 0
    Curve_Number_medium = 0
    Curve_Number_fine = 0
    season = None

    def __init__(self, v):
        """ """
        self.name = v[0]
        self.cropclass_num = abs(int(v[1]))
        if int(v[1]) < 0:
            self.isAnnual = True
        self.Irrigation_Flag = int(v[2])
        self.Days_after_planting_irrigation = int(v[3])
        self.crop_fw = int(v[4])
        self.winter_surface_cover_class = int(v[5])
        self.crop_Kc_Max = float(v[6])
        self.MAD_initial = int(v[7])
        self.MAD_midseason = int(v[8])
        self.Initial_rooting_depth = float(v[9])
        self.Maximum_rooting_depth = float(v[10])
        self.End_of_Root_growth_fraction_time = float(v[11])
        self.Starting_Crop_height = float(v[12])
        self.Maximum_Crop_height = float(v[13])
        ## [140822] changed for RioGrande
        self.Crop_curve_number = int(v[14])
        self.Crop_curve_name = v[15]
        self.Crop_curve_type = int(v[16])
        self.Flag_for_means_to_estimate_pl_or_gu = int(v[17])
        self.T30_for_pl_or_gu_or_cumGDD = float(v[18])
        self.Date_of_pl_or_gu = float(v[19])
        self.Tbase = float(v[20])
        self.cumGDD_For_EFC = int(v[21])
        self.cumGDD_For_Termination = int(v[22])
        self.time_for_EFC = int(v[24])
        self.time_for_harvest = int(v[25])
        self.Killing_frost_temperature = float(v[26])
        self.Invoke_Stress = int(v[27])
        self.Curve_Number_coarse_soil = int(v[29])
        self.Curve_Number_medium_soil = int(v[30])
        self.Curve_Number_fine_soil = int(v[31])

        # winter crop
        if self.Crop_curve_name == 'Winter Wheat':
            self.cropGDDTriggerDoy = CGDDWinterDoy
            self.season = 'winter'
        else:
            self.cropGDDTriggerDoy = CGDDMainDoy
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


def ReadCropParameters(fn):
    """
    ReadCropParameters() Then
    ' #varies by geographic Area, ie, Klamath, 

    DATA/EX/ExampleData/Params/crop_parameters.csv    # problems with ',' in some fields
    DATA/EX/ExampleData/Params/Crop_Parameters.txt    # 
     Parameter     Explanation  Crop1    Crop2 ...
     'text name'   'text'      int|str

    Crops are indexed

    """
    #fn = 'DATA/TEST/params/Crop_Parameters.txt'
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

    fn = 'DATA/TEST/params/Crop_Parameters.txt'
    fn = 'DATA/EX/txt_KlamathMetAndDepletionNodes/CropParams.txt'

    crops = ReadCropParameters(fn)
    print 'Crops:',len(crops)
    pprint(crops[0])
    c = crops[0]
    pprint(vars(c))
    print c, 
