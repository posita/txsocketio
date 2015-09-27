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
from txsocketio.engineio import (
    PayloadDecodeError,
    PayloadEncodeError,
    decbinpayloadsgen,
    encbinpayloadsgen,
)

#---- Constants ----------------------------------------------------------

__all__ = ()

#---- Classes ------------------------------------------------------------

#=========================================================================
class PayloadsTestCase(TestCase):

    #---- Public constants -----------------------------------------------

    GOOD_STR_PACKET = str(u'4{}')
    GOOD_BIN_PAYLOAD_STR_PACKET = bytes(b'\x00\x03\xff' + GOOD_STR_PACKET.encode('utf_8'))
    GOOD_BIN_PACKET = bytes(b'4\x00\x01\x02\x03')
    GOOD_BIN_PAYLOAD_BIN_PACKET = bytes(b'\x01\x05\xff' + GOOD_BIN_PACKET)
    BAD_BIN_PAYLOAD_TYPE = bytes(b'\x02' + GOOD_BIN_PAYLOAD_BIN_PACKET[1:])
    BAD_BIN_PAYLOAD_LEN_OCTET = bytes(b'\x00\x0a\xff6')
    BAD_BIN_PAYLOAD_LEN_TRUNC = bytes(b'\x00\x01\x02')
    BAD_BIN_PAYLOAD_LEN_VALUE = bytes(b'\x00\x03\x01\x01\xff6')
    BAD_BIN_PAYLOAD_TRUNC = bytes(b'\x00\x03\xff4')

    #---- Public hook methods --------------------------------------------

    #=====================================================================
    def setUp(self):
        super().setUp() # pylint: disable=missing-super-argument

    #=====================================================================
    def tearDown(self):
        super().tearDown() # pylint: disable=missing-super-argument

    #=====================================================================
    def test_payloaddec(self):
        raw = PayloadsTestCase.GOOD_BIN_PAYLOAD_STR_PACKET
        expected = [
            PayloadsTestCase.GOOD_STR_PACKET,
        ]
        actual = list(decbinpayloadsgen(raw))
        self.assertEqual(expected, actual)

        raw = PayloadsTestCase.GOOD_BIN_PAYLOAD_BIN_PACKET
        expected = [
            PayloadsTestCase.GOOD_BIN_PACKET,
        ]
        actual = list(decbinpayloadsgen(raw))
        self.assertEqual(expected, actual)

        raw = PayloadsTestCase.GOOD_BIN_PAYLOAD_BIN_PACKET \
            + PayloadsTestCase.GOOD_BIN_PAYLOAD_STR_PACKET \
            + PayloadsTestCase.GOOD_BIN_PAYLOAD_BIN_PACKET \
            + PayloadsTestCase.GOOD_BIN_PAYLOAD_STR_PACKET
        expected = [
            PayloadsTestCase.GOOD_BIN_PACKET,
            PayloadsTestCase.GOOD_STR_PACKET,
            PayloadsTestCase.GOOD_BIN_PACKET,
            PayloadsTestCase.GOOD_STR_PACKET,
        ]
        actual = list(decbinpayloadsgen(raw))
        self.assertEqual(expected, actual)

    #=====================================================================
    def test_payloaddecbadlen(self):
        raw = PayloadsTestCase.BAD_BIN_PAYLOAD_LEN_OCTET
        expected = []
        actual = []

        with self.assertRaisesRegex(PayloadDecodeError, r'^unrecognized length byte 10 at 1$'):
            for i in decbinpayloadsgen(raw):
                actual.append(i)

        self.assertEqual(expected, actual)

        raw = PayloadsTestCase.GOOD_BIN_PAYLOAD_BIN_PACKET \
            + PayloadsTestCase.GOOD_BIN_PAYLOAD_STR_PACKET \
            + PayloadsTestCase.BAD_BIN_PAYLOAD_LEN_OCTET
        expected = [
            PayloadsTestCase.GOOD_BIN_PACKET,
            PayloadsTestCase.GOOD_STR_PACKET,
        ]
        actual = []

        with self.assertRaisesRegex(PayloadDecodeError, r'^unrecognized length byte 10 at 15$'):
            for i in decbinpayloadsgen(raw):
                actual.append(i)

        self.assertEqual(expected, actual)

        raw = PayloadsTestCase.BAD_BIN_PAYLOAD_LEN_TRUNC
        expected = []
        actual = []

        with self.assertRaisesRegex(PayloadDecodeError, r'^payload length field truncated at 3$'):
            for i in decbinpayloadsgen(raw):
                actual.append(i)

        self.assertEqual(expected, actual)

        raw = PayloadsTestCase.GOOD_BIN_PAYLOAD_STR_PACKET \
            + PayloadsTestCase.GOOD_BIN_PAYLOAD_BIN_PACKET \
            + PayloadsTestCase.BAD_BIN_PAYLOAD_LEN_TRUNC
        expected = [
            PayloadsTestCase.GOOD_STR_PACKET,
            PayloadsTestCase.GOOD_BIN_PACKET,
        ]
        actual = []

        with self.assertRaisesRegex(PayloadDecodeError, r'^payload length field truncated at 17$'):
            for i in decbinpayloadsgen(raw):
                actual.append(i)

        self.assertEqual(expected, actual)

        raw = PayloadsTestCase.BAD_BIN_PAYLOAD_LEN_VALUE
        expected = []
        actual = []

        with self.assertRaisesRegex(PayloadDecodeError, r'^311 exceeds max bytes for length field at 5$'):
            for i in decbinpayloadsgen(raw):
                actual.append(i)

        self.assertEqual(expected, actual)

        raw = PayloadsTestCase.GOOD_BIN_PAYLOAD_BIN_PACKET \
            + PayloadsTestCase.GOOD_BIN_PAYLOAD_STR_PACKET \
            + PayloadsTestCase.BAD_BIN_PAYLOAD_LEN_VALUE
        expected = [
            PayloadsTestCase.GOOD_BIN_PACKET,
            PayloadsTestCase.GOOD_STR_PACKET,
        ]
        actual = []

        with self.assertRaisesRegex(PayloadDecodeError, r'^311 exceeds max bytes for length field at 19$'):
            for i in decbinpayloadsgen(raw):
                actual.append(i)

        self.assertEqual(expected, actual)

    #=====================================================================
    def test_payloaddecbadpayload(self):
        raw = PayloadsTestCase.BAD_BIN_PAYLOAD_TRUNC
        expected = []
        actual = []

        with self.assertRaisesRegex(PayloadDecodeError, r'^payload data truncated \(received only 1 of 3 expected octets\) at 3$'):
            for i in decbinpayloadsgen(raw):
                actual.append(i)

        self.assertEqual(expected, actual)

        raw = PayloadsTestCase.GOOD_BIN_PAYLOAD_STR_PACKET \
            + PayloadsTestCase.GOOD_BIN_PAYLOAD_BIN_PACKET \
            + PayloadsTestCase.BAD_BIN_PAYLOAD_TRUNC
        expected = [
            PayloadsTestCase.GOOD_STR_PACKET,
            PayloadsTestCase.GOOD_BIN_PACKET,
        ]
        actual = []

        with self.assertRaisesRegex(PayloadDecodeError, r'^payload data truncated \(received only 1 of 3 expected octets\) at 17$'):
            for i in decbinpayloadsgen(raw):
                actual.append(i)

        self.assertEqual(expected, actual)

    #=====================================================================
    def test_payloaddecbadtype(self):
        raw = PayloadsTestCase.BAD_BIN_PAYLOAD_TYPE
        expected = []
        actual = []

        with self.assertRaisesRegex(PayloadDecodeError, r'^unrecognized payload type 2 at 0$'):
            for i in decbinpayloadsgen(raw):
                actual.append(i)

        self.assertEqual(expected, actual)

        raw = PayloadsTestCase.GOOD_BIN_PAYLOAD_STR_PACKET \
            + PayloadsTestCase.GOOD_BIN_PAYLOAD_BIN_PACKET \
            + PayloadsTestCase.BAD_BIN_PAYLOAD_TYPE
        expected = [
            PayloadsTestCase.GOOD_STR_PACKET,
            PayloadsTestCase.GOOD_BIN_PACKET,
        ]
        actual = []

        with self.assertRaisesRegex(PayloadDecodeError, r'^unrecognized payload type 2 at 14$'):
            for i in decbinpayloadsgen(raw):
                actual.append(i)

        self.assertEqual(expected, actual)

    #=====================================================================
    def test_payloadenc(self):
        packets = (
            PayloadsTestCase.GOOD_STR_PACKET,
        )
        expected = [
            PayloadsTestCase.GOOD_BIN_PAYLOAD_STR_PACKET,
        ]
        actual = list(encbinpayloadsgen(packets))
        self.assertEqual(expected, actual)

        packets = (
            PayloadsTestCase.GOOD_BIN_PACKET,
        )
        expected = [
            PayloadsTestCase.GOOD_BIN_PAYLOAD_BIN_PACKET,
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
            PayloadsTestCase.GOOD_BIN_PAYLOAD_STR_PACKET,
            PayloadsTestCase.GOOD_BIN_PAYLOAD_BIN_PACKET,
            PayloadsTestCase.GOOD_BIN_PAYLOAD_STR_PACKET,
            PayloadsTestCase.GOOD_BIN_PAYLOAD_BIN_PACKET,
        ]
        actual = list(encbinpayloadsgen(packets))
        self.assertEqual(expected, actual)

    #=====================================================================
    def test_payloadencbad(self):
        packets = (
            PayloadsTestCase.GOOD_STR_PACKET,
            PayloadsTestCase.GOOD_BIN_PACKET,
            42,
            PayloadsTestCase.GOOD_STR_PACKET,
            PayloadsTestCase.GOOD_BIN_PACKET,
        )
        expected = [
            PayloadsTestCase.GOOD_BIN_PAYLOAD_STR_PACKET,
            PayloadsTestCase.GOOD_BIN_PAYLOAD_BIN_PACKET,
        ]
        actual = []

        with self.assertRaisesRegex(PayloadEncodeError, r'^unable to determine encoding for type ".*" of packet 2$'):
            for i in encbinpayloadsgen(packets):
                actual.append(i)

        self.assertEqual(expected, actual)

    #=====================================================================
    def test_payloaddecenc(self):
        raw = PayloadsTestCase.GOOD_BIN_PAYLOAD_BIN_PACKET \
            + PayloadsTestCase.GOOD_BIN_PAYLOAD_STR_PACKET \
            + PayloadsTestCase.GOOD_BIN_PAYLOAD_BIN_PACKET \
            + PayloadsTestCase.GOOD_BIN_PAYLOAD_STR_PACKET
        packets = list(decbinpayloadsgen(raw))
        self.assertEqual(raw, bytes(b''.join(encbinpayloadsgen(packets))))

    #=====================================================================
    def test_payloadencdec(self):
        packets = [
            PayloadsTestCase.GOOD_STR_PACKET,
            PayloadsTestCase.GOOD_BIN_PACKET,
            PayloadsTestCase.GOOD_STR_PACKET,
            PayloadsTestCase.GOOD_BIN_PACKET,
        ]
        raw = bytes(b''.join(encbinpayloadsgen(packets)))
        self.assertEqual(packets, list(decbinpayloadsgen(raw)))

#---- Initialization -----------------------------------------------------

if __name__ == '__main__':
    from unittest import main
    main()
