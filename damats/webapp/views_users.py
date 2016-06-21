#-------------------------------------------------------------------------------
#
#  DAMATS web app Django views
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

from damats.webapp.models import User, Group
from damats.util.object_parser import Object, String, Null
from damats.util.view_utils import (
    error_handler, method_allow, rest_json,
)
from damats.webapp.views_common import authorisation, JSON_OPTS

#-------------------------------------------------------------------------------
# Input parsers

USER_PARSER = Object((
    ('name', (String, Null)),
    ('description', (String, Null)),
))

#-------------------------------------------------------------------------------
# model instance serialization

def user_serialize(obj, extras=None):
    """ Serialize User django model instance to a JSON serializable
        dictionary.
    """
    response = extras if extras else {}
    response.update({
        "identifier": obj.identifier,
        "name": obj.name or None,
        "description": obj.description or None,
    })
    return response

def group_serialize(obj, extras=None):
    """ Serialize Group django model instance to a JSON serializable
        dictionary.
    """
    response = extras if extras else {}
    response.update({
        "identifier": obj.identifier,
        "name": obj.name or None,
        "description": obj.description or None,
    })
    return response

#-------------------------------------------------------------------------------
# views

@error_handler
@authorisation
@method_allow(['GET', 'POST', 'PUT'])
@rest_json(JSON_OPTS, USER_PARSER)
def user_view(method, input_, user, **kwargs):
    """ User profile interface.
    """
    if method in ("POST", "PUT"): # update
        if input_.has_key("name"):
            user.name = input_.get("name", None) or None
        if input_.has_key("description"):
            user.description = input_.get("description", None) or None
        user.save()

    return 200, user_serialize(user)


@error_handler
@authorisation
@method_allow(['GET'])
@rest_json(JSON_OPTS)
def users_all_view(method, input_, user, **kwargs):
    """ User groups interface.
    The view list all avaiable uses.
    """
    return 200, [user_serialize(obj) for obj in User.objects.all()]


@error_handler
@authorisation
@method_allow(['GET'])
@rest_json(JSON_OPTS)
def groups_view(method, input_, user, **kwargs):
    """ User groups interface.
    The view list all groups of the current user.
    """
    return 200, [group_serialize(obj) for obj in user.groups.all()]


@error_handler
@authorisation
@method_allow(['GET'])
@rest_json(JSON_OPTS)
def groups_all_view(method, input_, user, **kwargs):
    """ User groups interface.
    The view list all avaiable uses and groups.
    """
    return 200, [group_serialize(obj) for obj in Group.objects.all()]
