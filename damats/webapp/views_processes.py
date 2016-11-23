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

import json
import uuid
from contextlib import closing
from lxml.etree import parse, XMLParser
from django.db.models import Q
from django.core.exceptions import ObjectDoesNotExist
from eoxserver.core import env, Component, ExtensionPoint
from eoxserver.services.ows.wps.interfaces import (
    ProcessInterface, AsyncBackendInterface,
)
from eoxserver.services.ows.wps.parameters import (
    fix_parameter, AllowedAny, AllowedEnum, AllowedRange,
)
from damats.util.object_parser import (
    Object, String, Null, AnyObject,
)
from damats.util.view_utils import (
    HttpError, error_handler, method_allow, method_allow_conditional,
    rest_json, pack_datetime,
)
from damats.webapp.models import (
    Process, Job, #Result,
)
from damats.webapp.views_common import authorisation, JSON_OPTS
from damats.webapp.views_time_series import get_time_series

JOB_STATUS_DICT = dict(Job.STATUS_CHOICES)
SITS_PROCESSOR_PROFILE = "DAMATS-SITS-processor"
XML_PARSER = XMLParser(remove_blank_text=True)

WPS10_NS = "http://www.opengis.net/wps/1.0.0"
OWS11_NS = "http://www.opengis.net/ows/1.1"
WPS10_STATUS = "{%s}Status" % WPS10_NS
WPS10_PROCESS_OUTPUTS = "{%s}ProcessOutputs" % WPS10_NS
WPS10_OUTPUT = "{%s}Output" % WPS10_NS
WPS10_REFERENCE = "{%s}Reference" % WPS10_NS
WPS10_DATA = "{%s}Data" % WPS10_NS
WPS10_LITERAL_DATA = "{%s}LiteralData" % WPS10_NS
OWS11_IDENTIFIER = "{%s}Identifier" % OWS11_NS
OWS11_TITLE = "{%s}Title" % OWS11_NS
OWS11_ABSTRACT = "{%s}Abstract" % OWS11_NS
OWS11_EXCEPTION = "{%s}Exception" % OWS11_NS
OWS11_EXCEPTIONTEXT = "{%s}ExceptionText" % OWS11_NS

#-------------------------------------------------------------------------------

JOB_PARSER_POST = Object((
    ('process', String, True),
    ('time_series', String, True),
    ('inputs', AnyObject, False, {}),
    ('name', (String, Null), False, None),
    ('description', (String, Null), False, None),
))

JOB_PARSER_PUT = Object((
    ('name', (String, Null)),
    ('description', (String, Null)),
    ('inputs', AnyObject),
))

#-------------------------------------------------------------------------------

class _ProcessProvider(Component):
    """ Component providing list of WPS Process components. """
    #pylint: disable=too-few-public-methods
    processes = ExtensionPoint(ProcessInterface)


class _AsyncBackendProvider(Component):
    """ Component providing list of WPS AsyncBackend components. """
    #pylint: disable=too-few-public-methods
    async_backends = ExtensionPoint(AsyncBackendInterface)


def get_wps_processes():
    """ Get a dictionary of the WPS processes implementing the SITS processor
    interface.
    """
    return dict(
        (process.identifier, process) for process
        in _ProcessProvider(env).processes if (
            getattr(process, 'asynchronous', False) and
            SITS_PROCESSOR_PROFILE in getattr(process, 'profiles', [])
        )
    )

def get_wps_async_backend():
    """ Get the asynchronous WPS back-end. """
    for async_backend in _AsyncBackendProvider(env).async_backends:
        return async_backend
    return None

#-------------------------------------------------------------------------------

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
            idef for idef in (
                fix_parameter(iid, idef) for iid, idef
                in wps_processes[process.identifier].inputs
            ) if not idef.identifier.startswith('\\')
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
    qset = qset.prefetch_related('results', 'results__eoobj')
    if owned and read_only:
        qset = qset.filter(Q(owner=user) | Q(readers__identifier__in=id_list))
    elif owned:
        qset = qset.filter(owner=user)
    elif read_only:
        qset = qset.filter(readers__identifier__in=id_list)
    else: #nothing selected
        return []
    return qset


def is_job_owned(request, user, identifier, *args, **kwargs):
    """ Return true if the time_series object is owned by the user. """
    try:
        obj = get_jobs(user).get(identifier=identifier)
    except ObjectDoesNotExist:
        raise HttpError(404, "Not found")
    return obj.owner == user


def create_job(input_, user):
    """ Handle create requests and create a new Job object. """

    # get the process and time series objects
    try:
        process = get_processes(user).get(
            identifier=input_.get('process', None)
        )
        time_series = get_time_series(user).get(
            eoobj__identifier=input_.get('time_series', None)
        )
    except ObjectDoesNotExist:
        raise HttpError(400, "Bad Request")

    # TODO: lock the time-series

    # Create a new object.
    obj = Job()
    obj.owner = user
    obj.identifier = "job-" + uuid.uuid4().hex
    obj.name = input_.get('name', None) or None
    obj.description = input_.get('description', None) or None
    obj.time_series = time_series
    obj.process = process
    obj.inputs = json.dumps(pack_datetime(input_.get('inputs', {}) or {}))
    obj.save()

    return obj


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
    response['is_optional'] = idef.is_optional
    response['default_value'] = idef.default
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
    response["inputs"] = [
        input_serialize(idef) for idef in obj.inputs
        if idef.identifier != 'sits' # only the process specific inputs
    ]
    if obj.name:
        response['name'] = obj.name
    if obj.description:
        response['description'] = obj.description
    return response


def parse_wps_execute_response(wps_job_id):
    """ Get status details of a asynchronous WPS process. """

    def _text(elm):
        return None if elm is None else elm.text

    def _reference(elm):
        if elm is None:
            reference = None
        else:
            reference = {'url': elm.get('href')}
            mime_type = elm.get('mimeType')
            if mime_type:
                reference['mime_type'] = mime_type
        return reference

    def _literal(elm):
        return None if elm is None else {
            'value': elm.text,
            'type': elm.get('dataType', 'string'),
        }

    with closing(get_wps_async_backend().get_response(wps_job_id)) as fobj:
        xml = parse(fobj, parser=XML_PARSER)

    status_elm = xml.find(WPS10_STATUS)
    status_subelm = status_elm[0]
    status_tag = status_subelm.tag.split("}")[-1]

    status = {
        "creation_time": status_elm.get('creationTime'),
        "status": status_tag,
        "message": status_subelm.text,
    }

    if status_subelm.get('percentCompleted') is not None:
        status['percent_completed'] = int(
            status_subelm.get('percentCompleted')
        )

    if status_tag == 'ProcessFailed':
        exception_elm = status_elm.find(".//" + OWS11_EXCEPTION)

        status.update({
            'locator': exception_elm.get('locator'),
            'code': exception_elm.get('exceptionCode'),
            'message': _text(exception_elm.find(OWS11_EXCEPTIONTEXT)),
        })

    # NOTE: only Embedded Literals and Complex References are parsed.
    if status_tag == 'ProcessSucceeded':
        outputs = []
        for elm in xml.findall("%s/%s" % (WPS10_PROCESS_OUTPUTS, WPS10_OUTPUT)):
            outputs.append(dict(
                (key, value) for key, value in [
                    ("identifier", _text(elm.find(OWS11_IDENTIFIER))),
                    ("name", _text(elm.find(OWS11_TITLE))),
                    ("description", _text(elm.find(OWS11_ABSTRACT))),
                    ("reference", _reference(elm.find(WPS10_REFERENCE))),
                    ("literal", _literal(
                        elm.find("%s/%s" % (WPS10_DATA, WPS10_LITERAL_DATA))
                    )),
                    # TODO: implement bounding box parsing if needed
                ] if value is not None
            ))
    else:
        outputs = None

    return status, outputs


def job_serialize(obj, user, extras=None):
    response = dict(extras) if extras else {}

    if obj.wps_job_id:
        wps_status, outputs = parse_wps_execute_response(obj.wps_job_id)
    else:
        wps_status, outputs = None, None

    if outputs is not None:
        coverages = {}
        for result in obj.results.all():
            coverages[result.identifier] = dict((key, val) for key, val in [
                ("name", result.name),
                ("description", result.description),
                ("coverage_id", result.eoobj.identifier),
            ] if val is not None)

        # add available coverage ids to the outputs
        for output in outputs:
            try:
                output['coverage_id'] = (
                    coverages[output['identifier']]['coverage_id']
                )
            except KeyError:
                pass
    else:
        coverages = None

    response.update({
        "identifier": obj.identifier,
        "editable": obj.owner == user,
        "owned": obj.owner == user,
        "status": JOB_STATUS_DICT[obj.status],
        "created": pack_datetime(obj.created),
        "updated": pack_datetime(obj.updated),
        "inputs": json.loads(obj.inputs or '{}'),
        "process": obj.process.identifier,
        "time_series": obj.time_series.eoobj.identifier,
        "wps_job_id": obj.wps_job_id,
        "wps_response_url": obj.wps_response_url,
        "wps_status": wps_status,
        "outputs": outputs,
        "coverages": coverages,
    })

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
    """ List available processes.
    """
    response = []

    for obj in extend_processes(get_processes(user)):
        response.append(process_serialize(obj))
    return 200, response


@error_handler
@authorisation
@method_allow(['GET', 'POST'])
@rest_json(JSON_OPTS, JOB_PARSER_POST)
def jobs_view(method, input_, user, **kwargs):
    """ List available time-series.
    """
    if method == "POST": # new object to be created
        return 200, job_serialize(create_job(input_, user), user)

    return 200, [
        job_serialize(obj, user) for obj in get_jobs(user).order_by('-created')
    ]


@error_handler
@authorisation
@method_allow_conditional(['GET', 'PUT', 'DELETE'], ['GET'], is_job_owned)
@rest_json(JSON_OPTS, JOB_PARSER_PUT)
def job_item_view(method, input_, user, identifier, **kwargs):
    """ Single job item view.
    """
    try:
        obj = get_jobs(user).get(identifier=identifier)
    except ObjectDoesNotExist:
        raise HttpError(404, "Not found")

    if method == "DELETE":
        if obj.owner != user:
            raise HttpError(405, "Method not allowed\nRead-only job!")
        # TODO: reliable job termination
        # block removal of the accepted and in-progress jobs
        if obj.status in (Job.ACCEPTED, Job.IN_PROGRESS):
            raise HttpError(
                405, "Method not allowed\nCannot remove a running job!"
            )
        # TODO: de-register results
        # purge WPS process resources
        if obj.wps_job_id:
            get_wps_async_backend().purge(obj.wps_job_id)
        obj.delete()
        return 204, None

    elif method == "PUT":
        if obj.owner != user:
            raise HttpError(405, "Method not allowed\nRead-only job!")
        # update job
        if input_.has_key("name"):
            obj.name = input_["name"] or None
        if input_.has_key("description"):
            obj.description = input_["description"] or None
        if input_.has_key("inputs") and obj.status == Job.CREATED:
            # NOTE: Once the Job is submitted for execution the inputs cannot
            #       be changed.
            obj.inputs = json.dumps(pack_datetime(input_['inputs']))
        obj.save()

    return 200, job_serialize(obj, user)
