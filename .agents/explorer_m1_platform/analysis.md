# Architectural Analysis & Concrete Implementation Plan: M1 Platform Layer
**Subsystem:** Platform Layer (`src/platform/platform.h`, `src/platform/platform_desktop.c`)  
**Author:** explorer_m1_platform (Platform Architecture & OS Abstraction Specialist)  
**Methodology:** Ponytail Minimal-Complexity Engineering & Max-Pro Polymath Systems Audit  
**Date:** 2026-09-03  

---

## 1. Executive Summary & Problem Scope

The Platform Layer is the physical interface between host operating systems (Windows 7/10/11, Linux distributions, and macOS) and the deterministic Minecraft Desktop engine. In accordance with user requirement **R1 (Universal One-Click Native Distribution)** and documentation specifications in `docs/01_ARCHITECTURE_AND_RUNTIME.md` and `docs/05_GITHUB_PACKAGING_AND_CI.md`, the platform layer must ensure:

1. **Zero Shortcut CWD Bugs:** Operating systems launch executables with an arbitrary Current Working Directory (e.g. `%USERPROFILE%` via desktop shortcuts, or `/tmp` via terminal launchers). The engine must natively resolve its own physical executable binary directory and set the process CWD to that directory before performing any filesystem operations.
2. **Deterministic Portable Storage:** World saves and configurations must reside strictly in `<BasePath>/saves/`. If the launch location is read-only (e.g. CD-ROM, locked USB flash drive, or read-only network volume), the system must gracefully fall back to the host operating system's temporary directory without crashing or failing silently.
3. **Decoupled Windowing, Input, & Timer Subsystem:** A clean C99 contract abstracting display window management, input polling (mouse look delta, key states, cursor lock), high-resolution timing (`winmm timeBeginPeriod(1)` + `QueryPerformanceCounter` on Windows, `clock_gettime(CLOCK_MONOTONIC)` on POSIX), and headless execution flag (`--headless`).
4. **Zero Heap Allocation in Hot Loop:** All platform operations, events, and state queries must execute with **0 bytes** of dynamic heap allocation during runtime.

---

## 2. Platform-Native Base-Path Executable Resolution

### 2.1. The Root Cause of Shortcut CWD Failures
When an end-user creates a desktop shortcut on Windows, the `.lnk` file metadata dictates the initial Current Working Directory (CWD). If left blank or defaulted by the Windows shell, the CWD is set to `%USERPROFILE%` (`C:\Users\<Username>\`). Similarly, on Linux, launching via symlinks or desktop launchers from `/usr/bin` sets CWD to `/home/<user>/`.
If the engine calls `fopen("saves/world1.dat", "wb")`, relative file paths resolve against the operating system's CWD, resulting in:
- Polluting the user's home folder with game files.
- Inability to find adjacent game assets or existing save files.
- Permission errors if CWD is `System32` or root.

### 2.2. OS-Specific Resolution Matrix

| Operating System | Primary Platform API | Canonicalization Method | Fallback Strategy |
| :--- | :--- | :--- | :--- |
| **Windows (Win32)** | `GetModuleFileNameW(NULL, widePath, 1024)` | Scan backwards for `\` or `/`, truncate at separator, call `SetCurrentDirectoryW(wideDir)` | `argv[0]` via `GetCommandLineW` -> `SetCurrentDirectoryA(".")` |
| **Linux (POSIX)** | `readlink("/proc/self/exe", procPath, 1024)` | Scan backwards for `/`, truncate at separator, call `chdir(procPath)` | `realpath(argv[0])` or `"./"` |
| **macOS (Darwin)** | `_NSGetExecutablePath(applePath, &size)` | `realpath(applePath, resolvedPath)`, truncate at last `/`, call `chdir(resolvedPath)` | `getcwd()` or `"./"` |

### 2.3. Concrete Multi-Platform Base-Path Logic

```c
// Native Base Path Resolution across all desktop platforms
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>

#if defined(_WIN32)
    #define WIN32_LEAN_AND_MEAN
    #define NOGDI
    #define NOUSER
    #include <windows.h>
#elif defined(__linux__)
    #include <unistd.h>
    #include <linux/limits.h>
#elif defined(__APPLE__)
    #include <mach-o/dyld.h>
    #include <unistd.h>
    #include <sys/param.h>
#endif

static char g_BasePath[1024] = {0};

static bool Platform_ResolveBasePath(char* outPath, size_t maxLen) {
#if defined(_WIN32)
    wchar_t widePath[1024];
    DWORD len = GetModuleFileNameW(NULL, widePath, (DWORD)(sizeof(widePath) / sizeof(widePath[0])));
    if (len == 0 || len >= (sizeof(widePath) / sizeof(widePath[0]))) {
        return false;
    }
    // Find last path separator ('\\' or '/')
    wchar_t* lastSlash = wcsrchr(widePath, L'\\');
    wchar_t* lastForwardSlash = wcsrchr(widePath, L'/');
    if (lastForwardSlash && (!lastSlash || lastForwardSlash > lastSlash)) {
        lastSlash = lastForwardSlash;
    }
    if (lastSlash) {
        *lastSlash = L'\0'; // Strip binary filename, leaving directory without trailing slash
    }
    // Set current working directory using wide API to support non-ASCII/Unicode paths
    SetCurrentDirectoryW(widePath);

    // Convert UTF-16 directory to UTF-8
    int written = WideCharToMultiByte(CP_UTF8, 0, widePath, -1, outPath, (int)maxLen, NULL, NULL);
    return (written > 0);

#elif defined(__linux__)
    char procPath[1024];
    ssize_t len = readlink("/proc/self/exe", procPath, sizeof(procPath) - 1);
    if (len == -1) {
        return false;
    }
    procPath[len] = '\0';
    char* lastSlash = strrchr(procPath, '/');
    if (lastSlash) {
        *lastSlash = '\0';
    }
    chdir(procPath);
    strncpy(outPath, procPath, maxLen - 1);
    outPath[maxLen - 1] = '\0';
    return true;

#elif defined(__APPLE__)
    char applePath[1024];
    uint32_t size = sizeof(applePath);
    if (_NSGetExecutablePath(applePath, &size) != 0) {
        return false;
    }
    char resolvedPath[1024];
    if (realpath(applePath, resolvedPath) == NULL) {
        strncpy(resolvedPath, applePath, sizeof(resolvedPath) - 1);
        resolvedPath[sizeof(resolvedPath) - 1] = '\0';
    }
    char* lastSlash = strrchr(resolvedPath, '/');
    if (lastSlash) {
        *lastSlash = '\0';
    }
    chdir(resolvedPath);
    strncpy(outPath, resolvedPath, maxLen - 1);
    outPath[maxLen - 1] = '\0';
    return true;

#else
    strncpy(outPath, ".", maxLen - 1);
    outPath[maxLen - 1] = '\0';
    return true;
#endif
}
```

---

## 3. Portable Save Folder Resolution & Graceful Read-Only Fallback

### 3.1. Write Validation Contract & The Canary Test
Checking directory write permission using `access(path, W_OK)` or `_access()` is notoriously prone to false positives on modern OSs—it frequently evaluates file attributes while ignoring NTFS Discretionary Access Control Lists (DACLs), elevated integrity levels, or physical write-protection switches on flash media.

The **Canary File Write Test** is the gold standard for reliable runtime write validation:
1. Construct the target path `<CandidateSaveDir>/.write_test`.
2. Attempt `fopen(canaryPath, "wb")`.
3. If `fopen` returns `NULL`, write access is denied.
4. If `fopen` succeeds, write a small canary payload (`"ok\n"`), `fclose()`, and immediately delete the canary file using `remove(canaryPath)`.

### 3.2. Fallback Storage Path Derivation
If `<BasePath>/saves/` is write-locked (e.g. read-only optical disc, write-protected USB drive, shared school lab computer with locked drive permissions):
- **Windows Fallback:** `GetTempPathW()` $\to$ UTF-8 conversion $\to$ `%TEMP%\minecraft_desktop\saves\`.
- **Linux/macOS Fallback:** Environment `$TMPDIR`, `$TEMP`, `$TMP`, or `/tmp` $\to$ `/tmp/minecraft_desktop/saves/`.
- **Flagging:** Set `outPaths->isReadOnlyFallback = true`. The HUD subsystem renders an alert banner: `[WARNING] Storage media is read-only. World saved to temporary directory.`

```c
// Directory creation helper
#if defined(_WIN32)
    #include <direct.h>
    #include <io.h>
#else
    #include <sys/stat.h>
    #include <sys/types.h>
    #include <errno.h>
#endif

static bool Platform_CreateDir(const char* path) {
#if defined(_WIN32)
    wchar_t widePath[1024];
    WideCharToMultiByte(CP_UTF8, 0, widePath, -1, NULL, 0, NULL, NULL); // verify
    MultiByteToWideChar(CP_UTF8, 0, path, -1, widePath, 1024);
    if (CreateDirectoryW(widePath, NULL) || GetLastError() == ERROR_ALREADY_EXISTS) {
        return true;
    }
    return false;
#else
    if (mkdir(path, 0755) == 0 || errno == EEXIST) {
        return true;
    }
    return false;
#endif
}

static bool Platform_TestDirWritable(const char* dirPath) {
    char canary[1050];
    snprintf(canary, sizeof(canary), "%s/.write_test", dirPath);
    FILE* f = fopen(canary, "wb");
    if (!f) return false;
    const char* testData = "minecraft_desktop_write_probe\n";
    size_t written = fwrite(testData, 1, strlen(testData), f);
    fclose(f);
    remove(canary);
    return (written == strlen(testData));
}

static bool Platform_ResolveTempSaveDir(char* outTempSaveDir, size_t maxLen) {
#if defined(_WIN32)
    wchar_t wideTemp[1024];
    DWORD len = GetTempPathW(1024, wideTemp);
    if (len == 0 || len >= 1024) return false;
    char tempUtf8[1024];
    WideCharToMultiByte(CP_UTF8, 0, wideTemp, -1, tempUtf8, sizeof(tempUtf8), NULL, NULL);
    size_t slen = strlen(tempUtf8);
    if (slen > 0 && (tempUtf8[slen - 1] == '\\' || tempUtf8[slen - 1] == '/')) {
        tempUtf8[slen - 1] = '\0';
    }
    snprintf(outTempSaveDir, maxLen, "%s\\minecraft_desktop\\saves", tempUtf8);
    return true;
#else
    const char* tmp = getenv("TMPDIR");
    if (!tmp || tmp[0] == '\0') tmp = getenv("TEMP");
    if (!tmp || tmp[0] == '\0') tmp = getenv("TMP");
    if (!tmp || tmp[0] == '\0') tmp = "/tmp";
    snprintf(outTempSaveDir, maxLen, "%s/minecraft_desktop/saves", tmp);
    return true;
#endif
}
```

---

## 4. Windowing, Input Polling, High-Resolution Timer, and Headless Execution

### 4.1. Headless Execution Mode (`--headless`)
In automated CI runners (such as GitHub Actions Ubuntu/Windows runners without a display server) and automated E2E test suites (Tiers 1–4):
- The executable must execute without requiring an X11 display, Wayland socket, or physical desktop window.
- When `config.headless == true` or `--headless` CLI flag is passed:
  1. Window creation is bypassed entirely.
  2. Audio device initialization is bypassed.
  3. Frame drawing calls (`BeginDrawing`, `EndDrawing`) are no-ops.
  4. Platform timing (`Platform_GetTime`, `Platform_Sleep`) remains fully active.
  5. Deterministic game ticks can be stepped via command-line arguments (e.g. `--ticks 120`).

### 4.2. High-Resolution Timer Design
Standard Windows scheduler time slices are coarse (typically 15.6 ms). A game loop calling `Sleep(1)` without timer reconfiguration can stall for 16 ms, dropping framerates from 60 FPS down to 30–45 FPS.
- On Windows:
  - `Platform_Init()` invokes `timeBeginPeriod(1)` to force the kernel timer resolution to 1 ms.
  - Sub-millisecond timing uses `QueryPerformanceFrequency` and `QueryPerformanceCounter`.
  - `Platform_Shutdown()` calls `timeEndPeriod(1)`.
- On Linux / macOS:
  - Monotonic clock: `clock_gettime(CLOCK_MONOTONIC, &ts)` provides nanosecond precision unaffected by system wall-clock adjustments (NTP/leap seconds).

### 4.3. Input Polling & Cursor Management
- **Key States:** Continuous down, single-frame pressed, single-frame released.
- **Mouse Relative Motion:** Raw mouse delta (`dx`, `dy`) polled each frame for first-person Euler camera look.
- **Cursor Modes:**
  - Game camera active: `Platform_SetCursorCaptured(true)` $\to$ locks cursor, hides hardware pointer, yields relative delta.
  - Menus/Inventory: `Platform_SetCursorCaptured(false)` $\to$ unlocks cursor, reveals hardware pointer for UI interaction.
- **Escape Key Trap Mitigation:** In Raylib, `KEY_ESCAPE` terminates the window loop by default! The platform layer **must** call `SetExitKey(KEY_NULL)` during window initialization so `KEY_ESCAPE` cleanly opens the Pause Menu instead of crashing the process.

---

## 5. Interface Contract: `src/platform/platform.h`

```c
#ifndef PLATFORM_H
#define PLATFORM_H

#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

#define PLATFORM_PATH_MAX 1024
#define PLATFORM_DEFAULT_WINDOW_WIDTH 854
#define PLATFORM_DEFAULT_WINDOW_HEIGHT 480

// Key codes mapped directly to standard GLFW / Raylib key integer values
typedef enum {
    PLATFORM_KEY_UNKNOWN       = 0,
    PLATFORM_KEY_SPACE         = 32,
    PLATFORM_KEY_APOSTROPHE    = 39,
    PLATFORM_KEY_COMMA         = 44,
    PLATFORM_KEY_MINUS         = 45,
    PLATFORM_KEY_PERIOD        = 46,
    PLATFORM_KEY_SLASH         = 47,
    PLATFORM_KEY_0             = 48,
    PLATFORM_KEY_1             = 49,
    PLATFORM_KEY_2             = 50,
    PLATFORM_KEY_3             = 51,
    PLATFORM_KEY_4             = 52,
    PLATFORM_KEY_5             = 53,
    PLATFORM_KEY_6             = 54,
    PLATFORM_KEY_7             = 55,
    PLATFORM_KEY_8             = 56,
    PLATFORM_KEY_9             = 57,
    PLATFORM_KEY_SEMICOLON     = 59,
    PLATFORM_KEY_EQUAL         = 61,
    PLATFORM_KEY_A             = 65,
    PLATFORM_KEY_B             = 66,
    PLATFORM_KEY_C             = 67,
    PLATFORM_KEY_D             = 68,
    PLATFORM_KEY_E             = 69,
    PLATFORM_KEY_F             = 70,
    PLATFORM_KEY_G             = 71,
    PLATFORM_KEY_H             = 72,
    PLATFORM_KEY_I             = 73,
    PLATFORM_KEY_J             = 74,
    PLATFORM_KEY_K             = 75,
    PLATFORM_KEY_L             = 76,
    PLATFORM_KEY_M             = 77,
    PLATFORM_KEY_N             = 78,
    PLATFORM_KEY_O             = 79,
    PLATFORM_KEY_P             = 80,
    PLATFORM_KEY_Q             = 81,
    PLATFORM_KEY_R             = 82,
    PLATFORM_KEY_S             = 83,
    PLATFORM_KEY_T             = 84,
    PLATFORM_KEY_U             = 85,
    PLATFORM_KEY_V             = 86,
    PLATFORM_KEY_W             = 87,
    PLATFORM_KEY_X             = 88,
    PLATFORM_KEY_Y             = 89,
    PLATFORM_KEY_Z             = 90,
    PLATFORM_KEY_ESCAPE        = 256,
    PLATFORM_KEY_ENTER         = 257,
    PLATFORM_KEY_TAB           = 258,
    PLATFORM_KEY_BACKSPACE     = 259,
    PLATFORM_KEY_INSERT        = 260,
    PLATFORM_KEY_DELETE        = 261,
    PLATFORM_KEY_RIGHT         = 262,
    PLATFORM_KEY_LEFT          = 263,
    PLATFORM_KEY_DOWN          = 264,
    PLATFORM_KEY_UP            = 265,
    PLATFORM_KEY_F1            = 290,
    PLATFORM_KEY_F2            = 291,
    PLATFORM_KEY_F3            = 292,
    PLATFORM_KEY_F4            = 293,
    PLATFORM_KEY_F5            = 294,
    PLATFORM_KEY_LEFT_SHIFT    = 340,
    PLATFORM_KEY_LEFT_CONTROL  = 341,
    PLATFORM_KEY_LEFT_ALT      = 342
} PlatformKeyCode;

typedef enum {
    PLATFORM_MOUSE_BUTTON_LEFT   = 0,
    PLATFORM_MOUSE_BUTTON_RIGHT  = 1,
    PLATFORM_MOUSE_BUTTON_MIDDLE = 2
} PlatformMouseButton;

typedef struct {
    int windowWidth;
    int windowHeight;
    const char* title;
    bool targetFps60;
    bool headless;
} PlatformConfig;

typedef struct {
    char basePath[PLATFORM_PATH_MAX];
    char saveDir[PLATFORM_PATH_MAX];
    bool isReadOnlyFallback;
} StoragePaths;

// Lifecycle & Window Management
bool Platform_Init(const PlatformConfig* config);
void Platform_Shutdown(void);
bool Platform_ShouldClose(void);
void Platform_RequestClose(void);
void Platform_PollEvents(void);
void Platform_BeginFrame(void);
void Platform_EndFrame(void);
int  Platform_GetWindowWidth(void);
int  Platform_GetWindowHeight(void);
bool Platform_IsWindowResized(void);
bool Platform_IsHeadless(void);

// High-Resolution Timing
double Platform_GetTime(void);
void   Platform_Sleep(double seconds);

// Storage & Paths
void        Platform_GetStoragePaths(StoragePaths* outPaths);
const char* Platform_GetBasePath(void);
const char* Platform_GetSaveDir(void);
bool        Platform_IsReadOnlyStorage(void);

// Input State Queries
bool  Platform_IsKeyDown(int keyCode);
bool  Platform_IsKeyPressed(int keyCode);
bool  Platform_IsKeyReleased(int keyCode);
bool  Platform_IsMouseButtonDown(int button);
bool  Platform_IsMouseButtonPressed(int button);
bool  Platform_IsMouseButtonReleased(int button);
void  Platform_GetMousePosition(float* outX, float* outY);
void  Platform_GetMouseDelta(float* outDx, float* outDy);
float Platform_GetMouseWheelMove(void);
void  Platform_SetCursorCaptured(bool captured);
bool  Platform_IsCursorCaptured(void);

#ifdef __cplusplus
}
#endif

#endif // PLATFORM_H
```

---

## 6. Concrete Implementation Design: `src/platform/platform_desktop.c`

### 6.1. State Machine & Global Storage
```c
#include "platform.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#if defined(_WIN32)
    #define WIN32_LEAN_AND_MEAN
    #define NOGDI
    #define NOUSER
    #include <windows.h>
    #include <timeapi.h>
    #include <direct.h>
    #include <io.h>
#elif defined(__linux__)
    #include <unistd.h>
    #include <linux/limits.h>
    #include <sys/stat.h>
    #include <sys/types.h>
    #include <time.h>
    #include <errno.h>
#elif defined(__APPLE__)
    #include <mach-o/dyld.h>
    #include <unistd.h>
    #include <sys/param.h>
    #include <sys/stat.h>
    #include <sys/types.h>
    #include <time.h>
    #include <errno.h>
#endif

#if !defined(HEADLESS_ONLY)
    #include "raylib.h"
#endif

typedef struct {
    PlatformConfig config;
    StoragePaths paths;
    bool initialized;
    bool shouldClose;
    bool cursorCaptured;
#if defined(_WIN32)
    LARGE_INTEGER timerFreq;
    LARGE_INTEGER timerStart;
#else
    struct timespec timerStart;
#endif
} PlatformState;

static PlatformState s_Platform = {0};
```

### 6.2. Initialization Sequence
1. **Resolve Base Path:** Identify executable parent directory and call `SetCurrentDirectoryW` / `chdir`.
2. **Resolve Save Directory:**
   - Candidate directory: `<BasePath>/saves`.
   - Ensure directory exists (`Platform_CreateDir`).
   - Run Canary Write Test (`Platform_TestDirWritable`).
   - If test passes: `paths.isReadOnlyFallback = false`.
   - If test fails: resolve OS temp directory (`%TEMP%\minecraft_desktop\saves` or `/tmp/minecraft_desktop/saves`), create path, and set `paths.isReadOnlyFallback = true`.
3. **Initialize High-Resolution Timer:**
   - Windows: call `timeBeginPeriod(1)` and capture baseline `QueryPerformanceCounter`.
   - POSIX: capture baseline `clock_gettime(CLOCK_MONOTONIC)`.
4. **Window & Graphics Context (If not headless):**
   - Call `SetConfigFlags(FLAG_WINDOW_RESIZABLE | FLAG_VSYNC_HINT);`.
   - Call `InitWindow(config->windowWidth, config->windowHeight, config->title);`.
   - Call `SetExitKey(KEY_NULL);` (vital: disables auto-exit on Escape).
   - If `config->targetFps60`: call `SetTargetFPS(60);`.
   - Default cursor to captured: `Platform_SetCursorCaptured(true)`.

### 6.3. Shutdown Sequence
1. If not headless, call `CloseWindow()`.
2. On Windows, call `timeEndPeriod(1)`.
3. Set `s_Platform.initialized = false`.

### 6.4. Input & Frame Polling
- In graphical mode: directly query Raylib functions (`IsKeyDown`, `GetMouseDelta`, `BeginDrawing`, `EndDrawing`).
- In headless mode: return safe defaults (`false`, `0.0f`), allowing headless tests to run with zero display driver dependency.

---

## 7. Red-Teaming & Edge Case Analysis (Max-Pro Audit)

| # | Edge Case / Hazard | Root Cause | Architectural Defense |
|---|---|---|---|
| 1 | **Non-ASCII / Unicode Path (e.g. `C:\Игры\Minecraft\`)** | Win32 ANSI functions (`GetModuleFileNameA`, `SetCurrentDirectoryA`) mangle UTF-8 strings based on system code page. | Use `GetModuleFileNameW` and `SetCurrentDirectoryW` throughout Windows path initialization; convert to UTF-8 only for internal engine string buffers. |
| 2 | **Raylib vs. Windows.h Identifier Collision** | Both libraries define `Rectangle`, `CloseWindow`, `ShowCursor`, `DrawText`. | Guard `#include <windows.h>` with `#define WIN32_LEAN_AND_MEAN`, `#define NOGDI`, `#define NOUSER`. Include OS headers before Raylib or wrap Win32 calls in isolated static helpers. |
| 3 | **Escape Key Process Suicide** | Raylib hardcodes `KEY_ESCAPE` to call `CloseWindow()` by default. | Explicitly invoke `SetExitKey(KEY_NULL)` during `Platform_Init`. This allows Escape to be handled as the Pause Menu toggle. |
| 4 | **Read-Only USB Thumb Drive / Optical Disc** | Executable launched from write-protected storage fails on `fopen` in save logic. | Canary write test detects lock at startup; transparently redirects `saveDir` to OS temp directory and alerts HUD. |
| 5 | **CI Runner Crash on Headless Linux** | Linux GitHub Actions runners lack an X11 server / `$DISPLAY`, causing `InitWindow()` to crash. | Passing `--headless` sets `config.headless = true`, completely bypassing window and OpenGL initialization while keeping timers and physics loops functional. |

---

## 8. Ponytail Minimalist Ledger

```c
// ponytail: [executable base-path resolution: native GetModuleFileNameW/readlink] -> [standard C++17 std::filesystem if codebase modernizes]
// ponytail: [storage fallback: canary test to OS temp] -> [XDG Base Directory standard / multi-profile cloud sync]
// ponytail: [windowing & context: statically linked Raylib] -> [direct native Win32/X11 window pump with raw WGL/GLX]
// ponytail: [timer: timeBeginPeriod(1) + QPC] -> [modern Windows WaitableTimerEx asynchronous timer queue]
```

---

## 9. Verification & Test Plan

1. **Base-Path Resolution Test:**
   - Launch executable from a separate directory (e.g. `cd C:\Users && G:\minecraft_desktop\build\minecraft.exe`).
   - Verify `Platform_GetBasePath()` equals the directory containing `minecraft.exe`, NOT `C:\Users`.
   - Verify `saves/` folder is created adjacent to executable.
2. **Read-Only Storage Fallback Test:**
   - Launch executable pointing to a read-only directory or simulated write-locked folder.
   - Verify canary test fails, fallback temp path is activated (`Platform_IsReadOnlyStorage() == true`), and `saveDir` contains `%TEMP%` or `/tmp`.
3. **Headless Mode Test:**
   - Run `minecraft.exe --headless --ticks 60`.
   - Verify process executes 60 ticks without window popup and terminates with exit code `0`.
4. **Timer Accuracy Test:**
   - Query `Platform_GetTime()` over 60 frames; verify average frame delta is $16.67 \pm 1.0\text{ ms}$ with zero drift.
