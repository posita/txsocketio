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
from builtins import * # pylint: disable=redefined-builtin,unused-wildcard-import,wildcard-import
from future.builtins.disabled import * # pylint: disable=redefined-builtin,unused-wildcard-import,wildcard-import

#---- Imports ------------------------------------------------------------

from twisted.trial.unittest import TestCase
from txsocketio.baseurl import BaseUrl

#---- Constants ----------------------------------------------------------

__all__ = ()

#---- Classes ------------------------------------------------------------

#=========================================================================
class BaseUrlTestCase(TestCase):

    #---- Public hook methods --------------------------------------------

    #=====================================================================
    def setUp(self):
        super().setUp() # pylint: disable=missing-super-argument

    #=====================================================================
    def tearDown(self):
        super().tearDown() # pylint: disable=missing-super-argument

    #=====================================================================
    def test_join(self):
        base = BaseUrl.fromString(b'http://localhost/~xyz')
        self.assertEqual(base.path, b'/~xyz')

        sub = base.join(b'')
        self.assertEqual(sub.path, b'/~xyz/')

        # See <https://twistedmatrix.com/trac/ticket/7994>
        # sub = base.child(b'')
        # self.assertEqual(sub.path, b'~xyz/')
        #
        # sub = base.child(b'/')
        # self.assertEqual(sub.path, b'/')

        sub = base.join(b'', b'', b'')
        self.assertEqual(sub.path, b'/~xyz/')

        sub = base.join(b'abc')
        self.assertEqual(sub.path, b'/~xyz/abc')

        sub = base.join(b'abc', b'')
        self.assertEqual(sub.path, b'/~xyz/abc/')

        sub = base.join(b'abc', b'', b'', b'')
        self.assertEqual(sub.path, b'/~xyz/abc/')

        sub = base.join(b'abc', b'', b'', b'', b'def')
        self.assertEqual(sub.path, b'/~xyz/abc/def')

        sub = base.join(b'/abc')
        self.assertEqual(sub.path, b'/abc')

        # See <https://twistedmatrix.com/trac/ticket/7994>
        # sub = base.child(b'/abc')
        # self.assertEqual(sub.path, b'/abc')

#---- Initialization -----------------------------------------------------

if __name__ == '__main__':
    from unittest import main
    main()
