#-------------------------------------------------------------------------------
#
#  NDK-LDA algorithm WPS process wrapper
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
from damats.util.imports import import_object
from damats.util.clc.rasterize import rasterize_shapes
from damats.util.clc.statistics import write_class_statistics
from damats_algs.ndk_lda import ndk_lda_wrapper

SITS_DIR = "sits" # path must be with respect to the current workspace
LC_DATASETS = OrderedDict(
    (item['title'], item) for item in settings.DAMATS_LAND_COVER_DATASETS
)
WCS_URL = settings.DAMATS_WCS_URL #"http://127.0.0.1:80/eoxs/ows?"


class ProcessNDKLDA(SITSProcessor):
    """ SITS analysis using N-Dimensional K-means change detection and
    Latent Dirichlet Allocation (LDA) algorithm.
    """
    identifier = "DAMATS:NDKLDA"
    title = "N-Dimensional K-means with Latent Dirichlet Allocation (NDK-LDA)"

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
        ('lc_reference', LiteralData(
            'land_cover_dataset', str, optional=False,
            default=iter(LC_DATASETS).next(), allowed_values=tuple(LC_DATASETS),
            title="Reference Land Cover",
            abstract="Reference land cover vector dataset."
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
            'ndk_binary_changes', title="List of URLs",
            abstract="Plain text URL list of the binary changes.",
            formats=(FormatText('text/plain'))
        )),
        ("output_indices", ComplexData(
            'indices', title="Class Indices (Tiff Image)", abstract=(
                "An image containing indices of the calculated change classes."
            ), formats=(FormatBinaryRaw('image/tiff'))
        )),
        ("output_land_cover", ComplexData(
            'land_cover', title="Class Indices (Tiff Image)", abstract=(
                "An image containing indices of the reference land cover "
                "classes."
            ), formats=(FormatBinaryRaw('image/tiff'))
        )),
        ("output_statistics", ComplexData(
            'statistics', title="Class Statistic (TSV)", abstract=(
                "Tab separated values table containing the pixel statistic "
                " with respect to the reference land cover."
            ), formats=(FormatBinaryRaw('text/tab-separated-values'))
        )),
    ]

    def process_sits(self, job, sits, nclasses, nclusters, patch_size,
                     scaling_factor, interp_method, lc_reference,
                     context, **options):
        # parse selection
        selection = SELECTION_PARSER.parse(
            json.loads(sits.selection or '{}')
        )
        # parse land cover dataset
        lc_dataset = LC_DATASETS[lc_reference]

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

        identifier_cls = "%s_NDK_LDA" % context.identifier
        filename_cls = "%s.tif" % identifier_cls

        # detect various floating-point errors and always throw an exception
        numpy_error_settings = seterr(divide='raise', invalid='raise')
        try:
            ndk_output = ndk_lda_wrapper(
                [(scene,) for scene in sits_content],
                nclusters, nclasses, patch_size,
                # write output to the current workspace
                "", "%s_NDK_" % context.identifier, filename_cls,
                cpu_nr=1, custom_logger=context.logger,
                status_callback=context.update_progress,
            )
        finally:
            # restore the original behaviour
            seterr(**numpy_error_settings)

        context.update_progress(95, "Rasterizing the reference land cover.")

        # rasterize the reference land cover
        identifier_rlc = "%s_%s" % (context.identifier, lc_dataset['identifier'])
        filename_rlc = "%s.tif" % identifier_rlc

        classes = import_object(lc_dataset['classes'])
        rasterize_shapes(
            sits_content[0], filename_rlc, lc_dataset['path'],
            lc_dataset['layer'], classes, lc_dataset['attrib']
        )

        context.update_progress(98, "Calculating statistics.")

        # produce the final statistics
        filename_stat = "%s_NDK_LDA_%s_statistics.tsv" % (
            context.identifier, lc_dataset['identifier']
        )
        write_class_statistics(
            filename_stat, filename_cls, filename_rlc, nclasses, classes,
        )

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
                        job, "ndk_binary_change[%d]" % idx,
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


        # publish LDA outputs
        filename_cls, url_cls = context.publish(filename_cls)
        filename_rlc, url_rlc = context.publish(filename_rlc)
        filename_stat, url_stat = context.publish(filename_stat)

        # create job results if possible
        if job is not None:
            register_result(
                job, "ndk_cumulative_change", "Cumulative change",
                extless_basename(filename_ndk_cc, '.tif'),
                filename_ndk_cc, "Grayscale", visible=False,
            )
            register_result(
                job, "indices", "Class indices", identifier_cls,
                filename_cls, "classmap:uint8", visible=False,
            )
            register_result(
                job, "land_cover", "Reference land cover", identifier_rlc,
                filename_rlc, "classmap:uint8", visible=False,
            )

        return {
            "output_cumulative_change": Reference(
                filename_ndk_cc, url_ndk_cc,
                **options["output_cumulative_change"]
            ),
            "output_binary_changes": Reference(
                filename_ndk_bc, url_ndk_bc, **options["output_binary_changes"]
            ),
            "output_indices": Reference(
                filename_cls, url_cls, **options["output_indices"]
            ),
            "output_land_cover": Reference(
                filename_rlc, url_rlc, **options["output_land_cover"]
            ),
            "output_statistics": Reference(
                filename_stat, url_stat, **options["output_statistics"]
            ),
        }
