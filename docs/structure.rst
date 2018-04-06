ET-Demands Folder Structure
===========================

The ET-Demands scripts and tools are assuming that the user will use a folder structure similar to the one below.  The exact folder paths can generally be adjusted by either changing the INI file or explicitly setting the folder using the script command line arguments.  Most of the GIS sub-folders can be built and populated using the :doc:`CropET prep tools<prep_tools>`::

    et-demands
    |
    +---common
    |   +---cdl
    |   |       2010_30m_cdls.img
    |   |       2010_30m_cdls.zip
    |   +---huc8
    |   |       wbdhu8_albers.shp
    |   +---nldas_4km
    |   \---soils
    |       +---gsmsoil_awc
    |       |       gsmsoilmu_a_us_awc_albers.shp
    |       +---gsmsoil_clay
    |       |       gsmsoilmu_a_us_clay_albers.shp
    |       \---gsmsoil_sand
    |               gsmsoilmu_a_us_sand_albers.shp
    |
    +---et-demands
    |   +---cropET
    |   |   \---bin
    |   +---prep
    |   +---refET
    |   +---static
    |   |       CropCoefs.txt
    |   |       CropParams.txt
    |   |       ETCellsCrops.txt
    |   |       ETCellsProperties.txt
    |   |       EToRatiosMon.txt
    |   |       MeanCuttings.txt
    |   |       TemplateMetAndDepletionNodes.xlsx
    |   \---tools
    |
    \---example
        |       example.ini
        +---annual_stats
        +---daily_baseline
        +---daily_plots
        +---daily_stats
        +---gis
        |   +---cdl
        |   +---huc8
        |   |       wbdhu8_albers.shp
        |   +---soils
        |   |       awc_30m_albers.img
        |   |       clay_30m_albers.img
        |   |       sand_30m_albers.img
        |   \---stations
        |           nldas_4km_dd_pts.shp
        +---monthly_stats
        \---static