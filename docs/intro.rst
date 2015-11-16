.. -*- encoding: utf-8; mode: rst -*-
    >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
    >>>>>>>>>>>>>>>> IMPORTANT: READ THIS BEFORE EDITING! <<<<<<<<<<<<<<<<
    >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
    Please keep each sentence on its own unwrapped line.
    It looks like crap in a text editor, but it has no effect on rendering, and it allows much more useful diffs.
    Thank you!

.. toctree::
    :maxdepth: 3
    :hidden:

Copyright |(c)| 2015 `Matt Bogosian`_ (|@posita|_).

.. |(c)| unicode:: u+a9
.. _`Matt Bogosian`: mailto:mtb19@columbia.edu?Subject=txsocketio
.. |@posita| replace:: **@posita**
.. _`@posita`: https://github.com/posita

Please see the accompanying |LICENSE|_ (or |LICENSE.txt|_) file for rights and restrictions governing use of this software.
All rights not expressly waived or licensed are reserved.
If such a file did not accompany this software, then please contact the author before viewing or using this software in any capacity.

.. |LICENSE| replace:: ``LICENSE``
.. _`LICENSE`: _sources/LICENSE.txt
.. |LICENSE.txt| replace:: ``LICENSE.txt``
.. _`LICENSE.txt`: _sources/LICENSE.txt

Introduction
============

``txsocketio`` is a :doc:`pure Python module <modules>` for accessing `Socket.IO`_ v1.x services from `Twisted`_.

.. _`Socket.IO`: http://socket.io/
.. _`Twisted`: https://twistedmatrix.com/

License
-------

``txsocketio`` is licensed under the `MIT License <https://opensource.org/licenses/MIT>`_.
Source code is `available on GitHub <https://github.com/posita/txsocketio>`__.

Installation
------------

Installation can be performed via ``pip`` (which will download and install the `latest release <https://pypi.python.org/pypi/txsocketio/>`__):

.. code-block:: sh

    % pip install txsocketio
    ...

Alternately, you can download the sources (e.g., `from GitHub <https://github.com/posita/txsocketio>`__) and run ``setup.py``:

.. code-block:: sh

    % git clone https://github.com/posita/txsocketio
    ...
    % cd txsocketio
    % python setup.py install
    ...

Requirements
------------

The service you want to consume must use v1.x of the Socket.IO protocol. Earlier versions are not supported.

A modern version of Python is required:

*   `cPython <https://www.python.org/>`_ (2.7 or 3.3+)

*   `PyPy <http://pypy.org/>`_ (Python 2.7 or 3.3+ compatible)

Python 2.6 will *not* work.

``txsocketio`` has the following dependencies (which will be installed automatically):

*   |autobahn|_

*   |future|_

*   |mock|_ (for Python 2.7)

*   |twisted|_

.. |autobahn| replace:: ``autobahn``
.. _`autobahn`: http://autobahn.ws/python/
.. |future| replace:: ``future``
.. _`future`: http://python-future.org/
.. |mock| replace:: ``mock``
.. _`mock`: https://github.com/testing-cabal/mock
.. |twisted| replace:: ``twisted``
.. _`twisted`: https://twistedmatrix.com/

Motivation
----------

TODO

Similar Tools
-------------

If you want a Socket.IO client for Python, but don't (or can't) use Twisted, check out Roy Hyunjin Han's |socketIO-client|_, which served as a very helpful source of information and guidance for understanding the various protocols and handshakes, and without which, this project may never have seen the light of day.
(It is a longstanding gripe that Socket.IO's documentation is severely inadequate, and its source code is sometimes difficult to follow.)

.. |socketIO-client| replace:: ``socketIO-client``
.. _`socketIO-client`: https://github.com/invisibleroads/socketIO-client
