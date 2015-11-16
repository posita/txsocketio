#-*- encoding: utf-8; grammar-ext: py; mode: python; test-case-name: txsocketio.test_engineio -*-

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
_chr = chr
from future.builtins.disabled import * # pylint: disable=redefined-builtin,unused-wildcard-import,useless-suppression,wildcard-import
chr = _chr
del _chr
from future.utils import (
    iteritems,
    iterkeys,
)

#---- Imports ------------------------------------------------------------

import collections
import decimal
import functools
import io
import logging
# import pprint
import time
import simplejson
from twisted.internet import (
    defer as t_defer,
    error as t_error,
    task as t_task,
)
from twisted.python import urlpath as t_urlpath
from twisted.web import (
    client as t_client,
    http_headers as t_http_headers,
)
import txrc.logging
from zope import interface # pylint: disable=import-error

from .dispatcher import Dispatcher
from .endpoint import (
    BaseUrl,
    ClientEndpointFactory,
)
from .symmetries import (
    cookiejar,
    parse,
)

#---- Constants ----------------------------------------------------------

__all__ = (
    'EIO_TYPE_CLOSE',
    'EIO_TYPE_CODES_BY_NAME',
    'EIO_TYPE_MESSAGE',
    'EIO_TYPE_NAMES_BY_CODE',
    'EIO_TYPE_NOOP',
    'EIO_TYPE_OPEN',
    'EIO_TYPE_PING',
    'EIO_TYPE_PONG',
    'EIO_TYPE_UPGRADE',
    'EngineIo',
    'EngineIoException',
    'EngineIoServerError',
    'MethodMismatchError',
    'PayloadDecodeError',
    'PayloadEncodeError',
    'ReceivedClosePacket',
    'TransportMismatchError',
    'TransportStateError',
    'UnexpectedServerError',
    'UnknownSessionIdError',
    'UnrecognizedTransportError',
)

EIO_PROTOCOL = 3

TRANSPORT_POLLING = 'polling'
TRANSPORT_WEBSOCKETS = 'websocket'

EIO_TYPE_OPEN    = bytes(b'0')
EIO_TYPE_CLOSE   = bytes(b'1')
EIO_TYPE_PING    = bytes(b'2')
EIO_TYPE_PONG    = bytes(b'3')
EIO_TYPE_MESSAGE = bytes(b'4')
EIO_TYPE_UPGRADE = bytes(b'5')
EIO_TYPE_NOOP    = bytes(b'6')

EIO_TYPE_NAMES_BY_CODE = {
    EIO_TYPE_OPEN:    'open',
    EIO_TYPE_CLOSE:   'close',
    EIO_TYPE_PING:    'ping',
    EIO_TYPE_PONG:    'pong',
    EIO_TYPE_MESSAGE: 'message',
    EIO_TYPE_UPGRADE: 'upgrade',
    EIO_TYPE_NOOP:    'noop',
}

EIO_TYPE_CODES_BY_NAME = dict(( ( v, k ) for k, v in iteritems(EIO_TYPE_NAMES_BY_CODE) ))

TRANSPORT_STATE_CONNECTED = 'connected'
TRANSPORT_STATE_CONNECTING = 'connecting'
TRANSPORT_STATE_DISCONNECTED = 'disconnected'
TRANSPORT_STATE_DISCONNECTING = 'disconnecting'
TRANSPORT_STATE_RECEIVING = 'receiving'

_TRANSPORT_STATES = {
    TRANSPORT_STATE_CONNECTED: ( TRANSPORT_STATE_DISCONNECTING, ),
    TRANSPORT_STATE_CONNECTING: ( TRANSPORT_STATE_CONNECTED, TRANSPORT_STATE_DISCONNECTING, TRANSPORT_STATE_RECEIVING ),
    TRANSPORT_STATE_DISCONNECTED: ( TRANSPORT_STATE_CONNECTING, ),
    TRANSPORT_STATE_DISCONNECTING: ( TRANSPORT_STATE_DISCONNECTED, ),
    TRANSPORT_STATE_RECEIVING: ( TRANSPORT_STATE_DISCONNECTING, ),
}

_PAYLOAD_TYPE_STR = 0
_PAYLOAD_TYPE_BIN = 1
_PAYLOAD_TYPES = (
    _PAYLOAD_TYPE_STR,
    _PAYLOAD_TYPE_BIN,
)

_LOGGER = logging.getLogger(__name__)

#---- Exceptions ---------------------------------------------------------

#=========================================================================
class EngineIoException(Exception):
    ""

    #---- Constructor ----------------------------------------------------

    def __init__(self, *args, **kw):
        super().__init__(*args)

        if set(kw).difference(( 'wrapped_exc', )):
            raise TypeError('unexpected keyword argument(s): {}'.format(', '.join(iterkeys(kw))))

        self.wrapped_exc = kw.get('wrapped_exc')

#=========================================================================
class PayloadDecodeError(EngineIoException):
    ""

#=========================================================================
class PayloadEncodeError(EngineIoException):
    ""

#=========================================================================
class EngineIoServerError(EngineIoException):
    ""

#=========================================================================
class MethodMismatchError(EngineIoServerError):
    ""

#=========================================================================
class ReceivedClosePacket(EngineIoException):
    ""

#=========================================================================
class TransportMismatchError(EngineIoServerError):
    ""

#=========================================================================
class TransportStateError(EngineIoException):
    ""

#=========================================================================
class UnexpectedServerError(EngineIoServerError):
    ""

#=========================================================================
class UnknownSessionIdError(EngineIoServerError):
    ""

#=========================================================================
class UnrecognizedTransportError(EngineIoServerError):
    ""

_ENGINEIO_UNKNOWN_TRANSPORT_ERR = 0
_ENGINEIO_UNKNOWN_SID_ERR = 1
_ENGINEIO_BAD_HANDSHAKE_METHOD_ERR = 2
_ENGINEIO_BAD_REQUEST_ERR = 3

_ENGINEIO_EXC_BY_ERR_CODE = {
    None: UnexpectedServerError,
    _ENGINEIO_UNKNOWN_TRANSPORT_ERR: UnrecognizedTransportError,
    _ENGINEIO_UNKNOWN_SID_ERR: UnknownSessionIdError,
    _ENGINEIO_BAD_HANDSHAKE_METHOD_ERR: MethodMismatchError,
    _ENGINEIO_BAD_REQUEST_ERR: TransportMismatchError,
}

#---- Interfaces ---------------------------------------------------------

#=========================================================================
class ITransport(interface.Interface):
    """
    An interface for a Transport capable of sending and receiving
    Engine.IO packets.
    """
    # pylint: disable=no-method-argument,no-self-argument,useless-suppression

    #---- Attributes -----------------------------------------------------

    state = interface.Attribute('state', """
        States and transitions:

        +-------------------+--------------------------------------------------+
        | Current State     | Next States                                      |
        |                   +------------------------------+-------------------+
        |                   | On Success                   | On Error          |
        +===================+==============================+===================+
        | ``disconnected``  | ``connecting``               |                   |
        +-------------------+------------------------------+-------------------+
        | ``connecting``    | ``connected``, ``receiving`` | ``disconnecting`` |
        +-------------------+------------------------------+-------------------+
        | ``connected``     | ``disconnecting``                                |
        +-------------------+--------------------------------------------------+
        | ``receiving``     | ``disconnecting``                                |
        +-------------------+--------------------------------------------------+
        | ``disconnecting`` | ``disconnected``                                 |
        +-------------------+--------------------------------------------------+

        Note that ``connecting`` can go to either ``connected`` or
        ``receiving``, although not all providers will necessarily
        implement all paths (see :meth:`~ITransport.connect`).
        """)

    #---- Hooks ----------------------------------------------------------

    def connect(transport_context):
        """
        Set the provider's :attr:`~ITransport.state` to ``connecting`` and
        attempts to connect to the server identified by
        :attr:`~ITransport.transport_context`. If an existing session is
        available, it should be used (in which case
        :attr:`~ITransport.state` becomes ``receiving`` on success).
        Otherwise, the provider tries to establish a new session (in
        which case :attr:`~ITransport.state` becomes ``connected`` on
        success). If the provider does not support establishing a new
        session, but one is required, a :exc:`NotImplementedError` is
        raised, and :attr:`~ITransport.state` is set to ``disconnected``.

        :param transport_context: the transport context

        :type transport_context: :class:`TransportContext`

        :returns: a :class:`twisted.internet.defer.Deferred` whose
            callback is fired with a `None` argument once
            :attr:`~ITransport.state` is either ``connected`` or
            ``receiving`` as appropriate, or whose errback is fired if
            :attr:`~ITransport.state` becomes ``disconnected`` due to an
            error

        :raises NotImplementedError: should be raised if the
            :attr:`~ITransport.transport_context` has no session, and the
            provider is incapable of establishing a new one

        :raises TransportStateError: should be raised if
            :attr:`~ITransport.state` is not ``disconnected``
        """

    def disconnect():
        """
        Tears down any existing connection(s) to the server, just as with
        :meth:`~ITransport.standby`.

        In addition, this method sends a ``close`` packet to the server
        (if possible) and calls :meth:`TransportContext.clear` on
        :attr:`~ITransport.transport_context`.

        Otherwise, semantics are identical to :meth:`~ITransport.standby`.
        """

    def sendpacket(packet_type, packet_data):
        """
        Sends an Engine.IO packet using the implementing transport.

        :param bytes packet_type: the Engine.IO packet type (one of
            the values from :const:`EIO_TYPE_CODES_BY_NAME`)

        :param packet_data: the packet data

        :type packet_data: `bytes`, `str` (`unicode`), or `None`

        :returns: a :class:`twisted.internet.defer.Deferred` whose
            callback is fired with a `None` argument after the packet is
            sent
        """

    def standby():
        """
        Tears down any existing connection(s) to the server.

        :returns: a :class:`twisted.internet.defer.Deferred` whose
            callback is fired with a `None` argument once
            :attr:`~ITransport.state` is ``disconnected`` and whose
            errback is fired if ``lose_session`` is falsy and an error is
            encountered (in which case, :attr:`~ITransport.state` is set
            to ``disconnected``, and :meth:`TransportContext.clear` is
            called on :attr:`~ITransport.transport_context`)

        :raises TransportStateError: if :attr:`~ITransport.state` is one
            of ``disconnected`` and ``disconnecting``
        """

#=========================================================================
class ITransportFactory(interface.Interface):
    """
    An interface for a factory capable of building an :class:`ITransport`
    provider.
    """
    # pylint: disable=no-method-argument,no-self-argument,useless-suppression

    #---- Hooks ----------------------------------------------------------

    def buildTransport(reactor):
        """
        Builds the new :class:`ITransport` provider.
        """

#---- Classes ------------------------------------------------------------

#=========================================================================
class TransportContext(object):
    """
    Common state shared created by (and possibly shared among)
    :class:`ITransport` providers.
    """

    #---- Constructor ----------------------------------------------------

    def __init__(self, base_url):
        ""
        super().__init__()
        self._base_url = base_url
        self.clear()

    #---- Public properties ----------------------------------------------

    @property
    def base_url(self):
        """
        The base URL assocated with the context, usually in the form of
        one of:

            * ``http(s)://<server>/engine.io/``
            * ``http(s)://<server>/socket.io/``
        """
        return self._base_url

    @property
    def ping_interval(self):
        """
        The ping interval assocated with the context. Before a connection
        has been established, this is `None`.
        """
        return self._ping_interval

    @property
    def ping_timeout(self):
        """
        The ping timeout assocated with the context. Before a connection
        has been established, this is `None`.
        """
        return self._ping_timeout

    @property
    def session_id(self):
        """
        The Engine.IO session ID assocated with the context. Before a
        connection has been established, this is `None`.
        """
        return self._session_id

    @property
    def upgrades(self):
        """
        The protocol upgrades available under the context. Before a
        connection has been established, this is `None`.
        """
        return self._upgrades

    #---- Public methods -------------------------------------------------

    def clear(self):
        """
        Clears any connection-related attributes associated with the
        context.
        """
        self._ping_interval = None
        self._ping_timeout = None
        self._session_id = None
        self._upgrades = None

    def set(self, session_id, ping_timeout, ping_interval, upgrades):
        """
        Associates connection-related attributes with the context.

        :param str session_id: the Engine.IO session ID

        :param Integral ping_timeout: the ping timeout

        :param Integral ping_interval: the ping interval

        :param list upgrades: the transport upgrades supported by the
            Engine.IO server
        """
        # pylint: disable=attribute-defined-outside-init
        self._ping_interval = ping_interval
        self._ping_timeout = ping_timeout
        self._session_id = session_id
        self._upgrades = upgrades

#=========================================================================
class _BaseTransport(Dispatcher):
    ""

    #---- Constructor ----------------------------------------------------

    def __init__(self):
        """
        :param transport_context: the transport context to associate with
            the transport

        :type transport_context: :class:`TransportContext`
        """
        super().__init__()
        self._state = TRANSPORT_STATE_DISCONNECTED
        self._transport_context = None

    #---- Public properties ----------------------------------------------

    @property
    def state(self):
        """
        The state associated with the transport.
        """
        return self._state

    @state.setter
    def state(self, value):
        if value not in _TRANSPORT_STATES:
            raise ValueError('{!r} is one of: {}'.format(value, ', '.join(( repr(i) for i in sorted(_TRANSPORT_STATES) ))))

        if value not in _TRANSPORT_STATES[self._state]:
            raise TransportStateError('{!r} cannot transition to {!r}, only one of: {}'.format(self._state, value, ', '.join(( repr(i) for i in sorted(_TRANSPORT_STATES[self._state]) ))))

        self._state = value

    @property
    def transport_context(self):
        """
        The :class:`TransportContext` associated with the transport.
        """
        return self._transport_context

    #---- Public hooks ---------------------------------------------------

    def connect(self, transport_context):
        if self.state != TRANSPORT_STATE_DISCONNECTED:
            raise TransportStateError('{} state {!r} is not {!r}'.format(self.__class__.__name__, self.state, TRANSPORT_STATE_DISCONNECTED))

        self._transport_context = transport_context

    def disconnect(self):
        if self.state in ( TRANSPORT_STATE_DISCONNECTED, TRANSPORT_STATE_DISCONNECTING ):
            raise TransportStateError('{} state is {!r}'.format(self.__class__.__name__, self.state))

    def sendpacket(self, packet_type, packet_data): # pylint: disable=unused-argument
        if self.state not in ( TRANSPORT_STATE_CONNECTED, TRANSPORT_STATE_RECEIVING ):
            raise TransportStateError('{} state is not {!r} or {!r}'.format(self.__class__.__name__, TRANSPORT_STATE_CONNECTED, TRANSPORT_STATE_RECEIVING))

    def standby(self):
        if self.state not in ( TRANSPORT_STATE_CONNECTED, TRANSPORT_STATE_RECEIVING ):
            raise TransportStateError('{} state is not {!r} or {!r}'.format(self.__class__.__name__, TRANSPORT_STATE_CONNECTED, TRANSPORT_STATE_RECEIVING))

#=========================================================================
@interface.implementer(ITransport)
class PollingTransport(_BaseTransport):
    """
    Implements :class:`ITransport` for the Engine.IO ``polling`` protocol
    and dispatches received packets as events.
    """

    #---- Public inner classes -------------------------------------------

    @interface.implementer(ITransportFactory)
    class Factory(object):
        """
        A :class:`PollingTransport` factory.
        """

        #---- Constructor ------------------------------------------------

        def __init__(self, agent=None, pool=None, headers=None):
            """
            :param agent: passed to :meth:`PollingTransport.__init__`

            :param headers: passed to :meth:`PollingTransport.__init__`
            """
            super().__init__()

            kw = {
                'agent': agent,
                'pool': pool,
                'headers': headers,
            }

            self.buildTransport = functools.partial(PollingTransport, **kw)

    #---- Constructor ----------------------------------------------------

    def __init__(self, reactor, agent=None, pool=None, headers=None):
        """
        ``reactor`` is typically provided from
        :meth:`ITransportFactory.buildTransport`.

        :param agent: the agent used to establish the connection

        :type agent: :class:`twisted.web.client.Agent`

        :param pool: the connection pool to be used;
            :attr:`~twisted.web.client.HTTPConnectionPool.maxPersistentPerHost`
            is recommended to be 3 or more, but should be at least 2 (one
            for retrieving packets and one for sending them; packets to be
            sent, *including periodic ``ping`` packets*, will be queued
            until a persistent connection is available)

        :type pool: :class:`twisted.web.client.HTTPConnectionPool`

        :param headers: additional headers used for each request

        :type headers: :class:`twisted.web.http_headers.Headers`
        """
        super().__init__()

        self._query = {
            b'EIO': EIO_PROTOCOL,
            b'transport': TRANSPORT_POLLING.encode('ascii'),
        }

        self._request_count = 0

        self._headers = {
            b'Accept':         [ b'application/octet-stream', b'application/json' ],
            b'Accept-Charset': [ b'UTF-8' ],
        }

        if headers is not None:
            self._headers.update(headers)

        self._reactor = reactor
        self._pool = pool if pool is not None else self._builddefaultpool()
        # We need at least two persistent connections (one for polling for
        # packets and one for sending them)
        self._pool.maxPersistentPerHost = max(self._pool.maxPersistentPerHost, 2)
        # Leave one connection for polling
        self._send_queue = PollingTransport._SendQueue(backlog=self._pool.maxPersistentPerHost - 1)
        self._sending_ds = collections.deque()
        self._agent = agent if agent is not None else self._builddefaultagent()
        self._connecting_d = None
        self._disconnecting_d = None
        self._receiving_d = None
        # Because we're still disconnected at this point, this initializes
        # self._receiving_d without starting the loop
        self._receiveloop()

    #---- Public properties ----------------------------------------------

    default_timeout = 3

    #---- Public hooks ---------------------------------------------------

    def connect(self, transport_context):
        super().connect(transport_context)
        self.state = TRANSPORT_STATE_CONNECTING

        def _startsendworkerloops():
            for _ in range(self._send_queue.backlog):
                self._sendworkerloop()

        if self.transport_context.session_id is not None:
            # Assume that we're "upgrading" our own transport and that a
            # session has already been established; also assume that the
            # session is still good
            self.state = TRANSPORT_STATE_RECEIVING
            d = t_defer.succeed(None)
            _startsendworkerloops()
            self._receiveloop()

            return d

        d = self._connecting_d = self._packetsrequest()

        def _done(_passthru):
            self._connecting_d = None

            return _passthru

        d.addBoth(_done)

        def _connected(_passthru):
            self.state = TRANSPORT_STATE_CONNECTED
            _startsendworkerloops()

            return _passthru

        d.addCallback(_connected)
        d.addErrback(self._shutitdown, lose_connection=True)
        d.addErrback(txrc.logging.logerrback, logger=_LOGGER, msg='Failure while connecting:')

        return d

    def disconnect(self):
        super().disconnect()
        d = self._stopconnecting(None)
        d.addBoth(self._shutitdown, lose_connection=True)

        return d

    def sendpacket(self, packet_type, packet_data=''):
        super().sendpacket(packet_type, packet_data)

        return self._send_queue.putpacket(packet_type, packet_data)

    def standby(self):
        super().standby()
        d = self._stopconnecting(None)
        d.addBoth(self._shutitdown, lose_connection=False)

        return d

    #---- Private inner classes ------------------------------------------

    class _SendQueue(t_defer.DeferredQueue):

        #---- Public methods ---------------------------------------------

        def putpacket(self, packet_type, packet_data):
            callback_d = t_defer.Deferred()
            self.put(( callback_d, packet_type, packet_data ))

            return callback_d

    #---- Private methods ------------------------------------------------

    def _builddefaultagent(self):
        endpoint_factory = ClientEndpointFactory(self._reactor)
        agent = t_client.Agent.usingEndpointFactory(self._reactor, endpoint_factory, pool=self._pool)
        jar = cookiejar.CookieJar()
        agent = t_client.CookieAgent(agent, jar)
        agent = t_client.ContentDecoderAgent(agent, [ ( b'gzip', t_client.GzipDecoder ) ])

        return agent

    def _builddefaultpool(self):
        pool = t_client.HTTPConnectionPool(self._reactor) #, persistent=False)
        pool.retryAutomatically = True

        return pool

    def _checkresponse(self, response_with_body):
        content_type = response_with_body.headers.getRawHeaders(b'Content-Type')
        charset = 'latin_1'

        if content_type is not None:
            content_type = content_type[0].split(';')
            content_type, content_type_params = content_type[0], content_type[1:]
            content_type = content_type.lower()
            content_type_params = list(( v.split('=', 1) for v in content_type_params ))
            content_type_params = dict(( ( k.lower(), v ) for k, v in content_type_params ))
            charset = content_type_params.setdefault('charset', charset)
        else:
            content_type = 'application/json'

        response_with_body.body_charset = charset

        if response_with_body.code >= 200 \
                and response_with_body.code < 300:

            return response_with_body

        message = 'response body: {!r}'.format(response_with_body.body)
        exc = _ENGINEIO_EXC_BY_ERR_CODE.get(None)(message)

        if response_with_body.code == 400:
            body_json = {}

            if content_type == 'application/json':
                try:
                    body = response_with_body.body.decode(response_with_body.body_charset)
                    body_json = jsonloads(body)
                except ( UnicodeDecodeError, ValueError ):
                    pass

            code = body_json.get('code', None)
            message = body_json.get('message', message)
            exc = _ENGINEIO_EXC_BY_ERR_CODE.get(code, _ENGINEIO_EXC_BY_ERR_CODE.get(None))(message)

        if isinstance(exc, UnknownSessionIdError):
            self.transport_context.clear()

        raise exc

    def _nextrequesturl(self):
        request_count = self._request_count
        self._request_count += 1
        query = dict(self._query)

        if self.transport_context.session_id is not None:
            query[b't'] = '{}-{}'.format(int(time.time() * 1000), request_count).encode('utf_8')

        url_bytes = self.transport_context.base_url.replace(query=parse.urlencode(query)).unsplit()

        return request_count, url_bytes

    def _packetsrequest(self):
        if self.state in ( TRANSPORT_STATE_DISCONNECTED, TRANSPORT_STATE_DISCONNECTING ):
            raise TransportStateError('packets requested when {} state is {!r}'.format(self.__class__.__name__, self.state))

        d = self._sessionrequest()
        d.addCallback(self._parsepackets)

        return d

    def _parsepackets(self, response_with_body):
        try:
            packets = [ deceiopacket(pckt) for pckt in decbinpayloadsgen(response_with_body.body) ]
        except PayloadDecodeError as exc:
            new_exc = type(exc)('unparseable response from request[{}]: {!r}'.format(response_with_body.request_count, response_with_body.body), wrapped_exc=exc)

            raise new_exc

        closing = False

        for i, packet in enumerate(packets):
            packet_type, packet_data = packet
            packet_name = EIO_TYPE_NAMES_BY_CODE[packet_type]
            _LOGGER.debug('received packet[%d] ("%s") from request[%d]', i, packet_name, response_with_body.request_count)

            if packet_type == EIO_TYPE_OPEN \
                    and (i > 0
                        or response_with_body.request_count != 0):
                raise TransportStateError('received out-of-band "{}" packet'.format(packet_name))

            if closing:
                raise TransportStateError('received out-of-band "{}" packet after close'.format(packet_name))

            if packet_type == EIO_TYPE_OPEN:
                data = jsonloads(packet_data)
                ping_interval = data['pingInterval']
                ping_timeout = data['pingTimeout']
                session_id = data['sid']
                upgrades = data.get('upgrades', ())
                self.transport_context.set(session_id, ping_timeout, ping_interval, upgrades)
                self._query['sid'] = session_id
                _LOGGER.debug('session "%s" opened', session_id)

            dispatch_args = [ packet_name ]

            if packet_type in ( EIO_TYPE_MESSAGE, EIO_TYPE_PING, EIO_TYPE_PONG ):
                dispatch_args.append(packet_data)

            if packet_type == EIO_TYPE_CLOSE:
                closing = True
                _LOGGER.debug('session "%s" closed by server', self.transport_context.session_id)
            else:
                self.dispatch(*dispatch_args)

        if closing:
            self.transport_context.clear()

            raise ReceivedClosePacket

    def _receiveloop(self, _=None):
        if self.state != TRANSPORT_STATE_RECEIVING:
            # Suppress any :exc:`twisted.internet.defer.CancelledError` in
            # case we try to cancel it outside the loop
            self._receiving_d = t_defer.succeed(None)
            _LOGGER.debug('receive loop halting')

            return

        self._receiving_d = self._packetsrequest()
        self._receiving_d.addCallback(self._receiveloop)
        self._receiving_d.addErrback(self._stopconnecting)
        self._receiving_d.addErrback(self._shutitdown, lose_connection=True, stop_packets_loop=False)
        handled = ( t_defer.CancelledError, t_client.ResponseFailed, ReceivedClosePacket, UnknownSessionIdError )
        self._receiving_d.addErrback(txrc.logging.logerrback, logger=_LOGGER, log_lvl=logging.WARNING, msg='Failure raised when retrieving packets:', handled=handled)

    def _sendpacket(self, packet_type, packet_data=''):
        packet = enceiopacket(packet_type, packet_data)
        payload = encbinpayload(packet)
        d = self._sessionrequest(payload)

        def _checkbody(_request_with_body):
            if _request_with_body.body != 'ok':
                raise UnexpectedServerError('unrecognized response from request[{}]: {!r}'.format(_request_with_body.request_count, _request_with_body.body))

        d.addCallback(_checkbody)

        return d

    def _sendworkerloop(self, _=None):
        if self.state not in ( TRANSPORT_STATE_CONNECTED, TRANSPORT_STATE_RECEIVING ):
            _LOGGER.debug('send worker loop halting')

            return

        d = self._send_queue.get()
        self._sending_ds.append(d)

        def _sendpacket(_queue_item):
            _callback_d, _packet_type, _packet_data = _queue_item
            _d = self._sendpacket(_packet_type, _packet_data)

            def __done(__passthru):
                self._sending_ds.remove(d)

                return __passthru

            _d.addBoth(__done)
            _d.addErrback(self._stopconnecting)
            _d.addErrback(self._shutitdown, lose_connection=True)
            _d.chainDeferred(_callback_d)
            # handled = ( t_defer.CancelledError, t_client.ResponseFailed, UnknownSessionIdError )
            # _d.addErrback(txrc.logging.logerrback, logger=_LOGGER, log_lvl=logging.WARNING, msg='Failure raised when sending packet <{}:{!r}>:'.format(EIO_TYPE_NAMES_BY_CODE.get(_packet_type, '[WTF?! UNKNOWN PACKET TYPE?!]'), _packet_data), handled=handled)

            return _d

        d.addCallback(_sendpacket)
        d.addCallback(self._sendworkerloop)

    def _sessionrequest(self, payload=None, method=None, timeout=None):
        request_count, url_bytes = self._nextrequesturl()
        headers = t_http_headers.Headers(self._headers)

        if payload is None:
            method = method if method is not None else b'GET'
            body_producer = None
            _LOGGER.debug('%s-ing[%d] from <%s>', method, request_count, url_bytes.decode('utf_8'))
        else:
            method = method if method is not None else b'POST'
            headers.addRawHeader(b'Content-Type', b'application/octet-stream')
            body_producer = t_client.FileBodyProducer(io.BytesIO(payload))
            _LOGGER.debug('%s-ing[%d] %r to <%s>', method, request_count, payload, url_bytes.decode('utf_8'))

        d = self._agent.request(method, url_bytes, headers, body_producer)

        if timeout is None:
            if self._transport_context is not None \
                    and self._transport_context.ping_timeout is not None:
                timeout = self._transport_context.ping_timeout / 1000
            else:
                timeout = self.default_timeout

        d = txrc.deferredtimeout(self._reactor, timeout, d)

        def _responsereceived(_response, _request_count):
            _response.request_count = _request_count
            _LOGGER.debug('response code from request[%d]: %d %s', _request_count, _response.code, _response.phrase.decode('utf_8'))
            # _LOGGER.debug('response headers from request[%d]:', _request_count)
            # _LOGGER.debug(pprint.pformat(list(_response.headers.getAllRawHeaders())))

            _d = t_client.readBody(_response)

            def __bodyreceived(__body):
                _response.body = __body

                return _response

            _d.addCallback(__bodyreceived)

            return _d

        d.addCallback(_responsereceived, request_count)
        d.addCallback(self._checkresponse)

        return d

    def _shutitdown(self, passthru, lose_connection, stop_packets_loop=True):
        try:
            self.state = TRANSPORT_STATE_DISCONNECTING
        except TransportStateError:
            # Someone else is working on this, so we're done

            return passthru

        def _trysendclose(_passthru):
            if self.transport_context.session_id is None:
                return t_defer.execute(lambda: _passthru)

            # This may grab a non-cached connection outside of our pool if
            # all cached connections are in use; in rare cases, this could
            # trigger <https://github.com/socketio/engine.io/issues/363>,
            # which is one reason to treat the
            # :exc:`~twisted.internet.defer.CancelledError` as handled
            _d = self._sendpacket(EIO_TYPE_CLOSE)
            handled = ( t_defer.CancelledError, UnknownSessionIdError, )
            _d.addErrback(txrc.logging.logerrback, logger=_LOGGER, log_lvl=logging.WARNING, msg='Failure raised when sending close packet:', handled=handled)
            _d.addBoth(lambda _: _passthru)

            return _d

        if lose_connection:
            d = _trysendclose(passthru)
        else:
            d = t_defer.execute(lambda: passthru)

        def _stopsendworkerloops(_passthru):
            _dl = t_defer.DeferredList(self._sending_ds, consumeErrors=True)
            _dl.cancel()
            _dl.addBoth(lambda _: _passthru)

            return _dl

        d.addBoth(_stopsendworkerloops)

        def _stopreceiveloop(_passthru):
            self._receiving_d.cancel()
            self._receiving_d.addBoth(lambda _: _passthru)

            return self._receiving_d

        if stop_packets_loop:
            d.addBoth(_stopreceiveloop)

        def _stoppool(_passthru):
            _d = self._pool.closeCachedConnections()
            _d.addErrback(txrc.logging.logerrback, logger=_LOGGER, msg='Failure in shutting down pool:')
            _d.addBoth(lambda _: _passthru)

            return _d

        d.addBoth(_stoppool)

        def _finished(_passthru):
            if lose_connection:
                self.transport_context.clear()

            self.state = TRANSPORT_STATE_DISCONNECTED

            if lose_connection:
                self.dispatch(EIO_TYPE_NAMES_BY_CODE[EIO_TYPE_CLOSE])

            return _passthru

        d.addBoth(_finished)

        return d

    def _stopconnecting(self, passthru):
        def _stopconnectingimpl():
            if self._connecting_d is not None:
                _LOGGER.debug('_stopconnectingimpl canceling self._connecting_d')
                self._connecting_d.cancel()

            f = lambda: self._connecting_d

            return t_defer.maybeDeferred(f)

        d = _stopconnectingimpl()
        handled = ( t_defer.CancelledError, t_error.ConnectingCancelledError )
        d.addErrback(txrc.logging.logerrback, logger=_LOGGER, msg='Failure raised when canceling pending connection:', handled=handled, suppress_msg_on_handled=False)
        d.addBoth(lambda _: passthru)

        return d

#=========================================================================
class EngineIo(Dispatcher):
    """
    Abstracts an Engine.IO connection, handling any underlying transport
    upgrades, and dispatching received packets as events with ``event``
    set to one of one of the keys from :const:`EIO_TYPE_CODES_BY_NAME`.

    ``base_url`` is usually in the form of one of:

        * ``http(s)://<server>/engine.io/``
        * ``http(s)://<server>/socket.io/``

    :param base_url: the base URL to which to connect

    :type base_url: `bytes`, `str` (`unicode`),
        :class:`twisted.web.client.URI`, or
        :class:`twisted.python.urlpath.URLPath`

    :param DictType transport_factories: a mapping of transport names to
        :class:`ITransportFactory` providers; if provided, this must
        provide at least one entry for `TRANSPORT_POLLING`

    :param reactor: the reactor used for scheduling, making connections,
        etc.

    :type reactor: provider of
        :class:`twisted.internet.interfaces.IReactorTime`, and one or more
        of: :class:`twisted.internet.interfaces.IReactorSSL`,
        :class:`twisted.internet.interfaces.IReactorSocket`,
        :class:`twisted.internet.interfaces.IReactorTCP`, and
        :class:`twisted.internet.interfaces.IReactorUNIX` (as necessary)
    """

    #---- Constructor ----------------------------------------------------

    def __init__(self, base_url, transport_factories=None, reactor=None):
        super().__init__()

        if isinstance(base_url, t_client.URI):
            base_url = BaseUrl.fromURI(base_url)
        elif isinstance(base_url, t_urlpath.URLPath):
            if not isinstance(base_url, BaseUrl):
                base_url = BaseUrl.fromString(base_url.__str__().encode('utf_8'))
        elif isinstance(base_url, bytes):
            base_url = BaseUrl.fromString(base_url)
        elif isinstance(base_url, str):
            base_url = BaseUrl.fromString(base_url.encode('utf_8'))
        else:
            raise TypeError('base_url type must be one of bytes, str, URI, URLPath, not {}'.format(type(base_url).__name__))

        self._transport_context = TransportContext(base_url)

        if reactor is None:
            from twisted.internet import reactor

        self._reactor = reactor

        self._transport_factories = transport_factories if transport_factories is not None else {
            TRANSPORT_POLLING: PollingTransport.Factory(),
        }

        for k, v in iteritems(self._transport_factories):
            if not ITransportFactory.providedBy(v):
                raise TypeError('transport_factories["{}"] must provide ITransportFactory'.format(k))

        if TRANSPORT_POLLING not in self._transport_factories:
            raise ValueError('transport_factories missing entry for "{}"'.format(TRANSPORT_POLLING))

        self._transport = None
        self._tmp_event_queue = collections.deque()
        self._pingloop_d = t_defer.Deferred()
        # Suppress any :exc:``twisted.internet.defer.CancelledError`` in
        # case we try to cancel it before we start the loop
        self._pingloop_d.callback(None)

    #---- Public properties ----------------------------------------------

    @property
    def running(self):
        return self._transport is not None \
            and self._transport.state == TRANSPORT_STATE_RECEIVING

    #---- Public methods -------------------------------------------------

    def sendeiopacket(self, packet_type, packet_data=''):
        """
        Sends an Engine.IO packet using the underlying :class:`ITransport`
        provider with the same semantics as with
        :meth:`ITransport.sendpacket`.
        """
        if self._transport is None:
            raise TransportStateError('no transport')

        return self._transport.sendpacket(packet_type, packet_data)

    def start(self):
        """
        Starts (and possibly upgrades) the underlying :class:`ITransport`
        provider.

        :returns: a :class:`twisted.internet.defer.Deferred` akin to the
            return value from the :meth:`~ITransport.connect` method of
            the underlying :class:`ITransport` provider
        """
        if self._transport is not None:
            raise TransportStateError('no transport')

        transport_factory = self._transport_factories[TRANSPORT_POLLING]
        self._transport = transport_factory.buildTransport(self._reactor)
        self._registerstarttransport(self._transport)
        d = self._transport.connect(self._transport_context)

        def _startconnected(_):
            _d = self._transport.standby()

            def __upgradetransport(__): # pylint: disable=unused-argument
                self._unregisterstarttransport(self._transport)
                upgrades = [ t for t in self._transport_context.upgrades if t in self._transport_factories ]

                if upgrades:
                    transport_factory = self._transport_factories[upgrades[0]]
                    self._transport = transport_factory.buildTransport(self._reactor)

                self._registertransport(self._transport)

                return self._transport.connect(self._transport_context)

            _d.addCallback(__upgradetransport)

            return _d

        d.addCallback(_startconnected)

        def _cleanup(_passthru):
            self._dispatchqueuedevents()

            return _passthru

        d.addBoth(_cleanup)

        return d

    def stop(self):
        """
        Disconnects the underlying :class:`ITransport` provider.

        :returns: a :class:`twisted.internet.defer.Deferred` from the
            :meth:`~ITransport.disconnect` method of the underlying
            :class:`ITransport` provider
        """
        if self._transport is None:
            raise TransportStateError('no transport')

        return self._transport.disconnect()

    #---- Private methods ------------------------------------------------

    def _dispatchqueuedevents(self):
        while self._tmp_event_queue:
            event, args, kw = self._tmp_event_queue.popleft()
            if self._transport is not None:
                _LOGGER.debug('dispatching queued %s event to transport', event)
                self._transport.dispatch(event, *args, **kw)
            else:
                _LOGGER.debug('dropping queued %s event', event)

    @t_defer.inlineCallbacks
    def _handleclose(self, event):
        _LOGGER.debug('received %s event from transport', event)
        self._unregistertransport(self._transport)
        self._transport = None
        self._pingloop_d.cancel()

        try:
            _LOGGER.debug('waiting for ping loop to end...')
            yield self._pingloop_d
        except t_defer.CancelledError:
            _LOGGER.debug('ping loop canceled')
        except Exception: # pylint: disable=broad-except
            _LOGGER.debug('ping loop erred', exc_info=True)
        else:
            _LOGGER.debug('ping loop completed')

        self.dispatch(event)

    def _handleclosestart(self, event):
        _LOGGER.debug('received %s event from transport', event)
        self._unregisterstarttransport(self._transport)
        self._transport = None
        self._queueevent(event)

    def _handleopen(self, event):
        _LOGGER.debug('received %s event from transport', event)
        self._pingloop()
        self.dispatch(event)

    def _handleping(self, event, payload):
        _LOGGER.debug('received %s => %r event from transport', event, payload)
        self.sendeiopacket(EIO_TYPE_PONG, '')
        self.dispatch(event, payload)

    def _onerror(self, event, exception):
        _LOGGER.debug('received %s event from transport', event)
        _LOGGER.debug(exception)
        self.dispatch(event, exception)

    def _onnopayload(self, event):
        _LOGGER.debug('received %s event from transport', event)
        self.dispatch(event)

    def _onpayload(self, event, payload):
        _LOGGER.debug('received %s => %r event from transport', event, payload)
        self.dispatch(event, payload)

    def _onupgrade(self, event):
        _LOGGER.debug('received %s event from transport', event)
        self.dispatch(event)

    def _queueevent(self, event, *args, **kw):
        _LOGGER.debug('queuing %s event from transport', event)
        self._tmp_event_queue.append(( event, args, kw ))

    def _pingloop(self):
        def _sendping():
            _d = self.sendeiopacket(EIO_TYPE_PING, 'probe')
            _d.addCallback(_loop)
            handled = ( t_defer.CancelledError, t_client.ResponseFailed, ReceivedClosePacket, UnknownSessionIdError )
            _d.addErrback(txrc.logging.logerrback, logger=_LOGGER, log_lvl=logging.WARNING, msg='Failure raised when pinging:', handled=handled)

            return _d

        def _loop(_passthru=None):
            if not self.running:
                _LOGGER.debug('ping loop halting')

                return

            self._pingloop_d = t_task.deferLater(self._reactor, self._transport_context.ping_interval / 1000, _sendping)

            return _passthru

        _loop()

    def _registerstarttransport(self, transport):
        transport.register(EIO_TYPE_NAMES_BY_CODE[EIO_TYPE_CLOSE],   self._handleclosestart)
        transport.register(EIO_TYPE_NAMES_BY_CODE[EIO_TYPE_OPEN],    self._queueevent)
        transport.register(EIO_TYPE_NAMES_BY_CODE[EIO_TYPE_MESSAGE], self._queueevent)
        transport.register(EIO_TYPE_NAMES_BY_CODE[EIO_TYPE_NOOP],    self._queueevent)
        transport.register(EIO_TYPE_NAMES_BY_CODE[EIO_TYPE_PING],    self._queueevent)
        transport.register(EIO_TYPE_NAMES_BY_CODE[EIO_TYPE_PONG],    self._queueevent)
        transport.register(EIO_TYPE_NAMES_BY_CODE[EIO_TYPE_UPGRADE], self._queueevent)

    def _registertransport(self, transport):
        transport.register(EIO_TYPE_NAMES_BY_CODE[EIO_TYPE_CLOSE],   self._handleclose)
        transport.register(EIO_TYPE_NAMES_BY_CODE[EIO_TYPE_OPEN],    self._handleopen)
        transport.register(EIO_TYPE_NAMES_BY_CODE[EIO_TYPE_MESSAGE], self._onpayload)
        transport.register(EIO_TYPE_NAMES_BY_CODE[EIO_TYPE_NOOP],    self._onnopayload)
        transport.register(EIO_TYPE_NAMES_BY_CODE[EIO_TYPE_PING],    self._handleping)
        transport.register(EIO_TYPE_NAMES_BY_CODE[EIO_TYPE_PONG],    self._onpayload)
        transport.register(EIO_TYPE_NAMES_BY_CODE[EIO_TYPE_UPGRADE], self._onnopayload)

    def _unregisterstarttransport(self, transport):
        transport.unregister(EIO_TYPE_NAMES_BY_CODE[EIO_TYPE_CLOSE],   self._handleclosestart)
        transport.unregister(EIO_TYPE_NAMES_BY_CODE[EIO_TYPE_OPEN],    self._queueevent)
        transport.unregister(EIO_TYPE_NAMES_BY_CODE[EIO_TYPE_MESSAGE], self._queueevent)
        transport.unregister(EIO_TYPE_NAMES_BY_CODE[EIO_TYPE_NOOP],    self._queueevent)
        transport.unregister(EIO_TYPE_NAMES_BY_CODE[EIO_TYPE_PING],    self._queueevent)
        transport.unregister(EIO_TYPE_NAMES_BY_CODE[EIO_TYPE_PONG],    self._queueevent)
        transport.unregister(EIO_TYPE_NAMES_BY_CODE[EIO_TYPE_UPGRADE], self._queueevent)

    def _unregistertransport(self, transport):
        transport.unregister(EIO_TYPE_NAMES_BY_CODE[EIO_TYPE_CLOSE],   self._handleclose)
        transport.unregister(EIO_TYPE_NAMES_BY_CODE[EIO_TYPE_OPEN],    self._handleopen)
        transport.unregister(EIO_TYPE_NAMES_BY_CODE[EIO_TYPE_MESSAGE], self._onpayload)
        transport.unregister(EIO_TYPE_NAMES_BY_CODE[EIO_TYPE_NOOP],    self._onnopayload)
        transport.unregister(EIO_TYPE_NAMES_BY_CODE[EIO_TYPE_PING],    self._handleping)
        transport.unregister(EIO_TYPE_NAMES_BY_CODE[EIO_TYPE_PONG],    self._onpayload)
        transport.unregister(EIO_TYPE_NAMES_BY_CODE[EIO_TYPE_UPGRADE], self._onnopayload)

#---- Functions ----------------------------------------------------------

#=========================================================================
def decbinpayloadsgen(raw):
    """
    Decodes a binary Engine.IO message containing zero or more payloads
    and yields their respective packets. String packets are returned as
    unicode, either as :class:`~future.types.newstr.newstr` in Python 2
    or :class:`str` in Python 3. Binary packets are returned as raw bytes,
    either as :class:`~future.types.newbytes.newbytes` in Python 2 or
    :class:`bytes` in Python 3.

    :param bytes raw: the raw Engine.IO message containing zero or more
        payloads

    :returns: a :class:`generator` that yeilds each packet

    :raises: :exc:`PayloadDecodeError` if there was a problem decoding
        `raw`
    """
    raw = bytes(raw)
    pos = 0

    while True:
        try:
            payload_type = raw[pos]
        except IndexError:
            return

        if payload_type not in _PAYLOAD_TYPES:
            raise PayloadDecodeError('unrecognized payload type {} at {}'.format(payload_type, pos))

        pos += 1
        payload_len_pos = pos
        payload_len_str = ''

        while True:
            try:
                byte_int = raw[pos]
            except IndexError:
                raise PayloadDecodeError('payload length field truncated at {}'.format(pos))

            if byte_int == 255:
                pos += 1
                break

            if byte_int < 0 \
                    or byte_int > 9:
                raise PayloadDecodeError('unrecognized length byte {} at {}'.format(byte_int, pos))

            pos += 1
            payload_len_str += str(byte_int)

        # Number.MAX_VALUE ~ 1 * 10 ** 308 or 310 characters
        if len(payload_len_str) > 310:
            raise PayloadDecodeError('{} exceeds max bytes for length field at {}'.format(payload_len_str, payload_len_pos))

        payload_len = int(payload_len_str, 10)
        payload = raw[pos:pos + payload_len]

        if len(payload) != payload_len:
            raise PayloadDecodeError('payload data truncated (received only {} of {} expected octets) at {}'.format(len(payload), payload_len, pos))

        if payload_type == _PAYLOAD_TYPE_STR:
            payload = payload.decode('utf_8')

        pos += payload_len
        yield payload

#=========================================================================
def deceiopacket(packet):
    """
    Decodes a single Engine.IO packet. String packets are returned as
    unicode, either as :class:`~future.types.newstr.newstr` in Python 2
    or :class:`str` in Python 3. Binary packets are returned as raw bytes,
    either as :class:`~future.types.newbytes.newbytes` in Python 2 or
    :class:`bytes` in Python 3.

    :param packet: the packet to decode

    :type packet: `bytes` or `str` (`unicode`)

    :returns: a tuple ( ``packet_type``, ``packet_data`` ), where
        ``packet_type`` is one of the values from
        :const:`EIO_TYPE_CODES_BY_NAME`, and ``packet_data``
        contains the data
    """
    if isinstance(packet, str):
        try:
            packet_type = bytes(packet[0:1].encode('ascii'))
            packet_data = str(packet[1:])
        except UnicodeEncodeError:
            packet_type = bytes(b'\xff')
            packet_data = None
    elif isinstance(packet, bytes):
        packet_type = bytes(packet[0:1])
        packet_data = bytes(packet[1:])
    else:
        raise TypeError('packet type must be one of bytes or str, not {}'.format(type(packet).__name__))

    if len(packet) == 0:
        raise PayloadDecodeError('packet truncated')

    if packet_type not in EIO_TYPE_NAMES_BY_CODE:
        raise PayloadDecodeError('unrecognized packet type "{!r}"'.format(packet_type))

    return packet_type, packet_data

#=========================================================================
def deceiopacketsgen(packets):
    """
    Calls :func:`deceiopacket` on each item in ``packets``.

    :param iterable packets: the packets to decode

    :returns: an iterable of decoded packets
    """
    return map(deceiopacket, packets)

#=========================================================================
def encbinpayload(packet):
    """
    Encodes an Engine.IO packet as an Engine.IO payload. A unicode packet
    is encoded as a (UTF-8) string payload. A bytes packet is encoded as a
    binary payload. Other types are considered errors.

    :param packet: the packet to encode as an Engine.IO payload

    :returns: the packet encoded as an Engine.IO payload

    :raises: :exc:`TypeError` if there was a problem encoding `packet`
    """
    if isinstance(packet, str):
        payload_type = _PAYLOAD_TYPE_STR
        packet = str(packet).encode('utf_8')
    elif isinstance(packet, bytes):
        payload_type = _PAYLOAD_TYPE_BIN
        packet = bytes(packet)
    else:
        raise TypeError('packet type must be one of bytes or str, not {}'.format(type(packet).__name__))

    packet_len_str = str(len(packet))
    payload_len_bytes = bytes([ ord(c) - ord('0') for c in packet_len_str ])

    return bytes(( payload_type, )) + payload_len_bytes + bytes(( 255, )) + packet

#=========================================================================
def encbinpayloads(packets):
    """
    Encodes zero or more Engine.IO packets by calling
    :func:`encbinpayloadsgen` and joining the results.

    :param iterable packets: the packets to encode as Engine.IO payloads

    :returns: the payload

    :raises: exceptions raised by :func:`encbinpayload` are re-raised
    """
    # See github:PythonCharmers/python-future#172
    return bytes(b''.join(encbinpayloadsgen(packets)))

#=========================================================================
def encbinpayloadsgen(packets):
    """
    Encodes zero or more Engine.IO packets by calling
    :func:`encbinpayload` and yielding the results.

    :param iterable packets: the packets to encode as Engine.IO payloads

    :returns: a :class:`generator` that yeilds each payload

    :raises: exceptions raised by :func:`encbinpayload` are re-raised
    """
    for i, packet in enumerate(packets):
        try:
            yield encbinpayload(packet)
        except Exception as exc:
            raise type(exc)(exc.args[0] + ' for packet[{}]'.format(i), *exc.args[1:])

#=========================================================================
def enceiopacket(packet_type, packet_data = ''):
    """
    Encodes a single Engine.IO packet.

    :param bytes packet_type: the packet type, one of the values from
        :const:`EIO_TYPE_CODES_BY_NAME`

    :param packet_data: the packet data (:class:`bytes` for a binary
        packet; :class:`str` (:class:`unicode`) for a string packet)

    :type packet_data: `bytes` or `str` (`unicode`)

    :returns: the packet, whose type is one of bytes or str
        (:class:`unicode`)

    :raises: :class:`PayloadEncodeError` if `packet_type` is not a
        recognized value
    """
    if packet_type not in EIO_TYPE_NAMES_BY_CODE:
        raise PayloadEncodeError('unrecognized packet type "{!r}"'.format(packet_type))

    if isinstance(packet_data, str):
        packet_type = packet_type.decode()
    elif isinstance(packet_data, bytes):
        pass
    else:
        raise TypeError('packet_data type must be one of bytes or str, not {}'.format(type(packet_data).__name__))

    return packet_type + packet_data

#=========================================================================
def jsondumps(*args, **kw):
    kw.setdefault('use_decimal', True)

    return simplejson.dumps(*args, **kw)

#=========================================================================
def jsonloads(*args, **kw):
    kw.setdefault('parse_constant', decimal.Decimal)
    kw.setdefault('use_decimal', True)

    return simplejson.loads(*args, **kw)
