# Handoff Report: Architecture, Runtime & Universal Packaging Specification Mining

**Agent:** spec_miner_arch  
**Role:** Specification Miner / Systems & Universal Packaging Architect  
**Working Directory:** `g:/minecraft_desktop/.agents/spec_miner_arch/`  
**Handoff Type:** Hard (Task Complete)  
**Date:** 2026-09-03  

---

## 1. Observation

Direct observations made during investigation of `g:/minecraft_desktop`:

1. **Authoritative Specification Documents:**
   - `ORIGINAL_REQUEST.md` (lines 12–18, 37–53): Mandates R1 Universal One-Click Native Distribution (Windows `.exe` with static CRT, Linux glibc 2.31 ELF, macOS Universal 2 binary, portable `./saves/`), cold start < 80ms, 60+ FPS at 8-chunk render distance, adherence to Ponytail minimal-complexity principles.
   - `docs/01_ARCHITECTURE_AND_RUNTIME.md` (lines 64–76, 114–124, 156–209, 222–232, 248–266, 283–298, 317–334, 340–363): Ratifies C99/C++17 + statically linked Raylib with OpenGL 3.3 Core profile. Disqualifies JVM (GC stutter, 45-120MB bloat, slow startup), Python (AV heuristic detection, GIL), and Bevy/WGPU (35-60MB bloat, Vulkan driver failures). Mandates fixed 60 Hz physics update loop with sub-frame render state interpolation, budget-capped single-thread chunk meshing (max 2 chunks/frame, <1.5ms budget), 64KB cache-aligned chunks (`uint8_t` Y-major layout), 17x17 toroidal world grid (289 chunks, ~18.5 MB RAM in BSS), 4-byte packed uint32 vertex format (88.9% GPU bandwidth savings), and static scratchpad linear mesh allocator (0 heap allocations in game loop).
   - `docs/05_GITHUB_PACKAGING_AND_CI.md` (lines 26–47, 69–102, 118–176, 183–375): Defines dynamic linker audit rules (allowed Win32 imports: KERNEL32, USER32, GDI32, OPENGL32, WINMM, SHELL32; banned: VCRUNTIME140, MSVCP140, D3DCompiler, DXGI), portable base-path resolution (`GetModuleFileNameW`, `/proc/self/exe`, `_NSGetExecutablePath`), Win32 resource script (`res/resource.rc`) embedding icon and `app.manifest` (`asInvoker`, `PerMonitorV2`), raw PE/ELF packaging without UPX, and full 3-platform GitHub Actions matrix CI/CD pipeline (`.github/workflows/build_and_release.yml`).
   - `docs/04_ASSET_PIPELINE_AND_AUDIO.md` (lines 35–42, 94–126, 143–187, 358–400): Specifies embedded zero-asset strategy (texture atlas and ASCII bitmap font compiled directly into binary `.rodata` segment), texel bleed isolation via half-margin inset epsilon, and procedural 8-bit sound synthesis (Galois LFSR noise, square/triangle waveforms, 16-voice mixer) requiring 0 bytes of external audio files.
   - `docs/06_OFFICIAL_MINECRAFT_CANONICAL_SPEC.md` (lines 43–57): Establishes canonical constants: 20 TPS tick rate, player AABB 0.6 x 1.8 x 0.6 m, eye level 1.62 m, downward gravity g = 0.08 blk/tick^2, air drag 0.98, ground friction 0.546, jump impulse 0.42 blk/tick, auto-step 0.6 m, reach distance 5.0 blocks.

2. **Workspace & Toolchain State:**
   - Tool execution: `Get-ChildItem -Recurse -File -Path 'g:/minecraft_desktop'` showed only `ORIGINAL_REQUEST.md`, 6 files in `docs/`, `graphify-out/`, and `.agents/`. Zero C/C++ source files, headers, Makefiles, CMakeLists, or CI scripts exist.
   - Tool execution: `git status` returned `fatal: not a git repository`.
   - Tool execution: `Get-Command` identified `git.exe` (2.x), `gh.exe` (GitHub CLI), `python.exe` (3.13), `winget.exe`, `wsl.exe` (with stopped `docker-desktop`), and `ripgrep`. GCC, Clang, and MSVC `cl.exe` are not currently in the default user PATH.

---

## 2. Logic Chain

1. **From Distribution Mandate to Runtime Selection:**
   - Observation 1 establishes the hard requirement: instant single-click execution with zero prerequisite installations (<15MB, <80ms startup).
   - Candidates requiring runtime VMs (JVM) or dynamic interpreters/packers (Python/PyInstaller) violate either the size, startup time, or AV clearance constraints. Heavy modern Rust engines (Bevy/WGPU) introduce Vulkan driver failures on older integrated GPUs.
   - Therefore, a statically linked C99/C++17 binary using Raylib and OpenGL 3.3 Core (Observation 1) is the only architecture satisfying all R1 criteria simultaneously.

2. **From Portability Mandate to Base-Path and Asset Architecture:**
   - Double-clicking desktop shortcuts sets CWD to `%USERPROFILE%` rather than the game folder (Observation 1, `docs/05`).
   - If assets or save paths are resolved relative to the OS CWD, the application fails to launch or pollutes user directories.
   - Therefore, runtime must execute native executable directory discovery (`GetModuleFileNameW` / `/proc/self/exe` / `_NSGetExecutablePath`) at boot, store saves exclusively in `<BasePath>/saves/`, and embed all textures into `.rodata` alongside procedural audio synthesis, completely eliminating loose disk file vulnerabilities.

3. **From Performance Ceiling to Zero-Allocation Memory Model:**
   - Garbage collection and dynamic heap allocations (`malloc`/`free`) during chunk meshing or physics updates induce cache misses and frame drops (Observation 1, `docs/01`).
   - Allocating 64KB per chunk in a flat contiguous array with Y-major indexing ensures a full chunk fits within the CPU L2 cache. Packing vertices into 4 bytes (`uint32_t`) achieves an 88.9% GPU bandwidth reduction.
   - Therefore, the engine must use static BSS allocations (17x17 chunk grid = 289 chunks, ~18.5 MB RAM) and a reusable scratchpad mesh buffer, guaranteeing 0 bytes allocated in the game loop.

4. **From Ponytail Principles to Interleaved Single-Threaded Meshing:**
   - Spawning background worker thread pools with mutexes introduces synchronization overhead, race conditions, and boilerplate (Observation 1).
   - Capping mesh generation to 1–2 chunks per frame within a strict <= 1.5ms budget maintains 60 FPS deterministically without threading complexity, adhering to Ponytail Rung 1 (YAGNI) and Rung 7 (minimum code that works).

5. **From Host Audit to Implementation Strategy:**
   - Observation 2 demonstrates that the repository is in Greenfield phase (specifications complete, 0 code files written, git not yet initialized).
   - The host system has Git, GitHub CLI, Python, Winget, and WSL.
   - For Milestone 1 bootstrapping, the engine code can be authored in standard C99/C++17 with Raylib, tested locally via toolchain install (e.g., via `winget` or MinGW) or validated via GitHub Actions CI matrix runners (`windows-latest`, `ubuntu-20.04`, `macos-latest`).

---

## 3. Caveats

1. **Local Host Compiler Setup:** While Git, GitHub CLI, and Python are active on the host machine, MSVC/MinGW C compilers are not currently in `%PATH%`. Local compilation during Phase 2 will require installing MinGW/LLVM via Winget or compiling via WSL or validating builds via GitHub Actions.
2. **Audio Callback Hardware Differences:** The procedural synthesizer relies on a fixed 44.1 kHz PCM stream. Audio device sample rate mismatches (e.g. 48 kHz or 96 kHz on modern Windows WASAPI / PipeWire) must be handled by Raylib's internal resampler or an explicit sample rate conversion step in the callback.
3. **Save System Region Format vs. Flat Dat:** While `docs/01` and `docs/05` cite a single flat `world1.dat` binary save for Ponytail simplicity, `docs/06` specifies the full Anvil `.mca` format (32x32 chunks, 8KB header). The Ponytail evolution path clearly maps: `world1.dat` flat binary save -> full Anvil `.mca` region serialization.

---

## 4. Conclusion

The architectural, runtime, and packaging specifications for the Minecraft Desktop project have been exhaustively discovered, red-team audited, and documented.
- The authoritative specification report has been compiled and saved to:
  `g:/minecraft_desktop/.agents/spec_miner_arch/spec_report.md`
- The system topology, interface contracts, memory layouts (64KB chunks, 4-byte packed vertices, static 17x17 grid), platform linkage rules (zero missing DLLs, glibc 2.31, macOS Universal 2), base-path resolver, embedded asset/audio pipeline, and CI/CD matrix pipeline are fully defined.
- The project is 100% prepared to transition to Orchestrator Phase 1 (Test Harness and Infrastructure) and Phase 2 Milestone 1 (Engine Core Implementation).

---

## 5. Verification Method

1. **Inspect Specification Report:**
   - Path: `g:/minecraft_desktop/.agents/spec_miner_arch/spec_report.md`
   - Verify presence of 28 Discovered Features and 12 Edge Cases in standard markdown tables.
   - Verify all 7 Ponytail comment tags are registered and matched to subsystem evolution paths.
2. **Verify File Integrity & Workspace State:**
   ```powershell
   Get-Item g:/minecraft_desktop/.agents/spec_miner_arch/spec_report.md | Select-Object Name, Length
   # Expected length: > 30,000 bytes
   ```
3. **Invalidation Conditions:**
   - Any requirement for external runtimes (JRE, Python, VC++ redistributable) would invalidate Section 1 and Section 5.
   - Dynamic memory allocation (`malloc`/`free`) occurring inside the physics or render loop would invalidate the performance and cache model in Section 4 and Section 8.