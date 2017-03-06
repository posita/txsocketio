#!/usr/bin/env sh
# -*- encoding: utf-8; grammar-ext: sh; mode: shell-script -*-

# ========================================================================
# Copyright and other protections apply. Please see the accompanying
# ``LICENSE`` and ``CREDITS`` files for rights and restrictions governing
# use of this software. All rights not expressly waived or licensed are
# reserved. If those files are missing or appear to be modified from their
# originals, then please contact the author before viewing or using this
# software in any capacity.
# ========================================================================

_PARENT_DIR="$( cd "$( dirname "${0}" )" && pwd )/.."
set -ex
[ -d "${_PARENT_DIR}" ]
[ "${_PARENT_DIR}/docs/checkmodified.sh" -ef "${0}" ]
cd "${_PARENT_DIR}"
test -z "$( git ls-files --other --exclude-from .gitignore docs )"
