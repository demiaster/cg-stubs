Set-StrictMode -Version Latest

$ErrorActionPreference = "Stop"


if ( -not $env:NUKE_EXECUTABLE ) {
    Write-Error (
        "NUKE_EXECUTABLE is not set or, set to an empty value in the environment. " +
        "Consider setting it in nuke/.env."
    )
    exit 1
}


# Get this Nuke's Python version.
$py_version_script = Join-Path $PSScriptRoot "get_py_version.py"

if ( -not ( Test-Path $py_version_script -PathType Leaf ) ) {
    Write-Error "Cannot infer Nuke's python version - $py_version_script is not a file."
    exit 1
}

$nuke_exe_args = @("-t")
if ($env:NUKE_NON_COMMERCIAL) {
    $nuke_exe_args += "--nc"
}

# NOTE: This is PowerShell 5/7 friendly. In PowerShell 7 one could use `New-TemporaryFile`.
$py_version_file = [System.IO.Path]::GetTempFileName()
try {
    & $env:NUKE_EXECUTABLE @nuke_exe_args $py_version_script $py_version_file *> $null
    $py_version = $(Get-Content $py_version_file)
}
finally {
    Remove-Item $py_version_file -ErrorAction SilentlyContinue
}

if ( -not $py_version ) {
    Write-Error  "Could not infer Nuke's python version."
    exit 1
}

Write-Output "Running uv with python $py_version"
uv run --only-dev --python $py_version --reinstall-package stubgenlib nuke_shim.py
