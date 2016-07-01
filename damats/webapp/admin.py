#-------------------------------------------------------------------------------
#
#  DAMATS web app Django admin
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
# pylint: disable=no-init
# pylint: disable=missing-docstring

from django.core.exceptions import ValidationError
from django import forms
from django.contrib import admin
from damats.webapp.models import (
    User, Group, Process, SourceSeries, TimeSeries, Job, Result,
)

#-------------------------------------------------------------------------------
# utilities
def update_related(target, items):
    """ Update related from the list of items. """
    target.clear()
    for item in items:
        target.add(item)

#-------------------------------------------------------------------------------
# Users ans Groups (a.k.a. Entities)

class BaseEntityForm(forms.ModelForm):
    """ Base form class used by all entities. """
    sources = forms.ModelMultipleChoiceField(
        label='Sources',
        widget=admin.widgets.FilteredSelectMultiple('SourceSeries', False),
        queryset=SourceSeries.objects.all(),
        required=False,
    )
    processes = forms.ModelMultipleChoiceField(
        label='Processes',
        widget=admin.widgets.FilteredSelectMultiple('Processes', False),
        queryset=Process.objects.all(),
        required=False,
    )


class BaseEntityAdmin(admin.ModelAdmin):
    """ Base admin class used by all entities. """
    def save_model(self, request, obj, form, change):
        super(BaseEntityAdmin, self).save_model(request, obj, form, change)
        update_related(obj.sources, form.cleaned_data['sources'])
        update_related(obj.processes, form.cleaned_data['processes'])

    def get_form(self, request, obj=None, **kwargs):
        self.form.base_fields['sources'].initial = (
            obj.sources.values_list('pk', flat=True) if obj else []
        )
        self.form.base_fields['processes'].initial = (
            obj.processes.values_list('pk', flat=True) if obj else []
        )
        return super(BaseEntityAdmin, self).get_form(request, obj, **kwargs)

    def get_readonly_fields(self, request, obj=None):
        read_only_fields = []
        constant_fields = ['identifier']
        # constant fields are changed only when creating new object
        if obj: # modifying an existing object
            return read_only_fields + constant_fields
        else: # creating new object
            return read_only_fields


class UserAdminForm(BaseEntityForm):
    def clean_identifier(self):
        # user id must not start with @
        id_ = self.cleaned_data["identifier"]
        if id_[:1] == '@':
            id_ = id_[1:]
        return id_


class UserAdmin(BaseEntityAdmin):
    form = UserAdminForm
    model = User
    fields = (
        'active',
        'identifier',
        'name',
        'description',
        'groups',
        'sources',
        'processes',
    )
    filter_horizontal = ['groups']
    search_fields = ['identifier', 'name']

admin.site.register(User, UserAdmin)


class GroupAdminForm(BaseEntityForm):
    users = forms.ModelMultipleChoiceField(
        label='Users',
        widget=admin.widgets.FilteredSelectMultiple('Users', False),
        queryset=User.objects.all(),
        required=False,
    )

    def clean_identifier(self):
        # group id must always start with @
        id_ = self.cleaned_data["identifier"]
        if id_[:1] != '@':
            id_ = '@' + id_
        return id_


class GroupAdmin(BaseEntityAdmin):
    form = GroupAdminForm
    model = Group
    fields = (
        'identifier',
        'name',
        'description',
        'users',
        'sources',
        'processes',
    )
    search_fields = ['identifier', 'name']

    def save_model(self, request, obj, form, change):
        super(GroupAdmin, self).save_model(request, obj, form, change)
        update_related(obj.users, form.cleaned_data['users'])

    def get_form(self, request, obj=None, **kwargs):
        self.form.base_fields['users'].initial = (
            obj.users.values_list('pk', flat=True) if obj else []
        )
        return super(GroupAdmin, self).get_form(request, obj, **kwargs)

admin.site.register(Group, GroupAdmin)

#-------------------------------------------------------------------------------
# Image Time Series

class SourceSeriesAdmin(admin.ModelAdmin):
    model = SourceSeries
    fields = (
        'name',
        'description',
        'eoobj',
        'readers',
    )
    filter_horizontal = ['readers']
    search_fields = ['name']

    def get_readonly_fields(self, request, obj=None):
        read_only_fields = []
        constant_fields = ['eoobj']
        # constant fields are changed only when creating new object
        if obj: # modifying an existing object
            return read_only_fields + constant_fields
        else: # creating new object
            return read_only_fields

admin.site.register(SourceSeries, SourceSeriesAdmin)


class TimeSeriesAdmin(admin.ModelAdmin):
    model = TimeSeries
    fields = (
        'locked',
        'name',
        'description',
        'source',
        'selection',
        'eoobj',
        'owner',
        'readers',
    )
    filter_horizontal = ['readers']
    search_fields = ['name']

    def get_readonly_fields(self, request, obj=None):
        read_only_fields = []
        constant_fields = ['eoobj', 'owner', 'source']
        # constant fields are changed only when creating new object
        if obj: # modifying an existing object
            return read_only_fields + constant_fields
        else: # creating new object
            return read_only_fields

admin.site.register(TimeSeries, TimeSeriesAdmin)

#-------------------------------------------------------------------------------
# Processes

class ProcessAdmin(admin.ModelAdmin):
    model = Process
    fields = (
        'identifier',
        'name',
        'description',
        'readers',
    )
    filter_horizontal = ['readers']
    search_fields = ['name', 'identifier']

    def get_readonly_fields(self, request, obj=None):
        read_only_fields = []
        constant_fields = ['identifier']
        # constant fields are changed only when creating new object
        if obj: # modifying an existing object
            return read_only_fields + constant_fields
        else: # creating new object
            return read_only_fields

admin.site.register(Process, ProcessAdmin)


class JobAdmin(admin.ModelAdmin):
    model = Job
    fields = (
        'identifier',
        'name',
        'description',
        'owner',
        'status',
        'created',
        'updated',
        'readers',
        'process',
        'inputs',
        'outputs',
        #'results',
    )

    filter_horizontal = ['readers']
    search_fields = ['name', 'identifier']

    def get_readonly_fields(self, request, obj=None):
        read_only_fields = ['created', 'updated', 'status']
        constant_fields = ['identifier', 'process']
        # constant fields are changed only when creating new object
        if obj: # modifying an existing object
            return read_only_fields + constant_fields
        else: # creating new object
            return read_only_fields

admin.site.register(Job, JobAdmin)


class ResultAdmin(admin.ModelAdmin):
    model = Result
    fields = (
        'name',
        'description',
        'eoobj',
        'job',
    )

    def get_readonly_fields(self, request, obj=None):
        read_only_fields = []
        constant_fields = ['job', 'eoobj']
        # constant fields are changed only when creating new object
        if obj: # modifying an existing object
            return read_only_fields + constant_fields
        else: # creating new object
            return read_only_fields

admin.site.register(Result, ResultAdmin)
