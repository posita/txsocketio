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

from setuptools import (
    find_packages,
    setup,
)

# See this e-mail thread:
# <http://www.eby-sarna.com/pipermail/peak/2010-May/003348.html>
import logging # pylint: disable=unused-import
import multiprocessing # pylint: disable=unused-import

from inspect import (
    currentframe,
    getframeinfo,
)
from os.path import (
    dirname,
    isfile,
    join as ospath_join,
)

#---- Constants ----------------------------------------------------------

__all__ = ()

INSTALL_REQUIRES = (
    'future',
    'twisted',
)

_MY_DIR = dirname(getframeinfo(currentframe()).filename)

#---- Initialization -----------------------------------------------------

_namespace = {
    '_version_path': ospath_join(_MY_DIR, '_txsocketio', 'version.py'),
}

if isfile(_namespace['_version_path']):
    with open(_namespace['_version_path']) as _version_file:
        exec(compile(_version_file.read(), _namespace['_version_path'], 'exec'), _namespace, _namespace) # pylint: disable=exec-used

with open(ospath_join(_MY_DIR, 'README.rst')) as _readme_file:
    README = _readme_file.read()

__version__ = _namespace.get('__version__')
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
        'Development Status :: 1 - Planning',
        'Framework :: Twisted',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Topic :: System :: Networking',
    ),

    'packages'            : find_packages(exclude = ( 'tests', )),
    'include_package_data': True,
    'install_requires'    : INSTALL_REQUIRES,
    'test_suite'          : 'tests',
}

if __name__ == '__main__':
    setup(**_SETUP_ARGS)
