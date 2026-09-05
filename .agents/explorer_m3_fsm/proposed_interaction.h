/**
 * @file proposed_interaction.h
 * @brief Progressive Block Destruction FSM, Placement Validation & Voxel Interaction Engine.
 *
 * Implements:
 * 1. Progressive Block Destruction FSM:
 *    - Crosshair tracking with target coordinate lock.
 *    - Instant cancellation upon cursor departure, release, or reach exceeding 5.0m.
 *    - Canonical hardness timing and tool efficiency multipliers.
 *    - 10-stage crack overlay progression (stages 0..9).
 *    - Atomic block breaking, drop spawning, and audio trigger.
 * 2. Block Placement Validation:
 *    - Face normal displacement (P_place = P_block + normal).
 *    - Vertical world boundary enforcement (0 <= Y < 256).
 *    - Target occupancy verification (air/replaceable check).
 *    - Anti-suffocation player AABB vs block AABB intersection rejection.
 *    - Active hotbar stack decrement.
 *
 * Zero heap allocations, strictly C99, Ponytail minimal complexity.
 */

#ifndef MINECRAFT_GAMEPLAY_INTERACTION_H
#define MINECRAFT_GAMEPLAY_INTERACTION_H

#include <stdint.h>
#include <stdbool.h>
#include "../core/math_utils.h"
#include "../world/world.h"
#include "proposed_inventory.h"

#ifdef __cplusplus
extern "C" {
#endif

// =============================================================================
// Interaction Kinematic Constants (Canonical Minecraft Java Edition)
// =============================================================================
#define MAX_REACH_SURVIVAL      4.5f  // meters
#define MAX_REACH_CREATIVE      5.0f  // meters
#define MAX_INTERACTION_REACH   5.0f  // maximum threshold for interaction loop
#define ITEM_PICKUP_RADIUS      1.5f  // meters

// ponytail: [5.0m static interaction radius] -> [dynamic reach attribute for creative / modifier potions]

// =============================================================================
// Raycast Hit Result (Matches Amanatides-Woo DDA Output)
// =============================================================================
typedef struct RaycastHit {
    bool hit;
    int targetX, targetY, targetZ;     // Coordinates of solid voxel intersected
    int placeX, placeY, placeZ;        // Coordinates of adjacent placement voxel (target + normal)
    int normalX, normalY, normalZ;     // Entered face normal (-step_i * e_i)
    float distance;                    // Euclidean distance from ray origin to contact point
} RaycastHit;

// =============================================================================
// Item Drop Entity (Bobbing 3D Voxel Drop)
// =============================================================================
typedef struct ItemDrop {
    bool active;
    uint8_t itemId;
    uint8_t count;
    float x, y, z;                     // Center of spawned drop
    float spawnTime;                   // Timestamp for despawn & bobbing animation
} ItemDrop;

// =============================================================================
// Progressive Block Destruction FSM State
// =============================================================================
typedef struct BlockDestructionFSM {
    bool isMining;                     // True while left-click is actively held on target
    int targetX;                       // Locked target X
    int targetY;                       // Locked target Y
    int targetZ;                       // Locked target Z
    uint8_t targetBlockId;             // BlockID when mining began
    float progress;                    // Normalized destruction progress [0.0f, 1.0f]
    int crackStage;                    // 0..9 visual crack overlay stage (-1 if idle)
} BlockDestructionFSM;

// =============================================================================
// Hardness & Tool Efficiency Lookup
// =============================================================================
float    Interaction_GetBlockHardness(uint8_t blockId);
float    Interaction_GetToolMultiplier(uint8_t toolItemId, uint8_t blockId);
uint8_t  Interaction_GetBlockDropItem(uint8_t blockId);

// =============================================================================
// Block Destruction FSM API
// =============================================================================
void     Interaction_DestructionInit(BlockDestructionFSM* fsm);
void     Interaction_DestructionReset(BlockDestructionFSM* fsm);
int      Interaction_GetCrackStage(const BlockDestructionFSM* fsm);

/**
 * @brief Ticks the block destruction FSM for a single physics/gameplay tick.
 *
 * @param fsm              Pointer to state machine.
 * @param hasRaycastHit    True if DDA raycast hit a block within reach.
 * @param hit              Raycast hit structure.
 * @param playerDistance   Distance from player camera to target block center.
 * @param heldItemId       ItemId currently in active hotbar slot.
 * @param dt               Delta time (e.g. 1/60s).
 * @param leftMouseDown    Current state of primary attack/mine button.
 * @param outDrop          Output pointer populated with spawned drop if block shatters.
 * @return true if the target block shattered this tick, false otherwise.
 */
bool     Interaction_UpdateDestruction(
             BlockDestructionFSM* fsm,
             bool hasRaycastHit,
             const RaycastHit* hit,
             float playerDistance,
             uint8_t heldItemId,
             float dt,
             bool leftMouseDown,
             ItemDrop* outDrop
         );

// =============================================================================
// Block Placement Validation API
// =============================================================================
/**
 * @brief Validates whether a block can be safely placed at candidate coordinate.
 *
 * Checks:
 * 1. World vertical height: 0 <= placeY < 256.
 * 2. Target cell occupancy: must be air/replaceable.
 * 3. Anti-suffocation: block AABB must NOT intersect player AABB.
 *
 * @param placeX, placeY, placeZ Candidate voxel coordinates.
 * @param playerX, playerY, playerZ Base position of player.
 * @param isSneaking True if player is sneaking (height 1.5m vs 1.8m).
 * @param currentBlockAtPlace Current block ID at candidate position.
 * @return true if placement is valid, false if rejected.
 */
bool     Interaction_ValidatePlacement(
             int placeX, int placeY, int placeZ,
             float playerX, float playerY, float playerZ,
             bool isSneaking,
             uint8_t currentBlockAtPlace
         );

/**
 * @brief Attempts to place a block from the player's active hotbar slot.
 *
 * @param hit       DDA raycast hit result.
 * @param playerX, playerY, playerZ Player position.
 * @param isSneaking Player sneaking state.
 * @param inv       Player inventory.
 * @return true if block was placed and stack decremented, false otherwise.
 */
bool     Interaction_TryPlaceBlock(
             const RaycastHit* hit,
             float playerX, float playerY, float playerZ,
             bool isSneaking,
             PlayerInventory* inv
         );

#ifdef __cplusplus
}
#endif

#endif // MINECRAFT_GAMEPLAY_INTERACTION_H
