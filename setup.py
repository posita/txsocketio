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
    absolute_import, division, print_function,
    # See <https://bugs.python.org/setuptools/issue152>
    # unicode_literals,
)

#---- Imports ------------------------------------------------------------

import setuptools

# See this e-mail thread:
# <http://www.eby-sarna.com/pipermail/peak/2010-May/003348.html>
import logging # pylint: disable=unused-import
import multiprocessing # pylint: disable=unused-import

import inspect
import os
from os import path

#---- Constants ----------------------------------------------------------

__all__ = ()

INSTALL_REQUIRES = [
    'Twisted >= 15.3',
    'future',
    'simplejson >= 3.0.0',
    'txrc >= 0.1.0, < 0.3.0',
]

_MY_DIR = path.dirname(inspect.getframeinfo(inspect.currentframe()).filename)

#---- Initialization -----------------------------------------------------

_namespace = {
    '_version_path': path.join(_MY_DIR, 'txsocketio', 'version.py'),
}

if path.isfile(_namespace['_version_path']):
    with open(_namespace['_version_path']) as _version_file:
        exec(compile(_version_file.read(), _namespace['_version_path'], 'exec'), _namespace, _namespace) # pylint: disable=exec-used

with open(path.join(_MY_DIR, 'README.rst')) as _readme_file:
    README = _readme_file.read()

__version__ = _namespace.get('__version__')
__version__ = u'.'.join(( str(i) for i in __version__ )) if __version__ is not None else None
__release__ = _namespace.get('__release__', __version__)

_SETUP_ARGS = {
    'name'                : 'txsocketio',
    'version'             : __version__,
    'author'              : 'Matt Bogosian',
    'author_email'        : 'mtb19@columbia.edu',
    'url'                 : 'https://txsocketio.readthedocs.org/en/{}/'.format(__release__),
    'license'             : 'MIT License',
    'description'         : 'Twisted Socket.IO client',
    'long_description'    : README,

    # From <https://pypi.python.org/pypi?%3Aaction=list_classifiers>
    'classifiers': (
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Development Status :: 3 - Alpha',
        'Framework :: Twisted',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        # TODO: Twisted isn't ready for these yet; maybe in 15.5?
        # 'Programming Language :: Python :: 3.3',
        # 'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Topic :: System :: Networking',
    ),

    'packages'            : setuptools.find_packages(exclude = ( 'tests', )),
    'include_package_data': True,
    'install_requires'    : INSTALL_REQUIRES,
}

if __name__ == '__main__':
    os.environ['COVERAGE_PROCESS_START'] = os.environ.get('COVERAGE_PROCESS_START', path.join(_MY_DIR, '.coveragerc'))
    setuptools.setup(**_SETUP_ARGS)
