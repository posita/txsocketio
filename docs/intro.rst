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

Copyright and other protections apply.
Please see the accompanying :doc:`LICENSE <LICENSE>` and :doc:`CREDITS <CREDITS>` file(s) for rights and restrictions governing use of this software.
All rights not expressly waived or licensed are reserved.
If those files are missing or appear to be modified from their originals, then please contact the author before viewing or using this software in any capacity.

Introduction
============

``txsocketio`` is a :doc:`pure Python module <modules>` for accessing `Socket.IO`_ v1.x services from `Twisted`_.

.. _`Socket.IO`: http://socket.io/
.. _`Twisted`: https://twistedmatrix.com/

License
-------

``txsocketio`` is licensed under the `MIT License <https://opensource.org/licenses/MIT>`_.
See the :doc:`LICENSE <LICENSE>` file for details.
Source code is `available on GitHub <https://github.com/posita/txsocketio>`__.

Installation
------------

Installation can be performed via ``pip`` (which will download and install the `latest release <https://pypi.python.org/pypi/txsocketio/>`__):

.. code-block:: console

    % pip install txsocketio
    ...

Alternately, you can download the sources (e.g., `from GitHub <https://github.com/posita/txsocketio>`__) and run ``setup.py``:

.. code-block:: console

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

*   |Twisted|_
*   |autobahn|_
*   |future|_
*   |mock|_ (for Python 2.7)

.. |Twisted| replace:: ``Twisted``
.. _`Twisted`: https://twistedmatrix.com/
.. |autobahn| replace:: ``autobahn``
.. _`autobahn`: http://autobahn.ws/python/
.. |future| replace:: ``future``
.. _`future`: http://python-future.org/
.. |mock| replace:: ``mock``
.. _`mock`: https://github.com/testing-cabal/mock

Motivation
----------

TODO

Similar Tools
-------------

If you want a Socket.IO client for Python, but don't (or can't) use Twisted, check out Roy Hyunjin Han's |socketIO-client|_, which served as a very helpful source of information and guidance for understanding the various protocols and handshakes, and without which, this project may never have seen the light of day.
(It is a longstanding gripe that Socket.IO's documentation is severely inadequate, and its source code is sometimes difficult to follow.)

.. |socketIO-client| replace:: ``socketIO-client``
.. _`socketIO-client`: https://github.com/invisibleroads/socketIO-client
