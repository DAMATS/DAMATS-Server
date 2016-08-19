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

from collections import OrderedDict
from damats.util.view_utils import (
    error_handler, method_allow, rest_json,
    # HttpError, error_handler, method_allow, method_allow_conditional,
)
from damats.webapp.views_common import authorisation, JSON_OPTS
from damats.webapp.views_users import (
    user_view, groups_view, users_all_view, groups_all_view,
)
from damats.webapp.views_time_series import (
    sources_view, sources_item_view, time_series_view, time_series_item_view,
    sources_coverage_view, time_series_coverage_view,
    get_sources, get_time_series,
)
from damats.webapp.views_processes import (
    get_processes, get_jobs, processes_view, jobs_view, job_item_view,
    JOB_STATUS_DICT,
)

INTERFACE_NAME = "DAMATS"
INTERFACE_VERSION = "0.0.2"


# TEST ROOT VIEW
@error_handler
@authorisation
@method_allow(['GET'])
@rest_json(JSON_OPTS)
def root_view(method, input_, user, **kwargs):
    """ DAMATS user profile view.
    """
    user_id = user.identifier
    groups = [obj.identifier for obj in user.groups.all()]
    sources = [
        OrderedDict((
            ("identifier", obj.eoobj.identifier),
            ("name", obj.name),
            ("description", obj.description),
        )) for obj in get_sources(user)
    ]
    time_series = [
        OrderedDict((
            ("identifier", obj.eoobj.identifier),
            ("name", obj.name),
            ("description", obj.description),
            ("is_owner", obj.owner.identifier == user_id),
        )) for obj in get_time_series(user)
    ]
    processes = [
        OrderedDict((
            ("identifier", obj.identifier),
            ("name", obj.name),
            ("description", obj.description),
        )) for obj in get_processes(user)
    ]
    jobs = [
        OrderedDict((
            ("identifier", obj.identifier),
            ("name", obj.name),
            ("description", obj.description),
            ("status", JOB_STATUS_DICT[obj.status]),
            ("is_owner", obj.owner.identifier == user_id),
        )) for obj in get_jobs(user)
    ]
    return 200, OrderedDict((
        ("interface", INTERFACE_NAME),
        ("version", INTERFACE_VERSION),
        ("user", user_id),
        ("groups", groups),
        ("sources", sources),
        ("processes", processes),
        ("time_series", time_series),
        ("jobs", jobs),
    ))
