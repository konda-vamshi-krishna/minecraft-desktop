## 2026-09-03T07:19:24Z
You are worker_m1.
Your working directory is: g:/minecraft_desktop/.agents/worker_m1/
Project Root: g:/minecraft_desktop

MANDATORY: Read g:/minecraft_desktop/ORIGINAL_REQUEST.md before starting work.
Also read:
- g:/minecraft_desktop/.agents/orchestrator/PROJECT.md
- g:/minecraft_desktop/.agents/explorer_m1_platform/analysis.md
- g:/minecraft_desktop/.agents/explorer_m1_runtime/analysis.md
- g:/minecraft_desktop/.agents/explorer_m1_camera/analysis.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Exclusively Owned Files:
You exclusively own and will write the following files:
- src/platform/platform.h
- src/platform/platform_desktop.c
- src/core/runtime.h
- src/core/runtime.c
- src/core/math_utils.h
- src/main.c
- Makefile
- CMakeLists.txt

Your mission:
Implement Milestone 1 (M1): Architecture, Platform Abstraction, Windowing & Engine Core.
1. Implement src/core/math_utils.h:
   - Value types: Vec2, Vec3, Vec4, Mat4 (column-major float m[16]), AABB, Ray, Plane, Frustum, Camera.
   - Vector arithmetic, dot, cross, normalization.
   - LookAt view matrix and Perspective projection matrix matching OpenGL NDC [-1, 1] with dynamic FOV calculation (Sprint 1.15x, Sneak 0.90x, lambda = 12.0 s^-1).
   - Euler angle clamping: Yaw [0, 360) positive modulo, Pitch [-89, +89] clamping.
   - Closed-form direction vectors: F_look, F_planar, R_planar, U_cam without runtime square roots.
   - Frustum extraction (6 planes normalized) and O(1) p-vertex AABB culling test.
   - Bitshift coordinate conversions: WorldToChunkCoord, WorldToLocalCoord.
   - Zero dynamic memory allocations.

2. Implement src/platform/platform.h and src/platform/platform_desktop.c:
   - Base-path executable discovery: GetModuleFileNameW on Windows, /proc/self/exe on Linux, _NSGetExecutablePath on macOS, setting CWD to the binary folder to eliminate shortcut CWD bugs.
   - Portable saves directory: canary-probed <BasePath>/saves/ (.write_test) with graceful fallback to OS temporary directory (%TEMP% or /tmp).
   - Windowing and input: Raylib integration (with SetExitKey(KEY_NULL) to preserve Escape for Pause Menu, WIN32_LEAN_AND_MEAN / NOGDI / NOUSER guards to prevent header macro collisions).
   - Headless mode: when config.headless == true, bypass window/GL creation, while keeping monotonic high-resolution timing active.
   - High-resolution timing: timeBeginPeriod(1) + QueryPerformanceCounter on Windows, clock_gettime(CLOCK_MONOTONIC) on POSIX.

3. Implement src/core/runtime.h and src/core/runtime.c:
   - Fixed 60 Hz physics loop (dt = 1.0 / 60.0).
   - High-precision double accumulator state machine with 0.25s spiral-of-death clamp.
   - Sub-frame render interpolation alpha calculation (alpha = accumulator / dt).
   - Main game state integration, frame pacing, 60 FPS target throttling.
   - Headless test simulation hooks (Runtime_SimulateDelta).

4. Implement src/main.c:
   - CLI parsing: --headless, --test-m1, --seed <N>, --help.
   - When --test-m1 is passed, run a deterministic validation suite testing base-path resolution, math_utils vector/matrix invariants, frustum culling, fixed 60Hz loop stepping, and exit with code 0 on success.
   - Clean startup, main loop execution, and graceful shutdown.

5. Implement Makefile and CMakeLists.txt:
   - Standard C99/C11 build configuration.
   - Standalone/headless target (using standard C library, zero Raylib dependency needed for testing) as well as full Raylib desktop target.

6. Verification:
   - Run compilation and tests on the machine. Verify that the build succeeds and tests pass.
   - Document commands executed and test outputs in your handoff report.
   - Write a self-contained handoff.md in your working directory and send a message to parent when done.

## 2026-09-03T07:34:48Z
**Context**: URGENT COMPLIANCE DIRECTIVE FOR MILESTONE 1 WORKER
**Content**: 
CRITICAL CONSTRAINT FROM USER/PARENT:
Do NOT download any external binary toolchains (such as w64devkit, MinGW zips, or foreign executables) to the host system. The recent download of `w64devkit.zip` to `C:\Users\PC\tools\` triggered Windows Defender's generic heuristic flag `Trojan:Win32/Vigorf.A`.

Enforce Ponytail minimalism:
1. Do NOT attempt to install or download compilers on the user's host machine. If you downloaded any files in `C:\Users\PC\tools\` or temporary folders, delete and clean them up immediately.
2. Delegate all multi-platform native binary compilation to the GitHub Actions CI/CD matrix (`.github/workflows/build_and_release.yml`).
3. Complete the C source implementations (`src/platform/platform.h`, `src/platform/platform_desktop.c`, `src/core/runtime.h`, `src/core/runtime.c`, `src/core/math_utils.h`, `src/main.c`, `Makefile`, `CMakeLists.txt`) according to the explorer specifications.
4. Conduct all local verification strictly via pure Python test runners (e.g. `tests/test_runner.py`, static syntax checks, or Python/regex audits) without downloading external binaries.
**Action**: Acknowledge immediately, clean up any downloaded tools/zips if present, and complete M1 implementation following this directive.
