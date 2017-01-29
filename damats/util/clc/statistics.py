#-------------------------------------------------------------------------------
#
#  DAMATS - Corine Land Cover statistic
#
# Project: EOxServer <http://eoxserver.org>
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

from numpy import zeros, prod, ravel_multi_index, bincount
from gdalconst import GA_ReadOnly
from osgeo import gdal; gdal.UseExceptions()


def write_class_statistics(fout, img_class, img_class_ref, n_class,
                           ref_classes):
    """ Calculate the class pixel statistics and relation to the reference
    classes and save the result to a file.
    """
    counts = calculate_2d_class_histogram(
        img_class, img_class_ref, n_class, max(c['index'] for c in ref_classes)
    )
    if isinstance(fout, basestring):
        with open(fout, "wb") as _fout:
            _save_class_statistics(_fout, counts, ref_classes)
    else:
        _save_class_statistics(fout, counts, ref_classes)


def _save_class_statistics(fout, counts, classes):
    """ Write output static to a file. """
    n_class = counts.shape[0] - 1
    extended_counts = zeros(
        (counts.shape[0] + 1, counts.shape[1] + 1), 'int64'
    )
    extended_counts[0, 0] = counts.sum()
    extended_counts[0, 1:] = counts.sum(axis=0)
    extended_counts[1:, 0] = counts.sum(axis=1)
    extended_counts[1:, 1:] = counts

    extended_counts = extended_counts.T

    fout.write("\t".join(["", "Total"] + [
        "Class #%i" % idx for idx in xrange(n_class)
    ] + ['Other']))
    fout.write("\r\n")
    fout.write("Pixel Count\t")
    fout.write("\t".join("%d" % v for v in extended_counts[0, :]))
    fout.write("\r\n")

    for class_ in classes:
        label = "%s %s\t" % (class_['attrib'].values()[0], class_['title'])
        idx = class_['index']
        fout.write(label)
        fout.write("\t".join("%d" % v for v in extended_counts[idx+1, :]))
        fout.write("\r\n")
    fout.write("Other\t")
    fout.write("\t".join("%d" % v for v in extended_counts[-1, :]))
    fout.write("\r\n")


def calculate_2d_class_histogram(img_class, img_class_ref,
                                 n_class=256, n_class_ref=256):
    """ Evaluate 2D class histogram for two given class images.
    Each bin of the histogram corresponds to a relation between
    the class image and the reverence class image.
    """
    # open datasets
    ds_class = gdal.Open(img_class, GA_ReadOnly)
    ds_class_ref = gdal.Open(img_class_ref, GA_ReadOnly)

    # check the image parameters
    if (
        (ds_class.RasterXSize != ds_class_ref.RasterXSize) or
        (ds_class.RasterYSize != ds_class_ref.RasterYSize)
    ):
        raise ValueError("Image size mismatch!")

    if (ds_class.RasterCount != 1) or (ds_class_ref.RasterCount != 1):
        raise ValueError("Band count mismatch!")

    if (
        (ds_class.GetRasterBand(1).DataType != gdal.GDT_Byte) or
        (ds_class_ref.GetRasterBand(1).DataType != gdal.GDT_Byte)
    ):
        raise ValueError("Unexpected image datatype!")

    # calculate the pixel statistics
    return _get_raw_pixel_counts(
        zeros((n_class + 1, n_class_ref + 1), 'int64'),
        ds_class.GetRasterBand(1),
        ds_class_ref.GetRasterBand(1)
    )


def bincount_multivar(multi_index, dims=(256, 256), order='C', mode='clip'):
    """ Multi-variate analogy of the `numpy.bincount`. """
    return bincount(
        ravel_multi_index(multi_index, dims, mode=mode, order=order),
        minlength=prod(dims)
    ).reshape(dims)


def _get_raw_pixel_counts(counts, band1, band2, tile_size_x=256, tile_size_y=256):
    """ Read data from two bands and yield the pixel values. """
    size_x, size_y = band1.XSize, band1.YSize
    ntile_x = 1 + (size_x - 1)//tile_size_x
    ntile_y = 1 + (size_y - 1)//tile_size_y
    for idx_y in xrange(ntile_y):
        for idx_x in xrange(ntile_x):
            offset_x = idx_x*tile_size_x
            offset_y = idx_y*tile_size_y
            tsize_x = min(tile_size_x, size_x - offset_x)
            tsize_y = min(tile_size_y, size_y - offset_y)
            data1 = band1.ReadAsArray(offset_x, offset_y, tsize_x, tsize_y)
            data2 = band2.ReadAsArray(offset_x, offset_y, tsize_x, tsize_y)
            counts += bincount_multivar(
                (data1.ravel(), data2.ravel()), dims=counts.shape,
            )
    return counts
