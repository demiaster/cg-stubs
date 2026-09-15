Set-StrictMode -Version Latest

$ErrorActionPreference = "Stop"


if ( -not $env:NUKE_ROOT ) {
    Write-Error (
        "NUKE_ROOT is not set or, set to an empty value in the environment. " +
        "Consider setting it in nuke/.env."
    )
    exit 1
}

if ( -not ( Test-Path $env:NUKE_ROOT -PathType Container ) ) {
    Write-Error "NUKE_ROOT $env:NUKE_ROOT is not a directory."
    exit 1
}

# Get this Nuke's Python interpreter.
$nuke_py_interpreter = Join-Path $env:NUKE_ROOT "python.exe"

if ( -not ( Test-Path $nuke_py_interpreter -PathType Leaf ) ) {
    Write-Error "Cannot locate Nuke's python interpreter - $nuke_py_interpreter is not a file."
    exit 1
}

Write-Output "Running uv with Nuke's python interpreter $nuke_py_interpreter"
uv run --only-dev --python $nuke_py_interpreter --reinstall-package stubgenlib nuke_shim.py
