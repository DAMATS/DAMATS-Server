#-------------------------------------------------------------------------------
#
#  LDA algorithm WPS process wrapper
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
# pylint: disable=too-few-public-methods, unused-argument

import sys
#TODO fix the path configuration
sys.path.append("/srv/damats/algs")

import json
from os import makedirs
from os.path import join
from contextlib import closing
from shutil import copyfileobj
from osgeo import gdal; gdal.UseExceptions() # pylint: disable=multiple-statements
from eoxserver.core import Component, implements
from eoxserver.services.ows.wps.interfaces import ProcessInterface
from eoxserver.services.ows.wps.exceptions import InvalidInputValueError
from eoxserver.services.ows.wps.parameters import LiteralData, AllowedRange
from damats.webapp.models import TimeSeries
from damats.webapp.views_time_series import get_coverages, SELECTION_PARSER
from damats.util.wcs_client import WCS20Client
from lda.lda2 import lda_wrapper


#OUTPUT = "lda.tif"
SITS_DIR = "sits" # path must be with respect to the current workspace
CHUNK_SIZE = 1024 * 1024 # 1MiB

# TODO: fix the base WCS URL configuration
WCS_URL = "http://127.0.0.1:80/eoxs/ows?"


class ProcessLDA(Component):
    """ SITS analysis using Latent Dirichlet Allocation (LDA) """
    implements(ProcessInterface)

    synchronous = False
    asynchronous = True
    identifier = "DAMATS:LDA"
    title = "Latent Dirichlet Allocation (LDA)"
    metadata = {}
    profiles = ["DAMATS-SITS-processor"]

    inputs = [
        ("sits", LiteralData(
            'sits', str,
            title="Satellite Image Time Series (SITS)",
            abstract="Satellite Image Time Series (SITS) identifier."
        )),
        ("nclasses", LiteralData(
            'nclasses', int, optional=True, default=10,
            allowed_values=AllowedRange(2, 64, dtype=int),
            title="number of classes",
            abstract="Optional number of classes parameter.",
        )),
        ("nclusters", LiteralData(
            'nclusters', int, optional=True, default=100,
            allowed_values=AllowedRange(100, 200, dtype=int),
            title="number of clusters",
            abstract="Optional number of clusters parameter.",
        )),
        ("patch_size", LiteralData(
            'patch_size', int, optional=True, default=20,
            allowed_values=(20, 50, 100),
            title="patch size",
            abstract="Optional patch size parameter.",
        )),
        ("scaling_factor", LiteralData(
            'scaling_factor', float, optional=True, default=1.0,
            allowed_values=AllowedRange(0.0, 1.0, 'open-closed', dtype=float),
            title="Image scaling factor.",
            abstract="This parameter defines the image downscaling factor."
        )),
        ("interp_method", LiteralData(
            'interp_method', str, optional=True,
            default='nearest-neighbour', allowed_values=(
                'average', 'nearest-neighbour', 'bilinear',
                'cubic', 'cubic-spline', 'lanczos', 'mode',
            ), title="Interpolation method.",
            abstract="Interpolation method used by the image re-sampling."
        )),
    ]

    outputs = [
        ("debug_output", str), # to be removed
    ]

    @staticmethod
    def execute(sits, nclasses, nclusters, patch_size, context,
                scaling_factor, interp_method, **kwargs):
        """ This method holds the actual executed process' code. """
        logger = context.logger

        # get the time-series Django object
        try:
            sits_obj = TimeSeries.objects.get(eoobj__identifier=sits)
        except TimeSeries.DoesNotExist:
            raise InvalidInputValueError('sits')

        logger.debug("SITS: %s OK", sits)

        # parse selection
        selection = SELECTION_PARSER.parse(
            json.loads(sits_obj.selection or '{}')
        )

        # get list of the contained coverages
        coverages = [
            cov_obj.identifier for cov_obj in
            get_coverages(sits_obj.eoobj).order_by('begin_time', 'identifier')
        ]

        context.update_progress(0, "Preparing the inputs data subsets.")

        # download the coverages
        sits_content = download_coverages(
            WCS_URL, coverages, selection, SITS_DIR, context.logger,
            scaling_factor, interp_method,
        )

        # execute the algorithm
        context.update_progress(5, "Executing the algorithm.")

        filename = "%s_lda.tif" % context.identifier

        lda_wrapper(
            sits_content, nclasses, nclusters, patch_size, filename=filename,
            cpu_nr=1, custom_logger=context.logger,
            status_callback=context.update_progress,
        )

        filename, url = context.publish(filename)

        return str((filename, url))

#-------------------------------------------------------------------------------

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
            options.update()

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