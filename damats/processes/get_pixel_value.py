#-------------------------------------------------------------------------------
#
#  DAMATS get pixel value
#
# Project: DAMATS
# Authors: Martin Paces <martin.paces@eox.at>
#
#-------------------------------------------------------------------------------
# Copyright (C) 2016 EOX IT Services GmbH
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

import json
from math import floor
from logging import getLogger
from osgeo import osr, gdal
from eoxserver.core import Component, implements
from eoxserver.services.ows.wps.interfaces import ProcessInterface
from eoxserver.services.ows.wps.parameters import (
    LiteralData, AllowedRange,
)
from eoxserver.services.ows.wps.exceptions import InvalidInputValueError
from eoxserver.resources.coverages.models import RectifiedDataset
from damats.processes.utils import invert_matrix_2x2

SR_WGS84 = osr.SpatialReference()
SR_WGS84.ImportFromEPSG(4326)


class OutOfExtent(Exception):
    """ Out of extent exception. """
    pass

def extract_pixel_value(image_path, latitude, longitude):
    """ Extract pixel value. """
    dataset = gdal.Open(image_path)
    size_u = dataset.RasterXSize
    size_v = dataset.RasterYSize
    x00, dxu, dxv, y00, dyu, dyv = dataset.GetGeoTransform()

    # coordinate conversion
    ct_ = osr.CoordinateTransformation(
        SR_WGS84, osr.SpatialReference(dataset.GetProjection()),
    )

    # calculate pixel coordinates
    x, y = ct_.TransformPoint(longitude, latitude)[:2]
    dx, dy = x - x00, y - y00
    dux, duy, dvx, dvy = invert_matrix_2x2(dxu, dxv, dyu, dyv)
    u, v = int(floor(dux*dx + duy*dy)), int(floor(dvx*dx + dvy*dy))

    if u < 0 or u >= size_u or v < 0 or v > size_v:
        raise OutOfExtent

    # extract pixel
    pixel = dataset.ReadAsArray(u, v, 1, 1)[..., 0, 0]

    if len(pixel.shape) == 0:
        return [float(pixel)]
    else:
        return [float(v) for v in pixel]


class GetPixelValue(Component):
    """ Extract value of a pixel at the queried geographic location.

    The process returns an exception if the location outside of the image
    extent.
    """
    implements(ProcessInterface)

    synchronous = True
    asynchronous = False

    identifier = "getPixelValue"
    title = "Get pixel value."""
    metadata = {}
    profiles = ["point-query"]

    inputs = [
        ("coverage_id", LiteralData(
            "coverage", str, title="Coverage identifier"
        )),
        ("latitude", LiteralData(
            'latitude', float, title="Latitude",
            allowed_values=AllowedRange(-90.0, 90.0, 'closed', dtype=float),
            abstract="Latitude of the queried pixel."
        )),
        ("longitude", LiteralData(
            'longitude', float, title="Longitude",
            allowed_values=AllowedRange(-180.0, 180.0, 'closed', dtype=float),
            abstract="Longitude of the queried pixel."
        )),
    ]

    outputs = [
        ("pixel", LiteralData(
            "pixel", str, title="Queried pixel value",
            abstract=(
                "Comma separated list of band values the queried pixel. "
                "An empty string is returned if the queried location is "
                "not within the image extent."
            ),
        )),
    ]

    def execute(self, coverage_id, latitude, longitude, **params):
        logger = getLogger("damats.processes.get_pixel_value")
        try:
            coverage = RectifiedDataset.objects.get(identifier=coverage_id)
        except RectifiedDataset.DoesNotExist:
            raise InvalidInputValueError(
                "coverage", "Invalid coverage identifier!"
            )
        pixel_values = []
        for data_item in coverage.data_items.all():
            if data_item.semantic.startswith("bands"):
                #TODO: add data items' connectors
                logger.info("%s: %s" % (data_item.semantic, data_item.location))
                try:
                    pixel_values.extend(extract_pixel_value(
                        data_item.location, latitude, longitude
                    ))
                except OutOfExtent:
                    return ""
                    #raise InvalidInputValueError(
                    #    "latitude,longitude",
                    #    "Location outside of the image extent!"
                    #)
        return ",".join("%.18g" % v for v in pixel_values)
