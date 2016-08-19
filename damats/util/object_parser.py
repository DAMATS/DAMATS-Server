#-------------------------------------------------------------------------------
#
#  Object Validating Parsers
#  Used to validate parsed JSON input.
#
# Project: EOxServer <http://eoxserver.org>
# Authors: Martin Paces <martin.paces@eox.at>
#
#-------------------------------------------------------------------------------
# Copyright (C) 2015 EOX IT Services GmbH
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
# pylint: disable=too-few-public-methods

from datetime import datetime
import _strptime # DO NOT REMOVE! #pylint: disable=unused-import

def _parse(parsers, value):
    """ Parse value using single (one object) or multiple parsers
    (sequence or iterable).
    """
    message = "Parsing failed!"
    try:
        for parser in parsers:
            try:
                return parser.parse(value)
            except (TypeError, ValueError) as exc:
                message = str(exc)
    except TypeError:
        return parsers.parse(value)
    raise ValueError(message)

class Null(object):
    """ Null parser. """
    @staticmethod
    def parse(value):
        """ parse null value """
        if value is not None:
            raise ValueError("Not a null value!")
        return value

class Bool(object):
    """ String parser. """
    @staticmethod
    def parse(value):
        """ parse string value """
        if isinstance(value, bool):
            return value
        if isinstance(value, basestring):
            if value.lower() in ("true", "yes", "1"):
                return True
            if value.lower() in ("false", "no", "0"):
                return False
        raise ValueError("Not a boolean value!")

class Float(object):
    """ String parser. """
    @staticmethod
    def parse(value):
        """ parse float value """
        return float(value)

class Int(object):
    """ String parser. """
    @staticmethod
    def parse(value):
        """ parse float value """
        return int(value)

class String(object):
    """ String parser. """
    @staticmethod
    def parse(value):
        """ parse string value """
        if not isinstance(value, basestring):
            raise ValueError("Not a string value!")
        return value

class DateTime(object):
    """ time-stamp parser. """
    @staticmethod
    def parse(value):
        """ parse an ISO 8601 UTC time-stamp value """
        value = String.parse(value)
        # NOTE: The string input must me always zulu UTC time.
        try:
            return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ")


        return value

class AnyObject(object):
    """ Pass an unparsed object. """
    @staticmethod
    def parse(value):
        """ Parse any (dict) object. """
        if not isinstance(value, dict):
            raise ValueError("An object (dictionary) expected!")
        return value

class Array(object):
    """ Array parser. """
    def __init__(self, item_parser):
        self.item_parser = item_parser

    def parse(self, sequence):
        """ parse array """
        output = []
        for item in sequence:
            output.append(_parse(self.item_parser, item))
        return output

class Object(object):
    """ Object parser.

        The schema is a list of object attribute parsers.
        Mandatory attribute parser item:
            (<key>, <parser>, True)
            (<key>, (<parser>, <parser>, ...), True)

        Optional attribute parser item with a default value:
            (<key>, <parser>, False, <default>)
            (<key>, (<parser>, <parser>, ...), False, <default>)

        Optional attribute parser item without a default value:
            (<key>, <parser>)
            (<key>, (<parser>, <parser>, ...))
            (<key>, <parser>, None)
            (<key>, (<parser>, <parser>, ...), None)
    """
    def __init__(self, schema):
        if isinstance(schema, dict):
            schema = schema.items()
        # fill the default required field
        self.schema = [(tuple(item) + (None, None))[:4] for item in schema]

    def parse(self, obj):
        """ parse object """
        output = {}
        for key, parser, required, default in self.schema:
            if required or obj.has_key(key):
                output[key] = _parse(parser, obj[key])
            elif required is not None:
                output[key] = default
        return output
