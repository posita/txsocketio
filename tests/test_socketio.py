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
import string
import hypothesis
from hypothesis import strategies
from twisted.trial import unittest as t_unittest

from txsocketio.engineio import (
    PayloadDecodeError,
    PayloadEncodeError,
)
from txsocketio.socketio import (
    SIO_TYPE_BIN_ACK,
    SIO_TYPE_BIN_EVENT,
    SIO_TYPE_EVENT,
    SIO_TYPE_NAMES_BY_CODE,
    decsiopacket,
    encsiopacket,
)
import tests # pylint: disable=unused-import
from tests import JSON

#---- Constants ----------------------------------------------------------

__all__ = ()

_LOGGER = logging.getLogger(__name__)

#---- Classes ------------------------------------------------------------

#=========================================================================
class PacketsTestCase(t_unittest.TestCase):

    longMessage = True

    #---- Public constants -----------------------------------------------

    BAD_TRUNC_PACKET = ''
    BAD_TYPE = bytes(b'\x2a')
    BAD_TYPE_STR_PACKET = BAD_TYPE.decode('latin_1')
    BAD_PACKET_STR_BIN_ACK = SIO_TYPE_BIN_ACK.decode('utf_8')
    BAD_PACKET_STR_BIN_EVENT = SIO_TYPE_BIN_EVENT.decode('utf_8')

    #---- Public hooks ---------------------------------------------------

    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()

    @hypothesis.given(packet_type=strategies.sampled_from(set(SIO_TYPE_NAMES_BY_CODE).difference(( SIO_TYPE_BIN_EVENT, SIO_TYPE_BIN_ACK ))), packet_obj=JSON | strategies.just(''), packet_path=strategies.text(alphabet=string.digits + string.letters + '/'), packet_id=strategies.integers(min_value=0) | strategies.none())
    @hypothesis.example(packet_type=SIO_TYPE_EVENT, packet_obj='', packet_path='/', packet_id=None)
    @hypothesis.example(packet_type=SIO_TYPE_EVENT, packet_obj='', packet_path='/', packet_id=0)
    def test_enc_dec(self, packet_type, packet_obj, packet_path, packet_id):
        packet_path = '/' + packet_path
        args = ( packet_type, packet_obj, packet_path, packet_id )
        self.assertEqual(args, decsiopacket(encsiopacket(*args)))

    def test_packet_dec(self):
        packets = (
            encsiopacket(SIO_TYPE_EVENT, None, None, None),
            encsiopacket(SIO_TYPE_EVENT, '',   None, None),
            encsiopacket(SIO_TYPE_EVENT, None, '',   None),
            encsiopacket(SIO_TYPE_EVENT, '',   '',   None),
            encsiopacket(SIO_TYPE_EVENT, None, '/',  None),
            encsiopacket(SIO_TYPE_EVENT, '',   '/',  None),
            SIO_TYPE_EVENT.decode('utf_8'),
        )

        expected = ( SIO_TYPE_EVENT, '', '/', None )

        for i, packet in enumerate(packets):
            actual = decsiopacket(packet)
            self.assertEqual(expected, actual, msg='packet[{}]: {!r}'.format(i, packet))

    def test_packet_dec_bad_len(self):
        with self.assertRaisesRegex(PayloadDecodeError, r'^packet truncated$'):
            decsiopacket(PacketsTestCase.BAD_TRUNC_PACKET)

    def test_packet_dec_bad_type(self):
        packets = [
            SIO_TYPE_BIN_ACK,
            SIO_TYPE_BIN_EVENT,
        ]

        for i, packet in enumerate(packets):
            with self.assertRaisesRegex(NotImplementedError, r'^binary Socket\.IO packets are currently unsupported$', msg='packet[{}]: {!r}'.format(i, packet)):
                decsiopacket(packet)

        packets = [
            SIO_TYPE_EVENT,
        ]

        for i, packet in enumerate(packets):
            with self.assertRaisesRegex(PayloadDecodeError, r'^packet type is ".*", but payload is binary$', msg='packet[{}]: {!r}'.format(i, packet)):
                decsiopacket(packet)

        packets = [
            PacketsTestCase.BAD_TYPE_STR_PACKET,
        ]

        for i, packet in enumerate(packets):
            with self.assertRaisesRegex(PayloadDecodeError, r'^unrecognized packet type ".*"$', msg='packet[{}]: {!r}'.format(i, packet)):
                decsiopacket(packet)

        packets = [
            PacketsTestCase.BAD_PACKET_STR_BIN_ACK,
            PacketsTestCase.BAD_PACKET_STR_BIN_EVENT,
        ]

        for i, packet in enumerate(packets):
            with self.assertRaisesRegex(PayloadDecodeError, r'^packet type is ".*", but payload is not binary$', msg='packet[{}]: {!r}'.format(i, packet)):
                decsiopacket(packet)

        packets = [
            None,
            42,
            (),
            [],
            {},
        ]

        for i, packet in enumerate(packets):
            with self.assertRaisesRegex(TypeError, r'^packet type must be one of bytes or str, not .*', msg='packet[{}]: {!r}'.format(i, packet)):
                decsiopacket(packet)

    def test_packet_enc_bad_type(self):
        packets_type_data = [
            ( PacketsTestCase.BAD_TYPE, {} ),
        ]

        for i, packet_type_data in enumerate(packets_type_data):
            with self.assertRaisesRegex(PayloadEncodeError, r'^unrecognized packet type "', msg='packet_type_data[{}]: {!r}'.format(i, packet_type_data)):
                encsiopacket(*packet_type_data)

#---- Initialization -----------------------------------------------------

if __name__ == '__main__':
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    from unittest import main
    main()
