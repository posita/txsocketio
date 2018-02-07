#!/usr/bin/env python
# -*- encoding: utf-8; grammar-ext: py; mode: python -*-

# ========================================================================
"""
Copyright and other protections apply. Please see the accompanying
:doc:`LICENSE <LICENSE>` and :doc:`CREDITS <CREDITS>` file(s) for rights
and restrictions governing use of this software. All rights not expressly
waived or licensed are reserved. If those files are missing or appear to
be modified from their originals, then please contact the author before
viewing or using this software in any capacity.
"""
# ========================================================================

from __future__ import (
    absolute_import, division, print_function,
    # See <https://bugs.python.org/setuptools/issue152>
    # unicode_literals,
)

# ---- Imports -----------------------------------------------------------

import setuptools

import codecs
import inspect
import os

# ---- Constants ---------------------------------------------------------

__all__ = ()

_MY_DIR = os.path.dirname(inspect.getframeinfo(inspect.currentframe()).filename)

INSTALL_REQUIRES = (
    'Twisted >= 16.0.0',
    'future',
    'simplejson >= 3.0.0',
    'txrc >= 0.1.0, < 0.3.0',
)

TESTS_REQUIRE = [
    'pytest',
]

# WARNING: This imposes limitations on test/requirements.txt such that the
# full Pip syntax is not supported. See also
# <http://stackoverflow.com/questions/14399534/>.
with open(os.path.join(_MY_DIR, 'test', 'requirements.txt')) as f:
    TESTS_REQUIRE.extend(f.read().splitlines())

# ---- Initialization ----------------------------------------------------

_namespace = {
    '_version_path': os.path.join(_MY_DIR, 'txsocketio', 'version.py'),
}

if os.path.isfile(_namespace['_version_path']):
    with open(_namespace['_version_path']) as _version_file:
        exec(compile(_version_file.read(), _namespace['_version_path'], 'exec'), _namespace, _namespace)  # pylint: disable=exec-used

with codecs.open(os.path.join(_MY_DIR, 'README.rst'), encoding='utf-8') as _readme_file:
    README = _readme_file.read()

__vers_str__ = _namespace.get('__vers_str__')
__release__ = _namespace.get('__release__', __vers_str__)

SETUP_ARGS = {
    'name': 'txsocketio',
    'version': __vers_str__,
    'author': 'Matt Bogosian',
    'author_email': 'matt@bogosian.net',
    'url': 'https://txsocketio.readthedocs.org/en/{}/'.format(__release__),
    'license': 'MIT License',
    'description': 'Twisted Socket.IO client',
    'long_description': README,

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
        # 'Programming Language :: Python :: 3.4',
        # 'Programming Language :: Python :: 3.5',
        # 'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Topic :: System :: Networking',
    ),

    'packages': setuptools.find_packages(),
    'include_package_data': True,
    'install_requires': INSTALL_REQUIRES,
    'setup_requires': ( 'pytest-runner', ),
    'tests_require': TESTS_REQUIRE,
}

if __name__ == '__main__':
    os.environ['COVERAGE_PROCESS_START'] = os.environ.get('COVERAGE_PROCESS_START', os.path.join(_MY_DIR, '.coveragerc'))
    setuptools.setup(**SETUP_ARGS)
