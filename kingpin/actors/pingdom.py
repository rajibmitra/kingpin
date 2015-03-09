# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Copyright 2014 Nextdoor.com, Inc

"""Pingdom Actor objects"""

import logging
import os

from tornado import gen

from kingpin.constants import REQUIRED
from kingpin.actors import base
from kingpin.actors import exceptions
from kingpin.actors.support import api

log = logging.getLogger(__name__)

__author__ = 'Matt Wise <matt@nextdoor.com>'


USER = os.getenv('PINGDOM_USER', None)
PASS = os.getenv('PINGDOM_PASS', None)
TOKEN = os.getenv('PINGDOM_TOKEN', None)


class PingdomAPI(api.RestConsumer):

    _ENDPOINT = 'https://api.pingdom.com'
    _CONFIG = {
        'attrs': {
            'checks': {
                'path': '/api/2.0/checks',
                'http_methods': {'get': {}}
            },
            'check': {
                'path': '/api/2.0/checks/%check_id%',
                'http_methods': {'put': {}}
            },
        },
        'auth': {
            'user': USER,
            'pass': PASS
        }
    }


class PingdomBase(base.BaseActor):

    """Simple Pingdom Abstract Base Object"""

    all_options = {
        'name': (str, REQUIRED, 'Name of the check'),
    }

    def __init__(self, *args, **kwargs):
        """Check required environment variables."""
        super(PingdomBase, self).__init__(*args, **kwargs)

        if not TOKEN:
            raise exceptions.InvalidCredentials(
                'Missing the "PINGDOM_TOKEN" environment variable.')

        rest_client = api.RestClient(
            headers={'App-Key': TOKEN}
        )
        self._pingdom_client = PingdomAPI(client=rest_client)

    @gen.coroutine
    def _get_check(self):
        resp = yield self._pingdom_client.checks().http_get()
        all_checks = resp['checks']
        check = [c for c in all_checks
                 if c['name'] == self.option('name')]

        if not check:
            raise exceptions.InvalidOptions(
                'Check name "%s" was not found.' % self.option('name'))

        raise gen.Return(check[0])


class Pause(PingdomBase):
    """Start Pingdom Maintenance.
    
    Pause a particular "check" on Pingdom."""

    @gen.coroutine
    def _execute(self):
        check = yield self._get_check()

        if self._dry:
            self.log.info('Would pause %s (%s) pingdom check.' % (
                check['name'], check['hostname']))
            raise gen.Return()

        self.log.info('Pausing %s' % check['name'])
        yield self._pingdom_client.check(
            check_id=check['id']).http_put(paused='true')


class Unause(PingdomBase):
    """Stop Pingdom Maintenance.
    
    Unpause a particular "check" on Pingdom."""

    @gen.coroutine
    def _execute(self):
        check = yield self._get_check()

        if self._dry:
            self.log.info('Would unpause %s (%s) pingdom check.' % (
                check['name'], check['hostname']))
            raise gen.Return()

        self.log.info('Unpausing %s' % check['name'])
        yield self._pingdom_client.check(
            check_id=check['id']).http_put(paused='false')
