#-------------------------------------------------------------------------------
#
#  NDK algorithm WPS process wrapper
#
# Project: DAMATS
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
# pylint: disable=too-few-public-methods, unused-argument
# pylint: disable=too-many-arguments, too-many-locals

import json
from collections import OrderedDict
from numpy import seterr
from django.conf import settings
from eoxserver.services.ows.wps.parameters import (
    LiteralData, ComplexData, AllowedRange, Reference,
    FormatBinaryRaw, FormatText,
)
from damats.processes.sits_processor import SITSProcessor
from damats.webapp.views_time_series import get_coverages, SELECTION_PARSER
from damats.processes.utils import download_coverages, extless_basename
from damats.util.results import register_result
from damats_algs.ndk import ndk_wrapper

SITS_DIR = "sits" # path must be with respect to the current workspace
LC_DATASETS = OrderedDict(
    (item['title'], item) for item in settings.DAMATS_LAND_COVER_DATASETS
)
WCS_URL = settings.DAMATS_WCS_URL #"http://127.0.0.1:80/eoxs/ows?"


class ProcessNDK(SITSProcessor):
    """ SITS change detection using N-Dimensional K-means (NDK) algorithm. """
    identifier = "DAMATS:NDK"
    title = "N-Dimensional K-means (NDK)"

    inputs = SITSProcessor.inputs + [
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
        ("output_cumulative_change", ComplexData(
            'ndk_cumulative_change', title="Cumulative Change (Tiff Image)",
            abstract=(
                "NDK Cumulative change."
            ), formats=(FormatBinaryRaw('image/tiff'))
        )),
        ("output_binary_changes", ComplexData(
            'ndk_binary_changes', title="Binary changes (URL list)",
            abstract="Plain text URL list of the binary changes.",
            formats=(FormatText('text/plain'))
        )),
    ]

    def process_sits(self, job, sits, scaling_factor, interp_method,
                     context, **options):

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

        # detect various floating-point errors and always throw an exception
        numpy_error_settings = seterr(divide='raise', invalid='raise')
        try:
            ndk_output = ndk_wrapper(
                [(scene,) for scene in sits_content],
                # write output to the current workspace
                "", "%s_NDK_" % context.identifier,
                status_callback=context.update_progress,
            )
        finally:
            # restore the original behaviour
            seterr(**numpy_error_settings)

        # write the manifest of the binary change images
        filename_ndk_bc = (
            "%s_NDK_binary_changes_manifest.txt" % context.identifier
        )
        with file(filename_ndk_bc, "wb") as fobj:
            for idx, src_path in enumerate(ndk_output["ndk_binary_changes"]):
                dst_path, url = context.publish(src_path)
                fobj.write("%s\r\n" % url)
                if job is not None:
                    register_result(
                        job, "ndk_binary_changes[%d]" % idx,
                        "Binary change #%d" % idx,
                        extless_basename(dst_path, '.tif'),
                        dst_path, "Grayscale", visible=False,
                    )

        # publish the manifest of the binary change images
        filename_ndk_bc, url_ndk_bc = context.publish(filename_ndk_bc)

        # publish the cumulative change image
        filename_ndk_cc, url_ndk_cc = context.publish(
            ndk_output["ndk_cumulative_change"]
        )

        # create job results if possible
        if job is not None:
            register_result(
                job, "ndk_cumulative_change", "Cumulative change",
                extless_basename(filename_ndk_cc, '.tif'),
                filename_ndk_cc, "Grayscale", visible=False,
            )

        return {
            "output_cumulative_change": Reference(
                filename_ndk_cc, url_ndk_cc,
                **options["output_cumulative_change"]
            ),
            "output_binary_changes": Reference(
                filename_ndk_bc, url_ndk_bc, **options["output_binary_changes"]
            ),
        }
