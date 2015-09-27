#-*- encoding: utf-8; grammar-ext: py; mode: python test-case-name: txsocketio.test_engineio -*-

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
_chr = chr
from future.builtins.disabled import * # pylint: disable=redefined-builtin,unused-wildcard-import,wildcard-import
chr = _chr
del _chr

#---- Constants ----------------------------------------------------------

__all__ = (
    'ENGINEIO_PROTOCOL',
    'EngineIoError',
    'PayloadDecodeError',
    'PayloadEncodeError',
    'TRANSPORTS',
    'decbinpayloadsgen',
    'encbinpayloadsgen',
)

ENGINEIO_PROTOCOL = 3
TRANSPORTS = (
    'websocket',
    'xhr-polling',
)

_PAYLOAD_TYPE_STR = 0
_PAYLOAD_TYPE_BIN = 1
_PAYLOAD_TYPES = (
    _PAYLOAD_TYPE_STR,
    _PAYLOAD_TYPE_BIN,
)

_PACKET_TYPE_STR = bytes(b'0')[0]
_PACKET_TYPE_BIN = bytes(b'1')[0]
_PACKET_TYPES = (
    _PACKET_TYPE_STR,
    _PACKET_TYPE_BIN,
)

#---- Classes ------------------------------------------------------------

#=========================================================================
class EngineIoError(Exception):
    pass

#=========================================================================
class PayloadDecodeError(EngineIoError):
    pass

#=========================================================================
class PayloadEncodeError(EngineIoError):
    pass

#---- Functions ----------------------------------------------------------

#=========================================================================
def decbinpayloadsgen(raw):
    """
    Decodes a binary EngineIO message containing zero or more payloads and
    yields their respective packets. String packets are returned as
    unicode, either as :class:`~future.types.newstr.newstr` in Python 2
    or :class:`str` in Python 3. Binary packets are returned as raw bytes,
    either as :class:`~future.types.newbytes.newbytes` in Python 2 or
    :class:`bytes` in Python 3.

    :param bytes raw: the raw EngineIO message

    :returns: a :obj:`generator` that yeilds each packet

    :raises: :class:`PayloadDecodeError` if there was a problem decoding
             `raw`
    """
    pos = 0

    while True:
        try:
            payload_type = raw[pos]
        except IndexError:
            return

        if payload_type not in _PAYLOAD_TYPES:
            raise PayloadDecodeError('unrecognized payload type {} at {}'.format(payload_type, pos))

        pos += 1
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

        payload_len = int(payload_len_str, 10)

        # Number.MAX_VALUE ~ 1 * 10 ** 308 or 310 characters
        if payload_len > 310:
            raise PayloadDecodeError('{} exceeds max bytes for length field at {}'.format(payload_len, pos))

        payload_len = int(payload_len_str, 10)
        payload = raw[pos:pos + payload_len]

        if len(payload) != payload_len:
            raise PayloadDecodeError('payload data truncated (received only {} of {} expected octets) at {}'.format(len(payload), payload_len, pos))

        if payload_type == _PAYLOAD_TYPE_STR:
            payload = payload.decode('utf_8')

        pos += payload_len

        yield payload

#=========================================================================
def encbinpayloadsgen(packets):
    """
    Encodes zero or more EngineIO packets and yields them as respective
    encoded payloads. String packets are encoded as string types. Bytes
    packets are encoded as binary types. Other types are considered
    errors.

    :param iterable packets: the EngineIO packets

    :returns: a :obj:`generator` that yeilds each payload

    :raises: :class:`PayloadEncodeError` if there was a problem encoding
             one of the `packets`
    """
    for i, packet in enumerate(packets):
        if isinstance(packet, str):
            payload_type = _PAYLOAD_TYPE_STR
            # packet = bytes(packet, 'utf_8') # See PythonCharmers/python-future#171
            packet = bytes(packet.encode('utf_8'))
        elif isinstance(packet, bytes):
            payload_type = _PAYLOAD_TYPE_BIN
        else:
            raise PayloadEncodeError('unable to determine encoding for type "{}" of packet {}'.format(type(packet).__name__, i))

        packet_len_str = str(len(packet))
        payload_len_bytes = bytes([ ord(c) - ord('0') for c in packet_len_str ])

        yield bytes(( payload_type, )) + payload_len_bytes + bytes(( 255, )) + packet
