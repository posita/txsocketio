#!/usr/bin/env python
#-*- encoding: utf-8; grammar-ext: py; mode: python -*-

#=========================================================================
"""
  Copyright |(c)| 2015 `Matt Bogosian`_ (|@posita|_).

  .. |(c)| unicode:: u+a9
  .. _`Matt Bogosian`: mailto:mtb19@columbia.edu
  .. |@posita| replace:: **@posita**
  .. _`@posita`: https://github.com/posita

  Please see the accompanying ``LICENSE`` (or ``LICENSE.txt``) file for
  rights and restrictions governing use of this software. All rights not
  expressly waived or licensed are reserved. If such a file did not
  accompany this software, then please contact the author before viewing
  or using this software in any capacity.
"""
#=========================================================================

from __future__ import (
    absolute_import, division, print_function, unicode_literals,
)
from builtins import * # pylint: disable=redefined-builtin,unused-wildcard-import,useless-suppression,wildcard-import
from future.builtins.disabled import * # pylint: disable=redefined-builtin,unused-wildcard-import,useless-suppression,wildcard-import

#---- Imports ------------------------------------------------------------

import io
import json
import os
import logging
import sys
import time
import unittest
from twisted.internet import (
    defer as t_defer,
    reactor,
    task as t_task,
)
from twisted.python import failure as t_failure
from twisted.trial import unittest as t_unittest
from twisted.web import (
    client as t_client,
    http_headers as t_http_headers,
)

from txsocketio.endpoint import ClientEndpointFactory
from txsocketio.symmetries import parse
import tests # pylint: disable=unused-import

#---- Constants ----------------------------------------------------------

__all__ = ()

_LOGGER = logging.getLogger(__name__)

#---- Classes ------------------------------------------------------------

#=========================================================================
class TestDeadlock(t_unittest.TestCase):

    longMessage = True

    @unittest.skipUnless(os.environ.get('TEST_DEADLOCK'), 'TEST_DEADLOCK not set')
    @t_defer.inlineCallbacks
    def test_deadlock(self):
        # Base URL naming a UNIX socket to be resolved by
        # ClientEndpointFactory
        url_bytes = b'unix://.%2Fintegrations%2Fnode%2Fhttp.sock/engine.io/?transport=polling'

        headers = t_http_headers.Headers({
            b'Accept':         [ b'application/octet-stream', b'application/json' ],
            b'Accept-Charset': [ b'UTF-8' ],
        })

        endpoint_factory = ClientEndpointFactory(reactor)
        pool = t_client.HTTPConnectionPool(reactor, persistent=False)
        agent = t_client.Agent.usingEndpointFactory(reactor, endpoint_factory, pool=pool)

        # Single GET request (gets the Engine.IO session ID)
        response = yield agent.request(b'GET', url_bytes, headers)
        body = yield t_client.readBody(response)
        session = json.loads(body[5:])['sid'].encode('utf_8')
        del body, response

        # Basic POST stuff
        post_headers = t_http_headers.Headers({
            b'Accept':         [ b'application/octet-stream', b'application/json' ],
            b'Accept-Charset': [ b'UTF-8' ],
            b'Content-Type':   [ b'application/octet-stream' ],
        })

        def _sendpacket(_session, _payload):
            post_url_bytes = url_bytes + b'&' + parse.urlencode({ b'sid': _session })
            body_producer = t_client.FileBodyProducer(io.BytesIO(_payload))
            d = agent.request(b'POST', post_url_bytes, post_headers, body_producer)
            d.addErrback(lambda _: [ _ ] if isinstance(_, t_failure.Failure) else _)
            return d

        # POST a bunch of Engine.IO packets (these are ping packets, but
        # message packets trigger deadlocks as well)
        packet_raw = b'\x00\x06\xff2probe' # b'\x00\x06\xff4abcde'
        post_deferreds = []

        for _ in range(int(os.environ.get('NUM_POSTS', 3))):
            post_deferreds.append(_sendpacket(session, packet_raw))

        def _printpostdeferreds(_summary):
            print('================================================================', file=sys.stderr)
            print(_summary, file=sys.stderr)

            for i, post_deferred in enumerate(post_deferreds):
                print('post_deferreds[{}]: {!r}'.format(i, post_deferred, file=sys.stderr))

            print('================================================================', file=sys.stderr)

        # Wait (this should be plenty of time for the above to resolve)
        spinner = "/-\\|"
        wait_seconds = 100
        now = i = time.time()
        then = now + wait_seconds

        while now < then:
            all_good = True

            for post_deferred in post_deferreds:
                all_good = all_good \
                        and post_deferred.called \
                        and not post_deferred.paused \
                        and post_deferred._chainedTo is None # pylint: disable=protected-access

            if all_good:
                break

            i = i + 1
            yield t_task.deferLater(reactor, max(0, i - time.time()), lambda: None)
            print('{}\r'.format(spinner[0]), end='', file=sys.stderr)
            spinner = spinner[1:] + spinner[:1]
            now = time.time()

        try:
            for post_deferred in post_deferreds:
                self.assertTrue(post_deferred.called)
                self.assertFalse(post_deferred.paused)
                self.assertIsNone(post_deferred._chainedTo) # pylint: disable=protected-access
        except AssertionError as e: # pylint: disable=unused-variable
            _printpostdeferreds('>>> FAIL: at least one of the requests is hung after {} seconds! <<<'.format(wait_seconds))

            try:
                import debug # TODO pylint: disable=reimported,unused-variable,useless-suppression
            except ImportError:
                pass

            raise
        else:
            _printpostdeferreds('All requests resolved')

        yield pool.closeCachedConnections()

if __name__ == '__main__':
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    from unittest import main
    main()
