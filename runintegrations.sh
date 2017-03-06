#!/usr/bin/env sh
# -*- encoding: utf-8; grammar-ext: sh; mode: shell-script -*-

# =======================================================================
# Copyright and other protections apply. Please see the accompanying
# ``LICENSE`` and ``CREDITS`` files for rights and restrictions governing
# use of this software. All rights not expressly waived or licensed are
# reserved. If those files are missing or appear to be modified from their
# originals, then please contact the author before viewing or using this
# software in any capacity.
# ========================================================================

_MY_DIR="$( cd "$( dirname "${0}" )" && pwd )"
set -e
[ -d "${_MY_DIR}" ]
[ "${_MY_DIR}/runintegrations.sh" -ef "${0}" ]
cd "${_MY_DIR}"

if [ -n "${CLEAN}" ] ; then
    rm -frv "${_MY_DIR}/integrations/node/node_modules"
fi

TOX_ENV="${TOX_ENV:-check}"
COVERAGE="${_MY_DIR}/.tox/${TOX_ENV}/bin/coverage"

[ -x "${COVERAGE}" ] \
    || tox -e "${TOX_ENV}"

[ -x "${_MY_DIR}/integrations/node/node_modules/.bin/node-daemon" ] \
    || (
            set -x
            cd "${_MY_DIR}/integrations/node"
            npm install
        )

_SOCK=./node-daemon.sock

rm -fv \
        "${_MY_DIR}/integrations/node/node-daemon.err" \
        "${_MY_DIR}/integrations/node/node-daemon.log"

(
    set -x
    cd "${_MY_DIR}/integrations/node"
    DEBUG='*' ./node_modules/.bin/node-daemon --socket "${_SOCK}" --worker server.js --workers 1
)

_retval="${?}"

[ "${_retval}" -eq 0 ] \
    || exit "${_retval}"

(
    set -x
    cd "${_MY_DIR}/integrations/node"
    _remaining=10

    while ! curl >/dev/null --max-time 1 --silent --unix-socket ./http.sock 'http:/engine.io/' ; do
        _remaining="$(( _remaining - 1 ))"

        if [ "${_remaining}" -le 0 ] ; then
            curl --version
            (
                cd "${_MY_DIR}/integrations/node"
                grep -n '' *.log
            )
            break
            # exit 1
        fi

        sleep 1
    done
)

_retval="${?}"

if [ "${_retval}" -ne 0 ] ; then
    (
        cd "${_MY_DIR}/integrations/node"
        ./node_modules/.bin/node-daemon-ctl --socket "${_SOCK}" stop
    )

    exit "${_retval}"
fi

set +e

_num_failed=0

for t in $( find "${_MY_DIR}/integrations/scripts" -type f -perm +100 -o -name \*.py ) ; do
    if [ "${t%.py}x" != "${t}x" ] ; then
        ( set -x ; "${_MY_DIR}/.tox/check/bin/coverage" run --append "${t}" )
    else
        ( set -x ; "${t}" )
    fi

    _retval="${?}"

    if [ "${_retval}" -ne 0 ] ; then
        echo 1>&2 "${t} failed with exit status ${_retval}"
        _num_failed="$(( _num_failed + 1 ))"
    fi
done

( set -x ; "${COVERAGE}" run --append -m unittest discover --pattern 'integration_*.py' --verbose ) \
    || _num_failed="$(( _num_failed + 1 ))"

(
    set -x
    cd "${_MY_DIR}/integrations/node"
    _remaining=30

    while [ -S "${_SOCK}" ] ; do
        ./node_modules/.bin/node-daemon-ctl --socket "${_SOCK}" stop
        _remaining="$(( _remaining - 1 ))"

        if [ "${_remaining}" -le 0 ] ; then
            exit 1
        fi

        sleep 1
    done
)

_retval="${?}"

if [ "${_retval}" -ne 0 ] ; then
    exit "${_retval}"
elif [ "${_num_failed}" -ne 0 ] ; then
    exit 63
fi
