#ifndef RUNTIME_H
#define RUNTIME_H

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

// =============================================================================
// Constants & Canonical Timing Specifications
// =============================================================================
#define RUNTIME_PHYSICS_HZ         60
#define RUNTIME_FIXED_DT           (1.0 / (double)RUNTIME_PHYSICS_HZ) // 0.016666666666666666 s
#define RUNTIME_MAX_FRAME_TIME     0.25                               // 250 ms spiral-of-death clamp
#define RUNTIME_MAX_SUBSTEPS       15                                 // 0.25 / (1/60) = 15 steps max
#define RUNTIME_CELESTIAL_PERIOD   1200.0                             // 20 minutes canonical day/night cycle

// =============================================================================
// Configuration Structure
// =============================================================================
typedef struct {
    int targetFps;               // Target FPS throttle (e.g. 60, or 0 for unthrottled/vsync)
    bool headless;               // Headless execution flag (no window/rendering)
    double fixedDt;              // Physics timestep (default RUNTIME_FIXED_DT)
    double maxAccumulator;       // Clamp limit for accumulator (default RUNTIME_MAX_FRAME_TIME)
    int maxSubsteps;             // Hard cap on physics substeps per frame (default 15)
    uint64_t maxFrames;          // Limit execution to N frames (0 = run indefinitely)
    double maxDuration;          // Limit execution to N seconds (0 = run indefinitely)
} RuntimeConfig;

// =============================================================================
// Performance & Telemetry Metrics
// =============================================================================
typedef struct {
    uint64_t totalFrames;        // Total render frames presented
    uint64_t totalTicks;         // Total physics steps executed
    double totalSimulatedTime;   // Simulated game time (ticks * fixedDt)
    double totalRealTime;        // Elapsed wall-clock time
    float fps;                   // Rolling smoothed FPS
    float tps;                   // Rolling smoothed TPS (Ticks Per Second)
    float lastFrameTimeMs;       // Last frame duration in milliseconds
    int substepsLastFrame;       // Substeps executed in the last frame
} RuntimeMetrics;

// =============================================================================
// Celestial & Lighting State
// =============================================================================
typedef struct {
    double timeOfDay;            // Current time within cycle: [0.0, 1200.0) seconds
    float cycleProgress;         // Normalized [0.0, 1.0)
    float celestialAngle;        // Sun/Moon orbital angle in radians [0.0, 2*PI)
    float sunDirection[3];       // Normalized unit vector pointing to the sun
    float daylightFactor;        // Ambient sunlight intensity [0.0, 1.0]
    bool isDaytime;              // True if sun is above horizon
} CelestialClock;

// =============================================================================
// Subsystem Callback Hooks (Zero dynamic allocation, function pointers)
// =============================================================================
typedef void (*RuntimeEventPollFn)(void);
typedef void (*RuntimePhysicsTickFn)(double dt);
typedef void (*RuntimeMeshBudgetFn)(int maxChunks);
typedef void (*RuntimeRenderFrameFn)(float alpha);

typedef struct {
    RuntimeEventPollFn onPollEvents;
    RuntimePhysicsTickFn onPhysicsTick;
    RuntimeMeshBudgetFn onMeshBudget;
    RuntimeRenderFrameFn onRenderFrame;
} RuntimeHooks;

// =============================================================================
// Primary Runtime State Machine
// =============================================================================
typedef struct {
    RuntimeConfig config;
    RuntimeHooks hooks;
    RuntimeMetrics metrics;
    CelestialClock celestial;

    double accumulator;
    double previousTime;
    double currentTime;
    float renderAlpha;

    bool isInitialized;
    bool isRunning;
    bool isPaused;
    bool shouldQuit;
} RuntimeState;

// =============================================================================
// Lifecycle & Core Functions
// =============================================================================
void Runtime_GetDefaultConfig(RuntimeConfig* outConfig);
void Runtime_Init(const RuntimeConfig* config, const RuntimeHooks* hooks);
void Runtime_Shutdown(void);

// Running the loop
void Runtime_Run(void);                 // Runs the full loop until shouldQuit or Platform_ShouldClose()
void Runtime_StepFrame(void);           // Executes a single complete frame (Begin -> Physics -> Render -> End)
void Runtime_RequestQuit(void);         // Signals loop termination
bool Runtime_IsRunning(void);

// Granular step functions (for custom loops & fine-grained testing)
void Runtime_BeginFrame(void);          // Computes frame delta, clamps, updates accumulator
bool Runtime_ShouldStepPhysics(void);   // Checks accumulator >= fixedDt & substeps < max; decrements accumulator
float Runtime_GetRenderAlpha(void);     // Computes alpha = accumulator / fixedDt in [0.0, 1.0]
void Runtime_EndFrame(void);            // Calculates FPS/TPS metrics and applies frame throttling

// Testing & Simulation Utility (Direct deterministic injection without wall-clock wait)
int Runtime_SimulateDelta(double deltaSeconds); // Feeds delta into accumulator and runs physics steps

// Telemetry & State Queries
const RuntimeMetrics* Runtime_GetMetrics(void);
const CelestialClock* Runtime_GetCelestialClock(void);
float Runtime_GetAlpha(void);
bool Runtime_IsPaused(void);
void Runtime_SetPaused(bool paused);

#ifdef __cplusplus
}
#endif

#endif // RUNTIME_H
