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
from os.path import join, dirname, abspath
from urllib2 import urlopen
from contextlib import closing
from shutil import copyfileobj
from eoxserver.core import Component, implements
from eoxserver.services.ows.wps.interfaces import ProcessInterface
from eoxserver.services.ows.wps.exceptions import InvalidInputValueError
from eoxserver.services.ows.wps.parameters import LiteralData, AllowedRange
from damats.webapp.models import TimeSeries
from damats.webapp.views_time_series import get_coverages, SELECTION_PARSER
from lda.lda2 import lda_wrapper


OUTPUT = "lda.tif"
SITS_DIR = "sits" # path must be with respect to the current workspace
CHUNK_SIZE = 1024 * 1024 # 1MiB

# TODO: fix the base WCS URL configuration
WCS_URL = "http://127.0.0.1:80/eoxs/ows?"

def get_wcs_request(covid, aoi):
    """ Get the WCS 2.0 HTTP/POST request. """

    def _request_():
        yield '<?xml version="1.0"?>'
        yield '<wcs:GetCoverage service="WCS" version="2.0.0"'
        yield '  xmlns:wcs="http://www.opengis.net/wcs/2.0"'
        yield '  xmlns:wcscrs="http://www.opengis.net/wcs/crs/1.0"'
        yield '  xmlns:wcsmask="http://www.opengis.net/wcs/mask/1.0"'
        yield '  xmlns:wcsrsub="http://www.opengis.net/wcs/range-subsetting/1.0">'
        yield '<wcs:CoverageId>%s</wcs:CoverageId>' % covid
        yield '<wcs:format>image/tiff</wcs:format>'
        yield '<wcs:DimensionTrim>'
        yield '  <wcs:Dimension>x</wcs:Dimension>'
        yield '  <wcs:TrimLow>%.9g</wcs:TrimLow>' % aoi['left']
        yield '  <wcs:TrimHigh>%.9g</wcs:TrimHigh>' % aoi['right']
        yield '</wcs:DimensionTrim>'
        yield '<wcs:DimensionTrim>'
        yield '  <wcs:Dimension>y</wcs:Dimension>'
        yield '  <wcs:TrimLow>%.9g</wcs:TrimLow>' % aoi['bottom']
        yield '  <wcs:TrimHigh>%.9g</wcs:TrimHigh>' % aoi['top']
        yield '</wcs:DimensionTrim>'
        yield '<wcs:Extension><wcscrs:subsettingCrs>http://www.opengis.net/def/'\
              'crs/EPSG/0/4326</wcscrs:subsettingCrs></wcs:Extension>'
        yield '</wcs:GetCoverage>'

    return "\n".join(_request_())


def download(url, path, data=None, logger=None):
    """ Download file to the given path. """
    if logger:
        logger.debug('downloading %s from %s', path, url)
        if data:
            logger.debug('post payload:\n%s', data)

    with open(path, 'wb') as fdst:
        with closing(urlopen(url, data)) as fsrc:
            copyfileobj(fsrc, fdst, CHUNK_SIZE)

    if logger:
        logger.info("downloaded %s", path)

    return path


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
            'nclasses', int, optional=True,
            title="number of classes",
            abstract="Optional number of classes parameter.",
            allowed_values=AllowedRange(2, 64, dtype=int), default=10,
        )),
        ("nclusters", LiteralData(
            'nclusters', int, optional=True,
            title="number of clusters",
            abstract="Optional number of clusters parameter.",
            allowed_values=AllowedRange(100, 200, dtype=int), default=100,
        )),
        ("patch_size", LiteralData(
            'patch_size', int, optional=True,
            title="patch size",
            abstract="Optional patch size parameter.",
            allowed_values=(20, 50, 100), default=20,
        )),
    ]

    outputs = [
        ("debug_output", str), # to be removed
    ]

    @staticmethod
    def execute(sits, nclasses, nclusters, patch_size, context, **kwargs):
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
        makedirs(SITS_DIR)
        sits_content = []
        output_urls = []
        for cid in coverages:
            logger.debug("COVERAGE: %s", cid)
            path = join(SITS_DIR, "%s.tif" % cid)
            download(WCS_URL, path, data=get_wcs_request(cid, selection['aoi']))
            sits_content.append(path)

        # execute the algorithm
        context.update_progress(5, "Executing the algorithm.")

        filename = "%s_lda.tif" % context.identifer

        lda_wrapper(
            sits_content, nclasses, nclusters, patch_size, filename=filename,
            cpu_nr=1, custom_logger=context.logger,
            status_callback=context.update_progress,
        )

        filename, url = context.publish(OUTPUT)

        return str((filename, url))
