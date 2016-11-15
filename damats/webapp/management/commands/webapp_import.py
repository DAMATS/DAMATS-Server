#-------------------------------------------------------------------------------
#
#  DAMATS web app - import the DB objects form JSON
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
    CommandOutputMixIn, nested_commit_on_success
)
from eoxserver.resources.coverages.models import DatasetSeries, Coverage
from damats.webapp.models import (
    Entity, User, Group, Process, SourceSeries, TimeSeries, Job,
)


class Command(CommandOutputMixIn, BaseCommand):
    help = (
        "Import the DAMATS webapp model in JSON format. "
    )
    args = "[<model-entity> ...]"
    option_list = BaseCommand.option_list + (
        make_option(
            "-i", "--input", dest="input", default=None,
            help=(
                "Optional input filename. If not provided the input is "
                "imported from the standard input."
            )
        ),
    )

    def handle(self, *args, **opts):
        input_filename = opts["input"]
        if input_filename and (input_filename != "-"):
            fin = open(input_filename, "rb")
        else:
            fin = sys.stdin

        with fin:
            input_ = json.load(fin)

        load_data(input_, args)


@nested_commit_on_success
def load_data(data, args=None):
    for key in args or HANDLERS:
        try:
            handler = HANDLERS[key]
        except KeyError as exc:
            raise CommandError("Invalid model entity %r!" % exc)
        for item in data.get(key, []):
            handler(item)


def set_user(data):
    """ Insert or update user object. """
    identifier = data['identifier']
    try:
        new, obj = False, User.objects.get(identifier=identifier)
    except User.DoesNotExist:
        new, obj = True, User(identifier=identifier)
    set_name_and_description(obj, data)
    obj.save()
    if 'groups' in data:
        current_groups = set(obj.groups.values_list('identifier', flat=True))
        new_groups = set(data['groups'] or [])
        for group in get_groups(current_groups - new_groups):
            obj.groups.remove(group)
        for group in get_groups(new_groups - current_groups):
            obj.groups.add(group)
    print "User %s %s." % (obj, "inserted" if new else "updated")


def set_group(data):
    """ Insert or update group object. """
    identifier = data['identifier']
    try:
        new, obj = False, Group.objects.get(identifier=identifier)
    except Group.DoesNotExist:
        new, obj = True, Group(identifier=identifier)
    set_name_and_description(obj, data)
    obj.save()
    print "Group %s %s." % (obj, "inserted" if new else "updated")


def set_process(data):
    """ Insert or update process object. """
    identifier = data['identifier']
    try:
        new, obj = False, Process.objects.get(identifier=identifier)
    except Process.DoesNotExist:
        new, obj = True, Process(identifier=identifier)
    set_name_and_description(obj, data)
    obj.save()
    set_readers(obj, data)
    print "Process %s %s." % (obj, "inserted" if new else "updated")


def set_source(data):
    """ Insert or update source object. """
    identifier = data['identifier']
    try:
        new, obj = False, SourceSeries.objects.get(eoobj__identifier=identifier)
    except SourceSeries.DoesNotExist:
        try:
            eoobj = DatasetSeries.objects.get(identifier=identifier)
        except DatasetSeries.DoesNotExist:
            eoobj = DatasetSeries(identifier=identifier)
            eoobj.save()
        new, obj = True, SourceSeries(eoobj=eoobj)
    set_name_and_description(obj, data)
    obj.save()
    set_readers(obj, data)
    print "Source %s %s." % (obj, "inserted" if new else "updated")


def set_job(data):
    """ Insert or update job object. """
    identifier = data['identifier']
    try:
        new, obj = False, Job.objects.get(identifier=identifier)
    except Job.DoesNotExist:
        owner = User.objects.get(identifier=data['owner'])
        time_series = TimeSeries.objects.get(eoobj__identifier=data['sits'])
        process = Process.objects.get(identifier=data['process'])
        inputs = json.dumps(data.get('inputs') or {})
        new, obj = True, Job(
            identifier=identifier, owner=owner, time_series=time_series,
            process=process, inputs=inputs
        )
    if not new and ('owner' not in data):
        obj.owner = User.objects.get(identifier=data['owner'])
    set_name_and_description(obj, data)
    obj.save()
    set_readers(obj, data)
    print "Job %s %s." % (obj, "inserted" if new else "updated")


def set_sits(data):
    """ Insert or update time_series object. """
    identifier = data['identifier']
    try:
        new, obj = False, TimeSeries.objects.get(eoobj__identifier=identifier)
    except TimeSeries.DoesNotExist:
        source = SourceSeries.objects.get(eoobj__identifier=data['source'])
        owner = User.objects.get(identifier=data['owner'])
        selection = json.dumps(data.get('selection') or {})
        eoobj = DatasetSeries(identifier=identifier)
        eoobj.save()
        new, obj = True, TimeSeries(
            eoobj=eoobj, owner=owner, source=source, selection=selection,
        )
    if 'editable' in data:
        obj.editable = data['editable']
    if not new and ('owner' not in data):
        obj.owner = User.objects.get(identifier=data['owner'])
    set_name_and_description(obj, data)
    obj.save()
    set_readers(obj, data)
    set_sits_content(obj, data)
    print "TimeSeries %s %s." % (obj, "inserted" if new else "updated")


HANDLERS = OrderedDict([
    ("groups", set_group),
    ("users", set_user),
    ("processes", set_process),
    ("sources", set_source),
    ("sits", set_sits),
    ("jobs", set_job),
])


def set_name_and_description(obj, data):
    """ Set model name and description. """
    if 'name' in data:
        obj.name = data['name']
    if 'description' in data:
        obj.description = data['description']
    return obj


def set_readers(obj, data):
    """ Set model readers. """
    if 'readers' in data:
        current_readers = set(obj.readers.values_list('identifier', flat=True))
        new_readers = set(data['readers'] or [])
        for group in get_entities(current_readers - new_readers):
            obj.readers.remove(group)
        for group in get_entities(new_readers - current_readers):
            obj.readers.add(group)
    return obj


def set_sits_content(obj, data):
    """ Set time_series coverages. """
    if 'content' in data:
        old_covs = set(get_coverage_ids(obj.eoobj))
        new_covs = set(data['content'] or [])
        for coverage in get_coverages(old_covs - new_covs):
            obj.eoobj.remove(coverage)
        for coverage in get_coverages(new_covs - old_covs):
            obj.eoobj.insert(coverage)
    return obj


def get_groups(ids):
    """ Generate Groups from the id list. """
    for id_ in ids:
        yield Group.objects.get(identifier=id_)


def get_entities(ids):
    """ Generate Entities from the id list. """
    for id_ in ids:
        yield Entity.objects.get(identifier=id_)


def get_coverages(ids):
    """ Generate Coverages from the is list. """
    for id_ in ids:
        yield Coverage.objects.get(identifier=id_)


def get_coverage_ids(eoobj):
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
