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

/* Canonical reach limits from docs/06 §3 and docs/02 §5.1 */
#define RAYCAST_REACH_CREATIVE 5.0f /* Maximum reach in Creative mode (5.0m) */
#define RAYCAST_REACH_SURVIVAL 4.5f /* Maximum reach in Survival mode (4.5m) */

/* Maximum DDA steps to prevent runaway loops under extreme inputs */
#define RAYCAST_MAX_STEPS      64

/* Targeting mode bitmask flags */
typedef enum RaycastFlags {
    RAYCAST_FLAG_NONE       = 0,
    RAYCAST_FLAG_LIQUIDS    = (1 << 0), /* Intersect liquid blocks (e.g. WATER) for bucket pickup */
    RAYCAST_FLAG_VEGETATION = (1 << 1)  /* Intersect non-solid vegetation (FLOWER, TALLGRASS) for harvesting */
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
    uint8_t blockId;       /* Canonical block palette ID of the struck voxel (BLOCK_AIR on miss) */
} RaycastResult;

/* Callback predicate function for custom or unit-test voxel grid evaluation */
typedef bool (*RaycastVoxelPredicate)(int x, int y, int z, void* userData);

/* ========================================================================= */
/* 4. Public API Declarations                                                */
/* ========================================================================= */

/**
 * Pure mathematical Amanatides-Woo Fast Voxel Traversal (DDA).
 *
 * Steps through every discrete 3D lattice cell intersected by the continuous ray.
 * Zero heap allocation. Guarantees entered face normal invariant: n = -step_i * e_i.
 *
 * @param origin        Ray camera eye position in continuous world space.
 * @param dir           Normalized view look direction vector.
 * @param maxReach      Maximum interaction envelope (e.g. 5.0f Creative, 4.5f Survival).
 * @param isSolidVoxel  Predicate callback returning true if voxel at (x,y,z) is an obstacle.
 * @param userData      Opaque pointer forwarded to predicate callback.
 * @return              RaycastResult containing hit status, target/place coordinates, and face normal.
 */
RaycastResult Raycast_Traverse(
    Vec3 origin,
    Vec3 dir,
    float maxReach,
    RaycastVoxelPredicate isSolidVoxel,
    void* userData
);

/**
 * High-level engine raycast querying active world voxels via World_GetBlock().
 *
 * Automatically checks chunk bounds, air, liquids, vegetation, and solid blocks.
 *
 * @param eyePos        Player camera eye position (P_feet + (0, 1.62, 0)).
 * @param lookDir       Normalized camera forward vector.
 * @param maxReach      Interaction distance limit (5.0f Creative, 4.5f Survival).
 * @param flags         Bitwise combination of RaycastFlags (liquids, vegetation).
 * @return              RaycastResult with populated targetBlock, placeBlock, faceNormal, and blockId.
 */
RaycastResult Raycast_World(
    Vec3 eyePos,
    Vec3 lookDir,
    float maxReach,
    uint32_t flags
);

/**
 * Validates block placement invariant against player AABB, chunk height, and cell occupancy.
 *
 * Adheres strictly to docs/02 §5.3 Anti-Suffocation Validation:
 * 1. World height boundary check: 0 <= placePos.y < 256
 * 2. Occupancy check: cell must be empty (Air or replaceable fluid)
 * 3. Player self-intersection check: AABB_block does NOT overlap player AABB
 *
 * @param hit           Completed raycast result from Raycast_World().
 * @param playerAABB    Current player bounding box (standing 1.8m or sneaking 1.5m).
 * @param outPlacePos   Optional pointer receiving the validated placement position.
 * @return              True if placement is permissible, false if rejected.
 */
bool Raycast_ValidatePlacement(
    const RaycastResult* hit,
    const AABB* playerAABB,
    Vec3i* outPlacePos
);

#ifdef __cplusplus
}
#endif

#endif /* MINECRAFT_GAMEPLAY_RAYCAST_H */
