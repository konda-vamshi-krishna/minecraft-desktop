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

/* Key codes mapped directly to standard GLFW / Raylib key integer values */
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
