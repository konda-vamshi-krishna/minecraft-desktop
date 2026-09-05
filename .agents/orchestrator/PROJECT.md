# Project: Minecraft Desktop — Universal 1-Click Native Edition

## Architecture
The Minecraft Desktop engine is structured into strictly decoupled, zero-allocation subsystems implemented in clean C99/C++17 with statically linked Raylib and OpenGL 3.3 Core profile. The system guarantees instant single-click desktop execution across Windows, Linux, and macOS with zero runtime dependencies (no JRE, Python, .NET, or MSVC redistributable DLLs), cold start < 80ms, uncompressed release binary < 4.0MB, and peak RSS < 96MB.

```
+-----------------------------------------------------------------------------------+
|                                  PLATFORM LAYER                                   |
|   Base-Path Resolver (GetModuleFileNameW / /proc/self/exe / _NSGetExecutablePath) |
|   Windowing, Input Events, High-Res Timer, OpenGL 3.3 Context, Audio Stream Out   |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                                  ENGINE RUNTIME                                   |
|   Fixed 60 Hz Physics Loop (dt=1/60s, accumulator clamping <= 0.25s)              |
|   Render Interpolation Alpha (alpha = accumulator / dt)                           |
|   Day/Night Celestial Clock (1200s period, orbital sun vector)                    |
+-----------------------------------------------------------------------------------+
        |                                        |                          |
        v                                        v                          v
+-----------------------+     +-----------------------+     +-----------------------+
|    WORLD & CHUNKS     |     |   GAMEPLAY & ENTITY   |     |    ASSETS & AUDIO     |
| - 16x256x16 Chunk Mem |     | - Player AABB         |     | - Embedded Atlas      |
|   (64 KiB contiguous) |     |   (0.6x1.8m / 0.6x1.5m|     |   (256x256 .rodata)   |
| - 17x17 Toroidal Grid |     | - Kinematics (g=32,   |     | - ASCII Bitmap Font   |
|   (289 chunks, 18 MiB)|     |   v_term=-78.4, jump) |     | - 16-Voice Synthesizer|
| - fBM Simplex Terrain |     | - Collision (Y->X->Z) |     |   (Click, Step, Jump, |
| - Whittaker Biomes    |     | - Auto-step (0.55m)   |     |    Break, Place)      |
| - 3D Cave Carving     |     | - DDA Raycast (5.0m)  |     | - HUD & Menus         |
| - 3-Axis Greedy Mesh  |     | - Break / Place FSM   |     |   (Crosshair, Hotbar, |
| - 4-Byte Packed Verts |     | - 41-Slot Inventory   |     |    Hearts, Pause, Inv)|
| - Per-Vertex AO (0..3)|     | - Crafting 2x2 & 3x3  |     +-----------------------+
+-----------------------+     | - Survival (HP, Hunger|
                              | - Item Drops (3D bob) |
                              +-----------------------+
```

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Base-Path Resolution Engine | Platform-native discovery of executable folder (`GetModuleFileNameW`, `/proc/self/exe`, `_NSGetExecutablePath`) | M1 | docs/05 §2 |
| 2 | Portable Save Storage | Game saves stored strictly in `<BasePath>/saves/` with graceful fallback | M1 | docs/05 §2 |
| 3 | Fixed 60 Hz Physics Loop | Deterministic physics update loop with 0.25s accumulator clamping | M1 | docs/01 §4 |
| 4 | Render Interpolation Alpha | Sub-frame state interpolation ($\alpha = \text{acc} / dt$) for stutter-free display | M1 | docs/01 §4 |
| 5 | Camera Euler Matrices | Yaw [0, 360), Pitch [-89, +89] clamping with planar forward/right vectors | M1 | docs/02 §2 |
| 6 | Subsystem Decoupling | Clean separation of Platform, Runtime, World, Physics, and Audio subsystems | M1 | docs/01 §3 |
| 7 | Contiguous Chunk Memory | 64 KiB flat array per chunk (`alignas(64) uint8_t[65536]`, Y-internal index) | M2 | docs/03 §2 |
| 8 | Toroidal 17x17 Active Grid | 289 active chunks (18.06 MiB static BSS RAM) centered around player | M2 | docs/03 §2 |
| 9 | Floored Coordinate Math | Fast bitshift coordinate conversions (`WorldToChunkCoord`, `WorldToLocalCoord`) | M2 | docs/03 §2 |
| 10 | fBM Simplex 2D Terrain | Multi-octave fractional Brownian motion noise generating natural terrain | M2 | docs/03 §3 |
| 11 | Whittaker Biome Matrix | Temperature and Moisture fields mapping Plains, Desert, Mountains, Forest | M2 | docs/03 §3 |
| 12 | 3D Cave Worm Carving | Dual-field 3D Simplex noise carve-out ($|N_1| < 0.05 \land |N_2| < 0.05$) | M2 | docs/03 §3 |
| 13 | Coordinate PRNG Seeding | SplitMix64 hash seeding for trees, foliage, and ore generation | M2 | docs/03 §3 |
| 14 | 3-Axis Greedy Meshing | Single-pass quad merging reducing vertices/draw calls by >80% | M2 | docs/03 §4 |
| 15 | 4-Byte Packed Vertex Format | Single `uint32_t` encoding X:5, Y:9, Z:5, Normal:3, Tex:8, AO:2 | M2 | docs/01 §5 |
| 16 | Vertex Ambient Occlusion | 4-level AO (0..3) with quad diagonal index flip guard | M2 | docs/03 §4 |
| 17 | Budget-Capped Meshing | Queue capping mesh generation to max 2 chunks/frame ($\le 1.5\text{ms}$) | M2 | docs/01 §4 |
| 18 | Axis-Decoupled Collision | Collision resolution ordered strictly $Y \to X \to Z$ against voxel grid | M3 | docs/02 §4 |
| 19 | Player Hitbox Dimensions | AABB: Standing $0.6 \times 1.8 \times 0.6\text{m}$, Sneaking $0.6 \times 1.5 \times 0.6\text{m}$ | M3 | docs/02 §4 |
| 20 | Eye Height Offsets | Camera offset: Standing +1.62m, Sneaking +1.35m | M3 | docs/02 §4 |
| 21 | Gravity & Terminal Velocity | $g = 32.0\text{ m/s}^2$, exponential drag, $v_{\text{term}} = -78.4\text{ m/s}$ | M3 | docs/06 §3 |
| 22 | Ground Friction & Air Drag | Ground damping 0.546, air damping 0.98, normalized wish vector | M3 | docs/06 §3 |
| 23 | Jump Impulse Kinematics | Instantaneous $v_y = 8.4\text{ m/s}$ reaching 1.252m apex clearance | M3 | docs/06 §3 |
| 24 | Auto-Step Upward Probe | Speculative $+0.55\text{m}$ upward clearance test for seamless 0.5m step-up | M3 | docs/02 §4 |
| 25 | Sneak Ledge-Clamp | Downward $-0.05\text{m}$ edge probe preventing fall-off | M3 | docs/02 §4 |
| 26 | Dynamic FOV Warping | Velocity-based FOV multiplier (1.15x sprint, 0.90x sneak, $\lambda=12$) | M3 | docs/02 §2 |
| 27 | Amanatides-Woo DDA Raycast | Fast voxel traversal stepping through every intersected lattice cell | M3 | docs/02 §3 |
| 28 | Reach Distance Limits | Survival 4.5m, Creative 5.0m maximum interaction envelope | M3 | docs/06 §3 |
| 29 | Entered Face Normal Invariant | Surface normal of block face entered during raycast ($\mathbf{n} = -\text{step}_i \hat{\mathbf{e}}_i$) | M3 | docs/02 §3 |
| 30 | Progressive Block Breaking FSM | Continuous hold breaking with material hardness and tool multipliers | M3 | docs/02 §5 |
| 31 | 10-Stage Crack Visuals | Crack stages $0..9$ mapped from normalized breaking progress | M3 | docs/02 §5 |
| 32 | Anti-Suffocation Placement | Rejection of block placement intersecting player AABB | M3 | docs/02 §5 |
| 33 | 41-Slot Flat Inventory Array | 9 Hotbar + 27 Main Storage + 4 Armor + 1 Offhand in contiguous memory | M4 | docs/02 §6 |
| 34 | Hotbar Scroll State Machine | 9-slot selection mapped to keys 1-9 and mouse wheel with modulo wrap | M4 | docs/02 §6 |
| 35 | Stack Size Hierarchy | Canonical stack boundaries: 64 (blocks/items), 16 (compact), 1 (tools/armor) | M4 | docs/02 §6 |
| 36 | Mouse Slot Interactions | Pickup stack, place single, swap stacks, remainder retention | M4 | docs/02 §6 |
| 37 | Shift-Click Quick-Move | Instant slot transfer between hotbar, main storage, and armor | M4 | docs/02 §6 |
| 38 | Mouse Drag Distribution | Left-drag even distribution, Right-drag 1-per-slot distribution | M4 | docs/02 §6 |
| 39 | 2x2 Player Crafting Grid | Embedded 4-input matrix in player inventory with 1 output | M4 | docs/02 §6 |
| 40 | 3x3 Crafting Table Grid | 9-input crafting matrix accessed via Crafting Table block | M4 | docs/02 §6 |
| 41 | Shaped & Shapeless Matcher | Pattern matching supporting relative coordinates and unordered sets | M4 | docs/02 §6 |
| 42 | Canonical Recipe Catalog | Planks, sticks, tools (wood/stone/iron), table, furnace, torches, etc. | M4 | docs/02 §6 |
| 43 | Player Health Pool & i-Frames | 20 HP (10 hearts), 10-tick (0.5s) invulnerability frames, damage flash | M4 | docs/02 §7 |
| 44 | Hunger & Exhaustion System | 20 food shanks, saturation pool, exhaustion counter driving starvation | M4 | docs/02 §7 |
| 45 | Fall Damage & Water Negation | Damage $= \max(0, \lceil d - 3.0 \rceil)$, full negation on water impact | M4 | docs/06 §3 |
| 46 | 3D Item Drop Entity | Floating bobbing item sprite ($0.1 \sin(\pi t)$, $180^\circ/\text{s}$ rotation, 5m despawn) | M4 | docs/02 §7 |
| 47 | Hand Swing Animation | 6-tick (0.3s) first-person tool swing rotation | M4 | docs/02 §7 |
| 48 | Creative vs Survival Rules | Finite HP/resources/mining vs instant break/invulnerability/flight | M4 | docs/06 §3 |
| 49 | Embedded 256x256 Texture Atlas | Master atlas compiled into `.rodata` segment (zero loose files) | M5 | docs/04 §3 |
| 50 | Embedded ASCII Bitmap Font | Glyphs 0..127 compiled into `.rodata` for text rendering | M5 | docs/04 §3 |
| 51 | Anti-Texel Bleed UV Insets | Half-margin inset epsilon eliminating edge bleeding in mipmaps | M5 | docs/04 §3 |
| 52 | 16-Voice Procedural Audio | Real-time polyphonic software mixer running at 44.1 kHz PCM | M5 | docs/04 §6 |
| 53 | Procedural UI Click Sound | 15ms 2400 Hz square wave with linear decay | M5 | docs/04 §6 |
| 54 | Procedural Footstep Sound | 40ms Galois LFSR noise + 80 Hz thump with exponential decay | M5 | docs/04 §6 |
| 55 | Procedural Jump Sound | 90ms square frequency sweep (140 $\to$ 560 Hz) | M5 | docs/04 §6 |
| 56 | Procedural Block Break Sound | 160ms LFSR noise + falling square sub-harmonic | M5 | docs/04 §6 |
| 57 | Procedural Block Place Sound | 50ms triangle wave pitch plummet ($220 \cdot 2^{-25t}$) | M5 | docs/04 §6 |
| 58 | Directional Face Shading | Top 1.0, Bottom 0.5, North/South 0.8, East/West 0.6 | M5 | docs/02 §7 |
| 59 | 1200s Celestial Orbital Cycle | Dynamic day/night cycle driving sun/moon orbit and sky lighting | M5 | docs/02 §7 |
| 60 | HUD Reticle & Hotbar UI | Centered crosshair, bottom-center hotbar with selection highlight | M5 | docs/04 §7 |
| 61 | HUD Health Hearts | 10 health hearts rendering current HP pool | M5 | docs/04 §7 |
| 62 | Pause Menu & Cursor Lock | Escape key unlocks mouse, shows pause menu; click resumes | M5 | docs/04 §7 |
| 63 | Inventory Screen Overlay | 'E' key toggles player inventory GUI with 2x2 crafting | M5 | docs/04 §7 |
| 64 | Universal Native Executables | Windows PE (`.exe`), Linux ELF, macOS Universal 2 binaries | M6 | docs/05 §1 |
| 65 | Win32 Resource Script & Icon | Embedded 101 ICON in `res/resource.rc` | M6 | docs/05 §3 |
| 66 | Win32 Application Manifest | Embedded manifest with `asInvoker` and `PerMonitorV2` DPI | M6 | docs/05 §3 |
| 67 | AV Clearance / Zero UPX | Raw PE/ELF packaging without compression packers | M6 | docs/05 §3 |
| 68 | GitHub Actions CI Matrix | 3-platform build workflow (`build_and_release.yml`) | M6 | docs/05 §5 |
| 69 | Dynamic Linker Audit Gates | Automated inspection (`dumpbin`, `ldd`, `otool`) enforcing zero missing DLLs | M6 | docs/05 §5 |
| 70 | Release Packaging & Hashes | Automated release creation with `SHA256SUMS.txt` | M6 | docs/05 §5 |
| 71 | 4-Tier E2E Test Suite | Automated opaque-box functional, boundary, interaction, and application tests | E2E | TEST_INFRA |
| 72 | Adversarial Hardening (Tier 5) | White-box edge case test coverage and stress testing | FM | Final M |
| 73 | Forensic Integrity Audit | Systematic anti-cheating / anti-facade verification | FM | Final M |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| E2E | E2E Testing Track | Requirement-driven opaque-box test runner, harness, and Tiers 1-4 test suites (`TEST_INFRA.md`, `TEST_READY.md`) | none | DONE |
| M1 | Architecture, Runtime & Engine Core | Subsystem architecture, base-path resolver, portable save path, windowing, input, fixed 60Hz loop, interpolation alpha, camera | none | DONE |
| M2 | World Generation, Chunks & Meshing | 64KB chunk memory, coordinate conversions, fBM Simplex terrain, Whittaker biomes, 3D caves, greedy meshing, 4-byte packed vertices, per-vertex AO | M1 | DONE |
| M3 | Player Kinematics, Collision & Interaction | Player AABB, gravity, terminal velocity, jump, axis-decoupled collision ($Y \to X \to Z$), auto-step, sneak clamp, DDA raycast, break/place FSM, 9-slot hotbar | M1, M2 | IN_PROGRESS |
| M4 | Inventory, Crafting & Survival Systems | 41-slot inventory, mouse slot state machine, stack limits, 2x2/3x3 crafting, canonical recipes, health/damage/hunger, fall damage, item drops | M3 | PLANNED |
| M5 | Asset Pipeline, Procedural Audio & UI | Embedded 256x256 atlas & font in `.rodata`, UV insets, 16-voice procedural audio synthesizer, directional shading, HUD, pause menu, inventory GUI | M1, M4 | PLANNED |
| M6 | GitHub Packaging & Zero-Config CI | Statically linked cross-platform builds (Win/Linux/Mac), Win32 manifest/resource, linker audit gates, GitHub Actions release matrix | M1, M5 | PLANNED |
| FM | Final Milestone: E2E Verification & Hardening | Phase 1: 100% pass on Tiers 1-4 E2E tests. Phase 2: Adversarial coverage hardening (Tier 5) + Forensic Auditor integrity pass | M1-M6, E2E | PLANNED |

## Interface Contracts

### Platform ↔ Engine Runtime (`platform.h` ↔ `runtime.h`)
```c
typedef struct {
    int windowWidth;
    int windowHeight;
    const char* title;
    bool targetFps60;
    bool headless;
} PlatformConfig;

typedef struct {
    char basePath[1024];
    char saveDir[1024];
    bool isReadOnlyFallback;
} StoragePaths;

void Platform_Init(const PlatformConfig* config);
void Platform_Shutdown(void);
bool Platform_ShouldClose(void);
void Platform_PollEvents(void);
double Platform_GetTime(void);
void Platform_GetStoragePaths(StoragePaths* outPaths);
```

### Engine Runtime ↔ World Subsystem (`runtime.h` ↔ `world.h`)
```c
#define CHUNK_WIDTH 16
#define CHUNK_HEIGHT 256
#define CHUNK_DEPTH 16
#define CHUNK_VOXEL_COUNT (CHUNK_WIDTH * CHUNK_HEIGHT * CHUNK_DEPTH)

typedef struct {
    alignas(64) uint8_t voxels[CHUNK_VOXEL_COUNT];
    int chunkX;
    int chunkZ;
    bool isModified;
    bool isMeshDirty;
    uint32_t vboId;
    uint32_t vertexCount;
} Chunk;

void World_Init(int seed);
void World_Update(float playerX, float playerZ, double dt);
uint8_t World_GetBlock(int worldX, int worldY, int worldZ);
bool World_SetBlock(int worldX, int worldY, int worldZ, uint8_t blockId);
void World_Render(const Camera* camera, float renderAlpha);
```

### World Subsystem ↔ Physics & Collision (`world.h` ↔ `physics.h`)
```c
typedef struct {
    float minX, minY, minZ;
    float maxX, maxY, maxZ;
} AABB;

typedef struct {
    float x, y, z;
    float vx, vy, vz;
    bool isGrounded;
    bool isSneaking;
    bool isSprinting;
    AABB hitbox;
} PlayerPhysicsState;

void Physics_Step(PlayerPhysicsState* player, float dt);
bool Physics_CheckCollision(const AABB* box);
bool Physics_Raycast(float startX, float startY, float startZ,
                     float dirX, float dirY, float dirZ,
                     float maxDist, RaycastHit* outHit);
```

### Gameplay ↔ Inventory & Crafting (`gameplay.h` ↔ `inventory.h`)
```c
typedef struct {
    uint8_t itemId;
    uint8_t count;
    uint16_t durability;
} ItemStack;

typedef struct {
    ItemStack hotbar[9];
    ItemStack main[27];
    ItemStack armor[4];
    ItemStack offhand;
    int selectedHotbarSlot;
    ItemStack cursorItem;
} PlayerInventory;

bool Inventory_CanAddItem(PlayerInventory* inv, const ItemStack* item);
bool Inventory_AddItem(PlayerInventory* inv, const ItemStack* item);
bool Crafting_Match2x2(const ItemStack input[4], ItemStack* outResult);
bool Crafting_Match3x3(const ItemStack input[9], ItemStack* outResult);
```

### Asset Pipeline ↔ Procedural Audio (`assets.h` ↔ `audio.h`)
```c
typedef enum {
    SOUND_CLICK = 0,
    SOUND_STEP,
    SOUND_JUMP,
    SOUND_BREAK,
    SOUND_PLACE,
    SOUND_COUNT
} SoundEvent;

void Audio_Init(int sampleRate);
void Audio_PlaySound(SoundEvent event, float volume, float pitch);
void Audio_MixCallback(float* outputBuffer, int frameCount);
void Audio_Shutdown(void);
```

## Code Layout
```
g:/minecraft_desktop/
├── .github/
│   └── workflows/
│       └── build_and_release.yml      # 3-platform matrix build & packaging CI
├── docs/                              # Project specifications & architecture docs
├── src/
│   ├── main.c                         # Entry point, base-path resolution, engine loop
│   ├── platform/
│   │   ├── platform.h                 # Windowing, input events, timing, storage paths
│   │   └── platform_desktop.c         # Raylib / OpenGL 3.3 platform implementation
│   ├── core/
│   │   ├── math_utils.h               # Vector, matrix, AABB, and bitshift helpers
│   │   └── runtime.c                  # Fixed 60Hz loop, state accumulator, render alpha
│   ├── world/
│   │   ├── world.h                    # World grid, chunk storage, coordinate transforms
│   │   ├── terrain.c                  # Simplex noise, Whittaker biomes, cave worms
│   │   ├── chunk.c                    # Contiguous 64KB chunk memory & indexing
│   │   └── mesher.c                   # 3-axis greedy mesher, packed vertices, vertex AO
│   ├── gameplay/
│   │   ├── player.h                   # Player kinematics, camera, and bounding box
│   │   ├── player.c                   # Axis-decoupled collision (Y->X->Z), auto-step
│   │   ├── raycast.c                  # Amanatides-Woo DDA voxel raymarching
│   │   ├── interaction.c              # Progressive block breaking & placement FSM
│   │   ├── inventory.c                # 41-slot flat inventory, drag/split interactions
│   │   └── crafting.c                 # 2x2 & 3x3 pattern matching and canonical recipes
│   ├── render/
│   │   ├── renderer.h                 # Voxel shader pipeline, camera, lighting
│   │   ├── renderer.c                 # OpenGL 3.3 draw calls, directional shading
│   │   └── hud.c                      # Crosshair, hotbar UI, health hearts, menus
│   ├── assets/
│   │   ├── atlas_data.h               # Embedded 256x256 texture atlas in .rodata
│   │   └── font_data.h                # Embedded retro ASCII bitmap font in .rodata
│   └── audio/
│       ├── audio.h                    # 16-voice procedural polyphonic software mixer
│       └── synthesizer.c              # LFSR noise, square/triangle ADSR waveforms
├── tests/
│   ├── test_runner.py                 # Opaque-box E2E test runner
│   ├── tier1_features/                # Tier 1 functional test cases (>=5 per feature)
│   ├── tier2_boundaries/              # Tier 2 boundary & corner test cases
│   ├── tier3_interactions/            # Tier 3 pairwise cross-feature test cases
│   └── tier4_workloads/               # Tier 4 real-world application scenarios
├── res/
│   ├── app.manifest                   # Win32 DPI & UAC execution manifest
│   ├── resource.rc                    # Win32 icon & version resource script
│   └── icon.ico                       # Game icon
├── Makefile                           # Local cross-platform Makefile
├── CMakeLists.txt                     # CMake build configuration
├── ORIGINAL_REQUEST.md                # Verbatim immutable user request
├── TEST_INFRA.md                      # E2E Test Suite Architecture & Specification
└── TEST_READY.md                      # Test Suite Readiness Attestation
```

## Ponytail Minimalist Ledger
All implementations must adhere to the 7 Ponytail rungs:
1. `// ponytail: [chunk meshing: single-thread budget capped] -> [thread pool worker queue if chunk loading lags at render distance >= 16]`
2. `// ponytail: [world grid: 17x17 toroidal BSS] -> [infinite dynamic chunk hash table if infinite world exploration requested]`
3. `// ponytail: [mesh upload: single dynamic VBO streaming] -> [persistent mapped buffer GL_ARB_buffer_storage]`
4. `// ponytail: [embedded assets: compile-time .rodata array] -> [external resource pack loader]`
5. `// ponytail: [UV mapping: half-margin inset epsilon] -> [GL_TEXTURE_2D_ARRAY to eliminate texel bleed at mip levels]`
6. `// ponytail: [block registry: compile-time switch lookup] -> [dynamic data-driven JSON registry for modding]`
7. `// ponytail: [lighting: directional face shading + vertex AO] -> [4-bit flood-fill cellular automata light propagation]`
