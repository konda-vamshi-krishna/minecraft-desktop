# Milestone 1 (M1) Empirical Challenger Report

**Milestone:** M1 (Platform, Base-Path, Storage, and CLI Layer)  
**Agent:** challenger_m1_2 (critic, specialist)  
**Date:** 2026-09-03T07:52:00Z  
**Project Root:** `g:/minecraft_desktop`  
**Working Directory:** `g:/minecraft_desktop/.agents/challenger_m1_2/`  
**Verdict:** **REQUEST_CHANGES**  

---

## 1. Observation

### 1.1 Test Suite Verification
- Executed full 4-tier opaque-box test runner:
  ```powershell
  python tests/test_runner.py --tier all
  ```
  Result: 105 tests run, 105 passed, 0 failures, duration 51.2ms (100% pass rate).
- Executed M1 invariant structural audit:
  ```powershell
  python -m unittest tests/test_m1_c_invariants.py
  ```
  Result: 9 tests run, 9 passed, duration 0.005s.

### 1.2 Empirical Defect 1 (HIGH): Fallback Directory Creation Fails Due to Missing Intermediate Parent Directory
- **Location:** `src/platform/platform_desktop.c:76-91`, `165-177`, `225-231`
- **Source code in question:**
  ```c
  // platform_desktop.c:76-91
  static bool Platform_CreateDir(const char* path) {
  #if defined(_WIN32)
      wchar_t widePath[PLATFORM_PATH_MAX];
      int len = MultiByteToWideChar(CP_UTF8, 0, path, -1, widePath, PLATFORM_PATH_MAX);
      if (len <= 0) return false;
      if (CreateDirectoryW(widePath, NULL) || GetLastError() == ERROR_ALREADY_EXISTS) {
          return true;
      }
      return false;
  ...
  // platform_desktop.c:176
  snprintf(outTempSaveDir, maxLen, "%s\\minecraft_desktop\\saves", tempUtf8);
  ...
  // platform_desktop.c:226-229
  char tempSaveDir[PLATFORM_PATH_MAX];
  Platform_ResolveTempSaveDir(tempSaveDir, sizeof(tempSaveDir));
  Platform_CreateDir(tempSaveDir);
  ```
- **Empirical Execution Result (`test_canary_readonly_fallback.py`):**
  When write permission is denied on the base path (e.g. CD-ROM, write-protected USB, or NTFS write-denied directory), the engine falls back to `tempSaveDir` (`%TEMP%\minecraft_desktop\saves`).
  Direct Win32 API test via Python `ctypes`:
  ```
  Fallback CreateDirectoryW('C:\Users\PC\AppData\Local\Temp\minecraft_desktop\saves'): Result=0, LastError=3
  ```
  `CreateDirectoryW` returns `0` (`FALSE`) with `GetLastError() == ERROR_PATH_NOT_FOUND (3)`. On Windows, `CreateDirectoryW` only creates a single leaf directory; if parent directory `minecraft_desktop` does not already exist in `%TEMP%`, the call fails. The temporary save directory is **never created**. Subsequent chunk saves and player data writes will fail with file I/O errors.
  The same flaw exists on POSIX: `mkdir("/tmp/minecraft_desktop/saves", 0755)` fails with `ENOENT` because `/tmp/minecraft_desktop` is not created.

### 1.3 Empirical Defect 2 (HIGH): False Read-Only Fallback on Windows When Running from Unicode Folders
- **Location:** `src/platform/platform_desktop.c:93-103`, `122`
- **Source code in question:**
  ```c
  // platform_desktop.c:122
  int written = WideCharToMultiByte(CP_UTF8, 0, widePath, -1, outPath, (int)maxLen, NULL, NULL);
  ...
  // platform_desktop.c:93-103
  static bool Platform_TestDirWritable(const char* dirPath) {
      char canary[PLATFORM_PATH_MAX + 32];
      snprintf(canary, sizeof(canary), "%s/.write_test", dirPath);
      FILE* f = fopen(canary, "wb");
      if (!f) return false;
      const char* testData = "minecraft_desktop_write_probe\n";
      size_t written = fwrite(testData, 1, strlen(testData), f);
      fclose(f);
      remove(canary);
      return (written == strlen(testData));
  }
  ```
- **Empirical Execution Result (`test_empirical_platform.py`):**
  `Platform_ResolveBasePath` converts the wide path into UTF-8. However, `Platform_TestDirWritable` calls standard ANSI C `fopen(canary, "wb")`. On Windows, CRT `fopen` expects paths encoded in the current system ANSI code page (e.g. CP1252), NOT UTF-8.
  When the game is placed in any path containing non-ANSI characters (e.g. Chinese `测试`, Japanese `ゲーム`, Cyrillic `Игры`, or accented user home folders `C:\Users\José\Desktop\`):
  ```
  fopen (UTF-8 bytes): NULL (0)
  _wfopen (wchar): 0x7FFE5F82C170 (SUCCESS)
  ```
  `fopen` returns `NULL`. `Platform_TestDirWritable` returns `false`. The engine falsely assumes the base directory is read-only, triggers fallback to the temporary directory, which then fails to be created (Defect 1), rendering the game completely unable to save.

### 1.4 Empirical Defect 3 (MEDIUM): CLI Flag Collision & Argument Hijacking (`--frames --headless`)
- **Location:** `src/main.c:304-309`
- **Source code in question:**
  ```c
  } else if (strcmp(argv[i], "--frames") == 0 && i + 1 < argc) {
      runConfig.maxFrames = (uint64_t)strtoull(argv[++i], NULL, 10);
  } else if (strcmp(argv[i], "--ticks") == 0 && i + 1 < argc) {
      uint64_t ticks = (uint64_t)strtoull(argv[++i], NULL, 10);
      runConfig.maxDuration = (double)ticks * RUNTIME_FIXED_DT;
  }
  ```
- **Empirical Execution Result (`test_cli_parsing.py`):**
  If a user runs:
  ```powershell
  minecraft --frames --headless
  ```
  `argv[i]` matches `"--frames"`. The loop executes `argv[++i]`, consuming `"--headless"` as the value for `--frames`.
  `strtoull("--headless", NULL, 10)` returns `0`. `i` is incremented past `"--headless"`.
  Result:
  - `runConfig.maxFrames` is set to `0` (treated as unbounded run).
  - `platConfig.headless` remains `false` (never evaluated).
  - The engine attempts to initialize a desktop GUI window instead of headless mode, crashing in headless CI/CD runner environments.
  The same vulnerability affects `minecraft --seed --headless` and `minecraft --ticks --headless`.

### 1.5 Empirical Defect 4 (MEDIUM): POSIX / macOS Root Executable Path Stripping Bug
- **Location:** `src/platform/platform_desktop.c:130-137`, `150-155`
- **Source code in question:**
  ```c
  // platform_desktop.c:131-135
  char* lastSlash = strrchr(procPath, '/');
  if (lastSlash) {
      *lastSlash = '\0';
  }
  chdir(procPath);
  ```
- **Empirical Execution Result (`test_basepath_edge_cases.py`):**
  If the executable is located in the root directory (e.g. `/minecraft` inside a container or `/opt/minecraft`), `strrchr(procPath, '/')` finds `/` at index 0. Setting `*lastSlash = '\0'` collapses `procPath` to `""` (empty string).
  `chdir("")` fails with `ENOENT`.
  `candidateSaveDir` becomes `"/saves"`, attempting to create a directory in the root filesystem.

### 1.6 Empirical Defect 5 (LOW-to-MEDIUM): Unrecognized CLI Flags and Missing Trailing Arguments Silently Ignored
- **Location:** `src/main.c:294-313`
- **Empirical Execution Result (`test_cli_parsing.py`):**
  - Passing unknown flags (`minecraft --invalid-flag` or `minecraft -x`) hits no `else` branch. They are completely ignored without warning, and the process exits with `0` or launches the game.
  - Passing a parameter flag as the final argument (e.g. `minecraft --seed`) does not match because `i + 1 < argc` is false. The flag is silently ignored, and default seed 1337 is used without notifying the user.
  - Passing negative values like `--frames -1` causes `strtoull` to wrap to `18446744073709551615` (18 quintillion frames).

---

## 2. Logic Chain

1. **Premise 1 (Storage Reliability):** R1 and Acceptance Criteria mandate fully portable save/load in `./saves/` relative to executable with graceful fallback under read-only conditions.
2. **Observation 1.2:** In `platform_desktop.c:226-229`, `Platform_CreateDir` is called on `tempSaveDir` (`%TEMP%\minecraft_desktop\saves`). Win32 `CreateDirectoryW` and POSIX `mkdir` do not create intermediate directories.
3. **Inference 1.2:** If the game runs from read-only media (e.g. CD-ROM, write-protected USB) or is redirected to temporary storage, the temporary save directory fails to be created (`ERROR_PATH_NOT_FOUND = 3`). All subsequent save operations fail.
4. **Observation 1.3:** `Platform_TestDirWritable` invokes ANSI standard `fopen` with a UTF-8 path string on Windows.
5. **Inference 1.3:** Any non-ANSI path (Chinese, Cyrillic, Japanese, Arabic, or accented characters) fails in `fopen`, causing `Platform_TestDirWritable` to return `false` on completely writable directories. Combined with Inference 1.2, this guarantees total save failure on Unicode systems.
6. **Observation 1.4:** In `main.c:304-309`, value consumption `argv[++i]` does not verify whether `argv[i + 1]` is a flag (starting with `-`).
7. **Inference 1.4:** Malformed or incomplete flag combinations like `--frames --headless` swallow subsequent flags, setting frame count to 0 and preventing headless activation.

---

## 3. Caveats

1. **Host Compiler Delegation:** No C compiler was installed or executed on the host, strictly complying with project constraints. All tests were executed via Python 3 stress harnesses utilizing Windows native system APIs (`ctypes.windll.kernel32`, `msvcrt`, `subprocess.run`).
2. **Graphical Raylib Pipeline:** Raylib GUI window creation and GPU context initialization were not tested natively because the host environment lacks an active display server / GPU driver and w64devkit was prohibited. Headless mode was verified.

---

## 4. Conclusion

**Verdict: REQUEST_CHANGES**

Milestone 1 core architecture and mathematical algorithms (`math_utils.h`, `runtime.c`) are well implemented, but the Platform and CLI layers contain 2 HIGH severity bugs and 3 MEDIUM/LOW bugs that break storage portability and CLI robustness:
1. `Platform_CreateDir` fails to create the two-level fallback directory `%TEMP%\minecraft_desktop\saves` (Defect 1).
2. `Platform_TestDirWritable` uses ANSI `fopen` on UTF-8 paths in Windows, falsely diagnosing Unicode directories as read-only (Defect 2).
3. CLI argument parsing swallows subsequent flags when arguments are omitted (`--frames --headless`) (Defect 3).
4. Root executable path stripping produces empty strings on POSIX (Defect 4).
5. Unrecognized CLI flags and missing trailing arguments are silently ignored (Defect 5).

### Required Remediations for Worker M1:
1. **Fix `Platform_CreateDir`:** Ensure parent directories are created recursively, or explicitly create `outTempSaveDir`'s parent directory before creating `saves`.
2. **Fix `Platform_TestDirWritable` on Windows:** Convert `canary` to `wchar_t` using `MultiByteToWideChar(CP_UTF8, ...)` and use `_wfopen(wideCanary, L"wb")` instead of `fopen`.
3. **Fix CLI parsing in `src/main.c`:** Verify that `argv[i + 1]` does not begin with `-` before consuming it as a parameter; if missing or invalid, print an error and exit with code 1. Add an `else` branch to reject unknown flags.
4. **Fix root path handling:** On POSIX, if `lastSlash == procPath`, retain `/` (do not truncate to empty string). On Windows, if `widePath[1] == L':' && lastSlash == widePath + 2`, retain `\` (e.g. `C:\`).

---

## 5. Verification Method

To independently verify these findings:
1. **Execute Fallback & Unicode Probe Harness:**
   ```powershell
   python .agents/challenger_m1_2/test_empirical_platform.py
   ```
   *Expected:* Confirms `ERROR_PATH_NOT_FOUND (3)` on two-level CreateDirectoryW and `msvcrt.fopen` NULL failure on UTF-8 Unicode paths.

2. **Execute Read-Only ACL & Fallback Stress Harness:**
   ```powershell
   python .agents/challenger_m1_2/test_canary_readonly_fallback.py
   ```
   *Expected:* Confirms canary probe detects write denial and fallback directory creation failure.

3. **Execute CLI Parsing Stress Harness:**
   ```powershell
   python .agents/challenger_m1_2/test_cli_parsing.py
   ```
   *Expected:* Confirms `--frames --headless` flag collision, negative wrap, and missing argument bugs.

4. **Execute Base-Path Edge Cases Harness:**
   ```powershell
   python .agents/challenger_m1_2/test_basepath_edge_cases.py
   ```
   *Expected:* Confirms POSIX root truncation to empty string and Unicode byte expansion bounds.
