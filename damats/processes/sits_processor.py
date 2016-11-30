#-------------------------------------------------------------------------------
#
#  DAMATS SITS processor base class
#
# Project: DAMATS
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
# pylint: disable=too-few-public-methods, unused-argument

from eoxserver.core import Component, implements
from eoxserver.services.ows.wps.interfaces import ProcessInterface
from eoxserver.services.ows.wps.parameters import LiteralData, RequestParameter
from eoxserver.services.ows.wps.exceptions import (
    NoApplicableCode, InvalidInputValueError,
)
from damats.util.config import WEBAPP_CONFIG
from damats.webapp.models import User, Process, Job, TimeSeries
from damats.webapp.views_time_series import get_time_series
from damats.processes.utils import (
    update_object, get_header, get_meta,
)


class SITSProcessor(Component):
    """ Base DAMATS SITS Processor WPS process class. """
    implements(ProcessInterface)
    abstract = True # abstract base class

    indentifier = None # must be overridden by the child class
    synchronous = False
    asynchronous = True
    metadata = {}
    profiles = ["DAMATS-SITS-processor"]

    inputs = [
        ("sits_id", LiteralData(
            'sits', str,
            title="Satellite Image Time Series (SITS)",
            abstract="Satellite Image Time Series (SITS) identifier."
        )),
        ('user_name', RequestParameter(get_meta(
            "REMOTE_USER", WEBAPP_CONFIG.default_user
        ))),
        ('job_id', RequestParameter(get_header("X-DAMATS-Job-Id", None))),
    ]

    outputs = [
        ("debug_output", str), # to be removed
    ]

    def initialize(self, context, inputs, outputs, parts):
        """ Asynchronous process initialization. """
        user_name = inputs['\\user_name']
        job_id = inputs['\\job_id']

        # check user service authorisation
        try:
            user = get_user(user_name)
        except User.DoesNotExist:
            raise NoApplicableCode(
                'This process requires an authorized user!', 'Unauthorized'
            )

        # check user process authorisation
        try:
            process = get_process(user, self.identifier)
        except Process.DoesNotExist:
            raise NoApplicableCode(
                'The user is not authorized to invoke this process!',
                'Unauthorized'
            )

        # connect this process job to the DAMATS Job DB object
        if job_id is not None:
            try:
                job = get_job(user, process, job_id)
            except Job.DoesNotExist:
                raise NoApplicableCode(
                    'Invalid job identifier!', 'Unauthorized'
                )
            if job.wps_job_id is not None:
                raise NoApplicableCode(
                    'The job has been already executed!', 'Unauthorized'
                )
            update_object(
                job, status=Job.ACCEPTED,
                wps_job_id=context.identifier,
                wps_response_url=context.status_location,
            )

    def execute(self, sits_id, user_name, job_id, **kwargs):
        """ Execute process - do not override!
        Use process_sits() method instead.
        """
        # get the DAMATS User obejct
        user = get_user(user_name)

        # get the DAMATS Job object (if the id is available)
        if job_id:
            process = get_process(user, self.identifier)
            job = get_job(user, process, job_id)
        else:
            job = None

        # get the DAMATS TimeSeries object
        try:
            sits = get_sits(user, sits_id)
        except TimeSeries.DoesNotExist:
            raise InvalidInputValueError('sits')

        # execute the processor
        if job:
            update_object(job, status=Job.IN_PROGRESS)

        try:
            result = self.process_sits(sits=sits, user=user, job=job, **kwargs)
        except:
            if job:
                update_object(job, status=Job.FAILED)
            raise

        if job:
            update_object(job, status=Job.FINISHED)

        return result

    def process_sits(self, sits, **kwargs):
        """ Process DAMATS image time-series (SITS). """
        raise NotImplementedError


def get_user(user_id):
    """ Get the user object for the given user-name (identifier). """
    return (
        User.objects
        .prefetch_related('groups')
        .get(identifier=user_id, active=True)
    )

def get_process(user, process_id):
    """ Get DAMATS Process object for the given user and process identifier. """
    return Process.objects.filter(readers__identifier__in=(
        [user.identifier] +
        list(user.groups.values_list('identifier', flat=True))
    )).distinct().get(identifier=process_id)

def get_job(user, process, job_id):
    """ Get DAMATS Job object for the given user, process and job identifier.
    """
    return Job.objects.get(identifier=job_id, owner=user, process=process)


def get_sits(user, sits_id):
    """ Find the collection object for the given SITS collection identifier
    and the user object.
    """
    return get_time_series(user).get(eoobj__identifier=sits_id)
