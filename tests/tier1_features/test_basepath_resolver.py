"""
Tier 1: Base-Path Resolver & Portable Storage Policy Tests.
Verifies executable directory discovery, save path adjacency (<BasePath>/saves/),
path normalization, and read-only storage fallback semantics.
"""

import unittest
import os
import tempfile
import sys
from pathlib import Path


def resolve_base_path(executable_path: str) -> str:
    """Canonical base path resolution: extracts directory containing executable."""
    last_slash = max(executable_path.rfind('/'), executable_path.rfind('\\'))
    if last_slash != -1:
        return executable_path[:last_slash]
    return executable_path


def get_save_directory(base_path: str, is_writable: bool = True) -> tuple[str, bool]:
    """
    Returns (save_path, is_fallback).
    If base_path is writable, saves strictly to <base_path>/saves/.
    If base_path is read-only, falls back to tempdir/minecraft_saves/.
    """
    if is_writable:
        return os.path.join(base_path, "saves"), False
    else:
        fallback = os.path.join(tempfile.gettempdir(), "minecraft_desktop_saves")
        return fallback, True


class TestBasePathResolver(unittest.TestCase):

    def test_01_strip_executable_name_to_directory(self):
        """Verify stripping executable binary name yields clean parent directory."""
        win_path = r"C:\Games\MinecraftDesktop\minecraft.exe"
        self.assertEqual(resolve_base_path(win_path), r"C:\Games\MinecraftDesktop")

        linux_path = "/opt/minecraft/bin/minecraft-linux-x64"
        self.assertEqual(resolve_base_path(linux_path), "/opt/minecraft/bin")

    def test_02_saves_directory_strict_adjacency(self):
        """Verify save files are stored strictly adjacent to binary in ./saves/."""
        base = r"D:\PortableApps\Minecraft"
        save_dir, is_fallback = get_save_directory(base, is_writable=True)
        self.assertEqual(save_dir, os.path.join(base, "saves"))
        self.assertFalse(is_fallback)

    def test_03_paths_with_spaces_and_special_characters(self):
        """Verify paths containing spaces, accents, or symbols resolve without corruption."""
        complex_path = r"C:\My Games & Apps\Minecraft (Desktop v1.0)\game.exe"
        resolved = resolve_base_path(complex_path)
        self.assertEqual(resolved, r"C:\My Games & Apps\Minecraft (Desktop v1.0)")
        save_dir, _ = get_save_directory(resolved, is_writable=True)
        self.assertTrue(save_dir.endswith("saves"))

    def test_04_read_only_media_fallback(self):
        """Verify read-only base path activates graceful fallback to temporary directory."""
        read_only_base = r"E:\CDROM_Minecraft"
        save_dir, is_fallback = get_save_directory(read_only_base, is_writable=False)
        self.assertTrue(is_fallback)
        self.assertTrue(save_dir.startswith(tempfile.gettempdir()))
        self.assertIn("saves", save_dir)

    def test_05_cwd_independence_invariant(self):
        """Verify game resolves base path from executable location, NOT from current working directory."""
        original_cwd = os.getcwd()
        try:
            # Change CWD to tempdir
            os.chdir(tempfile.gettempdir())
            fake_exe = os.path.join(original_cwd, "fake_bin", "minecraft.exe")
            resolved = resolve_base_path(fake_exe)
            self.assertNotEqual(resolved, os.getcwd())
            self.assertEqual(resolved, os.path.join(original_cwd, "fake_bin"))
        finally:
            os.chdir(original_cwd)


if __name__ == '__main__':
    unittest.main()
