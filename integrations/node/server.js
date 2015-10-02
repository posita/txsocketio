//-*- encoding: utf-8; grammar-ext: js; mode: js -*-

/*======================================================================*\
  Copyright (c) 2015 Matt Bogosian <mtb19@columbia.edu>.

  Please see the accompanying LICENSE (or LICENSE.txt) file for rights and
  restrictions governing use of this software. All rights not expressly
  waived or licensed are reserved. If such a file did not accompany this
  software, then please contact the author before viewing or using this
  software in any capacity.
\*======================================================================*/

//---- Imports -----------------------------------------------------------

var http = require('http');
var path = require('path');

var engine_io = require('engine.io');
var socket_io = require('socket.io');

//---- Initialization ----------------------------------------------------

require('console-stamp')(console, { pattern: 'HH:MM:ss.l' });
var app = http.createServer();

process.on('SIGINT', function () {
    app.close();
    process.exit();
});

var eio_clientclose = engine_io(app, { path: '/clientclose/engine.io' });

eio_clientclose.on('connection', function(socket) {
    console.log('clientclose connected');
    socket.send('Hello!');
});

var eio_hello = engine_io(app, { path: '/hello/engine.io' });

eio_hello.on('connection', function(socket) {
    console.log('hello connected');
    socket.send('Hello!');
    socket.close();
    console.log('hello disconnected');
});

var eio_hellodelay = engine_io(app, { path: '/hellodelay/engine.io' });

eio_hellodelay.on('connection', function(socket) {
    console.log('hellodelay connected');

    setTimeout(function () {
        socket.send('Hello!');

        setTimeout(function () {
            socket.close();
            console.log('hellodelay disconnected');
        }, 1000);
    }, 1000);
});

var eio = engine_io(app);
var sio = socket_io(app);

// eio.on('connection', function(socket) {
//     console.log(socket.id + ' connected ' + (new Date()).toISOString());
//     socket.send('nice to see you!');
//     socket.send('would you care to dance?');
//     var counter = 5;
//
//     function timecheck() {
//         setTimeout(function () {
//             if (! socket.disconnected) {
//                 --counter;
//                 socket.send('at the tone, the time will be ' + (new Date()).toISOString());
//                 socket.send('ting!');
//                 socket.send('you have ' + counter + ' notices remaining' + ((counter > 0) ? '...' : ''));
//
//                 if (counter > 0) {
//                     timecheck();
//                 // } else {
//                 //     socket.close();
//                 }
//             }
//         }, 1000);
//     }
//
//     function trivia() {
//         setTimeout(function () {
//             if (! socket.disconnected) {
//                 socket.send('do you know where your children are?');
//                 trivia();
//             }
//         }, 23000);
//     }
//
//     socket.on('echo', function (data) {
//         console.log(data);
//         socket.send(data);
//     });
//
//     socket.on('close', function () {
//         console.log(socket.id + ' closed ' + (new Date()).toISOString());
//     });
//
//     timecheck();
//     trivia();
// });
//
// var sio = socket_io(app);
//
// sio.on('connection', function(socket) {
//     console.log(socket.id + ' connected ' + (new Date()).toISOString());
//     socket.emit('greeting', 'nice to see you!');
//     socket.emit('question', 'would you care to dance?');
//     var counter = 5;
//
//     function timecheck() {
//         setTimeout(function () {
//             if (! socket.disconnected) {
//                 --counter;
//                 socket.emit('time', { 'at the tone, the time will be': (new Date()).toISOString() });
//                 socket.emit('tone', 'ting!');
//                 socket.emit('left', 'you have ' + counter + ' notices remaining' + ((counter > 0) ? '...' : ''));
//
//                 if (counter > 0) {
//                     timecheck();
//                 // } else {
//                 //     socket.disconnect();
//                 }
//             }
//         }, 1000);
//     }
//
//     function trivia() {
//         setTimeout(function () {
//             if (! socket.disconnected) {
//                 socket.emit('trivia', { 'do you know': 'where your children are?' });
//                 trivia();
//             }
//         }, 23000);
//     }
//
//     socket.on('echo', function (data) {
//         console.log(data);
//         socket.emit('echo', data);
//     });
//
//     socket.on('disconnect', function () {
//         console.log(socket.id + ' disconnected ' + (new Date()).toISOString());
//     });
//
//     timecheck();
//     trivia();
// });

var sock_path = path.join(__dirname, 'http.sock');
app.listen(sock_path);
