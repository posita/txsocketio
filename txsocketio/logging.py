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

import functools
import io
import logging as _logging
import sys
from twisted.internet import defer as t_defer

#---- Constants ----------------------------------------------------------

__all__ = ()

SILENT = -(sys.maxsize) - 1

_IS_PY3 = sys.version_info >= ( 3, 0 )
_LOGGER = _logging.getLogger(__name__)
_LOGGER_TOP_LEVEL = _logging.getLogger()

#---- Functions ----------------------------------------------------------

#=========================================================================
def formattraceback(failure, *args, **kw):
    """
    Returns a traceback string for ``failure``.

    :param failure: the failure for which to build the traceback string

    :type failure: :class:`twisted.python.failure.Failure`

    :param args: passed to
        :meth:`twisted.python.failure.Failure.printTraceback`

    :param kw: passed to
        :meth:`twisted.python.failure.Failure.printTraceback`
    """
    # See <https://twistedmatrix.com/trac/ticket/8044>
    buf = io.StringIO() if _IS_PY3 else io.BytesIO()
    failure.printTraceback(buf, *args, **kw)
    tb_str = buf.getvalue() if _IS_PY3 else buf.getvalue().decode('ascii')

    return tb_str.strip()

#=========================================================================
def logerrback(failure, logger=_LOGGER_TOP_LEVEL, log_lvl=_logging.DEBUG, msg='Unhandled error:', handled=(), suppress_msg_on_handled=True, reraise_handled=False):
    """
    Generic errback function to log failures.

    :param failure: the failure to inspect

    :type failure: :class:`twisted.python.failure.Failure`

    :param logger: the logger to use

    :type logger: :class:`logging.Logger`

    :param Integral log_lvl: level passed to :meth:`logging.Logger.log`

    :param str msg: the message to log or `None` for no message

    :param sequence handled: a sequence of :exc:`Exception`s whose stack
        traces will *not* be logged

    :param bool reraise: if `True`, causes ``failure`` to be returned
        (passed through)

    :param bool suppress_msg_on_handled: if `True`, suppress logging of
        ``msg`` ``failure.value`` matches ``handled``

    :returns: ``failure`` if ``reraise`` is `True`, otherwise `None`
    """
    is_handled = failure.check(*handled)

    if not is_handled \
            or not suppress_msg_on_handled:
        if msg is not None:
            logger.log(log_lvl, msg)

        logger.log(log_lvl, formattraceback(failure))

    if not is_handled \
            or reraise_handled:
        return failure

#=========================================================================
def logerrbackdl(dl_res, logger=_LOGGER, log_lvl=_logging.DEBUG, msg=None, handled=(), suppress_msg_on_handled=False):
    """
    Generic errback function to log individual failures from
    :class:`twisted.internet.defer.DeferredList`s. Each failure is logged
    using :func:`logerrback`.

    :param iterable dl_res: the deferred list results to inspect

    :param logger: the logger to use

    :type logger: :class:`logging.Logger`

    :param log_lvl: passed to :func:`logerrback`

    :param msg: passed to :func:`logerrback`

    :param handled: passed to :func:`logerrback`

    :param suppress_msg_on_handled: passed to :func:`logerrback`

    :returns: ``dl_res``
    """
    if dl_res is not None:
        for success, res in dl_res:
            if not success:
                logerrback(res, logger, log_lvl, msg, handled, suppress_msg_on_handled, reraise_handled=False)

    return dl_res

#=========================================================================
def logunhandlederr(log_lvl, logger=_LOGGER):
    """
    Decorates a maybe-deferred callable (the decorated callable always
    returns a deferred) to log unhandled errors. Example usage:

        .. code-block:: python
            :linenos:

            @logunhandlederr(logging.DEBUG)
            def raiseorreturn(raise=True):
                if raise:
                    raise Exception

                return 'Success!'

            d = raiseorreturn()

    :param Integral log_lvl: level passed to :meth:`logging.Logger.log`

    :param logger: the logger to use

    :type logger: :class:`logging.Logger`

    :return: the decorated callable
    """
    def wrap(_call):
        def _logunhandlederr(*__args, **__kw):
            target_d = t_defer.maybeDeferred(_call, *__args, **__kw)
            target_d.addErrback(logerrback, logger, log_lvl, handled=( Exception, ))

            return target_d

        try:
            _logunhandlederr = functools.wraps(_call)(_logunhandlederr)
        except AttributeError:
            pass

        return _logunhandlederr

    return wrap
