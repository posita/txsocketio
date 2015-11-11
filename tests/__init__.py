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
import os
import traceback
import unittest
import hypothesis
from hypothesis import strategies
from twisted.internet import base as t_base
from twisted.internet import defer as t_defer

import txsocketio
from txsocketio.logging import SILENT

#---- Constants ----------------------------------------------------------

__all__ = ()

# We keep out NaN because NaN == NaN is False, which frustrates our
# comparisons of deep JSON-ified objects; also, we don't allow numbers or
# nulls in the top level because the Socket.IO packet encoding does not
# contemplate such things (of course we needed another data encoding
# format, didn't we?)
_JSON = strategies.recursive(strategies.decimals().filter(lambda x: not x.is_nan()) | strategies.booleans() | strategies.text() | strategies.none(), lambda children: strategies.lists(children) | strategies.dictionaries(strategies.text(), children), max_leaves=5)
JSON = strategies.one_of(strategies.booleans(), strategies.text(), strategies.lists(_JSON), strategies.dictionaries(strategies.text(), _JSON))

_LOG_LVL = os.environ.get('_TXSOCKETIO_LOG_LVL')
_LOG_LVL = SILENT if not _LOG_LVL else logging.getLevelName(_LOG_LVL)
_LOG_FMT = os.environ.get('_TXSOCKETIO_LOG_FMT')

#---- Classes ------------------------------------------------------------

#=========================================================================
class MonkeyPatchedDebugDelayedCall(t_base.DelayedCall):

    #---- Constructor ----------------------------------------------------

    def __init__(self, *args, **kw):
        self._SUPER.__init__(self, *args, **kw) # pylint: disable=non-parent-init-called,useless-suppression
        self._whence = traceback.extract_stack()

    #---- Public properties ----------------------------------------------

    @property
    def whence(self):
        return ''.join(traceback.format_list(self._whence)).strip()

    #---- Private constances ---------------------------------------------

    # Save the original implementation, because it's an old-style class
    # (i.e., we can't use super(...)), and we're about to replace it
    _SUPER = t_base.DelayedCall

#---- Initialization -----------------------------------------------------

# Python 3.4 complains that assertRaisesRegexp is deprecated in favor of
# assertRaisesRegex, which Python 2.7's unittest doesn't have; this
# monkey patch fixes all that
if not hasattr(unittest.TestCase, 'assertRaisesRegex'):
    unittest.TestCase.assertRaisesRegex = unittest.TestCase.assertRaisesRegexp

t_defer.setDebugging(True)
logging.basicConfig(format=_LOG_FMT)
txsocketio.LOGGER.setLevel(_LOG_LVL)
t_base.DelayedCall = MonkeyPatchedDebugDelayedCall
