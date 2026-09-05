# Architectural & Runtime Specification Report
**Project:** Minecraft Desktop — Universal 1-Click Native Edition  
**Agent:** spec_miner_arch (Specification Miner & Systems Architect)  
**Standard:** Ponytail Minimal-Complexity Principles & Max-Pro Polymath Framework  
**Date:** 2026-09-03  
**Status:** RATIFIED ARCHITECTURAL SPECIFICATION  

---

## 1. Executive Summary & The Universal Distribution Imperative

The core architectural objective for Minecraft Desktop is uncompromising: **A user must be able to download an archive or executable from a GitHub Release onto any standard Windows, Linux, or macOS desktop, extract it anywhere (or run directly from a USB thumb drive), double-click, and enter an interactive voxel world in under 80 milliseconds—with ZERO external runtime installations, ZERO missing DLL errors, ZERO administrative UAC prompts, and ZERO configuration.**

Every architectural decision, data layout, memory allocation pattern, linker flag, and packaging rule documented in this report directly enforces this distribution imperative. When architectural cleverness collides with runtime portability, portability wins unconditionally.

```
[GitHub Release] ---> [Download Archive / Binary] ---> [Extract Anywhere] ---> [Double Click]
                                                                                      │
                                                                   ┌──────────────────┴──────────────────┐
                                                                   ▼                                     ▼
                                                            < 80ms Cold Boot                     Zero Missing DLLs
                                                            < 15MB Binary Size                   Zero Registry Writes
                                                            100% Offline Capable                 Zero Admin Elevation
```

---

## 2. Features Discovered

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|----------|---------|-------------|--------|---------|----------------|----------------|
| 1 | Runtime/Platform | Windows Native PE Executable | Statically linked Windows PE binary requiring only standard OS system DLLs present since Windows 7 SP1 | OS execution request, command line | Native Win32 window, OpenGL context, running game process | Displays fatal error message box and terminates cleanly if OpenGL 3.3 unsupported | `docs/01` §2.5, `docs/05` §2.1 |
| 2 | Runtime/Platform | Linux Portable ELF Binary | Linux x86_64 binary built against glibc 2.31 baseline (Ubuntu 20.04) or statically linked with musl | OS execution request | Native X11/Wayland window, OpenGL context | Logs error to stderr and exits cleanly if display server unavailable | `docs/01` §2.5, `docs/05` §2.1 |
| 3 | Runtime/Platform | macOS Universal 2 Fat Binary | Dual-architecture Mach-O fat binary containing native x86_64 and arm64 slices merged via `lipo` | OS execution request | Native Cocoa window, OpenGL context | Logs architecture error if OS version < 11.0 | `docs/01` §2.5, `docs/05` §2.1 |
| 4 | Execution/Portability | Portable Base Path Resolution | Runtime detection of binary physical directory across Windows/Linux/macOS; sets CWD to binary folder | `argv[0]`, `GetModuleFileNameW`, `/proc/self/exe`, `_NSGetExecutablePath` | Canonicalized absolute `g_BasePath` string | Falls back to `./` if platform API fails | `docs/05` §3 |
| 5 | Execution/Portability | Portable Relative Saves Directory | World data and configuration stored strictly in `<BasePath>/saves/` relative to executable | World save/load commands, chunk dirty flags | Binary world save files (`world1.dat` or region files) | If directory is read-only, issues in-game HUD warning and falls back to OS temp cache | `ORIGINAL_REQUEST.md` R1, `docs/05` §3.1 |
| 6 | Execution/Security | Zero-UAC Manifest Embedding | Win32 application manifest requesting `asInvoker` execution level | Windows Shell process spawn | Process executes in standard user context without UAC prompt | N/A (Windows OS strictly respects manifest) | `docs/05` §4.1 |
| 7 | Execution/Display | Per-Monitor DPI Awareness | Win32 manifest configuration for `PerMonitorV2` / `PerMonitor` DPI scaling | Display DPI changes / multi-monitor movement | Crisp unscaled framebuffer matching native physical display pixels | Falls back to system DPI if V2 unsupported | `docs/05` §4.1 |
| 8 | Execution/Security | AV False-Positive Elimination | Raw uncompressed PE/ELF machine code with standard section headers, strictly banning runtime packers (UPX) | Antivirus heuristic scanners, SmartScreen | High trust score, zero generic trojan heuristics | Unsigned binary warnings mitigated by standard PE metadata | `docs/05` §4 |
| 9 | Runtime Architecture | Statically Linked Raylib Engine | Pure C99/C++17 engine statically linked against Raylib, libc, and system OpenGL | User input, platform window events | 60+ FPS rendered frames, audio stream | Reports fatal error and terminates if window creation fails | `docs/01` §2.5 |
| 10 | Engine Core | Deterministic Fixed-Timestep Loop | 60 Hz physics update loop coupled to variable-rate rendering via accumulator | Wall-clock `GetTime()` frame delta | Fixed sub-step physics ticks + render alpha fraction | Clamps frame delta to 0.25s on lag spike/drag | `docs/01` §4.1, `ORIGINAL_REQUEST.md` R2 |
| 11 | Engine Core | Render State Interpolation | Sub-frame lerping of camera and entity transforms between previous and current physics ticks | Previous tick pos, current tick pos, alpha | Smoothed render transform | Exact frame synchronization | `docs/01` §4.1 |
| 12 | Engine Core | Zero-Allocation Memory Arenas | Pre-allocated contiguous memory pools; zero `malloc`/`free` calls inside game loop | Memory requests at startup | Fixed static chunk grid and scratch buffers | Out-of-memory prevented by fixed compile-time limits | `docs/01` §3.1, §5 |
| 13 | World Storage | Cacheline-Optimized Chunk Layout | 16x256x16 voxel chunk represented as flat 64 KB array (`uint8_t`), fitting in L2 cache | Block coordinate (x, y, z) | Block ID byte at flat index | Clamps out-of-bound (x, y, z) access | `docs/01` §5.1, `ORIGINAL_REQUEST.md` R3 |
| 14 | World Storage | Y-Major Voxel Index Ordering | Spatial flat indexing `(y * 256) + (z * 16) + x` optimizing vertical column cache locality | Local chunk coordinates x, y, z | Integer array offset 0..65535 | Bitmask clamp `(y << 8) \| (z << 4) \| x` | `docs/01` §5.1, `docs/06` §2.2 |
| 15 | World Storage | Static Toroidal World Grid | Fixed 17x17 chunk array (radius 8, 289 chunks, ~18.5 MB RAM) centered on player | Player chunk coordinate (X, Z) | Contiguous chunk buffer in BSS segment | Ring-buffer toroidal wrapping on movement | `docs/01` §5.2 |
| 16 | World Storage | Sparse Sub-Chunk Section Model | Empty air 16x16x16 sub-chunk sections omitted from memory allocation and meshing | Chunk height slices | Active non-empty section list | Skips empty air passes entirely | `ORIGINAL_REQUEST.md` R3, `docs/06` §2.1 |
| 17 | Meshing | Interleaved Budget-Capped Meshing | Main-thread mesh generation capped at 1-2 chunks / frame (<= 1.5 ms budget), sorted by distance | Dirty chunk queue, camera position | Updated chunk VBO/VAO | Defers excess dirty chunks to subsequent frames | `docs/01` §4.3 |
| 18 | Meshing/Rendering | 4-Byte Packed Voxel Vertex | Single uint32_t encoding X(5), Y(9), Z(5), Normal(3), Texture(8), AO(2) | Voxel face parameters | 32-bit packed integer vertex | Mask truncation prevents bit overflow | `docs/01` §5.3 |
| 19 | Meshing/Rendering | Scratchpad Linear Mesh Allocator | Static global vertex scratchpad buffer eliminating dynamic mesh reallocation | Quad vertices emitted by mesher | Contiguous vertex array ready for `glBufferSubData` | Truncates if theoretical max exceeded | `docs/01` §5.4 |
| 20 | Rendering | OpenGL 3.3 Core Profile Pipeline | Direct modern OpenGL pipeline with custom packed voxel vertex and fragment shaders | Packed VBO, Projection-View matrix uniform | Screen frame buffer rendering | Graceful fallback to GLES 2.0 if core 3.3 unavailable | `docs/01` §2.5, `docs/05` §6 |
| 21 | Asset Pipeline | Embedded Texture Atlas (.rodata) | Master 256x256 pixel atlas compiled directly into binary symbols via byte array / `#embed` | Atlas byte array in memory | GPU 2D Texture ID (`GL_TEXTURE_2D`) | Hardcoded fallback magenta texture if atlas corrupt | `ORIGINAL_REQUEST.md` R4, `docs/04` §1 |
| 22 | Asset Pipeline | Texel Normalization & Bleed Inset | Mathematical UV derivation for 16x16 tiles with sub-texel half-margin inset epsilon | Block type, face direction | UV bounding coordinates (u0, v0, u1, v1) | Defaults to error tile slot (15, 15) if unknown | `docs/04` §3.2 |
| 23 | Asset Pipeline | Embedded ASCII Font Reservation | Bitmap font characters 0-127 embedded in atlas rows 12-15 for zero-dependency HUD text | ASCII char code, screen position | Textured UI quads | Renders unmapped chars as default glyph | `docs/04` §3.3 |
| 24 | Audio | Procedural Software Audio Synth | Real-time procedural 8-bit sound generator (LFSR noise, square/triangle waves, ADSR) | Sound event trigger (break, place, step, jump) | 44.1 kHz PCM audio sample buffer | Voice-stealing limiter if 16 voices saturated | `ORIGINAL_REQUEST.md` R4, `docs/04` §6 |
| 25 | CI/CD | GitHub Actions Multi-OS Matrix | Production workflow building Windows, Linux, and macOS standalone packages in parallel | GitHub commit tag (v*) or pull request | 3 platform release archives + checksums | Fails workflow if linker audit detects banned DLL | `docs/05` §5 |
| 26 | CI/CD | Dynamic Linker Audit Gate | Automated verification using `dumpbin` (Win), `ldd`/`objdump` (Linux), `otool` (macOS) | Compiled binary artifact | Pass/Fail validation output | CI step fails immediately if dynamic runtime linked | `docs/05` §2, §7 |
| 27 | Packaging | Standalone Universal Release Bundle | Self-contained zero-installer zip/tar containing binary, saves folder, and README | Built executables and minimal assets | `*.zip` and `*.tar.gz` release archives | Checksum verification via SHA256SUMS.txt | `docs/05` §5, §6 |
| 28 | Code Standard | Ponytail Minimal-Complexity Architecture | Zero unrequested abstractions, minimal code, YAGNI, explicit `// ponytail:` comment tags | Specification & code implementations | Clean, minimal, verifiable codebase | Rejection of unnecessary dependencies or layers | `ORIGINAL_REQUEST.md` §Ponytail, `docs/01` §7 |

---

## 3. Edge Cases & Observed / Documented Behaviors

| # | Feature | Input / Condition | Observed / Documented Behavior |
|---|---------|-------------------|--------------------------------|
| 1 | Portable Path Resolver | Application launched via Windows desktop shortcut (CWD set to `%USERPROFILE%`) | Resolver queries `GetModuleFileNameW`, strips filename, and calls `SetCurrentDirectoryA(g_BasePath)`. Saves directory resolves adjacent to binary, NOT in `%USERPROFILE%`. |
| 2 | Portable Path Resolver | Linux executable launched via symbolic link in `/usr/local/bin` | `readlink("/proc/self/exe")` resolves canonical physical binary location, ensuring relative folders remain co-located with target binary. |
| 3 | Portable Saves Engine | Executable launched from read-only media (e.g. read-only USB, CD-ROM, locked network share) | Write test to `<BasePath>/saves/` fails; engine catches failure, displays in-game notification, and temporarily routes saves to OS temp directory (`GetTempPathW` / `/tmp`) to prevent crashing. |
| 4 | Fixed-Timestep Loop | Window drag, resize, or debugging breakpoint causing 3-second frame pause | Frame delta reaches 3.0s; accumulator clamping kicks in (`if (frameTime > 0.25f) frameTime = 0.25f`), preventing the "Spiral of Death" where hundreds of physics steps would freeze the engine. |
| 5 | Interleaved Meshing | Player teleports or rapidly loads 50 dirty chunks simultaneously | Dirty chunks are queued and sorted by Manhattan distance; engine strictly meshes a maximum of 2 chunks per frame (<= 1.5 ms budget). Framerate stays locked at 60 FPS without chunk hitching. |
| 6 | Texture Sampling | Perspective camera viewing block at extreme grazing angle under linear filtering | Sub-texel inset epsilon prevents floating-point UV leakage across adjacent 16x16 atlas tiles (eliminates texel bleeding artifact). |
| 7 | Dynamic Linker Audit | Binary inadvertently compiled without `/MT` or `-static-libgcc`, linking `VCRUNTIME140.dll` | CI audit gate runs `dumpbin /dependents` (or `objdump`), detects forbidden import, fails the build immediately with a non-zero exit code. |
| 8 | Linux Deployment | Linux binary executed on an older enterprise distribution (e.g. CentOS 7 / Debian 10) | If compiled on modern Ubuntu without baseline pinning, dynamic loader aborts with `GLIBC_2.38 not found`. Spec mandates building on Ubuntu 20.04 (glibc 2.31) or static musl to ensure universal compatibility. |
| 9 | macOS Deployment | Binary launched on Apple Silicon (M1/M2/M3) vs. Intel Mac (x86_64) | Mach-O fat binary contains both arm64 and x86_64 slices via `lipo`. OS kernel executes native slice directly with zero Rosetta translation overhead. |
| 10 | Antivirus Scanning | Executable subjected to heuristic scan by Microsoft Defender or VirusTotal | Executable has zero UPX packer compression, standard PE section layout, embedded version metadata, and manifest; avoids generic heuristic flagging (`ML.Attribute.HighConfidence`). |
| 11 | Sparse Sub-Chunks | Chunk contains 256 height of void / air (e.g., above build surface) | Section allocation table skips empty 16x16x16 blocks. Memory allocation and meshing loops skip 12 out of 16 sections, reducing memory and draw calls by 75%. |
| 12 | Audio Synthesizer | Multiple explosion, dig, and footstep sound effects triggered in identical physics tick | Real-time mixer voice allocator limits simultaneous voices to 16, applying voice-stealing to oldest low-priority voice. Zero memory allocation, zero audio buffer underrun. |

---

## 4. Architectural Boundaries & System Topology

The engine is partitioned into five strictly decoupled subsystems communicating through flat memory buffers and explicit function calls. Object inheritance, dynamic dispatch tables (vtables), and heap allocation in hot paths are strictly banned.

```
+-------------------------------------------------------------------------------+
|                            OPERATING SYSTEM LAYER                             |
|       Windows (Win32)      |       Linux (X11/Wayland)    |    macOS (Cocoa)  |
+-------------------------------------------------------------------------------+
                                        │
                                        ▼
+-------------------------------------------------------------------------------+
|                             PLATFORM / CORE LAYER                             |
|  - Windowing, Events & Raw Input Capture (Raylib Core / GLFW)                 |
|  - OpenGL 3.3 Core Context Creation                                           |
|  - High-Resolution Multimedia Timer (winmm timeBeginPeriod / clock_gettime)   |
|  - Base Path Resolution (InitPortablePaths)                                   |
+-------------------------------------------------------------------------------+
                                        │
                                        ▼
+-------------------------------------------------------------------------------+
|                              CORE ENGINE RUNTIME                              |
|  - Deterministic Fixed-Timestep Loop (PHYSICS_HZ = 60, DT = 0.01667s)         |
|  - Spiral-of-Death Accumulator Clamping (MAX_FRAME_TIME = 0.25s)             |
|  - Render State Interpolator (Alpha = Accumulator / FIXED_DT)                 |
|  - Global Static Memory Arenas (Zero heap allocation in game loop)            |
+-------------------------------------------------------------------------------+
       │                                │                               │
       ▼                                ▼                               ▼
+---------------------+      +---------------------+      +---------------------+
|  PHYSICS SUBSYSTEM  |      |   WORLD SUBSYSTEM   |      |  RENDER & MESHING   |
| - AABB Sweep Tests  |      | - 17x17 Toroidal    |      | - Budgeted Mesher   |
| - Gravity (g=0.08)  |      |   Chunk Grid (289)  |      |   (Max 2 chunks/fr) |
| - Drag & Friction   |      | - 64KB Contiguous   |      | - 4-Byte Packed     |
| - Step-up (0.6m)    |      |   Y-Major Chunks    |      |   Vertex VBOs       |
| - Amanatides-Woo    |      | - Sparse Sections   |      | - Direct OpenGL 3.3 |
|   DDA Raymarching   |      | - Portable Disk I/O |      |   Batch Draw Calls  |
+---------------------+      +---------------------+      +---------------------+
                                                                │
                                                                ▼
                                                     +---------------------+
                                                     |   ASSET & AUDIO     |
                                                     | - Embedded Atlas    |
                                                     |   (.rodata byte arr)|
                                                     | - Realtime Synth    |
                                                     |   (LFSR + Waves)    |
                                                     +---------------------+
```

### Subsystem Interface Contracts & Allocation Budgets

| Subsystem | Primary Responsibility | Memory Lifetime | In-Loop Heap Allocations | Target CPU Budget |
| :--- | :--- | :--- | :--- | :--- |
| **Platform/Core** | Window lifecycle, raw input polling, timing | Process lifetime | **0 bytes** | < 0.50 ms |
| **Physics** | Fixed-timestep kinematic integration, AABB sweeps, DDA | Frame lifetime | **0 bytes** | <= 1.50 ms |
| **World Storage** | 17x17 toroidal grid, block queries, disk serialization | Persistent BSS array | **0 bytes** | <= 1.00 ms |
| **Meshing** | Greedy or naive face culling, vertex packing | Scratchpad buffer | **0 bytes** | <= 2.00 ms |
| **Renderer** | Dynamic VBO streaming, camera matrices, GL draw calls | GPU VRAM buffers | **0 bytes** | <= 2.50 ms |
| **Audio Synth** | Real-time procedural PCM waveform synthesis callback | OS audio buffer | **0 bytes** | < 0.50 ms |
| **Idle / VSync** | Frame presentation, monitor refresh synchronization | Frame interval | **0 bytes** | ~ 10.66 ms |

---

## 5. Platform Linkage & Universal Distribution Contracts

### 5.1. Windows PE Contract (`minecraft.exe`)
- **CRT Strategy**: Statically linked via MSVC `/MT` or GCC MinGW `-static-libgcc -static`.
- **Permitted Import Libraries**:
  - `KERNEL32.dll`: Memory, thread, filesystem, process APIs.
  - `USER32.dll`: Window creation, message pump, raw input.
  - `GDI32.dll`: Device context management, pixel format descriptors.
  - `OPENGL32.dll`: Standard OpenGL ICD dispatch table.
  - `WINMM.dll`: `timeBeginPeriod(1)` / `timeEndPeriod(1)` for 1ms timer precision.
  - `SHELL32.dll`: Command-line arguments and shell path operations.
- **Strictly Banned Imports**:
  - `VCRUNTIME140.dll`, `MSVCP140.dll` (causes crashes on machines lacking Visual C++ Redistributable).
  - `D3DCompiler_*.dll`, `DXGI.dll` (DirectX dependencies are forbidden).
  - Dynamic game libraries: `raylib.dll`, `glfw3.dll` (must be statically linked into executable).
- **Resource Script (`res/resource.rc`)**:
  - Embeds high-resolution application icon (`101 ICON "res/icon.ico"`).
  - Embeds standard Win32 `VERSIONINFO` metadata (Company, Description, Copyright, Version).
  - Embeds application manifest (`res/app.manifest`) configuring `asInvoker` security and `PerMonitorV2` DPI scaling.

### 5.2. Linux ELF Contract (`minecraft`)
- **Glibc Ceiling**: Built strictly on Ubuntu 20.04 (`glibc 2.31`) or statically linked with `musl`. Binaries compiled on newer glibc versions will fail to load on enterprise and LTS distributions.
- **Allowed Dynamic Libraries**:
  - `libc.so.6`, `libm.so.6`, `libpthread.so.0`, `libdl.so.2`, `librt.so.1`, `libGL.so.1`, `libX11.so.6`.
- **System Packages**: X11, Wayland, Mesa OpenGL development libraries configured in CI.

### 5.3. macOS Universal Binary Contract (`minecraft`)
- **Architecture**: Universal 2 Fat Binary (`x86_64` + `arm64`) generated using `lipo -create`.
- **Deployment Target**: `MACOSX_DEPLOYMENT_TARGET=11.0` (Big Sur), covering all Apple Silicon Macs and Intel Macs since 2013.
- **Native Frameworks**: `OpenGL`, `Cocoa`, `IOKit`, `CoreVideo`.
- **Stripping**: `strip -x` to remove local symbols and minimize binary size.

---

## 6. Portable Storage & Base-Path Engine

To guarantee zero configuration, the engine implements native base-path resolution executed before any file operations:

```c
// Native Base Path Resolution across all desktop platforms
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#if defined(_WIN32)
    #include <windows.h>
#elif defined(__linux__)
    #include <unistd.h>
    #include <linux/limits.h>
#elif defined(__APPLE__)
    #include <mach-o/dyld.h>
#endif

static char g_BasePath[1024] = {0};

void InitPortablePaths(void) {
#if defined(_WIN32)
    wchar_t widePath[MAX_PATH];
    GetModuleFileNameW(NULL, widePath, MAX_PATH);
    WideCharToMultiByte(CP_UTF8, 0, widePath, -1, g_BasePath, sizeof(g_BasePath), NULL, NULL);
    char* lastSlash = strrchr(g_BasePath, '\\');
    if (lastSlash) *(lastSlash + 1) = '\0';
    SetCurrentDirectoryA(g_BasePath);
#elif defined(__linux__)
    char procPath[PATH_MAX];
    ssize_t len = readlink("/proc/self/exe", procPath, sizeof(procPath) - 1);
    if (len != -1) {
        procPath[len] = '\0';
        char* lastSlash = strrchr(procPath, '/');
        if (lastSlash) *(lastSlash + 1) = '\0';
        strncpy(g_BasePath, procPath, sizeof(g_BasePath) - 1);
        chdir(g_BasePath);
    }
#elif defined(__APPLE__)
    char applePath[1024];
    uint32_t size = sizeof(applePath);
    if (_NSGetExecutablePath(applePath, &size) == 0) {
        char* lastSlash = strrchr(applePath, '/');
        if (lastSlash) *(lastSlash + 1) = '\0';
        strncpy(g_BasePath, applePath, sizeof(g_BasePath) - 1);
        chdir(g_BasePath);
    }
#endif
}
```

### Save System Policy:
- Directory: `<BasePath>/saves/`.
- File naming: `<BasePath>/saves/world1.dat`.
- Read-only fallback: If write permissions fail (e.g. read-only flash drive), the engine notifies the user on the HUD and falls back to a temporary cache directory rather than terminating.

---

## 7. Mathematical Formulations & Physics Loop

### 7.1. Game Loop & Accumulator
- Accumulator update:
  `accumulator = accumulator + min(frameTime, 0.25f)`
- Render interpolation factor:
  `alpha = accumulator / FIXED_DT, where FIXED_DT = 1.0f / 60.0f`
- Interpolated render position:
  `pos_render = pos_prev * (1.0f - alpha) + pos_curr * alpha`

### 7.2. Canonical Physics Constants
- Physics Tick Rate: 20 TPS (0.05s) or 60 Hz (0.01667s) sub-step.
- Gravity: g = 0.08 blk/tick^2. Velocity update: `vy = (vy - 0.08) * 0.98`.
- Drag: Horizontal velocity decay `vx = vx * 0.98`, `vz = vz * 0.98`.
- Ground Friction: `vx = vx * 0.546`, `vz = vz * 0.546` when on ground.
- Jump Impulse: `vy = 0.42 blk/tick`.
- Player AABB: 0.6m x 1.8m x 0.6m, Eye height: 1.62m, Auto-step: 0.6m.
- Raycast DDA Reach: 5.0 blocks.

### 7.3. 4-Byte Packed Vertex Bitfield Layout
`Data = (X & 0x1F) | ((Y & 0x1FF) << 5) | ((Z & 0x1F) << 14) | ((Face & 0x7) << 19) | ((Tex & 0xFF) << 22) | ((AO & 0x3) << 30)`
- X in [0..16]: 5 bits (offset 0)
- Y in [0..256]: 9 bits (offset 5)
- Z in [0..16]: 5 bits (offset 14)
- Face Direction: 3 bits (offset 19)
- Texture Slot: 8 bits (offset 22)
- Ambient Occlusion: 2 bits (offset 30)
- **Total:** 32 bits (4 bytes).

---

## 8. Memory Model, Cache Alignment & Vertex Quantization

### 8.1. 64 KB Cacheline-Optimized Chunk Layout
Each chunk is an exact contiguous block column of 16x256x16 voxels stored as 8-bit unsigned integers (`uint8_t`):
- Total bytes: 16 * 256 * 16 = 65,536 bytes (exactly 64 KB).
- Exactly matches standard CPU L2 cache lines (64 bytes) and cache capacities (512 KB to 1 MB).
- Indexing is Y-major: `Index(x, y, z) = (y << 8) | (z << 4) | x`.
- Neighbor voxel queries within the same horizontal plane at height Y occupy identical or adjacent cache lines.

### 8.2. Static Toroidal Active World Grid
- Fixed-size flat array in BSS segment: `RENDER_DISTANCE = 8` (17x17 grid = 289 chunks).
- Total CPU memory: 289 * 64 KB ≈ 18.5 MB RAM.
- Zero dynamic heap allocation for chunk storage during runtime.

### 8.3. Scratchpad Linear Mesh Allocator
- Main-thread mesh generation writes quad vertices into a fixed global scratchpad buffer (`MAX_CHUNK_VERTICES = 65536 * 6`).
- Uploads directly to GPU VBO with a single `glBufferSubData` / `glBufferData` call.
- Zero runtime malloc/free calls during chunk rebuild.

---

## 9. Embedded Asset Pipeline & Procedural Audio Architecture

### 9.1. Zero-Asset Embedded Architecture
To eliminate file path errors, missing asset crashes, and working directory bugs:
- All textures are compiled directly into the executable binary in the `.rodata` segment (via `#embed` or static byte arrays).
- Single 256x256 master texture atlas containing 16x16 slots of 16x16 pixel retro tiles.
- Zero loose PNG or audio files are required for core execution.

### 9.2. Texel Normalization & Bleed Prevention
- Infinitesimal sub-texel half-margin inset epsilon prevents floating-point coordinate leakage across adjacent tile boundaries under perspective projection and bilinear filtering.
- Rows 12-15 of the atlas are reserved for a 16x16 ASCII glyph set (0-127), providing zero-dependency HUD font rendering.

### 9.3. Procedural Audio Synthesizer
- 8-bit software audio synthesizer runs in real-time platform callback.
- Waveform engines:
  - 16-bit Galois Linear Feedback Shift Register (LFSR) for block break / place / footstep noise.
  - Phase-accumulator square waves with pulse width modulation for UI selection blips.
  - Pitch-dropped triangle waves for impact thuds.
  - Ascending exponential frequency sweeps for player jumping.
- 16-voice realtime software mixer buffer writing directly to OS PCM audio stream (44.1 kHz, mono).
- Zero external audio files, zero audio decoders, zero memory allocation.

---

## 10. GitHub Packaging, CI/CD Workflows & Verification Runbook

### 10.1. Multi-OS Matrix Pipeline (`.github/workflows/build_and_release.yml`)
Runs on push to `main`, tags `v*`, and PRs:
1. `windows-x64`: Runner `windows-latest` -> Compiles `res/resource.rc` with `windres` -> Builds with static MinGW GCC or MSVC `/MT` -> Statically links Raylib, standard C runtime, and system DLLs -> Emits `minecraft.exe` -> Audits dynamic links with `dumpbin /dependents` -> Bundles into `minecraft-desktop-windows-x64.zip`.
2. `linux-x64`: Runner `ubuntu-20.04` (glibc 2.31 baseline) -> Installs X11/Wayland/Mesa headers -> Compiles with GCC `-O3 -flto` -> Statically links Raylib -> Links only baseline Linux dynamic libraries -> Emits `minecraft` -> Audits with `ldd` and `objdump` -> Bundles into `minecraft-desktop-linux-x64.tar.gz`.
3. `macos-universal`: Runner `macos-latest` -> Compiles `x86_64` and `arm64` slices targeting macOS 11.0 -> Merges with `lipo -create` -> Strips with `strip -x` -> Audits with `lipo -info` and `otool -L` -> Bundles into `minecraft-desktop-macos-universal.zip`.
4. `release`: On tag `v*`, collects all 3 packages, generates `SHA256SUMS.txt`, and publishes a GitHub Release using `softprops/action-gh-release@v2`.

### 10.2. Release Package Anatomy
```
minecraft-desktop-windows-x64/
├── minecraft.exe              # ~2.5 MB statically compiled executable
├── assets/                    # External overrides / shaders (embedded fallback exists)
│   ├── atlas.png              # 256x256 pixel block texture atlas
│   └── shaders/
│       ├── voxel.vs           # Packed uint32 voxel vertex shader
│       └── voxel.fs           # Ambient occlusion & texturing fragment shader
├── saves/                     # Default world save directory (auto-created)
│   └── world1.dat             # Flat binary voxel chunk serialization
└── README.txt                 # Quickstart guide
```

---

## 11. Ponytail Minimal-Complexity Principles & Tag Registry

The engine adheres strictly to the Lazy Senior Developer ladder:
1. **YAGNI**: No unrequested abstractions, no ECS, no scripting runtimes, no JSON parsers in hot paths.
2. **Standard Platform Features**: Native Win32/POSIX path APIs, standard OpenGL 3.3, native OS windowing via static Raylib.
3. **Contiguous Arrays Over Pointer Graphs**: Eliminates cache misses and pointer-chasing overhead.
4. **Simplification Upgrades**: Explicitly tagged with `// ponytail:` comment markers to allow future upgrades without requiring architecture rewrites.

### Authoritative Subsystem Ponytail Tag Registry:
1. `// ponytail: budget-capped single-thread chunk meshing (max 2 chunks/frame, <1.5ms budget) -> worker thread pool with atomic double-buffered vertex buffers`
2. `// ponytail: static chunk grid array (17x17 chunks around player) -> sparse spatial hash map with asynchronous disk streaming`
3. `// ponytail: static scratchpad VBO upload with glBufferData -> persistent mapped buffers (GL_ARB_buffer_storage) with triple-buffering`
4. `// ponytail: asset folder relative to executable -> embedded virtual filesystem (in-binary assets) via xxd/incbin to achieve true 100% single-file distribution`
5. `// ponytail: nearest-neighbor with zero bleed margin -> sub-texel half-margin inset if mipmapping enabled`
6. `// ponytail: static lookup array indexed by BlockID and FaceDirection -> dynamic block metadata registry`
7. `// ponytail: dynamic 3D BFS flood-fill lighting -> ambient occlusion + directional face shading + vertex daylight factor [upgrade path: compute shader BFS light propagation]`

---

## 12. Existing Workspace State & Toolchain Audit

### Workspace State (`g:/minecraft_desktop`):
- **Source Code**: Currently **zero** `.c`, `.cpp`, or `.h` files exist.
- **Build Scripts**: No `Makefile`, `CMakeLists.txt`, or CI workflow files exist yet.
- **Documentation**: 6 comprehensive architecture and specification files exist in `docs/` (`01` through `06`).
- **Version Control**: Git repository is not yet initialized (no `.git` directory).

### Host System Toolchain Audit (Current Windows Runner):
- **Available Tools**:
  - `git.exe` (`C:\Program Files\Git\cmd\git.exe`)
  - `gh.exe` (`C:\Program Files\GitHub CLI\gh.exe`)
  - `python.exe` (Python 3.13)
  - `winget.exe` (Windows Package Manager)
  - `wsl.exe` (WSL available, `docker-desktop` stopped)
  - `ripgrep` (`15.1.0`)
- **C/C++ Compilers**: GCC / Clang / MSVC are not currently configured in the system PATH.
  - *Recommendation for Milestone 1 Bootstrapping*: In the implementation phase, the orchestrator/implementer can use `winget install LLVM.LLVM` or `winget install MSYS2.MSYS2` / `wsl` / standalone compiler to build and test locally, or execute builds through GitHub Actions CI runners (`windows-latest`, `ubuntu-20.04`, `macos-latest`) where all compilers and libraries are pre-installed.

---

## 13. Comprehensive Acceptance Criteria & Interface Boundaries

1. **Universal Execution Gate**:
   - Single executable runs immediately on fresh Windows 7/10/11, Ubuntu 20.04+, and macOS 11.0+ without installing any prerequisites.
   - Cold start latency from process launch to first rendered frame < 80 ms.
   - Uncompressed binary size < 4.0 MB.
2. **Portability Gate**:
   - Running from arbitrary path or USB drive maintains saves and configuration in `./saves/` adjacent to binary.
   - Read-only parent directory falls back to temp directory without crashing.
3. **Rendering & Simulation Gate**:
   - 60+ FPS at 8-chunk render distance on integrated GPUs (Intel HD 4000 / UHD 620).
   - Zero dynamic heap allocations (`malloc`/`free`) during the render/physics loop.
   - Exact player kinematic fidelity matching canonical constants (g=0.08, air drag 0.98, ground friction 0.546, jump 0.42).