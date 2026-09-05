import os
import pathlib
import subprocess
import sys
from pathlib import Path
from typing import Mapping

NUKE_EXECUTABLE_ENV_VAR = "NUKE_EXECUTABLE"
NUKE_NON_COMMERCIAL_ENV_VAR = "NUKE_NON_COMMERCIAL"
STUBS_OUT = "stubs"
STUBGEN_SCRIPT = "stubgen_nuke.py"
_CURRENT_PATH = pathlib.Path(__file__).parent.absolute()


def get_nuke_executable() -> Path:
    """Retrieve path to nuke executable from environment."""
    nuke_executable_env_var = os.getenv(NUKE_EXECUTABLE_ENV_VAR, "")
    if not nuke_executable_env_var:
        raise KeyError(
            "NUKE_EXECUTABLE is not set, or set to an empty value in the environment. "
            "Consider setting it in nuke/.env."
        )

    nuke_executable_path = Path(nuke_executable_env_var)

    if not nuke_executable_path.exists() or not nuke_executable_path.is_file():
        raise ValueError(
            f"Candidate Nuke executable {str(nuke_executable_path)} is not a file!"
        )
    return nuke_executable_path


def get_venv_site_packages(env: Mapping[str, str] | None) -> Path:
    if env is None:
        env = os.environ

    if not env.get("VIRTUAL_ENV"):
        raise RuntimeError("Must run this from a virtual environment!")

    if sys.platform == "win32":
        venv_py_executable = Path(env["VIRTUAL_ENV"]) / "Scripts" / "python.exe"
    else:
        venv_py_executable = next(iter(Path(env["VIRTUAL_ENV"], "bin").glob("python*")))
    if not venv_py_executable or not venv_py_executable.exists():
        raise RuntimeError("Cannot identify venv py executable")

    venv_site_packages = subprocess.check_output(
        [
            str(venv_py_executable),
            "-c",
            'import sysconfig; print(sysconfig.get_paths()["purelib"])',
        ],
        text=True,
    ).strip()

    return Path(venv_site_packages)


def get_nuke_site_packages(nuke_root: Path) -> Path:
    # FIXME: this was in the bash/pwsh as setting PYTHONPATH from scratch, here it is being added.
    #  does it cause any issues?
    nuke_libs = nuke_root / "lib"
    if sys.platform == "win32":
        nuke_site_packages = nuke_libs / "site-packages"
    else:
        nuke_site_packages = next(iter(nuke_libs.glob("*/site-packages")), "")
    if not nuke_site_packages or not nuke_site_packages.is_dir():
        raise NotADirectoryError(
            f"Nuke site-packages directory {str(nuke_site_packages)} does not exist!"
        )
    return nuke_site_packages


def get_pythonpath_env_var(
    nuke_root: Path, env: Mapping[str, str] | None
) -> dict[str, str]:
    if env is None:
        env = os.environ

    pythonpath = os.pathsep.join(
        [
            str(get_venv_site_packages(env)),
            str(get_nuke_site_packages(nuke_root)),
            env.get("PYTHONPATH", ""),
        ]
    )
    return {"PYTHONPATH": pythonpath}


def get_nuke_usd_lib_env_vars(nuke_root: Path) -> dict[str, str]:
    """Env vars for Nuke USD setup.

    https://learn.foundry.com/nuke/content/comp_environment/script_editor/nuke_python_module.html#WindowsSetup
    """
    if sys.platform != "win32":
        return {}

    usg_lib_path = nuke_root / "FnUSD" / "lib"
    usg_plugin_path = nuke_root / "FnUSD" / "plugin" / "usd"
    usg_shim_dll_path = next(iter(nuke_root.glob("FnUsdShim.*.dll")), None)
    for path in (usg_lib_path, usg_plugin_path, usg_shim_dll_path):
        if path is None or not path.exists():
            raise FileNotFoundError(
                f"Cannot configure USD for Nuke: {str(path)!r} does not exist!"
            )

    return {
        "USG_USD_LIB_PATH": str(usg_lib_path),
        "USG_USD_PLUGIN_PATH": str(usg_plugin_path),
        "USG_SHIMLIB_NAME": str(usg_shim_dll_path),
    }


def get_stubs_out_dir() -> pathlib.Path:
    """Get the stubs out dir.

    This is the `STUBS_OUT` folder sibling of this script.
    """
    out_dir = Path(_CURRENT_PATH / STUBS_OUT).resolve()
    if not out_dir.is_dir():
        raise NotADirectoryError(f"Stubs out directory {str(out_dir)} does not exist!")
    return out_dir


def get_stubs_generation_script_path() -> pathlib.Path:
    """Get the .py stubs generation script path.

    This is the `STUBGEN_SCRIPT` Python script sibling of this one.
    """
    stubs_generation_script = Path(_CURRENT_PATH / STUBGEN_SCRIPT).resolve()
    if not stubs_generation_script.exists():
        raise FileNotFoundError(
            f"Stubs generation script {str(stubs_generation_script)} does not exist!"
        )
    return stubs_generation_script


def run_stubgen_in_nuke_venv() -> None:
    # Construct env for stub generation.
    env = os.environ.copy()

    nuke_executable_path = get_nuke_executable()
    env.update(get_pythonpath_env_var(nuke_executable_path.parent, env))
    env.update(get_nuke_usd_lib_env_vars(nuke_executable_path.parent))

    args = [
        str(nuke_executable_path),
        "-t",
    ]

    if os.getenv(NUKE_NON_COMMERCIAL_ENV_VAR):
        args.append("--nc")

    args.extend(
        [
            str(get_stubs_generation_script_path()),
            str(get_stubs_out_dir()),
        ]
    )
    print(f"Running command: {' '.join(args)}")
    result = subprocess.run(args, env=env)

    raise SystemExit(result.returncode)


if __name__ == "__main__":
    run_stubgen_in_nuke_venv()
