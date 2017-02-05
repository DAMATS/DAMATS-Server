#-------------------------------------------------------------------------------
#
# Coverage registration helpers.
#
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
# pylint: disable=missing-docstring
import json
from logging import getLogger
from osgeo import gdal, osr
from django.contrib.gis.geos import LinearRing, Polygon, MultiPolygon
from eoxserver.backends.models import DataItem
from eoxserver.resources.coverages.models import (
    RangeType, RectifiedDataset, Collection,
)
from eoxserver.resources.coverages.management.commands import (
    nested_commit_on_success,
)
from damats.webapp.models import Result

SR_WGS84 = osr.SpatialReference()
SR_WGS84.ImportFromEPSG(4326)


@nested_commit_on_success
def register_result(job, identifier, name, coverage_id, image_path,
                    range_type_name, collections=None, description=None,
                    logger=None, **kwargs):
    """ Register result image as a plain coverage.
        Optional keyword arguments are:
            visible (bool)
            begin_time (datetime.datetime)
            end_time (datetime.datetime)
    """
    logger = logger or getLogger(__name__)
    #job = Job.objects.get(identifier=job_id)
    #job = Job.objects.get(wps_job_id=wps_job_id)
    selection_toi = json.loads(job.time_series.selection)['toi']

    metadata = extract_image_info(image_path)
    metadata.update({
        'begin_time': selection_toi['start'],
        'end_time': selection_toi['end'],
    })
    metadata.update(kwargs)

    range_type = RangeType.objects.get(name=range_type_name)
    coverage = register_coverage(
        coverage_id, image_path, range_type, collections, logger, **metadata
    )

    result = Result()
    result.job = job
    result.eoobj = coverage
    result.identifier = identifier
    result.name = name
    result.description = description
    result.save()

    logger.info("Result %s created.", str(result))

    return result


def register_coverage(coverage_id, image_path, range_type, collections=None,
                      logger=None, **metadata):
    """ Register image as a plain coverage.
        Mandatory keyword arguments:
            size_x (int)
            size_y (int)
            srid (int)
            extent (tuple[4])
            footprint (MultiPolygon)
        Optional keyword arguments are:
            visible (bool)
            begin_time (datetime.datetime)
            end_time (datetime.datetime)
    """
    logger = logger or getLogger(__name__)
    coverage = RectifiedDataset()
    coverage.identifier = coverage_id
    coverage.size_x = metadata['size_x']
    coverage.size_y = metadata['size_y']
    coverage.srid = metadata['srid']
    coverage.extent = metadata['extent']
    coverage.footprint = metadata['footprint']
    coverage.begin_time = metadata.get('begin_time', None)
    coverage.end_time = metadata.get('end_time', None)
    coverage.visible = metadata.get('visible', True)
    coverage.range_type = range_type
    coverage.full_clean()
    coverage.save()

    data_item = DataItem(
        location=image_path, semantic="bands[1]",
        format="", storage=None, package=None,
    )
    data_item.dataset = coverage
    data_item.full_clean()
    data_item.save()

    logger.info("%s registered.", str(coverage))

    for collection_id in collections or ():
        try:
            collection = Collection.objects.get(collection_id).cast()
        except Collection.DoesNotExist:
            continue
        collection.insert(coverage)
        logger.info("%s linked to %s", str(coverage), str(collection))

    return coverage


def extract_image_info(image_path):
    """ Extract image metadata. """
    dataset = gdal.Open(image_path)
    spref = osr.SpatialReference(dataset.GetProjection())
    if spref.GetAuthorityName(None) != 'EPSG':
        return {
            "size_x": dataset.RasterXSize,
            "size_y": dataset.RasterYSize,
        }
    srid = int(spref.GetAuthorityCode(None))
    extent, outline = extract_extent_and_outline(dataset, 5, 5)
    return  {
        "size_x": dataset.RasterXSize,
        "size_y": dataset.RasterYSize,
        "srid": srid,
        "extent": extent,
        "footprint": assure_multipolygon(outline_to_geom(outline)),
    }


def extract_extent_and_outline(dataset, npx=1, npy=1):
    """ Extract rectangular outline of the image in WGS84. """
    # pylint: disable=invalid-name, too-many-locals
    size_x = dataset.RasterXSize
    size_y = dataset.RasterYSize
    x00, dxx, dxy, y00, dyx, dyy = dataset.GetGeoTransform()
    corners = [
        (x00 + dxx*x + dxy*y, y00 + dyx*x + dyy*y)
        for x, y in [(0, 0), (size_x, 0), (size_x, size_y), (0, size_y), (0, 0)]
    ]
    outline = []
    npx, npy = max(npx, 1), max(npy, 1)
    npl = (npx, npy, npx, npy)
    for nstep, (x0, y0), (x1, y1) in (
            (npl[i], corners[i], corners[i+1]) for i in xrange(4)
        ):
        rstep = 1.0 / nstep
        dx, dy = rstep*(x1 - x0), rstep*(y1 - y0)
        outline.append((x0, y0))
        for step in xrange(1, nstep):
            outline.append((x0 + dx*step, y0 + dy*step))
    outline.append(outline[0])
    # coordinate conversion
    ct_ = osr.CoordinateTransformation(
        osr.SpatialReference(dataset.GetProjection()), SR_WGS84
    )
    outline = [
        ct_.TransformPoint(float(x), float(y))[:2] for x, y in outline
    ]
    return points_to_extent(corners), outline


def points_to_extent(outline):
    """ Extract extent of the outline. """
    # pylint: disable=invalid-name
    x = [x for x, _ in outline]
    y = [y for _, y in outline]
    return [min(x), min(y), max(x), max(y)]


def outline_to_geom(outline, srid=4326):
    """ Convert single polygon outline (no-inner rings) to polygon. """
    return Polygon(LinearRing(outline), srid=srid)


def assure_multipolygon(geom):
    """" Make sure the geometry is multi-polygon. """
    if isinstance(geom, MultiPolygon):
        return geom
    elif isinstance(geom, Polygon):
        return MultiPolygon(geom)
    else:
        raise ValueError("Invalid planar geometry!")
