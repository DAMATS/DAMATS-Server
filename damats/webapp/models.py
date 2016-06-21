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

from django.db import models
from eoxserver.resources.coverages import models as coverages
#from django.core.validators import MaxValueValidator, MinValueValidator

#-------------------------------------------------------------------------------
# Users ans Groups

class Entity(models.Model):
    """ Base model for Users and Group. """
    identifier = models.CharField(
        max_length=256, null=False, blank=False, unique=True
    )
    name = models.CharField(max_length=256, null=True, blank=True)
    description = models.TextField(null=True, blank=True)

    sources = models.ManyToManyField(
        'SourceSeries', blank=True, related_name='+readers'
    )
    time_series_ro = models.ManyToManyField(
        'TimeSeries', blank=True, related_name='+readers'
    )
    processes = models.ManyToManyField(
        'Process', blank=True, related_name='+readers'
    )

    class Meta:
        verbose_name = "DAMATS User or Group"
        verbose_name_plural = "DAMATS Users and Groups"

    def __unicode__(self):
        name = self.identifier
        if self.name:
            name = "%s (%s)" % (self.name, name)
        return name


class Group(Entity):
    """ Group model."""
    users = models.ManyToManyField(
        'User', blank=True, related_name='+users'
    )

    class Meta:
        verbose_name = "DAMATS Group"
        verbose_name_plural = "DAMATS Groups"


class User(Entity):
    """ User model."""
    locked = models.BooleanField(default=False)
    groups = models.ManyToManyField(
        Group, through=Group.users.through, blank=True, related_name='+'
    )

    class Meta:
        verbose_name = "DAMATS User"
        verbose_name_plural = "DAMATS Users"

#-------------------------------------------------------------------------------
# Image Time Series

class SourceSeries(models.Model):
    """ DAMATS Source Image Series
    """
    EOOBJ_CLASS = coverages.DatasetSeries
    eoobj = models.OneToOneField(
        EOOBJ_CLASS, related_name='damats_sources',
        verbose_name='Related Dataset Series'
    )
    name = models.CharField(max_length=256, null=False, blank=False)
    description = models.TextField(null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    readers = models.ManyToManyField(
        Entity, through=Entity.sources.through, blank=True,
        related_name='+sources'
    )

    class Meta:
        verbose_name = "DAMATS Source Image Series"
        verbose_name_plural = "DAMATS Source Image Series"

    def __unicode__(self):
        name = self.eoobj.identifier
        if self.name:
            name = "%s (%s)" % (self.name, name)
        return name


class TimeSeries(models.Model):
    """ DAMATS Image Time Series (aka SITS)
    """
    EOOBJ_CLASS = coverages.DatasetSeries
    eoobj = models.OneToOneField(
        EOOBJ_CLASS, related_name='damats_time_series',
        verbose_name='Related Dataset Series'
    )
    name = models.CharField(max_length=256, null=False, blank=False)
    description = models.TextField(null=True, blank=True)
    source = models.ForeignKey(SourceSeries, related_name='time_series')
    selection = models.TextField(null=True, blank=True)
    owner = models.ForeignKey(User, related_name='time_series')
    locked = models.BooleanField(default=False)

    readers = models.ManyToManyField(
        Entity, through=Entity.time_series_ro.through, blank=True,
        related_name='+time_series_ro',
    )

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "DAMATS Image Time Series"
        verbose_name_plural = "DAMATS Image Time Series"

    def __unicode__(self):
        name = self.eoobj.identifier
        if self.name:
            name = "%s (%s)" % (self.name, name)
        return name

#-------------------------------------------------------------------------------
# Jobs, Processes and Results

class Process(models.Model):
    """ DAMATS Process
    """
    identifier = models.CharField(
        max_length=512, null=False, blank=False, unique=True
    )
    name = models.CharField(max_length=256, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    readers = models.ManyToManyField(
        Entity, through=Entity.processes.through, blank=True,
        related_name='+processes'
    )

    class Meta:
        verbose_name = "DAMATS Process"
        verbose_name_plural = "DAMATS Processes"

    def __unicode__(self):
        name = self.identifier
        if self.name:
            name = "%s (%s)" % (self.name, name)
        return name


class Job(models.Model):
    """ DAMATS Processing Job
    """
    CREATED = 'C'
    IN_PROGRESS = 'P'
    FINISHED = 'S'
    ABORTED = 'A'
    FAILED = 'F'

    STATUS_CHOICES = (
        (CREATED, "CREATED"),
        (IN_PROGRESS, "IN_PROGRESS"),
        (FINISHED, "FINISHED"),
        (ABORTED, "ABORTED"),
        (FAILED, "FAILED"),
    )

    identifier = models.CharField(
        max_length=256, null=False, blank=False, unique=True
    )
    name = models.CharField(max_length=256, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    owner = models.ForeignKey(User, related_name='jobs')
    readers = models.ManyToManyField(Entity, related_name='jobs_ro')
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    # process details
    status = models.CharField(
        max_length=1, choices=STATUS_CHOICES, default=CREATED
    )
    process = models.ForeignKey(Process, related_name='jobs')
    inputs = models.TextField(null=True, blank=True) # processing inputs
    outputs = models.TextField(null=True, blank=True) # processing outputs

    class Meta:
        verbose_name = "DAMATS Process Job"
        verbose_name_plural = "DAMATS Process Jobs"

    def __unicode__(self):
        name = self.identifier
        if self.name:
            name = "%s (%s)" % (self.name, name)
        return name


class Result(models.Model):
    """ DAMATS Processing Result - base of the SourceSeries and TimeSeries.
    """
    EOOBJ_CLASS = coverages.RectifiedDataset
    eoobj = models.OneToOneField(
        EOOBJ_CLASS, related_name='damats_result',
        verbose_name='Related EO Object'
    )
    name = models.CharField(max_length=256, null=False, blank=False)
    description = models.TextField(null=True, blank=True)
    job = models.ForeignKey(Job, related_name='results')
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "DAMATS Job Result"
        verbose_name_plural = "DAMATS Job Results"

    def __unicode__(self):
        name = self.eoobj.identifier
        if self.name:
            name = "%s (%s)" % (self.name, name)
        return name
