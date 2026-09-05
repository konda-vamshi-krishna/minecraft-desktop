#include "raycast.h"
#include <string.h>

// ponytail: [Direct DDA loop] -> [SIMD 4-ray packet traversal if particle/shadow raycasting added]
// ponytail: [Synchronous placement validation] -> [Multiplayer speculative prediction buffer]

/* ========================================================================= */
/* 1. Pure Mathematical Amanatides-Woo Fast Voxel Traversal (DDA)           */
/* ========================================================================= */

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
        return result; /* Miss: degenerate direction vector */
    }

    float invLen = 1.0f / sqrtf(lenSq);
    float dx = dir.x * invLen;
    float dy = dir.y * invLen;
    float dz = dir.z * invLen;

    /* 2. Initial integer voxel coordinates (strictly floored for negative coordinates) */
    int x = FloorToInt(origin.x);
    int y = FloorToInt(origin.y);
    int z = FloorToInt(origin.z);

    /* 3. Immediate inside-solid-block check (docs/02 §3.2, distance = 0.0, normal = (0, 1, 0)) */
    if (isSolidVoxel(x, y, z, userData)) {
        result.hit = true;
        result.targetBlock = Vec3i_Create(x, y, z);
        result.faceNormal  = Vec3i_Create(0, 1, 0); /* Canonical top-face fallback */
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
        /* Advance along the axis with the minimal distance to the next boundary */
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

        /* Reach envelope boundary check */
        if (currentT > maxReach) {
            break;
        }

        /* Test candidate voxel */
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

/* ========================================================================= */
/* 2. World Subsystem Interfacing                                            */
/* ========================================================================= */

typedef struct WorldRaycastContext {
    uint32_t flags;
} WorldRaycastContext;

static bool WorldVoxelPredicate(int x, int y, int z, void* userData) {
    const WorldRaycastContext* ctx = (const WorldRaycastContext*)userData;

    /* Out-of-bounds voxels (sky or void) are non-solid air */
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

/* ========================================================================= */
/* 3. Placement Anti-Suffocation Validation                                  */
/* ========================================================================= */

bool Raycast_ValidatePlacement(
    const RaycastResult* hit,
    const AABB* playerAABB,
    Vec3i* outPlacePos
) {
    if (!hit || !hit->hit) {
        return false;
    }

    Vec3i placePos = hit->placeBlock;

    /* 1. World vertical height bounds [0, 255] (docs/02 §5.3, docs/06 §2.1) */
    if (placePos.y < 0 || placePos.y >= CHUNK_HEIGHT) {
        return false;
    }

    /* 2. Target cell must be empty (Air or replaceable fluid) */
    uint8_t currentId = World_GetBlock(placePos.x, placePos.y, placePos.z);
    if (currentId != BLOCK_AIR && !Block_IsLiquid(currentId)) {
        return false;
    }

    /* 3. Anti-suffocation self-intersection invariant: */
    /* Proposed block AABB [placePos, placePos + 1.0] must NOT intersect player AABB */
    if (playerAABB) {
        AABB blockAABB;
        blockAABB.minX = (float)placePos.x;
        blockAABB.minY = (float)placePos.y;
        blockAABB.minZ = (float)placePos.z;
        blockAABB.maxX = (float)placePos.x + 1.0f;
        blockAABB.maxY = (float)placePos.y + 1.0f;
        blockAABB.maxZ = (float)placePos.z + 1.0f;

        if (AABB_Intersects(playerAABB, &blockAABB)) {
            return false; /* Rejected: placement overlaps player bounding box */
        }
    }

    if (outPlacePos) {
        *outPlacePos = placePos;
    }
    return true;
}
