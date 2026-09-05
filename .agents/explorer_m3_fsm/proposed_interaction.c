/**
 * @file proposed_interaction.c
 * @brief Implementation of Block Destruction FSM, Placement Validation & Voxel Interaction.
 */

#include "proposed_interaction.h"
#include <math.h>

// ponytail: [static block hardness switch] -> [JSON data-driven block property registry for modding]

float Interaction_GetBlockHardness(uint8_t blockId) {
    switch (blockId) {
        case BLOCK_AIR:
        case BLOCK_FLOWER:
        case BLOCK_TALLGRASS:
            return 0.0f;       // Instant break

        case BLOCK_SNOW:
        case BLOCK_LEAVES:
            return 0.2f;       // Fast break

        case BLOCK_CACTUS:
            return 0.4f;

        case BLOCK_DIRT:
        case BLOCK_SAND:
            return 0.5f;       // 0.5s duration

        case BLOCK_GRASS:
            return 0.6f;

        case BLOCK_SANDSTONE:
            return 0.8f;

        case BLOCK_STONE:
            return 1.5f;       // 1.5s duration

        case BLOCK_WOOD:
            return 2.0f;       // 2.0s duration

        case BLOCK_BEDROCK:
        case BLOCK_WATER:
        default:
            return -1.0f;      // Indestructible / unmineable
    }
}

float Interaction_GetToolMultiplier(uint8_t toolItemId, uint8_t blockId) {
    // Check pickaxe tier against stone/sandstone
    if (blockId == BLOCK_STONE || blockId == BLOCK_SANDSTONE) {
        switch (toolItemId) {
            case ITEM_WOODEN_PICKAXE:
                return 2.0f;   // 2.0x mining speedup (cuts stone break time to 0.75s)
            case ITEM_STONE_PICKAXE:
                return 4.0f;   // 4.0x mining speedup
            case ITEM_IRON_PICKAXE:
                return 6.0f;   // 6.0x mining speedup
            default:
                return 1.0f;   // Bare hands or non-pickaxe
        }
    }

    // Default bare-hands multiplier
    return 1.0f;
}

uint8_t Interaction_GetBlockDropItem(uint8_t blockId) {
    return Block_ToItemId(blockId);
}

void Interaction_DestructionInit(BlockDestructionFSM* fsm) {
    if (!fsm) return;
    fsm->isMining = false;
    fsm->targetX = 0;
    fsm->targetY = 0;
    fsm->targetZ = 0;
    fsm->targetBlockId = BLOCK_AIR;
    fsm->progress = 0.0f;
    fsm->crackStage = -1;
}

void Interaction_DestructionReset(BlockDestructionFSM* fsm) {
    if (!fsm) return;
    fsm->isMining = false;
    fsm->targetX = 0;
    fsm->targetY = 0;
    fsm->targetZ = 0;
    fsm->targetBlockId = BLOCK_AIR;
    fsm->progress = 0.0f;
    fsm->crackStage = -1;
}

int Interaction_GetCrackStage(const BlockDestructionFSM* fsm) {
    if (!fsm || !fsm->isMining) return -1;
    return fsm->crackStage;
}

bool Interaction_UpdateDestruction(
    BlockDestructionFSM* fsm,
    bool hasRaycastHit,
    const RaycastHit* hit,
    float playerDistance,
    uint8_t heldItemId,
    float dt,
    bool leftMouseDown,
    ItemDrop* outDrop
) {
    if (!fsm) return false;

    // Reset output drop record
    if (outDrop) {
        outDrop->active = false;
    }

    // 1. Cancellation checks: button release, raycast miss, or reach limit exceeded (> 5.0m)
    if (!leftMouseDown || !hasRaycastHit || !hit || !hit->hit || playerDistance > MAX_INTERACTION_REACH) {
        Interaction_DestructionReset(fsm);
        return false;
    }

    int tx = hit->targetX;
    int ty = hit->targetY;
    int tz = hit->targetZ;

    // Sample target block from world
    uint8_t currentBlock = World_GetBlock(tx, ty, tz);
    if (currentBlock == BLOCK_AIR) {
        Interaction_DestructionReset(fsm);
        return false;
    }

    float hardness = Interaction_GetBlockHardness(currentBlock);

    // 2. Bedrock & Indestructible blocks (H < 0.0f)
    if (hardness < 0.0f) {
        fsm->targetX = tx;
        fsm->targetY = ty;
        fsm->targetZ = tz;
        fsm->targetBlockId = currentBlock;
        fsm->progress = 0.0f;
        fsm->crackStage = 0;
        fsm->isMining = true;
        return false; // Never breaks
    }

    // 3. Instant break blocks (H == 0.0f, e.g. tallgrass, flower)
    if (hardness == 0.0f) {
        World_SetBlock(tx, ty, tz, BLOCK_AIR);
        uint8_t dropId = Interaction_GetBlockDropItem(currentBlock);
        if (dropId != ITEM_AIR && outDrop) {
            outDrop->active = true;
            outDrop->itemId = dropId;
            outDrop->count = 1;
            outDrop->x = (float)tx + 0.5f;
            outDrop->y = (float)ty + 0.5f;
            outDrop->z = (float)tz + 0.5f;
        }
        Interaction_DestructionReset(fsm);
        return true;
    }

    // 4. Target tracking: reset progress if crosshair switched to a different voxel
    if (!fsm->isMining || fsm->targetX != tx || fsm->targetY != ty || fsm->targetZ != tz || fsm->targetBlockId != currentBlock) {
        fsm->targetX = tx;
        fsm->targetY = ty;
        fsm->targetZ = tz;
        fsm->targetBlockId = currentBlock;
        fsm->progress = 0.0f;
        fsm->isMining = true;
    }

    // 5. Accumulate destruction progress: Delta P = (dt * M_tool) / Hardness
    float toolMult = Interaction_GetToolMultiplier(heldItemId, currentBlock);
    float deltaP = (dt * toolMult) / hardness;
    fsm->progress += deltaP;

    // 6. Completion check (P >= 1.0f)
    if (fsm->progress >= 1.0f) {
        World_SetBlock(tx, ty, tz, BLOCK_AIR);
        uint8_t dropId = Interaction_GetBlockDropItem(currentBlock);
        if (dropId != ITEM_AIR && outDrop) {
            outDrop->active = true;
            outDrop->itemId = dropId;
            outDrop->count = 1;
            outDrop->x = (float)tx + 0.5f;
            outDrop->y = (float)ty + 0.5f;
            outDrop->z = (float)tz + 0.5f;
        }
        Interaction_DestructionReset(fsm);
        return true;
    }

    // 7. Update visual crack overlay stage: S = min(9, max(0, floor(P * 10.0)))
    int stage = (int)floorf(fsm->progress * 10.0f);
    if (stage > 9) stage = 9;
    if (stage < 0) stage = 0;
    fsm->crackStage = stage;

    return false;
}

bool Interaction_ValidatePlacement(
    int placeX, int placeY, int placeZ,
    float playerX, float playerY, float playerZ,
    bool isSneaking,
    uint8_t currentBlockAtPlace
) {
    // 1. World height boundary check
    if (placeY < 0 || placeY >= CHUNK_HEIGHT) {
        return false;
    }

    // 2. Target cell occupancy check: must be air
    if (currentBlockAtPlace != BLOCK_AIR) {
        return false;
    }

    // 3. Anti-suffocation self-intersection: block AABB vs player AABB
    AABB blockBox;
    blockBox.minX = (float)placeX;
    blockBox.minY = (float)placeY;
    blockBox.minZ = (float)placeZ;
    blockBox.maxX = (float)placeX + 1.0f;
    blockBox.maxY = (float)placeY + 1.0f;
    blockBox.maxZ = (float)placeZ + 1.0f;

    float halfW = 0.3f;
    float height = isSneaking ? 1.5f : 1.8f;
    AABB playerBox;
    playerBox.minX = playerX - halfW;
    playerBox.minY = playerY;
    playerBox.minZ = playerZ - halfW;
    playerBox.maxX = playerX + halfW;
    playerBox.maxY = playerY + height;
    playerBox.maxZ = playerZ + halfW;

    if (AABB_Intersects(&playerBox, &blockBox)) {
        return false; // Placement rejected: overlaps player volume
    }

    return true;
}

bool Interaction_TryPlaceBlock(
    const RaycastHit* hit,
    float playerX, float playerY, float playerZ,
    bool isSneaking,
    PlayerInventory* inv
) {
    if (!hit || !hit->hit || !inv) return false;

    ItemStack* active = Inventory_GetActiveItem(inv);
    if (!active || active->count == 0 || active->itemId == ITEM_AIR) {
        return false;
    }

    // Convert item to placeable block ID
    uint8_t blockId = Item_ToBlockId(active->itemId);
    if (blockId == BLOCK_AIR) {
        return false; // Not a placeable block (e.g. tool or stick)
    }

    int px = hit->placeX;
    int py = hit->placeY;
    int pz = hit->placeZ;

    // Check existing block at target position
    uint8_t existing = World_GetBlock(px, py, pz);
    if (!Interaction_ValidatePlacement(px, py, pz, playerX, playerY, playerZ, isSneaking, existing)) {
        return false;
    }

    // Commit placement into world
    if (!World_SetBlock(px, py, pz, blockId)) {
        return false;
    }

    // Decrement item stack
    Inventory_DecrementActiveItem(inv, 1);
    return true;
}
