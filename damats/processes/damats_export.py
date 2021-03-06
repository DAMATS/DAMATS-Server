#-------------------------------------------------------------------------------
#
#  Export SITS subset images.
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
# pylint: disable=too-many-arguments,too-many-locals


import json
from cStringIO import StringIO
from eoxserver.services.ows.wps.parameters import (
    LiteralData, ComplexData, AllowedRange, CDFileWrapper, FormatText,
    Reference,
)
from damats.processes.sits_processor import SITSProcessor
from damats.webapp.views_time_series import get_coverages, SELECTION_PARSER
from damats.processes.utils import download_coverages

# TODO: fix the base WCS URL configuration
WCS_URL = "http://127.0.0.1:80/eoxs/ows?"
SITS_DIR = "sits" # path must be with respect to the current workspace


class ExportSITS(SITSProcessor):
    """ Auxiliary process exporting the SITS images' subsets. """
    identifier = "DAMATS:ExportSITS"
    title = "SIST Export"

    inputs = SITSProcessor.inputs + [
        ("scaling_factor", LiteralData(
            'scaling_factor', float, optional=True, default=1.0,
            allowed_values=AllowedRange(0.0, 1.0, 'open-closed', dtype=float),
            title="Image Scaling Factor",
            abstract="This parameter defines the image downscaling factor."
        )),
        ("interp_method", LiteralData(
            'interp_method', str, optional=True,
            default='nearest-neighbour', allowed_values=(
                'average', 'nearest-neighbour', 'bilinear',
                'cubic', 'cubic-spline', 'lanczos', 'mode',
            ), title="Interpolation Method",
            abstract="Interpolation method used by the image re-sampling."
        )),
    ]

    outputs = [
        ("output", ComplexData(
            'index', title="List of URLs",
            abstract="Plain text URL list of the exported images.",
            formats=(FormatText('text/plain'))
        )),
    ]

    def process_sits(self, sits, scaling_factor, interp_method, context,
                     output, **kwargs):
        # parse selection
        selection = SELECTION_PARSER.parse(
            json.loads(sits.selection or '{}')
        )

        # get list of the contained coverages
        coverages = [
            cov_obj.identifier for cov_obj in
            get_coverages(sits.eoobj).order_by('begin_time', 'identifier')
        ]

        context.update_progress(0, "Publishing the data subsets.")

        # download the coverages
        images = download_coverages(
            WCS_URL, coverages, selection, SITS_DIR, context.logger,
            scaling_factor, interp_method,
        )

        # publish the image subsets
        #output_fobj = StringIO()
        #output_fobj.write("coverageIdentifier\tlocalFilename\tdownloadURL\r\n")
        #for coverage, image in zip(coverages, images):
        #    filename, url = context.publish(image)
        #    output_fobj.write("%s\t%s\t%s\r\n" % (coverage, filename, url))
        #return CDFileWrapper(output_fobj, **output)

        # save the manifest
        manifest_filename = "manifest.txt"
        with file(manifest_filename, "wb") as fobj:
            for coverage, image in zip(coverages, images):
                _, url = context.publish(image)
                fobj.write("%s\r\n" % url)

        # publish the manifest
        manifest_filename, url = context.publish(manifest_filename)

        context.logger.info("%s" % output)
        return Reference(manifest_filename, url, **output)
