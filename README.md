# Minecraft Desktop (Universal 1-Click Edition)

A standalone, universal single-click desktop Minecraft game clone distributable directly via GitHub Releases, requiring **zero external runtime installations or configuration** for end users on Windows, Linux, and macOS.

Built strictly in accordance with **ISO C99**, **Minecraft Java Edition canonical physics constants**, and **Ponytail minimal-complexity principles** (zero unnecessary abstractions, zero heap allocation in critical paths).

---

## 🌟 Key Features & Architectural Highlights

### 1. Zero-Dependency Native Portability (R1)
* **Single-Click Execution**: No Java Runtime (JRE), Python interpreter, or external dynamic libraries required.
* **Portable Saves**: Relative path resolver stores world saves and configuration directly in `./saves/` adjacent to the executable.
* **Multi-Platform CI/CD Matrix**:
  * **Windows**: Standalone `.exe` statically linked against standard C runtime (`-static-libgcc -static -s`) and Win32 system DLLs (`opengl32`, `gdi32`, `winmm`, `user32`, `shell32`).
  * **Linux**: Portable ELF binary built against `glibc 2.31` baseline with standard Mesa/X11 linkage.
  * **macOS**: Universal 2 fat binary supporting both Apple Silicon (`arm64`) and Intel (`x86_64`) via `lipo`.

### 2. Canonical Voxel Physics & Raymarching (R2)
* **Fixed 20 TPS Kinematics**: Deterministic 20 TPS physics tick accumulator with alpha sub-frame render interpolation.
* **Player AABB Kinematics**: Canonical Java constants ($0.6 \times 1.8 \times 0.6\text{m}$ standing bounding box, eye level $1.62\text{m}$, sneak height $1.5\text{m}$, auto-step $0.6\text{m}$, gravity $g = 0.08\text{ blk/tick}^2$, drag $0.98$, ground friction $0.546$, jump impulse $0.42\text{ blk/tick}$).
* **Sneak Edge Clamping**: Automatic ledge clamping preventing falls while sneaking.
* **Fast Voxel Traversal**: Amanatides-Woo DDA raymarching calculating exact voxel entry normals and contact faces up to $5.0\text{m}$ reach.
* **10-Stage Crack FSM**: Progressive block destruction state machine with hardness multipliers and drop spawning.

### 3. Sub-Chunk World Generation & Greedy Meshing (R3)
* **Sparse Section Grid**: $16 \times 16 \times 16$ sub-chunk section model (256 height total) with optimal YZX memory layout in 64KB slabs. Empty air sections consume zero memory.
* **Simplex Procedural Terrain**: Multi-octave 2D/3D Simplex noise with Whittaker biome matrix (Plains, Desert, Mountains, Forest) and 3D cave carve-out.
* **3-Axis Greedy Meshing**: Quad-merging algorithm reducing vertex counts and draw calls by $>80\%$ with per-vertex ambient occlusion.

### 4. Embedded Zero-Asset & Audio Pipeline (R4)
* **Embedded `.rodata` Texture Atlas**: Full $256 \times 256$ RGBA32 texture atlas embedded directly in executable read-only memory (`src/assets/atlas_data.h`). Zero external texture files, zero missing texture paths.
* **Procedural 8-Bit Audio Synthesizer**: 16-voice polyphonic real-time software mixer (`src/audio/synthesizer.c`) synthesizing procedural waveforms for jump, footstep, block break, and block place directly into platform audio buffers.

---

## 📁 Repository Structure

```
g:/minecraft_desktop/
├── .github/
│   └── workflows/
│       └── build_and_release.yml   # 3-platform GitHub Actions build & release matrix
├── docs/                           # 6 canonical architecture & gameplay specification docs
├── res/                            # Windows manifest, resource script, and icon
│   ├── app.manifest
│   ├── icon.ico
│   └── resource.rc
├── scripts/
│   └── package_release.py          # Standalone zero-installer release packager
├── src/
│   ├── assets/                     # Embedded 256x256 RGBA atlas (.rodata)
│   ├── audio/                      # 16-voice real-time procedural synthesizer
│   ├── core/                       # 60Hz loop accumulator, runtime hooks, math utilities
│   ├── gameplay/                   # Swept AABB physics, DDA raycast, interaction, inventory
│   ├── platform/                   # Win32, Linux, macOS platform abstractions
│   ├── world/                      # Simplex terrain, chunk storage, 3-axis greedy mesher
│   └── main.c                      # Integrated engine entry point
├── tests/
│   ├── canonical_models.py         # Ground-truth Python specification oracle
│   ├── test_runner.py              # Master opaque-box 4-tier E2E test runner (105 tests)
│   ├── test_m3_gameplay.py         # 30-test M3 gameplay & physics invariant suite
│   └── ...                         # Subsystem invariant & boundary tests (279 tests)
├── CMakeLists.txt                  # Universal CMake build specification
└── Makefile                        # Native GNU Makefile compiling all 12 translation units
```

---

## 🧪 Testing & Verification

The project is backed by a 100% passing automated test suite with zero external third-party dependencies (pure Python standard library):

```powershell
# 1. Run Master Opaque-Box E2E Runner (105 tests)
python tests/test_runner.py

# 2. Run Full Repository Discovery Suite (279 tests)
python -m unittest discover -s tests -p "test_*.py"

# 3. Run Milestone 3 Gameplay & Physics Suite (30 tests)
python -m unittest tests/test_m3_gameplay.py

# 4. Dry-Run Zero-Installer Packaging Utility
python scripts/package_release.py --allow-missing-exe --archive zip
```

---

## 🚀 Building & Releasing

### Native Cross-Compilation (GitHub Actions)
All native cross-compilation is automated via [`.github/workflows/build_and_release.yml`](.github/workflows/build_and_release.yml).

To release a new version:
1. Commit all files:
   ```bash
   git add .
   git commit -m "feat: Minecraft Desktop Universal 1-Click Edition v1.0.0"
   ```
2. Tag the release:
   ```bash
   git tag v1.0.0
   ```
3. Push to your GitHub repository:
   ```bash
   git push origin main --tags
   ```
GitHub Actions will automatically build Windows `.exe`, Linux ELF, and macOS Universal 2 binaries, package them into standalone `.zip` and `.tar.gz` archives with SHA256 checksums, and publish them to GitHub Releases.
