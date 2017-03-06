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

# ---- Imports -----------------------------------------------------------

import logging
import unittest
from twisted.internet import endpoints as t_endpoints
from twisted.trial import unittest as t_unittest
from twisted.web import (
    client as t_client,
    error as t_error,
)

from txsocketio.endpoint import (
    BaseUrl,
    ClientEndpointFactory,
    NetLocParseError,
    _SSL_SUPPORTED,
)
import test  # noqa: F401; pylint: disable=unused-import

# ---- Constants ---------------------------------------------------------

__all__ = ()

_LOGGER = logging.getLogger(__name__)

# ---- Classes -----------------------------------------------------------

# ========================================================================
class BaseUrlTestCase(t_unittest.TestCase):

    longMessage = True

    # ---- Public hooks --------------------------------------------------

    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()

    def test_child(self):
        base = BaseUrl.fromBytes(b'http://localhost/~xyz?foo=bar')
        sub = base.child(b'')
        self.assertIs(type(sub), BaseUrl)
        self.assertEqual(sub.path, b'/%7Exyz/')

        sub = base.child(b'abc')
        self.assertEqual(sub.path, b'/%7Exyz/abc')

    def test_join(self):
        base = BaseUrl.fromBytes(b'http://localhost/~xyz?foo=bar')
        self.assertEqual(base.path, b'/%7Exyz')
        self.assertEqual(base.query, b'foo=bar')

        p = ( b'', )
        sub = base.join(*p)
        self.assertIs(type(sub), BaseUrl)
        self.assertEqual(sub.path, b'/%7Exyz/')
        self.assertEqual(sub.query, b'')

        subquery = base.joinquery(*p)
        self.assertIs(type(subquery), BaseUrl)
        self.assertEqual(subquery.path, sub.path)
        self.assertEqual(subquery.query, base.query)

        p = ( b'', b'', b'' )
        sub = base.join(*p)
        self.assertEqual(sub.path, b'/%7Exyz/')

        subquery = base.joinquery(*p)
        self.assertEqual(subquery.path, sub.path)
        self.assertEqual(subquery.query, base.query)

        p = ( b'abc', )
        sub = base.join(*p)
        self.assertEqual(sub.path, b'/%7Exyz/abc')

        subquery = base.joinquery(*p)
        self.assertEqual(subquery.path, sub.path)
        self.assertEqual(subquery.query, base.query)

        p = ( b'abc', b'' )
        sub = base.join(*p)
        self.assertEqual(sub.path, b'/%7Exyz/abc/')

        subquery = base.joinquery(*p)
        self.assertEqual(subquery.path, sub.path)
        self.assertEqual(subquery.query, base.query)

        p = ( b'abc', b'', b'', b'' )
        sub = base.join(*p)
        self.assertEqual(sub.path, b'/%7Exyz/abc/')

        subquery = base.joinquery(*p)
        self.assertEqual(subquery.path, sub.path)
        self.assertEqual(subquery.query, base.query)

        p = ( b'abc', b'', b'', b'', b'def' )
        sub = base.join(*p)
        self.assertEqual(sub.path, b'/%7Exyz/abc/def')

        subquery = base.joinquery(*p)
        self.assertEqual(subquery.path, sub.path)
        self.assertEqual(subquery.query, base.query)

        p = ( b'/abc', )
        sub = base.join(*p)
        self.assertEqual(sub.path, b'/abc')

        subquery = base.joinquery(*p)
        self.assertEqual(subquery.path, sub.path)
        self.assertEqual(subquery.query, base.query)

    def test_parse_netloc(self):
        parsenetloc = BaseUrl.parsenetloc

        host = 'hostname'
        port = None
        netloc = '{}'.format(host).encode()
        self.assertEqual(( host.encode(), port ), parsenetloc(netloc))

        defaultport = 1
        self.assertEqual(( host.encode(), defaultport ), parsenetloc(netloc, defaultport))

        netloc = '[{}]'.format(host).encode()
        self.assertRaises(NetLocParseError, parsenetloc, netloc)

        host = 'hostname'
        port = 42
        netloc = '{}:{}'.format(host, port).encode()
        self.assertEqual(( host.encode(), port ), parsenetloc(netloc))

        defaultport = 2
        self.assertEqual(( host.encode(), port ), parsenetloc(netloc, defaultport))

        netloc = '[{}]:{}'.format(host, port).encode()
        self.assertRaises(NetLocParseError, parsenetloc, netloc)

        netloc = '{}:{}:{}'.format(host, port, port).encode()
        self.assertRaises(NetLocParseError, parsenetloc, netloc)

        host = '::0123:4567:89ab:cdef'
        port = None
        netloc = '[{}]'.format(host).encode()
        self.assertEqual(( host.encode(), port ), parsenetloc(netloc))

        defaultport = 3
        self.assertEqual(( host.encode(), defaultport ), parsenetloc(netloc, defaultport))

        host = '::0123:4567:89ab:cdef'
        port = 42
        netloc = '[{}]:{}'.format(host, port).encode()
        self.assertEqual(( host.encode(), port ), parsenetloc(netloc))

        defaultport = 4
        self.assertEqual(( host.encode(), port ), parsenetloc(netloc, defaultport))

        netloc = '{}:{}'.format(host, port).encode()
        self.assertRaises(NetLocParseError, parsenetloc, netloc)

        netloc = b'@#$%!'
        self.assertRaises(NetLocParseError, parsenetloc, netloc)

    def test_scheme(self):
        base = BaseUrl.fromBytes(b'http://localhost/~xyz')
        self.assertEqual(base.scheme, b'http')

        sub = base.asscheme(b'https')
        self.assertIs(type(sub), BaseUrl)
        self.assertEqual(sub.scheme, b'https')
        self.assertEqual(sub.__str__(), 'https://localhost/%7Exyz')

    def test_uri(self):
        url_bytes = b'http://localhost/cgi-bin/test?key=val#name'
        uri = t_client.URI.fromBytes(url_bytes)
        base_url = BaseUrl.fromURI(uri)
        self.assertEqual(base_url.unsplit(), url_bytes)
        self.assertEqual(base_url.toURI().toBytes(), uri.toBytes())

# ========================================================================
class ClientEndpointFactoryTestCase(t_unittest.TestCase):

    longMessage = True

    # ---- Public hooks --------------------------------------------------

    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()

    def test_endpoint_bad_scheme(self):
        from twisted.internet import reactor
        factory = ClientEndpointFactory(reactor)

        url_bytes = b'homingpigeon://tweets.socket.io/engine.io/?EIO=3&transport=polling'
        url = BaseUrl.fromBytes(url_bytes)
        self.assertRaises(t_error.SchemeNotSupported, factory.endpointForURI, url)

    def test_endpoint_for_http(self):
        from twisted.internet import reactor
        factory = ClientEndpointFactory(reactor)

        url_bytes = b'http://tweets.socket.io/engine.io/?EIO=3&transport=polling'
        url = BaseUrl.fromBytes(url_bytes)
        endpoint = factory.endpointForURI(url)
        self.assertIsInstance(endpoint, t_endpoints.HostnameEndpoint)
        self.assertEqual(endpoint._hostText, 'tweets.socket.io')  # pylint: disable=protected-access
        self.assertEqual(endpoint._port, 80)  # pylint: disable=protected-access

        url_bytes = b'http://tweets.socket.io:54321/engine.io/?EIO=3&transport=polling'
        url = BaseUrl.fromBytes(url_bytes)
        endpoint = factory.endpointForURI(url)
        self.assertIsInstance(endpoint, t_endpoints.HostnameEndpoint)
        self.assertEqual(endpoint._hostText, 'tweets.socket.io')  # pylint: disable=protected-access
        self.assertEqual(endpoint._port, 54321)  # pylint: disable=protected-access

    @unittest.skipUnless(_SSL_SUPPORTED, 'OpenSSL not available')
    def test_endpoint_for_https(self):
        from twisted.internet import reactor
        factory = ClientEndpointFactory(reactor)

        url_bytes = b'https://tweets.socket.io/engine.io/?EIO=3&transport=polling'
        url = BaseUrl.fromBytes(url_bytes)
        endpoint = factory.endpointForURI(url)
        self.assertIsInstance(endpoint, t_endpoints._WrapperEndpoint)  # pylint: disable=protected-access
        self.assertIsInstance(endpoint._wrappedEndpoint, t_endpoints.HostnameEndpoint)  # pylint: disable=protected-access
        self.assertEqual(endpoint._wrappedEndpoint._hostText, 'tweets.socket.io')  # pylint: disable=protected-access
        self.assertEqual(endpoint._wrappedEndpoint._port, 443)  # pylint: disable=protected-access

        url_bytes = b'https://tweets.socket.io:54321/engine.io/?EIO=3&transport=polling'
        url = BaseUrl.fromBytes(url_bytes)
        endpoint = factory.endpointForURI(url)
        self.assertIsInstance(endpoint, t_endpoints._WrapperEndpoint)  # pylint: disable=protected-access
        self.assertIsInstance(endpoint._wrappedEndpoint, t_endpoints.HostnameEndpoint)  # pylint: disable=protected-access
        self.assertEqual(endpoint._wrappedEndpoint._hostText, 'tweets.socket.io')  # pylint: disable=protected-access
        self.assertEqual(endpoint._wrappedEndpoint._port, 54321)  # pylint: disable=protected-access

    @unittest.skipIf(_SSL_SUPPORTED, 'OpenSSL is installed')
    def test_endpoint_for_no_https(self):
        from twisted.internet import reactor
        factory = ClientEndpointFactory(reactor)

        url_bytes = b'https://tweets.socket.io/engine.io/?EIO=3&transport=polling'
        url = BaseUrl.fromBytes(url_bytes)
        self.assertRaises(t_error.SchemeNotSupported, factory.endpointForURI, url)

    @unittest.skipIf(_SSL_SUPPORTED, 'OpenSSL is installed')
    def test_endpoint_for_no_wss(self):
        from twisted.internet import reactor
        factory = ClientEndpointFactory(reactor)

        url_bytes = b'wss://tweets.socket.io/engine.io/?EIO=3&transport=polling'
        url = BaseUrl.fromBytes(url_bytes)
        self.assertRaises(t_error.SchemeNotSupported, factory.endpointForURI, url)

    def test_endpoint_for_unix(self):
        from twisted.internet import reactor
        factory = ClientEndpointFactory(reactor)

        url_bytes = b'unix://.%2Ftests%2Fnode%2Fhttp.sock/engine.io/?EIO=3&transport=polling'
        url = BaseUrl.fromBytes(url_bytes)
        endpoint = factory.endpointForURI(url)
        self.assertIsInstance(endpoint, t_endpoints.UNIXClientEndpoint)
        self.assertEqual(endpoint._path.encode('utf_8'), b'./tests/node/http.sock')  # pylint: disable=protected-access

    def test_endpoint_for_ws(self):
        from twisted.internet import reactor
        factory = ClientEndpointFactory(reactor)

        url_bytes = b'ws://tweets.socket.io/engine.io/?EIO=3&transport=polling'
        url = BaseUrl.fromBytes(url_bytes)
        endpoint = factory.endpointForURI(url)
        self.assertIsInstance(endpoint, t_endpoints.HostnameEndpoint)
        self.assertEqual(endpoint._hostText, 'tweets.socket.io')  # pylint: disable=protected-access
        self.assertEqual(endpoint._port, 80)  # pylint: disable=protected-access

        url_bytes = b'ws://tweets.socket.io:12345/engine.io/?EIO=3&transport=polling'
        url = BaseUrl.fromBytes(url_bytes)
        endpoint = factory.endpointForURI(url)
        self.assertIsInstance(endpoint, t_endpoints.HostnameEndpoint)
        self.assertEqual(endpoint._hostText, 'tweets.socket.io')  # pylint: disable=protected-access
        self.assertEqual(endpoint._port, 12345)  # pylint: disable=protected-access

    @unittest.skipUnless(_SSL_SUPPORTED, 'OpenSSL not available')
    def test_endpoint_for_wss(self):
        from twisted.internet import reactor
        factory = ClientEndpointFactory(reactor)

        url_bytes = b'wss://tweets.socket.io/engine.io/?EIO=3&transport=polling'
        url = BaseUrl.fromBytes(url_bytes)
        endpoint = factory.endpointForURI(url)
        print(dir(endpoint))
        self.assertIsInstance(endpoint, t_endpoints._WrapperEndpoint)  # pylint: disable=protected-access
        self.assertIsInstance(endpoint._wrappedEndpoint, t_endpoints.HostnameEndpoint)  # pylint: disable=protected-access
        self.assertEqual(endpoint._wrappedEndpoint._hostText, 'tweets.socket.io')  # pylint: disable=protected-access
        self.assertEqual(endpoint._wrappedEndpoint._port, 443)  # pylint: disable=protected-access

        url_bytes = b'wss://tweets.socket.io:54321/engine.io/?EIO=3&transport=polling'
        url = BaseUrl.fromBytes(url_bytes)
        endpoint = factory.endpointForURI(url)
        self.assertIsInstance(endpoint, t_endpoints._WrapperEndpoint)  # pylint: disable=protected-access
        self.assertIsInstance(endpoint._wrappedEndpoint, t_endpoints.HostnameEndpoint)  # pylint: disable=protected-access
        self.assertEqual(endpoint._wrappedEndpoint._hostText, 'tweets.socket.io')  # pylint: disable=protected-access
        self.assertEqual(endpoint._wrappedEndpoint._port, 54321)  # pylint: disable=protected-access

# ---- Initialization ----------------------------------------------------

if __name__ == '__main__':
    from unittest import main
    main()
