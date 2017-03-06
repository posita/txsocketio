//-*- encoding: utf-8; grammar-ext: js; mode: js -*-

/*======================================================================*\
  Copyright and other protections apply. Please see the accompanying
  ``LICENSE`` and ``CREDITS`` files for rights and restrictions governing
  use of this software. All rights not expressly waived or licensed are
  reserved. If those files are missing or appear to be modified from their
  originals, then please contact the author before viewing or using this
  software in any capacity.
\*======================================================================*/

// ---- Imports ----------------------------------------------------------

var http = require('http');
var path = require('path');

var engine_io = require('engine.io');
var socket_io = require('socket.io');

// ---- Initialization ---------------------------------------------------

require('console-stamp')(console, { pattern: 'HH:MM:ss.l' });
var app = http.createServer();

process.on('SIGINT', function () {
    app.close();
    process.exit();
});

var eio_client_close = engine_io(app, { path: '/client_close/engine.io' });

eio_client_close.on('connection', function(socket) {
    console.log('eio_client_close opened');

    socket.on('close', function() {
        console.log('eio_client_close closed');
    });

    socket.send('Hello!');
});

var eio_hello = engine_io(app, { path: '/hello/engine.io' });

eio_hello.on('connection', function(socket) {
    console.log('eio_hello opened');

    socket.on('close', function() {
        console.log('eio_hello closed');
    });

    socket.send('Hello!');
    socket.close();
});

var eio_hello_delay = engine_io(app, { path: '/hello_delay/engine.io' });

eio_hello_delay.on('connection', function(socket) {
    console.log('eio_hello_delay opened');

    socket.on('close', function() {
        console.log('eio_hello_delay closed');
    });

    setTimeout(function () {
        socket.send('Hello!');

        setTimeout(function () {
            socket.close();
        }, 1000);
    }, 1000);
});

var sio_echo_ack = socket_io(app, { path: '/echo_ack/socket.io' });

sio_echo_ack.on('connection', function(socket) {
    console.log('sio_echo_ack connected');

    socket.on('close', function() {
        console.log('sio_echo_ack closed');
    });

    socket.on('disconnect', function() {
        console.log('sio_echo_ack disconnected');
    });

    socket.on('msg', function(msg, callback) {
        callback = callback || function () {};
        console.log('sio_echo_ack got message: ' + msg);
        sio_echo_ack.sockets.emit('msg', msg);
        callback();
    });
});

var eio = engine_io(app);

var sock_path = path.join(__dirname, 'http.sock');
app.listen(sock_path);
