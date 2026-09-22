#!/bin/env bash

set -euo pipefail


[[ -z "${NUKE_ROOT:-}" ]] && {
    msg="NUKE_ROOT is not set, or set to an empty value in the environment. "
    msg+="Consider setting it in nuke/.env."
    >&2 echo "${msg}"
    exit 1
}

[[ ! -d "${NUKE_ROOT}" ]] && {
    >&2 echo "NUKE_ROOT ${NUKE_ROOT} is not a directory."
    exit 1
}


# Get this Nuke's Python interpreter.
readarray -d '' nuke_py_interpreter < <(
    find "${NUKE_ROOT}" -maxdepth 1 -regextype posix-extended -regex '.*/python[0-9]\.[0-9]{1,2}' -type f -print0
)

(( ${#nuke_py_interpreter[@]} == 0 )) && {
    >&2 echo "Cannot locate Nuke's python interpreter in ${NUKE_ROOT}."
    exit 1
}

(( ${#nuke_py_interpreter[@]} > 1 )) && {
    echo "Found multiple Nuke python interpreters in ${NUKE_ROOT}, proceeding with the first one."
}
echo "Running uv with Nuke's python interpreter ${nuke_py_interpreter[0]}"
uv run --only-dev --python "${nuke_py_interpreter[0]}" --reinstall-package stubgenlib nuke_shim.py
