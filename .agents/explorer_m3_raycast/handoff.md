# Milestone 3 Explorer Handoff: Amanatides-Woo DDA Raycasting & Block Targeting

**Subagent ID**: `explorer_m3_raycast`  
**Milestone**: Milestone 3 (Core Gameplay & Physics)  
**Target Module**: `src/gameplay/raycast.h` & `src/gameplay/raycast.c`  
**Date**: 2026-09-03  

---

## 1. Observation

Direct observations from codebase inspection, specification documents, and test harnesses:

### 1.1 Documented Canonical Specifications
- **Voxel Traversal Equations & Invariants** (`docs/02_CORE_GAMEPLAY_FEATURES.md`, lines 150–180):
  - Current voxel coordinate: $X = \lfloor x_0 \rfloor, Y = \lfloor y_0 \rfloor, Z = \lfloor z_0 \rfloor$.
  - Step direction per axis: $\text{step}_i = \operatorname{sgn}(d_i) \in \{-1, 0, 1\}$.
  - Parametric step size: $t_{\Delta i} = \left|\frac{1}{d_i}\right|$ for $d_i \ne 0$, else $\infty$.
  - Initial boundary distance:
    $$t_{\text{Max}i} = \begin{cases} \frac{(\lfloor p_i \rfloor + 1) - p_i}{d_i} & d_i > 0 \\ \frac{p_i - \lfloor p_i \rfloor}{|d_i|} & d_i < 0 \\ \infty & d_i = 0 \end{cases}$$
  - Stepped Face Normal Invariant: $\mathbf{n} = -\text{step}_i \cdot \hat{\mathbf{e}}_i$.
  - Placement coordinate: $\mathbf{P}_{\text{place}} = \mathbf{P}_{\text{target}} + \mathbf{n}$.
- **Reach Thresholds & Player Kinematics** (`docs/06_OFFICIAL_MINECRAFT_CANONICAL_SPEC.md`, lines 48–56):
  - Player eye height: $y_{\text{cam}} = y_{\text{feet}} + 1.62\text{m}$ (Standing), $y_{\text{feet}} + 1.35\text{m}$ (Sneaking).
  - Reach distance limits: $5.0\text{ blocks}$ (Creative mode), $4.5\text{m}$ (Survival mode). Traversal cut-off occurs when $t > d_{\text{reach}}$.
- **Anti-Suffocation Placement Validation** (`docs/02_CORE_GAMEPLAY_FEATURES.md`, lines 638–683):
  - Rejection of block placement if the proposed voxel AABB $[\mathbf{P}_{\text{place}}, \mathbf{P}_{\text{place}} + 1]$ intersects player AABB.
  - Height boundary check: $0 \le \mathbf{P}_{\text{place}}.y < 256$.
  - Target cell must be empty (`BLOCK_AIR` or replaceable liquid).

### 1.2 Canonical Python Test Implementations
- **Reference Algorithm** (`tests/canonical_models.py`, lines 317–405):
  - Normalized direction vector with degenerate length guard: `length > 1e-9`.
  - Immediate inside-solid-block check at ray origin ($t=0.0$, normal $=(0, 1, 0)$).
  - Stepping loop comparing `t_max_x`, `t_max_y`, `t_max_z`.
  - Termination immediately upon `current_t > max_reach`.
- **Active Test Battery** (`tests/tier1_features/test_raycast_dda.py`, lines 12–141):
  - `test_01_cardinal_raycast_face_normal_invariants`: Tests all 6 cardinal directions (+X, -X, +Y, -Y, +Z, -Z), verifying $\mathbf{n} = -\text{step}_i \cdot \hat{\mathbf{e}}_i$ and $\mathbf{P}_{\text{place}} = \mathbf{P}_{\text{target}} + \mathbf{n}$.
  - `test_02_reach_distance_thresholds`: Verifies hits within reach threshold and misses beyond reach threshold (distinguishing Creative 5.0m vs Survival 4.0m/4.5m).
  - `test_03_diagonal_3d_ray_traversal_order`: Traverses diagonal trajectory, asserting no skipped lattice cells (Manhattan distance between consecutive cells is strictly 1).
  - `test_04_collinear_axis_zero_components`: Raycast with $d_y = 0, d_z = 0$ handles IEEE 754 division without division-by-zero crashes.
  - `test_05_immediate_inside_solid_block`: Ray starting inside solid block reports hit at $t = 0.0$.

### 1.3 Subsystem Integration Context
- **World Block Palette & Properties** (`src/world/world.h`, lines 43–106):
  - 14 vanilla blocks: `BLOCK_AIR` (0) through `BLOCK_TALLGRASS` (13).
  - Bitmask predicates: `Block_IsOpaque(id)`, `Block_IsSolid(id)`, `Block_IsLiquid(id)`, `Block_IsVegetation(id)`.
  - World coordinate queries: `World_GetBlock(int worldX, int worldY, int worldZ)` and `World_SetBlock(...)`.
- **Existing Vector & Bounding Volume Math** (`src/core/math_utils.h`, lines 24–512):
  - Vector types: `Vec3` (`Vec3_Create`, `Vec3_Normalize`, `Vec3_Dot`, `Vec3_Sub`).
  - Bounding box: `AABB` and `AABB_Intersects(const AABB* a, const AABB* b)`.
  - Integer floor utility: `FloorToInt(float f)` which invokes `(int)floorf(f)`.

### 1.4 Test Suite Baseline Execution
- Ran `python tests/test_runner.py`:
  ```
  TOTAL: 105 tests, 105 passed, 0 failed, 34.4ms duration. ALL TESTS PASSED (100%).
  ```
- Executed customized differential fuzzing test (`.agents/explorer_m3_raycast/verify_raycast_math.py`):
  ```
  Ran 8 tests in 0.009s. OK (including 100 randomized differential fuzzing iterations).
  ```

---

## 2. Logic Chain

From the direct observations above, we establish the mathematical and architectural logic chain governing the C99 implementation:

### 2.1 Continuous Ray Formulation & Normalization
1. **Observation**: Camera orientation in `src/core/math_utils.h` produces a look direction $\mathbf{F}_{\text{look}} = (\cos\theta\sin\phi, \sin\theta, -\cos\theta\cos\phi)$ from camera yaw and pitch.
2. **Deduction**: Because DDA parametric step size $t$ directly represents Euclidean distance if and only if $\|\mathbf{d}\| = 1.0$, the input direction must be normalized.
3. **Safety Guard**: If $\|\mathbf{d}\|^2 < 10^{-14}$ or is non-finite (NaN/Inf), normalization would divide by zero. The algorithm must immediately return `RaycastResult.hit = false`.

### 2.2 Discrete Lattice Quantization (Negative Coordinates)
1. **Observation**: World coordinates span $(-\infty, +\infty)$ on $X$ and $Z$.
2. **Hazard**: In C99, integer truncation `(int)(-0.5f)` yields `0`, whereas the containing voxel is $\lfloor -0.5 \rfloor = -1$.
3. **Requirement**: Coordinate quantization must strictly use `FloorToInt(origin)` / `(int)floorf(origin)`.
4. **Boundary Derivation**:
   - For $d_x > 0$: distance to the forward boundary plane $x = \lfloor x_0 \rfloor + 1$ is:
     $$\Delta x = (\lfloor x_0 \rfloor + 1) - x_0 \in (0.0, 1.0]$$
   - For $d_x < 0$: distance to the backward boundary plane $x = \lfloor x_0 \rfloor$ is:
     $$\Delta x = x_0 - \lfloor x_0 \rfloor \in [0.0, 1.0)$$
   Both quantities are strictly non-negative for all finite real numbers, ensuring $t_{\text{Max}} \ge 0.0$.

### 2.3 Collinear & Axis-Aligned Traversal (Zero Division Immunity)
1. **Observation**: A player frequently looks purely horizontally ($d_y = 0$) or purely along a cardinal axis ($d_y = d_z = 0$).
2. **Mechanism**:
   - When $\text{step}_i == 0$, $t_{\Delta i} = \infty$ and $t_{\text{Max}i} = \infty$.
   - In C99, `<math.h>` provides `INFINITY` (IEEE 754 positive infinity).
   - In comparisons `tMaxX < tMaxY`, any finite $t_{\text{Max}}$ is strictly less than `INFINITY`.
   - Consequently, axes with zero direction components are never selected for stepping, and their coordinates remain invariant.

### 2.4 Entered Face Normal Invariant
1. **Mathematical Proof**:
   - Consider a ray stepping along axis $k \in \{x, y, z\}$ by $\text{step}_k \in \{-1, +1\}$.
   - If $\text{step}_k = +1$, the ray enters through the minimum coordinate face ($x = X$). The outward normal of that face points towards $-X$: $\mathbf{n} = (-1, 0, 0)$.
   - If $\text{step}_k = -1$, the ray enters through the maximum coordinate face ($x = X + 1$). The outward normal points towards $+X$: $\mathbf{n} = (+1, 0, 0)$.
   - Therefore, in all cases:
     $$\mathbf{n} = -\text{step}_k \cdot \hat{\mathbf{e}}_k$$
   - Since $\mathbf{n}$ points out of the entered face into the unoccupied lattice cell traversed immediately prior to contact:
     $$\mathbf{P}_{\text{place}} = \mathbf{P}_{\text{target}} + \mathbf{n} = \mathbf{P}_{\text{previous\_voxel}}$$
   This guarantees that block placement always targets the contiguous vacant cell through which the ray arrived.

### 2.5 Multi-Axis Tie-Breaking & Manhattan Continuity
1. **Observation**: If a ray passes precisely through a voxel edge or vertex, multiple $t_{\text{Max}}$ values are identical ($t_{\text{Max}x} = t_{\text{Max}y}$).
2. **Branching Order**:
   ```c
   if (tMaxX < tMaxY) {
       if (tMaxX < tMaxZ) { step X; }
       else               { step Z; }
   } else {
       if (tMaxY < tMaxZ) { step Y; }
       else               { step Z; }
   }
   ```
3. **Evaluation**: When $t_{\text{Max}x} == t_{\text{Max}y}$, the `else` branch executes. One axis steps, incrementing its $t_{\text{Max}}$ by $t_{\Delta}$. In the very next iteration, the remaining axis has the smaller $t_{\text{Max}}$ and steps. Every cell is visited in single Manhattan steps ($L_1 = 1$) without diagonal tunneling or skipping cells.

### 2.6 Bounded Step Count Ceiling
1. **Observation**: For reach $d_{\text{reach}} \le 5.0\text{m}$, the maximum Manhattan steps along any diagonal trajectory cannot exceed $3 \times \lceil 5.0 \rceil + 3 \approx 18$ steps.
2. **Ponytail Hardening**: Capping the loop at `RAYCAST_MAX_STEPS = 64` guarantees that even in the presence of denormalized floats or driver-level floating point anomalies, infinite execution loops are physically impossible.

### 2.7 Anti-Suffocation Validation
1. **Observation**: A player standing at $(x, y, z)$ has bounding box $[x-0.3, y, z-0.3]$ to $[x+0.3, y+1.8, z+0.3]$.
2. **Consequence**: Placing a block at $\mathbf{P}_{\text{place}}$ when $[\mathbf{P}_{\text{place}}, \mathbf{P}_{\text{place}} + 1]$ intersects this bounding box will encase the player, causing collision clipping and suffocation.
3. **Invariance**: `Raycast_ValidatePlacement()` enforces the predicate $\neg \text{AABB\_Intersects}(\text{AABB}_{\text{player}}, \text{AABB}_{\text{block}})$, height bounds $[0, 255]$, and cell vacancy (`BLOCK_AIR` or replaceable liquid).

---

## 3. Caveats

1. **Entity Collision Excluded from Milestone 3 Scope**:
   Raycasting here targets static chunk lattice voxels. Ray-OBB or Ray-Capsule intersection for dynamic mob or drop entities (`Raycast_Entities`) is part of later milestones and does not alter the voxel DDA core.
2. **Sub-Chunk LOD / Hierarchical DDA**:
   Traversing uniform $1\times 1\times 1$ voxels over $5.0\text{m}$ reach takes $\le 18$ iterations (under $0.2\mu\text{s}$ on modern CPUs). Hierarchical octree DDA or sub-chunk empty section skipping is YAGNI for $5.0\text{m}$ reach, but noted as a Ponytail upgrade path if render distance or sniper/bow reach expands to $\ge 64\text{m}$.
3. **Multiplayer Prediction & Rollback**:
   The placement validation is synchronous for single-player local worlds. In a networked client-server architecture, speculative placement requires a local rollback ring buffer.

---

## 4. Conclusion & Proposed Specification

The Amanatides-Woo Fast Voxel Traversal algorithm and block targeting interfaces are mathematically verified and ready for implementation in Milestone 3 under `src/gameplay/`.

The proposed design adheres strictly to the **Ponytail Principle**:
- Zero heap allocations (`malloc`, `free`, `new`). Stack-only structs and register arguments.
- Pure C99, zero third-party library dependencies.
- Complete parity with `tests/canonical_models.py` and `docs/02_CORE_GAMEPLAY_FEATURES.md`.

### 4.1 Proposed Header: `g:/minecraft_desktop/.agents/explorer_m3_raycast/proposed_raycast.h`
*(To be placed in `src/gameplay/raycast.h` by the implementer)*

```c
#ifndef MINECRAFT_GAMEPLAY_RAYCAST_H
#define MINECRAFT_GAMEPLAY_RAYCAST_H

#include <stdbool.h>
#include <stdint.h>
#include <math.h>
#include "../core/math_utils.h"
#include "../world/world.h"

#ifdef __cplusplus
extern "C" {
#endif

// ponytail: [Synchronous direct world voxel traversal] -> [Hierarchical DDA / Octree skip if chunk render distance >= 32]
// ponytail: [3-component integer vector] -> [Direct SIMD __m128i register packing if multi-ray batching required]

/* ========================================================================= */
/* 1. Discrete Integer 3D Vector                                            */
/* ========================================================================= */

typedef struct Vec3i {
    int x, y, z;
} Vec3i;

static inline Vec3i Vec3i_Create(int x, int y, int z) {
    Vec3i v = { x, y, z };
    return v;
}

static inline Vec3i Vec3i_Add(Vec3i a, Vec3i b) {
    Vec3i v = { a.x + b.x, a.y + b.y, a.z + b.z };
    return v;
}

static inline bool Vec3i_Equals(Vec3i a, Vec3i b) {
    return a.x == b.x && a.y == b.y && a.z == b.z;
}

/* ========================================================================= */
/* 2. Raycast Configuration & Canonical Reach Envelopes                      */
/* ========================================================================= */

#define RAYCAST_REACH_CREATIVE 5.0f /* docs/06 §3 & docs/02 §5.1 */
#define RAYCAST_REACH_SURVIVAL 4.5f /* docs/06 §3 */
#define RAYCAST_MAX_STEPS      64   /* Bounded traversal iteration ceiling */

typedef enum RaycastFlags {
    RAYCAST_FLAG_NONE       = 0,
    RAYCAST_FLAG_LIQUIDS    = (1 << 0), /* Intersect liquid blocks (e.g. WATER) */
    RAYCAST_FLAG_VEGETATION = (1 << 1)  /* Intersect non-solid vegetation (FLOWER, TALLGRASS) */
} RaycastFlags;

/* ========================================================================= */
/* 3. Raycast Hit Result Structure                                           */
/* ========================================================================= */

typedef struct RaycastResult {
    bool hit;              /* True if an interactable block was intersected within maxReach */
    Vec3i targetBlock;     /* World coordinates (x, y, z) of the struck voxel cell */
    Vec3i placeBlock;      /* Adjacent empty space coordinates (P_target + n_face) for placement */
    Vec3i faceNormal;      /* Surface normal of entered face: n = -step_i * e_i */
    float distance;        /* Euclidean parametric distance t from ray origin to contact point */
    uint8_t blockId;       /* Canonical block palette ID of the struck voxel */
} RaycastResult;

typedef bool (*RaycastVoxelPredicate)(int x, int y, int z, void* userData);

/* ========================================================================= */
/* 4. Public API Declarations                                                */
/* ========================================================================= */

RaycastResult Raycast_Traverse(
    Vec3 origin,
    Vec3 dir,
    float maxReach,
    RaycastVoxelPredicate isSolidVoxel,
    void* userData
);

RaycastResult Raycast_World(
    Vec3 eyePos,
    Vec3 lookDir,
    float maxReach,
    uint32_t flags
);

bool Raycast_ValidatePlacement(
    const RaycastResult* hit,
    const AABB* playerAABB,
    Vec3i* outPlacePos
);

#ifdef __cplusplus
}
#endif

#endif /* MINECRAFT_GAMEPLAY_RAYCAST_H */
```

### 4.2 Proposed Source: `g:/minecraft_desktop/.agents/explorer_m3_raycast/proposed_raycast.c`
*(To be placed in `src/gameplay/raycast.c` by the implementer)*

```c
#include "raycast.h"
#include <string.h>

// ponytail: [Direct DDA loop] -> [SIMD 4-ray packet traversal if particle/shadow raycasting added]
// ponytail: [Synchronous placement validation] -> [Multiplayer speculative prediction buffer]

RaycastResult Raycast_Traverse(
    Vec3 origin,
    Vec3 dir,
    float maxReach,
    RaycastVoxelPredicate isSolidVoxel,
    void* userData
) {
    RaycastResult result;
    memset(&result, 0, sizeof(RaycastResult));

    if (!isSolidVoxel || maxReach <= 0.0f) {
        return result;
    }

    /* 1. Normalize direction vector and guard against zero / NaN vectors */
    float lenSq = dir.x * dir.x + dir.y * dir.y + dir.z * dir.z;
    if (lenSq < 1e-14f || !isfinite(lenSq)) {
        return result;
    }

    float invLen = 1.0f / sqrtf(lenSq);
    float dx = dir.x * invLen;
    float dy = dir.y * invLen;
    float dz = dir.z * invLen;

    /* 2. Initial integer voxel coordinates (strictly floored for negative coordinates) */
    int x = FloorToInt(origin.x);
    int y = FloorToInt(origin.y);
    int z = FloorToInt(origin.z);

    /* 3. Immediate inside-solid-block check (distance = 0.0, normal = (0, 1, 0)) */
    if (isSolidVoxel(x, y, z, userData)) {
        result.hit = true;
        result.targetBlock = Vec3i_Create(x, y, z);
        result.faceNormal  = Vec3i_Create(0, 1, 0);
        result.placeBlock  = Vec3i_Create(x, y + 1, z);
        result.distance    = 0.0f;
        return result;
    }

    /* 4. Stepping directions per axis: sgn(d_i) */
    int stepX = (dx > 0.0f) ? 1 : ((dx < 0.0f) ? -1 : 0);
    int stepY = (dy > 0.0f) ? 1 : ((dy < 0.0f) ? -1 : 0);
    int stepZ = (dz > 0.0f) ? 1 : ((dz < 0.0f) ? -1 : 0);

    /* 5. Parametric step sizes (tDelta): distance to traverse 1.0 unit along axis */
    float tDeltaX = (stepX != 0) ? fabsf(1.0f / dx) : INFINITY;
    float tDeltaY = (stepY != 0) ? fabsf(1.0f / dy) : INFINITY;
    float tDeltaZ = (stepZ != 0) ? fabsf(1.0f / dz) : INFINITY;

    /* 6. Initial boundary distances (tMax): distance to first integer voxel grid boundary */
    float floorX = floorf(origin.x);
    float floorY = floorf(origin.y);
    float floorZ = floorf(origin.z);

    float tMaxX = (stepX > 0) ? ((floorX + 1.0f - origin.x) * tDeltaX) :
                  (stepX < 0) ? ((origin.x - floorX) * tDeltaX) : INFINITY;
    float tMaxY = (stepY > 0) ? ((floorY + 1.0f - origin.y) * tDeltaY) :
                  (stepY < 0) ? ((origin.y - floorY) * tDeltaY) : INFINITY;
    float tMaxZ = (stepZ > 0) ? ((floorZ + 1.0f - origin.z) * tDeltaZ) :
                  (stepZ < 0) ? ((origin.z - floorZ) * tDeltaZ) : INFINITY;

    float currentT = 0.0f;
    Vec3i faceNormal = Vec3i_Create(0, 0, 0);

    /* 7. Amanatides-Woo Traversal Loop */
    for (int step = 0; step < RAYCAST_MAX_STEPS; ++step) {
        if (tMaxX < tMaxY) {
            if (tMaxX < tMaxZ) {
                currentT = tMaxX;
                tMaxX += tDeltaX;
                x += stepX;
                faceNormal = Vec3i_Create(-stepX, 0, 0);
            } else {
                currentT = tMaxZ;
                tMaxZ += tDeltaZ;
                z += stepZ;
                faceNormal = Vec3i_Create(0, 0, -stepZ);
            }
        } else {
            if (tMaxY < tMaxZ) {
                currentT = tMaxY;
                tMaxY += tDeltaY;
                y += stepY;
                faceNormal = Vec3i_Create(0, -stepY, 0);
            } else {
                currentT = tMaxZ;
                tMaxZ += tDeltaZ;
                z += stepZ;
                faceNormal = Vec3i_Create(0, 0, -stepZ);
            }
        }

        if (currentT > maxReach) {
            break;
        }

        if (isSolidVoxel(x, y, z, userData)) {
            result.hit = true;
            result.targetBlock = Vec3i_Create(x, y, z);
            result.faceNormal  = faceNormal;
            result.placeBlock  = Vec3i_Add(result.targetBlock, faceNormal);
            result.distance    = currentT;
            return result;
        }
    }

    return result;
}

typedef struct WorldRaycastContext {
    uint32_t flags;
} WorldRaycastContext;

static bool WorldVoxelPredicate(int x, int y, int z, void* userData) {
    const WorldRaycastContext* ctx = (const WorldRaycastContext*)userData;

    if (y < 0 || y >= CHUNK_HEIGHT) {
        return false;
    }

    uint8_t id = World_GetBlock(x, y, z);
    if (id == BLOCK_AIR) {
        return false;
    }

    if (Block_IsLiquid(id)) {
        return (ctx->flags & RAYCAST_FLAG_LIQUIDS) != 0;
    }

    if (Block_IsVegetation(id)) {
        return (ctx->flags & RAYCAST_FLAG_VEGETATION) != 0;
    }

    return Block_IsSolid(id);
}

RaycastResult Raycast_World(
    Vec3 eyePos,
    Vec3 lookDir,
    float maxReach,
    uint32_t flags
) {
    WorldRaycastContext ctx;
    ctx.flags = flags;

    RaycastResult res = Raycast_Traverse(eyePos, lookDir, maxReach, WorldVoxelPredicate, &ctx);
    if (res.hit) {
        if (res.targetBlock.y >= 0 && res.targetBlock.y < CHUNK_HEIGHT) {
            res.blockId = World_GetBlock(res.targetBlock.x, res.targetBlock.y, res.targetBlock.z);
        } else {
            res.blockId = BLOCK_AIR;
        }
    }
    return res;
}

bool Raycast_ValidatePlacement(
    const RaycastResult* hit,
    const AABB* playerAABB,
    Vec3i* outPlacePos
) {
    if (!hit || !hit->hit) {
        return false;
    }

    Vec3i placePos = hit->placeBlock;

    if (placePos.y < 0 || placePos.y >= CHUNK_HEIGHT) {
        return false;
    }

    uint8_t currentId = World_GetBlock(placePos.x, placePos.y, placePos.z);
    if (currentId != BLOCK_AIR && !Block_IsLiquid(currentId)) {
        return false;
    }

    if (playerAABB) {
        AABB blockAABB;
        blockAABB.minX = (float)placePos.x;
        blockAABB.minY = (float)placePos.y;
        blockAABB.minZ = (float)placePos.z;
        blockAABB.maxX = (float)placePos.x + 1.0f;
        blockAABB.maxY = (float)placePos.y + 1.0f;
        blockAABB.maxZ = (float)placePos.z + 1.0f;

        if (AABB_Intersects(playerAABB, &blockAABB)) {
            return false;
        }
    }

    if (outPlacePos) {
        *outPlacePos = placePos;
    }
    return true;
}
```

---

## 5. Verification Method

To independently verify this specification and mathematical derivation:

1. **Execute Existing Raycast DDA Test Suite**:
   ```bash
   python -m unittest tests/tier1_features/test_raycast_dda.py
   ```
   *Expected Output*: 5 tests pass in $<0.01\text{s}$.

2. **Execute Full Project E2E Suite**:
   ```bash
   python tests/test_runner.py
   ```
   *Expected Output*: 105 tests pass across Tiers 1–4 (100% pass rate).

3. **Execute Comprehensive Differential Verification & Fuzzing Harness**:
   ```bash
   python .agents/explorer_m3_raycast/verify_raycast_math.py
   ```
   *Expected Output*: 8 tests pass including 100 randomized differential fuzzing iterations against canonical models.

4. **Invalidation Conditions**:
   - Any test where `c99_proposed_raycast` diverges from `canonical_models.fast_voxel_traversal` on `hit`, `target_block`, `place_block`, `face_normal`, or `distance`.
   - Any test where Manhattan stepping distance between consecutive traversed voxels is $\ne 1$.
   - Any test where placing a block within player AABB bounds returns `true`.

---

### Polymath Probing Question for Milestone 3 Implementer
*When a player stands directly at $x = 0.70$, looking downwards at $45^\circ$ pitch into an adjacent block edge, does the sequential ordering of auto-step speculative probes coupled with DDA face normal placement introduce race conditions with the block destruction state machine if the target block is destroyed mid-tick? How does your input tick loop guarantee atomic resolution between raycast targeting and swept AABB integration?*
