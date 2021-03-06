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
from builtins import *  # noqa: F401,F403 # pylint: disable=redefined-builtin,unused-wildcard-import,useless-suppression,wildcard-import
from future.builtins.disabled import *  # noqa: F401,F403 # pylint: disable=no-name-in-module,redefined-builtin,unused-wildcard-import,useless-suppression,wildcard-import

# ---- Imports -----------------------------------------------------------

import functools
import logging
from twisted.python import failure as t_failure
from twisted.internet import defer as t_defer
from twisted.trial import unittest as t_unittest

from txsocketio.dispatcher import Dispatcher
import test  # noqa: F401 # pylint: disable=unused-import
from test.symmetries import mock

# ---- Constants ---------------------------------------------------------

__all__ = ()

_LOGGER = logging.getLogger(__name__)

# ---- Exceptions --------------------------------------------------------

# ========================================================================
class WeirdoError(Exception):
    pass

# ---- Classes -----------------------------------------------------------

# ========================================================================
class DispatcherTestCase(t_unittest.TestCase):

    longMessage = True

    # ---- Public hooks --------------------------------------------------

    @mock.patch('txsocketio.dispatcher._LOGGER')
    def test_dispatch_exception(self, _LOGGER):
        dispatcher = Dispatcher()
        raising_handler = mock.Mock(return_value=None)
        dispatcher.register('bingo', raising_handler)

        def _raise(err, event, *_args, **_kw):
            raise err(event + ' no-go')

        for e in ( TypeError, ValueError, WeirdoError ):
            raise_e = functools.partial(_raise, e)
            raising_handler.side_effect = raise_e
            dispatcher.dispatch('bingo', 'arg', kw='kw')
            raising_handler.assert_called_once_with('bingo', 'arg', kw='kw')
            self.assertEqual(_LOGGER.warning.call_count, 1)
            self.assertIsNotNone(_LOGGER.warning.call_args)
            warning_args, warning_kw = _LOGGER.warning.call_args
            self.assertEqual(len(warning_args), 1)
            self.assertTrue(warning_args[0].startswith('exception raised from event callback '))
            self.assertEqual(len(warning_kw), 1)
            self.assertIs(warning_kw.get('exc_info', False), True)
            raising_handler.reset_mock()
            raising_handler.side_effect = None
            _LOGGER.reset_mock()

    @mock.patch('txsocketio.dispatcher._LOGGER')
    def test_dispatch_failing_deferred(self, _LOGGER):
        dispatcher = Dispatcher()
        results = None

        def _raise_deferred(d, err, event, *_args, **_kw):
            def __raise(_):
                raise err(event + ' no-go')

            d.addCallback(__raise)

            def _recordresult(arg):
                results.append(arg)

                return arg

            d.addBoth(_recordresult)

            return d

        for e in ( TypeError, ValueError, WeirdoError ):
            results = []
            d = t_defer.Deferred()
            raising_handler = functools.partial(_raise_deferred, d, e)
            dispatcher.once('bingo', raising_handler)
            dispatcher.dispatch('bingo', 'arg', kw='kw')
            d.callback(None)
            self.assertTrue(d.called)
            self.assertEqual(len(results), 1)
            self.assertIsInstance(results[-1], t_failure.Failure)
            self.assertIs(results[-1].type, e)
            self.assertEqual(results[-1].value.args[0], 'bingo no-go')
            self.assertEqual(_LOGGER.warning.call_count, 1)
            self.assertIsNotNone(_LOGGER.warning.call_args)
            warning_args, warning_kw = _LOGGER.warning.call_args
            self.assertEqual(len(warning_args), 1)
            self.assertTrue(warning_args[0].startswith('failure raised from deferred event callback '))
            self.assertEqual(len(warning_kw), 0)
            _LOGGER.reset_mock()

    def test_event_restrictions(self):
        dispatcher = Dispatcher(( 1, 2 ))
        handler = mock.Mock(return_value=None)
        self.assertTrue(dispatcher.register(1, handler))
        dispatcher.dispatch(1, 'arg', kw='kw')
        handler.assert_called_once_with(1, 'arg', kw='kw')
        self.assertTrue(dispatcher.unregister(1, handler))

        handler.reset_mock()
        self.assertFalse(dispatcher.register(-1, handler))
        dispatcher.dispatch(-1, 'arg', kw='kw')
        handler.assert_not_called()
        self.assertFalse(dispatcher.unregister(-1, handler))

    def test_registration(self):
        results = None

        def _handler(i, event):
            try:
                _results_by_i = results[i]
            except KeyError:
                _results_by_i = results[i] = []

            _results_by_i.append(event)

        _handler1 = functools.partial(_handler, 1)
        _handler2 = functools.partial(_handler, 2)

        results = {}
        dispatcher = Dispatcher()
        self.assertTrue(dispatcher.register('a', _handler1))
        self.assertFalse(dispatcher.unregister('a', _handler1, once=True))
        self.assertTrue(dispatcher.unregister('a', _handler1))
        dispatcher.dispatch('a')
        self.assertEqual(len(results), 0)

        results = {}
        dispatcher = Dispatcher()
        self.assertTrue(dispatcher.once('a', _handler1))
        self.assertFalse(dispatcher.unregister('a', _handler1))
        self.assertTrue(dispatcher.unregister('a', _handler1, once=True))
        dispatcher.dispatch('a')
        self.assertEqual(len(results), 0)

        results = {}
        dispatcher = Dispatcher()
        self.assertTrue(dispatcher.on('a', _handler1))
        self.assertTrue(dispatcher.on('a', _handler1))
        self.assertTrue(dispatcher.once('a', _handler2))
        dispatcher.dispatch('a')

        expected = {
            1: [ 'a', 'a' ],
            2: [ 'a' ],
        }

        self.assertEqual(results, expected)
        self.assertFalse(dispatcher.unregister('a', _handler2, once=True))
        dispatcher.dispatch('a')
        expected[1].extend([ 'a', 'a' ])
        self.assertEqual(results, expected)
        self.assertTrue(dispatcher.unregister('a', _handler1))
        dispatcher.dispatch('a')
        expected[1].append('a')
        self.assertEqual(results, expected)
        self.assertTrue(dispatcher.unregister('a', _handler1))
        dispatcher.dispatch('a')
        self.assertEqual(results, expected)

# ---- Initialization ----------------------------------------------------

if __name__ == '__main__':
    from unittest import main
    main()
