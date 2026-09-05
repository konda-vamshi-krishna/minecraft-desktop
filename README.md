# Minecraft Desktop (Universal 1-Click Edition)

[![GitHub Release](https://img.shields.io/github/v/release/konda-vamshi-krishna/minecraft-desktop?style=for-the-badge&color=2ea44f)](https://github.com/konda-vamshi-krishna/minecraft-desktop/releases/latest)
[![Windows](https://img.shields.io/badge/Windows-Download%20x64%20(Zip)-0078D6?style=for-the-badge&logo=windows&logoColor=white)](https://github.com/konda-vamshi-krishna/minecraft-desktop/releases/latest/download/minecraft-desktop-windows-x64.zip)
[![Linux](https://img.shields.io/badge/Linux-Download%20x64%20(Tar.gz)-FCC624?style=for-the-badge&logo=linux&logoColor=black)](https://github.com/konda-vamshi-krishna/minecraft-desktop/releases/latest/download/minecraft-desktop-linux-x64.tar.gz)
[![macOS](https://img.shields.io/badge/macOS-Download%20Universal%20(Zip)-000000?style=for-the-badge&logo=apple&logoColor=white)](https://github.com/konda-vamshi-krishna/minecraft-desktop/releases/latest/download/minecraft-desktop-macos-universal.zip)

A standalone, universal single-click desktop Minecraft game clone requiring **zero external runtime installations or configuration** for end users on Windows, Linux, and macOS.

Built strictly in accordance with **ISO C99**, **Minecraft Java Edition canonical physics constants**, and **Ponytail minimal-complexity principles** (zero unnecessary abstractions, zero heap allocation in critical paths).

---

> [!WARNING]
> ### ⚠️ DO NOT CLICK THE GREEN "CODE -> DOWNLOAD ZIP" BUTTON TO PLAY!
> Clicking GitHub's green **`<> Code`** button and selecting **"Download ZIP"** downloads the **raw C source code repository**, not the playable game executable!
> 
> **To download and play the game immediately, click the direct download links in the table below:**

## 📥 Direct 1-Click Downloads (Playable Binaries)

| Operating System | Architecture | Package | Direct Download Link |
|---|---|---|---|
| **Windows 10 / 11** | 64-bit (x86_64) | Standalone `.zip` | 👉 [**Download Windows Version (.zip)**](https://github.com/konda-vamshi-krishna/minecraft-desktop/releases/latest/download/minecraft-desktop-windows-x64.zip) |
| **Linux** (Ubuntu, Fedora, Arch, etc.) | 64-bit (glibc 2.31+) | Portable `.tar.gz` | 👉 [**Download Linux Version (.tar.gz)**](https://github.com/konda-vamshi-krishna/minecraft-desktop/releases/latest/download/minecraft-desktop-linux-x64.tar.gz) |
| **macOS** (Apple Silicon M1/M2/M3 + Intel) | Universal 2 Fat Binary | Portable `.zip` | 👉 [**Download macOS Version (.zip)**](https://github.com/konda-vamshi-krishna/minecraft-desktop/releases/latest/download/minecraft-desktop-macos-universal.zip) |
| **Checksums** | SHA-256 Hashes | Text file | 👉 [**Download SHA256SUMS.txt**](https://github.com/konda-vamshi-krishna/minecraft-desktop/releases/latest/download/SHA256SUMS.txt) |

---

## 🎮 How to Play on Windows 11 (3 Simple Steps)

1. **Download**: Click the [**Download Windows Version**](https://github.com/konda-vamshi-krishna/minecraft-desktop/releases/latest/download/minecraft-desktop-windows-x64.zip) button above.
2. **Extract**: Right-click the downloaded `minecraft-desktop-windows-x64.zip` file -> select **Extract All...** -> choose a folder (e.g., Desktop).
3. **Play**: Open the folder and double-click **`minecraft.exe`**!

> [!NOTE]
> **Windows 11 SmartScreen Notice**: Because this is an open-source binary built from GitHub Actions, Windows SmartScreen may show a popup saying *"Windows protected your PC"*. Simply click **"More info"** and then **"Run anyway"**.

### ⌨️ Default Controls
* **W, A, S, D**: Walk / Strafe
* **Space**: Jump (plays procedural jump sound)
* **Left Shift**: Sneak (clamps player to block edges so you cannot fall off cliffs)
* **Left Ctrl**: Sprint (widens camera FOV)
* **Mouse**: Free-look camera
* **Left Click**: Mine / Break block (10-stage crack animation + drop items)
* **Right Click**: Place block (with anti-suffocation player protection)
* **1–9 / Scroll Wheel**: Hotbar item selection
* **Esc**: Release mouse cursor / Pause

---

## 💻 1-Line Terminal Launchers

If you prefer using your terminal, copy and paste one of these single-line commands:

### Windows (PowerShell)
```powershell
curl.exe -L -o minecraft-win.zip "https://github.com/konda-vamshi-krishna/minecraft-desktop/releases/latest/download/minecraft-desktop-windows-x64.zip"; Expand-Archive minecraft-win.zip -DestinationPath game; cd game/minecraft-desktop; .\minecraft.exe
```

### Linux (Bash)
```bash
curl -sSL -o minecraft-linux.tar.gz "https://github.com/konda-vamshi-krishna/minecraft-desktop/releases/latest/download/minecraft-desktop-linux-x64.tar.gz" && tar -xzf minecraft-linux.tar.gz && cd minecraft-desktop && ./minecraft
```

### macOS (Zsh / Terminal)
```bash
curl -sSL -o minecraft-mac.zip "https://github.com/konda-vamshi-krishna/minecraft-desktop/releases/latest/download/minecraft-desktop-macos-universal.zip" && unzip minecraft-mac.zip && cd minecraft-desktop && ./minecraft
```

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

## 🛠️ For Developers (Source Code)

If you are a developer and want to inspect, modify, or build the C source code:

```bash
# Clone the repository
git clone https://github.com/konda-vamshi-krishna/minecraft-desktop.git
cd minecraft-desktop

# Run the 105-test opaque-box E2E test suite
python tests/test_runner.py

# Run the full 279-test repository discovery suite
python -m unittest discover -s tests -p "test_*.py"
```
