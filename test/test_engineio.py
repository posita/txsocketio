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
import hypothesis
from hypothesis import strategies
from twisted.trial import unittest as t_unittest
# TODO
# from twisted.web import (
#     http_headers as t_http_headers,
#     iweb as t_iweb,
# )
# from zope import interface # pyl#int: disable=import-error

from txsocketio.engineio import (
    EIO_TYPE_CODES_BY_NAME,
    EIO_TYPE_NAMES_BY_CODE,
    PayloadDecodeError,
    PayloadEncodeError,
    TransportContext,
    decbinpayloadsgen,
    deceiopacket,
    encbinpayloads,
    encbinpayloadsgen,
    enceiopacket,
)
import test  # noqa: F401; pylint: disable=unused-import

# ---- Constants ---------------------------------------------------------

__all__ = ()

_LOGGER = logging.getLogger(__name__)

# ---- Classes -----------------------------------------------------------

# TODO
# # ========================================================================
# @interface.implementer(t_iweb.IResponse)
# class MockResponse(object):
#
#     # ---- Constructor ---------------------------------------------------
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
#     # ---- Public hooks --------------------------------------------------
#
#     def deliverBody(self, protocol):
#         protocol.dataReceived(self.body)
#         protocol.connectionLost(None)
#
#     def setPreviousResponse(self, response):
#         self.previousResponse = response
#
#     # ---- Public methods ------------------------------------------------
#
#     def setBody(self, body=b''):
#         self._body = b''
#         self.length = t_iweb.UNKNOWN_LENGTH
#         self.headers = [ h for h in self.headers if h[0] != b'Content-Length' ]
#         self.headers.append(( b'Content-Length', str(self.length).encode('ascii') ))

# ========================================================================
class PacketsTestCase(t_unittest.TestCase):

    longMessage = True

    # ---- Public constants ----------------------------------------------

    GOOD_STR_TYPE = EIO_TYPE_CODES_BY_NAME['ping']
    GOOD_STR_DATA = str('{}')
    GOOD_STR_PACKET = GOOD_STR_TYPE.decode('ascii') + GOOD_STR_DATA
    GOOD_BIN_TYPE = EIO_TYPE_CODES_BY_NAME['pong']
    GOOD_BIN_DATA = bytes(b'\x00\x01\x02\x03')
    GOOD_BIN_PACKET = GOOD_BIN_TYPE + GOOD_BIN_DATA
    BAD_TYPE = bytes(b'\x2a')
    BAD_TYPE_STR_PACKET = BAD_TYPE.decode('latin_1') + GOOD_STR_DATA
    BAD_TYPE_BIN_PACKET = BAD_TYPE + GOOD_BIN_DATA
    BAD_TRUNC_PACKET = ''

    # ---- Public hooks --------------------------------------------------

    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()

    @hypothesis.given(packet_type=strategies.sampled_from(EIO_TYPE_NAMES_BY_CODE), packet_data=strategies.binary() | strategies.text())
    def test_enc_dec(self, packet_type, packet_data):
        args = ( packet_type, packet_data )
        self.assertEqual(args, deceiopacket(enceiopacket(*args)))

    def test_packet_dec(self):
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
            self.assertEqual(expected, deceiopacket(packet), msg='packet[{}]: {!r}'.format(i, packet))

    def test_packet_enc(self):
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
            self.assertEqual(expected, enceiopacket(*packet_type_data), msg='packet_type_data[{}]: {!r}'.format(i, packet_type_data))

    def test_packet_dec_bad_len(self):
        with self.assertRaisesRegex(PayloadDecodeError, r'^packet truncated$'):
            deceiopacket(PacketsTestCase.BAD_TRUNC_PACKET)

    def test_packet_dec_bad_type(self):
        packets = [
            PacketsTestCase.BAD_TYPE_STR_PACKET,
            PacketsTestCase.BAD_TYPE_BIN_PACKET,
        ]

        for i, packet in enumerate(packets):
            with self.assertRaisesRegex(PayloadDecodeError, r'^unrecognized packet type "', msg='packet[{}]: {!r}'.format(i, packet)):
                deceiopacket(packet)

        packets = [
            list(range(10)),
            tuple(range(10)),
            42,
        ]

        for i, packet in enumerate(packets):
            with self.assertRaisesRegex(TypeError, r'^packet type must be one of bytes or str, not .+$', msg='packet[{}]: {!r}'.format(i, packet)):
                deceiopacket(packet)

    def test_packet_enc_bad_type(self):
        packets_type_data = [
            ( PacketsTestCase.BAD_TYPE, PacketsTestCase.GOOD_STR_DATA ),
            ( PacketsTestCase.BAD_TYPE, PacketsTestCase.GOOD_BIN_DATA ),
        ]

        for i, packet_type_data in enumerate(packets_type_data):
            with self.assertRaisesRegex(PayloadEncodeError, r'^unrecognized packet type "', msg='packet_type_data[{}]: {!r}'.format(i, packet_type_data)):
                enceiopacket(*packet_type_data)

        packets_type_data = [
            ( EIO_TYPE_CODES_BY_NAME['message'], list(range(10)) ),
            ( EIO_TYPE_CODES_BY_NAME['message'], tuple(range(10)) ),
            ( EIO_TYPE_CODES_BY_NAME['message'], 42 ),
        ]

        for i, packet_type_data in enumerate(packets_type_data):
            with self.assertRaisesRegex(TypeError, r'^packet_data type must be one of bytes or str, not .+$', msg='packet[{}]: {!r}'.format(i, packet_type_data)):
                enceiopacket(*packet_type_data)

    def test_packet_dec_enc(self):
        packets = [
            PacketsTestCase.GOOD_STR_PACKET,
            PacketsTestCase.GOOD_BIN_PACKET,
        ]

        for i, packet in enumerate(packets):
            self.assertEqual(packet, enceiopacket(*deceiopacket(packet)), msg='packet[{}]: {!r}'.format(i, packet))

    def test_packet_enc_dec(self):
        packets_type_data = [
            ( PacketsTestCase.GOOD_STR_TYPE, PacketsTestCase.GOOD_STR_DATA ),
            ( PacketsTestCase.GOOD_BIN_TYPE, PacketsTestCase.GOOD_BIN_DATA ),
        ]

        for i, packet_type_data in enumerate(packets_type_data):
            self.assertEqual(packet_type_data, deceiopacket(enceiopacket(*packet_type_data)), msg='packet_type_data[{}]: {!r}'.format(i, packet_type_data))

# ========================================================================
class PayloadsTestCase(t_unittest.TestCase):

    longMessage = True

    # ---- Public constants ----------------------------------------------

    GOOD_STR_PACKET = str('4{}')
    GOOD_STR_PACKET_PAYLOAD = bytes(b'\x00\x03\xff' + GOOD_STR_PACKET.encode('utf_8'))
    GOOD_BIN_PACKET = bytes(b'4\x00\x01\x02\x03')
    GOOD_BIN_PACKET_PAYLOAD = bytes(b'\x01\x05\xff' + GOOD_BIN_PACKET)
    BAD_TYPE_PAYLOAD = bytes(b'\x02' + GOOD_BIN_PACKET_PAYLOAD[1:])
    BAD_LEN_OCTET_PAYLOAD = bytes(b'\x00\x0a\xff6')
    BAD_LEN_TRUNC_PAYLOAD = bytes(b'\x00\x01\x02')
    BAD_LEN_VALUE_PAYLOAD = bytes(b'\x00' + b'\x09' * 311 + b'\xff6')
    BAD_TRUNC_PAYLOAD = bytes(b'\x00\x03\xff4')

    # ---- Public hooks --------------------------------------------------

    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()

    def test_payload_dec(self):
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

    def test_payload_enc(self):
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

    def test_payload_dec_bad_len(self):
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

        with self.assertRaisesRegex(PayloadDecodeError, r'^9{311} exceeds max bytes for length field at 1$'):
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

        with self.assertRaisesRegex(PayloadDecodeError, r'^9{311} exceeds max bytes for length field at 15$'):
            for i in decbinpayloadsgen(raw):
                actual.append(i)

        self.assertEqual(expected, actual)

    def test_payload_dec_bad_payload(self):
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

    def test_payload_dec_bad_type(self):
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

    def test_payload_enc_bad_type(self):
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

    def test_payload_dec_enc(self):
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

    def test_payload_enc_dec(self):
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

    def test_regression_long_payload(self):
        # This is raw data from Insight API (on or about 2015-11-05) that
        # we choked on because we (erroneously) didn't allow for payloads
        # longer than 310 characters
        raw = b'\x00\x02\x01\x05\xff42["tx",{"txid":"e9772f1171fb16c3461a545b320cf9882a3d60e8fe58af6058f14230cda5d493","valueOut":74.6768726,"vout":[{"1JzddE9RdGaxWbJgfBM15J3Xj6hzKX3o3f":1200000000},{"1GJ9AnmcwwCGSJyksX8thqRvnuAfS1ZB6C":6267687260}]}]\x00\x01\x01\x02\x05\xff42["tx",{"txid":"5c3264d64107f5398745bdbd2c6a2c40ee3ea022eb4bbacc79271ce0fc91e8ea","valueOut":31.47905388,"vout":[{"1BKLefgfSQjRWRHSkirEKPz9y5Z5VwUKYT":25257121},{"1BGv1vWNjvekSFD6SoyNQJvCDGbhCfyknp":24046431},{"1GMcQBw7NHL17Xw8b1ueDzP1fuCESCgDfy":70226431},{"1DZxmrAMnRssRNjqNTp5XsCACwQXte3fdz":25247121},{"1QA7FTnqvHabS979u19UvWzgLRxThH3vMP":42800000},{"176yohfzuRWw9PWXaKwxZuGZana5EJj4Wi":535262879},{"15iQFJNjprPNHhdFwHpg3NxYBQH4rqAis8":1200690},{"1L7kTokjjCsLhmTwBeTUaw3zZX5cmAZgey":688940},{"1HKugLe1iFnHFUdTNGtm1K8vCMjjhgfvKB":324710000},{"1F8LtvqAhMEFkcfYHvqLVDMPFQv8ncZoZ6":118062879},{"1CjLvNRipzdq6hUWJ14iE72TfXFL6hBgUu":254362879},{"137Em62DLiYoWtvYbZoe396XaQ1iwYJLnd":433500000},{"17hD8cgNetd6G4L4nLUmJeD7PxgjfSMhdk":460000000},{"14uP5jHc26Kmt9xKs8CJwXSWDFuZAkz47S":144562879},{"1GxscjUdN9Ntxo68zGXYJCq5p2dXLb1Q68":10000},{"13rgFRQqTuxTUBCsgBGonXKQXSSf6ThDxW":323700000},{"1PTDGyzVGkjgL3VTKXZjDSGkSyd5SquuvZ":24056431},{"17jJiNJiRwaZmwtsAU8BdCua3RNwK8c8DZ":71427121},{"1MPv7Px7BRzVXJQyYB1Fn5nFVMKt5TnXVz":511750},{"13LErEoUYp9HxGX9jYoZedPShXgTasUy5J":253352879},{"1KYLZwc939EJUz1y45YqbtbSqarjhtqJbi":14918957}]}]'

        expected = [
            (
                b'4',
                '2["tx",{"txid":"e9772f1171fb16c3461a545b320cf9882a3d60e8fe58af6058f14230cda5d493","valueOut":74.6768726,"vout":[{"1JzddE9RdGaxWbJgfBM15J3Xj6hzKX3o3f":1200000000},{"1GJ9AnmcwwCGSJyksX8thqRvnuAfS1ZB6C":6267687260}]}]',
            ),
            (
                b'4',
                '2["tx",{"txid":"5c3264d64107f5398745bdbd2c6a2c40ee3ea022eb4bbacc79271ce0fc91e8ea","valueOut":31.47905388,"vout":[{"1BKLefgfSQjRWRHSkirEKPz9y5Z5VwUKYT":25257121},{"1BGv1vWNjvekSFD6SoyNQJvCDGbhCfyknp":24046431},{"1GMcQBw7NHL17Xw8b1ueDzP1fuCESCgDfy":70226431},{"1DZxmrAMnRssRNjqNTp5XsCACwQXte3fdz":25247121},{"1QA7FTnqvHabS979u19UvWzgLRxThH3vMP":42800000},{"176yohfzuRWw9PWXaKwxZuGZana5EJj4Wi":535262879},{"15iQFJNjprPNHhdFwHpg3NxYBQH4rqAis8":1200690},{"1L7kTokjjCsLhmTwBeTUaw3zZX5cmAZgey":688940},{"1HKugLe1iFnHFUdTNGtm1K8vCMjjhgfvKB":324710000},{"1F8LtvqAhMEFkcfYHvqLVDMPFQv8ncZoZ6":118062879},{"1CjLvNRipzdq6hUWJ14iE72TfXFL6hBgUu":254362879},{"137Em62DLiYoWtvYbZoe396XaQ1iwYJLnd":433500000},{"17hD8cgNetd6G4L4nLUmJeD7PxgjfSMhdk":460000000},{"14uP5jHc26Kmt9xKs8CJwXSWDFuZAkz47S":144562879},{"1GxscjUdN9Ntxo68zGXYJCq5p2dXLb1Q68":10000},{"13rgFRQqTuxTUBCsgBGonXKQXSSf6ThDxW":323700000},{"1PTDGyzVGkjgL3VTKXZjDSGkSyd5SquuvZ":24056431},{"17jJiNJiRwaZmwtsAU8BdCua3RNwK8c8DZ":71427121},{"1MPv7Px7BRzVXJQyYB1Fn5nFVMKt5TnXVz":511750},{"13LErEoUYp9HxGX9jYoZedPShXgTasUy5J":253352879},{"1KYLZwc939EJUz1y45YqbtbSqarjhtqJbi":14918957}]}]',
            ),
        ]

        actual = [ deceiopacket(pckt) for pckt in decbinpayloadsgen(raw) ]
        self.assertEqual(expected, actual)

# ========================================================================
class TransportContextTestCase(t_unittest.TestCase):

    longMessage = True

    # ---- Public hooks --------------------------------------------------

    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()

    def test_transport_context(self):
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

# ---- Initialization ----------------------------------------------------

if __name__ == '__main__':
    from unittest import main
    main()
