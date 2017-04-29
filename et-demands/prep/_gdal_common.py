#--------------------------------
# Name:         gdal_common.py
# Purpose:      Common GDAL Support Functions
# Author:       Charles Morton & Andrew Vitale
# Created       2016-07-25
# Python:       2.7
#--------------------------------

import glob
import itertools
import math
import os
import random
import sys

import numpy as np
from osgeo import gdal, ogr, osr

gdal.UseExceptions()


class Extent:
    """Bounding Geographic Extent"""
    # def __repr__(self):
    #     return '<Extent xmin:{0} ymin:{1} xmax:{2} ymax:{3}>'.format(
    #         self.xmin, self.ymin, self.xmax, self.ymax)

    def __str__(self):
        return '{0} {1} {2} {3}'.format(
            self.xmin, self.ymin, self.xmax, self.ymax)

    def __iter__(self):
        return iter((self.xmin, self.ymin, self.xmax, self.ymax))

    def __init__(self, (xmin, ymin, xmax, ymax), ndigits=10):
        """Round values to avoid Float32 rounding errors"""
        self.xmin = round(xmin, ndigits)
        self.ymin = round(ymin, ndigits)
        self.xmax = round(xmax, ndigits)
        self.ymax = round(ymax, ndigits)

    def adjust_to_snap(self, method='EXPAND', snap_x=None, snap_y=None,
                       cs=None):
        if snap_x is None and env.snap_x is not None:
            snap_x = env.snap_x
        if snap_y is None and env.snap_y is not None:
            snap_y = env.snap_y
        if cs is None:
            if env.cellsize:
                cs = env.cellsize
            else:
                raise SystemExit('Cellsize was not set')
        if method.upper() == 'ROUND':
            self.xmin = math.floor((self.xmin - snap_x) / cs + 0.5) * cs + snap_x
            self.ymin = math.floor((self.ymin - snap_y) / cs + 0.5) * cs + snap_y
            self.xmax = math.floor((self.xmax - snap_x) / cs + 0.5) * cs + snap_x
            self.ymax = math.floor((self.ymax - snap_y) / cs + 0.5) * cs + snap_y
        elif method.upper() == 'EXPAND':
            self.xmin = math.floor((self.xmin - snap_x) / cs) * cs + snap_x
            self.ymin = math.floor((self.ymin - snap_y) / cs) * cs + snap_y
            self.xmax = math.ceil((self.xmax - snap_x) / cs) * cs + snap_x
            self.ymax = math.ceil((self.ymax - snap_y) / cs) * cs + snap_y
        elif method.upper() == 'SHRINK':
            self.xmin = math.ceil((self.xmin - snap_x) / cs) * cs + snap_x
            self.ymin = math.ceil((self.ymin - snap_y) / cs) * cs + snap_y
            self.xmax = math.floor((self.xmax - snap_x) / cs) * cs + snap_x
            self.ymax = math.floor((self.ymax - snap_y) / cs) * cs + snap_y

    def buffer_extent(self, distance):
        self.xmin -= distance
        self.ymin -= distance
        self.xmax += distance
        self.ymax += distance

    def split_extent(self):
        """List of extent terms (xmin, ymin, xmax, ymax)"""
        return self.xmin, self.ymin, self.xmax, self.ymax

    def copy(self):
        """Return a copy of the extent"""
        return Extent((self.xmin, self.ymin, self.xmax, self.ymax))

    def corner_points(self):
        """Corner points in clockwise order starting with upper-left point"""
        return [(self.xmin, self.ymax), (self.xmax, self.ymax),
                (self.xmax, self.ymin), (self.xmin, self.ymin)]

    def ul_lr_swap(self):
        """Copy of extent object reordered as xmin, ymax, xmax, ymin

        Some gdal utilities want the extent described using upper-left and
        lower-right points.
            gdal_translate -projwin ulx uly lrx lry
            gdal_merge -ul_lr ulx uly lrx lry

        """
        return Extent((self.xmin, self.ymax, self.xmax, self.ymin))

    def ogrenv_swap(self):
        """Copy of extent object reordered as xmin, xmax, ymin, ymax

        OGR feature (shapefile) extents are different than GDAL raster extents
        """
        return Extent((self.xmin, self.xmax, self.ymin, self.ymax))

    def origin(self):
        """Origin (upper-left corner) of the extent"""
        return (self.xmin, self.ymax)

    def center(self):
        """Centroid of the extent"""
        return ((self.xmin + 0.5 * (self.xmax - self.xmin)),
                (self.ymin + 0.5 * (self.ymax - self.ymin)))

    def shape(self, cs=None):
        """Return number of rows and columns of the extent
        Args:
            cs: cellsize (default to env.cellsize if not set)
        Returns:
            tuple of raster rows and columns
        """
        if cs is None and env.cellsize:
            cs = env.cellsize
        cols = int(round(abs((self.xmin - self.xmax) / cs), 0))
        rows = int(round(abs((self.ymax - self.ymin) / -cs), 0))
        return rows, cols

    def geo(self, cs=None):
        """Geo-tranform of the extent"""
        if cs is None:
            if env.cellsize:
                cs = env.cellsize
            else:
                raise SystemExit('Cellsize was not set')
        return (self.xmin, abs(cs), 0., self.ymax, 0., -abs(cs))

    def geometry(self):
        """GDAL geometry object of the extent"""
        ring = ogr.Geometry(ogr.wkbLinearRing)
        for point in self.corner_points():
            ring.AddPoint(point[0], point[1])
        ring.CloseRings()
        polygon = ogr.Geometry(ogr.wkbPolygon)
        polygon.AddGeometry(ring)
        return polygon

    def intersect_point(self, xy):
        """"Test if Point XY intersects the extent"""
        if ((xy[0] > self.xmax) or
            (xy[0] < self.xmin) or
            (xy[1] > self.ymax) or
            (xy[1] < self.ymin)):
            return False
        else:
            return True


class env:
    """"Generic enviornment parameters used in gdal_common"""
    snap_proj, snap_osr, snap_geo = None, None, None
    snap_gcs_proj, snap_gcs_osr = None, None
    # snap_extent = Extent((0, 0, 1, 1))
    cellsize, snap_x, snap_y = None, None, None
    mask_geo, mask_path, mask_array = None, None, None
    mask_extent = Extent((0, 0, 1, 1))
    mask_gcs_extent = Extent((0, 0, 1, 1))
    mask_rows, mask_cols = 0, 0
    cloud_mask_ws = ''


def raster_driver(raster_path):
    """Return the GDAL driver from a raster path

    Currently supports ERDAS Imagine format, GeoTiff,
    HDF-EOS (HDF4), BSQ/BIL/BIP, and memory drivers.

    Args:
        raster_path (str): filepath to a raster


    Returns:
        GDAL driver: GDAL raster driver

    """
    if raster_path.upper().endswith('IMG'):
        return gdal.GetDriverByName('HFA')
    elif raster_path.upper().endswith('TIF'):
        return gdal.GetDriverByName('GTiff')
    elif raster_path.upper().endswith('TIFF'):
        return gdal.GetDriverByName('GTiff')
    elif raster_path.upper().endswith('HDF'):
        return gdal.GetDriverByName('HDF4')
    elif raster_path[-3:].upper() in ['BSQ', 'BIL', 'BIP']:
        return gdal.GetDriverByName('EHdr')
    elif raster_path == '':
        return gdal.GetDriverByName('MEM')
    else:
        sys.exit()


def numpy_to_gdal_type(numpy_type):
    """Return the GDAL raster data type based on the NumPy array data type

    The following built in functions do roughly the same thing
        NumericTypeCodeToGDALTypeCode
        GDALTypeCodeToNumericTypeCode

    Args:
        numpy_type (:class:`np.dtype`): NumPy array type
            (i.e. np.bool, np.float32, etc)

    Returns:
        g_type: GDAL `datatype <http://www.gdal.org/gdal_8h.html#a22e22ce0a55036a96f652765793fb7a4/>`
        _equivalent to the input NumPy :class:`np.dtype`

    """
    if numpy_type == np.bool:
        g_type = gdal.GDT_Byte
    elif numpy_type == np.int:
        g_type = gdal.GDT_Int32
    elif numpy_type == np.int8:
        g_type = gdal.GDT_Int16
    elif numpy_type == np.int16:
        g_type = gdal.GDT_Int16
    elif numpy_type == np.int32:
        g_type = gdal.GDT_Int32
    elif numpy_type == np.uint8:
        g_type = gdal.GDT_Byte
    elif numpy_type == np.uint16:
        g_type = gdal.GDT_UInt16
    elif numpy_type == np.uint32:
        g_type = gdal.GDT_UInt32
    elif numpy_type == np.float:
        g_type = gdal.GDT_Float64
    # elif numpy_type == np.float16:
    #     g_type = gdal.GDT_Float32
    elif numpy_type == np.float32:
        g_type = gdal.GDT_Float32
    elif numpy_type == np.float64:
        g_type = gdal.GDT_Float32
    # elif numpy_type == np.int64:
    #     g_type = gdal.GDT_Int32
    # elif numpy_type == np.uint64:
    #     g_type = gdal.GDT_UInt32
    # elif numpy_type == np.complex:
    #     g_type = gdal.GDT_CFloat32
    # elif numpy_type == np.complex64:
    #     g_type = gdal.GDT_CFloat32
    # elif numpy_type == np.complex128:
    #     g_type = gdal.GDT_CFloat32
    # else:
    #     numpy_type, m_type_max = gdal.GDT_Unknown
    else:
        g_type = None
    return g_type


def numpy_type_nodata(numpy_type):
    """Return the default nodata value based on the NumPy array data type

    Args:
        numpy_type (:class:`np.dtype`): numpy array type
            (i.e. np.bool, np.float32, etc)

    Returns:
        nodata_value: Nodata value for GDAL which defaults to the
            minimum value for the number type

    """
    if numpy_type == np.bool:
        nodata_value = 0
    elif numpy_type == np.int:
        nodata_value = int(np.iinfo(np.int32).min)
    elif numpy_type == np.int8:
        nodata_value = int(np.iinfo(np.int8).min)
    elif numpy_type == np.int16:
        nodata_value = int(np.iinfo(np.int16).min)
    elif numpy_type == np.int32:
        nodata_value = int(np.iinfo(np.int32).min)
    elif numpy_type == np.uint8:
        nodata_value = int(np.iinfo(np.uint8).max)
    elif numpy_type == np.uint16:
        nodata_value = int(np.iinfo(np.uint16).max)
    elif numpy_type == np.uint32:
        nodata_value = int(np.iinfo(np.uint32).max)
    elif numpy_type == np.float:
        nodata_value = float(np.finfo(np.float64).min)
    elif numpy_type == np.float16:
        nodata_value = float(np.finfo(np.float32).min)
    elif numpy_type == np.float32:
        nodata_value = float(np.finfo(np.float32).min)
    elif numpy_type == np.float64:
        nodata_value = float(np.finfo(np.float32).min)
    # elif numpy_type == np.int64:   nodata_value =
    # elif numpy_type == np.uint64:  nodata_value =
    # elif numpy_type == np.complex:    nodata_value =
    # elif numpy_type == np.complex64:  nodata_value =
    # elif numpy_type == np.complex128: nodata_value =
    # else: numpy_type, m_type_max = gdal.GDT_Unknown
    else:
        nodata_value = None
    return nodata_value


def gdal_to_numpy_type(gdal_type):
    """Return the NumPy array data type based on a GDAL type

    Args:
        gdal_type (:class:`gdal.type`): GDAL data type

    Returns:
        numpy_type: NumPy datatype (:class:`np.dtype`)

    """
    if gdal_type == gdal.GDT_Unknown:
        numpy_type = np.float64
    elif gdal_type == gdal.GDT_Byte:
        numpy_type = np.uint8
    elif gdal_type == gdal.GDT_UInt16:
        numpy_type = np.uint16
    elif gdal_type == gdal.GDT_Int16:
        numpy_type = np.int16
    elif gdal_type == gdal.GDT_UInt32:
        numpy_type = np.uint32
    elif gdal_type == gdal.GDT_Int32:
        numpy_type = np.int32
    elif gdal_type == gdal.GDT_Float32:
        numpy_type = np.float32
    elif gdal_type == gdal.GDT_Float64:
        numpy_type = np.float64
    # elif gdal_type == gdal.GDT_CInt16:
    #     numpy_type = np.complex64
    # elif gdal_type == gdal.GDT_CInt32:
    #     numpy_type = np.complex64
    # elif gdal_type == gdal.GDT_CFloat32:
    #     numpy_type = np.complex64
    # elif gdal_type == gdal.GDT_CFloat64:
    #     numpy_type = np.complex64
    return numpy_type


def osr_proj(input_osr):
    """Return the projection WKT of a spatial reference object

    Args:
        input_osr (:class:`osr.SpatialReference`): the input OSR
            spatial reference

    Returns:
        WKT: :class:`osr.SpatialReference` in WKT format

    """
    return input_osr.ExportToWkt()


def proj_osr(input_proj):
    """Return the spatial reference object of a projection WKT

    Args:
        input_proj (:class:`osr.SpatialReference` WKT): Input
            WKT formatted :class:`osr.SpatialReference` object
            to be used in creation of an :class:`osr.SpatialReference`

    Returns:
        osr.SpatialReference: OSR SpatialReference object as represented
            by the input WKT

    """
    input_osr = osr.SpatialReference()
    input_osr.ImportFromWkt(input_proj)
    return input_osr


def epsg_osr(input_epsg):
    """Return the spatial reference object of an EPSG code

    Args:
        input_epsg (int): EPSG spatial reference code as integer

    Returns:
        osr.SpatialReference: :class:`osr.SpatialReference` object

    """
    input_osr = osr.SpatialReference()
    input_osr.ImportFromEPSG(input_epsg)
    return input_osr


def epsg_proj(input_epsg):
    """Return the projecttion WKT of an EPSG code

    Args:
        input_epsg (int): EPS spatial reference code as an integer

    Returns:
        WKT: Well known text rerpresentation of :class:`osr.SpatialReference`
            object

    """
    return osr_proj(epsg_osr(input_epsg))


def proj4_osr(input_proj4):
    """Return the spatial reference object of a PROJ4 code

    Args:
        input_proj4 (str): Proj4 string representing a projection or GCS

    Returns:
        osr.SpatialReference: :class:`osr.SpatialReference` of the input proj4

    """
    input_osr = osr.SpatialReference()
    input_osr.ImportFromProj4(input_proj4)
    return input_osr


def osr_proj4(input_osr):
    """Return the PROJ4 code of an osr.SpatialReference

    Args:
        input_osr (:class:`osr.SpatialReference`): OSR Spatial reference
            of the input projection/GCS

    Returns:
        str: Proj4 string of the projection or GCS

    """
    return input_osr.ExportToProj4()


def raster_path_osr(raster_path):
    """Return the spatial reference of a raster

    Args:
        raster_path (str): The filepath of the input raster

    Returns:
        osr.SpatialReference: :class:`osr.SpatialReference` object
            that defines the input raster's project/GCS

    """
    raster_ds = gdal.Open(raster_path, 0)
    raster_osr = raster_ds_osr(raster_ds)
    raster_ds = None
    return raster_osr


def raster_ds_osr(raster_ds):
    """Return the spatial reference of an opened raster dataset

    Args:
        raster_ds (:class:`gdal.Dataset`): An input GDAL raster dataset

    Returns:
        osr.SpatialReference: :class:`osr.SpatialReference` of a raster
            dataset

    """
    return proj_osr(raster_ds_proj(raster_ds))


def feature_path_osr(feature_path):
    """Return the spatial reference of a feature path

    Args:
        feature_path (str): file path to the OGR supported feature

    Returns:
        osr.SpatialReference: :class:`osr.SpatialReference` of the
            input feature file path

    """
    feature_ds = ogr.Open(feature_path)
    feature_osr = feature_ds_osr(feature_ds)
    feature_ds = None
    return feature_osr


def feature_ds_osr(feature_ds):
    """Return the spatial reference of an opened feature dataset

    Args:
        feature_ds (:class:`ogr.Datset`): Opened feature dataset
            from which you desire the spatial reference

    Returns:
        osr.SpatialReference: :class:`osr.SpatialReference` of the input
            OGR feature dataset

    """
    feature_lyr = feature_ds.GetLayer()
    return feature_lyr_osr(feature_lyr)


def feature_lyr_osr(feature_lyr):
    """Return the spatial reference of a feature layer

    Args:
        feature_lyr (:class:`ogr.Layer`): OGR feature layer from
            which you desire the :class:`osr.SpatialReference`

    Returns:
        osr.SpatialReference: the :class:`osr.SpatialReference` object
            of the input feature layer

    """
    return feature_lyr.GetSpatialRef()


def raster_path_proj(raster_path):
    """Return the projection WKT of a raster

    Args:
        raster_path (str): filepath of the input raster

    Returns:
        str: Well Known Text (WKT) string of the input raster path's
            geographic projection or coordinate system

    """
    raster_ds = gdal.Open(raster_path, 0)
    raster_proj = raster_ds_proj(raster_ds)
    raster_ds = None
    return raster_proj


def raster_ds_proj(raster_ds):
    """Return the projection WKT of an opened raster dataset

    Args:
        raster_ds (:class:`gdal.Dataset`): An opened GDAL raster
            dataset

    Returns:
        str: Well known text (WKT) formatted represetnation of the projection

    """
    return raster_ds.GetProjection()


def feature_path_extent(feature_path):
    """"Return the bounding extent of a feature path

    Args:
        feature_path (str): file path to the feature

    Returns:
        gdal_common.extent: :class:`gdal_common.extent` of the
            input feature path

    """
    feature_ds = ogr.Open(feature_path, 0)
    feature_extent = feature_ds_extent(feature_ds)
    feature_ds = None
    return feature_extent


def feature_ds_extent(feature_ds):
    """"Return the bounding extent of an opened feature dataset

    Args:
        feature_ds (:class:`ogr.Dataset`): An opened feature dataset
            from OGR

    Returns:
        gdal_common.extent: :class:`gdal_common.extent` of the input
            feature dataset

    """
    feature_lyr = feature_ds.GetLayer()
    feature_extent = feature_lyr_extent(feature_lyr)
    return feature_extent


def feature_lyr_extent(feature_lyr):
    """Return the extent of an opened feature layer

    Args:
        feature_lyr (:class:`ogr.Layer`): An OGR feature
            layer

    Returns:
        gdal_common.extent: :class:`gdal_common.extent` of the
            input feature layer

    """
    # OGR Extent format (xmin, xmax, ymin, ymax)
    # ArcGIS/GDAL(?) Extent format (xmin, ymin, xmax, ymax)
    f_extent = Extent(feature_lyr.GetExtent())
    f_env = f_extent.ogrenv_swap()
    # f_extent.ymin, f_extent.xmax = f_extent.xmax, f_extent.ymin
    return f_env


def raster_path_geo(raster_path):
    """Return the geo-transform of a raster

    Args:
        raster_path (str): File path of the input raster

    Returns:
        tuple: :class:`gdal.Geotransform` of the raster the
            input file path points to

    """
    raster_ds = gdal.Open(raster_path, 0)
    raster_geo = raster_ds_geo(raster_ds)
    raster_ds = None
    return raster_geo


def raster_ds_geo(raster_ds):
    """Return the geo-transform of an opened raster dataset

    Args:
        raster_ds (:class:`gdal.Dataset`): An Opened gdal raster dataset

    Returns:
        tuple: :class:`gdal.Geotransform` of the input dataset

    """
    return round_geo(raster_ds.GetGeoTransform())


def round_geo(geo, n=10):
    """Round the values of a geotransform to n digits

    Args:
        geo (tuple): :class:`gdal.Geotransform` object
        n (int): number of digits to round the
            :class:`gdal.Geotransform` to

    Returns:
        tuple: :class:`gdal.Geotransform` rounded to n digits

    """
    return tuple([round(i, n) for i in geo])


# def raster_path_nodata(raster_path, band=1):
#     raster_ds = gdal.Open(raster_path, 0)
#     band = raster_ds.GetRasterBand(band)
#     nodata_value = band.GetNoDataValue()
#     raster_ds = None
#     return nodata_value


def raster_path_extent(raster_path):
    """Return the extent of a raster

    Args:
        raster_path (str): File path of the input raster

    Returns:
        tuple: :class:`gdal_common.extent` of the raster file path

    """
    raster_ds = gdal.Open(raster_path, 0)
    raster_extent = raster_ds_extent(raster_ds)
    raster_ds = None
    return raster_extent


def raster_ds_extent(raster_ds):
    """Return the extent of an opened raster dataset

    Args:
        raster_ds (:class:`gdal.Dataset`): An opened GDAL raster
            dataset

    Returns:
        tuple: :class:`gdal_common.extent` of the input dataset

    """
    raster_rows, raster_cols = raster_ds_shape(raster_ds)
    raster_geo = raster_ds_geo(raster_ds)
    return geo_extent(raster_geo, raster_rows, raster_cols)


def raster_path_cellsize(raster_path, x_only=False):
    """Return pixel width & pixel height of raster


    Args:
        raster_path (str): filepath to the raster
        x_only (bool): If True, only return cell width

    Returns:
        float: cellsize of the input raster filepath
    """
    raster_ds = gdal.Open(raster_path, 0)
    raster_cellsize = raster_ds_cellsize(raster_ds, x_only)
    raster_ds = None
    return raster_cellsize


def raster_ds_cellsize(raster_ds, x_only=False):
    """Return pixel width & pixel height of an opened raster dataset

    Args:
        raster_ds (:class:`gdal.Dataset`): the input GDAL raster dataset
        x_only (bool): If True, only return cell width

    Returns:
        float: Cellsize of input raster dataset

    """
    return geo_cellsize(raster_ds_geo(raster_ds), x_only)


def geo_cellsize(raster_geo, x_only=False):
    """Return pixel width & pixel height of geo-transform

    Args:
        raster_geo (tuple): :class:`gdal.Geotransform` object
        x_only (bool): If True, only return cell width

    Returns:
        tuple: tuple containing the x or x and y cellsize
    """
    if x_only:
        return raster_geo[1]
    else:
        return (raster_geo[1], raster_geo[5])


def raster_path_origin(raster_path):
    """Return upper-left corner of raster

    Returns the upper-left corner coordinates of a raster file path,
    with the coordinates returned in the same projection/GCS as the
    input raster file.

    Args:
        raster_path (str): The raster filepath

    Returns:
        tuple:
        raster_origin: (x, y) coordinates of the upper left corner

    """
    raster_ds = gdal.Open(raster_path, 0)
    raster_origin = raster_ds_origin(raster_ds)
    raster_ds = None
    return raster_origin


def raster_ds_origin(raster_ds):
    """Return upper-left corner of an opened raster dataset

    Returns the upper-left corner coorindates of an open GDAL raster
    dataset with the coordinates returned in the same project/GCS as the
    input raster dataset.

    Args:
        raster_ds (:class:`GDAL.Dataset`): Open GDAL raster dataset

    Returns:
        tuple:
        raster_origin: (x, y) coordinates of the upper left corner

    """
    return geo_origin(raster_ds_geo(raster_ds))


def geo_origin(raster_geo):
    """Return upper-left corner of geo-transform

    Returns the upper-left corner cordinates of :class:`GDAL.Geotransform`
    with the coordinates returned in the same projection/GCS as the input
    geotransform.

    Args:
        raster_geo (:class:`GDAL.Geotransform`): Input GDAL Geotransform

    Returns:
        tuple:
        raster_origin: (x, y) coordinates of the upper left corner

    """
    return (raster_geo[0], raster_geo[3])


def geo_extent(geo, rows, cols):
    """Return the extent from a geo-transform and array shape

    This function takes the :class:`GDAL.Geotransform`, number of
    rows, and number of columns in a 2-dimensional :class:`np.array`
    (the :class:`np.array.shape`),and returns a :class:`gdc.extent`

    Geo-transform can be UL with +/- cellsizes or LL with +/+ cellsizes
    This approach should also handle UR and RR geo-transforms

    Returns ArcGIS/GDAL Extent format (xmin, ymin, xmax, ymax) but
        OGR Extent format (xmin, xmax, ymax, ymin) can be obtained using the
        extent.ul_lr_swap() method

    Args:
        geo (tuple): :class:`gdal.Geotransform` object
        rows (int): number of rows
        cols (int): number of cols

    Returns:
        gdal_common.extent:
        A :class:`gdal_common.extent` class object

    """
    cs_x, cs_y = geo_cellsize(geo, x_only=False)
    origin_x, origin_y = geo_origin(geo)
    # ArcGIS/GDAL Extent format (xmin, ymin, xmax, ymax)
    return Extent([min([origin_x + cols * cs_x, origin_x]),
                   min([origin_y + rows * cs_y, origin_y]),
                   max([origin_x + cols * cs_x, origin_x]),
                   max([origin_y + rows * cs_y, origin_y])])
    # OGR Extent format (xmin, xmax, ymax, ymin)
    # return Extent([origin_x, (origin_x + cols * cellsize),
    #                origin_y, (origin_y + rows * (-cellsize))])


def raster_path_shape(raster_path):
    """Return the number of rows and columns in a raster

    Args:
        raster_path (str): file path of the raster


    Returns:
        tuple of raster rows and columns
    """
    raster_ds = gdal.Open(raster_path, 0)
    raster_shape = raster_ds_shape(raster_ds)
    raster_ds = None
    return raster_shape


def raster_ds_shape(raster_ds):
    """Return the number of rows and columns in an opened raster dataset

    Args:
        raster_ds: opened raster dataset

    Returns:
        tuple of raster rows and columns
    """
    return raster_ds.RasterYSize, raster_ds.RasterXSize


def project_extent(input_extent, input_osr, output_osr, cellsize=None):
    """Project extent to different spatial reference / coordinate system

    Args:
        input_extent (): the input gdal_common.extent to be reprojected
        input_osr (): OSR spatial reference of the input extent
        output_osr (): OSR spatial reference of the desired output
        cellsize (): the cellsize used to calculate the new extent.
            If None, will attempt to use gdal_common.environmente
            This cellsize is in the input spatial reference

    Returns:
        tuple: :class:`gdal_common.extent` in the desired projection
    """
    if cellsize is None and env.cellsize:
        cellsize = env.cellsize
    # Build an in memory feature to project to
    mem_driver = ogr.GetDriverByName('Memory')
    output_ds = mem_driver.CreateDataSource('')
    output_lyr = output_ds.CreateLayer(
        'projected_extent', geom_type=ogr.wkbPolygon)
    feature_defn = output_lyr.GetLayerDefn()
    # Place points at every "cell" between pairs of corner points
    ring = ogr.Geometry(ogr.wkbLinearRing)
    corners = input_extent.corner_points()
    for point_a, point_b in zip(corners, corners[1:] + [corners[0]]):
        if cellsize is None:
            steps = 1000
        else:
            steps = float(max(
                abs(point_b[0] - point_a[0]),
                abs(point_b[1] - point_a[1]))) / cellsize
        # steps = float(abs(point_b[0] - point_a[0])) / cellsize
        for x, y in zip(np.linspace(point_a[0], point_b[0], steps + 1),
                        np.linspace(point_a[1], point_b[1], steps + 1)):
            ring.AddPoint(x, y)
    ring.CloseRings()
    # Set the ring geometry into a polygon
    polygon = ogr.Geometry(ogr.wkbPolygon)
    polygon.AddGeometry(ring)
    # Project the geometry
    tx = osr.CoordinateTransformation(input_osr, output_osr)
    polygon.Transform(tx)
    # Create a new feature and set the geometry into it
    feature = ogr.Feature(feature_defn)
    feature.SetGeometry(polygon)
    # Add the feature to the output layer
    output_lyr.CreateFeature(feature)
    # Get the extent from the projected polygon
    return feature_lyr_extent(output_lyr)


def block_gen(rows, cols, bs=64, random_flag=False):
    """Generate block indices for reading rasters/arrays as blocks

    Return the row (y/i) index, then the column (x/j) index

    Args:
        rows (int): number of rows in raster/array
        cols (int): number of columns in raster/array
        bs (int): gdal_common block size (produces square block)
        random (boolean): randomize the order or yielded blocks

    Yields:
        block_i and block_j indices of the raster using the specified block size

    Example:
        from osgeo import gdal, ogr, osr
        import gdal_common as gis

        ds = gdal.Open('/home/vitale232/Downloads/ndvi.img')
        rows = ds.RasterYSize
        cols = ds.RasterXSize

        generator = gis.block_gen(rows, cols)
        for row, col in generator:
            print('Row: {0}'.format(row))
            print('Col: {0}\\n'.format(col))

        random_generator = gis.block_gen(rows, cols, random_flag=True)
        for row, col in random_generator:
            print('Row/Col: {0} {1}\n'.format(row, col))

    """
    if random_flag:
        # DEADBEEF - Is this actually a generator?
        block_ij_list = list(itertools.product(
            range(0, rows, bs), range(0, cols, bs)))
        random.shuffle(block_ij_list)
        for b_i, b_j in block_ij_list:
            yield b_i, b_j
    else:
        for block_i in xrange(0, rows, bs):
            for block_j in xrange(0, cols, bs):
                yield block_i, block_j


def block_shape(input_rows, input_cols, block_i=0, block_j=0, bs=64):
    """"""
    int_rows = bs if (block_i + bs) < input_rows else input_rows - block_i
    int_cols = bs if (block_j + bs) < input_cols else input_cols - block_j
    return int_rows, int_cols


def raster_to_block(input_raster, block_i=0, block_j=0, bs=64, band=1,
                    fill_value=None, return_nodata=False):
    """Return a NumPy array from an opened raster dataset

    Args:
        input_raster (str): file path of the raster
        block_i (int): gdal_common row index for the block
        block_j (int): gdal_common column index for the block
        bs (int): gdal_common block size (cells)
        band (int): band number to read the array from
        fill_value (float): Use as nodata value if raster nodata value is not set
        return_nodata (bool): If True, returns no data value with the array

    Returns:
        output_array: The array of the raster values
        output_nodata: No data value of the raster file
    """
    input_raster_ds = gdal.Open(input_raster, 0)
    output_array, output_nodata = raster_ds_to_block(
        input_raster_ds, block_i, block_j, bs, band,
        fill_value, return_nodata=True)
    input_raster_ds = None
    if return_nodata:
        return output_array, output_nodata
    else:
        return output_array

def raster_ds_to_block(input_raster_ds, block_i=0, block_j=0, bs=64, band=1,
                       fill_value=None, return_nodata=False):
    """Return a NumPy array from an opened raster dataset

    Args:
        input_raster_ds (): opened raster dataset as gdal raster
        block_i (int): gdal_common row index for the block
        block_j (int): gdal_common column index for the block
        bs (int): gdal_common block size (cells)
        band (int): band number to read the array from
        fill_value (float): Use as nodata value if raster nodata value is not set
        return_nodata (bool): If True, returns no data value with the array

    Returns:
        output_array: The array of the raster values
        output_nodata: No data value of the raster file
    """
    # Array is read from upper left corner
    # input_extent = raster_ds_extent(input_raster_ds)
    # input_geo = raster_ds_geo(input_raster_ds)
    # input_cs = geo_cellsize(input_geo, x_only=True)
    input_rows, input_cols = raster_ds_shape(input_raster_ds)
    input_band = input_raster_ds.GetRasterBand(band)
    input_type = input_band.DataType
    input_nodata = input_band.GetNoDataValue()
    # Use fill_value as the raster nodata value if raster doesn't have a
    #   nodata value set
    if input_nodata is None and fill_value is not None:
        input_nodata = fill_value
    # If raster doesn't have a nodata value and fill value isn't set
    #   use default nodata value for raster data type
    elif input_nodata is None and fill_value is None:
        input_nodata = numpy_type_nodata(input_type)
    #
    int_rows, int_cols = block_shape(
        input_rows, input_cols, block_i, block_j, bs)
    output_array = input_band.ReadAsArray(block_j, block_i, int_cols, int_rows)
    if (output_array.dtype == np.float32 or
        output_array.dtype == np.float64):
        output_nodata = np.nan
        output_array[output_array == input_nodata] = output_nodata
    else:
        output_nodata = int(input_nodata)
    if return_nodata:
        return output_array, output_nodata
    else:
        return output_array


def block_to_raster(input_array, output_raster, block_i=0, block_j=0,
                    bs=64, band=1, output_nodata=None):
    """Write a gdal_common block to an output raster file

    Args:
        input_array (np.ndarray): array with values to write
        output_raster (str): filepath of the raster for the block to write to
        block_i (int): gdal_common row index for the block
        block_j (int): gdal_common column index for the block
        bs (int): gdal_common block size (cells)
        band (int): band of output_raster for writing to occur
        output_nodata (int, float): nodata value of the output_raster

    Returns:
        None. Operates on disk.
    """
    try:
        output_raster_ds = gdal.Open(output_raster, 1)
        output_rows, output_cols = raster_ds_shape(output_raster_ds)
        output_band = output_raster_ds.GetRasterBand(band)
        # If output_nodata is not set, use the existing raster nodata value
        if output_nodata is None:
            output_nodata = output_band.GetNoDataValue()
        # otherwise, reset the raster nodata value
        else:
            output_band.SetNoDataValue(output_nodata)
        # If float type, set nan values to raster nodata value
        if (input_array.dtype == np.float32 or
            input_array.dtype == np.float64):
            # Copy the input raster so that the nodata value can be modified
            output_array = np.copy(input_array)
            output_array[np.isnan(input_array)] = output_nodata
            output_band.WriteArray(output_array, block_j, block_i)
        else:
            output_band.WriteArray(input_array, block_j, block_i)
        # Don't calculate statistics for block
        output_raster_ds = None
    except:
        raise IOError(('Does the output raster exist?\n' +
                       '{0} may not exist.\n'.format(output_raster) +
                       'See gdal_common.build_empty_raster()'))


def build_empty_raster_mp(args):
    """Wrapper for calling build_empty_raster"""
    build_empty_raster(*args)


def build_empty_raster(output_raster, band_cnt=1, output_dtype=None,
                       output_nodata=None, output_proj=None,
                       output_cs=None, output_extent=None,
                       output_fill_flag=False, output_bs=64):
    """Build a new empty raster

    Args:
        output_raster (str):
        band_cnt (int):
        output_dtype ():
        output_nodata ():
        output_proj ():
        output_cs (int):
        output_extent ():
        output_fill_flag (bool):
        output_bs (int):

    Returns:
        Bool: True if raster was successfully written. Otherwise, False.
    """
    if output_dtype is None:
        output_dtype = np.float32
    output_gtype = numpy_to_gdal_type(output_dtype)
    # Only get the numpy nodata value if one was not passed to function
    if output_nodata is None and output_dtype:
        output_nodata = numpy_type_nodata(output_dtype)
    if output_proj is None and env.snap_proj:
        output_proj = env.snap_proj
    if output_cs is None and env.cellsize:
        output_cs = env.cellsize
    if output_extent is None and env.mask_extent:
        output_extent = env.mask_extent
    output_driver = raster_driver(output_raster)
    remove_file(output_raster)
    # output_driver.Delete(output_raster)
    output_rows, output_cols = output_extent.shape(output_cs)
    if output_raster.upper().endswith('IMG'):
        output_ds = output_driver.Create(
            output_raster, output_cols, output_rows, band_cnt, output_gtype,
            ['COMPRESSED=YES', 'BLOCKSIZE={}'.format(output_bs)])
    else:
        output_ds = output_driver.Create(
            output_raster, output_cols, output_rows,
            band_cnt, output_gtype)
    output_ds.SetGeoTransform(output_extent.geo(output_cs))
    output_ds.SetProjection(output_proj)
    for band in xrange(band_cnt):
        output_band = output_ds.GetRasterBand(band + 1)
        if output_fill_flag:
            output_band.Fill(output_nodata)
        output_band.SetNoDataValue(output_nodata)
    output_ds = None
    return True


def remove_file(file_path):
    """Remove a feature/raster and all of its anciallary files"""
    file_ws = os.path.dirname(file_path)
    for file_name in glob.glob(os.path.splitext(file_path)[0]+".*"):
        os.remove(os.path.join(file_ws, file_name))
