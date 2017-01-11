Static Template Files
=====================

The text files in the "et-demands\\static" folder are templates of the static input files needed for running ET-Demands.  The files are tab delimited and the structure and naming mimic the Excel file used to control the VB version of the ET-Demands model.  The file "et-demands\\static\\TemplateMetAndDepletionNodes.xlsx" is an example of the Excel control file.

The template files should not be modified directly.  Instead, the :doc:`prep tools workflow<prep>` should be used to automatically populate the files or the files can copied to a "project\\static" folder and the values set manually.

CropCoefs.txt
  Crop coefficient curves for each crop.  Generally, these values should not be modified.
CropParams.txt
  Crop parameters that can/should be modified during calibration.
ETCellsCrops.txt
  Flags controlling which crops to simulate.  If using the prep workflow, the flags will initially be set based on the CDL acreage.
ETCellsProperties.txt
  Soil properties and weather station data for each ET cell.  This file links the stations and the ET cells.
EToRatiosMon.txt
  Reference ET scale factors by month for each ET cell.  This file could be used to account for a seasonal bias in the input weather data.  This file is optional.
MeanCuttings.txt
  Sets the assumed number of alfalfa cuttings.  This is important since the CropET module will use different crop coefficient curves for the first and last cutting.
