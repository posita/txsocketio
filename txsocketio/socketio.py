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
from future.builtins.disabled import * # pylint: disable=redefined-builtin,unused-wildcard-import,useless-suppression,wildcard-import
from future.utils import iteritems
from future.utils import iterkeys

#---- Imports ------------------------------------------------------------

import logging
import re

from .engineio import (
    EIO_TYPE_MESSAGE,
    EIO_TYPE_NAMES_BY_CODE,
    EngineIo,
    EngineIoException,
    PayloadDecodeError,
    PayloadEncodeError,
    jsondumps,
    jsonloads,
)

#---- Constants ----------------------------------------------------------

__all__ = (
    'SIO_TYPE_ACK',
    'SIO_TYPE_BIN_ACK',
    'SIO_TYPE_BIN_EVENT',
    'SIO_TYPE_CODES_BY_NAME',
    'SIO_TYPE_CONNECT',
    'SIO_TYPE_DISCONNECT',
    'SIO_TYPE_ERROR',
    'SIO_TYPE_EVENT',
    'SIO_TYPE_NAMES_BY_CODE',
    'SocketIo',
    'SocketIoException',
)

SIO_TYPE_CONNECT    = bytes(b'0')
SIO_TYPE_DISCONNECT = bytes(b'1')
SIO_TYPE_EVENT      = bytes(b'2')
SIO_TYPE_ACK        = bytes(b'3')
SIO_TYPE_ERROR      = bytes(b'4')
SIO_TYPE_BIN_EVENT  = bytes(b'5')
SIO_TYPE_BIN_ACK    = bytes(b'6')

SIO_TYPE_NAMES_BY_CODE = {
    SIO_TYPE_CONNECT:    'connect',
    SIO_TYPE_DISCONNECT: 'disconnect',
    SIO_TYPE_EVENT:      'event',
    SIO_TYPE_ACK:        'ack',
    SIO_TYPE_ERROR:      'error',
    SIO_TYPE_BIN_EVENT:  'binary_event',
    SIO_TYPE_BIN_ACK:    'binary_ack',
}

SIO_TYPE_CODES_BY_NAME = dict(( ( v, k ) for k, v in iteritems(SIO_TYPE_NAMES_BY_CODE) ))

_SIO_ACK_TYPES_BY_TYPE = {
    SIO_TYPE_EVENT: SIO_TYPE_ACK,
    SIO_TYPE_BIN_EVENT: SIO_TYPE_BIN_ACK,
}

_PACKET_RES = (
    r'^ (?P<path>/[^,]*) (?:, (?P<id>(?:0|[1-9][0-9]*))? (?P<data>[^0-9].*)?)? $',
    r'^ (?P<path>)            (?P<id>(?:0|[1-9][0-9]*))  (?P<data>[^0-9].*)?   $',
    r'^ (?P<path>)            (?P<id>(?:0|[1-9][0-9]*))? (?P<data>[^0-9].*)    $',
    r'^ (?P<path>)            (?P<id>)                   (?P<data>)            $',
)

_PACKET_RE_FLAGS = re.DOTALL | re.VERBOSE

_LOGGER = logging.getLogger(__name__)

#---- Exceptions ---------------------------------------------------------

#=========================================================================
class SocketIoException(EngineIoException):
    ""

#---- Classes ------------------------------------------------------------

#=========================================================================
class SocketIo(EngineIo):
    """
    Abstracts an Socket.IO connection, handling any underlying transport
    upgrades, and dispatching received packets as events with ``event``
    set to one of one of the keys from :const:`SIO_TYPE_CODES_BY_NAME`.

    Arguments are the same as with :class:`EngineIo`.
    """

    #---- Constructor ----------------------------------------------------

    def __init__(self, base_url, transport_factories=None, reactor=None):
        super().__init__(base_url, transport_factories, reactor)
        self._ack_serial = 1
        self.register(EIO_TYPE_NAMES_BY_CODE[EIO_TYPE_MESSAGE], self._onmessage)

    #---- Public methods -------------------------------------------------

    def connect(self, path):
        """
        TODO
        """
        return self.sendsiopacket(SIO_TYPE_CONNECT, packet_path=path)

    def disconnect(self, path):
        """
        TODO
        """
        return self.sendsiopacket(SIO_TYPE_DISCONNECT, packet_path=path)

    def emit(self, event, *args, **kw):
        """
        TODO
        """
        if set(kw).difference(( 'callback', 'path' )):
            raise TypeError('unexpected keyword argument(s): {}'.format(', '.join(iterkeys(kw))))

        callback = kw.get('callback', None)
        path = kw.get('path', '/')
        args_obj = [ event ]
        args_obj.extend(args)

        return self.sendsiopacket(SIO_TYPE_EVENT, args_obj, packet_path=path, ack_callback=callback)

    def sendsiopacket(self, packet_type, packet_obj=None, packet_path='/', ack_callback=None):
        """
        Sends a Socket.IO packet via a
        :const:`txsocketio.EIO_TYPE_MESSAGE` Engine.IO packet.

        TODO
        """
        if packet_type in ( SIO_TYPE_BIN_EVENT, SIO_TYPE_BIN_ACK ):
            raise NotImplementedError('binary Socket.IO packets are currently unsupported')

        if ack_callback is not None:
            try:
                ack_type = _SIO_ACK_TYPES_BY_TYPE[packet_type]
            except KeyError:
                raise ValueError('ack callback set, but packet type is "{}"'.format(SIO_TYPE_NAMES_BY_CODE[packet_type]))

            ack_serial = self._ack_serial
            self._ack_serial += 1
            ack_id_event = '{}-{}'.format(SIO_TYPE_NAMES_BY_CODE[ack_type], ack_serial)
            self.once(ack_id_event, lambda event, *args, **kw: ack_callback(*args, **kw))
        else:
            ack_serial = None

        return self.sendeiopacket(EIO_TYPE_MESSAGE, encsiopacket(packet_type, packet_obj, packet_path, ack_serial))

    #---- Public methods -------------------------------------------------

    def _onmessage(self, _, payload):
        packet_type, packet_obj, packet_path, packet_id = decsiopacket(payload)
        packet_name = SIO_TYPE_NAMES_BY_CODE[packet_type]
        self.dispatch(packet_name, packet_path, packet_obj)

        if packet_id is not None \
                and packet_type in ( SIO_TYPE_ACK, SIO_TYPE_BIN_ACK ):
            ack_id_event = '{}-{}'.format(SIO_TYPE_NAMES_BY_CODE[packet_type], packet_id)
            self.dispatch(ack_id_event, packet_path, packet_obj)

#---- Functions ----------------------------------------------------------

#=========================================================================
def decsiopacket(packet):
    """
    Decodes a single Socket.IO packet. String packets are returned as
    unicode, either as :class:`~future.types.newstr.newstr` in Python 2
    or :class:`str` in Python 3. Binary packets are returned as raw bytes,
    either as :class:`~future.types.newbytes.newbytes` in Python 2 or
    :class:`bytes` in Python 3.

    :param packet: the packet to decode

    :type packet: `bytes` or `str` (`unicode`)

    :returns: a tuple ( ``packet_type``, ``packet_obj``, TODO ), where
        ``packet_type`` is one of the values from
        :const:`SIO_TYPE_CODES_BY_NAME`, and ``packet_obj``
        contains the data
    """
    if isinstance(packet, str):
        try:
            packet_type = bytes(packet[0:1].encode('ascii'))
            packet_data = str(packet[1:])
        except UnicodeEncodeError:
            packet_type = bytes(b'\xff')
            packet_data = None

        if packet_type in ( SIO_TYPE_BIN_EVENT, SIO_TYPE_BIN_ACK ):
            raise PayloadDecodeError('packet type is "{}", but payload is not binary'.format(SIO_TYPE_NAMES_BY_CODE[packet_type]))
    elif isinstance(packet, bytes):
        packet_type = bytes(packet[0:1])
        packet_data = bytes(packet[1:])

        if packet_type in SIO_TYPE_NAMES_BY_CODE \
                and packet_type not in ( SIO_TYPE_BIN_EVENT, SIO_TYPE_BIN_ACK ):
            raise PayloadDecodeError('packet type is "{}", but payload is binary'.format(SIO_TYPE_NAMES_BY_CODE[packet_type]))

        raise NotImplementedError('binary Socket.IO packets are currently unsupported')
    else:
        raise TypeError('packet type must be one of bytes or str, not {}'.format(type(packet).__name__))

    if len(packet) == 0:
        raise PayloadDecodeError('packet truncated')

    if packet_type not in SIO_TYPE_NAMES_BY_CODE:
        raise PayloadDecodeError('unrecognized packet type "{!r}"'.format(packet_type))

    for packet_re in _PACKET_RES:
        matches = re.search(packet_re, packet_data, _PACKET_RE_FLAGS)

        if matches:
            break

    if matches:
        packet_path = matches.group('path')
        packet_path = packet_path if packet_path else '/'
        packet_id = matches.group('id')
        packet_id = int(packet_id, 10) if packet_id else None
        packet_json = matches.group('data')

        try:
            packet_obj = jsonloads(packet_json) if packet_json else ''
        except ValueError:
            raise PayloadDecodeError('unparsable JSON data')
    else:
        raise PayloadDecodeError('unrecognized Socket.IO packet format')

    return packet_type, packet_obj, packet_path, packet_id

#=========================================================================
def encsiopacket(packet_type, packet_obj, packet_path='/', packet_id=None):
    """
    Encodes a single Socket.IO packet.

    :param bytes packet_type: the packet type, one of the values from
        :const:`SIO_TYPE_CODES_BY_NAME`

    :param object packet_obj: JSON-encodeable packet data

    TODO

    :returns: the packet

    :raises: :class:`PayloadEncodeError` if `packet_type` is not a
        recognized value
    """
    if packet_type not in SIO_TYPE_NAMES_BY_CODE:
        raise PayloadEncodeError('unrecognized packet type "{!r}"'.format(packet_type))

    packet_type = packet_type.decode('ascii')
    packet_path = packet_path if packet_path else '/'
    packet_json = '' if packet_obj in ( None, '' ) else jsondumps(packet_obj)
    packet_json = packet_json.decode('utf_8') if isinstance(packet_json, bytes) else packet_json
    packet_tail = '{:d}{}'.format(packet_id, packet_json) if packet_id is not None else packet_json

    return '{}{},{}'.format(packet_type[0], packet_path, packet_tail)
