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

_REPO_DIR="$( cd "$( dirname "${0}" )" && pwd )/.."
set -e
[ -d "${_REPO_DIR}" ]
[ "${_REPO_DIR}/helpers/runintegrations.sh" -ef "${0}" ]
cd "${_REPO_DIR}"

if [ -n "${CLEAN}" ] ; then
    rm -frv "${_REPO_DIR}/integration/node/node_modules"
fi

[ -x "${_REPO_DIR}/integration/node/node_modules/.bin/node-daemon" ] \
    || (
            set -x
            cd "${_REPO_DIR}/integration/node"
            npm install
        )

_SOCK=./node-daemon.sock

rm -fv \
        "${_REPO_DIR}/integration/node/node-daemon.err" \
        "${_REPO_DIR}/integration/node/node-daemon.log"

(
    set -x
    cd "${_REPO_DIR}/integration/node"
    DEBUG='*' ./node_modules/.bin/node-daemon --socket "${_SOCK}" --worker server.js --workers 1
)

_retval="${?}"

[ "${_retval}" -eq 0 ] \
    || exit "${_retval}"

(
    set -x
    cd "${_REPO_DIR}/integration/node"
    _remaining=10

    while ! curl >/dev/null --max-time 1 --silent --unix-socket ./http.sock 'http:/engine.io/' ; do
        _remaining="$(( _remaining - 1 ))"

        if [ "${_remaining}" -le 0 ] ; then
            curl --version
            (
                cd "${_REPO_DIR}/integration/node"
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
        cd "${_REPO_DIR}/integration/node"
        ./node_modules/.bin/node-daemon-ctl --socket "${_SOCK}" stop
    )

    exit "${_retval}"
fi

set +e

_num_failed=0

for t in $( find "${_REPO_DIR}/integration/scripts" -type f -perm +100 -o -name \*.py ) ; do
    if [ "${t%.py}x" != "${t}x" ] ; then
        ( set -x ; coverage run --append "${t}" )
    else
        ( set -x ; "${t}" )
    fi

    _retval="${?}"

    if [ "${_retval}" -ne 0 ] ; then
        echo 1>&2 "${t} failed with exit status ${_retval}"
        _num_failed="$(( _num_failed + 1 ))"
    fi
done

( set -x ; coverage run --append -m unittest discover --pattern 'integration_*.py' --verbose ) \
    || _num_failed="$(( _num_failed + 1 ))"

(
    set -x
    cd "${_REPO_DIR}/integration/node"
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
