"""
Empirical Challenger Test Suite: Canary Probe & Read-Only Fallback
Tests:
1. Canary probe write and removal on normal writable directories
2. Canary probe detection on genuinely write-denied (read-only) directories via ACLs
3. Fallback directory path resolution and existence validation
4. Multi-level directory creation failure in fallback path
5. Non-removal / file locking edge cases
"""

import os
import sys
import tempfile
import shutil
import subprocess
import ctypes

kernel32 = ctypes.windll.kernel32

def test_canary_writable_dir():
    temp_dir = tempfile.mkdtemp(prefix="m1_writable_")
    canary = os.path.join(temp_dir, ".write_test")
    try:
        # Simulate Platform_TestDirWritable
        with open(canary, "wb") as f:
            f.write(b"minecraft_desktop_write_probe\n")
        assert os.path.exists(canary), "Canary file must exist before removal"
        os.remove(canary)
        assert not os.path.exists(canary), "Canary file must be removed"
        print("[PASS] Test 1: Normal writable directory canary probe works")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

def test_canary_readonly_acl_dir():
    temp_dir = tempfile.mkdtemp(prefix="m1_readonly_acl_")
    canary = os.path.join(temp_dir, ".write_test")
    try:
        # Deny write permission on Windows using icacls
        subprocess.run(["icacls", temp_dir, "/deny", "Everyone:(W)"], 
                       capture_output=True, check=True)
        
        # Test if canary write fails
        write_failed = False
        try:
            with open(canary, "wb") as f:
                f.write(b"test\n")
        except PermissionError:
            write_failed = True
        
        assert write_failed, "Canary write MUST fail on write-denied directory"
        print("[PASS] Test 2: Canary probe detects read-only directory via PermissionError")

        # Now test fallback directory logic:
        # On fallback, platform_desktop.c does:
        # snprintf(outTempSaveDir, maxLen, "%s\\minecraft_desktop\\saves", tempUtf8);
        # Platform_CreateDir(tempSaveDir);
        temp_base = tempfile.gettempdir()
        temp_save_dir = os.path.join(temp_base, "minecraft_desktop", "saves")
        parent_dir = os.path.join(temp_base, "minecraft_desktop")

        # Clean up prior test artifacts if any
        if os.path.exists(parent_dir):
            shutil.rmtree(parent_dir, ignore_errors=True)

        # Call CreateDirectoryW on temp_save_dir
        res = kernel32.CreateDirectoryW(temp_save_dir, None)
        err = kernel32.GetLastError()
        print(f"  Fallback CreateDirectoryW('{temp_save_dir}'): Result={res}, LastError={err}")
        if not res and err == 3:
            print("  -> CONFIRMED BUG: Fallback directory creation fails (ERROR_PATH_NOT_FOUND = 3) because intermediate parent directory 'minecraft_desktop' was not created first!")
            fallback_created = False
        else:
            fallback_created = bool(res) or os.path.exists(temp_save_dir)

        assert not fallback_created, "Empirically verified that CreateDirectoryW fails on two-level path without parent"

    finally:
        # Restore ACL so directory can be cleaned up
        subprocess.run(["icacls", temp_dir, "/remove:d", "Everyone"], 
                       capture_output=True)
        shutil.rmtree(temp_dir, ignore_errors=True)

def test_canary_locked_removal_failure():
    """
    Test what happens if the canary file is opened by another process (e.g. AV scanner)
    when remove(canary) is called.
    """
    temp_dir = tempfile.mkdtemp(prefix="m1_locked_")
    canary = os.path.join(temp_dir, ".write_test")
    try:
        # Open file and keep handle open (simulating AV scanner holding handle)
        f1 = open(canary, "wb")
        f1.write(b"probe\n")
        f1.flush()

        # Try to remove while locked:
        remove_failed = False
        try:
            os.remove(canary)
        except OSError:
            remove_failed = True
        
        f1.close()
        print(f"[TEST 3] Canary removal under file lock: remove_failed={remove_failed}")
        if remove_failed:
            print("  In platform_desktop.c lines 100-102:")
            print("    fclose(f);")
            print("    remove(canary);")
            print("    return (written == strlen(testData));")
            print("  -> VULNERABILITY/DEFECT: If remove(canary) fails, return code of remove() is IGNORED,")
            print("     leaving orphaned .write_test in the player's saves directory!")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    print("=== Empirical Canary Probe & Fallback Stress Suite ===")
    test_canary_writable_dir()
    print("-" * 50)
    test_canary_readonly_acl_dir()
    print("-" * 50)
    test_canary_locked_removal_failure()
