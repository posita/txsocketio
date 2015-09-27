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
from builtins import * # pylint: disable=redefined-builtin,unused-wildcard-import,wildcard-import
from future.builtins.disabled import * # pylint: disable=redefined-builtin,unused-wildcard-import,wildcard-import
# pylint: disable=missing-super-argument

#---- Imports ------------------------------------------------------------

from os import environ
from logging import (
    CRITICAL,
    basicConfig as logging_basicConfig,
    getLevelName as logging_getLevelName,
    getLogger,
)
from twisted.trial.unittest import TestCase

#---- Constants ----------------------------------------------------------

__all__ = ()

_LOG_LVL = environ.get('_TXSOCKETIO_LOG_LVL')
_LOG_LVL = CRITICAL + 1 if not _LOG_LVL else logging_getLevelName(_LOG_LVL)
_LOG_FMT = environ.get('_TXSOCKETIO_LOG_FMT')

#---- Initialization -----------------------------------------------------

# Python 3.4 complains that assertRaisesRegexp is deprecated in favor of
# assertRaisesRegex, which Python 2.7's unittest doesn't have; this
# monkey patch fixes all that
if not hasattr(TestCase, 'assertRaisesRegex'):
    TestCase.assertRaisesRegex = TestCase.assertRaisesRegexp

# Suppress logging messages during testing
logging_basicConfig(format=_LOG_FMT)
getLogger('txsocketio').setLevel(_LOG_LVL)
