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
# pylint: disable=too-many-arguments, too-many-locals

import json
import sys
from numpy import seterr
from eoxserver.services.ows.wps.parameters import (
    LiteralData, ComplexData, AllowedRange, Reference, FormatBinaryRaw,
)
from damats.processes.sits_processor import SITSProcessor
from damats.webapp.views_time_series import get_coverages, SELECTION_PARSER
from damats.processes.utils import download_coverages

#TODO fix the path configuration
sys.path.append("/srv/damats/algs")

from lda.lda2 import lda_wrapper

# TODO: fix the base WCS URL configuration
WCS_URL = "http://127.0.0.1:80/eoxs/ows?"
SITS_DIR = "sits" # path must be with respect to the current workspace


class ProcessLDA(SITSProcessor):
    """ SITS analysis using Latent Dirichlet Allocation (LDA) """
    identifier = "DAMATS:LDA"
    title = "Latent Dirichlet Allocation (LDA)"

    inputs = SITSProcessor.inputs + [
        ("nclasses", LiteralData(
            'nclasses', int, optional=True, default=10,
            allowed_values=AllowedRange(2, 64, dtype=int),
            title="Number of Classes",
        )),
        ("nclusters", LiteralData(
            'nclusters', int, optional=True, default=100,
            allowed_values=AllowedRange(100, 200, dtype=int),
            title="Number of Clusters",
        )),
        ("patch_size", LiteralData(
            'patch_size', int, optional=True, default=20,
            allowed_values=(20, 50, 100),
            title="Patch Size",
        )),
        ("scaling_factor", LiteralData(
            'scaling_factor', float, optional=True, default=1.0,
            allowed_values=AllowedRange(0.0, 1.0, 'open-closed', dtype=float),
            title="Image Scaling Factor",
            abstract="Image downscaling factor. Set to 1 for full resolution."
        )),
        ("interp_method", LiteralData(
            'interp_method', str, optional=True,
            default='nearest-neighbour', allowed_values=(
                'nearest-neighbour', 'average', 'bilinear',
                'cubic', 'cubic-spline', 'lanczos', 'mode',
            ), title="Interpolation Method",
            abstract="Interpolation method used by the image re-sampling."
        )),
    ]

    outputs = [
        ("output_indices", ComplexData(
            'indices', title="Class Indices (Tiff Image)", abstract=(
                "An image containing indices of the calculated change classes."
            ), formats=(FormatBinaryRaw('image/tiff'))
        )),
    ]

    def process_sits(self, sits, nclasses, nclusters, patch_size,
                     scaling_factor, interp_method, context, **options):
        # parse selection
        selection = SELECTION_PARSER.parse(
            json.loads(sits.selection or '{}')
        )

        # get list of the contained coverages
        coverages = [
            cov_obj.identifier for cov_obj in
            get_coverages(sits.eoobj).order_by('begin_time', 'identifier')
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

        # detect various floating-point errors and always throw an exception
        numpy_error_settings = seterr(divide='raise', invalid='raise')
        try:
            lda_wrapper(
                sits_content, nclusters, nclasses,
                patch_size, filename=filename,
                cpu_nr=1, custom_logger=context.logger,
                status_callback=context.update_progress,
            )
        finally:
            # restore the original behaviour
            seterr(**numpy_error_settings)

        filename, url = context.publish(filename)

        return {
            "output_indices": Reference(
                filename, url, **options["output_indices"]
            ),
        }
