#-------------------------------------------------------------------------------
#
#  DAMATS web app Django models
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
# pylint: disable=old-style-class
# pylint: disable=too-few-public-methods
# pylint: disable=no-init
# pylint: disable=missing-docstring

#from django.db import models
from django.db.models import (
    Model, BooleanField, CharField, TextField, DateTimeField,
    OneToOneField, ForeignKey, ManyToManyField,
)
from django.db.models.signals import post_delete
from django.dispatch import receiver
#from django.core.validators import MaxValueValidator, MinValueValidator
from eoxserver.resources.coverages.models import (
    DatasetSeries, RectifiedDataset,
)

#-------------------------------------------------------------------------------
# Users ans Groups

class Entity(Model):
    """ Base model for Users and Group. """
    identifier = CharField(
        max_length=256, null=False, blank=False, unique=True
    )
    name = CharField(max_length=256, null=True, blank=True)
    description = TextField(null=True, blank=True)

    class Meta:
        verbose_name = "DAMATS User or Group"
        verbose_name_plural = "0. DAMATS Users and Groups"

    def __unicode__(self):
        name = self.identifier
        if self.name:
            name = "%s (%s)" % (self.name, name)
        return name


class Group(Entity):
    """ Group model."""
    class Meta:
        verbose_name = "DAMATS Group"
        verbose_name_plural = "2. DAMATS Groups"


class User(Entity):
    """ User model."""
    active = BooleanField(default=True)
    groups = ManyToManyField(Group, blank=True, related_name='users')

    class Meta:
        verbose_name = "DAMATS User"
        verbose_name_plural = "1. DAMATS Users"

#-------------------------------------------------------------------------------
# Image Time Series

class SourceSeries(Model):
    """ DAMATS Source Image Series
    """
    EOOBJ_CLASS = DatasetSeries
    eoobj = OneToOneField(
        EOOBJ_CLASS, related_name='damats_sources',
        verbose_name='Related Dataset Series'
    )
    name = CharField(max_length=256, null=False, blank=False)
    description = TextField(null=True, blank=True)
    created = DateTimeField(auto_now_add=True)
    updated = DateTimeField(auto_now=True)
    readers = ManyToManyField(Entity, blank=True, related_name='sources')

    class Meta:
        verbose_name = "DAMATS Source Image Series"
        verbose_name_plural = "3. DAMATS Source Image Series"

    def __unicode__(self):
        name = self.eoobj.identifier
        if self.name:
            name = "%s (%s)" % (self.name, name)
        return name


class TimeSeries(Model):
    """ DAMATS Image Time Series (aka SITS)
    """
    EOOBJ_CLASS = DatasetSeries
    eoobj = OneToOneField(
        EOOBJ_CLASS, related_name='damats_time_series',
        verbose_name='Related Dataset Series'
    )
    name = CharField(max_length=256, null=False, blank=False)
    description = TextField(null=True, blank=True)
    source = ForeignKey(SourceSeries, related_name='time_series')
    selection = TextField(null=True, blank=True)
    owner = ForeignKey(User, related_name='time_series')
    editable = BooleanField(default=True)

    readers = ManyToManyField(
        Entity, blank=True, related_name='time_series_ro',
    )

    created = DateTimeField(auto_now_add=True)
    updated = DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "DAMATS Image Time Series"
        verbose_name_plural = "4. DAMATS Image Time Series"

    def __unicode__(self):
        name = self.eoobj.identifier
        if self.name:
            name = "%s (%s)" % (self.name, name)
        return name

#-------------------------------------------------------------------------------
# Jobs, Processes and Results

class Process(Model):
    """ DAMATS Process
    """
    identifier = CharField(
        max_length=512, null=False, blank=False, unique=True
    )
    name = CharField(max_length=256, null=True, blank=True)
    description = TextField(null=True, blank=True)
    readers = ManyToManyField(
        Entity, blank=True, related_name='processes'
    )

    class Meta:
        verbose_name = "DAMATS Process"
        verbose_name_plural = "6. DAMATS Processes"

    def __unicode__(self):
        name = self.identifier
        if self.name:
            name = "%s (%s)" % (self.name, name)
        return name


class Job(Model):
    """ DAMATS Processing Job
    """
    CREATED = 'C'           # Created
    ACCEPTED = 'E'          # Enqueued
    IN_PROGRESS = 'R'       # Running
    FINISHED = 'S'          # Success
    ABORTED = 'A'           # Aborted
    FAILED = 'F'            # Failed

    STATUS_CHOICES = (
        (CREATED, "CREATED"),
        (ACCEPTED, "ACCEPTED"),
        (IN_PROGRESS, "IN_PROGRESS"),
        (FINISHED, "FINISHED"),
        (ABORTED, "ABORTED"),
        (FAILED, "FAILED"),
    )

    identifier = CharField(
        max_length=256, null=False, blank=False, unique=True
    )
    name = CharField(max_length=256, null=True, blank=True)
    description = TextField(null=True, blank=True)
    owner = ForeignKey(User, related_name='jobs')
    readers = ManyToManyField(Entity, related_name='jobs_ro')
    created = DateTimeField(auto_now_add=True)
    updated = DateTimeField(auto_now=True)
    # process details
    status = CharField(
        max_length=1, choices=STATUS_CHOICES, default=CREATED
    )
    time_series = ForeignKey(TimeSeries, related_name='jobs')
    process = ForeignKey(Process, related_name='jobs')
    inputs = TextField(null=True, blank=True) # processing inputs
    outputs = TextField(null=True, blank=True) # processing outputs
    wps_job_id = CharField(max_length=256, null=True, blank=True)
    wps_response_url = CharField(max_length=512, null=True, blank=True)

    class Meta:
        verbose_name = "DAMATS Process Job"
        verbose_name_plural = "7. DAMATS Process Jobs"

    def __unicode__(self):
        name = self.identifier
        if self.name:
            name = "%s (%s)" % (self.name, name)
        return name


class Result(Model):
    """ DAMATS Processing Result - base of the SourceSeries and TimeSeries.
    """
    EOOBJ_CLASS = RectifiedDataset
    eoobj = OneToOneField(
        EOOBJ_CLASS, related_name='damats_result',
        verbose_name='Related EO Object'
    )
    identifier = CharField(max_length=256, null=False, blank=False)
    name = CharField(max_length=256, null=True, blank=True)
    description = TextField(null=True, blank=True)
    job = ForeignKey(Job, related_name='results')
    created = DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "DAMATS Job Result"
        verbose_name_plural = "8. DAMATS Job Results"

    def __unicode__(self):
        name = self.eoobj.identifier
        if self.name:
            name = "%s (%s)" % (self.identifier, name)
        return name

# Make sure EO object linked by the result gets removed upon Result removal ...
@receiver(post_delete, sender=Result)
def post_delete_result(sender, instance, *args, **kwargs):
    if instance.eoobj: # just in case user is not specified
        instance.eoobj.delete()
