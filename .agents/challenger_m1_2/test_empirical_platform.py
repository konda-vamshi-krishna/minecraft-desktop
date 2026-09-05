"""
Empirical Challenger Test Suite for Milestone 1: Platform & Storage Layer
Tests:
1. Base-path resolution edge cases (spaces, deep subdirectories, root drives, Unicode)
2. Canary write probe and temp fallback in read-only environments
3. Multi-level directory creation bug in fallback logic
4. Unicode handling in Windows fopen canary probe
"""

import os
import sys
import tempfile
import shutil
import ctypes
from ctypes import wintypes

kernel32 = ctypes.windll.kernel32

def test_win32_create_dir_multilevel():
    """
    Test if CreateDirectoryW succeeds when creating 'minecraft_desktop\\saves'
    if the parent 'minecraft_desktop' does NOT exist.
    """
    temp_base = tempfile.gettempdir()
    probe_parent = os.path.join(temp_base, "m1_test_parent_probe")
    probe_child = os.path.join(probe_parent, "saves")

    # Ensure probe_parent does not exist
    if os.path.exists(probe_parent):
        shutil.rmtree(probe_parent, ignore_errors=True)

    # Now call CreateDirectoryW on probe_child directly (as platform_desktop.c does)
    res = kernel32.CreateDirectoryW(probe_child, None)
    err = kernel32.GetLastError()

    print(f"[TEST 1] CreateDirectoryW('{probe_child}'): Result={res}, LastError={err}")
    # ERROR_PATH_NOT_FOUND is 3
    if not res and err == 3:
        print("  -> BUG CONFIRMED: CreateDirectoryW fails with ERROR_PATH_NOT_FOUND (3) when intermediate parent does not exist!")
        return False
    elif res:
        print("  -> CreateDirectoryW unexpectedly succeeded")
        shutil.rmtree(probe_parent, ignore_errors=True)
        return True
    else:
        print(f"  -> Failed with unexpected error {err}")
        return False

def test_root_drive_basepath_resolution():
    """
    Test what happens if the binary path is at the root of a drive, e.g., 'C:\\minecraft.exe'.
    Simulate the C code:
    wchar_t* lastSlash = wcsrchr(widePath, L'\\');
    *lastSlash = L'\\0';
    SetCurrentDirectoryW(widePath);
    snprintf(candidateSaveDir, ..., "%s\\saves", basePath);
    """
    simulated_exe = r"C:\minecraft.exe"
    # wcsrchr finds the slash at index 2
    idx = simulated_exe.rfind('\\')
    base_path = simulated_exe[:idx]
    print(f"[TEST 2] Root drive base-path simulation for '{simulated_exe}':")
    print(f"  Base path after stripping slash: '{base_path}'")

    # In Win32, SetCurrentDirectoryW('C:') vs SetCurrentDirectoryW('C:\\')
    cur_dir_buf = ctypes.create_unicode_buffer(1024)
    kernel32.GetCurrentDirectoryW(1024, cur_dir_buf)
    orig_dir = cur_dir_buf.value
    print(f"  Original current directory: {orig_dir}")

    # What happens when SetCurrentDirectoryW is passed 'C:'?
    drive_letter = orig_dir[:2]  # e.g. 'G:'
    res = kernel32.SetCurrentDirectoryW(drive_letter)
    kernel32.GetCurrentDirectoryW(1024, cur_dir_buf)
    after_set_drive = cur_dir_buf.value
    print(f"  SetCurrentDirectoryW('{drive_letter}'): Result={res}, Current Dir is now: '{after_set_drive}'")

    # Now what if we pass 'G:\\'?
    kernel32.SetCurrentDirectoryW(drive_letter + "\\")
    kernel32.GetCurrentDirectoryW(1024, cur_dir_buf)
    after_set_root = cur_dir_buf.value
    print(f"  SetCurrentDirectoryW('{drive_letter}\\\\'): Current Dir is now: '{after_set_root}'")

    # Restore original directory
    kernel32.SetCurrentDirectoryW(orig_dir)

    # Candidate save dir:
    candidate_save_dir = f"{base_path}\\saves"
    print(f"  Candidate save dir: '{candidate_save_dir}'")
    if base_path == drive_letter:
        print("  -> NOTICE: Base path is 'C:' without trailing slash. While 'C:\\saves' forms 'C:\\saves',")
        print("     passing 'C:' to SetCurrentDirectory does NOT set root directory C:\\ but keeps previous drive CWD!")

def test_unicode_paths_and_fopen_probe():
    """
    Test canary probe with Unicode directory names outside system ANSI codepage.
    Simulate fopen(canary, 'wb') vs _wfopen on Windows.
    """
    temp_dir = tempfile.mkdtemp(prefix="m1_unicode_测试_")
    canary = os.path.join(temp_dir, ".write_test")

    safe_dir_repr = temp_dir.encode('ascii', 'backslashreplace').decode('ascii')
    print(f"[TEST 3] Testing Unicode directory canary probe in: '{safe_dir_repr}'")
    
    # Try creating with ANSI fopen (via ctypes msvcrt fopen)
    msvcrt = ctypes.cdll.msvcrt
    msvcrt.fopen.restype = ctypes.c_void_p
    msvcrt.fopen.argtypes = [ctypes.c_char_p, ctypes.c_char_p]

    # Convert UTF-8 bytes to pass to fopen
    utf8_canary = canary.encode('utf-8')
    f_handle = msvcrt.fopen(utf8_canary, b"wb")
    
    if not f_handle:
        print("  -> BUG CONFIRMED: msvcrt fopen() FAILS with UTF-8 path containing non-ANSI characters!")
        print("     Because platform_desktop.c uses fopen(canary, 'wb') with UTF-8 dirPath instead of _wfopen,")
        print("     the canary probe FAILS on Unicode directories, falsely claiming directory is read-only!")
        shutil.rmtree(temp_dir, ignore_errors=True)
        return False
    else:
        print("  -> msvcrt fopen succeeded")
        msvcrt.fclose(f_handle)
        if os.path.exists(canary):
            os.remove(canary)
        shutil.rmtree(temp_dir, ignore_errors=True)
        return True

def test_deep_path_resolution():
    """
    Test path resolution behavior when path exceeds MAX_PATH (260) or PLATFORM_PATH_MAX (1024).
    """
    print("[TEST 4] Testing Deep Subdirectory Path Bounds...")
    long_path = "C:\\" + "\\".join(["sub_" + str(i) for i in range(50)]) + "\\minecraft.exe"
    print(f"  Simulated long path length: {len(long_path)} characters")
    if len(long_path) > 260:
        print("  Path exceeds standard Windows MAX_PATH (260).")
    if len(long_path) < 1024:
        print("  Path fits within PLATFORM_PATH_MAX (1024).")
    
    excessive_path = "C:\\" + "a" * 1050 + "\\minecraft.exe"
    print(f"  Excessive path length: {len(excessive_path)} characters (exceeds PLATFORM_PATH_MAX 1024)")
    print("  In platform_desktop.c line 109:")
    print("  len >= (sizeof(widePath)/sizeof(widePath[0])) returns false -> falls back to '.'")

if __name__ == "__main__":
    print("=== Empirical Platform & Storage Stress Harness ===")
    test_win32_create_dir_multilevel()
    print("-" * 50)
    test_root_drive_basepath_resolution()
    print("-" * 50)
    test_unicode_paths_and_fopen_probe()
    print("-" * 50)
    test_deep_path_resolution()
