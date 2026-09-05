# Comprehensive Specification Report: World Representation, Generation, Meshing, Lighting, Asset Pipeline, Audio, and HUD/Menus

**Agent:** `spec_miner_world_assets`  
**Date:** 2026-09-03  
**Integrity Mode:** Development  
**Target Platform:** Cross-Platform Desktop (Windows PE, Linux ELF, macOS Universal 2)  
**Architectural Philosophy:** Ponytail Minimal-Complexity Principles (Zero Boilerplate, Mechanical Sympathy, YAGNI) & Official Minecraft Canonical Mechanics  

---

## Executive Overview

This report provides the exhaustive, authoritative technical specification for the world representation, procedural world generation, voxel meshing, lighting/shading, embedded asset pipeline, procedural audio synthesis, and HUD/menus for the single-click desktop Minecraft engine.

All findings are extracted directly from:
- `ORIGINAL_REQUEST.md`
- `docs/03_WORLD_GENERATION_AND_CHUNKS.md`
- `docs/04_ASSET_PIPELINE_AND_AUDIO.md`
- `docs/01_ARCHITECTURE_AND_RUNTIME.md`
- `docs/02_CORE_GAMEPLAY_FEATURES.md`
- `docs/06_OFFICIAL_MINECRAFT_CANONICAL_SPEC.md`

---

## Features Discovered

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|---|---|---|---|---|---|---|
| 1 | World Representation | Chunk Spatial Dimensions | Vertically continuous column of 16x256x16 blocks (65,536 voxels total per chunk). | Chunk coordinates $(CX, CZ)$ | Fixed 64 KiB contiguous memory block | $Y < 0$ or $Y \ge 256$ clamped/returns AIR | `docs/03` §2.1, `docs/01` §5.1 |
| 2 | World Representation | 1-Byte BlockID Scalar | Compact `uint8_t` representing block type; no OOP wrappers or heap pointers. | Voxel coordinate $(x,y,z)$ | `uint8_t` block ID (0-255) | Unmapped IDs fallback to missing texture slot (15,15) | `docs/03` §2.2, `docs/06` §4.2 |
| 3 | World Representation | Y-Internal Memory Layout | Contiguous 1D array flattened with $Y$ as stride-1 axis: $\text{Index} = y + 256x + 4096z$ for sequential vertical column cache locality. | Local coordinates $(x,y,z) \in [0..15] \times [0..255] \times [0..15]$ | 1D array index $[0..65535]$ | Out-of-bounds asserts in debug, clamped in release | `docs/03` §2.3, `docs/01` §5.1 |
| 4 | World Representation | Floored Coordinate Transforms | Bitshift coordinate mapping from world $(X,Y,Z)$ to chunk $(CX, CZ)$ and local $(lx, ly, lz)$ handling negative integers safely. | Signed integers $(X, Y, Z)$ | $(CX, CZ) = (X \gg 4, Z \gg 4)$, $(lx, ly, lz) = (X \& 15, Y, Z \& 15)$ | Negative flooring arithmetic prevents -1..-15 rounding towards 0 | `docs/03` §2.4 |
| 5 | World Representation | Sparse 16x16x16 Sub-Chunk Sections | Partition chunk into 16 vertical sections ($16^3$ voxels each); omit unallocated air sections from memory and meshing. | Sub-chunk $Y$-section index (0..15) | Section voxel buffer or NULL pointer | Accessing NULL section returns `BLOCK_AIR` (0) | `ORIGINAL_REQUEST.md` R3, `docs/06` §2.1 |
| 6 | World Representation | Active Toroidal World Grid | $17 \times 17$ chunk grid ($R=8$ render distance, 289 active chunks) centered on camera chunk; total voxel footprint ~18.06 MiB. | Player chunk coordinates $(CX_0, CZ_0)$ | Active array of 289 `Chunk` structures | Chunks outside radius $R+2$ unloaded and recycled | `docs/03` §5.1, `docs/01` §5.2 |
| 7 | World Generation | 64-bit Seed Determinism | Deterministic procedural pipeline converting seed + chunk coordinates into identical terrain every run. | 64-bit unsigned integer `seed`, $(CX, CZ)$ | Fully populated 64 KiB voxel buffer | Seed 0 handled identically to any other 64-bit integer | `docs/03` §3, `ORIGINAL_REQUEST.md` R3 |
| 8 | World Generation | Fast Coordinate PRNG Hash | SplitMix64 non-cryptographic hash for uniform pseudo-randomness across chunk coordinates. | Integers $x, z$, 64-bit seed | 64-bit uniform unsigned integer | Pure bitwise operations; never overflows or faults | `docs/03` §3.4 |
| 9 | World Generation | 2D Multi-Octave fBM Terrain | Continental heightmap $H(x,z) = 64 + \sum A \gamma^i \text{Simplex2D}(f \lambda^i x, f \lambda^i z)$ ($N=4..6, f=0.005, A=32.0$). | World coords $(x, z)$, seed | Surface base height $H \in [0, 255]$ | Height clamped to $[1, 255]$ | `docs/03` §3.1 |
| 10 | World Generation | Whittaker Biome Dual-Field | Temperature $T(x,z) \in [0,1]$ and Moisture $M(x,z) \in [0,1]$ via low-frequency fBM ($f=0.0015, N=2$). | World coords $(x, z)$, seed | Biome classification (Plains, Desert, Mountains, Forest) | Normalized strictly to $[0.0, 1.0]$ | `docs/03` §3.2 |
| 11 | World Generation | Biome Stratigraphy & Dressing | Surface, sub-surface, and core blocks populated according to biome rules (Plains=Grass/Dirt/Stone, Desert=Sand/Sandstone/Stone, etc.). | Biome enum, column height $H$, local voxel $y$ | Block IDs written into chunk column | Bedrock layer $y=0..4$ overrides all stratigraphy | `docs/03` §3.2 |
| 12 | World Generation | Bedrock Base Generation | Solid `BLOCK_BEDROCK` at $y=0$, randomized bedrock noise at $y=1..4$ to prevent falling out of world. | Voxel $y \in [0, 4]$, coordinate hash | `BLOCK_BEDROCK` or `BLOCK_STONE` | Always solid at $y=0$ | `docs/03` §3.3 |
| 13 | World Generation | Sea Level Water Filling | Basins and depressions below $y=62$ filled with `BLOCK_WATER` unless overridden by desert dry rules. | Voxel $y \le 62$, density $\rho \le 0$ | `BLOCK_WATER` (ID 10) | Water block treated as transparent in mesher | `docs/03` §3.2, §3.3 |
| 14 | World Generation | 3D Overhangs & Arches | 3D Simplex density field $\rho(x,y,z) = H_{2D}(x,z) - y + 3D\text{Simplex}(x f_3, y f_3, z f_3) \cdot A_3$ for cliffs and bridges. | World 3D coords $(x, y, z)$, seed | Solid if $\rho > 0$, Air if $\rho \le 0$ | Extreme density values clamped to valid chunk bounds | `docs/03` §3.3 |
| 15 | World Generation | 3D Cave Worm Carving | Dual 3D noise fields $N_1, N_2$; air tunnel carved where $|N_1| < \tau \land |N_2| < \tau$ for $y \in [5, 128]$ ($\tau \approx 0.05$). | World 3D coords $(x, y, z)$, seed | Air carved if cave threshold met | Cave carving disabled at $y < 5$ (bedrock barrier) and $y > 128$ | `docs/03` §3.3 |
| 16 | World Generation | Tree Decoration Stamping | Cellular canopy generator stamping Oak/Pine trunk ($H \in [4,6]$) and spherical/box leaf canopy. | Surface $(x, H, z)$, local PRNG | Wood trunk blocks + leaf cluster blocks | Stamping restricted to local $x,z \in [2, 13]$ to prevent chunk boundary deadlock | `docs/03` §3.4 |
| 17 | World Generation | Flora & Surface Foliage | Deterministic placement of Cacti, Dandelions, Poppies, and Tall Grass on valid surface blocks. | Surface block type, moisture, PRNG | Foliage block placed above surface | Aborted if block below is not valid soil/sand | `docs/03` §3.2, §3.4 |
| 18 | Voxel Meshing | Hidden Face Culling | Strict boundary test: $\text{EmitFace}(A, B) \iff \text{IsOpaque}(A) \land \neg \text{IsOpaque}(B)$. Never emit faces between solid blocks. | Current block $A$, neighbor block $B$ | Face generation boolean (True/False) | Chunk boundary sampling queries neighbor chunks safely | `docs/03` §4.1 |
| 19 | Voxel Meshing | 3-Axis Greedy Meshing | Mikola Lysenko algorithm merging contiguous coplanar identical faces on 2D slice masks into maximal $W \times H$ quads. | Chunk voxel buffer, 4 direct neighbor chunks | Merged quad geometry (slashes vertex count 80-90%) | Slices across boundaries fallback to AIR if neighbor chunk unready | `docs/03` §4.2 |
| 20 | Voxel Meshing | 64-bit Packed Vertex Format | Highly compressed vertex layout: `data0` (X:5, Y:9, Z:5, Normal:3, AO:2, BlockID:8) + `data1` (U:8, V:8, W:8, H:8). | Spatial and texture quad attributes | 8 bytes per vertex (2 uint32_t words) | Vertex coordinate overflow prevented by bitmasks | `docs/03` §4.2 |
| 21 | Voxel Meshing | 32-bit Packed Vertex Layout | Lightweight 4-byte vertex format for non-greedy quads: $X(5), Y(9), Z(5)$, Normal(3), TexID(8), AO(2). | Non-merged quad attributes | 4 bytes per vertex (1 uint32_t word) | 88.9% bandwidth reduction over 36-byte float vertices | `docs/01` §5.3 |
| 22 | Voxel Meshing | Multi-Pass Rendering | Separation into Opaque Solid Pass, Cutout Pass (leaves: discard if $\alpha < 0.5$), and Translucent Blend Pass (water $\alpha=0.6$, glass $\alpha < 1.0$). | Block visual definitions | Distinct draw calls or sorted geometry | Alpha blending enabled only on translucent pass to prevent depth sorting bugs | `docs/04` §5.1, `docs/01` §4.2 |
| 23 | Lighting & Shading | Per-Vertex Ambient Occlusion | Discrete AO calculation from 3 neighboring voxels ($S_1, S_2, C$) yielding integer values 0 (darkest) to 3 (brightest). | 3 neighbor block opacities per vertex | Vertex AO factor $0, 1, 2, 3$ | Corner fully blocked if $S_1 \land S_2$ opaque | `docs/03` §4.3 |
| 24 | Lighting & Shading | Quad Anisotropy Flip Guard | Diagonal tessellation flip: if $(AO_0 + AO_2 > AO_1 + AO_3)$, flip quad indices to $\{0,1,2,0,2,3\}$, preventing lighting creases. | 4 corner AO values of quad | Triangulation index order | Equal diagonal AO sums retain default triangulation | `docs/03` §4.3 |
| 25 | Lighting & Shading | Directional Face Shading | Static normal tinting factors: Top (+Y)=1.00, Bottom (-Y)=0.50, North/South (+/-Z)=0.80, East/West (+/-X)=0.60. | Face normal vector / face index | Scalar shading factor $K_{\text{face}} \in [0.5, 1.0]$ | Non-axis-aligned normals fallback to 1.0 | `docs/02` §7.2, `docs/06` §5 |
| 26 | Lighting & Shading | Celestial Day/Night Cycle | 1200s (20 min) diurnal cycle with $10^\circ$ axial tilt; evaluates sun direction, day factor, and ambient sky color. | World clock time $t \in [0, 1200)$ | Sun vector $\hat{\mathbf{L}}_{\text{sun}}$, sky color, ambient color | Day factor smoothstepped across horizon $[-0.2, +0.2]$ | `docs/02` §7.1, §7.2 |
| 27 | Lighting & Shading | Canonical Nibble Lighting | 4-bit dual-channel lighting (Sky light 0-15, Block light 0-15) with attenuation $I = 0.8^{15-L}$. | Local block emissions, sky propagation | Brightness levels per voxel | Handled via Ponytail simplification upgrade path | `docs/06` §5, `docs/02` §8 |
| 28 | Asset Pipeline | Zero-Asset Monolith Architecture | Compile-time embedding of textures and audio into executable binary (`.rodata`); zero filesystem hits at runtime. | Embedded binary byte arrays | Immediate GPU texture upload & software mixer | Eliminates missing asset crashes, relative path bugs, and disk I/O | `docs/04` §1, §2 |
| 29 | Asset Pipeline | Master 256x256 Texture Atlas | Uniform grid of 16x16 tiles (256 slots total), 32-bit RGBA (256 KiB raw). | Embedded PNG or raw RGBA byte slice | Single OpenGL texture handle (`GL_TEXTURE_2D`) | Nearest filtering prevents blur; missing slot defaults to magenta (15,15) | `docs/04` §3.1, §4.2 |
| 30 | Asset Pipeline | Texture Bleed Elimination | Mathematical texel bleed prevention via half-margin inset $\epsilon$ or hardware 2D Texture Array (`sampler2DArray`). | Tile index $(T_x, T_y)$, atlas dimensions | Normalized UV coordinates $(u_0, v_0, u_1, v_1)$ | Zero margin for nearest-neighbor; sub-texel inset for linear filtering | `docs/04` §3.2, `docs/03` §6.1 |
| 31 | Asset Pipeline | Greedy Texture UV Tiling | Fragment shader `fract(vUV)` wrapping across greedy quads with dimensions $(W, H)$. | Normalized / scaled quad UVs | Properly tiled 16x16 pixel textures without stretching | Discards fragments with $\alpha < 0.5$ for cutouts | `docs/03` §6.1 |
| 32 | Asset Pipeline | Canonical Block Texture Registry | Immutable lookup table mapping BlockID and FaceDirection (West, East, North, South, Top, Bottom) to tile coordinates. | BlockID, FaceDirection enum (0..5) | Tile coordinate $(T_x, T_y)$ | Unregistered block IDs return slot (15, 15) | `docs/04` §5.1, §5.2, `docs/06` §4.2 |
| 33 | Asset Pipeline | Embedded Retro ASCII Bitmap Font | Rows 12-15 of master atlas reserved for ASCII characters 0-127 ($16 \times 16$ cells) for zero-dependency UI text. | Character ASCII code (0..127) | Glyph UV bounding box | Characters $> 127$ fallback to '?' or space | `docs/04` §3.3 |
| 34 | Audio Engine | Procedural Audio Synthesizer | Real-time mathematical synthesis producing canonical waveforms directly in memory; zero `.wav` or `.ogg` files. | SoundID, volume, duration | PCM float samples [-1.0, 1.0] streamed to audio callback | CPU load < 0.1% for 16 voices | `docs/04` §6, `ORIGINAL_REQUEST.md` R4 |
| 35 | Audio Engine | Galois LFSR Noise Generator | 16-bit pseudo-random noise generator using bitwise taps: $(x^0 \oplus x^2 \oplus x^3 \oplus x^5)$ without stdlib rand mutex contention. | Internal 16-bit state | Float noise sample $\in [-1.0, +1.0]$ | Seed never 0 (initialized to non-zero constant) | `docs/04` §6.1 |
| 36 | Audio Engine | 16-Voice Polyphonic Mixer | Software audio mixer supporting 16 concurrent voices with ring voice stealing and hard saturation limiter. | Triggered sound events, stream frame count | Mixed float audio buffer for OS stream (44.1 kHz) | Saturated voices steal oldest channel (voice 0) | `docs/04` §6.3 |
| 37 | Audio Engine | Procedural UI Click Sound | 15ms duration, 2400 Hz square wave (50% duty), linear envelope decay. | Trigger UI click event | 15ms audio burst | Volume clamped to $[0.0, 1.0]$ | `docs/04` §6.2 |
| 38 | Audio Engine | Procedural Footstep (Step) Sound | 40ms duration, 0.7 LFSR noise + 0.3 80 Hz triangle thump, rapid exponential decay ($\lambda = 65$). | Footstep trigger event | 40ms percussive thud | Negligible volume ($< 0.001$) skips voice allocation | `docs/04` §6.2 |
| 39 | Audio Engine | Procedural Jump Sound | 90ms duration, 25% duty square wave, ascending frequency sweep 140 Hz $\to$ 560 Hz, linear decay. | Player jump keypress on ground | 90ms ascending chirp | Clamped at 560 Hz ceiling | `docs/04` §6.2 |
| 40 | Audio Engine | Procedural Block Break Sound | 160ms duration, 0.85 LFSR noise + 0.15 pitch-falling square wave ($120 \to 0$ Hz), irregular 4-grain power decay $(1-(t/0.16)^{0.7})$. | Block destroyed event | 160ms crunch and shatter | Automatically releases voice at 160ms | `docs/04` §6.2 |
| 41 | Audio Engine | Procedural Block Place Sound | 50ms duration, pitch plummeting triangle wave ($220 \cdot 2^{-25t}$ Hz), rapid exponential decay ($e^{-50t}$). | Block successfully placed | 50ms solid thud | Frequency plummets smoothly to ~45 Hz | `docs/04` §6.2 |
| 42 | Audio Engine | 3D Positional Audio Attenuation | Inverse distance law $\text{Volume} = V_0 / (1.0 + d/d_0)$ for single-channel mono sound events. | Sound world position, player eye position | Attenuated linear volume scalar | Distance $> 32\text{m}$ culled before mixer allocation | `docs/06` §4.3 |
| 43 | HUD & Menus | Crosshair Display | High-contrast centered reticle ($16 \times 16$ or $10 \times 10$) rendered at screen center $(W/2, H/2)$ with additive/invert blend. | Viewport width and height | Centered screen quad | Scales correctly on window resize | `ORIGINAL_REQUEST.md` R4, `docs/01` §4.2 |
| 44 | HUD & Menus | 9-Slot Hotbar UI | Bottom-centered HUD element displaying 9 item slots, active selection highlight border, and stack counts. | HotbarModel state (active slot, item counts) | 2D textured quad batch on HUD pass | Slot index clamped to $[0..8]$; scroll wraps modulo 9 | `docs/02` §6.1, `docs/01` §4.2 |
| 45 | HUD & Menus | Player Health Hearts HUD | Canonical 10-heart display (20 HP) rendered above hotbar; supports full heart, half heart, and empty background. | Player health scalar / integer ($0..20$) | Row of 10 heart glyphs | Health $> 20$ clamped to 20; health $\le 0$ shows 10 empty hearts | `ORIGINAL_REQUEST.md` R4, `docs/01` §4.2 |
| 46 | HUD & Menus | In-Game Pause Menu | Escape key toggles pause state; uncaptures mouse cursor, draws translucent dark overlay with Resume, Options, and Quit buttons. | Keypress `GLFW_KEY_ESCAPE` | Interactive GUI overlay | Simulation paused; world state preserved | `docs/02` §2.1, `docs/01` §4.2 |
| 47 | HUD & Menus | Inventory Screen GUI | 'E' key toggles inventory container screen; releases mouse cursor for slot dragging/inspection. | Keypress `GLFW_KEY_E` | Full inventory UI overlay | Re-pressing 'E' or 'Escape' recaptures cursor and hides UI | `docs/02` §6.1, §8 |
| 48 | Streaming & Lifecycle | Chunk Lifecycle State Machine | Unidirectional thread-safe states: UNLOADED $\to$ QUEUED_GEN $\to$ GEN_TERRAIN $\to$ GEN_FEATURES $\to$ READY_MESH $\to$ MESHING $\to$ PENDING_UPLOAD $\to$ ACTIVE $\to$ UNLOADED. | Chunk manager priority queue | Thread-safe state transitions | Requires 4 orthogonal neighbors in READY_MESH before meshing | `docs/03` §5.2 |
| 49 | Streaming & Lifecycle | Budgeted GPU Upload Subsystem | Frame-budgeted mesh consumption (max 2.0 ms or 2 chunks/frame) from worker MPSC ring buffer, preventing driver stalls. | Pending GPU mesh queue, elapsed frame timer | Committed OpenGL VBO/VAO bindings | Uploads exceeding 2.0 ms defer to subsequent frame | `docs/03` §5.3, `docs/01` §4.3 |
| 50 | Streaming & Lifecycle | Frustum Chunk Culling | AABB vs 6 frustum planes test on chunk bounds $([CX \cdot 16, 0, CZ \cdot 16], [CX \cdot 16 + 16, 256, CZ \cdot 16 + 16])$. | Camera View-Projection matrix, Chunk AABB | Render pass inclusion boolean | Skipped chunks bypass draw call submission entirely | `docs/03` §5.4 |

---

## Edge Cases

| # | Feature | Input | Observed Behavior |
|---|---|---|---|
| 1 | Coordinate Transform | World coordinate $X = -1$ | Bitshift `(-1 >> 4)` in standard C rounds to -1 on some compilers or depends on implementation. The flooring formula `(X >= 0) ? (X >> 4) : ((X - 15) >> 4)` correctly maps $X=-1 \to CX=-1$ and $lx = 15$. |
| 2 | Coordinate Transform | World coordinate $X = -16$ | Correctly maps to $CX = -1$ and $lx = 0$. $X = -17$ maps to $CX = -2$ and $lx = 15$. |
| 3 | Memory Indexing | Boundary voxel $(15, 255, 15)$ | Evaluates to $\text{Index} = 255 + 256 \times 15 + 4096 \times 15 = 255 + 3840 + 61440 = 65535$, exactly the last byte of the 64 KiB array. |
| 4 | Memory Indexing | $Y \ge 256$ or $Y < 0$ | World height bounds violated; sampled as `BLOCK_AIR` (0) without out-of-bounds memory access. |
| 5 | Tree Generation | Tree coordinate $(x=15, z=15)$ at chunk edge | Unconstrained canopy stamping would write to neighbor chunk not yet loaded, causing cascading deadlocks or memory corruption. Boundary rule forces decorators to stamp within $x,z \in [2, 13]$. |
| 6 | Cave Carving | Cave worm noise evaluated at $y \in [0, 4]$ | Dual-noise threshold is met, but bedrock protection overrides carving: $y=0$ remains 100% `BLOCK_BEDROCK`, preserving world floor barrier. |
| 7 | Meshing Face Culling | Two adjacent `BLOCK_STONE` voxels | Both blocks return `IsOpaque == true`. Mask evaluates to 0. No internal quad generated between the blocks. |
| 8 | Meshing Face Culling | `BLOCK_WATER` adjacent to `BLOCK_AIR` | Water is non-opaque (`IsOpaque == false`). Water surface emits a quad in the translucent pass; air emits nothing. |
| 9 | Meshing Face Culling | `BLOCK_WATER` adjacent to `BLOCK_WATER` | Both are water; boundary between identical transparent fluids does not emit interior faces. |
| 10 | Meshing Face Culling | Chunk edge voxel $(0, y, z)$ when West neighbor chunk is not loaded | West neighbor pointer is `nullptr`. Sample returns `BLOCK_AIR`, generating a visible chunk wall until neighbor generates and meshes. |
| 11 | Ambient Occlusion | Vertex in an interior convex crease with both side blocks opaque | $S_1$ opaque and $S_2$ opaque. AO formula forces $AO = 0$ immediately, preventing corner light leaks regardless of diagonal corner $C$. |
| 12 | Quad Triangulation | Greedy quad with asymmetrical diagonal AO ($AO_0=3, AO_2=3$ vs $AO_1=0, AO_3=0$) | $AO_0 + AO_2 = 6 > AO_1 + AO_3 = 0$. Triangulation index order flips to $\{0, 1, 2, 0, 2, 3\}$ to interpolate along the bright diagonal ridge without a dark seam. |
| 13 | Texture UV Wrapping | Greedy merged quad of width $W=8$, height $H=4$ | Naive UV would stretch single 16x16 texture over $8 \times 4$ blocks. Fragment shader `fract(vUV)` repeats texture $8 \times 4$ times seamlessly. |
| 14 | Texture Atlas Sampling | Linear interpolation (`GL_LINEAR`) across tile boundaries | Texels interpolate into adjacent atlas slots causing edge discoloration (texel bleeding). Resolved by using `GL_NEAREST` or 2D Texture Array (`sampler2DArray`). |
| 15 | Audio Voice Allocation | 17 simultaneous sounds triggered in single frame | Mixer capacity is 16 voices. Ring allocator steals voice 0 (the oldest voice), preventing mixer buffer overflow or audio stall. |
| 16 | Audio Limiter | 10 sounds playing simultaneously in phase | Cumulative sum of sample values exceeds $+1.0$. Hard saturation limiter clamps output to $[-1.0, +1.0]$, preventing integer wrap and crackle distortion. |
| 17 | Audio Attenuation | Sound event triggered 40 blocks away from player | $d = 40.0\text{ m} > 32.0\text{ m}$ threshold. Attenuation formula yields negligible volume; sound event is culled before allocating a mixer voice. |
| 18 | Hotbar Selection | Mouse wheel scrolled down 1 tick when on slot 8 | Standard Minecraft scroll increments index: $(8 + 1) \pmod 9 = 0$ (wraps back to first slot). |
| 19 | Hotbar Selection | Mouse wheel scrolled up 1 tick when on slot 0 | Evaluates to $(0 - 1) = -1$; modulo wrap logic converts to slot 8. |
| 20 | Pause Menu Toggle | Player hits Escape while in active gameplay | Engine immediately unlocks mouse cursor (`GLFW_CURSOR_NORMAL`), centers cursor, halts physics simulation updates, and presents pause GUI overlay. |

---

## Architectural & Data Structure Specifications

### 1. Chunk Data Structure & Indexing Formats

```cpp
#include <cstdint>
#include <cstddef>
#include <array>

// Exact 64 KiB flat chunk representation matching L2 cacheline alignment
class alignas(64) ChunkData {
public:
    static constexpr size_t CHUNK_SIZE_X = 16;
    static constexpr size_t CHUNK_SIZE_Y = 256;
    static constexpr size_t CHUNK_SIZE_Z = 16;
    static constexpr size_t TOTAL_VOXELS = CHUNK_SIZE_X * CHUNK_SIZE_Y * CHUNK_SIZE_Z; // 65,536

    // Flat contiguous storage: exactly 65,536 bytes
    std::array<uint8_t, TOTAL_VOXELS> voxels;

    // Y-Internal Indexing for contiguous vertical column scans
    [[nodiscard]] static constexpr inline size_t GetIndex(size_t x, size_t y, size_t z) noexcept {
        return y + (x * CHUNK_SIZE_Y) + (z * CHUNK_SIZE_Y * CHUNK_SIZE_X);
    }

    [[nodiscard]] inline uint8_t GetBlock(size_t x, size_t y, size_t z) const noexcept {
        return voxels[GetIndex(x, y, z)];
    }

    inline void SetBlock(size_t x, size_t y, size_t z, uint8_t id) noexcept {
        voxels[GetIndex(x, y, z)] = id;
    }
};

// Coordinate Transform Helpers (Floored arithmetic for negative values)
inline int WorldToChunkCoord(int worldCoord) noexcept {
    return (worldCoord >= 0) ? (worldCoord >> 4) : ((worldCoord - 15) >> 4);
}

inline int WorldToLocalCoord(int worldCoord) noexcept {
    return (worldCoord >= 0) ? (worldCoord & 15) : ((worldCoord % 16 + 16) & 15);
}
```

### 2. Core Block Palette & Material Classification

| ID (`uint8_t`) | Identifier | Material Class | Hardness ($H_{\text{sec}}$) | Pass | Texture Faces (Top, Bottom, Side) |
|---|---|---|---|---|---|
| `0x00` | `BLOCK_AIR` | Gas / Empty | 0.0 | None | N/A |
| `0x01` | `BLOCK_STONE` | Solid Rock | 1.5 | Opaque | `(1,0), (1,0), (1,0)` |
| `0x02` | `BLOCK_DIRT` | Soil | 0.5 | Opaque | `(2,0), (2,0), (2,0)` |
| `0x03` | `BLOCK_GRASS` | Soil / Organic | 0.6 | Opaque | `(0,0), (2,0), (3,0)` |
| `0x04` | `BLOCK_SAND` | Granular Soil | 0.5 | Opaque | `(2,1), (2,1), (2,1)` |
| `0x05` | `BLOCK_SANDSTONE`| Solid Rock | 0.8 | Opaque | `(0,2), (0,2), (0,2)` |
| `0x06` | `BLOCK_SNOW` | Solid Cover | 0.2 | Opaque | `(2,3), (2,0), (2,3)` |
| `0x07` | `BLOCK_WOOD` | Organic Solid | 2.0 | Opaque | `(5,1), (5,1), (4,1)` |
| `0x08` | `BLOCK_LEAVES` | Foliage | 0.2 | Cutout | `(4,3), (4,3), (4,3)` |
| `0x09` | `BLOCK_BEDROCK` | Indestructible | -1.0 | Opaque | `(1,1), (1,1), (1,1)` |
| `0x0A` | `BLOCK_WATER` | Liquid | 100.0 | Translucent | `(13,12), (13,12), (13,12)` |
| `0x0B` | `BLOCK_CACTUS` | Foliage / Hazard| 0.4 | Cutout | `(6,4), (6,4), (5,4)` |
| `0x0C` | `BLOCK_FLOWER` | Plant Foliage | 0.0 | Cutout | `(12,0), (12,0), (12,0)` |
| `0x0D` | `BLOCK_TALLGRASS`| Plant Foliage | 0.0 | Cutout | `(7,2), (7,2), (7,2)` |
| `0x0E` | `BLOCK_GLASS` | Synthetic Solid | 0.3 | Translucent | `(1,3), (1,3), (1,3)` |

### 3. Packed Vertex Format & GPU Memory Layout

```cpp
// 64-Bit Packed Vertex for Greedy Meshing (8 bytes per vertex)
struct PackedVertex {
    // Word 0: Spatial position, face normal, ambient occlusion, block type
    // Bits  0- 4: X (0-16)
    // Bits  5-13: Y (0-256)
    // Bits 14-18: Z (0-16)
    // Bits 19-21: Normal Face Index (0-5: -X, +X, -Y, +Y, -Z, +Z)
    // Bits 22-23: Ambient Occlusion (0-3)
    // Bits 24-31: BlockID (0-255)
    uint32_t data0;

    // Word 1: Greedy UV and quad dimensions
    // Bits  0- 7: Base U (0-16)
    // Bits  8-15: Base V (0-256)
    // Bits 16-23: Quad Width W (1-16)
    // Bits 24-31: Quad Height H (1-256)
    uint32_t data1;
};
```

### 4. Ambient Occlusion 4-Voxel Neighborhood Formula

For any vertex on an emitted quad face, let $S_1$ and $S_2$ be the two orthogonal side blocks sharing the vertex edge, and $C$ be the diagonal corner block:

$$\text{AO}(S_1, S_2, C) = \begin{cases}
0 & \text{if } \text{IsOpaque}(S_1) \land \text{IsOpaque}(S_2) \\
3 - \left(\text{IsOpaque}(S_1) + \text{IsOpaque}(S_2) + \text{IsOpaque}(C)\right) & \text{otherwise}
\end{cases}$$

**Tessellation Diagonal Flip Rule:**
Given quad vertices $(V_0, V_1, V_2, V_3)$ in counter-clockwise order:
$$\text{Indices} = \begin{cases}
\{0, 1, 2, 0, 2, 3\} & \text{if } (AO_0 + AO_2) > (AO_1 + AO_3) \\
\{1, 2, 3, 1, 3, 0\} & \text{otherwise}
\end{cases}$$

### 5. Procedural Synthesizer Formulas & Audio Catalog

| Sound ID | Sound Event | Duration | Generator Formula | Envelope Formula |
|---|---|---|---|---|
| 1 | `SFX_CLICK` | 15 ms | $S_{\text{sq}}(\phi), f=2400\text{ Hz}, d=0.5$ | $E(t) = 1.0 - \frac{t}{0.015}$ |
| 2 | `SFX_STEP` | 40 ms | $0.7 \cdot \text{LFSR}() + 0.3 \cdot S_{\text{tri}}(80\text{ Hz})$ | $E(t) = e^{-65.0 \cdot t}$ |
| 3 | `SFX_JUMP` | 90 ms | $S_{\text{sq}}(\phi), f(t) = 140 + 420 \cdot \left(\frac{t}{0.090}\right), d=0.25$ | $E(t) = 1.0 - \frac{t}{0.090}$ |
| 4 | `SFX_BLOCK_BREAK` | 160 ms | $0.85 \cdot \text{LFSR}() + 0.15 \cdot S_{\text{sq}}(120 \cdot (1 - \frac{t}{0.160}))$ | $E(t) = 1.0 - \left(\frac{t}{0.160}\right)^{0.7}$ |
| 5 | `SFX_BLOCK_PLACE` | 50 ms | $S_{\text{tri}}(\phi), f(t) = 220.0 \cdot 2^{-25.0 \cdot t}$ | $E(t) = e^{-50.0 \cdot t}$ |

### 6. Master Texture Atlas & Embedded Font Grid

- **Dimensions:** $256 \times 256$ pixels, 32-bit RGBA (262,144 bytes).
- **Tile Dimensions:** $16 \times 16$ pixels ($16 \times 16 = 256$ slots).
- **Rows 0 to 11:** Canonical block textures and fluid flow tiles.
- **Rows 12 to 15:** 64 monochrome ASCII font glyphs ($16 \times 16$ grid covering ASCII 0..127).
- **Embedded Storage:** Stored as static compressed PNG byte array in `.rodata` (~14.3 KiB) and decompressed into a temporary 256 KiB buffer during cold start (`LoadEmbeddedAtlas()`), or stored as raw static RGBA32 array.

---

## Ponytail Engineering Ceilings & Upgrade Paths

| Subsystem | Minimalist Baseline | Explicit Limitation / Ceiling | Trigger for Upgrade | Upgrade Path |
|---|---|---|---|---|
| **Voxel Storage** | `uint8_t` flat array (64 KiB) | 256 distinct block IDs | Extensive modding or >256 blocks | `uint16_t` palette mapping |
| **Noise Generation** | Hardcoded analytic fBM functions in C++ | Fixed 4 biomes | Dynamic biome scripting | Configurable biome graph parser |
| **Meshing** | Single-pass Greedy Mesher | Meshes entire 16x256 column | Dynamic deformation latency spikes | 16x16x16 sub-chunk section meshing |
| **Texture Atlas** | Hardware `GL_NEAREST` or 2D Texture Array | 256 slots (256x256 atlas) | High-res HD texture packs (64x64) | Bindless textures / 2048x2048 atlas |
| **Lighting** | Directional tinting + per-vertex AO | No dynamic light scattering in deep caves | Torches / lanterns emitting local light | 4-bit cellular automata BFS flood-fill |
| **Audio Engine** | 80-line real-time procedural synthesizer | Retro synthesized 8-bit sound character | Live acoustic foley / reverb requirements | Freeverb DSP topology + resonant biquad filter |
| **Inventory UI** | Fixed 9-slot linear hotbar array | No drag-and-drop 2x2 crafting container | Survival crafting table integration | Multi-container slot matrix with item dragging |

---

## Latency Budgets & Performance Verification Gates

1. **Cold-Start Latency:** Process launch to interactive first frame in **$< 80\text{ ms}$**.
2. **Memory Footprint:** Active 289-chunk voxel storage consumes **$18.06\text{ MiB}$**; total engine RSS **$< 96\text{ MB}$**.
3. **Meshing Performance:** Greedy meshing of single dirty chunk completes in **$< 1.2\text{ ms}$**; main thread upload budget capped at **$2.0\text{ ms}$** per frame.
4. **Frame Pacing:** Stable **$\ge 60\text{ FPS}$** with **zero in-loop heap allocations** (`0 bytes malloc/free`).
5. **Executable Size:** Self-contained stripped release executable **$< 4.0\text{ MB}$**.
