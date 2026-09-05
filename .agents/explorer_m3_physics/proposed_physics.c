/**
 * @file physics.c
 * @brief Canonical Swept AABB Player Kinematics & Collision Implementation for Milestone 3.
 *
 * Adheres strictly to Ponytail minimal-complexity principles:
 * - Zero dynamic heap allocations (no malloc/calloc/free).
 * - Exact canonical Java kinematics (gravity, terminal velocity, friction, drag, jump).
 * - Axis-decoupled collision invariant: strictly Y -> X -> Z against voxel lattice.
 * - Anti-tunneling sub-stepping for terminal velocity drops.
 * - Speculative auto-step with headspace clearance verification.
 * - Sneak ledge-clamping with downward ground support probe.
 * - Amanatides-Woo Fast Voxel Traversal DDA raycasting.
 */

#include  proposed_physics.h
#include <string.h>

// ponytail: [Synchronous direct array access] -> [Chunk octree / LOD traversal if world height expands]
// ponytail: [Full 1.0m block AABBs] -> [Sub-block / slab / stair custom AABB dispatch table]

/* ========================================================================= */
/* 1. Static Helper Functions & Internal Queries                             */
/* ========================================================================= */

static inline bool DefaultSolidPredicate(int x, int y, int z) {
    if (y < 0 || y >= CHUNK_HEIGHT) return false;
    return Block_IsSolid(World_GetBlock(x, y, z));
}

static inline float FloatMin(float a, float b) {
    return (a < b) ? a : b;
}

static inline float FloatMax(float a, float b) {
    return (a > b) ? a : b;
}

static inline int FloorInt(float f) {
    return (int)floorf(f);
}

/* ========================================================================= */
/* 2. Hitbox & Camera Geometry Resolution                                    */
/* ========================================================================= */

void Physics_InitPlayer(PlayerPhysicsState* player, float x, float y, float z) {
    if (!player) return;
    memset(player, 0, sizeof(PlayerPhysicsState));
    player->x = x;
    player->y = y;
    player->z = z;
    player->prevX = x;
    player->prevY = y;
    player->prevZ = z;
    player->isGrounded = false;
    player->isSneaking = false;
    player->isSprinting = false;
    player->jumpRequested = false;
    Physics_UpdateHitbox(player);
}

AABB Physics_GetAABBAt(float x, float y, float z, bool isSneaking) {
    float height = isSneaking ? PLAYER_HEIGHT_SNEAKING : PLAYER_HEIGHT_STANDING;
    AABB box;
    box.minX = x - PLAYER_HALF_WIDTH;
    box.maxX = x + PLAYER_HALF_WIDTH;
    box.minY = y;
    box.maxY = y + height;
    box.minZ = z - PLAYER_HALF_WIDTH;
    box.maxZ = z + PLAYER_HALF_WIDTH;
    return box;
}

void Physics_UpdateHitbox(PlayerPhysicsState* player) {
    if (!player) return;
    player->hitbox = Physics_GetAABBAt(player->x, player->y, player->z, player->isSneaking);
}

Vec3 Physics_GetEyePosition(const PlayerPhysicsState* player) {
    float eyeOffset = player->isSneaking ? PLAYER_EYE_OFFSET_SNEAKING : PLAYER_EYE_OFFSET_STANDING;
    return Vec3_Create(player->x, player->y + eyeOffset, player->z);
}

Vec3 Physics_GetInterpolatedRenderPosition(const PlayerPhysicsState* player, float alpha) {
    float clampedAlpha = ClampFloat(alpha, 0.0f, 1.0f);
    return Vec3_Create(
        player->prevX + (player->x - player->prevX) * clampedAlpha,
        player->prevY + (player->y - player->prevY) * clampedAlpha,
        player->prevZ + (player->z - player->prevZ) * clampedAlpha
    );
}

Vec3 Physics_GetInterpolatedEyePosition(const PlayerPhysicsState* player, float alpha) {
    Vec3 renderPos = Physics_GetInterpolatedRenderPosition(player, alpha);
    float eyeOffset = player->isSneaking ? PLAYER_EYE_OFFSET_SNEAKING : PLAYER_EYE_OFFSET_STANDING;
    return Vec3_Create(renderPos.x, renderPos.y + eyeOffset, renderPos.z);
}

/* ========================================================================= */
/* 3. Spatial Collision & Ledge Support Probing                              */
/* ========================================================================= */

bool Physics_CheckCollisionEx(const AABB* box, PhysicsSolidQueryFn customSolid) {
    if (!box) return false;
    PhysicsSolidQueryFn isSolid = customSolid ? customSolid : DefaultSolidPredicate;

    int minX = FloorInt(box->minX);
    int maxX = FloorInt(box->maxX);
    int minY = FloorInt(box->minY);
    int maxY = FloorInt(box->maxY);
    int minZ = FloorInt(box->minZ);
    int maxZ = FloorInt(box->maxZ);

    for (int bx = minX; bx <= maxX; ++bx) {
        for (int by = minY; by <= maxY; ++by) {
            for (int bz = minZ; bz <= maxZ; ++bz) {
                if (!isSolid(bx, by, bz)) continue;

                AABB blockBox;
                blockBox.minX = (float)bx;
                blockBox.minY = (float)by;
                blockBox.minZ = (float)bz;
                blockBox.maxX = (float)(bx + 1);
                blockBox.maxY = (float)(by + 1);
                blockBox.maxZ = (float)(bz + 1);

                if (AABB_Intersects(box, &blockBox)) {
                    return true;
                }
            }
        }
    }
    return false;
}

bool Physics_CheckCollision(const AABB* box) {
    return Physics_CheckCollisionEx(box, NULL);
}

bool Physics_HasGroundSupport(float x, float y, float z, PhysicsSolidQueryFn customSolid) {
    PhysicsSolidQueryFn isSolid = customSolid ? customSolid : DefaultSolidPredicate;

    // Probes a downward volume directly under the player foot footprint [-0.1m depth]
    float halfW = PLAYER_HALF_WIDTH;
    AABB probeBox;
    probeBox.minX = x - halfW;
    probeBox.maxX = x + halfW;
    probeBox.minY = y - PHYSICS_LEDGE_PROBE_DEPTH;
    probeBox.maxY = y;
    probeBox.minZ = z - halfW;
    probeBox.maxZ = z + halfW;

    int minX = FloorInt(probeBox.minX);
    int maxX = FloorInt(probeBox.maxX);
    int probeY = FloorInt(y - PHYSICS_LEDGE_PROBE_DEPTH);
    int minZ = FloorInt(probeBox.minZ);
    int maxZ = FloorInt(probeBox.maxZ);

    for (int bx = minX; bx <= maxX; ++bx) {
        for (int bz = minZ; bz <= maxZ; ++bz) {
            if (isSolid(bx, probeY, bz)) {
                return true;
            }
        }
    }
    return false;
}

/* ========================================================================= */
/* 4. Single-Axis Movement Resolution & Anti-Tunneling                      */
/* ========================================================================= */

/**
 * @brief Resolves a 1D coordinate displacement along an isolated axis against voxel lattice.
 * @param axis 0=X, 1=Y, 2=Z.
 * @return True if a collision contact occurred and position was clamped.
 */
static bool ResolveAxisDisplacement(PlayerPhysicsState* player, int axis, float delta,
                                    PhysicsSolidQueryFn isSolid) {
    if (fabsf(delta) < 1e-7f) return false;

    if (axis == 0) {
        player->x += delta;
    } else if (axis == 1) {
        player->y += delta;
    } else if (axis == 2) {
        player->z += delta;
    }
    Physics_UpdateHitbox(player);

    AABB box = player->hitbox;
    int minX = FloorInt(box.minX);
    int maxX = FloorInt(box.maxX);
    int minY = FloorInt(box.minY);
    int maxY = FloorInt(box.maxY);
    int minZ = FloorInt(box.minZ);
    int maxZ = FloorInt(box.maxZ);

    bool hit = false;
    for (int bx = minX; bx <= maxX; ++bx) {
        for (int by = minY; by <= maxY; ++by) {
            for (int bz = minZ; bz <= maxZ; ++bz) {
                if (!isSolid(bx, by, bz)) continue;

                AABB blockBox;
                blockBox.minX = (float)bx;
                blockBox.minY = (float)by;
                blockBox.minZ = (float)bz;
                blockBox.maxX = (float)(bx + 1);
                blockBox.maxY = (float)(by + 1);
                blockBox.maxZ = (float)(bz + 1);

                if (AABB_Intersects(&player->hitbox, &blockBox)) {
                    hit = true;
                    if (axis == 1) { // Y-Axis
                        if (delta > 0.0f) { // Upward ceiling head-bump
                            float playerHeight = player->isSneaking ? PLAYER_HEIGHT_SNEAKING : PLAYER_HEIGHT_STANDING;
                            player->y = blockBox.minY - playerHeight;
                            player->vy = 0.0f;
                        } else { // Downward floor landing
                            player->y = blockBox.maxY;
                            player->vy = 0.0f;
                            player->isGrounded = true;
                        }
                    } else if (axis == 0) { // X-Axis
                        if (delta > 0.0f) {
                            player->x = blockBox.minX - PLAYER_HALF_WIDTH;
                        } else {
                            player->x = blockBox.maxX + PLAYER_HALF_WIDTH;
                        }
                        player->vx = 0.0f;
                    } else if (axis == 2) { // Z-Axis
                        if (delta > 0.0f) {
                            player->z = blockBox.minZ - PLAYER_HALF_WIDTH;
                        } else {
                            player->z = blockBox.maxZ + PLAYER_HALF_WIDTH;
                        }
                        player->vz = 0.0f;
                    }
                    Physics_UpdateHitbox(player);
                }
            }
        }
    }
    return hit;
}

/**
 * @brief Sub-steps displacement if |delta| > 0.5m to guarantee zero tunneling across thin boundaries.
 */
static bool ResolveAxisWithSubstepping(PlayerPhysicsState* player, int axis, float delta,
                                       PhysicsSolidQueryFn isSolid) {
    float totalDist = fabsf(delta);
    if (totalDist < 1e-7f) return false;

    int steps = (int)ceilf(totalDist / PHYSICS_SUBSTEP_THRESHOLD);
    if (steps < 1) steps = 1;
    float stepDelta = delta / (float)steps;

    bool anyHit = false;
    for (int s = 0; s < steps; ++s) {
        bool hit = ResolveAxisDisplacement(player, axis, stepDelta, isSolid);
        if (hit) {
            anyHit = true;
            break;
        }
    }
    return anyHit;
}

/* ========================================================================= */
/* 5. Horizontal Resolution with Auto-Stepping                               */
/* ========================================================================= */

static void ResolveHorizontalWithAutoStep(PlayerPhysicsState* player, float dx, float dz,
                                          PhysicsSolidQueryFn isSolid) {
    float initialX = player->x;
    float initialY = player->y;
    float initialZ = player->z;

    // 1. Attempt standard flat horizontal resolution: X then Z
    ResolveAxisWithSubstepping(player, 0, dx, isSolid);
    ResolveAxisWithSubstepping(player, 2, dz, isSolid);

    float flatX = player->x;
    float flatZ = player->z;

    // Evaluate whether forward progress was impeded by a solid obstruction
    bool wasBlocked = (fabsf(flatX - (initialX + dx)) > 1e-4f) ||
                      (fabsf(flatZ - (initialZ + dz)) > 1e-4f);

    // Auto-stepping requires active ground support (cannot climb mid-air)
    if (wasBlocked && player->isGrounded) {
        // Revert to pre-horizontal starting coordinates
        player->x = initialX;
        player->y = initialY;
        player->z = initialZ;
        Physics_UpdateHitbox(player);

        // Speculative Step Phase 1: Elevate by step height (+0.55m)
        bool headBump = ResolveAxisDisplacement(player, 1, PHYSICS_AUTOSTEP_HEIGHT, isSolid);
        if (!headBump) {
            // Speculative Step Phase 2: Traverse horizontally at elevated height
            ResolveAxisWithSubstepping(player, 0, dx, isSolid);
            ResolveAxisWithSubstepping(player, 2, dz, isSolid);

            // Speculative Step Phase 3: Snap down onto obstacle surface
            ResolveAxisDisplacement(player, 1, -PHYSICS_AUTOSTEP_HEIGHT, isSolid);

            // Progress Evaluation: Compare squared horizontal travel distance
            float distSqFlat = (flatX - initialX) * (flatX - initialX) +
                               (flatZ - initialZ) * (flatZ - initialZ);
            float distSqStep = (player->x - initialX) * (player->x - initialX) +
                               (player->z - initialZ) * (player->z - initialZ);

            if (distSqStep <= distSqFlat + 1e-4f) {
                // Stepped path did not exceed flat progress (e.g. 1.0m tall wall); revert to flat
                player->x = flatX;
                player->y = initialY;
                player->z = flatZ;
                Physics_UpdateHitbox(player);
            } else {
                // Step committed successfully onto obstacle
                player->isGrounded = true;
            }
        } else {
            // Insufficient vertical headroom (<1.8m clearance above step); abort auto-step
            player->x = flatX;
            player->y = initialY;
            player->z = flatZ;
            Physics_UpdateHitbox(player);
        }
    }
}

/* ========================================================================= */
/* 6. Primary Physics Tick Execution (Physics_Step)                          */
/* ========================================================================= */

void Physics_StepEx(PlayerPhysicsState* player, float dt, PhysicsSolidQueryFn customSolid) {
    if (!player || dt <= 0.0f) return;
    PhysicsSolidQueryFn isSolid = customSolid ? customSolid : DefaultSolidPredicate;

    // Cache pre-tick position for 60 Hz sub-frame interpolation
    player->prevX = player->x;
    player->prevY = player->y;
    player->prevZ = player->z;

    // 1. Target Horizontal Velocity & Acceleration Blending
    float baseSpeed = PLAYER_SPEED_WALK;
    if (player->isSneaking) {
        baseSpeed = PLAYER_SPEED_SNEAK;
    } else if (player->isSprinting) {
        baseSpeed = PLAYER_SPEED_SPRINT;
    }

    float targetVx = player->wishX * baseSpeed;
    float targetVz = player->wishZ * baseSpeed;

    float accelRate = player->isGrounded ? PHYSICS_ACCEL_GROUND : PHYSICS_ACCEL_AIR;
    float blend = FloatMin(accelRate * dt, 1.0f);
    player->vx += (targetVx - player->vx) * blend;
    player->vz += (targetVz - player->vz) * blend;

    // 2. Vertical Jump & Gravity Acceleration
    if (player->jumpRequested && player->isGrounded) {
        player->vy = PHYSICS_JUMP_IMPULSE;
        player->isGrounded = false;
        player->jumpRequested = false;
    }

    player->vy += PHYSICS_GRAVITY * dt;
    if (player->vy < PHYSICS_TERMINAL_VELOCITY) {
        player->vy = PHYSICS_TERMINAL_VELOCITY;
    }

    // 3. Compute 3D Displacements
    float dx = player->vx * dt;
    float dy = player->vy * dt;
    float dz = player->vz * dt;

    // 4. Sneak Ledge-Falloff Clamp
    if (player->isSneaking && player->isGrounded) {
        if (fabsf(dx) > 1e-7f) {
            float probeX = player->x + dx;
            if (!Physics_HasGroundSupport(probeX, player->y, player->z, isSolid)) {
                dx = 0.0f;
            }
        }
        if (fabsf(dz) > 1e-7f) {
            float probeZ = player->z + dz;
            if (!Physics_HasGroundSupport(player->x, player->y, probeZ, isSolid)) {
                dz = 0.0f;
            }
        }
    }

    // 5. Collision Order Invariant: Step Y (Vertical) First
    player->isGrounded = false;
    ResolveAxisWithSubstepping(player, 1, dy, isSolid);

    // 6. Collision Order Invariant: Step X then Z with Auto-Stepping
    ResolveHorizontalWithAutoStep(player, dx, dz, isSolid);

    // Final bounding box update
    Physics_UpdateHitbox(player);
}

void Physics_Step(PlayerPhysicsState* player, float dt) {
    Physics_StepEx(player, dt, NULL);
}

/* ========================================================================= */
/* 7. Amanatides-Woo Fast Voxel Traversal (DDA Raycast)                      */
/* ========================================================================= */

bool Physics_RaycastEx(float startX, float startY, float startZ,
                       float dirX, float dirY, float dirZ,
                       float maxDist, RaycastHit* outHit,
                       PhysicsSolidQueryFn customSolid) {
    if (!outHit) return false;
    memset(outHit, 0, sizeof(RaycastHit));
    PhysicsSolidQueryFn isSolid = customSolid ? customSolid : DefaultSolidPredicate;

    // Normalize direction vector
    float lenSq = dirX * dirX + dirY * dirY + dirZ * dirZ;
    if (lenSq < 1e-12f) return false;
    float invLen = 1.0f / sqrtf(lenSq);
    dirX *= invLen;
    dirY *= invLen;
    dirZ *= invLen;

    // Current integer voxel coordinate
    int x = FloorInt(startX);
    int y = FloorInt(startY);
    int z = FloorInt(startZ);

    int stepX = (dirX > 0.0f) ? 1 : ((dirX < 0.0f) ? -1 : 0);
    int stepY = (dirY > 0.0f) ? 1 : ((dirY < 0.0f) ? -1 : 0);
    int stepZ = (dirZ > 0.0f) ? 1 : ((dirZ < 0.0f) ? -1 : 0);

    const float INF = 1e30f;
    float tDeltaX = (stepX != 0) ? fabsf(1.0f / dirX) : INF;
    float tDeltaY = (stepY != 0) ? fabsf(1.0f / dirY) : INF;
    float tDeltaZ = (stepZ != 0) ? fabsf(1.0f / dirZ) : INF;

    float tMaxX = (stepX > 0) ? ((floorf(startX) + 1.0f - startX) * tDeltaX)
                              : ((startX - floorf(startX)) * tDeltaX);
    float tMaxY = (stepY > 0) ? ((floorf(startY) + 1.0f - startY) * tDeltaY)
                              : ((startY - floorf(startY)) * tDeltaY);
    float tMaxZ = (stepZ > 0) ? ((floorf(startZ) + 1.0f - startZ) * tDeltaZ)
                              : ((startZ - floorf(startZ)) * tDeltaZ);

    // Check starting block
    if (isSolid(x, y, z)) {
        outHit->hit = true;
        outHit->targetX = x;
        outHit->targetY = y;
        outHit->targetZ = z;
        outHit->normalX = 0;
        outHit->normalY = 1;
        outHit->normalZ = 0;
        outHit->placeX = x;
        outHit->placeY = y + 1;
        outHit->placeZ = z;
        outHit->distance = 0.0f;
        return true;
    }

    float currentT = 0.0f;
    int normalX = 0, normalY = 0, normalZ = 0;

    while (currentT <= maxDist) {
        if (tMaxX < tMaxY) {
            if (tMaxX < tMaxZ) {
                currentT = tMaxX;
                tMaxX += tDeltaX;
                x += stepX;
                normalX = -stepX; normalY = 0; normalZ = 0;
            } else {
                currentT = tMaxZ;
                tMaxZ += tDeltaZ;
                z += stepZ;
                normalX = 0; normalY = 0; normalZ = -stepZ;
            }
        } else {
            if (tMaxY < tMaxZ) {
                currentT = tMaxY;
                tMaxY += tDeltaY;
                y += stepY;
                normalX = 0; normalY = -stepY; normalZ = 0;
            } else {
                currentT = tMaxZ;
                tMaxZ += tDeltaZ;
                z += stepZ;
                normalX = 0; normalY = 0; normalZ = -stepZ;
            }
        }

        if (currentT > maxDist) break;

        if (isSolid(x, y, z)) {
            outHit->hit = true;
            outHit->targetX = x;
            outHit->targetY = y;
            outHit->targetZ = z;
            outHit->normalX = normalX;
            outHit->normalY = normalY;
            outHit->normalZ = normalZ;
            outHit->placeX = x + normalX;
            outHit->placeY = y + normalY;
            outHit->placeZ = z + normalZ;
            outHit->distance = currentT;
            return true;
        }
    }

    return false;
}

bool Physics_Raycast(float startX, float startY, float startZ,
                     float dirX, float dirY, float dirZ,
                     float maxDist, RaycastHit* outHit) {
    return Physics_RaycastEx(startX, startY, startZ, dirX, dirY, dirZ, maxDist, outHit, NULL);
}

/* ========================================================================= */
/* 8. Block Placement Anti-Suffocation Validation                            */
/* ========================================================================= */

bool Physics_ValidateBlockPlacement(int placeX, int placeY, int placeZ,
                                   const PlayerPhysicsState* player,
                                   PhysicsSolidQueryFn customSolid) {
    if (!player) return false;
    PhysicsSolidQueryFn isSolid = customSolid ? customSolid : DefaultSolidPredicate;

    // 1. World height boundary check
    if (placeY < 0 || placeY >= CHUNK_HEIGHT) {
        return false;
    }

    // 2. Cell must currently be empty (not already solid)
    if (isSolid(placeX, placeY, placeZ)) {
        return false;
    }

    // 3. Block AABB vs Player Hitbox self-intersection test
    AABB blockBox;
    blockBox.minX = (float)placeX;
    blockBox.minY = (float)placeY;
    blockBox.minZ = (float)placeZ;
    blockBox.maxX = (float)(placeX + 1);
    blockBox.maxY = (float)(placeY + 1);
    blockBox.maxZ = (float)(placeZ + 1);

    if (AABB_Intersects(&blockBox, &player->hitbox)) {
        return false; // REJECT: Suffocation risk
    }

    return true;
}
