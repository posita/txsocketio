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
from builtins import * # pylint: disable=redefined-builtin,unused-wildcard-import,useless-suppression,wildcard-import
from future.builtins.disabled import * # pylint: disable=redefined-builtin,unused-wildcard-import,useless-suppression,wildcard-import

#---- Imports ------------------------------------------------------------

import logging
from twisted.trial import unittest as t_unittest
# TODO
# from twisted.web import (
#     http_headers as t_http_headers,
#     iweb as t_iweb,
# )
# from zope import interface # pyl#int: disable=import-error

from txsocketio.engineio import (
    PACKET_TYPE_CODES_BY_NAME,
    PayloadDecodeError,
    PayloadEncodeError,
    TransportContext,
    decbinpayloadsgen,
    decpacket,
    encbinpayloads,
    encbinpayloadsgen,
    encpacket,
)

#---- Constants ----------------------------------------------------------

__all__ = ()

_LOGGER = logging.getLogger(__name__)

#---- Classes ------------------------------------------------------------

# TODO
# #=========================================================================
# @interface.implementer(t_iweb.IResponse)
# class MockResponse(object):
#
#     #---- Constructor ----------------------------------------------------
#
#     def __init__(self, body=b''):
#         self.version = ( b'HTTP', 1, 1 )
#         self.code = 200
#         self.phrase = b'OK'
#         self.length = t_iweb.UNKNOWN_LENGTH
#         self.headers = []
#         self.previousResponse = None
#         self.setBody(body)
#
#     #---- Public hooks ---------------------------------------------------
#
#     def deliverBody(self, protocol):
#         protocol.dataReceived(self.body)
#         protocol.connectionLost(None)
#
#     def setPreviousResponse(self, response):
#         self.previousResponse = response
#
#     #---- Public methods -------------------------------------------------
#
#     def setBody(self, body=b''):
#         self._body = b''
#         self.length = t_iweb.UNKNOWN_LENGTH
#         self.headers = [ h for h in self.headers if h[0] != b'Content-Length' ]
#         self.headers.append(( b'Content-Length', str(self.length).encode('ascii') ))

#=========================================================================
class PacketsTestCase(t_unittest.TestCase):

    longMessage = True

    #---- Public constants -----------------------------------------------

    GOOD_STR_TYPE = PACKET_TYPE_CODES_BY_NAME['ping']
    GOOD_STR_DATA = str('{}')
    GOOD_STR_PACKET = GOOD_STR_TYPE.decode('ascii') + GOOD_STR_DATA
    GOOD_BIN_TYPE = PACKET_TYPE_CODES_BY_NAME['pong']
    GOOD_BIN_DATA = bytes(b'\x00\x01\x02\x03')
    GOOD_BIN_PACKET = GOOD_BIN_TYPE + GOOD_BIN_DATA
    BAD_TYPE = bytes(b'\x2a')
    BAD_TYPE_STR_PACKET = BAD_TYPE.decode('latin_1') + GOOD_STR_DATA
    BAD_TYPE_BIN_PACKET = BAD_TYPE + GOOD_BIN_DATA
    BAD_TRUNC_PACKET = ''

    #---- Public hooks ---------------------------------------------------

    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()

    def test_packetdec(self):
        packets = [
            PacketsTestCase.GOOD_STR_PACKET,
            PacketsTestCase.GOOD_BIN_PACKET,
        ]
        packets_type_data = [
            ( PacketsTestCase.GOOD_STR_TYPE, PacketsTestCase.GOOD_STR_DATA ),
            ( PacketsTestCase.GOOD_BIN_TYPE, PacketsTestCase.GOOD_BIN_DATA ),
        ]

        for i, zipped in enumerate(zip(packets_type_data, packets)):
            expected, packet = zipped
            self.assertEqual(expected, decpacket(packet), msg = 'packet[{}]: {!r}'.format(i, packet))

    def test_packetenc(self):
        packets_type_data = [
            ( PacketsTestCase.GOOD_STR_TYPE, PacketsTestCase.GOOD_STR_DATA ),
            ( PacketsTestCase.GOOD_BIN_TYPE, PacketsTestCase.GOOD_BIN_DATA ),
        ]
        packets = [
            PacketsTestCase.GOOD_STR_PACKET,
            PacketsTestCase.GOOD_BIN_PACKET,
        ]

        for i, zipped in enumerate(zip(packets, packets_type_data)):
            expected, packet_type_data = zipped
            self.assertEqual(expected, encpacket(*packet_type_data), msg = 'packet_type_data[{}]: {!r}'.format(i, packet_type_data))

    def test_packetdecbadlen(self):
        with self.assertRaisesRegex(PayloadDecodeError, r'^packet truncated$'):
            decpacket(PacketsTestCase.BAD_TRUNC_PACKET)

    def test_packetdecbadtype(self):
        packets = [
            PacketsTestCase.BAD_TYPE_STR_PACKET,
            PacketsTestCase.BAD_TYPE_BIN_PACKET,
        ]

        for i, packet in enumerate(packets):
            with self.assertRaisesRegex(PayloadDecodeError, r'^unrecognized packet type "', msg = 'packet[{}]: {!r}'.format(i, packet)):
                decpacket(packet)

        packets = [
            list(range(10)),
            tuple(range(10)),
            42,
        ]

        for i, packet in enumerate(packets):
            with self.assertRaisesRegex(TypeError, r'^packet type must be one of bytes or str, not .+$', msg = 'packet[{}]: {!r}'.format(i, packet)):
                decpacket(packet)

    def test_packetencbadtype(self):
        packets_type_data = [
            ( PacketsTestCase.BAD_TYPE, PacketsTestCase.GOOD_STR_DATA ),
            ( PacketsTestCase.BAD_TYPE, PacketsTestCase.GOOD_BIN_DATA ),
        ]

        for i, packet_type_data in enumerate(packets_type_data):
            with self.assertRaisesRegex(PayloadEncodeError, r'^unrecognized packet type "', msg = 'packet_type_data[{}]: {!r}'.format(i, packet_type_data)):
                encpacket(*packet_type_data)

        packets_type_data = [
            ( PACKET_TYPE_CODES_BY_NAME['message'], list(range(10)) ),
            ( PACKET_TYPE_CODES_BY_NAME['message'], tuple(range(10)) ),
            ( PACKET_TYPE_CODES_BY_NAME['message'], 42 ),
        ]

        for i, packet_type_data in enumerate(packets_type_data):
            with self.assertRaisesRegex(TypeError, r'^packet_data type must be one of bytes or str, not .+$', msg = 'packet[{}]: {!r}'.format(i, packet_type_data)):
                encpacket(*packet_type_data)

    def test_packetdecenc(self):
        packets = [
            PacketsTestCase.GOOD_STR_PACKET,
            PacketsTestCase.GOOD_BIN_PACKET,
        ]

        for i, packet in enumerate(packets):
            self.assertEqual(packet, encpacket(*decpacket(packet)), msg = 'packet[{}]: {!r}'.format(i, packet))

    def test_packetencdec(self):
        packets_type_data = [
            ( PacketsTestCase.GOOD_STR_TYPE, PacketsTestCase.GOOD_STR_DATA ),
            ( PacketsTestCase.GOOD_BIN_TYPE, PacketsTestCase.GOOD_BIN_DATA ),
        ]

        for i, packet_type_data in enumerate(packets_type_data):
            self.assertEqual(packet_type_data, decpacket(encpacket(*packet_type_data)), msg = 'packet_type_data[{}]: {!r}'.format(i, packet_type_data))

#=========================================================================
class PayloadsTestCase(t_unittest.TestCase):

    longMessage = True

    #---- Public constants -----------------------------------------------

    GOOD_STR_PACKET = str('4{}')
    GOOD_STR_PACKET_PAYLOAD = bytes(b'\x00\x03\xff' + GOOD_STR_PACKET.encode('utf_8'))
    GOOD_BIN_PACKET = bytes(b'4\x00\x01\x02\x03')
    GOOD_BIN_PACKET_PAYLOAD = bytes(b'\x01\x05\xff' + GOOD_BIN_PACKET)
    BAD_TYPE_PAYLOAD = bytes(b'\x02' + GOOD_BIN_PACKET_PAYLOAD[1:])
    BAD_LEN_OCTET_PAYLOAD = bytes(b'\x00\x0a\xff6')
    BAD_LEN_TRUNC_PAYLOAD = bytes(b'\x00\x01\x02')
    BAD_LEN_VALUE_PAYLOAD = bytes(b'\x00\x03\x01\x01\xff6')
    BAD_TRUNC_PAYLOAD = bytes(b'\x00\x03\xff4')

    #---- Public hooks ---------------------------------------------------

    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()

    def test_payloaddec(self):
        raw = PayloadsTestCase.GOOD_STR_PACKET_PAYLOAD
        expected = [
            PayloadsTestCase.GOOD_STR_PACKET,
        ]
        actual = list(decbinpayloadsgen(raw))
        self.assertEqual(expected, actual)

        raw = PayloadsTestCase.GOOD_BIN_PACKET_PAYLOAD
        expected = [
            PayloadsTestCase.GOOD_BIN_PACKET,
        ]
        actual = list(decbinpayloadsgen(raw))
        self.assertEqual(expected, actual)

        raw = PayloadsTestCase.GOOD_BIN_PACKET_PAYLOAD \
            + PayloadsTestCase.GOOD_STR_PACKET_PAYLOAD \
            + PayloadsTestCase.GOOD_BIN_PACKET_PAYLOAD \
            + PayloadsTestCase.GOOD_STR_PACKET_PAYLOAD
        expected = [
            PayloadsTestCase.GOOD_BIN_PACKET,
            PayloadsTestCase.GOOD_STR_PACKET,
            PayloadsTestCase.GOOD_BIN_PACKET,
            PayloadsTestCase.GOOD_STR_PACKET,
        ]
        actual = list(decbinpayloadsgen(raw))
        self.assertEqual(expected, actual)

    def test_payloadenc(self):
        packets = (
            PayloadsTestCase.GOOD_STR_PACKET,
        )
        expected = [
            PayloadsTestCase.GOOD_STR_PACKET_PAYLOAD,
        ]
        actual = list(encbinpayloadsgen(packets))
        self.assertEqual(expected, actual)

        packets = (
            PayloadsTestCase.GOOD_BIN_PACKET,
        )
        expected = [
            PayloadsTestCase.GOOD_BIN_PACKET_PAYLOAD,
        ]
        actual = list(encbinpayloadsgen(packets))
        self.assertEqual(expected, actual)

        packets = (
            PayloadsTestCase.GOOD_STR_PACKET,
            PayloadsTestCase.GOOD_BIN_PACKET,
            PayloadsTestCase.GOOD_STR_PACKET,
            PayloadsTestCase.GOOD_BIN_PACKET,
        )
        expected = [
            PayloadsTestCase.GOOD_STR_PACKET_PAYLOAD,
            PayloadsTestCase.GOOD_BIN_PACKET_PAYLOAD,
            PayloadsTestCase.GOOD_STR_PACKET_PAYLOAD,
            PayloadsTestCase.GOOD_BIN_PACKET_PAYLOAD,
        ]
        actual = list(encbinpayloadsgen(packets))
        self.assertEqual(expected, actual)

    def test_payloaddecbadlen(self):
        raw = PayloadsTestCase.BAD_LEN_OCTET_PAYLOAD
        expected = []
        actual = []

        with self.assertRaisesRegex(PayloadDecodeError, r'^unrecognized length byte 10 at 1$'):
            for i in decbinpayloadsgen(raw):
                actual.append(i)

        self.assertEqual(expected, actual)

        raw = PayloadsTestCase.GOOD_BIN_PACKET_PAYLOAD \
            + PayloadsTestCase.GOOD_STR_PACKET_PAYLOAD \
            + PayloadsTestCase.BAD_LEN_OCTET_PAYLOAD
        expected = [
            PayloadsTestCase.GOOD_BIN_PACKET,
            PayloadsTestCase.GOOD_STR_PACKET,
        ]
        actual = []

        with self.assertRaisesRegex(PayloadDecodeError, r'^unrecognized length byte 10 at 15$'):
            for i in decbinpayloadsgen(raw):
                actual.append(i)

        self.assertEqual(expected, actual)

        raw = PayloadsTestCase.BAD_LEN_TRUNC_PAYLOAD
        expected = []
        actual = []

        with self.assertRaisesRegex(PayloadDecodeError, r'^payload length field truncated at 3$'):
            for i in decbinpayloadsgen(raw):
                actual.append(i)

        self.assertEqual(expected, actual)

        raw = PayloadsTestCase.GOOD_STR_PACKET_PAYLOAD \
            + PayloadsTestCase.GOOD_BIN_PACKET_PAYLOAD \
            + PayloadsTestCase.BAD_LEN_TRUNC_PAYLOAD
        expected = [
            PayloadsTestCase.GOOD_STR_PACKET,
            PayloadsTestCase.GOOD_BIN_PACKET,
        ]
        actual = []

        with self.assertRaisesRegex(PayloadDecodeError, r'^payload length field truncated at 17$'):
            for i in decbinpayloadsgen(raw):
                actual.append(i)

        self.assertEqual(expected, actual)

        raw = PayloadsTestCase.BAD_LEN_VALUE_PAYLOAD
        expected = []
        actual = []

        with self.assertRaisesRegex(PayloadDecodeError, r'^311 exceeds max bytes for length field at 5$'):
            for i in decbinpayloadsgen(raw):
                actual.append(i)

        self.assertEqual(expected, actual)

        raw = PayloadsTestCase.GOOD_BIN_PACKET_PAYLOAD \
            + PayloadsTestCase.GOOD_STR_PACKET_PAYLOAD \
            + PayloadsTestCase.BAD_LEN_VALUE_PAYLOAD
        expected = [
            PayloadsTestCase.GOOD_BIN_PACKET,
            PayloadsTestCase.GOOD_STR_PACKET,
        ]
        actual = []

        with self.assertRaisesRegex(PayloadDecodeError, r'^311 exceeds max bytes for length field at 19$'):
            for i in decbinpayloadsgen(raw):
                actual.append(i)

        self.assertEqual(expected, actual)

    def test_payloaddecbadpayload(self):
        raw = PayloadsTestCase.BAD_TRUNC_PAYLOAD
        expected = []
        actual = []

        with self.assertRaisesRegex(PayloadDecodeError, r'^payload data truncated \(received only 1 of 3 expected octets\) at 3$'):
            for i in decbinpayloadsgen(raw):
                actual.append(i)

        self.assertEqual(expected, actual)

        raw = PayloadsTestCase.GOOD_STR_PACKET_PAYLOAD \
            + PayloadsTestCase.GOOD_BIN_PACKET_PAYLOAD \
            + PayloadsTestCase.BAD_TRUNC_PAYLOAD
        expected = [
            PayloadsTestCase.GOOD_STR_PACKET,
            PayloadsTestCase.GOOD_BIN_PACKET,
        ]
        actual = []

        with self.assertRaisesRegex(PayloadDecodeError, r'^payload data truncated \(received only 1 of 3 expected octets\) at 17$'):
            for i in decbinpayloadsgen(raw):
                actual.append(i)

        self.assertEqual(expected, actual)

    def test_payloaddecbadtype(self):
        raw = PayloadsTestCase.BAD_TYPE_PAYLOAD
        expected = []
        actual = []

        with self.assertRaisesRegex(PayloadDecodeError, r'^unrecognized payload type 2 at 0$'):
            for i in decbinpayloadsgen(raw):
                actual.append(i)

        self.assertEqual(expected, actual)

        raw = PayloadsTestCase.GOOD_STR_PACKET_PAYLOAD \
            + PayloadsTestCase.GOOD_BIN_PACKET_PAYLOAD \
            + PayloadsTestCase.BAD_TYPE_PAYLOAD
        expected = [
            PayloadsTestCase.GOOD_STR_PACKET,
            PayloadsTestCase.GOOD_BIN_PACKET,
        ]
        actual = []

        with self.assertRaisesRegex(PayloadDecodeError, r'^unrecognized payload type 2 at 14$'):
            for i in decbinpayloadsgen(raw):
                actual.append(i)

        self.assertEqual(expected, actual)

    def test_payloadencbadtype(self):
        packets = (
            PayloadsTestCase.GOOD_STR_PACKET,
            PayloadsTestCase.GOOD_BIN_PACKET,
            42,
            PayloadsTestCase.GOOD_STR_PACKET,
            PayloadsTestCase.GOOD_BIN_PACKET,
        )
        expected = [
            PayloadsTestCase.GOOD_STR_PACKET_PAYLOAD,
            PayloadsTestCase.GOOD_BIN_PACKET_PAYLOAD,
        ]
        actual = []

        with self.assertRaisesRegex(TypeError, r'^packet type must be one of bytes or str, not .+ for packet\[2\]$'):
            for i in encbinpayloadsgen(packets):
                actual.append(i)

        self.assertEqual(expected, actual)

    def test_payloaddecenc(self):
        raw = b''
        packets = list(decbinpayloadsgen(raw))
        self.assertEqual(raw, encbinpayloads(packets))

        raw = PayloadsTestCase.GOOD_STR_PACKET_PAYLOAD
        packets = list(decbinpayloadsgen(raw))
        self.assertEqual(raw, encbinpayloads(packets))

        raw = PayloadsTestCase.GOOD_BIN_PACKET_PAYLOAD
        packets = list(decbinpayloadsgen(raw))
        self.assertEqual(raw, encbinpayloads(packets))

        raw = PayloadsTestCase.GOOD_BIN_PACKET_PAYLOAD \
            + PayloadsTestCase.GOOD_STR_PACKET_PAYLOAD \
            + PayloadsTestCase.GOOD_BIN_PACKET_PAYLOAD \
            + PayloadsTestCase.GOOD_STR_PACKET_PAYLOAD
        packets = list(decbinpayloadsgen(raw))
        self.assertEqual(raw, encbinpayloads(packets))

    def test_payloadencdec(self):
        packets = []
        raw = encbinpayloads(packets)
        self.assertEqual(packets, list(decbinpayloadsgen(raw)))

        packets = [
            PayloadsTestCase.GOOD_STR_PACKET,
        ]
        raw = encbinpayloads(packets)
        self.assertEqual(packets, list(decbinpayloadsgen(raw)))

        packets = [
            PayloadsTestCase.GOOD_BIN_PACKET,
        ]
        raw = encbinpayloads(packets)
        self.assertEqual(packets, list(decbinpayloadsgen(raw)))

        packets = [
            PayloadsTestCase.GOOD_STR_PACKET,
            PayloadsTestCase.GOOD_BIN_PACKET,
            PayloadsTestCase.GOOD_STR_PACKET,
            PayloadsTestCase.GOOD_BIN_PACKET,
        ]
        raw = encbinpayloads(packets)
        self.assertEqual(packets, list(decbinpayloadsgen(raw)))

#=========================================================================
class TransportContextTestCase(t_unittest.TestCase):

    longMessage = True

    #---- Public hooks ---------------------------------------------------

    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()

    def test_transportcontext(self):
        base_url = b'http://dummy.dom/engine.io/'
        tc = TransportContext(base_url)
        self.assertEqual(tc.base_url, base_url)

        ping_interval = 4321
        ping_timeout = 1234
        session_id = '0123456789abcdef'
        upgrades = [ 'websocket', 'girlfriend 2.0' ]
        tc.set(session_id, ping_timeout, ping_interval, upgrades)
        self.assertEqual(tc.ping_interval, ping_interval)
        self.assertEqual(tc.ping_timeout, ping_timeout)
        self.assertEqual(tc.session_id, session_id)
        self.assertEqual(tc.upgrades, upgrades)

        tc.clear()
        self.assertIsNone(tc.ping_interval)
        self.assertIsNone(tc.ping_timeout)
        self.assertIsNone(tc.session_id)
        self.assertIsNone(tc.upgrades)

#---- Initialization -----------------------------------------------------

if __name__ == '__main__':
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    from unittest import main
    main()
