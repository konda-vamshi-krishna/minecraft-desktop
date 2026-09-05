# Original User Request

## 2026-09-03T06:50:50Z

A standalone, universal single-click desktop Minecraft game clone distributable directly via GitHub, requiring zero external runtime installations or configuration for end users on Windows, Linux, and macOS. Built strictly following Ponytail minimal-complexity principles and official Minecraft canonical mechanics as specified in `g:/minecraft_desktop/docs/`.

Working directory: g:/minecraft_desktop
Integrity mode: development

## Requirements

### R1. Universal One-Click Native Distribution
A completely portable, single-click executable pipeline requiring zero external dependencies (no separate Java runtime, no Python environment, no system DLL installations). When downloaded from a GitHub release into any folder, it runs immediately.
- Windows standalone `.exe` (statically linked C runtime, system DLLs only).
- Linux portable ELF binary (glibc 2.31 compatible).
- macOS Universal 2 binary (Apple Silicon + Intel x86_64).
- Portable relative base-path resolver storing `./saves/` adjacent to binary.

### R2. Official Canonical Physics & Voxel Interaction
Full mechanical parity with official Minecraft Java Edition kinematic constants (documented in `docs/02_CORE_GAMEPLAY_FEATURES.md` and `docs/06_OFFICIAL_MINECRAFT_CANONICAL_SPEC.md`):
- 20 TPS physics tick rate with sub-frame render interpolation.
- Player AABB collision (0.6 x 1.8 x 0.6m), eye level 1.62m, auto-step 0.6m.
- Exact downward acceleration (g = 0.08 blk/tick^2), air drag (0.98), ground friction (0.546), jump impulse (0.42 blk/tick).
- Fast Voxel Traversal (Amanatides-Woo DDA) for block raymarching up to 5.0 blocks.
- Block destruction timing with hardness stages and placement collision validation.

### R3. Anvil-Compatible Sub-Chunk World Generation
- Sparse 16x16x16 sub-chunk section model (256 height total) with YZX index ordering for optimal cache locality.
- Empty air sections omitted from memory allocation and meshing.
- Multi-octave 2D/3D Simplex procedural terrain with Whittaker biome matrix (Plains, Desert, Mountains, Forest) and 3D cave carve-out.
- 3-axis Greedy Meshing algorithm reducing draw calls and vertex counts by >80% with per-vertex ambient occlusion.

### R4. Embedded Zero-Asset & Audio Pipeline
- Embedded 256x256 retro 16x16 pixel texture atlas compiled directly into binary .rodata (zero loose texture files, zero path resolution bugs).
- Real-time procedural 8-bit sound synthesizer generating canonical audio waveforms (block breaking, placement, footsteps, jump) directly to the platform audio buffer without external audio files.

## Acceptance Criteria

### Universal Execution
- [ ] Single executable file or standalone archive starts with a single click/command on standard desktop OS without pre-installed runtimes.
- [ ] Initial cold start to interactive world under 80ms.
- [ ] Fully portable save/load in `./saves/` directory relative to executable.

### Engine Performance & Mechanics
- [ ] Stable 60+ FPS rendering at minimum 8-chunk render distance on standard integrated GPUs.
- [ ] Exact player movement fidelity matching Minecraft Java physics constants (g=0.08, drag=0.98, friction=0.546).
- [ ] Functional block destruction and placement with exact raycasted voxel grid alignment.
- [ ] Working hotbar selection and block item state machine.

### Architecture & Specification Integrity
- [ ] Complete implementation faithful to the 6 specification documents in `/docs/`.
- [ ] Code adheres to Ponytail minimal-complexity principles (`// ponytail: [limitation/ceiling] -> [upgrade path]`).

## 2026-09-03T07:33:28Z

URGENT DIRECTIVE: Do NOT download any external binary toolchains (such as w64devkit, MinGW zips, or foreign executables) to the host system. The recent download of `w64devkit.zip` to `C:\Users\PC\tools\` triggered Windows Defender's generic heuristic flag `Trojan:Win32/Vigorf.A`. 

Enforce Ponytail minimalism:
1. Do NOT attempt to install or download compilers on the user's host machine.
2. Delegate all multi-platform native binary compilation to the GitHub Actions CI/CD matrix (.github/workflows/build_and_release.yml).
3. Conduct all local verification via pure test runners (e.g. tests/test_runner.py) and static code audits without downloading external binaries.

## 2026-09-03T08:05:49Z

A standalone, universal single-click desktop Minecraft game clone distributable directly via GitHub, requiring zero external runtime installations or configuration for end users on Windows, Linux, and macOS. Built strictly following Ponytail minimal-complexity principles and official Minecraft canonical mechanics as specified in `g:/minecraft_desktop/docs/`.

Working directory: g:/minecraft_desktop
Integrity mode: development

RESUME DIRECTIVE:
Resume execution seamlessly from the existing workspace state in `g:/minecraft_desktop/`. 
- Phase 0 survey and 6 docs in `docs/` are complete.
- E2E testing framework in `tests/` is complete (105/105 tests pass).
- Milestone 1 (Runtime & Engine Core) is implemented in `src/`. Resolve any open review findings noted in `.agents/orchestrator/GATE_STATUS.md` and advance immediately through Milestone 2 (WorldGen & Greedy Meshing), Milestone 3 (Gameplay & Physics), Milestone 4 (Embedded Assets & Audio), and Milestone 5 (GitHub Actions Packaging).
- Strictly enforce Ponytail principles: zero host compiler downloads, zero unnecessary abstractions, and pure test-runner verification.

## Requirements

### R1. Universal One-Click Native Distribution
A completely portable, single-click executable pipeline requiring zero external dependencies (no separate Java runtime, no Python environment, no system DLL installations). When downloaded from a GitHub release into any folder, it runs immediately.
- Windows standalone `.exe` (statically linked C runtime, system DLLs only).
- Linux portable ELF binary (glibc 2.31 compatible).
- macOS Universal 2 binary (Apple Silicon + Intel x86_64).
- Portable relative base-path resolver storing `./saves/` adjacent to binary.

### R2. Official Canonical Physics & Voxel Interaction
Full mechanical parity with official Minecraft Java Edition kinematic constants (documented in `docs/02_CORE_GAMEPLAY_FEATURES.md` and `docs/06_OFFICIAL_MINECRAFT_CANONICAL_SPEC.md`):
- 20 TPS physics tick rate with sub-frame render interpolation.
- Player AABB collision ($0.6 \times 1.8 \times 0.6\text{m}$), eye level $1.62\text{m}$, auto-step $0.6\text{m}$.
- Exact downward acceleration ($g = 0.08\text{ blk/tick}^2$), air drag ($0.98$), ground friction ($0.546$), jump impulse ($0.42\text{ blk/tick}$).
- Fast Voxel Traversal (Amanatides-Woo DDA) for block raymarching up to 5.0 blocks.
- Block destruction timing with hardness stages and placement collision validation.

### R3. Anvil-Compatible Sub-Chunk World Generation
- Sparse $16 \times 16 \times 16$ sub-chunk section model (256 height total) with YZX index ordering for optimal cache locality.
- Empty air sections omitted from memory allocation and meshing.
- Multi-octave 2D/3D Simplex procedural terrain with Whittaker biome matrix (Plains, Desert, Mountains, Forest) and 3D cave carve-out.
- 3-axis Greedy Meshing algorithm reducing draw calls and vertex counts by >80% with per-vertex ambient occlusion.

### R4. Embedded Zero-Asset & Audio Pipeline
- Embedded $256 \times 256$ retro 16x16 pixel texture atlas compiled directly into binary `.rodata` (zero loose texture files, zero path resolution bugs).
- Real-time procedural 8-bit sound synthesizer generating canonical audio waveforms (block breaking, placement, footsteps, jump) directly to the platform audio buffer without external audio files.

## Acceptance Criteria

### Universal Execution
- [ ] Single executable file or standalone archive starts with a single click/command on standard desktop OS without pre-installed runtimes.
- [ ] Initial cold start to interactive world under 80ms.
- [ ] Fully portable save/load in `./saves/` directory relative to executable.

### Engine Performance & Mechanics
- [ ] Stable 60+ FPS rendering at minimum 8-chunk render distance on standard integrated GPUs.
- [ ] Exact player movement fidelity matching Minecraft Java physics constants ($g=0.08$, $\text{drag}=0.98$, $\text{friction}=0.546$).
- [ ] Functional block destruction and placement with exact raycasted voxel grid alignment.
- [ ] Working hotbar selection and block item state machine.

### Architecture & Specification Integrity
- [ ] Complete implementation faithful to the 6 specification documents in `/docs/`.
- [ ] Code adheres to Ponytail minimal-complexity principles (`// ponytail: [limitation/ceiling] -> [upgrade path]`).

## 2026-09-03T08:44:32Z

A standalone, universal single-click desktop Minecraft game clone distributable directly via GitHub, requiring zero external runtime installations or configuration for end users on Windows, Linux, and macOS. Built strictly following Ponytail minimal-complexity principles and official Minecraft canonical mechanics as specified in `g:/minecraft_desktop/docs/`.

Working directory: g:/minecraft_desktop
Integrity mode: development

RESUME DIRECTIVE:
Resume execution directly from the existing workspace state in `g:/minecraft_desktop/`.
- Milestone 1 remediation has been implemented in `src/platform/platform_desktop.c`, `src/main.c`, and `src/core/math_utils.h` (component-by-component recursive path creation, wide-char UTF-8 canary probing, CLI parsing hardening, and angle/dimension safeguards).
- Verify M1 closure and immediately dispatch Milestone 2: World Generation (multi-octave 2D Simplex terrain, Whittaker biomes, 3D cave carve-out, and 3-axis Lysenko Greedy Meshing).
- Proceed through Milestone 3 (Gameplay & Physics), Milestone 4 (Embedded Assets & Audio), and Milestone 5 (GitHub Actions Matrix Packaging).
- Strictly enforce Ponytail principles: zero host binary downloads, zero unnecessary abstractions, pure Python test-runner verification.

## Requirements

### R1. Universal One-Click Native Distribution
A completely portable, single-click executable pipeline requiring zero external dependencies (no separate Java runtime, no Python environment, no system DLL installations). When downloaded from a GitHub release into any folder, it runs immediately.
- Windows standalone `.exe` (statically linked C runtime, system DLLs only).
- Linux portable ELF binary (glibc 2.31 compatible).
- macOS Universal 2 binary (Apple Silicon + Intel x86_64).
- Portable relative base-path resolver storing `./saves/` adjacent to binary.

### R2. Official Canonical Physics & Voxel Interaction
Full mechanical parity with official Minecraft Java Edition kinematic constants (documented in `docs/02_CORE_GAMEPLAY_FEATURES.md` and `docs/06_OFFICIAL_MINECRAFT_CANONICAL_SPEC.md`):
- 20 TPS physics tick rate with sub-frame render interpolation.
- Player AABB collision ($0.6 \times 1.8 \times 0.6\text{m}$), eye level $1.62\text{m}$, auto-step $0.6\text{m}$.
- Exact downward acceleration ($g = 0.08\text{ blk/tick}^2$), air drag ($0.98$), ground friction ($0.546$), jump impulse ($0.42\text{ blk/tick}$).
- Fast Voxel Traversal (Amanatides-Woo DDA) for block raymarching up to 5.0 blocks.
- Block destruction timing with hardness stages and placement collision validation.

### R3. Anvil-Compatible Sub-Chunk World Generation
- Sparse $16 \times 16 \times 16$ sub-chunk section model (256 height total) with YZX index ordering for optimal cache locality.
- Empty air sections omitted from memory allocation and meshing.
- Multi-octave 2D/3D Simplex procedural terrain with Whittaker biome matrix (Plains, Desert, Mountains, Forest) and 3D cave carve-out.
- 3-axis Greedy Meshing algorithm reducing draw calls and vertex counts by >80% with per-vertex ambient occlusion.

### R4. Embedded Zero-Asset & Audio Pipeline
- Embedded $256 \times 256$ retro 16x16 pixel texture atlas compiled directly into binary `.rodata` (zero loose texture files, zero path resolution bugs).
- Real-time procedural 8-bit sound synthesizer generating canonical audio waveforms (block breaking, placement, footsteps, jump) directly to the platform audio buffer without external audio files.

## Acceptance Criteria

### Universal Execution
- [ ] Single executable file or standalone archive starts with a single click/command on standard desktop OS without pre-installed runtimes.
- [ ] Initial cold start to interactive world under 80ms.
- [ ] Fully portable save/load in `./saves/` directory relative to executable.

### Engine Performance & Mechanics
- [ ] Stable 60+ FPS rendering at minimum 8-chunk render distance on standard integrated GPUs.
- [ ] Exact player movement fidelity matching Minecraft Java physics constants ($g=0.08$, $\text{drag}=0.98$, $\text{friction}=0.546$).
- [ ] Functional block destruction and placement with exact raycasted voxel grid alignment.
- [ ] Working hotbar selection and block item state machine.

### Architecture & Specification Integrity
- [ ] Complete implementation faithful to the 6 specification documents in `/docs/`.
- [ ] Code adheres to Ponytail minimal-complexity principles (`// ponytail: [limitation/ceiling] -> [upgrade path]`).

## 2026-09-03T09:30:59Z

A standalone, universal single-click desktop Minecraft game clone distributable directly via GitHub, requiring zero external runtime installations or configuration for end users on Windows, Linux, and macOS. Built strictly following Ponytail minimal-complexity principles and official Minecraft canonical mechanics as specified in `g:/minecraft_desktop/docs/`.

Working directory: g:/minecraft_desktop
Integrity mode: development

RESUME DIRECTIVE:
Resume execution directly from the existing workspace state in `g:/minecraft_desktop/`.
1. Milestone 1 (Runtime & Engine Core) is complete in `src/core/` and `src/platform/`.
2. Milestone 2 (World Generation, Chunks & Greedy Meshing) is complete in `src/world/` (`world.h`, `chunk.c`, `terrain.h/c`, `mesher.h/c`), with all 125/125 tests passing (`tests/test_runner.py`, `tests/test_m2_chunk_invariants.py`, `tests/test_mesher_canonical.py`).
3. Immediately dispatch Milestone 3: Core Gameplay & Physics:
   - Amanatides-Woo Fast Voxel Traversal (DDA) raymarching (5.0m reach) in `src/gameplay/`
   - Custom swept AABB player physics with canonical Java constants (g=0.08, drag=0.98, friction=0.546, auto-step 0.6m) in `src/gameplay/`
   - Block destruction FSM and placement validation in `src/gameplay/`
   - 9-slot hotbar item stack state machine in `src/gameplay/`
4. Proceed to Milestone 4: Embedded Assets & Audio:
   - Embedded 256x256 texture atlas in `.rodata` (zero loose files) in `src/assets/`
   - Real-time procedural 8-bit sound synthesizer in `src/audio/`
5. Proceed to Milestone 5: GitHub Actions CI/CD matrix (.github/workflows/build_and_release.yml) and single-click zero-install packaging.
6. Strictly enforce Ponytail principles: zero host binary downloads, zero unnecessary abstractions, pure Python test-runner verification.
7. Perform full test suite validation and report completion to the Sentinel for independent victory auditing.

## Requirements

### R1. Universal One-Click Native Distribution
A completely portable, single-click executable pipeline requiring zero external dependencies (no separate Java runtime, no Python environment, no system DLL installations). When downloaded from a GitHub release into any folder, it runs immediately.
- Windows standalone `.exe` (statically linked C runtime, system DLLs only).
- Linux portable ELF binary (glibc 2.31 compatible).
- macOS Universal 2 binary (Apple Silicon + Intel x86_64).
- Portable relative base-path resolver storing `./saves/` adjacent to binary.

### R2. Official Canonical Physics & Voxel Interaction
Full mechanical parity with official Minecraft Java Edition kinematic constants (documented in `docs/02_CORE_GAMEPLAY_FEATURES.md` and `docs/06_OFFICIAL_MINECRAFT_CANONICAL_SPEC.md`):
- 20 TPS physics tick rate with sub-frame render interpolation.
- Player AABB collision ($0.6 \times 1.8 \times 0.6\text{m}$), eye level $1.62\text{m}$, auto-step $0.6\text{m}$.
- Exact downward acceleration ($g = 0.08\text{ blk/tick}^2$), air drag ($0.98$), ground friction ($0.546$), jump impulse ($0.42\text{ blk/tick}$).
- Fast Voxel Traversal (Amanatides-Woo DDA) for block raymarching up to 5.0 blocks.
- Block destruction timing with hardness stages and placement collision validation.

### R3. Anvil-Compatible Sub-Chunk World Generation
- Sparse $16 \times 16 \times 16$ sub-chunk section model (256 height total) with YZX index ordering for optimal cache locality.
- Empty air sections omitted from memory allocation and meshing.
- Multi-octave 2D/3D Simplex procedural terrain with Whittaker biome matrix (Plains, Desert, Mountains, Forest) and 3D cave carve-out.
- 3-axis Greedy Meshing algorithm reducing draw calls and vertex counts by >80% with per-vertex ambient occlusion.

### R4. Embedded Zero-Asset & Audio Pipeline
- Embedded $256 \times 256$ retro 16x16 pixel texture atlas compiled directly into binary `.rodata` (zero loose texture files, zero path resolution bugs).
- Real-time procedural 8-bit sound synthesizer generating canonical audio waveforms (block breaking, placement, footsteps, jump) directly to the platform audio buffer without external audio files.

## Acceptance Criteria

### Universal Execution
- [ ] Single executable file or standalone archive starts with a single click/command on standard desktop OS without pre-installed runtimes.
- [ ] Initial cold start to interactive world under 80ms.
- [ ] Fully portable save/load in `./saves/` directory relative to executable.

### Engine Performance & Mechanics
- [ ] Stable 60+ FPS rendering at minimum 8-chunk render distance on standard integrated GPUs.
- [ ] Exact player movement fidelity matching Minecraft Java physics constants ($g=0.08$, $\text{drag}=0.98$, $\text{friction}=0.546$).
- [ ] Functional block destruction and placement with exact raycasted voxel grid alignment.
- [ ] Working hotbar selection and block item state machine.

### Architecture & Specification Integrity
- [ ] Complete implementation faithful to the 6 specification documents in `/docs/`.
- [ ] Code adheres to Ponytail minimal-complexity principles (`// ponytail: [limitation/ceiling] -> [upgrade path]`).

## 2026-09-03T10:49:28Z

A standalone, universal single-click desktop Minecraft game clone distributable directly via GitHub, requiring zero external runtime installations or configuration for end users on Windows, Linux, and macOS. Built strictly following Ponytail minimal-complexity principles and official Minecraft canonical mechanics as specified in `g:/minecraft_desktop/docs/`.

Working directory: g:/minecraft_desktop
Integrity mode: development

RESUME DIRECTIVE (POST-RESTART):
Resume execution directly from the existing workspace state in `g:/minecraft_desktop/`.
1. Milestone 1 (Runtime & Engine Core) is complete in `src/core/` and `src/platform/`.
2. Milestone 2 (World Generation, Chunks & Greedy Meshing) is complete in `src/world/` (`chunk.c`, `terrain.c`, `mesher.c`, `world.h`), with 100% passing tests.
3. Milestone 3 (Gameplay & Physics) is complete in `src/gameplay/` (`physics.c/h`, `raycast.c/h`, `interaction.c/h`, `inventory.c/h`), with all 21 verification tests passing.
4. Immediately dispatch Milestone 4 (Embedded Assets & Audio):
   - In-memory embedded 256x256 texture atlas in `.rodata` and 6-face block visual table in `src/assets/`
   - Real-time procedural 8-bit sound synthesizer in `src/audio/`
5. Immediately dispatch Milestone 5 (Packaging & Distribution):
   - GitHub Actions CI/CD matrix `.github/workflows/build_and_release.yml` (Windows .exe, Linux ELF, macOS universal binary)
   - Zero-installer single-click release bundle packaging
6. Strictly enforce Ponytail principles: zero host binary downloads, zero unnecessary abstractions, pure Python test-runner verification (`python tests/test_runner.py`).
7. Perform full test suite validation and report completion to the Sentinel for independent victory auditing.

## Requirements

### R1. Universal One-Click Native Distribution
A completely portable, single-click executable pipeline requiring zero external dependencies (no separate Java runtime, no Python environment, no system DLL installations). When downloaded from a GitHub release into any folder, it runs immediately.
- Windows standalone `.exe` (statically linked C runtime, system DLLs only).
- Linux portable ELF binary (glibc 2.31 compatible).
- macOS Universal 2 binary (Apple Silicon + Intel x86_64).
- Portable relative base-path resolver storing `./saves/` adjacent to binary.

### R2. Official Canonical Physics & Voxel Interaction
Full mechanical parity with official Minecraft Java Edition kinematic constants (documented in `docs/02_CORE_GAMEPLAY_FEATURES.md` and `docs/06_OFFICIAL_MINECRAFT_CANONICAL_SPEC.md`):
- 20 TPS physics tick rate with sub-frame render interpolation.
- Player AABB collision ($0.6 \times 1.8 \times 0.6\text{m}$), eye level $1.62\text{m}$, auto-step $0.6\text{m}$.
- Exact downward acceleration ($g = 0.08\text{ blk/tick}^2$), air drag ($0.98$), ground friction ($0.546$), jump impulse ($0.42\text{ blk/tick}$).
- Fast Voxel Traversal (Amanatides-Woo DDA) for block raymarching up to 5.0 blocks.
- Block destruction timing with hardness stages and placement collision validation.

### R3. Anvil-Compatible Sub-Chunk World Generation
- Sparse $16 \times 16 \times 16$ sub-chunk section model (256 height total) with YZX index ordering for optimal cache locality.
- Empty air sections omitted from memory allocation and meshing.
- Multi-octave 2D/3D Simplex procedural terrain with Whittaker biome matrix (Plains, Desert, Mountains, Forest) and 3D cave carve-out.
- 3-axis Greedy Meshing algorithm reducing draw calls and vertex counts by >80% with per-vertex ambient occlusion.

### R4. Embedded Zero-Asset & Audio Pipeline
- Embedded $256 \times 256$ retro 16x16 pixel texture atlas compiled directly into binary `.rodata` (zero loose texture files, zero path resolution bugs).
- Real-time procedural 8-bit sound synthesizer generating canonical audio waveforms (block breaking, placement, footsteps, jump) directly to the platform audio buffer without external audio files.

## Acceptance Criteria

### Universal Execution
- [ ] Single executable file or standalone archive starts with a single click/command on standard desktop OS without pre-installed runtimes.
- [ ] Initial cold start to interactive world under 80ms.
- [ ] Fully portable save/load in `./saves/` directory relative to executable.

### Engine Performance & Mechanics
- [ ] Stable 60+ FPS rendering at minimum 8-chunk render distance on standard integrated GPUs.
- [ ] Exact player movement fidelity matching Minecraft Java physics constants ($g=0.08$, $\text{drag}=0.98$, $\text{friction}=0.546$).
- [ ] Functional block destruction and placement with exact raycasted voxel grid alignment.
- [ ] Working hotbar selection and block item state machine.

### Architecture & Specification Integrity
- [ ] Complete implementation faithful to the 6 specification documents in `/docs/`.
- [ ] Code adheres to Ponytail minimal-complexity principles (`// ponytail: [limitation/ceiling] -> [upgrade path]`).
