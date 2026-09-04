Set-StrictMode -Version Latest

$ErrorActionPreference = "Stop"

if (-not $env:NUKE_ROOT) {
    Write-Error "NUKE_ROOT is not set in the environment. Consider setting it in nuke/.env."
    exit 1
}

# USD Lib env vars
# https://learn.foundry.com/nuke/content/comp_environment/script_editor/nuke_python_module.html#WindowsSetup
$env:USG_USD_LIB_PATH = "$env:NUKE_ROOT/FnUSD/lib"
$env:USG_USD_PLUGIN_PATH = "$env:NUKE_ROOT/FnUSD/plugin/usd"

# The `FnUsdShim` DLL uses a versioned name that differs between Nuke versions
$shimDLL=(Get-ChildItem -path $env:NUKE_ROOT -filter "FnUsdShim.*.dll")[0]
if (-not $shimDLL) {
    Write-Error "Could not find FnUsdShim DLL in Nuke root $env:NUKE_ROOT"
    exit 1
}
$env:USG_SHIMLIB_NAME = $shimDLL.FullName

$env:PYTHONPATH = "$env:NUKE_ROOT/lib/site-packages"

$REPO_PATH = $(git rev-parse --show-toplevel)
$outdir = "$REPO_PATH/nuke/stubs"

uv run `
  --only-dev `
  --reinstall-package stubgenlib `
  --python "$env:NUKE_ROOT/python.exe" `
  stubgen_nuke.py `
  $outdir

# XXX: For command portability with the bash script
Set-Alias sed "C:\Program Files\Git\usr\bin\sed.exe"

sed -i 's/\bstring\b/str/g' $outdir/nuke-stubs/_nuke.pyi
sed -i 's/MenuorNone/Optional[Menu]/g' $outdir/nuke-stubs/_nuke.pyi
sed -i 's/\bBool\b/bool/g' $outdir/nuke-stubs/_nuke.pyi

# rm -r "$outdir/nuke-stubs"
# mv "$outdir/nuke_internal" "$outdir/nuke-stubs"
# mv "$outdir/_*.pyi" "$outdir/nuke-stubs"
