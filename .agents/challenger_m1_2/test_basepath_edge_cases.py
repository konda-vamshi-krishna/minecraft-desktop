"""
Empirical Challenger Test Suite: Base-Path Resolution Edge Cases
Stress tests simulated base-path resolution logic against:
1. Spaces in folder and file names
2. Deep subdirectories (approaching and exceeding MAX_PATH and PLATFORM_PATH_MAX)
3. Root drives (Windows C:\\, POSIX /, UNC network shares)
4. Full Unicode spectrum (CJK, Cyrillic, Arabic, Accents, Emoji)
"""

import os
import sys
import ctypes

PLATFORM_PATH_MAX = 1024

def simulate_c_resolve_base_path_win32(wide_path_str: str):
    """
    Simulates lines 106-123 of platform_desktop.c:
    wchar_t widePath[PLATFORM_PATH_MAX];
    DWORD len = GetModuleFileNameW(NULL, widePath, ...);
    if (len == 0 || len >= 1024) return false;
    wchar_t* lastSlash = wcsrchr(widePath, L'\\');
    wchar_t* lastForwardSlash = wcsrchr(widePath, L'/');
    if (lastForwardSlash && (!lastSlash || lastForwardSlash > lastSlash)) {
        lastSlash = lastForwardSlash;
    }
    if (lastSlash) {
        *lastSlash = L'\0';
    }
    SetCurrentDirectoryW(widePath);
    WideCharToMultiByte(CP_UTF8, 0, widePath, -1, outPath, (int)maxLen, NULL, NULL);
    """
    if len(wide_path_str) >= PLATFORM_PATH_MAX or len(wide_path_str) == 0:
        return None, False, "Length overflow or zero"

    # Find last backslash or forward slash
    last_slash = wide_path_str.rfind('\\')
    last_forward_slash = wide_path_str.rfind('/')
    cut_idx = max(last_slash, last_forward_slash)

    if cut_idx != -1:
        resolved_base = wide_path_str[:cut_idx]
    else:
        resolved_base = wide_path_str

    # In C, snprintf candidateSaveDir: "%s\\saves"
    candidate_save_dir = f"{resolved_base}\\saves"
    
    # Check if resolved_base can be converted to UTF-8 within PLATFORM_PATH_MAX bytes
    try:
        utf8_bytes = resolved_base.encode('utf-8')
        if len(utf8_bytes) >= PLATFORM_PATH_MAX:
            return resolved_base, False, f"UTF-8 encoded bytes ({len(utf8_bytes)}) exceed PLATFORM_PATH_MAX ({PLATFORM_PATH_MAX})"
    except UnicodeEncodeError as e:
        return resolved_base, False, f"Unicode conversion error: {e}"

    return resolved_base, candidate_save_dir, True


def simulate_c_resolve_base_path_posix(posix_path_str: str):
    """
    Simulates lines 124-138 of platform_desktop.c (Linux readlink):
    char procPath[PLATFORM_PATH_MAX];
    char* lastSlash = strrchr(procPath, '/');
    if (lastSlash) *lastSlash = '\0';
    chdir(procPath);
    strncpy(outPath, procPath, maxLen - 1);
    """
    if len(posix_path_str) >= PLATFORM_PATH_MAX or len(posix_path_str) == 0:
        return None, False, "Length overflow or zero"

    cut_idx = posix_path_str.rfind('/')
    if cut_idx != -1:
        resolved_base = posix_path_str[:cut_idx]
    else:
        resolved_base = posix_path_str

    candidate_save_dir = f"{resolved_base}/saves"
    return resolved_base, candidate_save_dir, True


def run_basepath_stress_tests():
    print("=== Base-Path Resolution Stress Tests ===")

    # 1. Spaces in path
    p1 = r"C:\Program Files\Minecraft Universal Edition\bin\minecraft.exe"
    base1, save1, ok1 = simulate_c_resolve_base_path_win32(p1)
    assert ok1 is True
    assert base1 == r"C:\Program Files\Minecraft Universal Edition\bin"
    assert save1 == r"C:\Program Files\Minecraft Universal Edition\bin\saves"
    print("[PASS] Case 1: Spaces in path handled correctly.")

    # 2. Deep subdirectories
    parts = ["dir_" + str(i).zfill(3) for i in range(40)]
    deep_path = "C:\\" + "\\".join(parts) + "\\minecraft.exe"
    print(f"Deep path length: {len(deep_path)} chars")
    base2, save2, ok2 = simulate_c_resolve_base_path_win32(deep_path)
    assert ok2 is True
    print(f"[PASS] Case 2a: Deep path within 1024 ({len(deep_path)} chars) handled.")

    # 2b. Exceeding PLATFORM_PATH_MAX
    excessive_parts = ["dir_" + str(i).zfill(4) for i in range(130)]
    overflow_path = "C:\\" + "\\".join(excessive_parts) + "\\minecraft.exe"
    print(f"Overflow path length: {len(overflow_path)} chars")
    base2b, ok2b, msg = simulate_c_resolve_base_path_win32(overflow_path)
    assert ok2b is False
    print(f"[PASS] Case 2b: Overflow beyond 1024 correctly rejected: {msg}")

    # 3. Root drives
    # 3a. Windows Root C:\minecraft.exe
    root_win = r"C:\minecraft.exe"
    base3a, save3a, ok3a = simulate_c_resolve_base_path_win32(root_win)
    print(f"[CASE 3a] Windows Root '{root_win}':")
    print(f"  basePath = '{base3a}'")
    print(f"  candidateSaveDir = '{save3a}'")
    if base3a == "C:":
        print("  -> BUG / EDGE CASE: basePath becomes 'C:' without trailing backslash.")
        print("     Passing 'C:' to SetCurrentDirectoryW does NOT change to root 'C:\\'.")

    # 3b. Linux Root /minecraft
    root_posix = "/minecraft"
    base3b, save3b, ok3b = simulate_c_resolve_base_path_posix(root_posix)
    print(f"[CASE 3b] Linux Root '{root_posix}':")
    print(f"  basePath = '{base3b}' (empty string!)")
    print(f"  candidateSaveDir = '{save3b}'")
    if base3b == "":
        print("  -> CRITICAL BUG: When binary is in root /minecraft, strrchr finds '/' at index 0,")
        print("     setting *lastSlash = '\\0' makes procPath an EMPTY STRING \"\"!")
        print("     chdir(\"\") FAILS with ENOENT, and candidateSaveDir becomes \"/saves\"!")

    # 3c. UNC Path
    unc_path = r"\\network_server\games_share\minecraft.exe"
    base3c, save3c, ok3c = simulate_c_resolve_base_path_win32(unc_path)
    print(f"[CASE 3c] UNC Share '{unc_path}':")
    print(f"  basePath = '{base3c}'")
    print(f"  candidateSaveDir = '{save3c}'")

    # 4. Unicode Characters
    unicode_cases = [
        ("Chinese", r"C:\游戏\我的世界\minecraft.exe"),
        ("Japanese", r"C:\ゲーム\マインクラフト\minecraft.exe"),
        ("Cyrillic", r"C:\Игры\Майнкрафт\minecraft.exe"),
        ("Arabic", r"C:\ألعاب\ماينكرافت\minecraft.exe"),
        ("Accents", r"C:\Jeux\Édition_Française\minecraft.exe"),
        ("Emoji", r"C:\Games\🎮Craft\minecraft.exe"),
    ]

    print("\n--- Testing Unicode Spectrum ---")
    for lang, upath in unicode_cases:
        base_u, save_u, ok_u = simulate_c_resolve_base_path_win32(upath)
        utf8_len = len(base_u.encode('utf-8'))
        wchar_len = len(base_u)
        print(f"[{lang}] WChars: {wchar_len}, UTF-8 bytes: {utf8_len}, OK: {ok_u}")
        assert ok_u is True

    # 4b. Unicode expansion buffer overflow
    # Suppose a path has 400 4-byte characters (emojis / CJK extension)
    extreme_unicode = "C:\\" + "🎮" * 300 + "\\minecraft.exe"
    print(f"\n[Extreme Unicode] Length in wchar: {len(extreme_unicode)}")
    base_ex, ok_ex, msg_ex = simulate_c_resolve_base_path_win32(extreme_unicode)
    print(f"  Result: ok={ok_ex}, msg={msg_ex}")
    if not ok_ex:
        print("  -> CONFIRMED: High-expansion Unicode characters (emoji/CJK) can fit within 1024 wchar_t")
        print("     but overflow the 1024 UTF-8 byte buffer during WideCharToMultiByte conversion!")


if __name__ == "__main__":
    run_basepath_stress_tests()
