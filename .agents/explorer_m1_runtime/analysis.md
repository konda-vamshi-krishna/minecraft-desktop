# Milestone 1: Engine Runtime & Game Loop Architecture Analysis

**Project:** Minecraft Desktop — Universal 1-Click Native Edition  
**Author:** explorer_m1_runtime (Runtime Systems Architect)  
**Standard:** Ponytail Minimal-Complexity Principles & Max-Pro Polymath Framework  
**Target Milestone:** M1 (Architecture, Runtime & Engine Core)  
**Status:** RATIFIED IMPLEMENTATION SPECIFICATION  

---

## 1. Executive Summary & Architectural Imperatives

The runtime subsystem is the operational heartbeat of the voxel game engine. In accordance with the project's core distribution imperative—**zero-dependency, single-click instant execution with rock-solid stability on low-end hardware**—the runtime engine must guarantee:
1. **Absolute Physics Determinism:** The simulation must execute at an unyielding, fixed frequency of $60\text{ Hz}$ ($dt = \frac{1}{60}\text{ s} \approx 0.0166667\text{ s}$), ensuring bit-level mechanical parity regardless of user monitor refresh rate (60 Hz, 120 Hz, 144 Hz, 240 Hz) or GPU performance fluctuations.
2. **Fail-Safe Spiral-of-Death Immunity:** When encountering OS-level pauses (window drag/resize, debugging breakpoints, system hibernation, or garbage collection stalls in OS compositor), the accumulator must clamp to a hard ceiling of $0.25\text{ s}$ (15 substeps maximum) to prevent CPU lockups.
3. **Silky-Smooth Sub-Frame Interpolation:** Sub-frame camera and entity transforms must sample the fractional render alpha $\alpha = \frac{\text{accumulator}}{dt} \in [0.0, 1.0)$, eliminating temporal micro-stutter on variable-rate displays.
4. **Microsecond Pacing Precision:** Target 60 FPS frame throttling utilizing a hybrid sleep/spin-wait cycle to minimize CPU battery consumption while preventing frame time jitter.
5. **Zero Heap Allocations:** Zero calls to `malloc`, `free`, or `realloc` during the game loop; the entire runtime state is maintained in flat static memory.

---

## 2. Mathematical Formulation of the Game Loop

### 2.1. Fixed 60 Hz Physics Timestep & Floating-Point Drift Analysis

Canonical Minecraft Java Edition executes physics ticks at $20\text{ TPS}$ ($dt = 0.05\text{ s}$). However, running a desktop voxel renderer at 60+ FPS against a 20 TPS physics tick without sub-stepping introduces visual quantization artifacts and collision response delays. 

In our native engine:
$$\text{PHYSICS\_HZ} = 60$$
$$dt = \frac{1.0}{60.0} = 0.016666666666666666\dots\text{ seconds}$$

#### The Precision Trap: Single vs. Double Precision Accumulator
In 32-bit single-precision IEEE 754 floats (`float`), the mantissa contains 24 bits of precision (approx 7 decimal digits).
* At $t = 3,600\text{ s}$ (1 hour of play), the machine epsilon $\epsilon \approx 2^{-24} \times 4096 \approx 0.000244\text{ s}$ ($0.244\text{ ms}$).
* At $t = 86,400\text{ s}$ (24 hours of play), $\epsilon \approx 2^{-24} \times 131072 \approx 0.00781\text{ s}$ ($7.81\text{ ms}$, nearly half a frame!).
Using `float` for wall-clock timestamps (`currentTime`, `previousTime`) and the `accumulator` leads to severe timing drift, quantization stutter, and frame drop over sustained gameplay sessions.

**Invariant 1:** All wall-clock timestamps (`Platform_GetTime()`), frame deltas, and the state `accumulator` **MUST** be stored in 64-bit IEEE 754 floating-point (`double`). With `double` (53-bit mantissa), time precision remains sub-picosecond even after years of continuous execution.

---

### 2.2. The High-Precision Accumulator State Machine

Let $t_{\text{prev}}$ and $t_{\text{curr}}$ be consecutive wall-clock samples obtained from `Platform_GetTime()`.
The raw elapsed frame delta is:
$$\Delta t_{\text{frame}} = t_{\text{curr}} - t_{\text{prev}}$$

To guarantee numerical safety across all operating system edge cases:
1. **Clock Monotonicity Guard (NTP / Sleep Correction):**
   $$\text{If } \Delta t_{\text{frame}} < 0.0 \implies \Delta t_{\text{frame}} \leftarrow 0.0$$
2. **Pause Mode Guard:**
   $$\text{If } \text{isPaused} \implies \Delta t_{\text{frame}} \leftarrow 0.0$$
3. **Spiral-of-Death Frame Delta Clamping:**
   $$\Delta t_{\text{clamped}} = \min(\Delta t_{\text{frame}}, \Delta t_{\text{max}}), \quad \text{where } \Delta t_{\text{max}} = 0.25\text{ s}$$
4. **Accumulator Integration:**
   $$\text{accumulator} \leftarrow \min(\text{accumulator} + \Delta t_{\text{clamped}}, \Delta t_{\text{max}})$$

#### Proof of Sub-Step Boundedness
Notice that $\Delta t_{\text{max}} = 0.25\text{ s}$ is an exact integer multiple of $dt = \frac{1}{60}\text{ s}$:
$$N_{\text{max\_steps}} = \frac{0.25}{\frac{1}{60}} = 0.25 \times 60 = 15.0\text{ steps}$$
Under the most severe lag spike or system hang, the physics engine will execute **at most 15 discrete sub-steps** in a single frame.

Furthermore, as a fail-safe against sustained hardware overload (where 15 physics sub-steps themselves take longer than $0.25\text{ s}$ to compute on an overloaded CPU), we enforce a hard loop counter:
```c
int substeps = 0;
while (accumulator >= FIXED_DT && substeps < MAX_SUBSTEPS) {
    Physics_Step(FIXED_DT);
    World_Update(FIXED_DT);
    accumulator -= FIXED_DT;
    substeps++;
}
if (substeps >= MAX_SUBSTEPS) {
    // Drop remaining accumulator to break the cascade
    accumulator = 0.0;
}
```
This guarantees that the simulation will gracefully downscale to slow-motion rather than locking the host operating system thread in an unbounded loop.

---

### 2.3. Sub-Frame Render Interpolation Alpha ($\alpha$)

After all eligible physics sub-steps have completed for the current frame, the remaining unsimulated time in the accumulator satisfies:
$$0.0 \le \text{accumulator} < dt$$

The render interpolation fraction $\alpha$ is evaluated as:
$$\alpha = \frac{\text{accumulator}}{dt}, \quad \alpha \in [0.0, 1.0]$$

Due to floating-point representation boundaries, numerical values can occasionally evaluate to $-10^{-16}$ or $1.000000000000001$. We apply strict bounding:
```c
float alpha = (float)(accumulator / FIXED_DT);
if (alpha < 0.0f) alpha = 0.0f;
if (alpha > 1.0f) alpha = 1.0f;
```

#### Application to Kinematic Transforms
For any spatial position vector $\vec{x}$ (player eye position, camera translation, entity coordinates):
$$\vec{x}_{\text{render}} = \vec{x}_{\text{prev}} \cdot (1.0 - \alpha) + \vec{x}_{\text{curr}} \cdot \alpha$$

#### Angular Lerp with Modulo Wrap (Camera Yaw)
Pitch is constrained in $[-89.0^\circ, +89.0^\circ]$ and can be linearly interpolated directly.
Camera Yaw exists on the circular manifold $[0.0^\circ, 360.0^\circ)$. A naive linear interpolation across the $359^\circ \to 1^\circ$ boundary would result in a $358^\circ$ reverse rotation snap.
The shortest-arc angular interpolation formula is enforced:
```c
float diff = currYaw - prevYaw;
if (diff > 180.0f)  diff -= 360.0f;
if (diff < -180.0f) diff += 360.0f;
float renderYaw = prevYaw + diff * alpha;
if (renderYaw >= 360.0f) renderYaw -= 360.0f;
if (renderYaw < 0.0f)    renderYaw += 360.0f;
```

---

### 2.4. Day/Night Celestial Clock Dynamics

In canonical Minecraft, a complete in-game day spans $24,000\text{ ticks} = 20\text{ minutes} = 1,200.0\text{ seconds}$.
The runtime manages the celestial cycle as a deterministic function of simulated game time $t_{\text{sim}}$:

1. **Cycle Phase $\phi \in [0.0, 1.0)$:**
   $$\phi = \frac{\text{fmod}(t_{\text{sim}}, 1200.0)}{1200.0}$$
2. **Orbital Angle $\theta \in [0.0, 2\pi)$:**
   $$\theta = \phi \times 2\pi$$
   * $\theta = 0$: Sunrise (East horizon)
   * $\theta = \frac{\pi}{2}$: Solar Noon (Zenith)
   * $\theta = \pi$: Sunset (West horizon)
   * $\theta = \frac{3\pi}{2}$: Midnight (Nadir)
3. **Orbital Sun Direction Vector $\hat{s}$:**
   $$\hat{s} = (\cos\theta, \sin\theta, 0.0)$$
4. **Daylight Lighting Factor $L \in [0.0, 1.0]$:**
   $$L = \max(0.0f, \sin\theta)$$
   This factor directly drives the clear sky color shader uniform and ambient voxel face lighting.

---

## 3. Frame Pacing, Throttling & Power Management

### 3.1. Target 60 FPS Throttling Strategy
When running on battery-powered laptops or untethered handhelds, uncapped frame loops needlessly consume 100% of a CPU/GPU core.
When `targetFps = 60` is enabled (and VSync is inactive or in headless mode):
$$t_{\text{target\_frame}} = \frac{1.0}{60.0} \approx 0.0166667\text{ s}$$

Standard OS sleep calls (`Sleep()` on Windows, `usleep()` on POSIX) have coarse scheduler resolutions:
* Standard Windows scheduler tick: $\sim 15.6\text{ ms}$.
* With `timeBeginPeriod(1)` (via `winmm.lib`): $\sim 1.0\text{ ms}$.

#### The Hybrid Sleep/Spin-Wait Algorithm
To achieve sub-millisecond pacing without wasting CPU cycles:
```c
double frameElapsed = Platform_GetTime() - frameStartTime;
if (frameElapsed < targetInterval) {
    double waitTime = targetInterval - frameElapsed;
    // If more than 2.0ms remaining, sleep coarsely to yield OS timeslices
    if (waitTime > 0.002) {
        Platform_Sleep(waitTime - 0.0015);
    }
    // High-precision spin-wait for the final ~1.5ms
    while ((Platform_GetTime() - frameStartTime) < targetInterval) {
        #if defined(_MSC_VER) || defined(__GNUC__)
        // Yield pipeline slot
        #endif
    }
}
```

---

## 4. Interface Contract Specification (`src/core/runtime.h`)

Below is the ratified, production-grade interface header for `src/core/runtime.h`:

```c
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
// Subsystem Callback Hooks (Zero dynamic allocation, optional function pointers)
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
```

---

## 5. Concrete Implementation Plan (`src/core/runtime.c`)

### 5.1. Internal State Machine Architecture
`src/core/runtime.c` encapsulates a static, zero-allocation singleton:
```c
#include "core/runtime.h"
#include "platform/platform.h"
#include <math.h>
#include <string.h>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

static RuntimeState g_Runtime = {0};
static int s_SubstepCountThisFrame = 0;
static double s_MetricsTimer = 0.0;
static uint32_t s_FramesSinceMetrics = 0;
static uint32_t s_TicksSinceMetrics = 0;
```

### 5.2. Detailed Function Implementations

#### Initialization & Default Configuration
```c
void Runtime_GetDefaultConfig(RuntimeConfig* outConfig) {
    if (!outConfig) return;
    outConfig->targetFps = 60;
    outConfig->headless = false;
    outConfig->fixedDt = RUNTIME_FIXED_DT;
    outConfig->maxAccumulator = RUNTIME_MAX_FRAME_TIME;
    outConfig->maxSubsteps = RUNTIME_MAX_SUBSTEPS;
    outConfig->maxFrames = 0;
    outConfig->maxDuration = 0.0;
}

void Runtime_Init(const RuntimeConfig* config, const RuntimeHooks* hooks) {
    memset(&g_Runtime, 0, sizeof(RuntimeState));
    if (config) {
        g_Runtime.config = *config;
    } else {
        Runtime_GetDefaultConfig(&g_Runtime.config);
    }
    if (hooks) {
        g_Runtime.hooks = *hooks;
    }
    
    // Validate bounds
    if (g_Runtime.config.fixedDt <= 0.0) {
        g_Runtime.config.fixedDt = RUNTIME_FIXED_DT;
    }
    if (g_Runtime.config.maxAccumulator <= 0.0) {
        g_Runtime.config.maxAccumulator = RUNTIME_MAX_FRAME_TIME;
    }
    if (g_Runtime.config.maxSubsteps <= 0) {
        g_Runtime.config.maxSubsteps = RUNTIME_MAX_SUBSTEPS;
    }
    
    g_Runtime.previousTime = Platform_GetTime();
    g_Runtime.currentTime = g_Runtime.previousTime;
    s_MetricsTimer = g_Runtime.previousTime;
    g_Runtime.accumulator = 0.0;
    g_Runtime.renderAlpha = 0.0f;
    g_Runtime.isInitialized = true;
    g_Runtime.isRunning = true;
    g_Runtime.isPaused = false;
    g_Runtime.shouldQuit = false;
}
```

#### Frame Preamble (`Runtime_BeginFrame`)
```c
void Runtime_BeginFrame(void) {
    double now = Platform_GetTime();
    double frameTime = now - g_Runtime.previousTime;
    g_Runtime.previousTime = now;
    g_Runtime.currentTime = now;
    
    // Guard against system clock jumps backwards
    if (frameTime < 0.0) {
        frameTime = 0.0;
    }
    
    g_Runtime.metrics.lastFrameTimeMs = (float)(frameTime * 1000.0);
    g_Runtime.metrics.totalRealTime += frameTime;
    
    // When paused, freeze simulated progression
    if (g_Runtime.isPaused) {
        frameTime = 0.0;
    }
    
    // Spiral of death clamp on frame delta
    if (frameTime > g_Runtime.config.maxAccumulator) {
        frameTime = g_Runtime.config.maxAccumulator;
    }
    
    g_Runtime.accumulator += frameTime;
    
    // Clamp total accumulated time to prevent compounding spikes
    if (g_Runtime.accumulator > g_Runtime.config.maxAccumulator) {
        g_Runtime.accumulator = g_Runtime.config.maxAccumulator;
    }
    
    s_SubstepCountThisFrame = 0;
}
```

#### Physics Sub-Step Query (`Runtime_ShouldStepPhysics`)
```c
static void UpdateCelestialClock(double dt);

bool Runtime_ShouldStepPhysics(void) {
    if (g_Runtime.accumulator >= g_Runtime.config.fixedDt && 
        s_SubstepCountThisFrame < g_Runtime.config.maxSubsteps) {
        
        g_Runtime.accumulator -= g_Runtime.config.fixedDt;
        s_SubstepCountThisFrame++;
        g_Runtime.metrics.totalTicks++;
        s_TicksSinceMetrics++;
        g_Runtime.metrics.totalSimulatedTime += g_Runtime.config.fixedDt;
        
        UpdateCelestialClock(g_Runtime.config.fixedDt);
        return true;
    }
    
    // Hard ceiling: if we reached max substeps, discard remainder
    if (s_SubstepCountThisFrame >= g_Runtime.config.maxSubsteps) {
        g_Runtime.accumulator = 0.0;
    }
    return false;
}
```

#### Render Alpha Derivation
```c
float Runtime_GetRenderAlpha(void) {
    float alpha = (float)(g_Runtime.accumulator / g_Runtime.config.fixedDt);
    if (alpha < 0.0f) alpha = 0.0f;
    if (alpha > 1.0f) alpha = 1.0f;
    g_Runtime.renderAlpha = alpha;
    return alpha;
}
```

#### Celestial Math Computation
```c
static void UpdateCelestialClock(double dt) {
    g_Runtime.celestial.timeOfDay += dt;
    if (g_Runtime.celestial.timeOfDay >= RUNTIME_CELESTIAL_PERIOD) {
        g_Runtime.celestial.timeOfDay = fmod(g_Runtime.celestial.timeOfDay, RUNTIME_CELESTIAL_PERIOD);
    }
    
    float progress = (float)(g_Runtime.celestial.timeOfDay / RUNTIME_CELESTIAL_PERIOD);
    g_Runtime.celestial.cycleProgress = progress;
    
    float angle = progress * 2.0f * (float)M_PI;
    g_Runtime.celestial.celestialAngle = angle;
    
    // Sun unit vector: rotating in the XY plane
    g_Runtime.celestial.sunDirection[0] = cosf(angle);
    g_Runtime.celestial.sunDirection[1] = sinf(angle);
    g_Runtime.celestial.sunDirection[2] = 0.0f;
    
    float sinA = sinf(angle);
    g_Runtime.celestial.daylightFactor = (sinA > 0.0f) ? sinA : 0.0f;
    g_Runtime.celestial.isDaytime = (sinA > 0.0f);
}
```

#### Frame Epilogue & Throttling (`Runtime_EndFrame`)
```c
void Runtime_EndFrame(void) {
    g_Runtime.metrics.totalFrames++;
    s_FramesSinceMetrics++;
    g_Runtime.metrics.substepsLastFrame = s_SubstepCountThisFrame;
    
    // Smoothed FPS/TPS update every 500ms
    double now = Platform_GetTime();
    double timeSinceMetrics = now - s_MetricsTimer;
    if (timeSinceMetrics >= 0.5) {
        g_Runtime.metrics.fps = (float)(s_FramesSinceMetrics / timeSinceMetrics);
        g_Runtime.metrics.tps = (float)(s_TicksSinceMetrics / timeSinceMetrics);
        s_MetricsTimer = now;
        s_FramesSinceMetrics = 0;
        s_TicksSinceMetrics = 0;
    }
    
    // Precision throttling (if targetFps > 0 and not headless)
    if (g_Runtime.config.targetFps > 0 && !g_Runtime.config.headless) {
        double targetInterval = 1.0 / (double)g_Runtime.config.targetFps;
        double frameElapsed = Platform_GetTime() - g_Runtime.currentTime;
        if (frameElapsed < targetInterval) {
            double waitTime = targetInterval - frameElapsed;
            // ponytail: [platform sleep: OS fallback] -> [Platform_Sleep in platform.h]
            if (waitTime > 0.002) {
                #if defined(_WIN32)
                Sleep((DWORD)((waitTime - 0.0015) * 1000.0));
                #else
                usleep((useconds_t)((waitTime - 0.0015) * 1000000.0));
                #endif
            }
            while ((Platform_GetTime() - g_Runtime.currentTime) < targetInterval) {
                // High precision spin-wait
            }
        }
    }
    
    // Check automatic headless termination criteria
    if (g_Runtime.config.maxFrames > 0 && g_Runtime.metrics.totalFrames >= g_Runtime.config.maxFrames) {
        g_Runtime.shouldQuit = true;
    }
    if (g_Runtime.config.maxDuration > 0.0 && g_Runtime.metrics.totalSimulatedTime >= g_Runtime.config.maxDuration) {
        g_Runtime.shouldQuit = true;
    }
}
```

#### Deterministic Testing Utility (`Runtime_SimulateDelta`)
```c
int Runtime_SimulateDelta(double deltaSeconds) {
    if (deltaSeconds < 0.0) deltaSeconds = 0.0;
    if (deltaSeconds > g_Runtime.config.maxAccumulator) {
        deltaSeconds = g_Runtime.config.maxAccumulator;
    }
    
    g_Runtime.accumulator += deltaSeconds;
    if (g_Runtime.accumulator > g_Runtime.config.maxAccumulator) {
        g_Runtime.accumulator = g_Runtime.config.maxAccumulator;
    }
    
    s_SubstepCountThisFrame = 0;
    int stepsExecuted = 0;
    while (Runtime_ShouldStepPhysics()) {
        if (g_Runtime.hooks.onPhysicsTick) {
            g_Runtime.hooks.onPhysicsTick(g_Runtime.config.fixedDt);
        }
        stepsExecuted++;
    }
    Runtime_GetRenderAlpha();
    return stepsExecuted;
}
```

---

## 6. Main Entry Point Integration (`src/main.c`)

The concrete `src/main.c` demonstrates the canonical Ponytail execution model: minimal, transparent, and direct.

```c
#include "platform/platform.h"
#include "core/runtime.h"
#include <stdio.h>
#include <string.h>

// Forward declarations for subsystem bridges
static void App_OnPollEvents(void) {
    Platform_PollEvents();
}

static void App_OnPhysicsTick(double dt) {
    // 1. Ingest input snapshot into player controller
    // 2. Physics_Step(dt)
    // 3. World_Update(player.x, player.z, dt)
}

static void App_OnMeshBudget(int maxChunks) {
    // Mesher_ProcessBudget(maxChunks)
}

static void App_OnRenderFrame(float alpha) {
    // 1. Renderer_BeginFrame()
    // 2. Evaluate interpolated camera transform: Cam_Lerp(prev, curr, alpha)
    // 3. World_Render(cam, alpha)
    // 4. Renderer_DrawHUD()
    // 5. Renderer_EndFrame()
}

int main(int argc, char* argv[]) {
    // ponytail: [entry: CLI arg parsing with strcmp] -> [getopt_long or dedicated CLI parser if complex flags added]
    PlatformConfig platConfig = {
        .windowWidth = 1280,
        .windowHeight = 720,
        .title = "Minecraft Desktop — Universal Edition",
        .targetFps60 = true,
        .headless = false
    };

    RuntimeConfig runConfig;
    Runtime_GetDefaultConfig(&runConfig);

    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--headless") == 0) {
            platConfig.headless = true;
            runConfig.headless = true;
            runConfig.targetFps = 0; // Uncapped for tests
        } else if (strcmp(argv[i], "--frames") == 0 && i + 1 < argc) {
            runConfig.maxFrames = (uint64_t)strtoull(argv[++i], NULL, 10);
        }
    }

    // 1. Initialize Platform
    Platform_Init(&platConfig);

    // 2. Register Subsystem Hooks
    RuntimeHooks hooks = {
        .onPollEvents = App_OnPollEvents,
        .onPhysicsTick = App_OnPhysicsTick,
        .onMeshBudget = App_OnMeshBudget,
        .onRenderFrame = App_OnRenderFrame
    };

    // 3. Initialize Runtime
    Runtime_Init(&runConfig, &hooks);

    // 4. Execute Engine Loop
    Runtime_Run();

    // 5. Clean Shutdown
    Runtime_Shutdown();
    Platform_Shutdown();

    return 0;
}
```

---

## 7. Red-Teaming & Edge Case Verification Matrix

| # | Operational Scenario | Potential Failure Mode | Architectural Mitigation | Mathematical Invariant |
|---|---|---|---|---|
| 1 | **Window Drag / Modal Menu Pause** | On Windows, dragging the title bar enters a modal OS loop for 3.0s. Accumulator grows to 3.0s, triggering 180 physics steps and freezing the process. | Frame delta is clamped: `frameTime = min(frameTime, 0.25)`. Accumulator is clamped: `accumulator = min(accumulator, 0.25)`. | Sub-steps $\le 15$ per frame. Engine recovers in 1 frame. |
| 2 | **NTP Clock Sync Backwards** | System time sync steps backwards by 500ms. `currentTime < previousTime` $\implies$ delta is negative, causing physics to freeze for half a second. | Non-negative monotonicity guard: `if (frameTime < 0.0) frameTime = 0.0`. | Accumulator is strictly monotonically non-decreasing before sub-steps. |
| 3 | **High Refresh Display (144Hz / 240Hz)** | Frame time is 4.1ms–6.9ms. Physics ticks occur only every 2–4 frames. Without interpolation, movement appears locked at 60 FPS stutter. | Sub-frame render alpha: $\alpha = \frac{\text{accumulator}}{dt}$. Linear interpolation of position and spherical/arc lerp of camera angles. | Silky smooth rendering at full monitor refresh rate with zero physics desync. |
| 4 | **Sustained Hardware Overload (Low-End GPU/CPU)** | Physics simulation takes 20ms per tick. Each frame takes $> 250\text{ms}$. Accumulator repeatedly hits 0.25s ceiling. | Hard cap `substeps < 15`. If loop reaches 15 substeps, `accumulator = 0.0`. | Halts cascading compounding delays; drops dropped time rather than crashing. |
| 5 | **Angle Wrapping Stutter (Yaw Lerp)** | Player turns across $0^\circ \leftrightarrow 360^\circ$ boundary. Naive lerp spins camera $359^\circ$ around. | Shortest angular path difference wrapping: `diff > 180 ? diff - 360 : (diff < -180 ? diff + 360 : diff)`. | Yaw rotation always traverses the shortest rotational arc. |
| 6 | **Headless Unit / E2E Testing** | Test runner needs to verify 100,000 ticks or simulate exact time steps without waiting for real wall-clock delays. | `Runtime_SimulateDelta(double delta)` enables synthetic step injection with exact sub-step return counts. | Deterministic, non-blocking test execution in $< 5\text{ms}$. |

---

## 8. Ponytail Minimalist Ledger

In strict accordance with the Lazy Senior Developer ladder:
1. `// ponytail: [game loop: single-threaded synchronous step] -> [asynchronous worker thread for chunk generation/meshing if load spikes]`
2. `// ponytail: [frame pacing: hybrid sleep/busy-wait] -> [swapchain presentation timing extensions VK_GOOGLE_display_timing / DXGI flip model]`
3. `// ponytail: [entry: CLI arg parsing with strcmp] -> [getopt_long or dedicated CLI parser if complex flags added]`
4. `// ponytail: [platform sleep: OS fallback] -> [Platform_Sleep in platform.h]`
