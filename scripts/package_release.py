from __future__ import annotations

import argparse
import platform
import shutil
import stat
import subprocess
import sys
import zipfile
from pathlib import Path


def project_version(root: Path) -> str:
    init_file = root / "src" / "mpris_bridge" / "__init__.py"
    namespace: dict[str, str] = {}
    exec(init_file.read_text(encoding="utf-8"), namespace)
    return namespace["APP_VERSION"]


def make_executable(path: Path) -> None:
    mode = path.stat().st_mode
    path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def copy_file(source: Path, target: Path, executable: bool = False) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    if executable:
        make_executable(target)


def build_binary(root: Path) -> None:
    subprocess.check_call([sys.executable, str(root / "scripts" / "build_binary.py")], cwd=root)


def create_zip(source_dir: Path, zip_path: Path) -> None:
    if zip_path.exists():
        zip_path.unlink()

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(source_dir.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(source_dir.parent))


def main(argv: list[str] | None = None) -> int:
    root = Path(__file__).resolve().parents[1]
    version = project_version(root)
    machine = platform.machine() or "unknown"

    parser = argparse.ArgumentParser(description="Package MPRIS Bridge binary and systemd user service scripts.")
    parser.add_argument("--skip-build", action="store_true", help="Package the existing dist/mpris-bridge binary.")
    parser.add_argument("--version", default=version, help="Version string for the release archive name.")
    parser.add_argument(
        "--output-dir",
        default=root / "release",
        type=Path,
        help="Directory that receives the release zip.",
    )
    args = parser.parse_args(argv)

    if not args.skip_build:
        build_binary(root)

    binary = root / "dist" / "mpris-bridge"
    if not binary.exists():
        print("Missing dist/mpris-bridge. Run python scripts/build_binary.py first.", file=sys.stderr)
        return 1

    package_name = f"mpris-bridge-{args.version}-linux-{machine}"
    staging = root / "build" / "release" / package_name
    if staging.exists():
        shutil.rmtree(staging)

    copy_file(binary, staging / "bin" / "mpris-bridge", executable=True)
    copy_file(root / "settings.ini", staging / "settings.ini")
    copy_file(root / "README.md", staging / "README.md")
    copy_file(root / "systemd" / "mpris-bridge.service", staging / "systemd" / "mpris-bridge.service")
    copy_file(root / "scripts" / "install_systemd_user.sh", staging / "install_systemd_user.sh", executable=True)
    copy_file(root / "scripts" / "uninstall_systemd_user.sh", staging / "uninstall_systemd_user.sh", executable=True)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    zip_path = args.output_dir / f"{package_name}.zip"
    create_zip(staging, zip_path)
    print(f"Packaged {zip_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
