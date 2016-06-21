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
from damats.webapp import models

#-------------------------------------------------------------------------------
# Users ans Groups

#class EntityAdmin(admin.ModelAdmin):
#    model = models.Entity
#    fields = (
#        'identifier',
#        'name',
#        'description',
#    )
#    search_fields = ['identifier', 'name']
#
#    # Entities cannot be added or deleted directly.
#    def has_add_permission(self, request, obj=None):
#        return False
#
#    def has_delete_permission(self, request, obj=None):
#        return False
#
#admin.site.register(models.Entity, EntityAdmin)

class UserAdminForm(forms.ModelForm):
    def clean_identifier(self):
        if str(self.cleaned_data["identifier"])[:1] == '@':
            raise ValidationError(
                "A user identifier is not allowed to start with the '@' "
                "character!"
            )
        return self.cleaned_data["identifier"]

class UserAdmin(admin.ModelAdmin):
    form = UserAdminForm
    model = models.User
    fields = (
        'locked',
        'identifier',
        'name',
        'description',
        'groups',
        'sources',
        'processes',
    )
    filter_horizontal = ['groups', 'sources', 'processes']
    search_fields = ['identifier', 'name']

    def get_readonly_fields(self, request, obj=None):
        read_only_fields = []
        constant_fields = ['identifier']
        # constant fields are changed only when creating new object
        if obj: # modifying an existing object
            return read_only_fields + constant_fields
        else: # creating new object
            return read_only_fields

admin.site.register(models.User, UserAdmin)


class GroupAdminForm(forms.ModelForm):
    def clean_identifier(self):
        if str(self.cleaned_data["identifier"])[:1] != '@':
            raise ValidationError(
                "A group identifier is required to start with the '@' "
                "character!"
            )
        return self.cleaned_data["identifier"]

class GroupAdmin(admin.ModelAdmin):
    form = GroupAdminForm
    model = models.Group
    fields = (
        'identifier',
        'name',
        'description',
        'users',
        'sources',
        'processes',
    )
    filter_horizontal = ['users', 'sources', 'processes']
    search_fields = ['identifier', 'name']

    def get_readonly_fields(self, request, obj=None):
        read_only_fields = []
        constant_fields = ['identifier']
        # constant fields are changed only when creating new object
        if obj: # modifying an existing object
            return read_only_fields + constant_fields
        else: # creating new object
            return read_only_fields

admin.site.register(models.Group, GroupAdmin)

#-------------------------------------------------------------------------------
# Image Time Series

class SourceSeriesAdmin(admin.ModelAdmin):
    model = models.SourceSeries
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

admin.site.register(models.SourceSeries, SourceSeriesAdmin)


class TimeSeriesAdmin(admin.ModelAdmin):
    model = models.TimeSeries
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

admin.site.register(models.TimeSeries, TimeSeriesAdmin)

#-------------------------------------------------------------------------------
# Processes

class ProcessAdmin(admin.ModelAdmin):
    model = models.Process
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

admin.site.register(models.Process, ProcessAdmin)

class JobAdmin(admin.ModelAdmin):
    model = models.Job
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
#        'results',
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

admin.site.register(models.Job, JobAdmin)


class ResultAdmin(admin.ModelAdmin):
    model = models.Result
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

admin.site.register(models.Result, ResultAdmin)
