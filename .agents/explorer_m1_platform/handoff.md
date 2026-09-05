# Handoff Report: Milestone 1 Platform Layer Analysis & Design

**Author:** explorer_m1_platform  
**Recipient:** parent (`e598df24-3a79-45c8-8cc6-d95513d6c1f5`)  
**Type:** Hard Handoff  
**Date:** 2026-09-03  

---

## 1. Observation

1. **User Requirement R1 (`ORIGINAL_REQUEST.md`, lines 12–17):**
   > "A completely portable, single-click executable pipeline requiring zero external dependencies (no separate Java runtime, no Python environment, no system DLL installations). When downloaded from a GitHub release into any folder, it runs immediately... Portable relative base-path resolver storing `./saves/` adjacent to binary."

2. **System Specification Contract (`.agents/orchestrator/PROJECT.md`, lines 130–152):**
   The ratified contract defines `PlatformConfig` with `windowWidth`, `windowHeight`, `title`, `targetFps60`, `headless`, and `StoragePaths` with `basePath`, `saveDir`, `isReadOnlyFallback`, along with `Platform_Init`, `Platform_Shutdown`, `Platform_ShouldClose`, `Platform_PollEvents`, `Platform_GetTime`, and `Platform_GetStoragePaths`.

3. **Packaging Specification on CWD Shortcut Bugs (`docs/05_GITHUB_PACKAGING_AND_CI.md`, lines 49–54):**
   > "When a user double-clicks an executable from a desktop shortcut or secondary drive, the Operating System's current working directory (CWD) is frequently set to the user's home folder (`C:\Users\<Name>` or `/home/<user>`), NOT the directory containing the binary. The engine must explicitly resolve its absolute base directory on launch."

4. **Dynamic Linker & Header Collision Hazard (`docs/05_GITHUB_PACKAGING_AND_CI.md`, lines 26–38 and Win32 Raylib standard behavior):**
   On Windows PE, standard Win32 headers collide with Raylib on identifiers `Rectangle`, `CloseWindow`, `ShowCursor`, and `DrawText`. Furthermore, Raylib's default exit key is `KEY_ESCAPE`, which terminates the application unless `SetExitKey(KEY_NULL)` is explicitly invoked.

5. **Headless Execution Need for E2E Testing (`.agents/test_writer_e2e/DISPATCH.md`, lines 21–24):**
   Automated testing requires running without a physical display server via `--headless` flag.

---

## 2. Logic Chain

1. **Step 1 (Base-Path Discovery):**
   From Observation 1 and 3, launching from a desktop shortcut or foreign shell causes CWD to point away from the executable directory. Calling native APIs (`GetModuleFileNameW` on Windows, `readlink("/proc/self/exe")` on Linux, and `_NSGetExecutablePath` with `realpath` on macOS) identifies the true physical executable binary path. Truncating the binary name and invoking `SetCurrentDirectoryW` / `chdir` locks CWD to the executable folder, eliminating shortcut CWD bugs across all desktop platforms.

2. **Step 2 (Reliable Write Testing & Storage Fallback):**
   From Observation 1 and 3, save data must be stored in `<BasePath>/saves/`. Standard permission checks like `access(path, W_OK)` are unreliable for NTFS permissions and write-protected media. Executing a **Canary File Write Test** (attempting to create `<CandidateSaveDir>/.write_test`, writing a test payload, and deleting it) decisively proves write capability. If this test fails, gracefully routing `saveDir` to `%TEMP%\minecraft_desktop\saves` (Windows) or `/tmp/minecraft_desktop/saves` (POSIX) and setting `isReadOnlyFallback = true` prevents game crashes on read-only media.

3. **Step 3 (Escape Key & Identifier Collision Mitigations):**
   From Observation 4, including `<windows.h>` alongside Raylib causes macro collision errors. Defining `WIN32_LEAN_AND_MEAN`, `NOGDI`, and `NOUSER` prior to `<windows.h>` and including platform headers prior to Raylib avoids compiler symbol collisions. Furthermore, calling `SetExitKey(KEY_NULL)` during window initialization prevents Raylib from abruptly closing the process when the user presses Escape (which is required for the Pause Menu).

4. **Step 4 (Headless Execution & High-Precision Timing):**
   From Observation 2 and 5, automated tests and CI environments lack display hardware. Supporting a `headless` flag in `PlatformConfig` allows `Platform_Init()` to bypass window creation, GL context setup, and audio devices, while keeping monotonic high-resolution timing (`timeBeginPeriod(1)` + `QueryPerformanceCounter` on Windows, `clock_gettime(CLOCK_MONOTONIC)` on POSIX) fully operational for deterministic physics updates.

5. **Step 5 (Interface Contract Formulation):**
   From Steps 1–4, designing `src/platform/platform.h` with decoupled key codes, mouse state polling, cursor locking, storage path queries, and headless checks provides a clean abstraction with zero runtime heap allocation.

---

## 3. Caveats

1. **Raylib Static Library Linking:** The platform implementation assumes Raylib 5.x is statically linked as specified in `docs/05`. If compiled with `-DHEADLESS_ONLY`, Raylib headers are omitted entirely.
2. **Long Paths on Windows (>260 characters):** Modern Windows 10/11 supports extended paths if enabled in registry; using 1024-character wide buffers in `GetModuleFileNameW` accommodates deeply nested user directories.

---

## 4. Conclusion

The design for Milestone 1 Platform Layer is fully specified in `analysis.md`. The concrete interface `src/platform/platform.h` and implementation architecture `src/platform/platform_desktop.c`:
- Completely solve the shortcut CWD bug via native binary path discovery.
- Implement reliable canary-tested save storage with temporary directory fallback.
- Provide high-resolution timing, input polling, cursor locking, and headless execution.
- Incur **0 bytes** of heap allocation in the game loop.

---

## 5. Verification Method

1. **Verify Interface Contract Completeness:**
   Inspect `g:/minecraft_desktop/.agents/explorer_m1_platform/analysis.md` Section 5 (`platform.h`) and Section 6 (`platform_desktop.c`).
2. **Verify Base-Path Algorithm:**
   Confirm that `GetModuleFileNameW` uses `SetCurrentDirectoryW` with wide strings for Unicode path support, and `/proc/self/exe` uses `readlink` + `chdir`.
3. **Verify Canary Test Logic:**
   Confirm that write validation uses `fopen` on `.write_test`, writes test bytes, closes, and removes the file, falling back to `%TEMP%` or `/tmp` on failure.
4. **Verify Headless Operation:**
   Confirm that when `config.headless == true`, `InitWindow` is bypassed, `Platform_ShouldClose` is manageable programmatically, and `Platform_GetTime` functions autonomously.
