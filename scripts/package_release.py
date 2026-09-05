#!/usr/bin/env python3
"""
Release Packaging Script for Minecraft Desktop — Universal 1-Click Native Edition.
Assembles zero-installer, single-click distribution bundle and compressed archives
for Windows, Linux, and macOS.

Usage:
    python scripts/package_release.py [--build-dir PATH] [--dist-dir PATH]
                                      [--executable NAME] [--assets-dir PATH]
                                      [--target-name TARGET] [--archive {none,zip,tar.gz,auto}]
                                      [--clean]

Layout produced:
    <dist_dir>/minecraft-desktop/
    ├── <executable>           (minecraft.exe or minecraft)
    ├── assets/                (Resource assets copied from --assets-dir)
    ├── saves/                 (Default empty world saves folder)
    └── README.txt             (1-minute quickstart guide)
"""

# ponytail: local python packaging script copies file tree -> single-file self-extracting SFX archive or embedded virtual filesystem

import argparse
import os
import platform
import shutil
import sys
import tarfile
import zipfile
from pathlib import Path


CANONICAL_README = """==================================================
MINECRAFT DESKTOP - UNIVERSAL 1-CLICK EDITION
==================================================
1. Extract this entire folder anywhere you want.
2. Double-click the executable to launch.
3. Save files and settings will be stored in ./saves/
4. Zero installation or internet required. Enjoy!
==================================================
"""


def detect_target_name() -> str:
    """Detect default target-name from current host platform."""
    system = platform.system().lower()
    machine = platform.machine().lower()
    if system == "windows":
        return "windows-x64" if "64" in machine else "windows-x86"
    elif system == "linux":
        return "linux-x64" if "64" in machine else "linux-x86"
    elif system == "darwin":
        return "macos-universal"
    return f"{system}-{machine}"


def detect_executable_name(build_dir: str, preferred: str = None) -> str:
    """Find the best available executable in build_dir."""
    if preferred:
        return preferred

    system = platform.system().lower()
    candidates = []
    if system == "windows":
        candidates = ["minecraft.exe", "minecraft_headless.exe", "minecraft"]
    else:
        candidates = ["minecraft", "minecraft_headless", "minecraft.exe", "minecraft_headless.exe"]

    for name in candidates:
        if os.path.exists(os.path.join(build_dir, name)):
            return name

    # Default fallback if nothing built yet
    return "minecraft.exe" if system == "windows" else "minecraft"


def assemble_bundle(
    build_dir: str,
    dist_dir: str,
    executable_name: str,
    assets_dir: str,
    clean: bool = False,
    allow_missing_executable: bool = False
) -> Path:
    """
    Assemble the canonical release directory structure inside dist_dir/minecraft-desktop.
    """
    dist_path = Path(dist_dir)
    bundle_dir = dist_path / "minecraft-desktop"

    if clean and bundle_dir.exists():
        print(f"[CLEAN] Removing existing bundle directory: {bundle_dir}")
        shutil.rmtree(bundle_dir)

    bundle_dir.mkdir(parents=True, exist_ok=True)

    # 1. Copy or verify executable
    src_exe = Path(build_dir) / executable_name
    dest_exe = bundle_dir / executable_name

    if src_exe.is_file():
        print(f"[COPY] Executable: {src_exe} -> {dest_exe}")
        shutil.copy2(src_exe, dest_exe)
        # Ensure executable permissions on POSIX
        if os.name != "nt":
            dest_exe.chmod(0o755)
    else:
        if allow_missing_executable:
            print(f"[WARN] Executable {src_exe} not found. Creating placeholder for packaging dry-run.")
            dest_exe.write_text("// placeholder executable for verification\n", encoding="utf-8")
        else:
            raise FileNotFoundError(
                f"Executable not found at {src_exe}. Compile the engine before packaging or specify --allow-missing-exe."
            )

    # 2. Copy or create assets/ directory
    dest_assets = bundle_dir / "assets"
    src_assets = Path(assets_dir)
    if src_assets.is_dir():
        print(f"[COPY] Assets directory: {src_assets} -> {dest_assets}")
        if dest_assets.exists():
            shutil.rmtree(dest_assets)
        shutil.copytree(src_assets, dest_assets)
    else:
        print(f"[INIT] Creating empty assets directory: {dest_assets}")
        dest_assets.mkdir(parents=True, exist_ok=True)

    # 3. Create empty saves/ directory
    dest_saves = bundle_dir / "saves"
    print(f"[INIT] Creating portable saves directory: {dest_saves}")
    dest_saves.mkdir(parents=True, exist_ok=True)

    # 4. Write canonical README.txt
    dest_readme = bundle_dir / "README.txt"
    print(f"[WRITE] Canonical README: {dest_readme}")
    dest_readme.write_text(CANONICAL_README, encoding="utf-8")

    return bundle_dir


def create_archive(
    dist_dir: str,
    bundle_dir: Path,
    target_name: str,
    archive_format: str,
    archive_name: str = None
) -> Path:
    """
    Compress the assembled minecraft-desktop directory into release archive (.zip or .tar.gz).
    """
    dist_path = Path(dist_dir)
    if archive_format == "auto":
        archive_format = "tar.gz" if "linux" in target_name else "zip"

    if archive_name:
        out_name = archive_name
    else:
        ext = ".tar.gz" if archive_format == "tar.gz" else ".zip"
        out_name = f"minecraft-desktop-{target_name}{ext}"

    out_file = dist_path.parent / out_name if dist_path.name == "dist" else dist_path / out_name

    print(f"[ARCHIVE] Packaging {bundle_dir} into {out_file} (format: {archive_format})...")

    if archive_format == "zip":
        with zipfile.ZipFile(out_file, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(bundle_dir):
                for file in files:
                    full_path = Path(root) / file
                    arcname = full_path.relative_to(bundle_dir.parent)
                    zf.write(full_path, arcname)
    elif archive_format == "tar.gz":
        with tarfile.open(out_file, "w:gz") as tf:
            tf.add(bundle_dir, arcname=bundle_dir.name)
    else:
        raise ValueError(f"Unsupported archive format: {archive_format}")

    print(f"[SUCCESS] Archive generated: {out_file} ({out_file.stat().st_size} bytes)")
    return out_file


def main():
    parser = argparse.ArgumentParser(
        description="Minecraft Desktop Universal Single-Click Release Packager",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--build-dir",
        default="build",
        help="Path to directory containing compiled binaries (default: build)"
    )
    parser.add_argument(
        "--dist-dir",
        default="dist",
        help="Path to destination distribution staging directory (default: dist)"
    )
    parser.add_argument(
        "--executable",
        default=None,
        help="Name of compiled executable (default: auto-detect)"
    )
    parser.add_argument(
        "--assets-dir",
        default="assets",
        help="Path to game assets directory (default: assets)"
    )
    parser.add_argument(
        "--target-name",
        default=None,
        help="Target platform identifier, e.g. windows-x64 (default: auto-detect)"
    )
    parser.add_argument(
        "--archive",
        choices=["none", "zip", "tar.gz", "auto"],
        default="none",
        help="Create compressed archive package (default: none)"
    )
    parser.add_argument(
        "--archive-name",
        default=None,
        help="Override output archive filename"
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean distribution staging directory before assembling"
    )
    parser.add_argument(
        "--allow-missing-exe",
        action="store_true",
        help="Allow packaging without binary (creates placeholder for test validation)"
    )

    args = parser.parse_args()

    target_name = args.target_name or detect_target_name()
    executable_name = detect_executable_name(args.build_dir, args.executable)

    print(f"=== Assembling Minecraft Desktop Release Bundle [{target_name}] ===")
    bundle_dir = assemble_bundle(
        build_dir=args.build_dir,
        dist_dir=args.dist_dir,
        executable_name=executable_name,
        assets_dir=args.assets_dir,
        clean=args.clean,
        allow_missing_executable=args.allow_missing_exe
    )

    if args.archive != "none":
        create_archive(
            dist_dir=args.dist_dir,
            bundle_dir=bundle_dir,
            target_name=target_name,
            archive_format=args.archive,
            archive_name=args.archive_name
        )

    print("=== Release Assembly Complete ===")


if __name__ == "__main__":
    main()
