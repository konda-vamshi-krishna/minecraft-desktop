/**
 * @file physics.h
 * @brief Custom Swept AABB Player Kinematics & Collision Subsystem for Milestone 3.
 *
 * Implements full mechanical parity with official Minecraft Java Edition kinematics:
 * - Rigid player AABB geometry (standing 0.6x1.8x0.6m, sneaking 0.6x1.5x0.6m, eye levels +1.62m/+1.35m).
 * - Exact canonical Java constants: gravity g=-32.0 m/s^2, terminal velocity v_term=-78.4 m/s,
 *   ground friction 0.546 (0.6 * 0.91), air drag 0.98 factor/tick, jump impulse 8.944 m/s (discrete 8.4 m/s).
 * - Axis-Decoupled Collision Order Invariant: strictly Y -> X -> Z against voxel grid.
 * - Anti-tunneling sub-step partitioning for terminal velocity drops (|delta| > 0.5m).
 * - Speculative auto-step (+0.55m) with automatic low ceiling (<1.8m clearance) abort.
 * - Sneak ledge-clamping with downward -0.1m ground support probe.
 * - Fast Voxel Traversal (Amanatides-Woo DDA) for block raymarching up to 5.0m.
 * - Zero dynamic heap allocations (pure static/stack C99 value types).
 */

#ifndef MINECRAFT_GAMEPLAY_PHYSICS_H
#define MINECRAFT_GAMEPLAY_PHYSICS_H

#include <stdbool.h>
#include <stdint.h>
#include <math.h>
#include  ../core/math_utils.h
#include ../world/world.h

#ifdef __cplusplus
extern C {
#endif

// =============================================================================
// Canonical Minecraft Java Kinematic Constants (docs/02 §4, docs/06 §3)
// =============================================================================

// Player Bounding Box Dimensions (Meters)
#define PLAYER_WIDTH                0.60f   // Horizontal bounding box width (X and Z)
#define PLAYER_HALF_WIDTH           0.30f   // Horizontal extent from center: [-0.3, +0.3]
#define PLAYER_HEIGHT_STANDING      1.80f   // Standing bounding box height: [0.0, 1.8]
#define PLAYER_HEIGHT_SNEAKING      1.50f   // Sneaking bounding box height: [0.0, 1.5]
#define PLAYER_EYE_OFFSET_STANDING  1.62f   // Camera eye elevation above feet (standing)
#define PLAYER_EYE_OFFSET_SNEAKING  1.35f   // Camera eye elevation above feet (sneaking)

// Movement Speeds (Meters / Second)
#define PLAYER_SPEED_WALK           4.317f  // Base walking velocity (0.21585 blk/tick at 20 TPS)
#define PLAYER_SPEED_SPRINT         5.612f  // Sprinting velocity (1.30x walk)
#define PLAYER_SPEED_SNEAK          1.295f  // Sneaking velocity (0.30x walk)

// Gravitational Acceleration & Terminal Ceilings
#define PHYSICS_GRAVITY             -32.0f  // Downward acceleration: g = 0.08 blk/tick^2 * (20 TPS)^2 = 32.0 m/s^2
#define PHYSICS_TERMINAL_VELOCITY   -78.4f  // Terminal falling velocity: -3.92 blk/tick * 20 TPS = -78.4 m/s
#define PHYSICS_JUMP_IMPULSE        8.944f  // Continuous jump impulse (sqrt(2 * 32.0 * 1.25) = 8.944 m/s -> 1.250m apex)
#define PHYSICS_JUMP_IMPULSE_DISC   8.400f  // Discrete 20 TPS jump impulse (0.42 blk/tick * 20 = 8.4 m/s -> 1.252m apex)

// Traction, Drag & Friction Damping
#define PHYSICS_GROUND_FRICTION     0.546f  // Canonical Java ground friction factor: 0.6 * 0.91 = 0.546
#define PHYSICS_AIR_DRAG            0.980f  // Canonical Java air drag factor per tick
#define PHYSICS_ACCEL_GROUND        15.00f  // Ground responsive acceleration blend rate (1/s)
#define PHYSICS_ACCEL_AIR           4.000f  // Airborne inertial control blend rate (1/s)

// Geometry & Obstacle Thresholds
#define PHYSICS_AUTOSTEP_HEIGHT     0.550f  // Speculative auto-step upward probe height (0.5m slab + 0.05m tolerance)
#define PHYSICS_LEDGE_PROBE_DEPTH   0.100f  // Downward ground support probe depth beneath feet
#define PHYSICS_SUBSTEP_THRESHOLD   0.500f  // Maximum single-step displacement before anti-tunneling subdivision
#define PHYSICS_REACH_SURVIVAL      4.500f  // Survival mode raycast reach threshold (meters)
#define PHYSICS_REACH_CREATIVE      5.000f  // Creative mode raycast reach threshold (meters)

// =============================================================================
// Raycast Hit Result (Amanatides-Woo Fast Voxel Traversal)
// =============================================================================

typedef struct RaycastHit {
    bool hit;           // True if ray struck a solid voxel
    int targetX;        // Integer lattice coordinates of struck solid voxel
    int targetY;
    int targetZ;
    int normalX;        // Surface normal of entered face: n = -stepDir * e_i
    int normalY;
    int normalZ;
    int placeX;         // Adjacent placement coordinate: target + normal
    int placeY;
    int placeZ;
    float distance;     // Parametric distance from ray origin to impact point
} RaycastHit;

// Custom solid query predicate (NULL defaults to World_GetBlock + Block_IsSolid)
typedef bool (*PhysicsSolidQueryFn)(int x, int y, int z);

// =============================================================================
// Player Physics State Machine (Interface Contract)
// =============================================================================

// ponytail: [Discrete axis-by-axis resolution] -> [Continuous Minkowski swept volume hull if speeds exceed 60 m/s]
// ponytail: [Full 1.0m block AABBs] -> [Sub-block / slab / stair custom AABB dispatch table]
typedef struct PlayerPhysicsState {
    // Kinematic position of player base (feet level at center of horizontal hitbox)
    float x, y, z;

    // Kinematic velocity in meters/second
    float vx, vy, vz;

    // Previous physics tick position (used for sub-frame 60 Hz renderer interpolation)
    float prevX, prevY, prevZ;

    // Normalized planar movement wish direction from keyboard input: [-1.0, 1.0]
    float wishX, wishY, wishZ;

    // Kinematic state flags
    bool isGrounded;        // True if player base is supported by solid voxel
    bool isSneaking;        // True if sneak key is held (AABB height 1.5m, ledge edge-clamping active)
    bool isSprinting;       // True if sprint is engaged (speed multiplier 1.30x)
    bool jumpRequested;     // True if jump action was initiated this frame

    // Cached Axis-Aligned Bounding Box
    AABB hitbox;
} PlayerPhysicsState;

// =============================================================================
// Public Function Prototypes
// =============================================================================

/**
 * @brief Initializes a player physics state at the given starting coordinates.
 */
void Physics_InitPlayer(PlayerPhysicsState* player, float x, float y, float z);

/**
 * @brief Updates the player's rigid AABB hitbox from current position and sneaking state.
 */
void Physics_UpdateHitbox(PlayerPhysicsState* player);

/**
 * @brief Constructs an AABB for a player at an arbitrary coordinate.
 */
AABB Physics_GetAABBAt(float x, float y, float z, bool isSneaking);

/**
 * @brief Returns the camera eye position for the current player state.
 */
Vec3 Physics_GetEyePosition(const PlayerPhysicsState* player);

/**
 * @brief Computes linearly interpolated render position for smooth 60 Hz presentation.
 * @param player Pointer to player physics state.
 * @param alpha Accumulator interpolation fraction in [0.0, 1.0).
 */
Vec3 Physics_GetInterpolatedRenderPosition(const PlayerPhysicsState* player, float alpha);

/**
 * @brief Computes linearly interpolated camera eye position for smooth 60 Hz presentation.
 * @param player Pointer to player physics state.
 * @param alpha Accumulator interpolation fraction in [0.0, 1.0).
 */
Vec3 Physics_GetInterpolatedEyePosition(const PlayerPhysicsState* player, float alpha);

/**
 * @brief Advances player physics by fixed timestep dt against the active world grid.
 * Enforces strictly: Y-axis vertical -> X-axis horizontal -> Z-axis horizontal.
 */
void Physics_Step(PlayerPhysicsState* player, float dt);

/**
 * @brief Advances player physics using an explicit custom solid voxel predicate (for unit tests / mock worlds).
 */
void Physics_StepEx(PlayerPhysicsState* player, float dt, PhysicsSolidQueryFn customSolid);

/**
 * @brief Evaluates whether an AABB intersects any solid voxel in the active world.
 */
bool Physics_CheckCollision(const AABB* box);

/**
 * @brief Evaluates whether an AABB intersects any solid voxel using a custom predicate.
 */
bool Physics_CheckCollisionEx(const AABB* box, PhysicsSolidQueryFn customSolid);

/**
 * @brief Checks if ground support exists directly beneath the given foot position.
 */
bool Physics_HasGroundSupport(float x, float y, float z, PhysicsSolidQueryFn customSolid);

/**
 * @brief Performs Amanatides-Woo Fast Voxel Traversal DDA raycasting up to maxDist.
 */
bool Physics_Raycast(float startX, float startY, float startZ,
                     float dirX, float dirY, float dirZ,
                     float maxDist, RaycastHit* outHit);

/**
 * @brief Performs DDA raycasting with a custom solid query predicate.
 */
bool Physics_RaycastEx(float startX, float startY, float startZ,
                       float dirX, float dirY, float dirZ,
                       float maxDist, RaycastHit* outHit,
                       PhysicsSolidQueryFn customSolid);

/**
 * @brief Validates whether a block can be safely placed without suffocating the player.
 * Enforces Y in [0, 255], empty target cell, and non-intersection with player AABB.
 */
bool Physics_ValidateBlockPlacement(int placeX, int placeY, int placeZ,
                                   const PlayerPhysicsState* player,
                                   PhysicsSolidQueryFn customSolid);

#ifdef __cplusplus
}
#endif

#endif // MINECRAFT_GAMEPLAY_PHYSICS_H
