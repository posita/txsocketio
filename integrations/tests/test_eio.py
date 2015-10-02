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

try:
    from unittest import mock # pylint: disable=no-name-in-module,useless-suppression
except ImportError:
    import mock # pylint: disable=import-error,useless-suppression

try:
    from urllib import parse # pylint: disable=no-name-in-module,useless-suppression
except ImportError:
    import urllib as parse

from twisted.internet import (
    defer as t_defer,
    reactor,
    # task as t_task,
)
from twisted.trial import unittest as t_unittest

from txsocketio.endpoint import BaseUrl
from txsocketio.engineio import (
    EngineIo,
    PACKET_TYPE_CLOSE,
    PACKET_TYPE_NAMES_BY_CODE,
    PollingTransport,
    TRANSPORT_STATE_CONNECTED,
    TRANSPORT_STATE_CONNECTING,
    TRANSPORT_STATE_DISCONNECTED,
    TRANSPORT_STATE_DISCONNECTING,
    TRANSPORT_STATE_RECEIVING,
    TransportContext,
    TransportStateError,
)
from txsocketio.retry import deferredtimeout

#---- Constants ----------------------------------------------------------

__all__ = ()

_LOGGER = logging.getLogger(__name__)

#---- Classes ------------------------------------------------------------

#=========================================================================
class _IntegrationTestCase(t_unittest.TestCase):

    longMessage = True

    #---- Public hooks ---------------------------------------------------

    def setUp(self):
        super().setUp()
        self.url = BaseUrl.fromString(b'unix://<sockpath>/<path>')
        sockpath = './integrations/node/http.sock'
        self.url.netloc = parse.quote(sockpath.encode('utf_8'), safe=b'').encode('ascii')
        self.close_d = t_defer.Deferred()

        def _close_handler(event):
            _LOGGER.debug('_close_handler() called with %r', event)

            return reactor.callLater(0, self.close_d.callback, None)

        self.close_handler = _close_handler

    def tearDown(self):
        super().tearDown()

    #---- Private methods ------------------------------------------------

    def _registermock(self, dispatcher):
        handler = mock.Mock(return_value=None)

        for event in itervalues(PACKET_TYPE_NAMES_BY_CODE):
            self.assertTrue(dispatcher.register(event, handler))

        return handler

#=========================================================================
class PollingTransportIntegrationTestCase(_IntegrationTestCase):

    #---- Public hooks ---------------------------------------------------

    def setUp(self):
        super().setUp()
        transport_factory = PollingTransport.Factory()
        self.transport = transport_factory.buildTransport(reactor)
        self.transport.register('close', self.close_handler)
        self.hander = self._registermock(self.transport)

    def tearDown(self):
        super().tearDown()

    @t_defer.inlineCallbacks
    def test_closepacketafterupgradetoself(self):
        self.url.path = b'/clientclose/engine.io/'
        tc = TransportContext(self.url)

        connect_d = self.transport.connect(tc)
        self.assertIn(self.transport.state, ( TRANSPORT_STATE_CONNECTING, TRANSPORT_STATE_CONNECTED ))

        yield connect_d
        self.assertEqual(self.transport.state, TRANSPORT_STATE_CONNECTED)
        self.assertIsNotNone(tc.session_id)

        disconnect_d = self.transport.standby()
        self.assertIn(self.transport.state, ( TRANSPORT_STATE_DISCONNECTED, TRANSPORT_STATE_DISCONNECTING ))

        yield disconnect_d
        self.assertEqual(self.transport.state, TRANSPORT_STATE_DISCONNECTED)
        self.assertIsNotNone(tc.session_id)

        old_session_id = tc.session_id
        connect_d = self.transport.connect(tc)
        self.assertIn(self.transport.state, ( TRANSPORT_STATE_CONNECTING, TRANSPORT_STATE_RECEIVING ))

        yield connect_d
        self.assertEqual(self.transport.state, TRANSPORT_STATE_RECEIVING)
        self.assertEqual(tc.session_id, old_session_id)

        yield self.transport.sendpacket(PACKET_TYPE_CLOSE, '')
        yield deferredtimeout(reactor, 10, self.close_d)
        self.assertTrue(self.close_d.called)
        self.assertEqual(self.transport.state, TRANSPORT_STATE_DISCONNECTED)
        self.assertIsNone(tc.session_id)

    @t_defer.inlineCallbacks
    def test_disconnectafterconnected(self):
        self.url.path = b'/clientclose/engine.io/'
        tc = TransportContext(self.url)

        connect_d = self.transport.connect(tc)
        self.assertIn(self.transport.state, ( TRANSPORT_STATE_CONNECTING, TRANSPORT_STATE_CONNECTED ))

        yield connect_d
        self.assertEqual(self.transport.state, TRANSPORT_STATE_CONNECTED)
        self.assertIsNotNone(tc.session_id)

        disconnect_d = self.transport.disconnect()
        self.assertIn(self.transport.state, ( TRANSPORT_STATE_DISCONNECTED, TRANSPORT_STATE_DISCONNECTING ))
        self.assertRaises(TransportStateError, self.transport.standby)
        self.assertRaises(TransportStateError, self.transport.disconnect)

        yield disconnect_d
        self.assertEqual(self.transport.state, TRANSPORT_STATE_DISCONNECTED)
        self.assertIsNone(tc.session_id)

        yield deferredtimeout(reactor, 10, self.close_d)
        self.assertTrue(self.close_d.called)

    @t_defer.inlineCallbacks
    def test_disconnectafterupgradetoself(self):
        self.url.path = b'/clientclose/engine.io/'
        tc = TransportContext(self.url)

        connect_d = self.transport.connect(tc)
        self.assertIn(self.transport.state, ( TRANSPORT_STATE_CONNECTING, TRANSPORT_STATE_CONNECTED ))

        yield connect_d
        self.assertEqual(self.transport.state, TRANSPORT_STATE_CONNECTED)
        self.assertIsNotNone(tc.session_id)

        disconnect_d = self.transport.standby()
        self.assertIn(self.transport.state, ( TRANSPORT_STATE_DISCONNECTED, TRANSPORT_STATE_DISCONNECTING ))

        yield disconnect_d
        self.assertEqual(self.transport.state, TRANSPORT_STATE_DISCONNECTED)
        self.assertIsNotNone(tc.session_id)

        old_session_id = tc.session_id
        connect_d = self.transport.connect(tc)
        self.assertIn(self.transport.state, ( TRANSPORT_STATE_CONNECTING, TRANSPORT_STATE_RECEIVING ))

        yield connect_d
        self.assertEqual(self.transport.state, TRANSPORT_STATE_RECEIVING)
        self.assertEqual(tc.session_id, old_session_id)

        disconnect_d = self.transport.disconnect()
        self.assertIn(self.transport.state, ( TRANSPORT_STATE_DISCONNECTED, TRANSPORT_STATE_DISCONNECTING ))
        self.assertRaises(TransportStateError, self.transport.standby)
        self.assertRaises(TransportStateError, self.transport.disconnect)

        yield disconnect_d
        self.assertEqual(self.transport.state, TRANSPORT_STATE_DISCONNECTED)
        self.assertIsNone(tc.session_id)

        yield deferredtimeout(reactor, 10, self.close_d)
        self.assertTrue(self.close_d.called)

    @t_defer.inlineCallbacks
    def test_disconnectbeforeconnected(self):
        self.url.path = b'/clientclose/engine.io/'
        tc = TransportContext(self.url)

        connect_d = self.transport.connect(tc)
        self.assertEqual(self.transport.state, TRANSPORT_STATE_CONNECTING)
        self.assertRaises(TransportStateError, self.transport.connect, tc)

        disconnect_d = self.transport.disconnect()
        self.assertIn(self.transport.state, ( TRANSPORT_STATE_DISCONNECTED, TRANSPORT_STATE_DISCONNECTING ))
        self.assertRaises(TransportStateError, self.transport.standby)
        self.assertRaises(TransportStateError, self.transport.disconnect)

        yield disconnect_d

        with self.assertRaises(t_defer.CancelledError):
            yield connect_d

        self.assertEqual(self.transport.state, TRANSPORT_STATE_DISCONNECTED)
        self.assertIsNone(tc.session_id)

        yield deferredtimeout(reactor, 10, self.close_d)
        self.assertTrue(self.close_d.called)

#=========================================================================
class EngineIoIntegrationTestCase(_IntegrationTestCase):

    #---- Public hooks ---------------------------------------------------

    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()

    @t_defer.inlineCallbacks
    def test_closepacketafterstarted(self):
        self.url.path = b'/clientclose/engine.io/'
        engineio, handler = self._mkengineio()

        yield engineio.start()
        self.assertTrue(engineio.running)

        yield engineio.sendpacket(PACKET_TYPE_CLOSE)
        yield deferredtimeout(reactor, 10, self.close_d)
        self.assertTrue(self.close_d.called)
        self.assertFalse(engineio.running)
        self.assertIsNone(engineio._transport_context.session_id) # pylint: disable=protected-access
        self.assertGreaterEqual(len(handler.call_args_list), 2)

        expected = [
            mock.call('open'),
        ]

        self.assertEqual(handler.call_args_list[:1], expected)

        expected = [
            mock.call('close'),
        ]

        self.assertEqual(handler.call_args_list[-1:], expected)

    @t_defer.inlineCallbacks
    def test_closepacketafterstarteddelay(self):
        self.url.path = b'/clientclose/engine.io/'
        engineio, handler = self._mkengineio()

        def _sendclose(event): # pylint: disable=unused-argument
            reactor.callLater(1, engineio.sendpacket, PACKET_TYPE_CLOSE)

        engineio.register('open', _sendclose)

        yield engineio.start()
        self.assertTrue(engineio.running)

        yield deferredtimeout(reactor, 10, self.close_d)
        self.assertTrue(self.close_d.called)
        self.assertFalse(engineio.running)
        self.assertIsNone(engineio._transport_context.session_id) # pylint: disable=protected-access
        self.assertGreaterEqual(len(handler.call_args_list), 3)

        expected = [
            mock.call('open'),
            mock.call('message', b'Hello!'),
        ]

        self.assertEqual(handler.call_args_list[:2], expected)

        expected = [
            mock.call('close'),
        ]

        self.assertEqual(handler.call_args_list[-1:], expected)

    @t_defer.inlineCallbacks
    def test_stopafterstarted(self):
        self.url.path = b'/clientclose/engine.io/'
        engineio, handler = self._mkengineio()

        yield engineio.start()
        self.assertTrue(engineio.running)

        stop_d = engineio.stop()
        self.assertRaises(TransportStateError, engineio.stop)

        yield stop_d
        yield deferredtimeout(reactor, 10, self.close_d)
        self.assertTrue(self.close_d.called)
        self.assertFalse(engineio.running)
        self.assertIsNone(engineio._transport_context.session_id) # pylint: disable=protected-access
        self.assertGreaterEqual(len(handler.call_args_list), 1)

        expected = [
            mock.call('open'),
        ]

        self.assertEqual(handler.call_args_list[:1], expected)

    @t_defer.inlineCallbacks
    def test_hello(self):
        self.url.path = b'/hello/engine.io/'
        engineio, handler = self._mkengineio()

        yield engineio.start()
        self.assertTrue(engineio.running)

        yield deferredtimeout(reactor, 10, self.close_d)
        self.assertTrue(self.close_d.called)
        self.assertFalse(engineio.running)
        self.assertIsNone(engineio._transport_context.session_id) # pylint: disable=protected-access
        self.assertGreaterEqual(len(handler.call_args_list), 3)

        expected = [
            mock.call('open'),
            mock.call('message', b'Hello!'),
        ]

        self.assertEqual(handler.call_args_list[:2], expected)

        expected = [
            mock.call('close'),
        ]

        self.assertEqual(handler.call_args_list[-1:], expected)

    @t_defer.inlineCallbacks
    def test_hellodelay(self):
        self.url.path = b'/hellodelay/engine.io/'
        engineio, handler = self._mkengineio()

        yield engineio.start()
        self.assertTrue(engineio.running)

        yield deferredtimeout(reactor, 10, self.close_d)
        self.assertTrue(self.close_d.called)
        self.assertFalse(engineio.running)
        self.assertIsNone(engineio._transport_context.session_id) # pylint: disable=protected-access
        self.assertGreaterEqual(len(handler.call_args_list), 3)

        expected = [
            mock.call('open'),
            mock.call('message', b'Hello!'),
        ]

        self.assertEqual(handler.call_args_list[:2], expected)

        expected = [
            mock.call('close'),
        ]

        self.assertEqual(handler.call_args_list[-1:], expected)

    #---- Private static methods -----------------------------------------

    def _mkengineio(self):
        url_bytes = self.url.unsplit()
        engineio = EngineIo(url_bytes)
        handler = self._registermock(engineio)
        engineio.register('close', self.close_handler)

        return engineio, handler

#---- Initialization -----------------------------------------------------

if __name__ == '__main__':
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    from unittest import main
    main()
