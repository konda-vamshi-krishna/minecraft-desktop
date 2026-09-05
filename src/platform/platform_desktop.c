#include "platform.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#if defined(_WIN32)
    #ifndef WIN32_LEAN_AND_MEAN
    #define WIN32_LEAN_AND_MEAN
    #endif
    #ifndef NOGDI
    #define NOGDI
    #endif
    #ifndef NOUSER
    #define NOUSER
    #endif
    #include <windows.h>
    #include <timeapi.h>
    #include <direct.h>
    #include <io.h>

    // Undefine conflicting Windows macros before any potential Raylib header
    #undef CloseWindow
    #undef ShowCursor
    #undef Rectangle
    #undef DrawText
    #undef LoadImage
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

#if !defined(HEADLESS_ONLY) && (defined(HAVE_RAYLIB) || (defined(__has_include) && __has_include(<raylib.h>)))
    #define USE_RAYLIB 1
    #include <raylib.h>
#else
    #define USE_RAYLIB 0
#endif

// ponytail: [executable base-path resolution: native GetModuleFileNameW/readlink] -> [standard C++17 std::filesystem if codebase modernizes]
// ponytail: [storage fallback: canary test to OS temp] -> [XDG Base Directory standard / multi-profile cloud sync]
// ponytail: [windowing & context: statically linked Raylib] -> [direct native Win32/X11 window pump with raw WGL/GLX]
// ponytail: [timer: timeBeginPeriod(1) + QPC] -> [modern Windows WaitableTimerEx asynchronous timer queue]

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

/* ========================================================================= */
/* Directory & Storage Resolution Helpers                                    */
/* ========================================================================= */

static bool Platform_CreateDir(const char* path) {
    if (!path || path[0] == '\0') return false;

    char temp[PLATFORM_PATH_MAX];
    strncpy(temp, path, sizeof(temp) - 1);
    temp[sizeof(temp) - 1] = '\0';

    // Strip trailing slashes
    size_t pathLen = strlen(temp);
    while (pathLen > 1 && (temp[pathLen - 1] == '/' || temp[pathLen - 1] == '\\')) {
        temp[--pathLen] = '\0';
    }

    // Iteratively create intermediate directory components
    char* p = temp;
#if defined(_WIN32)
    // Skip Windows drive prefix (e.g. "C:\") or UNC path ("\\server\share\")
    if (((p[0] >= 'a' && p[0] <= 'z') || (p[0] >= 'A' && p[0] <= 'Z')) && p[1] == ':') {
        p += 2;
    } else if ((p[0] == '\\' && p[1] == '\\') || (p[0] == '/' && p[1] == '/')) {
        p += 2;
        while (*p && *p != '\\' && *p != '/') p++;
        if (*p) p++;
        while (*p && *p != '\\' && *p != '/') p++;
    }
#endif
    if (*p == '/' || *p == '\\') p++;

    for (; *p; p++) {
        if (*p == '/' || *p == '\\') {
            char slash = *p;
            *p = '\0';
#if defined(_WIN32)
            wchar_t wide[PLATFORM_PATH_MAX];
            if (MultiByteToWideChar(CP_UTF8, 0, temp, -1, wide, PLATFORM_PATH_MAX) > 0) {
                CreateDirectoryW(wide, NULL);
            }
#else
            mkdir(temp, 0755);
#endif
            *p = slash;
        }
    }

    // Create final leaf directory
#if defined(_WIN32)
    wchar_t widePath[PLATFORM_PATH_MAX];
    int len = MultiByteToWideChar(CP_UTF8, 0, temp, -1, widePath, PLATFORM_PATH_MAX);
    if (len <= 0) return false;
    if (CreateDirectoryW(widePath, NULL) || GetLastError() == ERROR_ALREADY_EXISTS) {
        return true;
    }
    return false;
#else
    if (mkdir(temp, 0755) == 0 || errno == EEXIST) {
        return true;
    }
    return false;
#endif
}

static bool Platform_TestDirWritable(const char* dirPath) {
    char canary[PLATFORM_PATH_MAX + 32];
    snprintf(canary, sizeof(canary), "%s%c.write_test", dirPath,
#if defined(_WIN32)
             '\\'
#else
             '/'
#endif
    );
#if defined(_WIN32)
    wchar_t wideCanary[PLATFORM_PATH_MAX + 32];
    int len = MultiByteToWideChar(CP_UTF8, 0, canary, -1, wideCanary, PLATFORM_PATH_MAX + 32);
    if (len <= 0) return false;
    FILE* f = _wfopen(wideCanary, L"wb");
    if (!f) return false;
    const char* testData = "minecraft_desktop_write_probe\n";
    size_t written = fwrite(testData, 1, strlen(testData), f);
    fclose(f);
    _wremove(wideCanary);
    return (written == strlen(testData));
#else
    FILE* f = fopen(canary, "wb");
    if (!f) return false;
    const char* testData = "minecraft_desktop_write_probe\n";
    size_t written = fwrite(testData, 1, strlen(testData), f);
    fclose(f);
    remove(canary);
    return (written == strlen(testData));
#endif
}

static bool Platform_ResolveBasePath(char* outPath, size_t maxLen) {
#if defined(_WIN32)
    wchar_t widePath[PLATFORM_PATH_MAX];
    DWORD len = GetModuleFileNameW(NULL, widePath, (DWORD)(sizeof(widePath) / sizeof(widePath[0])));
    if (len == 0 || len >= (sizeof(widePath) / sizeof(widePath[0]))) {
        return false;
    }
    wchar_t* lastSlash = wcsrchr(widePath, L'\\');
    wchar_t* lastForwardSlash = wcsrchr(widePath, L'/');
    if (lastForwardSlash && (!lastSlash || lastForwardSlash > lastSlash)) {
        lastSlash = lastForwardSlash;
    }
    if (lastSlash) {
        if (lastSlash == widePath + 2 && widePath[1] == L':') {
            *(lastSlash + 1) = L'\0';
        } else {
            *lastSlash = L'\0';
        }
    }
    SetCurrentDirectoryW(widePath);

    int written = WideCharToMultiByte(CP_UTF8, 0, widePath, -1, outPath, (int)maxLen, NULL, NULL);
    return (written > 0);
#elif defined(__linux__)
    char procPath[PLATFORM_PATH_MAX];
    ssize_t len = readlink("/proc/self/exe", procPath, sizeof(procPath) - 1);
    if (len == -1) {
        return false;
    }
    procPath[len] = '\0';
    char* lastSlash = strrchr(procPath, '/');
    if (lastSlash == procPath) {
        *(lastSlash + 1) = '\0';
    } else if (lastSlash) {
        *lastSlash = '\0';
    }
    chdir(procPath);
    strncpy(outPath, procPath, maxLen - 1);
    outPath[maxLen - 1] = '\0';
    return true;
#elif defined(__APPLE__)
    char applePath[PLATFORM_PATH_MAX];
    uint32_t size = sizeof(applePath);
    if (_NSGetExecutablePath(applePath, &size) != 0) {
        return false;
    }
    char resolvedPath[PLATFORM_PATH_MAX];
    if (realpath(applePath, resolvedPath) == NULL) {
        strncpy(resolvedPath, applePath, sizeof(resolvedPath) - 1);
        resolvedPath[sizeof(resolvedPath) - 1] = '\0';
    }
    char* lastSlash = strrchr(resolvedPath, '/');
    if (lastSlash == resolvedPath) {
        *(lastSlash + 1) = '\0';
    } else if (lastSlash) {
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

static bool Platform_ResolveTempSaveDir(char* outTempSaveDir, size_t maxLen) {
#if defined(_WIN32)
    wchar_t wideTemp[PLATFORM_PATH_MAX];
    DWORD len = GetTempPathW(PLATFORM_PATH_MAX, wideTemp);
    if (len == 0 || len >= PLATFORM_PATH_MAX) return false;
    char tempUtf8[PLATFORM_PATH_MAX];
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

/* ========================================================================= */
/* Lifecycle & Window Management                                             */
/* ========================================================================= */

bool Platform_Init(const PlatformConfig* config) {
    memset(&s_Platform, 0, sizeof(PlatformState));
    if (config) {
        s_Platform.config = *config;
    } else {
        s_Platform.config.windowWidth = PLATFORM_DEFAULT_WINDOW_WIDTH;
        s_Platform.config.windowHeight = PLATFORM_DEFAULT_WINDOW_HEIGHT;
        s_Platform.config.title = "Minecraft Desktop";
        s_Platform.config.targetFps60 = true;
        s_Platform.config.headless = false;
    }

    // 1. Resolve executable base path and set CWD
    if (!Platform_ResolveBasePath(s_Platform.paths.basePath, sizeof(s_Platform.paths.basePath))) {
        strncpy(s_Platform.paths.basePath, ".", sizeof(s_Platform.paths.basePath) - 1);
    }

    // 2. Resolve save directory with canary write probe
    char candidateSaveDir[PLATFORM_PATH_MAX];
    size_t baseLen = strlen(s_Platform.paths.basePath);
    bool hasTrailingSlash = (baseLen > 0 &&
        (s_Platform.paths.basePath[baseLen - 1] == '/' || s_Platform.paths.basePath[baseLen - 1] == '\\'));
    snprintf(candidateSaveDir, sizeof(candidateSaveDir),
             hasTrailingSlash ? "%ssaves" : "%s%csaves",
             s_Platform.paths.basePath,
#if defined(_WIN32)
             '\\'
#else
             '/'
#endif
    );

    Platform_CreateDir(candidateSaveDir);
    if (Platform_TestDirWritable(candidateSaveDir)) {
        strncpy(s_Platform.paths.saveDir, candidateSaveDir, sizeof(s_Platform.paths.saveDir) - 1);
        s_Platform.paths.isReadOnlyFallback = false;
    } else {
        // Fallback to OS temporary directory
        char tempSaveDir[PLATFORM_PATH_MAX];
        Platform_ResolveTempSaveDir(tempSaveDir, sizeof(tempSaveDir));
        Platform_CreateDir(tempSaveDir);
        strncpy(s_Platform.paths.saveDir, tempSaveDir, sizeof(s_Platform.paths.saveDir) - 1);
        s_Platform.paths.isReadOnlyFallback = true;
    }

    // 3. Initialize high-resolution monotonic timer
#if defined(_WIN32)
    timeBeginPeriod(1);
    QueryPerformanceFrequency(&s_Platform.timerFreq);
    QueryPerformanceCounter(&s_Platform.timerStart);
#else
    clock_gettime(CLOCK_MONOTONIC, &s_Platform.timerStart);
#endif

    // 4. Window & Graphics Context (if not headless)
    if (!s_Platform.config.headless) {
#if USE_RAYLIB
        SetConfigFlags(FLAG_WINDOW_RESIZABLE | FLAG_VSYNC_HINT);
        InitWindow(s_Platform.config.windowWidth, s_Platform.config.windowHeight,
                   s_Platform.config.title ? s_Platform.config.title : "Minecraft Desktop");
        SetExitKey(KEY_NULL); // Preserve ESC for Pause Menu!
        if (s_Platform.config.targetFps60) {
            SetTargetFPS(60);
        }
        Platform_SetCursorCaptured(true);
#endif
    }

    s_Platform.initialized = true;
    s_Platform.shouldClose = false;
    return true;
}

void Platform_Shutdown(void) {
    if (!s_Platform.initialized) return;

    if (!s_Platform.config.headless) {
#if USE_RAYLIB
        CloseWindow();
#endif
    }

#if defined(_WIN32)
    timeEndPeriod(1);
#endif

    s_Platform.initialized = false;
}

bool Platform_ShouldClose(void) {
    if (s_Platform.shouldClose) return true;
    if (!s_Platform.config.headless) {
#if USE_RAYLIB
        return WindowShouldClose();
#endif
    }
    return false;
}

void Platform_RequestClose(void) {
    s_Platform.shouldClose = true;
}

void Platform_PollEvents(void) {
    // In Raylib, event polling occurs inside BeginDrawing() / WindowShouldClose()
}

void Platform_BeginFrame(void) {
    if (!s_Platform.config.headless) {
#if USE_RAYLIB
        BeginDrawing();
#endif
    }
}

void Platform_EndFrame(void) {
    if (!s_Platform.config.headless) {
#if USE_RAYLIB
        EndDrawing();
#endif
    }
}

int Platform_GetWindowWidth(void) {
    if (!s_Platform.config.headless) {
#if USE_RAYLIB
        int w = GetScreenWidth();
        return (w > 0) ? w : 1;
#endif
    }
    return (s_Platform.config.windowWidth > 0) ? s_Platform.config.windowWidth : 1;
}

int Platform_GetWindowHeight(void) {
    if (!s_Platform.config.headless) {
#if USE_RAYLIB
        int h = GetScreenHeight();
        return (h > 0) ? h : 1;
#endif
    }
    return (s_Platform.config.windowHeight > 0) ? s_Platform.config.windowHeight : 1;
}

bool Platform_IsWindowResized(void) {
    if (!s_Platform.config.headless) {
#if USE_RAYLIB
        return IsWindowResized();
#endif
    }
    return false;
}

bool Platform_IsHeadless(void) {
    return s_Platform.config.headless;
}

/* ========================================================================= */
/* High-Resolution Timing                                                    */
/* ========================================================================= */

double Platform_GetTime(void) {
#if defined(_WIN32)
    if (s_Platform.timerFreq.QuadPart == 0) return 0.0;
    LARGE_INTEGER now;
    QueryPerformanceCounter(&now);
    return (double)(now.QuadPart - s_Platform.timerStart.QuadPart) / (double)s_Platform.timerFreq.QuadPart;
#else
    struct timespec now;
    clock_gettime(CLOCK_MONOTONIC, &now);
    double sec = (double)(now.tv_sec - s_Platform.timerStart.tv_sec);
    double nsec = (double)(now.tv_nsec - s_Platform.timerStart.tv_nsec);
    return sec + nsec * 1e-9;
#endif
}

void Platform_Sleep(double seconds) {
    if (seconds <= 0.0) return;
#if defined(_WIN32)
    DWORD ms = (DWORD)(seconds * 1000.0);
    Sleep(ms);
#else
    struct timespec req;
    req.tv_sec = (time_t)seconds;
    req.tv_nsec = (long)((seconds - (double)req.tv_sec) * 1e9);
    nanosleep(&req, NULL);
#endif
}

/* ========================================================================= */
/* Storage & Paths                                                           */
/* ========================================================================= */

void Platform_GetStoragePaths(StoragePaths* outPaths) {
    if (outPaths) {
        *outPaths = s_Platform.paths;
    }
}

const char* Platform_GetBasePath(void) {
    return s_Platform.paths.basePath;
}

const char* Platform_GetSaveDir(void) {
    return s_Platform.paths.saveDir;
}

bool Platform_IsReadOnlyStorage(void) {
    return s_Platform.paths.isReadOnlyFallback;
}

/* ========================================================================= */
/* Input State Queries                                                       */
/* ========================================================================= */

bool Platform_IsKeyDown(int keyCode) {
    if (s_Platform.config.headless) return false;
#if USE_RAYLIB
    return IsKeyDown(keyCode);
#else
    return false;
#endif
}

bool Platform_IsKeyPressed(int keyCode) {
    if (s_Platform.config.headless) return false;
#if USE_RAYLIB
    return IsKeyPressed(keyCode);
#else
    return false;
#endif
}

bool Platform_IsKeyReleased(int keyCode) {
    if (s_Platform.config.headless) return false;
#if USE_RAYLIB
    return IsKeyReleased(keyCode);
#else
    return false;
#endif
}

bool Platform_IsMouseButtonDown(int button) {
    if (s_Platform.config.headless) return false;
#if USE_RAYLIB
    return IsMouseButtonDown(button);
#else
    return false;
#endif
}

bool Platform_IsMouseButtonPressed(int button) {
    if (s_Platform.config.headless) return false;
#if USE_RAYLIB
    return IsMouseButtonPressed(button);
#else
    return false;
#endif
}

bool Platform_IsMouseButtonReleased(int button) {
    if (s_Platform.config.headless) return false;
#if USE_RAYLIB
    return IsMouseButtonReleased(button);
#else
    return false;
#endif
}

void Platform_GetMousePosition(float* outX, float* outY) {
    if (outX) *outX = 0.0f;
    if (outY) *outY = 0.0f;
    if (s_Platform.config.headless) return;
#if USE_RAYLIB
    Vector2 m = GetMousePosition();
    if (outX) *outX = m.x;
    if (outY) *outY = m.y;
#endif
}

void Platform_GetMouseDelta(float* outDx, float* outDy) {
    if (outDx) *outDx = 0.0f;
    if (outDy) *outDy = 0.0f;
    if (s_Platform.config.headless) return;
#if USE_RAYLIB
    Vector2 d = GetMouseDelta();
    if (outDx) *outDx = d.x;
    if (outDy) *outDy = d.y;
#endif
}

float Platform_GetMouseWheelMove(void) {
    if (s_Platform.config.headless) return 0.0f;
#if USE_RAYLIB
    return GetMouseWheelMove();
#else
    return 0.0f;
#endif
}

void Platform_SetCursorCaptured(bool captured) {
    s_Platform.cursorCaptured = captured;
    if (s_Platform.config.headless) return;
#if USE_RAYLIB
    if (captured) {
        DisableCursor();
    } else {
        EnableCursor();
    }
#endif
}

bool Platform_IsCursorCaptured(void) {
    return s_Platform.cursorCaptured;
}
