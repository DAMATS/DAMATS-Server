#-------------------------------------------------------------------------------
#
# DJango View Utilities
#
# Authors: Martin Paces <martin.paces@eox.at>
#
#-------------------------------------------------------------------------------
# Copyright (C) 2014 EOX IT Services GmbH
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
import sys
import traceback
from datetime import datetime
from functools import wraps
from ipaddr import IPAddress, IPNetwork
from django.http import HttpResponse
from django.conf import settings


def pack_datetime(obj):
    """ Convert all datetime objects in dictionary into ISO-8601 date-time
    strings.
    """
    if isinstance(obj, datetime):
        #if obj.tzinfo and not obj.utcoffset():
        if not obj.utcoffset():
            return obj.replace(tzinfo=None).isoformat("T") + "Z"
        return obj.isoformat("T")
    elif not isinstance(obj, dict):
        return obj
    else:
        return dict((key, pack_datetime(val)) for key, val in obj.iteritems())


class HttpError(Exception):
    """ Simple HTTP error exception """
    def __init__(self, status, message):
        Exception.__init__(self, message)
        self.status = status
        self.message = message

    def __unicode__(self):
        return "%d %s"%(self.status, self.message)


def error_handler(view):
    """ error handling decorator """
    @wraps(view)
    def _wrapper_(request, *args, **kwargs):
        try:
            return view(request, *args, **kwargs)
        except HttpError as exc:
            response = HttpResponse(
                unicode(exc), content_type="text/plain", status=exc.status
            )
        except Exception as exc:
            message = "Internal Server Error"
            trace = traceback.format_exc()
            sys.stderr.write(trace)
            if settings.DEBUG:
                message = "%s\n\n%s" % (message, trace)
            response = HttpResponse(
                message, content_type="text/plain", status=500
            )
        return response
    return _wrapper_


def method_allow(allowed_methods, allowed_headers=None, handle_options=True):
    """ Reject non-supported HTTP methods.
    By default the OPTIONS method is handled responding with
    the list of the supported methods and headers.
    """
    allowed_methods = set(allowed_methods)
    allowed_headers = list(allowed_headers or ["Content-Type"])
    if handle_options:
        allowed_methods.add('OPTIONS')

    def _wrap_(view):
        @wraps(view)
        def _wrapper_(request, *args, **kwargs):
            if handle_options and request.method == "OPTIONS":
                response = HttpResponse("")
                response['Access-Control-Allow-Methods'] = ", ".join(
                    allowed_methods
                )
                response['Access-Control-Allow-Headers'] = ", ".join(
                    allowed_headers
                )

            elif request.method not in allowed_methods:
                response = HttpResponse(
                    "Method not allowed", content_type="text/plain", status=405
                )
                response['Allow'] = ", ".join(allowed_methods)
            else:
                response = view(request, *args, **kwargs)
            return response
        return _wrapper_
    return _wrap_


def method_allow_conditional(allowed_methods_true, allowed_methods_false,
                             condition, allowed_headers=None,
                             handle_options=True):
    """ Reject non-supported HTTP methods.
    The list of the supported options is conditional based on the response
    of the is_read_only method.
    By default the OPTIONS method is handled responding with
    the list of the supported methods and headers.
    """
    allowed_methods_true = set(allowed_methods_true)
    allowed_methods_false = set(allowed_methods_false)
    allowed_headers = list(allowed_headers or ["Content-Type"])
    if handle_options:
        allowed_methods_true.add('OPTIONS')
        allowed_methods_false.add('OPTIONS')
    def _wrap_(view):
        @wraps(view)
        def _wrapper_(request, *args, **kwargs):
            if condition(request, *args, **kwargs):
                allowed_methods = allowed_methods_true
            else:
                allowed_methods = allowed_methods_false
            if handle_options and request.method == "OPTIONS":
                response = HttpResponse("")
                response['Access-Control-Allow-Methods'] = ", ".join(
                    allowed_methods
                )
                response['Access-Control-Allow-Headers'] = ", ".join(
                    allowed_headers
                )
            elif request.method not in allowed_methods:
                response = HttpResponse(
                    "Method not allowed", content_type="text/plain", status=405
                )
                response['Allow'] = ", ".join(allowed_methods)
            else:
                response = view(request, *args, **kwargs)
            return response
        return _wrapper_
    return _wrap_


def ip_deny(ip_list):
    """ IP black-list restricted access """
    def _wrap_(view):
        @wraps(view)
        def _wrapper_(request, *args, **kwargs):
            # get request source address and compare it with the forbiden ones
            ip_src = IPAddress(request.META['REMOTE_ADDR'])
            for ip_ in ip_list:
                if ip_src in IPNetwork(ip_):
                    raise HttpError(403, "Forbiden!")
            return view(request, *args, **kwargs)
        return _wrapper_
    return _wrap_


def ip_allow(ip_list):
    """ IP white-list restricted access """
    def _wrap_(view):
        @wraps(view)
        def _wrapper_(request, *args, **kwargs):
            # get request source address and compare it with the allowed ones
            ip_src = IPAddress(request.META['REMOTE_ADDR'])
            for ip_ in ip_list:
                if ip_src in IPNetwork(ip_):
                    break
            else:
                raise HttpError(403, "Forbiden!")
            return view(request, *args, **kwargs)
        return _wrapper_
    return _wrap_


def rest_json(json_options=None, validation_parser=None, defauts=None):
    """ JSON REST decorator serialising output object and parsing possible
        inputs.

        The wrapped view has following interface:

          view(method, input, *args, **kwargs)

        The view gets the method as the first argument.
        The second argument is the parsed input. If provided, the
        parsed JSON object is passed through the `parse()` method
        of the `validation_parser`.
        The kwargs contain the original request object if needed.
        The response object is always serialized to JSON.
    """
    json_options = json_options or {}
    defaults = defauts or {}
    def _wrap_(view):
        @wraps(view)
        def _wrapper_(request, *args, **kwargs):
            try:
                if request.body:
                    obj_input = json.loads(request.body)
                    if validation_parser:
                        if isinstance(validation_parser, dict):
                            _parser = validation_parser[request.method]
                        else:
                            _parser = validation_parser
                        obj_input = _parser.parse(obj_input)
                    if defaults: # fill the defaults
                        tmp = dict(defaults)
                        tmp.update(obj_input)
                        obj_input = tmp
                else:
                    obj_input = None
            except (KeyError, TypeError, ValueError):
                if settings.DEBUG:
                    trace = traceback.format_exc()
                    sys.stderr.write(trace)
                raise HttpError(400, "Bad Request")
            kwargs['request'] = request
            status, obj_output = view(
                request.method, obj_input, *args, **kwargs
            )
            if obj_output is None:
                response = HttpResponse("", status=status)
            else:
                response = HttpResponse(
                    json.dumps(obj_output, **json_options),
                    status=status, content_type="application/json"
                )
            return response
        return _wrapper_
    return _wrap_
