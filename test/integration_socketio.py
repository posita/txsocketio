#!/usr/bin/env python
# -*- encoding: utf-8; grammar-ext: py; mode: python -*-

# ========================================================================
"""
Copyright and other protections apply. Please see the accompanying
:doc:`LICENSE <LICENSE>` and :doc:`CREDITS <CREDITS>` file(s) for rights
and restrictions governing use of this software. All rights not expressly
waived or licensed are reserved. If those files are missing or appear to
be modified from their originals, then please contact the author before
viewing or using this software in any capacity.
"""
# ========================================================================

from __future__ import (
    absolute_import, division, print_function, unicode_literals,
)
from builtins import *  # noqa: F401,F403; pylint: disable=redefined-builtin,unused-wildcard-import,useless-suppression,wildcard-import
from future.builtins.disabled import *  # noqa: F401,F403; pylint: disable=redefined-builtin,unused-wildcard-import,useless-suppression,wildcard-import
from future.utils import itervalues

# ---- Imports -----------------------------------------------------------

import decimal
import logging
import os
from twisted.internet import (
    defer as t_defer,
    endpoints as t_endpoints,
    reactor,
)
import unittest
import txrc

from txsocketio.socketio import (
    SIO_TYPE_NAMES_BY_CODE,
    SocketIo,
)
import test  # noqa: F401; pylint: disable=unused-import
from test.integration_engineio import BaseIntegrationTestCase
from test.symmetries import mock

# ---- Constants ---------------------------------------------------------

__all__ = ()

_LOGGER = logging.getLogger(__name__)

# ---- Classes -----------------------------------------------------------

# ========================================================================
class SocketIoBaseIntegrationTestCase(BaseIntegrationTestCase):

    # ---- Public hooks --------------------------------------------------

    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()

    # ---- Public methods ------------------------------------------------

    def registermock(self, dispatcher):
        handler = super().registermock(dispatcher)

        for event in itervalues(SIO_TYPE_NAMES_BY_CODE):
            self.assertTrue(dispatcher.register(event, handler))

        return handler

    # ---- Private static methods ----------------------------------------

    def _mksocketio(self, url_bytes=None):
        url_bytes = self.url.unsplit() if url_bytes is None else url_bytes
        socketio = SocketIo(url_bytes)
        handler = self.registermock(socketio)
        socketio.register('close', self.close_handler)

        return socketio, handler

# ========================================================================
class SocketIoIntegrationTestCase(SocketIoBaseIntegrationTestCase):

    # ---- Public hooks --------------------------------------------------

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
        yield txrc.deferredtimeout(reactor, 5, callback_d)
        self.assertTrue(callback_d.called)
        self.assertEqual(callback_d.result, ( '/', ( [], ), {} ))

        yield socketio.stop()
        yield txrc.deferredtimeout(reactor, 10, self.close_d)
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

# ========================================================================
class InsightIntegrationTestCase(SocketIoIntegrationTestCase):

    timeout = 600

    # ---- Public hooks --------------------------------------------------

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
        yield txrc.deferredtimeout(reactor, 10, self.close_d)
        self.assertTrue(self.close_d.called)
        self.assertFalse(socketio.running)

        txs = [ i[0][2][1] for i in handler.call_args_list if i[0][0] == 'event' and i[0][2][0] == 'tx' ]

        if len(txs) == 0:
            try:
                # TODO - fix this
                import debug  # noqa: F401; pylint: disable=reimported,unused-variable,useless-suppression
            except ImportError:
                self.assertGreater(len(txs), 0)

        for tx in txs:
            self.assertIsInstance(tx.get('valueOut'), decimal.Decimal)
            self.assertGreater(tx.get('valueOut', 0), 0)
            self.assertGreater(len(tx.get('vout', ())), 0)
            self.assertRegexpMatches(tx.get('txid', ''), r'^[0-9A-Fa-f]{64}$')

# ---- Initialization ----------------------------------------------------

if __name__ == '__main__':
    from unittest import main
    main()
