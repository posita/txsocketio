# Adapted from
# <https://github.com/habnabit/txsocksx/blob/31e7be5418e7bf71df26e8f5a9b87dbb87f2c41f/txsocksx/tls.py>
# until <https://twistedmatrix.com/trac/ticket/5642> is fixed

# Copyright (c) 2010-2015, Aaron Gallagher <_@habnab.it>
#
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH
# REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND
# FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT,
# INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM
# LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR
# OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
# PERFORMANCE OF THIS SOFTWARE.


"""TLS convenience wrappers for endpoints.

"""


from __future__ import print_function, unicode_literals

from twisted.protocols import tls
from twisted.internet import interfaces
from zope.interface import implementer


@implementer(interfaces.IStreamClientEndpoint)
class TLSWrapClientEndpoint(object):
    """An endpoint which automatically starts TLS.

    :param contextFactory: A `ContextFactory`__ instance.
    :param wrappedEndpoint: The endpoint to wrap.

    __ http://twistedmatrix.com/documents/current/api/twisted.internet.protocol.ClientFactory.html

    """

    _wrapper = tls.TLSMemoryBIOFactory

    def __init__(self, contextFactory, wrappedEndpoint):
        self.contextFactory = contextFactory
        self.wrappedEndpoint = wrappedEndpoint

    def connect(self, fac):
        """Connect to the wrapped endpoint, then start TLS.

        The TLS negotiation is done by way of wrapping the provided factory
        with `TLSMemoryBIOFactory`__ during connection.

        :returns: A ``Deferred`` which fires with the same ``Protocol`` as
            ``wrappedEndpoint.connect(fac)`` fires with. If that ``Deferred``
            errbacks, so will the returned deferred.

        __ http://twistedmatrix.com/documents/current/api/twisted.protocols.tls.html

        """
        fac = self._wrapper(self.contextFactory, True, fac)
        return self.wrappedEndpoint.connect(fac).addCallback(self._unwrapProtocol)

    def _unwrapProtocol(self, proto):
        return proto.wrappedProtocol
