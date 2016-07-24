#-------------------------------------------------------------------------------
#
# Simple Web Coverage Service client.
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

import re
from logging import getLogger
from functools import wraps
from contextlib import closing
from urllib2 import urlopen, Request, HTTPError
from lxml.etree import parse, XMLParser, tostring


XML_PARSER = XMLParser(remove_blank_text=True)
XML_OPTS = {'pretty_print': True, 'xml_declaration': True, 'encoding': 'utf-8'}

NS_OWS20 = '{http://www.opengis.net/ows/2.0}'
NS_GML32 = '{http://www.opengis.net/gml/3.2}'
NS_WCS20 = '{http://www.opengis.net/wcs/2.0}'
NS_CRS10 = '{http://www.opengis.net/wcs/crs/1.0}'
NS_INT10 = '{http://www.opengis.net/wcs/interpolation/1.0}'
NS_WCSEO10 = '{http://www.opengis.net/wcs/wcseo/1.0}'

RE_SRS = re.compile(r'^http://www.opengis.net/def/crs/EPSG/0/([0-9]+)$')
RE_INT = re.compile(r'^http://www.opengis.net/def/interpolation/OGC/1/([^/]+)$')


def parse_int(int_code):
    """ Parse interpolation method."""
    match = RE_INT.match(int_code)
    return match.groups()[0] if match else None


def pack_int(int_str):
    """ Get interpolation method URL."""
    return "http://www.opengis.net/def/interpolation/OGC/1/%s" % int_str


def parse_srs(srs):
    """ Parse SRID from SRS string. """
    match = RE_SRS.match(srs)
    return int(match.groups()[0]) if match else None


def pack_srs(srid):
    """ Make SRS from SRID. """
    return "http://www.opengis.net/def/crs/EPSG/0/%d" % srid


class OWSException(Exception):
    """ Exception representing OWS exception. """
    def __init__(self, code, locator, text):
        locator = "(%s)" % locator if locator else ''
        super(OWSException, self).__init__("%s%s: %s" % (code, locator, text))


def parse_ows20_exception(funct):
    """ This decorator catches HTTPError exception as tries to parse the OWS
    exception.
    """
    @wraps(funct)
    def _parse_ows20_exception_wrapper_(*args, **kwargs):
        try:
            return funct(*args, **kwargs)
        except HTTPError as exception:
            if exception.info()['Content-Type'] == 'text/xml':
                xml = parse(exception, XML_PARSER)
                elm = xml.find(NS_OWS20 + 'Exception')
                if elm is None:
                    raise
                code = elm.get('exceptionCode')
                locator = elm.get('locator', '')
                text = elm.find(NS_OWS20 + 'ExceptionText').text
                raise OWSException(code, locator, text)
            else:
                raise
    return _parse_ows20_exception_wrapper_


class XMLWrapper(object):
    """ Simple XML wrapper with human friendly interface. """
    def __init__(self, xml):
        self.xml = xml

    @property
    def as_string(self):
        """ Return the xml document as string. """
        return tostring(self.xml, **XML_OPTS)

    def attr(self, path, name):
        """ Get property. """
        elm = self.xml.find(path)
        return elm.get(name, None) if elm is not None else None

    def text(self, path):
        """ Get property. """
        elm = self.xml.find(path)
        return elm.text if elm is not None else None

    def all_text(self, path):
        """ Get text of multiple elements. """
        return [elm.text for elm in  self.xml.findall(path)]


class WCS20Capabilities(XMLWrapper):
    """ Service capabilities object. """

    @property
    def type(self):
        """ Get service type. """
        return self.text(
            "//%sServiceIdentification/%sServiceType" % (NS_OWS20, NS_OWS20)
        )

    @property
    def versions(self):
        """ Get supported versions. """
        return self.all_text(
            "//%sServiceIdentification/%sServiceTypeVersion" %
            (NS_OWS20, NS_OWS20)
        )

    @property
    def profiles(self):
        """ Get profiles. """
        return self.all_text(
            "//%sServiceIdentification/%sProfile" % (NS_OWS20, NS_OWS20)
        )

    @property
    def formats(self):
        """ Get supported formats. """
        return self.all_text(
            "//%sServiceMetadata/%sformatSupported" % (NS_WCS20, NS_WCS20)
        )

    @property
    def srids(self):
        """ Get supported srids. """
        return [parse_srs(srs) for srs in self.all_text(
            "//%sServiceMetadata//%scrsSupported" % (NS_WCS20, NS_CRS10)
        )]

    @property
    def ints(self):
        """ Get supported interpolation methods. """
        return [parse_int(srs) for srs in self.all_text(
            "//%sServiceMetadata//%sInterpolationSupported" %
            (NS_WCS20, NS_INT10)
        )]

    @property
    def series(self):
        """ Get list of available EO dataset series. """
        return self.all_text(
            "//%sContents//%sDatasetSeriesId" % (NS_WCS20, NS_WCSEO10)
        )


class WCS20CoverageDescription(XMLWrapper):
    """ Coverage description object. """

    @property
    def srid(self):
        """ Get coverage SRID """
        return parse_srs(self.attr(
            "//%sboundedBy/%sEnvelope" % (NS_GML32, NS_GML32), 'srsName'
        ))

    @property
    def axis_labels(self):
        """ Get axes labels."""
        return self.attr(
            "//%sboundedBy/%sEnvelope" % (NS_GML32, NS_GML32), 'axisLabels'
        ).split()

    @property
    def uom_labels(self):
        """ Get axes labels."""
        return self.attr(
            "//%sboundedBy/%sEnvelope" % (NS_GML32, NS_GML32), 'uomLabels'
        ).split()

    @property
    def dim(self):
        """ Dimension. """
        return int(self.attr(
            "//%sboundedBy/%sEnvelope" % (NS_GML32, NS_GML32), 'srsDimension'
        ))

    @property
    def envelope(self):
        """ Get coverage envelope. """
        lower = self.text(
            "//%sEnvelope/%slowerCorner" % (NS_GML32, NS_GML32)
        ).split()
        upper = self.text(
            "//%sEnvelope/%supperCorner" % (NS_GML32, NS_GML32)
        ).split()
        return tuple(float(v) for v in lower + upper)


class WCS20Client(object):
    """ Simple Web Coverage Service v2.0 client. """

    def __init__(self, service_url, headers=None, logger=None):
        if service_url[-1] != '?':
            service_url += '?'
        self.url = service_url
        self.headers = dict(headers or {})
        self.logger = logger or getLogger(__name__)


    @parse_ows20_exception
    def _query(self, *query):
        """ Make generic WCS query and return the connection context manager.
        """
        url = self.url + "&".join(('service=WCS', 'version=2.0.0') + query)
        self.logger.info("query: %s", url)
        return urlopen(Request(url, headers=self.headers))

    def _query_xml(self, *query):
        """ Make generic request and parse the XML response. """
        with closing(self._query(*query)) as fsrc:
            return parse(fsrc, XML_PARSER)

    def get_capabilities(self):
        """ Get parsed service capabilities. """
        return WCS20Capabilities(self._query_xml('request=getCapabilities'))

    def describe_coverage(self, identifier):
        """ Get parsed coverage description. """
        return WCS20CoverageDescription(self._query_xml(
            'request=describeCoverage', 'coverageId=%s' % identifier
        ))

    def get_coverage(self, identifier, format=None, subset=None,
                     subsetting_srid=None, output_srid=None,
                     scale=None, size=None, interpolation=None, **options):
        """ Get file-like object allowing download of the file.
        """

        def _str(val):
            """ Conversion to string trying to minimize the lost of float
            precision.
            """
            try:
                return "%.16g" % float(val)
            except (TypeError, ValueError):
                return str(val)

        # core format
        args = []
        if format:
            args.append('format=%s' % format)

        # core sub-setting
        for key, val in (subset or {}).items():
            try:
                vmin, vmax = val
            except TypeError:
                args.append('subset=%s(%s)' % (key, _str(val)))
            else:
                args.append('subset=%s(%s,%s)' % (key, _str(vmin), _str(vmax)))

        # CRS extension
        if subsetting_srid is not None:
            args.append('subsettingCrs=%s' % pack_srs(subsetting_srid))
            if output_srid is None:
                output_srid = self.describe_coverage(identifier).srid
        if output_srid is not None:
            args.append('outputCrs=%s' % pack_srs(output_srid))

        # scaling extension
        if scale:
            try:
                args.append('scaleFactor=%s' % _str(float(scale)))
            except TypeError:
                args.append('scaleAxes=%s' % ",".join(
                    "%s(%s)" % (key, _str(val)) for key, val in scale.items()
                ))
        if size:
            args.append('scaleSize=%s' % ",".join(
                "%s(%d)" % (key, int(val)) for key, val in size.items()
            ))

        # interpolation extension
        if interpolation:
            args.append('interpolation=%s' % pack_int(interpolation))

        # format options
        for key, val in options.get('geotiff', {}).items():
            args.append('geotiff:%s=%s' % (key, val))


        return self._query(
            'request=getCoverage', 'coverageId=%s' % identifier, *args
        )
