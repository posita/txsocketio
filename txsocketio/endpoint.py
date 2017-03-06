# -*- encoding: utf-8; grammar-ext: py; mode: python; test-case-name: test.test_endpoint -*-

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
from future.moves.urllib import parse as url_parse
from future.utils import native

# ---- Imports -----------------------------------------------------------

import functools
import posixpath
import re
from twisted.internet import endpoints as t_endpoints
from twisted.python import urlpath as t_urlpath
from twisted.web import (
    client as t_client,
    error as t_error,
    iweb as t_iweb,
)
from zope import interface

try:
    from twisted.internet import ssl as t_ssl
except ImportError:
    _SSL_SUPPORTED = False
else:
    _SSL_SUPPORTED = hasattr(t_ssl, 'optionsForClientTLS')

# ---- Constants ---------------------------------------------------------

__all__ = (
    'BaseUrl',
)

_NETLOC_RE = re.compile(r'''^(:?
        (?P<host0>[-.0-9a-z]+)(?P<port0>)
            | (?P<host1>[-.0-9a-z]+):(?P<port1>[1-9][0-9]*)
            | \[(?P<host2>[:0-9a-f]+)\](?P<port2>)
            | \[(?P<host3>[:0-9a-f]+)\]:(?P<port3>[1-9][0-9]*)
    )$''', re.IGNORECASE | re.VERBOSE)

# ---- Exceptions --------------------------------------------------------

# ========================================================================
class NetLocParseError(Exception):
    ""

# ---- Classes -----------------------------------------------------------

# ========================================================================
class BaseUrl(t_urlpath.URLPath):
    """
    Basically a :class:`twisted.python.urlpath.URLPath` with a
    :meth:`join` method similar to :func:`posixpath.join`.
    """

    # ---- Public static methods -----------------------------------------

    @staticmethod
    def parsenetloc(netloc, defaultport=None):
        """
        Parses a network location (e.g., from a URL) and returns an
        :class:`twisted.internet.interfaces.IAddress` that corresponds
        to that location. If a port number is omitted in the network location,
        ``defaultport`` is used.
        """
        m = _NETLOC_RE.search(netloc.decode('utf_8'))

        if not m:
            raise NetLocParseError('unable to parse netloc {!r}'.format(netloc))

        # From <https://docs.python.org/2/library/itertools.html#recipes>;
        # group 0 is the entire matched string; captured groups start at
        # index 1
        zip_args = [ iter(m.groups()[1:]) ] * 2

        for host, port in zip(*zip_args):
            if host is not None:
                port = int(port) if port else defaultport
                host_quoted = url_parse.quote(host, safe=b':')

                # This works properly in Python 2 because str maps to
                # :class:`future.types.newstr` (it *may* also work in
                # Python 2 with the native `str` type, but that's only
                # because Python 2 perversely allows one to call `encode`
                # on a byte string; but the results would be
                # unpredictable if the URL was already encoded)
                if isinstance(host_quoted, str):
                    host_quoted = host_quoted.encode('utf_8')

                return host_quoted, port

    # ---- Public class methods ------------------------------------------

    @classmethod
    def fromURI(cls, uri):
        """
        Creates a :class:`BaseUrl` from a :class:`twisted.web.client.URI`.
        See also :meth:`~BaseUrl.toURI`.

        :param twisted.web.client.URI uri: the
            :class:`~twisted.web.client.URI` to convert

        :returns: the new :class:`BaseUrl`
        """
        return cls.fromBytes(uri.toBytes())

    # ---- Public hooks --------------------------------------------------

    @classmethod
    def fromBytes(cls, url_bytes):
        try:
            super().fromBytes
        except AttributeError:
            return cls.fromString(url_bytes)

        return cls.fromString(url_bytes.decode('ascii'))

    # ---- Public methods ------------------------------------------------

    def asscheme(self, scheme, keepQuery=False):
        """
        Replaces :attr:`~twisted.python.urlpath.urlpath.scheme`.

        .. code-block:: python
            :linenos:

            >>> url_bytes = bytes(b'http://localhost/cgi-bin/test?key=val#name')
            >>> url1 = BaseUrl.fromBytes(url_bytes)
            >>> url2 = url1.asscheme(bytes(b'https'), True)
            >>> url1.scheme == b'http'
            True
            >>> url2.scheme == b'https'
            True
            >>> url2.query == b'key=val'
            True
            >>> url2.fragment == b'name'
            True
            >>> bytes(url2.unsplit())
            b'https://localhost/cgi-bin/test?key=val#name'
            >>> url3 = url1.asscheme(b'https', False)
            >>> bytes(url3.unsplit())
            b'https://localhost/cgi-bin/test'

        :param bytes scheme: the new scheme

        :param bool keepQuery: if `True`, any query and fragment will be
            preserved in the returned :class:`BaseUrl`

        :returns: a new :class:`BaseUrl` with the new scheme
        """
        try:
            # This is to get around the faulty URLPath constructor that
            # tries to call :meth:`future.types.newbytes.encode`
            scheme = native(scheme)
        except AttributeError:
            pass

        if keepQuery:
            query = self.query
            fragment = self.fragment
        else:
            query = b''
            fragment = b''

        return self.replace(scheme=scheme, query=query, fragment=fragment)

    def join(self, *p):
        """
        Calls :func:`posixpath.join` on
        :attr:`~twisted.python.urlpath.urlpath.path` followed by each item
        in `p`. This method strips any ``query``. Use
        :meth:`~BaseUrl.joinquery` if it should be preserved.

        :param iterable p: an iterable of the parts of the path to join

        :returns: a new :class:`BaseUrl` with the joined path
        """
        parts = [ self.path ]
        parts.extend(p)

        return self._pathMod(parts, False)

    def joinquery(self, *p):
        """
        Calls :func:`posixpath.join` on
        :attr:`~twisted.python.urlpath.urlpath.path` followed by each item
        in `p`. This is just like :meth:`~BaseUrl.join`, except that any
        ``query`` is preserved.

        :param iterable p: an iterable of the parts of the path to join

        :returns: a new :class:`BaseUrl` with the joined path
        """
        parts = [ self.path ]
        parts.extend(p)

        return self._pathMod(parts, True)

    def replace(self, **kw):
        """
        Create a new :class:`BaseUrl`, but using each value in the ``kw``
        argument as an attribute replacement.

        .. code-block:: python
            :linenos:

            >>> url_bytes = bytes(b'http://localhost/cgi-bin/test?key=val#name')
            >>> url1 = BaseUrl.fromBytes(url_bytes)
            >>> url2 = url1.replace(query=b'getto=dachoppa', fragment=b'iamthelaw')
            >>> url1 is url2
            False
            >>> bytes(url2.unsplit())
            b'http://localhost/cgi-bin/test?getto=dachoppa#iamthelaw'

        :param dict kw: the attributes to replace

        :returns: the new :class:`BaseUrl`
        """
        constructor = functools.partial(self.__class__, scheme=self.scheme, netloc=self.netloc, path=self.path, query=self.query, fragment=self.fragment)

        return constructor(**kw)

    def toURI(self):
        """
        Creates a :class:`twisted.web.client.URI` from a :class:`BaseUrl`
        instance. See also :meth:`~BaseUrl.fromURI`.

        :returns: the new :class:`~twisted.web.client.URI`
        """
        return t_client.URI.fromBytes(self.unsplit())

    def unsplit(self):
        """
        Recreates the URL from its basic parts.

        .. code-block:: python
            :linenos:

            >>> url_bytes = bytes(b'http://localhost/cgi-bin/test?key=val#name')
            >>> url = BaseUrl.fromBytes(url_bytes)
            >>> url.scheme = b'https'
            >>> url.query = b'utf8=%E2%9C%93'
            >>> bytes(url.unsplit())
            b'https://localhost/cgi-bin/test?utf8=%E2%9C%93#name'

        :returns: the reformed URL
        """
        val = self.replace().__str__()

        try:
            val = val.encode('ascii')
        except AttributeError:
            pass

        return val

    # ---- Private hooks -------------------------------------------------

    def _pathMod(self, newpathsegs, keepQuery):
        if keepQuery:
            query = self.query
            fragment = self.fragment
        else:
            query = b''
            fragment = b''

        return BaseUrl(self.scheme, self.netloc, posixpath.join(*newpathsegs), query, fragment)

# ========================================================================
@interface.implementer(t_iweb.IAgentEndpointFactory)
class ClientEndpointFactory(object):
    """
    A :class:`twisted.web.iweb.IAgentEndpointFactory` that understands
    ``http(s)://`` and ``ws(s)://`` URLs as well as a ``unix://`` scheme
    for representing an HTTP endpoint served via a named socket.

    ``unix://`` URLs are of the format:

        ``unix://<socketpath>/<...>``

    ``<socketpath>`` is a URL-encoded path. For example, a ``unix://`` URL
    identifying a named socket by the relative path
    ``./tests/node/http.sock`` would be
    ``unix://.%2Ftests%2Fnode%2Fhttp.sock/<...>``. ``<...>`` is just as it
    would be with a ``http(s)://`` or ``ws(s)://`` URL.
    """

    # ---- Constructor ---------------------------------------------------

    def __init__(self, reactor):
        self.reactor = reactor

    # ---- Public hooks --------------------------------------------------

    def endpointForURI(self, uri):
        if uri.scheme in ( b'http', b'https', b'ws', b'wss' ):
            defaultport = 443 if uri.scheme in ( b'https', b'wss' ) else 80
            host, port = BaseUrl.parsenetloc(uri.netloc, defaultport)
            endpoint = t_endpoints.HostnameEndpoint(self.reactor, host, port)

            if defaultport == 443:
                if not _SSL_SUPPORTED:
                    raise t_error.SchemeNotSupported('{} not supported (OpenSSL is not available)'.format(uri.scheme.decode('utf_8')))

                options = t_ssl.optionsForClientTLS(host.decode('utf_8'))
                endpoint = t_endpoints.wrapClientTLS(options, endpoint)

            return endpoint

        if uri.scheme == b'unix':
            path = url_parse.unquote(uri.netloc.decode('ascii'))
            uri.netloc = b'localhost'

            return t_endpoints.UNIXClientEndpoint(self.reactor, path)

        raise t_error.SchemeNotSupported('{} not supported (unrecognized)'.format(uri.scheme.decode('utf_8')))
