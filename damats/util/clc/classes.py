#-------------------------------------------------------------------------------
#
#  DAMATS - Corine Land Cover Classes
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

CLC2012_CLASSES = [
    {
        "index": 1,
        "title": "Continuous urban fabric",
        "colour": (230, 0, 77, 255),
        "attrib": {"code_12": "111"},
    },
    {
        "index": 2,
        "title": "Discontinuous urban fabric",
        "colour": (255, 0, 0, 255),
        "attrib": {"code_12": "112"},
    },
    {
        "index": 3,
        "title": "Industrial or commercial units",
        "colour": (204, 77, 242, 255),
        "attrib": {"code_12": "121"},
    },
    {
        "index": 4,
        "title": "Road and rail networks and associated land",
        "colour": (204, 0, 0, 255),
        "attrib": {"code_12": "122"},
    },
    {
        "index": 5,
        "title": "Port areas",
        "colour": (230, 204, 204, 255),
        "attrib": {"code_12": "123"},
    },
    {
        "index": 6,
        "title": "Airports",
        "colour": (230, 204, 230, 255),
        "attrib": {"code_12": "124"},
    },
    {
        "index": 7,
        "title": "Mineral extraction sites",
        "colour": (166, 0, 204, 255),
        "attrib": {"code_12": "131"},
    },
    {
        "index": 8,
        "title": "Dump sites",
        "colour": (166, 77, 0, 255),
        "attrib": {"code_12": "132"},
    },
    {
        "index": 9,
        "title": "Construction sites",
        "colour": (255, 77, 255, 255),
        "attrib": {"code_12": "133"},
    },
    {
        "index": 10,
        "title": "Green urban areas",
        "colour": (255, 166, 255, 255),
        "attrib": {"code_12": "141"},
    },
    {
        "index": 11,
        "title": "Sport and leisure facilities",
        "colour": (255, 230, 255, 255),
        "attrib": {"code_12": "142"},
    },
    {
        "index": 12,
        "title": "Non-irrigated arable land",
        "colour": (255, 255, 168, 255),
        "attrib": {"code_12": "211"},
    },
    {
        "index": 13,
        "title": "Permanently irrigated land",
        "colour": (255, 255, 0, 255),
        "attrib": {"code_12": "212"},
    },
    {
        "index": 14,
        "title": "Rice fields",
        "colour": (230, 230, 0, 255),
        "attrib": {"code_12": "213"},
    },
    {
        "index": 15,
        "title": "Vineyards",
        "colour": (230, 128, 0, 255),
        "attrib": {"code_12": "221"},
    },
    {
        "index": 16,
        "title": "Fruit trees and berry plantations",
        "colour": (242, 166, 77, 255),
        "attrib": {"code_12": "222"},
    },
    {
        "index": 17,
        "title": "Olive groves",
        "colour": (230, 166, 0, 255),
        "attrib": {"code_12": "223"},
    },
    {
        "index": 18,
        "title": "Pastures",
        "colour": (230, 230, 77, 255),
        "attrib": {"code_12": "231"},
    },
    {
        "index": 19,
        "title": "Annual crops associated with permanent crops",
        "colour": (255, 230, 166, 255),
        "attrib": {"code_12": "241"},
    },
    {
        "index": 20,
        "title": "Complex cultivation patterns",
        "colour": (255, 230, 77, 255),
        "attrib": {"code_12": "242"},
    },
    {
        "index": 21,
        "title": "Land principally occupied by agriculture with significant areas of natural vegetation",
        "colour": (230, 204, 77, 255),
        "attrib": {"code_12": "243"},
    },
    {
        "index": 22,
        "title": "Agro-forestry areas",
        "colour": (242, 204, 166, 255),
        "attrib": {"code_12": "244"},
    },
    {
        "index": 23,
        "title": "Broad-leaved forest",
        "colour": (128, 255, 0, 255),
        "attrib": {"code_12": "311"},
    },
    {
        "index": 24,
        "title": "Coniferous forest",
        "colour": (0, 166, 0, 255),
        "attrib": {"code_12": "312"},
    },
    {
        "index": 25,
        "title": "Mixed forest",
        "colour": (77, 255, 0, 255),
        "attrib": {"code_12": "313"},
    },
    {
        "index": 26,
        "title": "Natural grasslands",
        "colour": (204, 242, 77, 255),
        "attrib": {"code_12": "321"},
    },
    {
        "index": 27,
        "title": "Moors and heathland",
        "colour": (166, 255, 128, 255),
        "attrib": {"code_12": "322"},
    },
    {
        "index": 28,
        "title": "Sclerophyllous vegetation",
        "colour": (166, 230, 77, 255),
        "attrib": {"code_12": "323"},
    },
    {
        "index": 29,
        "title": "Transitional woodland-shrub",
        "colour": (166, 242, 0, 255),
        "attrib": {"code_12": "324"},
    },
    {
        "index": 30,
        "title": "Beaches - dunes - sands",
        "colour": (230, 230, 230, 255),
        "attrib": {"code_12": "331"},
    },
    {
        "index": 31,
        "title": "Bare rocks",
        "colour": (204, 204, 204, 255),
        "attrib": {"code_12": "332"},
    },
    {
        "index": 32,
        "title": "Sparsely vegetated areas",
        "colour": (204, 255, 204, 255),
        "attrib": {"code_12": "333"},
    },
    {
        "index": 33,
        "title": "Burnt areas",
        "colour": (0, 0, 0, 255),
        "attrib": {"code_12": "334"},
    },
    {
        "index": 34,
        "title": "Glaciers and perpetual snow",
        "colour": (166, 230, 204, 255),
        "attrib": {"code_12": "335"},
    },
    {
        "index": 35,
        "title": "Inland marshes",
        "colour": (166, 166, 255, 255),
        "attrib": {"code_12": "411"},
    },
    {
        "index": 36,
        "title": "Peat bogs",
        "colour": (77, 77, 255, 255),
        "attrib": {"code_12": "412"},
    },
    {
        "index": 37,
        "title": "Salt marshes",
        "colour": (204, 204, 255, 255),
        "attrib": {"code_12": "421"},
    },
    {
        "index": 38,
        "title": "Salines",
        "colour": (230, 230, 255, 255),
        "attrib": {"code_12": "422"},
    },
    {
        "index": 39,
        "title": "Intertidal flats",
        "colour": (166, 166, 230, 255),
        "attrib": {"code_12": "423"},
    },
    {
        "index": 40,
        "title": "Water courses",
        "colour": (0, 204, 242, 255),
        "attrib": {"code_12": "511"},
    },
    {
        "index": 41,
        "title": "Water bodies",
        "colour": (128, 242, 230, 255),
        "attrib": {"code_12": "512"},
    },
    {
        "index": 42,
        "title": "Coastal lagoons",
        "colour": (0, 255, 166, 255),
        "attrib": {"code_12": "521"},
    },
    {
        "index": 43,
        "title": "Estuaries",
        "colour": (166, 255, 230, 255),
        "attrib": {"code_12": "522"},
    },
    {
        "index": 44,
        "title": "Sea and ocean",
        "colour": (230, 242, 255, 255),
        "attrib": {"code_12": "523"},
    },
    {
        "index": 49,
        "title": "UNCLASSIFIED LAND SURFACE",
        "colour": (255, 255, 255, 255),
        "attrib": {"code_12": "990"},
    },
    {
        "index": 50,
        "title": "UNCLASSIFIED WATER BODIES",
        "colour": (230, 242, 255, 255),
        "attrib": {"code_12": "995"},
    },
    {
        "index": 0, # changed from 48 to 0
        "title": "NODATA",
        "colour": (255, 255, 255, 255),
        "attrib": {"code_12": "999"},
    },
]
