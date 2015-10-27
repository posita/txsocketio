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

import logging
import sys
from twisted.internet import defer as t_defer
from twisted.internet import task as t_task
from twisted.trial import unittest as t_unittest

from txsocketio.retry import (
    RetryingCaller,
    calltimeout,
)

#---- Constants ----------------------------------------------------------

__all__ = ()

_LOGGER = logging.getLogger(__name__)

#---- Classes ------------------------------------------------------------

#=========================================================================
class CallTimeoutTestCase(t_unittest.TestCase):

    longMessage = True

    #---- Public hooks ---------------------------------------------------

    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()

    def test_calltimeout(self):
        clock = t_task.Clock()

        def _nondeferredcall(_val):
            state['fired'] = True

            return _val

        def _deferredcall(_val, _wait_seconds=1):
            _d = t_task.deferLater(clock, _wait_seconds, _nondeferredcall, _val)

            return _d

        delay = 0
        call_val = 'done1'
        state = { 'fired': False }
        d = calltimeout(clock, delay, _nondeferredcall, call_val)
        clock.advance(0)
        self.assertEqual(d.result, call_val)
        self.assertTrue(state['fired'])

        delay = 2
        call_val = 'done2'
        state = { 'fired': False }
        d = calltimeout(clock, delay, _nondeferredcall, call_val)
        clock.advance(0)
        self.assertEqual(d.result, call_val)
        self.assertTrue(state['fired'])

        for _ in range(delay + 1):
            clock.advance(1)
            self.assertEqual(d.result, call_val)
            self.assertTrue(state['fired'])

        delay = 0
        call_val = 'done3'
        state = { 'fired': False }
        d = calltimeout(clock, delay, _deferredcall, call_val)
        clock.advance(0)
        self.assertIsInstance(d.result.value, t_defer.CancelledError)
        self.assertFalse(state['fired'])
        clock.advance(2)
        self.assertIsInstance(d.result.value, t_defer.CancelledError)
        self.assertFalse(state['fired'])
        d.addErrback(lambda _res: None) # silence the unhandled error

        delay = 2
        call_val = 'done4'
        state = { 'fired': False }
        d = calltimeout(clock, delay, _deferredcall, call_val)
        clock.advance(0)
        self.assertFalse(hasattr(d, 'result'))

        for _ in range(delay + 1):
            clock.advance(1)
            self.assertEqual(d.result, call_val)
            self.assertTrue(state['fired'])

        delay = -1
        call_val = 'done5'
        state = { 'fired': False }
        d = calltimeout(clock, delay, _deferredcall, call_val, sys.maxsize >> 1)
        clock.advance(sys.maxsize)
        self.assertEqual(d.result, call_val)
        self.assertTrue(state['fired'])

#=========================================================================
class RetryingCallerTestCase(t_unittest.TestCase):

    longMessage = True

    #---- Public hooks ---------------------------------------------------

    def setUp(self):
        super().setUp()
        self._clock = t_task.Clock()

    def tearDown(self):
        super().tearDown()
        del self._clock

    def test_retry(self):
        retries = 5
        retrying_caller = RetryingCaller(retries, reactor=self._clock)

        def _mkflaky(_fail_this_many_times):
            def __calltoretry():
                _wrappedcalltoretry.times_called += 1

                if _wrappedcalltoretry.failures_left > 0:
                    _wrappedcalltoretry.failures_left -= 1
                    raise ValueError(_wrappedcalltoretry)

                return _wrappedcalltoretry

            _wrappedcalltoretry = retrying_caller(__calltoretry)
            _wrappedcalltoretry.times_called = 0
            _wrappedcalltoretry.failures_left = _fail_this_many_times

            return _wrappedcalltoretry

        def _checkdlresult(res):
            self.assertEqual(len(res), 3)
            self.assertTrue(res[0][0])
            self.assertEqual(res[0][1].times_called, retries)
            self.assertEqual(res[0][1].failures_left, 0)
            self.assertTrue(res[1][0])
            self.assertEqual(res[1][1].times_called, retries + 1)
            self.assertEqual(res[1][1].failures_left, 0)
            self.assertFalse(res[2][0])
            self.assertIsInstance(res[2][1].value, ValueError)
            self.assertEqual(res[2][1].value.args[0].times_called, retries + 1)
            self.assertEqual(res[2][1].value.args[0].failures_left, 0)

        def _handleresult(_call):
            def __attachresult(__passthru):
                _call.result = __passthru

                return __passthru

            return __attachresult

        call1 = _mkflaky(retries - 1) # should succeed in time
        d1 = call1()
        d1.addBoth(_handleresult(call1))

        call2 = _mkflaky(retries) # should succeed in time
        d2 = call2()
        d2.addBoth(_handleresult(call2))

        call3 = _mkflaky(retries + 1) # should not succeed in time
        d3 = call3()
        d3.addBoth(_handleresult(call3))

        dl = t_defer.DeferredList(( d1, d2, d3 ), consumeErrors=True)
        dl.addCallback(_checkdlresult)

        call4 = _mkflaky(retries) # will be canceled before completion
        d4 = call4()
        d4.addBoth(_handleresult(call4))
        d4.addErrback(lambda _res: None) # silence the unhandled error
        self._clock.advance(0)
        d4.cancel()

        delays = list(RetryingCaller.DefaultBehavior._basegenerator(retries)) # pylint: disable=protected-access
        self._clock.pump(delays)
        self.assertIsInstance(call4.result.value, t_defer.CancelledError)
        self.assertEqual(call4.times_called, 1)
        self.assertEqual(call4.failures_left, retries - 1)

    def test_firsterror(self):
        err_msg = 'Weee!'

        def _none(*_, **__): # pylint: disable=unused-argument
            return

        def _raise(*_, **__): # pylint: disable=unused-argument
            raise RuntimeError(err_msg)

        def _call():
            dl = t_defer.DeferredList(( t_defer.maybeDeferred(_none), t_defer.maybeDeferred(_raise) ), fireOnOneErrback=True, consumeErrors=True)

            return dl

        retrying_caller = RetryingCaller(0, reactor=self._clock)
        d = retrying_caller.retry(_call)
        self._clock.advance(0)
        self.assertIsInstance(d.result.value, RuntimeError)
        self.assertEqual(d.result.value.args[0], err_msg)
        d.addErrback(lambda _res: None) # silence the unhandled error

#---- Initialization -----------------------------------------------------

if __name__ == '__main__':
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    from unittest import main
    main()