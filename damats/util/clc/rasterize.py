#-------------------------------------------------------------------------------
#
#  DAMATS - Corine Land Cover - rasterization
#
# Project: EOxServer <http://eoxserver.org>
# Authors: Martin Paces <martin.paces@eox.at>
#
#-------------------------------------------------------------------------------
# Copyright (C) 2017 EOX IT Services GmbH
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies of this Software or works derived from this Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#-------------------------------------------------------------------------------

from os import remove
from os.path import isfile
from gdalconst import GA_ReadOnly
from osgeo import gdal; gdal.UseExceptions()
from osgeo import ogr; ogr.UseExceptions()
from osgeo import osr; osr.UseExceptions()

COLOR_FIELD = "index"

def rasterize_shapes(template, output, source, layer_name, classes, attrib):
    """ Rasterize vector dataset to a raster image with grid given by the
    sample raster image.
    """
    ds_source = ogr.Open(source, GA_ReadOnly)
    layer = get_layer(ds_source, layer_name)

    ds_template = gdal.Open(template, GA_ReadOnly)
    bbox = get_bbox(ds_template, layer.GetSpatialRef(), 0.2)

    # copy rasterized features to a temporary in-memory dataset
    ds_virt = ogr.GetDriverByName('Memory').CreateDataSource('tmp')
    virt_layer = ds_virt.CreateLayer(
        'shapes', layer.GetSpatialRef(), layer.GetGeomType()
    )
    virt_layer.CreateField(ogr.FieldDefn(COLOR_FIELD, ogr.OFTReal))
    _copy_colored_features(
        virt_layer, fetch_features(layer, bbox=bbox), classes,
        attrib, COLOR_FIELD
    )

    # output image rasterization
    if isfile(output):
        remove(output)
    ds_target = gdal.GetDriverByName('GTiff').Create(
        output, ds_template.RasterXSize, ds_template.RasterYSize, 1,
        gdal.GDT_Byte, ['TILED=YES', 'COMPRESS=LZW']
    )
    ds_target.SetGeoTransform(ds_template.GetGeoTransform())
    ds_target.SetProjection(ds_template.GetProjection())

    gdal.RasterizeLayer(
        ds_target, [1], virt_layer, burn_values=[127],
        options=["ATTRIBUTE=%s" % COLOR_FIELD]
    )

    # add palette to the image
    color_table = gdal.ColorTable()
    # set base colours
    for idx in xrange(255):
        color_table.SetColorEntry(idx, (0, 0, 0, 0))
    # set class colours
    for class_ in classes:
        color_table.SetColorEntry(class_['index'], class_['colour'])
    ds_target.GetRasterBand(1).SetColorTable(color_table)
    ds_target.GetRasterBand(1).GetNoDataValue()
    ds_target.FlushCache()


def get_layer(dataset, layer):
    """ Get layer from an OGR dataset by name. """
    for item in (
        dataset.GetLayer(idx) for idx in xrange(dataset.GetLayerCount())
    ):
        if item.GetName() == layer:
            return item
    else:
        raise ValueError("Invalid layer name.")


def fetch_features(layer, bbox=None, geom=None, **attr_filters):
    """ Fetch filtered features. """
    attr_filters = attr_filters.items()
    if geom:
        layer.SetSpatialFilter(geom)
    if bbox:
        minx, minx, maxx, maxy = bbox
        layer.SetSpatialFilterRect(minx, minx, maxx, maxy)
    layer.ResetReading()
    while True:
        feature = layer.GetNextFeature()
        if not feature:
            break
        for key, val in attr_filters:
            if feature.GetField(key) != val:
                break
        else:
            yield feature

def _copy_colored_features(target_layer, source_fetures, classes,
                           src_attribute, dst_attribute):
    """ Create new feature set for rasterisation. """
    # look-up table
    class_lookup = dict(
        (class_['attrib'][src_attribute], class_) for class_ in classes
        if class_['attrib'].get(src_attribute) is not None
    )

    for feature in source_fetures:
        class_ = class_lookup.get(feature.GetField(src_attribute))
        if class_:
            new_feature = ogr.Feature(target_layer.GetLayerDefn())
            new_feature.SetGeometry(feature.GetGeometryRef().Clone())
            new_feature.SetField(dst_attribute, class_[dst_attribute])
            target_layer.CreateFeature(new_feature)
    return target_layer


def _copy_field_definition(target_layer, source_layer):
    """ Copy field definitions from one-layer to another. """
    layer_defn = source_layer.GetLayerDefn()
    for field_defn in (
        layer_defn.GetFieldDefn(idx)
        for idx in xrange(layer_defn.GetFieldCount())
    ):
        target_layer.CreateField(field_defn)


def points_to_extent(outline):
    """ Extract extent of the outline. """
    # pylint: disable=invalid-name
    x = [x for x, _ in outline]
    y = [y for _, y in outline]
    return [min(x), min(y), max(x), max(y)]


def get_bbox(dataset, target_sr, expand_by=0):
    """ Get image bounding box in the desired projection system. """
    size_x = dataset.RasterXSize
    size_y = dataset.RasterYSize
    x00, dxx, dxy, y00, dyx, dyy = dataset.GetGeoTransform()
    corners = [
        (x00 + dxx*x + dxy*y, y00 + dyx*x + dyy*y) for x, y
        in [(0, 0), (size_x, 0), (size_x, size_y), (0, size_y), (0, 0)]
    ]
    if target_sr:
        ct_ = osr.CoordinateTransformation(
            osr.SpatialReference(dataset.GetProjection()), target_sr
        )
        corners = [
            ct_.TransformPoint(float(x), float(y))[:2] for x, y in corners
        ]
    bbox = points_to_extent(corners)
    if expand_by != 0:
        minx, miny, maxx, maxy = bbox
        dx = 0.5*expand_by*(maxx - minx)
        dy = 0.5*expand_by*(maxy - miny)
        bbox = [minx - dx, miny - dy, maxx + dx, maxy + dy]
    return bbox
