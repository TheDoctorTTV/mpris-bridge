from __future__ import annotations

#################
### IMPORTS ###
#################

import argparse
import importlib.util
import os
import subprocess
import sys
from pathlib import Path


############################
### ENVIRONMENT CHECKS ###
############################

def has_pyinstaller(python: Path) -> bool:
    # Check whether the selected Python can import PyInstaller.
    result = subprocess.run(
        [str(python), "-c", "import PyInstaller"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def in_venv() -> bool:
    # sys.prefix changes when Python is running inside a virtual environment.
    return sys.prefix != sys.base_prefix


def venv_python(root: Path) -> Path:
    # Return the virtual environment interpreter path used by this project.
    return root / ".venv" / "bin" / "python"


###########################
### BUILD BOOTSTRAP ###
###########################

def ensure_build_environment(root: Path) -> int:
    # Use a local virtual environment for repeatable binary builds.
    python = venv_python(root)
    if not python.exists():
        # Include system site packages so distro python-dbus can remain available.
        subprocess.check_call(
            [sys.executable, "-m", "venv", "--system-site-packages", str(root / ".venv")],
            cwd=root,
        )

    # Install the project and PyInstaller build extras when needed.
    if not has_pyinstaller(python):
        env = os.environ.copy()
        env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
        subprocess.check_call(
            [str(python), "-m", "pip", "install", "--no-build-isolation", "-e", f"{root}[build]"],
            cwd=root,
            env=env,
        )

    # Re-run this script inside the prepared environment.
    return subprocess.call([str(python), str(root / "scripts" / "build_binary.py"), "--no-bootstrap"], cwd=root)


######################
### BUILD SCRIPT ###
######################

def main(argv: list[str] | None = None) -> int:
    # Define build script flags.
    parser = argparse.ArgumentParser(description="Build a single-file MPRIS Bridge binary.")
    parser.add_argument(
        "--no-bootstrap",
        action="store_true",
        help="Build with the current Python environment instead of creating .venv.",
    )
    args = parser.parse_args(argv)

    # Project root is one directory above scripts.
    root = Path(__file__).resolve().parents[1]
    # Create or reuse a build environment unless disabled.
    if not args.no_bootstrap and not in_venv():
        return ensure_build_environment(root)

    # Fail early with a clear message if PyInstaller is not available.
    if importlib.util.find_spec("PyInstaller") is None:
        print('PyInstaller is not installed. Run: python scripts/build_binary.py')
        return 1

    # PyInstaller reads mpris-bridge.spec for build configuration.
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--clean",
        "--noconfirm",
        str(root / "mpris-bridge.spec"),
    ]
    subprocess.check_call(command, cwd=root)
    # Print the binary path for humans and release scripts.
    print(f"Built {root / 'dist' / 'mpris-bridge'}")
    return 0


if __name__ == "__main__":
    # Convert the script return code into the process exit code.
    raise SystemExit(main())
