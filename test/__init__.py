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

# ---- Imports -----------------------------------------------------------

import logging
import os
import sys
from twisted.internet import (
    base as t_base,
    defer as t_defer,
)
from twisted.trial import unittest as t_unittest

import txrc.logging

# ---- Constants ---------------------------------------------------------

__all__ = ()

_LOG_LVL = os.environ.get('LOG_LVL')
_LOG_LVL = txrc.logging.SILENT if not _LOG_LVL or _LOG_LVL == 'SILENT' else logging.getLevelName(_LOG_LVL)
_LOG_FMT = os.environ.get('LOG_FMT')

# ---- Initialization ----------------------------------------------------

# Python 3.2+ complains that the assert*Regexp* methods are deprecated in
# favor of the analogous assert*Regex methods, which Python 2.7's
# twisted.trial.unittest doesn't have; this monkey patch fixes all that
# nonsense
if not hasattr(t_unittest.TestCase, 'assertRaisesRegex'):
    t_unittest.TestCase.assertRaisesRegex = t_unittest.TestCase.assertRaisesRegexp

if not hasattr(t_unittest.TestCase, 'assertRegex'):
    t_unittest.TestCase.assertRegex = t_unittest.TestCase.assertRegexpMatches

if not hasattr(t_unittest.TestCase, 'assertNotRegex'):
    t_unittest.TestCase.assertNotRegex = t_unittest.TestCase.assertNotRegexpMatches

# TODO: add or condition once <https://tm.tl/#8110> is fixed
if sys.version_info[0] <= 2:  # \
    #     or ( twisted.version.major, twisted.version.minor ) >= ( 17, 2 ):
    t_base.DelayedCall.debug = True

t_defer.setDebugging(True)
logging.basicConfig(format=_LOG_FMT)
logging.getLogger().setLevel(_LOG_LVL)
