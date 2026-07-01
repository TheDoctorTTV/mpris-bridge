from __future__ import annotations

#################
### IMPORTS ###
#################

import argparse
import platform
import shutil
import stat
import subprocess
import sys
import zipfile
from pathlib import Path


###########################
### VERSION LOADING ###
###########################

def project_version(root: Path) -> str:
    # Read the package version from the package metadata file.
    init_file = root / "src" / "mpris_bridge" / "__init__.py"
    namespace: dict[str, str] = {}
    # Execute the small metadata file so the release version stays in one place.
    exec(init_file.read_text(encoding="utf-8"), namespace)
    return namespace["APP_VERSION"]


############################
### FILE HELPERS ###
############################

def make_executable(path: Path) -> None:
    # Preserve existing mode bits and add executable bits for user, group, and other.
    mode = path.stat().st_mode
    path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def copy_file(source: Path, target: Path, executable: bool = False) -> None:
    # Ensure the destination directory exists before copying.
    target.parent.mkdir(parents=True, exist_ok=True)
    # copy2 preserves metadata like modification time.
    shutil.copy2(source, target)
    if executable:
        make_executable(target)


##########################
### BUILD AND ZIP ###
##########################

def build_binary(root: Path) -> None:
    # Delegate binary creation to the dedicated build script.
    subprocess.check_call([sys.executable, str(root / "scripts" / "build_binary.py")], cwd=root)


def create_zip(source_dir: Path, zip_path: Path) -> None:
    # Replace an existing archive so releases are not appended to old zips.
    if zip_path.exists():
        zip_path.unlink()

    # Store all files relative to the release build directory.
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(source_dir.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(source_dir.parent))


##########################
### RELEASE SCRIPT ###
##########################

def main(argv: list[str] | None = None) -> int:
    # Project root is one directory above scripts.
    root = Path(__file__).resolve().parents[1]
    # Default release version follows the package version.
    version = project_version(root)
    # Include the current CPU architecture in the archive name.
    machine = platform.machine() or "unknown"

    # Define release packaging flags.
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

    # Build the binary unless the caller wants to package an existing one.
    if not args.skip_build:
        build_binary(root)

    # Refuse to package without the expected binary.
    binary = root / "dist" / "mpris-bridge"
    if not binary.exists():
        print("Missing dist/mpris-bridge. Run python scripts/build_binary.py first.", file=sys.stderr)
        return 1

    # Create a fresh staging directory for the release contents.
    package_name = f"mpris-bridge-{args.version}-linux-{machine}"
    staging = root / "build" / "release" / package_name
    if staging.exists():
        shutil.rmtree(staging)

    # Copy runtime files and user install helpers into the staging tree.
    copy_file(binary, staging / "bin" / "mpris-bridge", executable=True)
    copy_file(root / "settings.ini", staging / "settings.ini")
    copy_file(root / "README.md", staging / "README.md")
    copy_file(root / "systemd" / "mpris-bridge.service", staging / "systemd" / "mpris-bridge.service")
    copy_file(root / "scripts" / "install_systemd_user.sh", staging / "install_systemd_user.sh", executable=True)
    copy_file(root / "scripts" / "uninstall_systemd_user.sh", staging / "uninstall_systemd_user.sh", executable=True)

    # Write the final zip archive.
    args.output_dir.mkdir(parents=True, exist_ok=True)
    zip_path = args.output_dir / f"{package_name}.zip"
    create_zip(staging, zip_path)
    # Print the archive path for humans and CI logs.
    print(f"Packaged {zip_path}")
    return 0


if __name__ == "__main__":
    # Convert the script return code into the process exit code.
    raise SystemExit(main())
