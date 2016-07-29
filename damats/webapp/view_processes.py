#-------------------------------------------------------------------------------
#
#  DAMATS web app Django views
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
# pylint: disable=missing-docstring,unused-argument

from eoxserver.core import env, Component, ExtensionPoint
from eoxserver.services.ows.wps.interfaces import ProcessInterface
from eoxserver.services.ows.wps.parameters import (
    fix_parameter, AllowedAny, AllowedEnum, AllowedRange,
)
from django.db.models import Q
from damats.util.view_utils import (
    error_handler, method_allow, rest_json,
    # HttpError, error_handler, method_allow, method_allow_conditional,
)
from damats.webapp.models import (
    Process, Job, #Result,
)
from damats.webapp.views_common import authorisation, JSON_OPTS

JOB_STATUS_DICT = dict(Job.STATUS_CHOICES)
SITS_PROCESSOR_PROFILE = "DAMATS-SITS-processor"

#-------------------------------------------------------------------------------

class _ProcessProvider(Component):
    """ Component providing list of WPS Process components. """
    #pylint: disable=too-few-public-methods
    processes = ExtensionPoint(ProcessInterface)

def get_wps_processes():
    """ Get a dictionary of the WPS processes implementing the SITS processor
    interface.
    """
    return dict(
        (process.identifier, process)
        for process in _ProcessProvider(env).processes
        if getattr(process, 'asynchronous', False)
    )


def extend_processes(processes):
    """ Add the process definition to the process. """
    wps_processes = get_wps_processes()
    for process in processes:
        # skip processes which are not available
        if process.identifier not in wps_processes:
            continue
        wps_process = wps_processes[process.identifier]
        # add name and description if missing
        if not process.name:
            process.name = wps_process.title
        if not process.description:
            process.description = wps_process.__doc__
        # extend the class with the sanitized WPS input definitions
        process.inputs = [
            (id_, fix_parameter(id_, def_)) for id_, def_
            in wps_processes[process.identifier].inputs
        ]
        yield process


def get_processes(user):
    """ Get query set of all Process objects accessible by the user. """
    id_list = [user.identifier] + [obj.identifier for obj in user.groups.all()]
    return Process.objects.filter(readers__identifier__in=id_list)


def get_jobs(user, owned=True, read_only=True):
    """ Get query set of Job objects accessible by the user.
        By default both owned and read-only (items shared by a different users)
        are returned.
    """
    id_list = [user.identifier] + [obj.identifier for obj in user.groups.all()]
    qset = Job.objects.select_related('owner')
    if owned and read_only:
        qset = qset.filter(Q(owner=user) | Q(readers__identifier__in=id_list))
    elif owned:
        qset = qset.filter(owner=user)
    elif read_only:
        qset = qset.filter(readers__identifier__in=id_list)
    else: #nothing selected
        return []
    return qset

#-------------------------------------------------------------------------------

def range_serialize(rdef, extras=None):
    """ Serialize range definition. """
    response = dict(extras) if extras else {}
    response['closure'] = rdef.closure
    if rdef.minval is not None:
        response['min'] = rdef.minval
    if rdef.maxval is not None:
        response['max'] = rdef.maxval
    if rdef.spacing is not None:
        response['spacing'] = rdef.spacing
    return response


def input_serialize(idef, extras=None):
    """ Serialize WPS input definition. """
    response = dict(extras) if extras else {}
    response.update({
        'identifier': idef.identifier,
        'type': idef.dtype.name,
    })
    # optional metadata
    if idef.title:
        response['name'] = idef.title
    if idef.abstract:
        response['description'] = idef.abstract
    # allowed values
    if isinstance(idef.allowed_values, AllowedAny):
        pass
    elif isinstance(idef.allowed_values, AllowedRange):
        response['range'] = range_serialize(idef.allowed_values)
    elif isinstance(idef.allowed_values, AllowedEnum):
        response['enum'] = list(idef.allowed_values.values)
    else:
        raise NotImplementedError(
            'Type %r is not supported.' % idef.allowed_values
        )
    # UOMs
    if idef.uoms:
        response['uoms'] = idef.uoms
        response['default_uom'] = idef.default_uom
    return response


def process_serialize(obj, extras=None):
    """ Serialize process object. """
    response = dict(extras) if extras else {}
    response["identifier"] = obj.identifier
    response["inputs"] = [input_serialize(def_) for _, def_ in obj.inputs]
    if obj.name:
        response['name'] = obj.name
    if obj.description:
        response['description'] = obj.description
    return response

#-------------------------------------------------------------------------------

@error_handler
@authorisation
@method_allow(['GET'])
@rest_json(JSON_OPTS)
def processes_view(method, input_, user, **kwargs):
    """ List avaiable processes.
    """
    response = []

    for obj in extend_processes(get_processes(user)):
        response.append(process_serialize(obj))
    return 200, response


@error_handler
@authorisation
@method_allow(['GET'])
@rest_json(JSON_OPTS)
def jobs_view(method, input_, user, identifier=None, **kwargs):
    """ List avaiable time-series.
    """
    response = []
    for obj in get_jobs(user):
        item = {
            "identifier": obj.identifier,
            "read_only": obj.owner != user,
            "status": JOB_STATUS_DICT[obj.status],
        }
        if obj.name:
            item['name'] = obj.name
        if obj.description:
            item['description'] = obj.description
        response.append(item)
    return 200, response
