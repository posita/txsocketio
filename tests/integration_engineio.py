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
from future.moves.urllib import parse as url_parse
from future.utils import itervalues

#---- Imports ------------------------------------------------------------

import logging
from twisted.internet import (
    defer as t_defer,
    error as t_error,
    reactor,
    # task as t_task,
)
from twisted.trial import unittest as t_unittest
import txrc

from txsocketio.endpoint import BaseUrl
from txsocketio.engineio import (
    EIO_TYPE_CLOSE,
    EIO_TYPE_PING,
    EIO_TYPE_NAMES_BY_CODE,
    EngineIo,
    PollingTransport,
    TRANSPORT_STATE_CONNECTED,
    TRANSPORT_STATE_CONNECTING,
    TRANSPORT_STATE_DISCONNECTED,
    TRANSPORT_STATE_DISCONNECTING,
    TRANSPORT_STATE_RECEIVING,
    TransportContext,
    TransportStateError,
)
import tests # pylint: disable=unused-import
from tests.symmetries import mock

#---- Constants ----------------------------------------------------------

__all__ = ()

_LOGGER = logging.getLogger(__name__)

#---- Classes ------------------------------------------------------------

#=========================================================================
class BaseIntegrationTestCase(t_unittest.TestCase):

    longMessage = True

    #---- Public hooks ---------------------------------------------------

    def setUp(self):
        super().setUp()
        self.url = BaseUrl.fromString(b'unix://<sockpath>/<path>')
        sockpath = './integrations/node/http.sock'
        self.url.netloc = url_parse.quote(sockpath.encode('utf_8'), safe=b'').encode('ascii')
        self.close_d = t_defer.Deferred()

        def _close_handler(event):
            _LOGGER.debug('_close_handler() called with %r', event)

            return reactor.callLater(0, self.close_d.callback, None)

        self.close_handler = _close_handler

    def tearDown(self):
        super().tearDown()

    #---- Public methods -------------------------------------------------

    def registermock(self, dispatcher):
        handler = mock.Mock(return_value=None)

        for event in itervalues(EIO_TYPE_NAMES_BY_CODE):
            self.assertTrue(dispatcher.register(event, handler))

        return handler

#=========================================================================
class PollingTransportIntegrationTestCase(BaseIntegrationTestCase):

    #---- Public hooks ---------------------------------------------------

    def setUp(self):
        super().setUp()
        transport_factory = PollingTransport.Factory()
        self.transport = transport_factory.buildTransport(reactor)
        self.transport.register('close', self.close_handler)
        self.hander = self.registermock(self.transport)

    def tearDown(self):
        super().tearDown()

    @t_defer.inlineCallbacks
    def test_close_packet_after_upgrade_to_self(self):
        self.url.path = b'/client_close/engine.io/'
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

        send_d = self.transport.sendpacket(EIO_TYPE_CLOSE, '')
        yield send_d

        yield txrc.deferredtimeout(reactor, 10, self.close_d)
        self.assertTrue(self.close_d.called)
        self.assertEqual(self.transport.state, TRANSPORT_STATE_DISCONNECTED)
        self.assertIsNone(tc.session_id)

    @t_defer.inlineCallbacks
    def test_close_packet_before_upgrade_to_self(self):
        self.url.path = b'/client_close/engine.io/'
        tc = TransportContext(self.url)
        connect_d = self.transport.connect(tc)
        self.assertIn(self.transport.state, ( TRANSPORT_STATE_CONNECTING, TRANSPORT_STATE_CONNECTED ))

        yield connect_d
        self.assertEqual(self.transport.state, TRANSPORT_STATE_CONNECTED)
        self.assertIsNotNone(tc.session_id)

        send_d = self.transport.sendpacket(EIO_TYPE_CLOSE, '')
        yield send_d

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

        yield txrc.deferredtimeout(reactor, 10, self.close_d)
        self.assertTrue(self.close_d.called)
        self.assertEqual(self.transport.state, TRANSPORT_STATE_DISCONNECTED)
        self.assertIsNone(tc.session_id)

    @t_defer.inlineCallbacks
    def test_disconnect_after_connected(self):
        self.url.path = b'/client_close/engine.io/'
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

        yield txrc.deferredtimeout(reactor, 10, self.close_d)
        self.assertTrue(self.close_d.called)

    @t_defer.inlineCallbacks
    def test_disconnect_after_upgrade_to_self(self):
        self.url.path = b'/client_close/engine.io/'
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

        yield txrc.deferredtimeout(reactor, 10, self.close_d)
        self.assertTrue(self.close_d.called)

    @t_defer.inlineCallbacks
    def test_disconnect_before_connected(self):
        self.url.path = b'/client_close/engine.io/'
        tc = TransportContext(self.url)

        connect_d = self.transport.connect(tc)
        self.assertEqual(self.transport.state, TRANSPORT_STATE_CONNECTING)
        self.assertRaises(TransportStateError, self.transport.connect, tc)

        disconnect_d = self.transport.disconnect()
        self.assertIn(self.transport.state, ( TRANSPORT_STATE_DISCONNECTED, TRANSPORT_STATE_DISCONNECTING ))
        self.assertRaises(TransportStateError, self.transport.standby)
        self.assertRaises(TransportStateError, self.transport.disconnect)

        yield disconnect_d

        with self.assertRaises(( t_defer.CancelledError, t_error.ConnectingCancelledError )):
            yield connect_d

        self.assertEqual(self.transport.state, TRANSPORT_STATE_DISCONNECTED)
        self.assertIsNone(tc.session_id)

        yield txrc.deferredtimeout(reactor, 10, self.close_d)
        self.assertTrue(self.close_d.called)

#=========================================================================
class EngineIoIntegrationTestCase(BaseIntegrationTestCase):

    #---- Public hooks ---------------------------------------------------

    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()

    @t_defer.inlineCallbacks
    def test_close_packet_after_started(self):
        self.url.path = b'/client_close/engine.io/'
        engineio, handler = self._mkengineio()

        yield engineio.start()
        self.assertTrue(engineio.running)

        send_d = engineio.sendeiopacket(EIO_TYPE_CLOSE)
        yield send_d

        yield txrc.deferredtimeout(reactor, 10, self.close_d)
        self.assertTrue(self.close_d.called)
        self.assertFalse(engineio.running)
        self.assertIsNone(engineio._transport_context.session_id) # pylint: disable=protected-access

        call_args_list = [ i for i in handler.call_args_list if i[0][0] not in ( 'noop', 'pong' ) ]

        expected = [
            mock.call('open'),
            mock.call('close'),
        ]

        self.assertEqual(call_args_list[0], expected[0])
        self.assertEqual(call_args_list[-1], expected[-1])

    @t_defer.inlineCallbacks
    def test_close_packet_after_started_delay(self):
        self.url.path = b'/client_close/engine.io/'
        engineio, handler = self._mkengineio()

        def _sendclose(event): # pylint: disable=unused-argument
            reactor.callLater(1, engineio.sendeiopacket, EIO_TYPE_CLOSE)

        engineio.register('open', _sendclose)

        yield engineio.start()
        self.assertTrue(engineio.running)

        yield txrc.deferredtimeout(reactor, 10, self.close_d)
        self.assertTrue(self.close_d.called)
        self.assertFalse(engineio.running)
        self.assertIsNone(engineio._transport_context.session_id) # pylint: disable=protected-access

        call_args_list = [ i for i in handler.call_args_list if i[0][0] not in ( 'noop', 'pong' ) ]

        expected = [
            mock.call('open'),
            mock.call('message', b'Hello!'),
            mock.call('close'),
        ]

        self.assertEqual(call_args_list, expected)

    @t_defer.inlineCallbacks
    def test_hello(self):
        self.url.path = b'/hello/engine.io/'
        engineio, handler = self._mkengineio()

        yield engineio.start()
        self.assertTrue(engineio.running)

        yield txrc.deferredtimeout(reactor, 10, self.close_d)
        self.assertTrue(self.close_d.called)
        self.assertFalse(engineio.running)
        self.assertIsNone(engineio._transport_context.session_id) # pylint: disable=protected-access

        call_args_list = [ i for i in handler.call_args_list if i[0][0] not in ( 'noop', 'pong' ) ]

        expected = [
            mock.call('open'),
            mock.call('message', b'Hello!'),
            mock.call('close'),
        ]

        self.assertEqual(call_args_list, expected)

    @t_defer.inlineCallbacks
    def test_hello_delay(self):
        self.url.path = b'/hello_delay/engine.io/'
        engineio, handler = self._mkengineio()

        yield engineio.start()
        self.assertTrue(engineio.running)

        yield txrc.deferredtimeout(reactor, 10, self.close_d)
        self.assertTrue(self.close_d.called)
        self.assertFalse(engineio.running)
        self.assertIsNone(engineio._transport_context.session_id) # pylint: disable=protected-access

        call_args_list = [ i for i in handler.call_args_list if i[0][0] not in ( 'noop', 'pong' ) ]

        expected = [
            mock.call('open'),
            mock.call('message', b'Hello!'),
            mock.call('close'),
        ]

        self.assertEqual(call_args_list, expected)

    @t_defer.inlineCallbacks
    def test_no_deadlock(self):
        self.url.path = b'/client_close/engine.io/'
        engineio, handler = self._mkengineio()

        yield engineio.start()

        ping_ds = []

        for _ in range(10):
            ping_ds.append(engineio.sendeiopacket(EIO_TYPE_PING, 'probe'))

        for ping_d in ping_ds:
            yield txrc.deferredtimeout(reactor, 10, ping_d)

        yield engineio.stop()

        yield txrc.deferredtimeout(reactor, 10, self.close_d)
        self.assertTrue(self.close_d.called)
        self.assertFalse(engineio.running)
        self.assertIsNone(engineio._transport_context.session_id) # pylint: disable=protected-access

        call_args_list = [ i for i in handler.call_args_list if i[0][0] not in ( 'noop', 'pong' ) ]

        expected = [
            mock.call('open'),
        ]

        self.assertEqual(call_args_list[0], expected[0])

    @t_defer.inlineCallbacks
    def test_stop_after_started(self):
        self.url.path = b'/client_close/engine.io/'
        engineio, handler = self._mkengineio()

        yield engineio.start()
        self.assertTrue(engineio.running)

        engineio.stop()
        self.assertRaises(TransportStateError, engineio.stop)

        yield txrc.deferredtimeout(reactor, 10, self.close_d)
        self.assertTrue(self.close_d.called)
        self.assertFalse(engineio.running)
        self.assertIsNone(engineio._transport_context.session_id) # pylint: disable=protected-access

        call_args_list = [ i for i in handler.call_args_list if i[0][0] not in ( 'noop', 'pong' ) ]

        expected = [
            mock.call('open'),
        ]

        self.assertEqual(call_args_list[0], expected[0])

    #---- Private static methods -----------------------------------------

    def _mkengineio(self):
        url_bytes = self.url.unsplit()
        engineio = EngineIo(url_bytes)
        handler = self.registermock(engineio)
        engineio.register('close', self.close_handler)

        return engineio, handler

#---- Initialization -----------------------------------------------------

if __name__ == '__main__':
    from unittest import main
    main()
