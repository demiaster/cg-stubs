"""Configure the environment and options to generate Nuke stubs.

This script is executed in an uv managed venv, using the Python interpreter bundled with Nuke (see setup in
`stubgen_nuke.{ps1,sh}`).
The stubs generation runs via `nuke -t`, optionally selecting the non-commercial licensing (i.e. `--nc`).

Notes on stubs runtime environment setup:

  1. As the stubs generation happens via `nuke -t`, there is no need to configure any Nuke-specific env vars.
  2. As the Nuke executable is not a Python interpreter, this script ensures that the venv's site-packages contributions
     (crucially, `mypy`) are available.
"""

import os
import pathlib
import subprocess
import sys
import sysconfig
from pathlib import Path
from typing import Mapping

NUKE_ROOT_ENV_VAR = "NUKE_ROOT"
NUKE_NON_COMMERCIAL_ENV_VAR = "NUKE_NON_COMMERCIAL"
NUKE_INTERACTIVE_ENV_VAR = "NUKE_INTERACTIVE"
STUBS_OUT = "stubs"
STUBGEN_SCRIPT = "stubgen_nuke.py"
_CURRENT_PATH = pathlib.Path(__file__).parent.absolute()


def get_nuke_root() -> Path:
    """Get Nuke install directory."""
    nuke_root_env_var = os.getenv(NUKE_ROOT_ENV_VAR, "")
    if not nuke_root_env_var:
        raise KeyError(
            "NUKE_ROOT is not set, or set to an empty value in the environment. Consider setting it in nuke/.env."
        )

    nuke_root_path = Path(nuke_root_env_var)

    if not nuke_root_path.exists() or not nuke_root_path.is_dir():
        raise NotADirectoryError(
            f"Candidate Nuke root {str(nuke_root_path)!r} is not a directory!"
        )
    return nuke_root_path


def get_nuke_executable(nuke_root: Path) -> Path:
    """Identify the nuke executable within the provided Nuke install directory.

    Example Nuke executable path on different platforms:

      - Win: 'C:/Program Files/Nuke17.1v1/Nuke17.1.exe'
      - Linux: '/usr/local/Nuke17.0v2/Nuke17.0'
    """
    platform_pattern = (
        "Nuke[0-9][0-9].[0-9].exe"
        if sys.platform == "win32"
        else "Nuke[0-9][0-9].[0-9]"
    )

    try:
        nuke_executable_path = next(nuke_root.glob(platform_pattern))
    except StopIteration:
        nuke_executable_path = None

    if nuke_executable_path is None or not nuke_executable_path.is_file():
        raise FileNotFoundError(
            f"Cannot locate Nuke's executable in {str(nuke_root)!r}"
        )
    return nuke_executable_path


def get_stubgen_env_vars(env: Mapping[str, str] | None) -> dict[str, str]:
    """Configure suitable Nuke environment to run stubs generation in."""
    if env is None:
        env = os.environ

    stubgen_env = {}
    stubgen_env["PYTHONPATH"] = os.pathsep.join(
        [
            sysconfig.get_paths()["purelib"],
            env.get("PYTHONPATH", ""),
        ]
    )
    return stubgen_env


def run_stubgen_in_nuke_venv() -> None:
    """Run Nuke stub generation in a Nuke venv-like environment.

    The stubgen generation script is the `STUBGEN_SCRIPT` Python script sibling of this one.
    Stubs will be written in the `STUBS_OUT` dir sibling of this script.
    """
    nuke_root = get_nuke_root()
    nuke_executable_path = get_nuke_executable(nuke_root)
    env = os.environ.copy()
    env.update(get_stubgen_env_vars(env))

    stub_generation_script_path = Path(_CURRENT_PATH / STUBGEN_SCRIPT).resolve()
    stub_out_dir = Path(_CURRENT_PATH / STUBS_OUT).resolve()

    args = [
        str(nuke_executable_path),
        "-t",
    ]

    if os.getenv(NUKE_NON_COMMERCIAL_ENV_VAR):
        args.append("--nc")
    elif os.getenv(NUKE_INTERACTIVE_ENV_VAR):
        args.append("-i")

    args.extend(
        [
            str(stub_generation_script_path),
            str(stub_out_dir),
        ]
    )
    print(f"Running command: {subprocess.list2cmdline(args)}")
    result = subprocess.run(args, env=env)

    raise SystemExit(result.returncode)


if __name__ == "__main__":
    run_stubgen_in_nuke_venv()
