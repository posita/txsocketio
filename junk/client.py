###############################################################################
#
# The MIT License (MIT)
#
# Copyright (c) Tavendo GmbH
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
###############################################################################

from __future__ import (
    absolute_import, division, print_function, unicode_literals,
)

try:
    from urllib.parse import quote as urllib_quote # pylint: disable=no-name-in-module
except ImportError:
    from urllib import quote as urllib_quote # pylint: disable=no-name-in-module


if __name__ == '__main__':
    from autobahn.twisted.choosereactor import install_reactor
    install_reactor()

from autobahn.twisted.websocket import WebSocketClientProtocol, WebSocketClientFactory
from twisted.internet.defer import Deferred
from twisted.internet.protocol import ReconnectingClientFactory
from twisted.python.log import err as log_err

from txsocketio.endpoint import BaseUrl
from txsocketio.engineio import EngineIo

class MyClientProtocol(WebSocketClientProtocol):

    def onConnect(self, response):
        print("Server connected: {0}".format(response.peer))

    def onOpen(self):
        print("WebSocket connection open.")

        def hello():
            self.sendMessage(u'42["subscribe", "inv"]'.encode('utf8'))
            # self.factory.reactor.callLater(1, hello)

        # start sending messages every second ..
        hello()

    def onMessage(self, payload, isBinary):
        if isBinary:
            print("Binary message received: {0} bytes".format(len(payload)))
        else:
            print("Text message received: {0}".format(payload.decode('utf8')))

    def onClose(self, wasClean, code, reason):
        print("WebSocket connection closed: {0}".format(reason))

class MyClientFactory(WebSocketClientFactory, ReconnectingClientFactory):

    protocol = MyClientProtocol

    def clientConnectionFailed(self, connector, reason):
        print("Client connection failed .. retrying ..")
        self.retry(connector)

    def clientConnectionLost(self, connector, reason):
        print("Client connection lost .. retrying ..")
        self.retry(connector)

def main(reactor, argv): # pylint: disable=redefined-outer-name,unused-argument
    url = BaseUrl.fromString(b'unix://<replaceme>/eiohello/engine.io/')
    path = str('./integrations/node/http.sock')
    url.netloc = urllib_quote(path.encode('utf_8'), safe=b'').encode('ascii')
    urlbytes = url.unsplit()
    # urlbytes = b'https://bc.veritaseum.com/socket.io/'
    engineio = EngineIo(urlbytes, reactor=reactor)
    d = Deferred()

    def _done(event):
        print('done() called with {!r}'.format(event))

        d.callback(None)

    engineio.register('close', _done)
    engineio.start()
    d.addErrback(log_err)

    return d

if __name__ == '__main__':
    from logging import DEBUG, basicConfig, getLogger
    from sys import argv
    from twisted.internet.task import react
    from twisted.python.log import PythonLoggingObserver
    PythonLoggingObserver().start()
    # from sys import stderr
    # from twisted.python.log import startLogging
    # startLogging(stderr)
    basicConfig(format='%(levelname)-8s: %(message)s')
    getLogger().setLevel(DEBUG)
    react(main, argv[1:])
