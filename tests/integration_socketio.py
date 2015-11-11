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
from future.utils import itervalues

#---- Imports ------------------------------------------------------------

import logging
import os
from twisted.internet import (
    defer as t_defer,
    endpoints as t_endpoints,
    reactor,
)
import unittest

from txsocketio.retry import deferredtimeout
from txsocketio.socketio import (
    SIO_TYPE_NAMES_BY_CODE,
    SocketIo,
)
import tests # pylint: disable=unused-import
from .integration_engineio import BaseIntegrationTestCase
from .symmetries import mock

#---- Constants ----------------------------------------------------------

__all__ = ()

_LOGGER = logging.getLogger(__name__)

#---- Classes ------------------------------------------------------------

#=========================================================================
class SocketIoIntegrationTestCase(BaseIntegrationTestCase):

    #---- Public hooks ---------------------------------------------------

    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()

    @t_defer.inlineCallbacks
    def test_echo_ack(self):
        self.url.path = b'/echo_ack/socket.io/'
        socketio, handler = self._mksocketio()

        yield socketio.start()
        self.assertTrue(socketio.running)

        callback_d = t_defer.Deferred()

        def _callback(path, *args, **kw):
            callback_d.callback(( path, args, kw ))

        yield socketio.emit('msg', 'Hey')
        yield socketio.emit('msg', 'you')
        yield socketio.emit('msg', 'guys!', callback=_callback)
        yield deferredtimeout(reactor, 5, callback_d)
        self.assertTrue(callback_d.called)
        self.assertEqual(callback_d.result, ( '/', ( [], ), {} ))

        yield socketio.stop()
        yield deferredtimeout(reactor, 10, self.close_d)
        self.assertTrue(self.close_d.called)
        self.assertFalse(socketio.running)

        self.assertGreaterEqual(len(handler.call_args_list), 4)
        self.assertIn(mock.call('open'), handler.call_args_list)
        self.assertIn(mock.call('connect', '/', ''), handler.call_args_list)
        self.assertIn(mock.call('event', '/', [ 'msg', 'Hey' ]), handler.call_args_list)
        self.assertIn(mock.call('event', '/', [ 'msg', 'you' ]), handler.call_args_list)
        self.assertIn(mock.call('event', '/', [ 'msg', 'guys!' ]), handler.call_args_list)
        self.assertIn(mock.call('ack', '/', []), handler.call_args_list)
        self.assertIn(mock.call('close'), handler.call_args_list)

    #---- Public methods -------------------------------------------------

    def registermock(self, dispatcher):
        handler = super().registermock(dispatcher)

        for event in itervalues(SIO_TYPE_NAMES_BY_CODE):
            self.assertTrue(dispatcher.register(event, handler))

        return handler

    #---- Private static methods -----------------------------------------

    def _mksocketio(self, url_bytes=None):
        url_bytes = self.url.unsplit() if url_bytes is None else url_bytes
        socketio = SocketIo(url_bytes)
        handler = self.registermock(socketio)
        socketio.register('close', self.close_handler)

        return socketio, handler


#=========================================================================
class InsightIntegrationTestCase(SocketIoIntegrationTestCase):

    timeout = 600

    #---- Public hooks ---------------------------------------------------

    @unittest.skipUnless(os.environ.get('TEST_INSIGHT') and hasattr(t_endpoints, 'TLSWrapperClientEndpoint'), 'TEST_INSIGHT not set or OpenSSL not available')
    @t_defer.inlineCallbacks
    def test_insight(self):
        socketio, handler = self._mksocketio(b'https://insight.bitpay.com/socket.io/')

        yield socketio.start()
        self.assertTrue(socketio.running)

        yield socketio.emit('subscribe', 'inv')
        from twisted.internet import task as t_task
        yield t_task.deferLater(reactor, 30, lambda: None)
        yield socketio.stop()
        yield deferredtimeout(reactor, 10, self.close_d)
        self.assertTrue(self.close_d.called)
        self.assertFalse(socketio.running)
        # import debug # TODO pylint: disable=reimported,unused-variable,useless-suppression

#---- Initialization -----------------------------------------------------

if __name__ == '__main__':
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    from unittest import main
    main()
