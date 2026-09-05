#!/bin/env bash

set -euo pipefail


[[ -z "${NUKE_EXECUTABLE:-}" ]] && {
    msg="NUKE_EXECUTABLE is not set, or set to an empty value in the environment. "
    msg+="Consider setting it in nuke/.env."
    >&2 echo "${msg}"
    exit 1
}


# Get this Nuke's Python version.
THIS_SCRIPT_DIR=$(dirname "${BASH_SOURCE[0]}")
py_version_script="${THIS_SCRIPT_DIR}/get_py_version.py"

[[ ! -f "${py_version_script}" ]] && {
    >&2 echo "Cannot infer Nuke's python version - ${py_version_script} is not a file."
    exit 1
}

py_version_file=$(mktemp -t "py_version.XXXXXXXXXX")
trap "rm ${py_version_file}" EXIT

&>/dev/null ${NUKE_EXECUTABLE} -t ${NUKE_NON_COMMERCIAL:+--nc} "${py_version_script}" "${py_version_file}"

py_version=$(cat ${py_version_file})

[[ -z "${py_version}" ]] && {
    >&2 echo "Could not infer Nuke's python version."
    exit 1
}

echo "Running uv with python ${py_version}"
uv run --only-dev --python "${py_version}" --reinstall-package stubgenlib nuke_shim.py
