#!/usr/bin/env python
import logging

import numpy as np


class CropParameters:
    def __init__(self, crop_params_data):
        """
        Args:
            crop_params_data (list): crop params data from static text file
        Returns:
            None
        """

        # If there is a comma in the string, it will also have quotes
        self.name = str(crop_params_data[0]).replace('"', '').strip()
        self.class_number = abs(int(crop_params_data[1]))
        # DEADBEEF - Is this even used?
        if int(crop_params_data[1]) < 0:
            self.is_annual = True
        else:
            self.is_annual = False
        self.irrigation_flag = int(crop_params_data[2])
        self.days_after_planting_irrigation = int(crop_params_data[3])
        self.crop_fw = int(crop_params_data[4])
        self.winter_surface_cover_class = int(crop_params_data[5])
        self.kc_max = float(crop_params_data[6])
        self.mad_initial = int(crop_params_data[7])
        self.mad_midseason = int(crop_params_data[8])
        self.rooting_depth_initial = float(crop_params_data[9])
        self.rooting_depth_max = float(crop_params_data[10])
        self.end_of_root_growth_fraction_time = float(crop_params_data[11])
        self.height_initial = float(crop_params_data[12])
        self.height_max = float(crop_params_data[13])
        self.curve_number = int(crop_params_data[14])
        self.curve_name = str(crop_params_data[15]).replace('"', '').strip()
        self.curve_type = int(crop_params_data[16])
        self.flag_for_means_to_estimate_pl_or_gu = int(crop_params_data[17])
        self.t30_for_pl_or_gu_or_cgdd = float(crop_params_data[18])
        self.date_of_pl_or_gu = float(crop_params_data[19])
        self.tbase = float(crop_params_data[20])
        self.cgdd_for_efc = float(crop_params_data[21])
        self.cgdd_for_termination = float(crop_params_data[22])
        self.time_for_efc = float(crop_params_data[24])
        self.time_for_harvest = float(crop_params_data[25])
        self.killing_frost_temperature = float(crop_params_data[26])
        self.invoke_stress = int(crop_params_data[27])
        self.cn_coarse_soil = float(crop_params_data[29])
        self.cn_medium_soil = float(crop_params_data[30])
        self.cn_fine_soil = float(crop_params_data[31])

        # Winter crop
        if (self.class_number in [13, 14] or
            'WINTER' in self.curve_name.upper()):
            self.gdd_trigger_doy = 274
            self.winter_crop = True
        else:
            self.gdd_trigger_doy = 1
            self.winter_crop = False

        # DEADBEEF
        # In older versions of VB code, "WINTER CANOLA" GDD trigger day isn't changed
        #   but it is still processed as a "winter" crop in the rest of the code
        # if (self.class_number in [13, 14] and
        #     .curve_name.upper().strip() == 'WINTER WHEAT'):
        #     .gdd_trigger_doy = 274
        #     .winter_crop = True
        # elif (vb_flag and self.class_number in [40] and
        #      'WINTER' in self.curve_name.upper().strip()):
        #      # 'WINTER' in self.curve_name.upper().strip() == 'WINTER CANOLA'):
        #     .gdd_trigger_doy = 274
        #     .winter_crop = False
        # else:
        #     .gdd_trigger_doy = 1
        #     .winter_crop = False

        # Pre-compute parameters instead of re-computing them daily
        # # Flag_for_means_to_estimate_pl_or_gu Case 3
        if self.flag_for_means_to_estimate_pl_or_gu == 3:
            # Compute planting or green-up date from fractional month
            # Putting in a date_of_pl_or_gu of "1" will return Jan. 15th
            # Putting in a date_of_pl_or_gu of "10" will return Oct. 15th
            # Putting in a date_of_pl_or_gu of "4.8333" will return Apr. 25th
            self.month_of_pl_or_gu = int(self.date_of_pl_or_gu)
            self.day_of_pl_or_gu = int(round(
                (self.date_of_pl_or_gu - self.month_of_pl_or_gu) * 30.4))
            if self.day_of_pl_or_gu < 0.5:
                self.day_of_pl_or_gu = 15
            if self.month_of_pl_or_gu == 0:
                # vb code (DateSerial) apparently resolves Mo=0 to 12
                self.date_of_pl_or_gu = 12
                logging.info('  Changing date_of_pl_or_gu from 0 to 12')
            # self.doy_of_pl_or_gu = datetime.datetime(
            #     _day.year, self.month_of_pl_or_gu,
            #     .day_of_pl_or_gu).timetuple().tm_yday

        # Cuttings
        # Special case for ALFALFA   1 added 4/18/08
        if (self.class_number in [1, 2, 3] or
            (self.class_number >= 4 and
             self.curve_name.upper() == "ALFALFA 1ST CYCLE")):
            self.cutting_crop = True
        else:
            self.cutting_crop = False

    def __str__(self):
        """ """
        output = '  Crop {} - {}\n'.format(self.class_number, self.name)
        for key in self.__dict__:
            output += "    {k} = {v}\n".format(k=key, v=self.__dict__[key])
        return output
        # return '<%s>' % (self.name)

    # def __repr__(self):
    #     """ """
    #     sb = []
    #     for key in self.__dict__:
    #         sb.append("{key}='{value}'".format(key=key, value=self.__dict__[key]))
    #     return '<%s>' % (self.name)

    def set_winter_soil(self, crops=[]):
        """ """
        pass
        # # setup curve number for antecedent II condition for winter covers
        # wscc = self.winter_surface_cover_class
        # self.cn_coarse_soil_winter = int(crop_params_path[29])
        # self.cn_medium_soil_winter = int(crop_params_path[30])
        # self.cn_fine_soil_winter   = int(crop_params_path[31])


def read_crop_parameters(fn):
    """Read in the crop parameter text file"""

    # For now, hardcode reading the first 32 lines after the 3 header rows
    crop_param_data = np.loadtxt(fn, delimiter="\t", dtype='str', skiprows=3)
    crop_param_data = crop_param_data[:32, :]

    # Replace empty values with 0
    crop_param_data[crop_param_data == ''] = '0'
    # crop_param_data = np.where(crop_param_data == '', '0', crop_param_data)

    crops_dict = {}
    for crop_i, crop_num in enumerate(crop_param_data[1, 2:]):
        if crop_num != '0':
            crop_num = abs(int(crop_num))
        else:
            break
        crops_dict[crop_num] = CropParameters(crop_param_data[:, crop_i+2])
    return crops_dict

if __name__ == '__main__':
    pass