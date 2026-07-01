from __future__ import annotations

import argparse
import importlib.util
import os
import subprocess
import sys
from pathlib import Path


def has_pyinstaller(python: Path) -> bool:
    result = subprocess.run(
        [str(python), "-c", "import PyInstaller"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def in_venv() -> bool:
    return sys.prefix != sys.base_prefix


def venv_python(root: Path) -> Path:
    return root / ".venv" / "bin" / "python"


def ensure_build_environment(root: Path) -> int:
    python = venv_python(root)
    if not python.exists():
        subprocess.check_call(
            [sys.executable, "-m", "venv", "--system-site-packages", str(root / ".venv")],
            cwd=root,
        )

    if not has_pyinstaller(python):
        env = os.environ.copy()
        env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
        subprocess.check_call(
            [str(python), "-m", "pip", "install", "--no-build-isolation", "-e", f"{root}[build]"],
            cwd=root,
            env=env,
        )

    return subprocess.call([str(python), str(root / "scripts" / "build_binary.py"), "--no-bootstrap"], cwd=root)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a single-file MPRIS Bridge binary.")
    parser.add_argument(
        "--no-bootstrap",
        action="store_true",
        help="Build with the current Python environment instead of creating .venv.",
    )
    args = parser.parse_args(argv)

    root = Path(__file__).resolve().parents[1]
    if not args.no_bootstrap and not in_venv():
        return ensure_build_environment(root)

    if importlib.util.find_spec("PyInstaller") is None:
        print('PyInstaller is not installed. Run: python scripts/build_binary.py')
        return 1

    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--clean",
        "--noconfirm",
        str(root / "mpris-bridge.spec"),
    ]
    subprocess.check_call(command, cwd=root)
    print(f"Built {root / 'dist' / 'mpris-bridge'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
