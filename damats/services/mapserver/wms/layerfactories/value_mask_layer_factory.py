#-------------------------------------------------------------------------------
#
# Project: EOxServer <http://eoxserver.org>
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

from eoxserver.contrib.mapserver import (
    Layer, classObj as Class, styleObj as Style, colorObj as Color
)
from eoxserver.resources.coverages import models

from eoxserver.services.mapserver.wms.layerfactories.base import (
    BaseCoverageLayerFactory, BaseStyleMixIn,
)

class ValueMaskLayerFactory(BaseCoverageLayerFactory):
    """ Value mask hides all pixels which not of the desired pixel value."""
    handles = (models.RectifiedDataset, models.RectifiedStitchedMosaic)
    suffixes = ("_value_mask",)
    requires_connection = True

    COLORS = dict((n, (r, g, b)) for n, r, g, b in BaseStyleMixIn.STYLES)
    DEFAULT_COLOR = 'black'

    def generate(self, eo_object, group_layer, suffix, options):
        coverage = eo_object.cast()
        name = eo_object.identifier + "_value_mask"
        layer = Layer(name)
        layer.setMetaData("ows_title", name)
        layer.setMetaData("wms_label", name)
        layer.addProcessing("CLOSE_CONNECTION=CLOSE")

        coverage = eo_object.cast()

        request = options.get("request", {})
        value = request.get("mask_value", "0")
        color = self.COLORS[request.get("mask_style", self.DEFAULT_COLOR)]
        if value.startswith("!"):
            expression = "([pixel] != %g)" % float(value[1:])
        else:
            expression = "([pixel] == %g)" % float(value)

        class_ = Class()
        class_.setExpression(expression)
        style = Style()
        style.color = Color(*color)
        class_.insertStyle(style)
        layer.insertClass(class_)

        yield (layer, coverage.data_items.all())


    def generate_group(self, name):
        return Layer(name)
