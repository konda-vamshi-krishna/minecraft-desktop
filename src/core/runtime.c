#include "core/runtime.h"
#include "platform/platform.h"
#include <math.h>
#include <string.h>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

// ponytail: [game loop: single-threaded synchronous step] -> [asynchronous worker thread for chunk generation/meshing if load spikes]
// ponytail: [frame pacing: hybrid sleep/busy-wait] -> [swapchain presentation timing extensions VK_GOOGLE_display_timing / DXGI flip model]

static RuntimeState g_Runtime = {0};
static int s_SubstepCountThisFrame = 0;
static double s_MetricsTimer = 0.0;
static uint32_t s_FramesSinceMetrics = 0;
static uint32_t s_TicksSinceMetrics = 0;

static void UpdateCelestialClock(double dt) {
    g_Runtime.celestial.timeOfDay += dt;
    if (g_Runtime.celestial.timeOfDay >= RUNTIME_CELESTIAL_PERIOD) {
        g_Runtime.celestial.timeOfDay = fmod(g_Runtime.celestial.timeOfDay, RUNTIME_CELESTIAL_PERIOD);
    }

    float progress = (float)(g_Runtime.celestial.timeOfDay / RUNTIME_CELESTIAL_PERIOD);
    g_Runtime.celestial.cycleProgress = progress;

    float angle = progress * 2.0f * (float)M_PI;
    g_Runtime.celestial.celestialAngle = angle;

    /* Sun unit vector: rotating in the XY plane */
    g_Runtime.celestial.sunDirection[0] = cosf(angle);
    g_Runtime.celestial.sunDirection[1] = sinf(angle);
    g_Runtime.celestial.sunDirection[2] = 0.0f;

    float sinA = sinf(angle);
    g_Runtime.celestial.daylightFactor = (sinA > 0.0f) ? sinA : 0.0f;
    g_Runtime.celestial.isDaytime = (sinA > 0.0f);
}

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

    // Initial celestial tick
    UpdateCelestialClock(0.0);
}

void Runtime_Shutdown(void) {
    g_Runtime.isRunning = false;
    g_Runtime.isInitialized = false;
}

void Runtime_RequestQuit(void) {
    g_Runtime.shouldQuit = true;
}

bool Runtime_IsRunning(void) {
    return g_Runtime.isRunning && !g_Runtime.shouldQuit;
}

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

float Runtime_GetRenderAlpha(void) {
    float alpha = (float)(g_Runtime.accumulator / g_Runtime.config.fixedDt);
    if (alpha < 0.0f) alpha = 0.0f;
    if (alpha >= 1.0f) alpha = 0.99999f;
    g_Runtime.renderAlpha = alpha;
    return alpha;
}

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
            if (waitTime > 0.002) {
                Platform_Sleep(waitTime - 0.0015);
            }
            while ((Platform_GetTime() - g_Runtime.currentTime) < targetInterval) {
                // High precision spin-wait
            }
        }
    }

    // Check automatic termination criteria
    if (g_Runtime.config.maxFrames > 0 && g_Runtime.metrics.totalFrames >= g_Runtime.config.maxFrames) {
        g_Runtime.shouldQuit = true;
    }
    if (g_Runtime.config.maxDuration > 0.0 && g_Runtime.metrics.totalSimulatedTime >= g_Runtime.config.maxDuration) {
        g_Runtime.shouldQuit = true;
    }
}

void Runtime_StepFrame(void) {
    if (g_Runtime.hooks.onPollEvents) {
        g_Runtime.hooks.onPollEvents();
    }

    Runtime_BeginFrame();

    while (Runtime_ShouldStepPhysics()) {
        if (g_Runtime.hooks.onPhysicsTick) {
            g_Runtime.hooks.onPhysicsTick(g_Runtime.config.fixedDt);
        }
    }

    if (g_Runtime.hooks.onMeshBudget) {
        g_Runtime.hooks.onMeshBudget(2);
    }

    float alpha = Runtime_GetRenderAlpha();
    if (g_Runtime.hooks.onRenderFrame) {
        g_Runtime.hooks.onRenderFrame(alpha);
    }

    Runtime_EndFrame();
}

void Runtime_Run(void) {
    while (Runtime_IsRunning() && !Platform_ShouldClose()) {
        Runtime_StepFrame();
    }
}

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

const RuntimeMetrics* Runtime_GetMetrics(void) {
    return &g_Runtime.metrics;
}

const CelestialClock* Runtime_GetCelestialClock(void) {
    return &g_Runtime.celestial;
}

float Runtime_GetAlpha(void) {
    return g_Runtime.renderAlpha;
}

bool Runtime_IsPaused(void) {
    return g_Runtime.isPaused;
}

void Runtime_SetPaused(bool paused) {
    g_Runtime.isPaused = paused;
}
