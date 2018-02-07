# -*- encoding: utf-8; grammar-ext: py; mode: python; test-case-name: test.test_dispatcher -*-

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
    absolute_import, division, print_function, unicode_literals,
)
from builtins import *  # noqa: F401,F403 # pylint: disable=redefined-builtin,unused-wildcard-import,useless-suppression,wildcard-import
from future.builtins.disabled import *  # noqa: F401,F403 # pylint: disable=no-name-in-module,redefined-builtin,unused-wildcard-import,useless-suppression,wildcard-import

# ---- Imports -----------------------------------------------------------

import collections
import logging
import os
from twisted.internet import defer as t_defer
from twisted.python import failure as t_failure

# ---- Constants ---------------------------------------------------------

__all__ = (
    'Dispatcher',
)

_LOGGER = logging.getLogger(__name__)

# ---- Classes -----------------------------------------------------------

# ========================================================================
class Dispatcher(object):
    """
    An event dispatcher. Event handlers are callbacks with the signature:

        .. code-block:: python

            callback(event, ...)

    Callbacks can be registered to be called when the
    :meth:`~Dispatcher:dispatch` method is called with a particular
    ``event``. Any arguments passed to :meth:`~Dispatcher:dispatch` are
    passed directly to the callbacks.

    Callbacks are called serially in the order in which they were
    registered, leaving the concurrence model up to the registrant. Errors
    raised by callbacks are logged, but otherwise ignored.

    :param iterable events: if non-empty, this restricts the events for
        which callbacks can be registered
    """

    # ---- Constructor ---------------------------------------------------

    def __init__(self, events=()):
        self._events = frozenset(events)
        self._callbacks = dict(( ( e, collections.deque() ) for e in self._events ))

    # ---- Public methods ------------------------------------------------

    def deferredon(self, event):
        """
        Creates a :class:`twisted.internet.defer.Deferred` and registers
        its callback to be fired once (see :meth:`~Dispatcher.once`) when
        ``event`` is next dispatched. The event and any arguments are
        passed to :meth:`twisted.internet.defer.Deferred.callback` as a
        3-`tuple`: ``( event, args, kw )`` (see
        :meth:`~Dispatcher.dispatch`).

        .. code-block:: python
            :linenos:

            >>> d = Dispatcher()
            >>> deferred = d.deferredon('event')
            >>> def handler(d_arg):
            ...     event, args, kw = d_arg
            ...     print('handler called with {}, {}, {}'.format(event, args, kw))
            >>> deferred.addCallback(handler) # doctest: +ELLIPSIS
            <Deferred at ...>
            >>> d.dispatch('event')
            handler called with event, (), {}
            >>> d.dispatch('event')
        """
        d = t_defer.Deferred()

        def _callback(event, *args, **kw):
            return d.callback(( event, args, kw ))

        if not self.register(event, _callback, once=True):
            raise ValueError('unable to register callback for {!r}'.format(event))

        return d

    def dispatch(self, event, *args, **kw):
        """
        Invokes all callbacks registered for ``event`` with the provided
        ``args`` and ``kw``, one at a time. Exceptions are logged and
        ignored. If a callback returns a
        :class:`~twisted.internet.defer.Deferred`, an errback is added to
        log and ignore any failure. If this behavior is undesirable,
        consider decorating callbacks such that unhandled errors are
        adequately treated.
        """
        try:
            # We copy the callbacks because we (or they) might modify the
            # deque during processing
            callbacks = tuple(reversed(self._callbacks[event]))
        except KeyError:
            return

        for callback, once in callbacks:
            if once:
                self.unregister(event, callback, once)

            try:
                retval = callback(event, *args, **kw)

                if isinstance(retval, t_defer.Deferred):
                    retval.addErrback(self._logerror, 'failure raised from deferred event callback {!r} (ignored)'.format(callback))
            except Exception as exc:  # pylint: disable=broad-except
                self._logerror(exc, 'exception raised from event callback {!r} (ignored)'.format(callback))

    def on(self, event, callback):
        """
        Alias for :meth:`~Dispatcher.register`.
        """
        return self.register(event, callback)

    def once(self, event, callback):
        """
        Alias for :meth:`~Dispatcher.register` with ``once`` set to
        `True`.

        .. code-block:: python
            :linenos:

            >>> d = Dispatcher()
            >>> def handler(event):
            ...   print('handler({})'.format(event))
            >>> d.once('event', handler)
            True
            >>> d.dispatch('event')
            handler(event)
            >>> d.dispatch('event')
        """
        return self.register(event, callback, once=True)

    def register(self, event, callback, once=False):
        """
        Registers ``callback`` to be called when
        :meth:`~Dispatcher.dispatch` is subsequently called with a
        matching ``event``. Arguments passed to
        :meth:`~Dispatcher.dispatch` are passed directly to each
        registered callback, which means that in most cases, callbacks
        should take care not to modify any mutable arguments, as
        subsequent callbacks will see the modifications.

        A callback can be registered multiple times and will be called
        exactly once for each time it is registered. See also
        :meth:`~Dispatcher.unregister`.

        Note that once a ``callback`` is registered, if it is to be
        unregistered, :meth:`~Dispatcher.unregister` must be called with
        the same values for each argument, including ``once``.

        :param event: the event for which ``callback`` should be
            registered

        :param callable callback: the callback to be registered

        :param bool once: if `True`, :meth:`~Dispatcher.unregister` will
            be called for ``event`` and ``callable`` just before it is
            called

        :returns: `True` if ``callback`` was added, `False` otherwise;
            this should always be `True` unless a non-empty ``events``
            parameter was passed to :meth:`~Dispatcher.__init__`
        """
        if self._events \
                and event not in self._events:
            return False

        try:
            event_callbacks = self._callbacks[event]
        except KeyError:
            event_callbacks = self._callbacks[event] = collections.deque()

        event_callbacks.appendleft(( callback, once ))

        return True

    def unregister(self, event, callback, once=False):
        """
        Unregisters a previously registered ``callback`` so that it will
        no longer be called when :meth:`~Dispatcher.dispatch` is called
        with a matching ``event``.

        .. code-block:: python
            :linenos:

            >>> d = Dispatcher()
            >>> def handler(event):
            ...   print('handler({})'.format(event))
            >>> d.register('event1', handler)
            True
            >>> d.register('event2', handler)
            True
            >>> d.dispatch('event1')
            handler(event1)
            >>> d.dispatch('event2')
            handler(event2)
            >>> d.unregister('event1', handler)
            True
            >>> d.dispatch('event1')
            >>> d.dispatch('event2')
            handler(event2)

        All arguments must match those used with
        :meth:`~Dispatcher.register` to register the callback.

        :param event: the event for which ``callback`` should be
            unregistered

        :param callable callback: the callback to be unregistered

        :param bool once: see :meth:`~Dispatcher.register`

        :returns: `True` if ``callback`` was found, `False` if it wasn't
        """
        try:
            self._callbacks[event].remove(( callback, once ))
        except ( KeyError, ValueError ):
            return False

        return True

    # ---- Private methods -----------------------------------------------

    def _logerror(self, e, msg=''):
        if isinstance(e, t_failure.Failure):
            _LOGGER.warning(msg + os.linesep + e.getTraceback(detail='verbose'))
        else:
            _LOGGER.warning(msg, exc_info=True)
