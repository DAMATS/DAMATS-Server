#-------------------------------------------------------------------------------
#
#  DAMATS web app Django views - shared utilities
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
# pylint: disable=missing-docstring,unused-argument

from functools import wraps
from django.core.exceptions import ObjectDoesNotExist

from damats.webapp.models import User
from damats.util.view_utils import HttpError
from damats.util.config import WEBAPP_CONFIG

# JSON formatting options
#JSON_OPTS = {'sort_keys': False, 'indent': 2, 'separators': (',', ': ')}
JSON_OPTS={}

#-------------------------------------------------------------------------------
# authorisation enforcement decorator

def authorisation(view):
    """ Check if request.META['REMOTE_USER'] is an authorised DAMATS user
        and the User object in the view parameters.
    """
    @wraps(view)
    def _wrapper_(request, *args, **kwargs):
        # NOTE: Default user is is read from the configuration.
        uid = request.META.get('REMOTE_USER', WEBAPP_CONFIG.default_user)
        try:
            user = (
                User.objects
                .prefetch_related('groups')
                .get(identifier=uid, active=True)
            )
        except ObjectDoesNotExist:
            raise HttpError(401, "Unauthorised")
        return view(request, user, *args, **kwargs)
    return _wrapper_
