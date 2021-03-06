#-------------------------------------------------------------------------------
#
#  Export Corine Land Cover snapshot.
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
from collections import OrderedDict
from django.conf import settings
from eoxserver.services.ows.wps.parameters import (
    LiteralData, ComplexData, AllowedRange, FormatBinaryRaw, Reference,
)
from damats.processes.sits_processor import SITSProcessor
from damats.webapp.views_time_series import get_coverages, SELECTION_PARSER
from damats.util.results import register_result
from damats.util.imports import import_object
from damats.util.clc.rasterize import rasterize_shapes
from damats.processes.utils import download_coverages

SITS_DIR = "sits" # path must be with respect to the current workspace
LC_DATASETS = OrderedDict(
    (item['title'], item) for item in settings.DAMATS_LAND_COVER_DATASETS
)
WCS_URL = settings.DAMATS_WCS_URL #"http://127.0.0.1:80/eoxs/ows?"


class RasterizeSITSLandCover(SITSProcessor):
    """ Auxiliary process exporting the SITS images' subsets. """
    identifier = "DAMATS:RasterizeSITSLandCover"
    title = "Rasterize SIST Land Cover"

    inputs = SITSProcessor.inputs + [
        ('lc_source', LiteralData(
            'land_cover_dataset', str, optional=False,
            default=iter(LC_DATASETS).next(), allowed_values=tuple(LC_DATASETS),
            title="Land Cover Dataset",
            abstract="Reference land cover vector dataset."
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
                "An image containing indices of the reference land cover "
                "classes."
            ), formats=(FormatBinaryRaw('image/tiff'))
        )),
    ]

    def process_sits(self, job, sits, lc_source, scaling_factor, interp_method,
                     context, **options):
        # parse selection
        selection = SELECTION_PARSER.parse(
            json.loads(sits.selection or '{}')
        )
        # parse land cover dataset
        lc_dataset = LC_DATASETS[lc_source]

        # get list of the contained coverages
        coverages = [
            cov_obj.identifier for cov_obj in
            get_coverages(sits.eoobj).order_by('begin_time', 'identifier')[:1]
        ]

        context.update_progress(0, "Retrieving the template raster.")

        # download the coverages
        images = download_coverages(
            WCS_URL, coverages, selection, SITS_DIR, context.logger,
            scaling_factor, interp_method,
        )

        context.update_progress(20, "Vector dataset rasterization.")

        # rasterize the reference land cover
        identifier = "%s_%s" % (context.identifier, lc_dataset['identifier'])
        filename = "%s.tif" % identifier

        rasterize_shapes(
            images[0],
            filename,
            lc_dataset['path'],
            lc_dataset['layer'],
            import_object(lc_dataset['classes']),
            lc_dataset['attrib']
        )

        filename, url = context.publish(filename)

        # create job result if possible
        if job is not None:
            register_result(
                job, "indices", "Class indices", identifier,
                filename, "classmap:uint8", visible=False,
                # begin_time, end_time,
            )

        return {
            "output_indices": Reference(
                filename, url, **options["output_indices"]
            ),
        }
