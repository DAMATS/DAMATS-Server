#-------------------------------------------------------------------------------
#
#  Utilities shared by the WPS processes.
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
# pylint: disable=too-many-arguments, too-many-locals

from os import makedirs
from os.path import join
from contextlib import closing
from shutil import copyfileobj
from osgeo import gdal; gdal.UseExceptions() # pylint: disable=multiple-statements
from damats.util.wcs_client import WCS20Client

CHUNK_SIZE = 1024 * 1024 # 1MiB


def update_object(obj, **kwargs):
    """ Update Django model instance"""
    for key, value in kwargs.iteritems():
        setattr(obj, key, value)
    obj.save()


def get_header(header, default=None):
    """ Second order function returning function extracting header from
    the HTTP request.
    """
    return get_meta("HTTP_" + header.upper().replace("-", "_"), default)


def get_meta(meta_key, default=None):
    """ Second order function returning function extracting meta field from
    the Django HTTP request.
    """
    def _get_meta(request):
        """ Function extracting META field from the HTTP request. """
        return request.META.get(meta_key, default)
    return _get_meta


def download_coverages(url, coverages, selection, output_dir, logger,
                       scaling_factor=1.0, interp_method='nearest-neighbour'):
    """ Download coverages to the given output directory. """
    base_options = {
        'format': 'image/tiff',
        'interpolation': interp_method,
        'geotiff': {
            'compression': 'None',
            'tiling': 'true',
            'tilewidth': 256,
            'tileheight': 256,
        }
    }

    # options of the first (master) image
    options = dict(base_options)
    aoi = selection['aoi']
    options.update({
        'subsetting_srid': 4326,
        'subset': {
            'x': (aoi['left'], aoi['right']),
            'y': (aoi['bottom'], aoi['top']),
        },
        'scale': float(scaling_factor),
    })

    # download the coverages
    makedirs(output_dir)
    images = []
    client = WCS20Client(url)
    for idx, coverage in enumerate(coverages):
        logger.debug("COVERAGE: %s", coverage)

        if idx == 0:
            # query SRID of the master image
            options['output_srid'] = output_srid = (
                client.describe_coverage(coverage).srid
            )

        filename = join(output_dir, "%s.tif" % coverage)
        with closing(client.get_coverage(coverage, **options)) as fsrc:
            with file(filename, "wb") as fdst:
                copyfileobj(fsrc, fdst, CHUNK_SIZE)
        logger.info("downloaded %s", filename)
        images.append(filename)

        if idx == 0:
            # set options for the slave images
            options = dict(base_options)
            options.update({
                'subsetting_srid': output_srid,
                'output_srid': output_srid,
            })
            options.update(get_size_and_subset(filename))

    return images


def get_size_and_subset(image):
    """ Get size and subset parameters from the extent of an existing image. """
    dataset = gdal.Open(image)
    trn = dataset.GetGeoTransform()

    size_x = dataset.RasterXSize
    size_y = dataset.RasterYSize
    transform = lambda x, y: (
        trn[0] + trn[1] * x + trn[2] * y,
        trn[3] + trn[4] * x + trn[5] * y,
    )
    x_ul, y_ul = transform(0, 0)
    x_br, y_br = transform(size_x, size_y)

    return {
        'size': {'x': size_x, 'y': size_y},
        'subset': {'x': (x_ul, x_br), 'y': (y_br, y_ul)},
    }
