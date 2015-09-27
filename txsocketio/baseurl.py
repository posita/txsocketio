#-*- encoding: utf-8; grammar-ext: py; mode: python test-case-name: txsocketio.test_baseuri -*-

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

from posixpath import join as posixpath_join
from twisted.python.urlpath import URLPath

#---- Constants ----------------------------------------------------------

__all__ = (
    'BaseUrl',
)

#---- Classes ------------------------------------------------------------

#=========================================================================
class BaseUrl(URLPath):
    """
    Basically a :class:`twisted.python.urlpath.URLPath` with a
    :meth:`join` method similar to :func:`posixpath.join`.
    """

    #---- Public methods -------------------------------------------------

    #=====================================================================
    def join(self, *p):
        """
        Calls :func:`posixpath.join` on
        :attr:`~twisted.python.urlpath.URLPath.path` followed by each item
        in `p`.

        :param iterable p: an iterable of the parts of the path to join

        :returns: a new :class:`BaseUrl` with the joined path
        """
        parts = [ self.path ]
        parts.extend(p)

        return self._pathMod(parts, False)

    #---- Private hook methods -------------------------------------------

    #=====================================================================
    def _pathMod(self, newpathsegs, keepQuery):
        if keepQuery:
            query = self.query
        else:
            query = b''

        return URLPath(self.scheme, self.netloc, posixpath_join(*newpathsegs), query)
