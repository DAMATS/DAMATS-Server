#-------------------------------------------------------------------------------
#
#  DAMATS web app - export the DB objects to JSON
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
# pylint: disable=missing-docstring, too-few-public-methods

import sys
import json
from collections import OrderedDict
from optparse import make_option
from django.core.management.base import CommandError, BaseCommand
from eoxserver.resources.coverages.management.commands import (
    CommandOutputMixIn,
)
from eoxserver.resources.coverages.models import Coverage
from damats.webapp.models import (
    User, Group, Process, SourceSeries, TimeSeries, Job,
)
from damats.webapp.views_users import user_serialize, group_serialize
from damats.util.view_utils import pack_datetime

JSON_OPTS = {
    'sort_keys': False, 'indent': 2, 'separators': (',', ': ')
}

class Command(CommandOutputMixIn, BaseCommand):
    help = (
        "Export the DAMATS webapp model in JSON format. "
    )
    args = "[<model-entity> ...]"
    option_list = BaseCommand.option_list + (
        make_option(
            "-o", "--output", dest="output", default=None,
            help=(
                "Optional output filename. If not provided the output is "
                "exported to the standard output."
            )
        ),
    )

    def handle(self, *args, **opts):
        output = OrderedDict()
        try:
            for key in args or HANDLERS:
                output[key] = HANDLERS[key]()
        except KeyError as exc:
            raise CommandError("Invalid model entity %r!" % exc)

        output_filename = opts["output"]
        if output_filename and (output_filename != "-"):
            fout = open(output_filename, "wb")
        else:
            fout = sys.stdout

        with fout:
            json.dump(output, fout, **JSON_OPTS)


def get_users():
    """ Get list of the user JSON objects. """
    return [
        user_serialize(item, {
            "groups": list(item.groups.values_list('identifier', flat=True))
        }) for item in User.objects.prefetch_related('groups').all()
    ]


def get_groups():
    """ Get list of the group JSON objects. """
    return [group_serialize(item) for item in Group.objects.all()]


def get_processes():
    """ Get list of the process JSON objects. """
    return [
        process_serialize(item)
        for item in Process.objects.prefetch_related('readers')
    ]


def get_sources():
    """ Get list of the source series JSON objects. """
    return [
        source_series_serialize(item)
        for item in (
            SourceSeries.objects
            .select_related('eoobj')
            .prefetch_related('readers')
        )
    ]


def get_sits():
    """ Get list of the time series objects. """
    return [
        time_series_serialize(item)
        for item in (
            TimeSeries.objects.select_related(
                'eoobj', 'owner', 'source', 'source__eoobj'
            ).prefetch_related('readers')
        )
    ]


def get_jobs():
    """ Get list of the time series objects. """
    return [
        jobs_serialize(item)
        for item in (
            Job.objects.select_related(
                'owner', 'process', 'time_series', 'time_series__eoobj'
            ).prefetch_related('readers')
        )
    ]


HANDLERS = OrderedDict([
    ("users", get_users),
    ("groups", get_groups),
    ("processes", get_processes),
    ("sources", get_sources),
    ("sits", get_sits),
    ("jobs", get_jobs),
])


def process_serialize(obj, extras=None):
    """ Serialize process object. """
    response = extras if extras else {}
    response.update({
        "identifier": obj.identifier,
        "name": obj.name or None,
        "description": obj.description or None,
        "readers": list(obj.readers.values_list('identifier', flat=True)),
    })
    return response


def source_series_serialize(obj, extras=None):
    """ Serialize source series object. """
    response = extras if extras else {}
    response.update({
        "identifier": obj.eoobj.identifier,
        "name": obj.name or None,
        "description": obj.description or None,
        "readers": list(obj.readers.values_list('identifier', flat=True)),
    })
    return response


def time_series_serialize(obj, extras=None):
    """ Serialize time series object. """
    response = extras if extras else {}
    response.update({
        "identifier": obj.eoobj.identifier,
        "name": obj.name or None,
        "description": obj.description or None,
        "owner": obj.owner.identifier,
        "readers": list(obj.readers.values_list('identifier', flat=True)),
        "created": pack_datetime(obj.created),
        "updated": pack_datetime(obj.updated),
        "editable": obj.editable,
        "source": obj.source.eoobj.identifier,
        "selection": json.loads(obj.selection or '{}'),
        "content": get_coverages_ids(obj.eoobj),
    })
    return response


def jobs_serialize(obj, extras=None):
    """ Serialize job object. """
    response = extras if extras else {}
    response.update({
        "identifier": obj.identifier,
        "name": obj.name or None,
        "description": obj.description or None,
        "owner": obj.owner.identifier,
        "readers": list(obj.readers.values_list('identifier', flat=True)),
        "created": pack_datetime(obj.created),
        "updated": pack_datetime(obj.updated),
        "sits": obj.time_series.eoobj.identifier,
        "process": obj.process.identifier,
        "inputs": json.loads(obj.inputs or '{}'),
    })
    return response


def get_coverages_ids(eoobj):
    """ Get a list of ids of all Coverage objects held by given DatastSeries
    object.
    """
    def _get_children_ids(eoobj):
        """ recursive dataset series lookup """
        qset = (
            eoobj.cast().eo_objects
            .filter(real_content_type=eoobj.real_content_type)
        )
        id_list = [eoobj.id]
        for child_eoobj in qset:
            id_list.extend(_get_children_ids(child_eoobj))
        return id_list

    return list(
        Coverage.objects
        .filter(collections__id__in=_get_children_ids(eoobj))
        .values_list('identifier', flat=True)
    )
