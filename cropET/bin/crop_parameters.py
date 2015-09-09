#!/usr/bin/env python

import logging
import sys

import numpy as np

class CropParameters:
    name = ''

    def __init__(self, v, vb_flag=False):
        """
        
        Args:
            v ():
            vb_flag (bool): If True, 
        
        """
        ## If there is a comma in the string, it will also have quotes
        self.name = str(v[0]).replace('"', '').strip()
        self.class_number = abs(int(v[1]))
        ## DEADBEEF - Is this even used?
        if int(v[1]) < 0:
            self.is_annual = True
        else:
            self.is_annual = False
        self.irrigation_flag = int(v[2])
        self.days_after_planting_irrigation = int(v[3])
        self.crop_fw = int(v[4])
        self.winter_surface_cover_class = int(v[5])
        self.kc_max = float(v[6])
        self.mad_initial = int(v[7])
        self.mad_midseason = int(v[8])
        self.rooting_depth_initial = float(v[9])
        self.rooting_depth_max = float(v[10])
        self.end_of_root_growth_fraction_time = float(v[11])
        self.height_initial = float(v[12])
        self.height_max = float(v[13])
        ## [140822] changed for RioGrande
        self.curve_number = int(v[14])
        self.curve_name = str(v[15]).replace('"', '').strip()
        self.curve_type = int(v[16])
        self.flag_for_means_to_estimate_pl_or_gu = int(v[17])
        self.t30_for_pl_or_gu_or_cgdd = float(v[18])
        self.date_of_pl_or_gu = float(v[19])
        self.tbase = float(v[20])
        self.cgdd_for_efc = float(v[21])
        self.cgdd_for_termination = float(v[22])
        self.time_for_efc = float(v[24])
        self.time_for_harvest = float(v[25])
        self.killing_frost_temperature = float(v[26])
        self.invoke_stress = int(v[27])
        self.cn_coarse_soil = float(v[29])
        self.cn_medium_soil = float(v[30])
        self.cn_fine_soil = float(v[31])

        ## Winter crop
        if (self.class_number in [13, 14] or 
            'WINTER' in self.curve_name.upper()):
            self.gdd_trigger_doy = 274
            self.winter_crop = True
        else:
            self.gdd_trigger_doy = 1
            self.winter_crop = False
        ## DEADBEEF
        ## In older versions of VB code, "WINTER CANOLA" GDD trigger day isn't changed
        ##   but it is still processed as a "winter" crop in the rest of the code
        ##if (self.class_number in [13, 14] and
        ##    self.curve_name.upper().strip() == 'WINTER WHEAT'):
        ##    self.gdd_trigger_doy = 274
        ##    self.winter_crop = True
        ##elif (vb_flag and self.class_number in [40] and
        ##      'WINTER' in self.curve_name.upper().strip()):
        ##      ##'WINTER' in self.curve_name.upper().strip() == 'WINTER CANOLA'):
        ##    self.gdd_trigger_doy = 274
        ##    self.winter_crop = False
        ##else:
        ##    self.gdd_trigger_doy = 1
        ##    self.winter_crop = False
            
        ## Pre-compute parameters instead of re-computing them daily
        if self.flag_for_means_to_estimate_pl_or_gu == 3:
            ## Compute planting or green-up date from fractional month
            ## Putting in a date_of_pl_or_gu of "1" will return Jan. 15th
            ## Putting in a date_of_pl_or_gu of "10" will return Oct. 15th
            ## Putting in a date_of_pl_or_gu of "4.8333" will return Apr. 25th
            self.month_of_pl_or_gu = int(self.date_of_pl_or_gu)
            self.day_of_pl_or_gu = int(round(
                (self.date_of_pl_or_gu - self.month_of_pl_or_gu) * 30.4))
            if self.day_of_pl_or_gu < 0.5:  
                self.day_of_pl_or_gu = 15
            if self.month_of_pl_or_gu == 0:
                ## vb code (DateSerial) apparently resolves Mo=0 to 12
                self.date_of_pl_or_gu = 12
                logging.info('  Changing date_of_pl_or_gu from 0 to 12')
            ##self.doy_of_pl_or_gu = datetime.datetime(
            ##    foo_day.year, self.month_of_pl_or_gu, 
            ##    self.day_of_pl_or_gu).timetuple().tm_yday

    def __str__(self):
        """ """
        return '<%s>' % (self.name)

    def set_winter_soil(self, crops=[]):
        """ """
        pass
        #' setup curve number for antecedent II condition for winter covers
        #wscc = self.winter_surface_cover_class
        #self.cn_coarse_soil_winter = int(v[29])
        #self.cn_medium_soil_winter = int(v[30])
        #self.cn_fine_soil_winter   = int(v[31])

def read_crop_parameters(fn, vb_flag=False):
    """Read in the crop parameter text file"""

    ## For now, hardcode reading the first 32 lines after the 3 header rows
    crop_param_data = np.loadtxt(fn, delimiter="\t", dtype='str', skiprows=3)
    crop_param_data = crop_param_data[:32,:]

    ## Replace empty values
    crop_param_data[crop_param_data == ''] = '0'
    ##crop_param_data = np.where(crop_param_data == '', '0', crop_param_data)

    crops_dict = {}
    for crop_i, crop_num in enumerate(crop_param_data[1,2:]):
        if crop_num <> '0':
            crop_num = abs(int(crop_num))
        else:
            break
        crops_dict[crop_num] = CropParameters(crop_param_data[:,crop_i+2], vb_flag)
    return crops_dict

if __name__ == '__main__':
    pass
