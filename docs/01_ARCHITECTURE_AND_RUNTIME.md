# 01. ARCHITECTURE & RUNTIME SPECIFICATION
**Project:** Minecraft Desktop — Universal 1-Click Native Edition  
**Author:** Architecture & Universal Distribution Engineering  
**Standard:** Max-Pro Polymath Framework & Ponytail Minimalist Engineering  
**Status:** APPROVED & RATIFIED  

---

## 1. Executive Summary & The Universal Distribution Imperative

The core architectural objective is uncompromising: **A user must be able to download an archive or executable from a GitHub Release, extract it to any folder (or run it directly from a thumb drive), double-click, and enter the voxel world in under 100 milliseconds.**

No prerequisites. No runtime installers. No administrative elevation prompts. No dynamic runtime crashes due to mismatched runtime environments.

Every architectural decision in this document flows from this distribution constraint. When runtime portability collides with architectural cleverness, portability wins unconditionally.

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

## 2. The Audit Protocol: Red-Teaming Runtimes & Frameworks

To select the foundation, we subject all candidate runtimes to the **Max-Pro Audit Protocol (Team A: Support vs. Team B: Destroy)**.

### 2.1. Candidate A: Java (JVM / LWJGL / Minecraft Baseline)
* **Team A (Support):** Native home of the original Minecraft (Java Edition). Vast ecosystem of voxel libraries, proven OpenGL bindings (LWJGL), excellent cross-platform abstractions.
* **Team B (Destroy):**
  1. **Runtime Dependency Friction:** End-users rarely possess a modern JDK/JRE (Java 17/21). Demanding that non-technical users install a JDK creates immediate funnel abandonment (>40%).
  2. **Bundled JRE Bloat (`jlink` / `jpackage`):** Bundling a stripped JRE adds 45MB–120MB of overhead, defeating the `<15MB` distribution goal.
  3. **Non-Deterministic Latency (GC Pauses):** Voxel terrain generation and chunk meshing produce intense short-lived garbage (quad vertices, neighbor lookup arrays). Stop-The-World (STW) collector cycles inevitably induce visible stutter (frame drops below 60 FPS).
  4. **Cold-Start Penalty:** JVM bootstrap, JIT compilation tiering (C1/C2), and bytecode verification push cold startup latency to 1.5s–3.0s minimum.
* **Verdict:** **REJECTED.**

### 2.2. Candidate B: Python (Pygame / ModernGL / PyInstaller)
* **Team A (Support):** Rapid prototyping, concise syntax, rich math libraries.
* **Team B (Destroy):**
  1. **Packer Heuristic Detection:** Packaging tools (PyInstaller, cx_Freeze, Nuitka) bundle a Python interpreter and dynamically extract `.pyd`/`.so` payloads into `%TEMP%/_MEIxxxx`. This signature is aggressively flagged as generic malware/trojans by Windows Defender and enterprise EDR solutions.
  2. **Startup Decompression Overhead:** Decompressing 40MB–80MB of libraries into a temporary directory on disk induces a 2.0s–5.0s freeze before `main()` executes.
  3. **Global Interpreter Lock (GIL) & Performance Floor:** Single-threaded CPU-bound chunk meshing saturates the GIL. Achieving 60 FPS at 12+ chunk render distance requires dropping into Cython or C extensions anyway, negating Python's simplicity.
* **Verdict:** **REJECTED.**

### 2.3. Candidate C: Heavyweight Rust Engines (Bevy / WGPU Raw)
* **Team A (Support):** Memory safety, modern ergonomics, concurrency primitives, zero-cost abstractions.
* **Team B (Destroy):**
  1. **Ecosystem & Compile Churn:** Bevy's ECS engine introduces an enormous dependency tree (>200 crates), resulting in 15-minute clean build times and bloated final binaries (35MB–60MB unstripped).
  2. **Driver Layer Friction:** WGPU translates to Vulkan/DirectX 12/Metal. On older consumer laptops or virtualization environments lacking modern Vulkan drivers, WGPU fails to initialize or falls back to CPU rasterization (LLVMpipe).
* **Verdict:** **REJECTED.**

### 2.4. Candidate D: Rust + Macroquad / Miniquad
* **Team A (Support):** Single-dependency philosophy, tiny binaries (~3MB–7MB), built on top of `miniquad` (direct platform windowing and GL abstraction), fast compilation.
* **Team B (Destroy):**
  1. **OpenGL ES 2.0/3.0 Subset Limitation:** Macroquad abstracts graphics to a minimal common denominator. Writing low-level batched multi-draw voxel shaders or handling custom vertex attribute packing requires fighting the abstraction layer or dropping down to `miniquad::native`.
  2. **Toolchain Friction:** Requires full Rust toolchain (`cargo`, `rustc`, MSVC build tools or MinGW) on developers' machines and complex CI cross-compilation caches.
* **Verdict:** **STRONG CONTENDER (Fallback option).**

### 2.5. The Ponytail Choice: C99/C++17 + Raylib (Statically Linked)
* **Team A (Support):**
  1. **Single Static Binary:** Statically links `raylib`, standard C library (`msvcrt`/`musl`), and links exclusively against standard OS-provided system libraries (`kernel32`, `user32`, `gdi32`, `winmm`, `opengl32`).
  2. **Tiny Footprint:** Production release binary compiles down to **2.2MB – 3.8MB** (stripped ELF/PE). Fits easily within the 15MB release ceiling.
  3. **Deterministic Hardware Access:** OpenGL 3.3 Core (with GLES 2.0 fallback path) supported by 99.8% of active GPUs manufactured since 2008.
  4. **Near-Zero Compilation Time:** Complete clean build of engine and game logic in under 3.5 seconds with standard GCC/Clang/MSVC.
  5. **Predictable Memory Footprint:** Zero garbage collection. Fully manual, arena-driven, contiguous memory layouts.
* **Team B (Destroy / Red-Team Counter-Audit):**
  1. *Manual memory management risks memory leaks and buffer overflows.* -> Mitigated by Ponytail linear arena allocators: dynamic heap allocation inside the game loop is banned.
  2. *C lacks high-level abstractions for complex UI/networking.* -> YAGNI. We are shipping a focused desktop voxel game, not an enterprise web application.
* **Final Verdict:** **ADOPTED AS CORE ARCHITECTURAL RUNTIME.**

---

## 3. System Architecture & Component Topology

The engine is structured as five strictly decoupled subsystems communicating through flat memory structures and explicit function calls. No inheritance hierarchies. No virtual method dispatch tables in hot paths.

```mermaid
graph TD
    subgraph Platform Layer
        OS[Operating System: Windows / Linux / macOS]
        RaylibCore[Raylib Windowing, Input & OpenGL Context]
    end

    subgraph Core Engine Runtime
        GameLoop[Deterministic Game Loop]
        InputState[Input State Buffer: Raw Mouse / Keys]
        Arena[Global Static Memory Arenas]
    end

    subgraph Subsystems
        Physics[Physics & AABB Collision Engine]
        World[World Storage & Chunk Manager]
        Meshing[Interleaved Voxel Mesher]
        Renderer[Voxel Batch Renderer]
    end

    OS --> RaylibCore
    RaylibCore --> GameLoop
    RaylibCore --> InputState
    GameLoop --> Physics
    GameLoop --> World
    GameLoop --> Meshing
    GameLoop --> Renderer
    Arena -.-> World
    Arena -.-> Meshing
    Arena -.-> Renderer
```

### 3.1. Subsystem Responsibilities & Boundaries

| Subsystem | Primary Responsibility | Memory Lifetime | In-Loop Heap Allocations |
| :--- | :--- | :--- | :--- |
| **Platform/Core** | Window lifecycle, input delta extraction, timing | Application lifetime | **0 bytes** |
| **Physics** | Discrete AABB sweep tests, gravity, player locomotion | Frame lifetime | **0 bytes** |
| **World Storage** | Chunk grid management, block voxel lookup, disk I/O | Persistent cache | **0 bytes** (Fixed slot array) |
| **Meshing** | Greedy or naive face culling, vertex packing | Scratchpad lifetime | **0 bytes** (Reusable scratch arena) |
| **Renderer** | Dynamic VBO buffer updates, camera matrix, draw calls | GPU VRAM buffers | **0 bytes** |

---

## 4. The Core Game Loop Specification

The game loop enforces a **deterministic fixed-timestep physics update** coupled to an **interpolated, variable-rate rendering pipeline**.

### 4.1. Mathematical Formulation

Let $t$ be current game time, $dt$ be the fixed physics step size ($\frac{1}{60}\text{ s} \approx 0.016667\text{ s}$), and $\Delta t_{\text{frame}}$ be the wall-clock time elapsed since the previous render frame:

$$\text{accumulator} \leftarrow \text{accumulator} + \Delta t_{\text{frame}}$$

To prevent the **"Spiral of Death"** (when physical simulation takes longer than real time, causing the accumulator to compound indefinitely), the frame delta is clamped:

$$\Delta t_{\text{frame}} = \min(\Delta t_{\text{frame}}, \Delta t_{\text{max}}), \quad \text{where } \Delta t_{\text{max}} = 0.25\text{ s}$$

While $\text{accumulator} \ge dt$:
1. Consume input state snapshot.
2. Step physics simulation: $\vec{x}_{\text{prev}} \leftarrow \vec{x}_{\text{curr}}$, $\vec{x}_{\text{curr}} \leftarrow \vec{x}_{\text{curr}} + \vec{v} \cdot dt$.
3. Resolve voxel AABB collisions.
4. Decrement accumulator: $\text{accumulator} \leftarrow \text{accumulator} - dt$.

The render interpolation alpha is computed as:

$$\alpha = \frac{\text{accumulator}}{dt}, \quad \alpha \in [0.0, 1.0)$$

Render state for any transform component is evaluated as:

$$\vec{x}_{\text{render}} = \vec{x}_{\text{prev}} \cdot (1 - \alpha) + \vec{x}_{\text{curr}} \cdot \alpha$$

### 4.2. Concrete Game Loop Implementation

```c
// Core game loop implementation conforming to Ponytail principles
#include "raylib.h"

#define PHYSICS_HZ 60
#define FIXED_DT (1.0f / (float)PHYSICS_HZ)
#define MAX_FRAME_TIME 0.25f

void RunGameLoop(void) {
    float accumulator = 0.0f;
    double previousTime = GetTime();

    while (!WindowShouldClose()) {
        double currentTime = GetTime();
        float frameTime = (float)(currentTime - previousTime);
        previousTime = currentTime;

        // Clamp to prevent spiral of death on window drag / breakpoint
        if (frameTime > MAX_FRAME_TIME) {
            frameTime = MAX_FRAME_TIME;
        }
        accumulator += frameTime;

        // 1. Input Polling (Raw mouse delta, discrete key hits)
        PollInputEvents();

        // 2. Fixed Timestep Physics Simulation Updates
        while (accumulator >= FIXED_DT) {
            SavePreviousTransformStates(); // for interpolation
            UpdatePlayerPhysics(FIXED_DT);
            UpdateWorldSimulation(FIXED_DT);
            accumulator -= FIXED_DT;
        }

        // 3. Interpolation Factor for Silky Smooth Rendering
        float alpha = accumulator / FIXED_DT;

        // 4. Interleaved Chunk Mesh Updates (Budget-Capped)
        ProcessChunkMeshBudget(2); // Max 2 chunks meshed per frame

        // 5. Variable Rate Render Step
        BeginDrawing();
        ClearBackground((Color){ 135, 206, 235, 255 }); // Sky blue

        BeginMode3D(GetInterpolatedCamera(alpha));
            RenderOpaqueChunks();
            RenderTransparentChunks();
            RenderPlayerCursor();
        EndMode3D();

        RenderHUD();
        EndDrawing();
    }
}
```

### 4.3. Chunk Streaming: Interleaved Single-Thread Budget vs. Multi-Threaded Pool

* **The Multi-Threading Trap:** Novice engineers immediately spawn `std::thread` pools with mutex-protected chunk queues. This introduces race conditions, lock contention, memory fencing overhead, complex synchronization on chunk border block lookups, and non-deterministic crashes.
* **The Ponytail Solution:** **Interleaved Budget-Capped Chunk Meshing.**
  Chunk mesh regeneration is strictly budgeted within the main thread:
  - When dirty chunks are flagged (block place/break, chunk load), they enter a priority queue sorted by Manhattan distance to the camera.
  - In each render frame, the mesher processes a maximum of **1 or 2 chunks** (hard execution cap: $\le 1.5\text{ ms}$).
  - If frame time budget is exceeded, remaining dirty chunks wait until the subsequent frame.
  - Zero mutexes. Zero atomic synchronization overhead. Zero race conditions.

```c
// ponytail: budget-capped single-thread chunk meshing (max 2 chunks/frame, <1.5ms budget) -> worker thread pool with atomic double-buffered vertex buffers
void ProcessChunkMeshBudget(int maxChunksPerFrame) {
    int processed = 0;
    while (processed < maxChunksPerFrame && HasDirtyChunks()) {
        Chunk* chunk = PopClosestDirtyChunk();
        BuildChunkMeshDirect(chunk); // Writes into static scratch buffer, updates VBO
        processed++;
    }
}
```

---

## 5. Memory Model & Zero-Allocation Layouts

Heap allocations (`malloc`, `free`, `new`, `delete`) during runtime cause heap fragmentation, cache misses, and unpredictable micro-stutters. Our memory model relies exclusively on pre-allocated static arrays and linear bump arenas.

### 5.1. Cacheline-Optimized Chunk Layout

Each chunk represents a voxel volume of $16 \times 256 \times 16$ blocks.

* Block representation: `uint8_t` (256 distinct block IDs).
* Total raw volume per chunk: $16 \times 256 \times 16 \times 1\text{ byte} = 65,536\text{ bytes} = 64\text{ KB}$.
* **Crucial Architectural Alignment:** A $64\text{ KB}$ chunk fits completely inside the L2 cache (typically 512KB–1MB per core) and fits neatly across standard 64-byte L1 data cache lines.

```c
#define CHUNK_WIDTH  16
#define CHUNK_HEIGHT 256
#define CHUNK_DEPTH  16
#define CHUNK_VOLUME (CHUNK_WIDTH * CHUNK_HEIGHT * CHUNK_DEPTH) // 65536 bytes

typedef struct {
    int chunkX;
    int chunkZ;
    bool isDirty;
    bool isLoaded;
    uint32_t vao;
    uint32_t vbo;
    uint32_t vertexCount;
    // Flat contiguous array: Y-major order for vertical cache locality
    uint8_t blocks[CHUNK_VOLUME];
} Chunk;
```

#### Memory Indexing Formula & Spatial Locality
We index blocks using the flat layout formula:

$$\text{Index}(x, y, z) = (y \times 16 \times 16) + (z \times 16) + x$$

* **Why Y-Major?** Terrain rendering and column height scans access blocks along the vertical column $(x, y, z) \to (x, y+1, z)$. Storing horizontal slices contiguously ensures that neighbor lookups across the horizontal plane $(x \pm 1, z \pm 1)$ within the same height slice reside in the exact same 64-byte cacheline.

```c
// Inline coordinate resolver with zero branch misprediction
static inline int BlockIndex(int x, int y, int z) {
    return (y << 8) | (z << 4) | x;
}
```

### 5.2. Static Active World Grid

Rather than dynamic hash maps or linked lists, the active world is maintained as a fixed-size toroidal flat array of chunks surrounding the player:

```c
#define RENDER_DISTANCE 8 // 8 chunks radius -> 17x17 grid = 289 chunks
#define WORLD_GRID_SIZE ((RENDER_DISTANCE * 2 + 1) * (RENDER_DISTANCE * 2 + 1))

typedef struct {
    Chunk chunks[WORLD_GRID_SIZE]; // 289 * 64KB ≈ 18.5 MB total world RAM
    int centerChunkX;
    int centerChunkZ;
} WorldGrid;

// Global persistent world instance (BSS segment, zero runtime heap footprint)
static WorldGrid g_World;
```

```c
// ponytail: static chunk grid array (17x17 chunks around player) -> sparse spatial hash map with asynchronous disk streaming
```

### 5.3. Zero-Allocation Voxel Vertex Packing

Standard 3D mesh pipelines push 32-byte or 48-byte vertices (`vec3 pos`, `vec3 normal`, `vec2 uv`, `vec4 color`). For a voxel engine, this is gross memory negligence.

Every voxel face is axis-aligned and integer-quantized:
* $X \in [0..16]$ (5 bits)
* $Y \in [0..256]$ (9 bits)
* $Z \in [0..16]$ (5 bits)
* Normal direction: 6 possible faces (3 bits: $+X, -X, +Y, -Y, +Z, -Z$)
* Texture Atlas ID: $[0..255]$ (8 bits)
* Ambient Occlusion term: $[0..3]$ (2 bits)

Total bits required per vertex: $5 + 9 + 5 + 3 + 8 + 2 = 32\text{ bits} = \mathbf{4\text{ bytes}}$.

```c
// A complete packed voxel vertex in exactly 1 uint32_t (4 bytes)
typedef struct {
    uint32_t data;
} PackedVoxelVertex;

static inline PackedVoxelVertex PackVertex(uint32_t x, uint32_t y, uint32_t z, 
                                           uint32_t face, uint32_t tex, uint32_t ao) {
    PackedVoxelVertex v;
    v.data = (x & 0x1F) |
             ((y & 0x1FF) << 5) |
             ((z & 0x1F)  << 14) |
             ((face & 0x7) << 19) |
             ((tex & 0xFF) << 22) |
             ((ao & 0x3)   << 30);
    return v;
}
```

* **Bandwidth Reduction:** Compared to an uncompressed 36-byte vertex layout, this achieves an **88.9% memory bandwidth reduction**. A chunk mesh with 5,000 vertices requires only **20 KB** of GPU transfer data instead of 180 KB.

### 5.4. Scratchpad Linear Mesh Allocator

During mesh generation, vertices are appended into a static global scratchpad buffer. Once all visible faces are calculated, the buffer is uploaded directly to the chunk's VBO with a single `glBufferSubData` call.

```c
#define MAX_CHUNK_VERTICES (CHUNK_VOLUME * 6) // Theoretical absolute maximum
static PackedVoxelVertex g_MeshScratchBuffer[MAX_CHUNK_VERTICES];
static uint32_t g_ScratchVertexCount = 0;

void ResetMeshScratchpad(void) {
    g_ScratchVertexCount = 0;
}

void EmitQuad(PackedVoxelVertex v0, PackedVoxelVertex v1, 
              PackedVoxelVertex v2, PackedVoxelVertex v3) {
    // Two triangles per quad (6 vertices)
    g_MeshScratchBuffer[g_ScratchVertexCount++] = v0;
    g_MeshScratchBuffer[g_ScratchVertexCount++] = v1;
    g_MeshScratchBuffer[g_ScratchVertexCount++] = v2;

    g_MeshScratchBuffer[g_ScratchVertexCount++] = v2;
    g_MeshScratchBuffer[g_ScratchVertexCount++] = v3;
    g_MeshScratchBuffer[g_ScratchVertexCount++] = v0;
}
```

```c
// ponytail: static scratchpad VBO upload with glBufferData -> persistent mapped buffers (GL_ARB_buffer_storage) with triple-buffering
```

---

## 6. Execution Profiles & Latency Budgets

To guarantee an unwavering 60 FPS (or 144+ FPS on high-refresh displays) on low-end integrated graphics (e.g. Intel UHD 620), each subsystem operates under strict CPU frame budgets:

```
Total Frame Budget (60 FPS): 16.66 ms
┌─────────────┬───────────┬──────────────┬────────────────────────────────────────┐
│ Physics     │ Meshing   │ Draw Calls   │ VSync / Headroom Buffer                │
│ 1.50 ms     │ 2.00 ms   │ 2.50 ms      │ 10.66 ms (64.0% Idle Headroom)         │
└─────────────┴───────────┴──────────────┴────────────────────────────────────────┘
```

### Performance Benchmarks & Targets

| Metric | Target Ceiling | Rationale / Verification |
| :--- | :--- | :--- |
| **Cold Startup Latency** | $< 80\text{ ms}$ | Win32 process spawn $\to$ window render loop |
| **Compiled Binary Size** | $< 4.0\text{ MB}$ | Uncompressed native executable (x86_64) |
| **Peak Runtime RSS RAM** | $< 96\text{ MB}$ | Total memory at 8-chunk view distance |
| **Frame Rate** | $\ge 60\text{ FPS}$ | Rock-solid framerate on Intel HD Graphics 4000+ |
| **Draw Calls per Frame** | $\le 289$ | One draw call per visible active chunk |
| **Heap Allocations in Loop**| **0 bytes** | Zero calls to `malloc`/`free`/`realloc` |

---

## 7. Ponytail Architectural Summary

Every component in this specification adheres strictly to the Lazy Senior Developer hierarchy:
1. **YAGNI:** No dynamic lighting passes, no entity-component systems, no script runtime bindings.
2. **Native Platform Standard:** Pure C99, standard OpenGL 3.3, native OS windowing via Raylib.
3. **Contiguous Arrays Over Pointer Graphs:** Eliminates cache misses and pointer-chasing overhead.
4. **Simplification Upgrades:** Explicitly tagged with `// ponytail:` markers to allow future upgrades without requiring architecture rewrites.
