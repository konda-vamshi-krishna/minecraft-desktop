/**
 * @file proposed_inventory.c
 * @brief Implementation of 9-Slot Hotbar & 41-Slot Player Inventory State Machine.
 */

#include "inventory.h"
#include <string.h>

// ponytail: [fixed stack limits table] -> [dynamic NBT / data-driven item registry]

uint8_t Item_GetDefaultMaxStack(uint8_t itemId) {
    switch (itemId) {
        case ITEM_WOODEN_PICKAXE:
        case ITEM_STONE_PICKAXE:
        case ITEM_IRON_PICKAXE:
            return DEFAULT_MAX_STACK_TOOL; // 1
        default:
            return DEFAULT_MAX_STACK_BLOCK; // 64
    }
}

uint16_t Item_GetDefaultDurability(uint8_t itemId) {
    switch (itemId) {
        case ITEM_WOODEN_PICKAXE:
            return 59;
        case ITEM_STONE_PICKAXE:
            return 131;
        case ITEM_IRON_PICKAXE:
            return 250;
        default:
            return 0;
    }
}

bool Item_IsTool(uint8_t itemId) {
    return (itemId == ITEM_WOODEN_PICKAXE ||
            itemId == ITEM_STONE_PICKAXE  ||
            itemId == ITEM_IRON_PICKAXE);
}

bool Item_IsPlaceableBlock(uint8_t itemId) {
    switch (itemId) {
        case ITEM_STONE:
        case ITEM_DIRT:
        case ITEM_GRASS_BLOCK:
        case ITEM_COBBLESTONE:
        case ITEM_WOOD_LOG:
        case ITEM_WOOD_PLANKS:
        case ITEM_CRAFTING_TABLE:
        case ITEM_FURNACE:
        case ITEM_BEDROCK:
        case ITEM_SAND:
        case ITEM_SANDSTONE:
        case ITEM_SNOW:
        case ITEM_LEAVES:
        case ITEM_CACTUS:
        case ITEM_FLOWER:
        case ITEM_TALLGRASS:
            return true;
        default:
            return false;
    }
}

uint8_t Item_ToBlockId(uint8_t itemId) {
    switch (itemId) {
        case ITEM_STONE:
        case ITEM_COBBLESTONE:
            return BLOCK_STONE;
        case ITEM_DIRT:
            return BLOCK_DIRT;
        case ITEM_GRASS_BLOCK:
            return BLOCK_GRASS;
        case ITEM_WOOD_LOG:
        case ITEM_WOOD_PLANKS:
            return BLOCK_WOOD;
        case ITEM_SAND:
            return BLOCK_SAND;
        case ITEM_SANDSTONE:
            return BLOCK_SANDSTONE;
        case ITEM_SNOW:
            return BLOCK_SNOW;
        case ITEM_LEAVES:
            return BLOCK_LEAVES;
        case ITEM_BEDROCK:
            return BLOCK_BEDROCK;
        case ITEM_CACTUS:
            return BLOCK_CACTUS;
        case ITEM_FLOWER:
            return BLOCK_FLOWER;
        case ITEM_TALLGRASS:
            return BLOCK_TALLGRASS;
        default:
            return BLOCK_AIR;
    }
}

uint8_t Block_ToItemId(uint8_t blockId) {
    switch (blockId) {
        case BLOCK_STONE:
            return ITEM_COBBLESTONE;
        case BLOCK_DIRT:
            return ITEM_DIRT;
        case BLOCK_GRASS:
            return ITEM_DIRT;
        case BLOCK_WOOD:
            return ITEM_WOOD_LOG;
        case BLOCK_SAND:
            return ITEM_SAND;
        case BLOCK_SANDSTONE:
            return ITEM_SANDSTONE;
        case BLOCK_SNOW:
            return ITEM_SNOW;
        case BLOCK_CACTUS:
            return ITEM_CACTUS;
        case BLOCK_FLOWER:
            return ITEM_FLOWER;
        case BLOCK_BEDROCK:
            return ITEM_BEDROCK;
        case BLOCK_LEAVES:
        case BLOCK_TALLGRASS:
        case BLOCK_WATER:
        case BLOCK_AIR:
        default:
            return ITEM_AIR; // Leaves and tallgrass drop nothing by default with bare hands
    }
}

void Inventory_Init(PlayerInventory* inv) {
    if (!inv) return;
    for (int i = 0; i < TOTAL_SLOT_COUNT; i++) {
        ItemStack_Clear(&inv->slots[i]);
    }
    inv->selectedHotbarSlot = 0;
    ItemStack_Clear(&inv->cursorItem);
}

ItemStack* Inventory_GetSlot(PlayerInventory* inv, int slotIndex) {
    if (!inv || slotIndex < 0 || slotIndex >= TOTAL_SLOT_COUNT) return NULL;
    return &inv->slots[slotIndex];
}

const ItemStack* Inventory_GetSlotConst(const PlayerInventory* inv, int slotIndex) {
    if (!inv || slotIndex < 0 || slotIndex >= TOTAL_SLOT_COUNT) return NULL;
    return &inv->slots[slotIndex];
}

void Inventory_SelectHotbar(PlayerInventory* inv, int slotIndex) {
    if (!inv) return;
    if (slotIndex >= 0 && slotIndex < HOTBAR_SLOT_COUNT) {
        inv->selectedHotbarSlot = slotIndex;
    }
}

void Inventory_SelectHotbarKey(PlayerInventory* inv, int keyNumber) {
    if (!inv) return;
    if (keyNumber >= 1 && keyNumber <= HOTBAR_SLOT_COUNT) {
        inv->selectedHotbarSlot = keyNumber - 1;
    }
}

void Inventory_ScrollHotbar(PlayerInventory* inv, int scrollDelta) {
    if (!inv) return;
    // Positive modulo wrap-around: ((slot - delta) % 9 + 9) % 9
    int next = ((inv->selectedHotbarSlot - scrollDelta) % HOTBAR_SLOT_COUNT + HOTBAR_SLOT_COUNT) % HOTBAR_SLOT_COUNT;
    inv->selectedHotbarSlot = next;
}

ItemStack* Inventory_GetActiveItem(PlayerInventory* inv) {
    if (!inv) return NULL;
    return &inv->slots[inv->selectedHotbarSlot];
}

const ItemStack* Inventory_GetActiveItemConst(const PlayerInventory* inv) {
    if (!inv) return NULL;
    return &inv->slots[inv->selectedHotbarSlot];
}

bool Inventory_DecrementActiveItem(PlayerInventory* inv, uint8_t amount) {
    if (!inv) return false;
    ItemStack* active = &inv->slots[inv->selectedHotbarSlot];
    if (ItemStack_IsEmpty(active) || active->count < amount) {
        return false;
    }
    active->count -= amount;
    if (active->count == 0) {
        ItemStack_Clear(active);
    }
    return true;
}

int Inventory_AddItem(PlayerInventory* inv, const ItemStack* item) {
    if (!inv || ItemStack_IsEmpty(item)) return 0;

    int rem = (int)item->count;
    uint8_t maxStk = item->maxStack > 0 ? item->maxStack : Item_GetDefaultMaxStack(item->itemId);

    // 1. Fill existing matching stacks (hotbar first, then main)
    if (maxStk > 1) {
        for (int i = 0; i < HOTBAR_SLOT_COUNT + MAIN_SLOT_COUNT; i++) {
            ItemStack* slot = &inv->slots[i];
            if (slot->itemId == item->itemId && slot->count < maxStk && slot->durability == item->durability) {
                int space = (int)maxStk - (int)slot->count;
                int toAdd = (rem < space) ? rem : space;
                slot->count += (uint8_t)toAdd;
                rem -= toAdd;
                if (rem == 0) return 0;
            }
        }
    }

    // 2. Fill first empty slot (hotbar first, then main)
    for (int i = 0; i < HOTBAR_SLOT_COUNT + MAIN_SLOT_COUNT; i++) {
        ItemStack* slot = &inv->slots[i];
        if (ItemStack_IsEmpty(slot)) {
            int toAdd = (rem < (int)maxStk) ? rem : (int)maxStk;
            slot->itemId = item->itemId;
            slot->count = (uint8_t)toAdd;
            slot->maxStack = maxStk;
            slot->durability = item->durability;
            rem -= toAdd;
            if (rem == 0) return 0;
        }
    }

    return rem;
}

void Inventory_MouseClickSlot(PlayerInventory* inv, int slotIndex, bool isRightClick) {
    if (!inv || slotIndex < 0 || slotIndex >= TOTAL_SLOT_COUNT) return;
    ItemStack* slot = &inv->slots[slotIndex];

    if (!isRightClick) {
        // Left Click: Pickup, Place, or Swap
        if (ItemStack_IsEmpty(&inv->cursorItem)) {
            if (!ItemStack_IsEmpty(slot)) {
                inv->cursorItem = *slot;
                ItemStack_Clear(slot);
            }
        } else {
            if (ItemStack_IsEmpty(slot)) {
                *slot = inv->cursorItem;
                ItemStack_Clear(&inv->cursorItem);
            } else if (slot->itemId == inv->cursorItem.itemId && slot->maxStack > 1 && slot->durability == inv->cursorItem.durability) {
                int space = (int)slot->maxStack - (int)slot->count;
                int toAdd = ((int)inv->cursorItem.count < space) ? (int)inv->cursorItem.count : space;
                slot->count += (uint8_t)toAdd;
                inv->cursorItem.count -= (uint8_t)toAdd;
                if (inv->cursorItem.count == 0) {
                    ItemStack_Clear(&inv->cursorItem);
                }
            } else {
                // Swap
                ItemStack temp = *slot;
                *slot = inv->cursorItem;
                inv->cursorItem = temp;
            }
        }
    } else {
        // Right Click: Place single item or split slot
        if (ItemStack_IsEmpty(&inv->cursorItem)) {
            if (!ItemStack_IsEmpty(slot)) {
                // Pick up ceil(count / 2)
                uint8_t half = (slot->count + 1) / 2;
                uint8_t rem = slot->count - half;

                inv->cursorItem.itemId = slot->itemId;
                inv->cursorItem.count = half;
                inv->cursorItem.maxStack = slot->maxStack;
                inv->cursorItem.durability = slot->durability;

                slot->count = rem;
                if (slot->count == 0) {
                    ItemStack_Clear(slot);
                }
            }
        } else {
            // Place 1 item from cursor into slot
            if (ItemStack_IsEmpty(slot)) {
                slot->itemId = inv->cursorItem.itemId;
                slot->count = 1;
                slot->maxStack = inv->cursorItem.maxStack;
                slot->durability = inv->cursorItem.durability;
                inv->cursorItem.count--;
                if (inv->cursorItem.count == 0) {
                    ItemStack_Clear(&inv->cursorItem);
                }
            } else if (slot->itemId == inv->cursorItem.itemId && slot->count < slot->maxStack && slot->durability == inv->cursorItem.durability) {
                slot->count++;
                inv->cursorItem.count--;
                if (inv->cursorItem.count == 0) {
                    ItemStack_Clear(&inv->cursorItem);
                }
            }
        }
    }
}

void Inventory_ShiftClickSlot(PlayerInventory* inv, int slotIndex) {
    if (!inv || slotIndex < 0 || slotIndex >= TOTAL_SLOT_COUNT) return;
    ItemStack* slot = &inv->slots[slotIndex];
    if (ItemStack_IsEmpty(slot)) return;

    int targetStart = (slotIndex < HOTBAR_SLOT_COUNT) ? MAIN_START_INDEX : HOTBAR_START_INDEX;
    int targetCount = (slotIndex < HOTBAR_SLOT_COUNT) ? MAIN_SLOT_COUNT : HOTBAR_SLOT_COUNT;
    int targetEnd = targetStart + targetCount;

    // 1. Try to merge with existing matching stacks
    int rem = (int)slot->count;
    if (slot->maxStack > 1) {
        for (int i = targetStart; i < targetEnd; i++) {
            ItemStack* dest = &inv->slots[i];
            if (dest->itemId == slot->itemId && dest->count < dest->maxStack && dest->durability == slot->durability) {
                int space = (int)dest->maxStack - (int)dest->count;
                int toAdd = (rem < space) ? rem : space;
                dest->count += (uint8_t)toAdd;
                rem -= toAdd;
                if (rem == 0) {
                    ItemStack_Clear(slot);
                    return;
                }
            }
        }
    }

    // 2. Find first empty slot in target range
    for (int i = targetStart; i < targetEnd; i++) {
        ItemStack* dest = &inv->slots[i];
        if (ItemStack_IsEmpty(dest)) {
            dest->itemId = slot->itemId;
            dest->count = (uint8_t)rem;
            dest->maxStack = slot->maxStack;
            dest->durability = slot->durability;
            ItemStack_Clear(slot);
            return;
        }
    }

    slot->count = (uint8_t)rem;
}

/* ============================================================================
 * Crafting Engine API Implementation
 * ============================================================================ */

ItemStack Crafting_Match(const ItemStack grid[3][3], int gridSize) {
    ItemStack result;
    ItemStack_Clear(&result);

    if (!grid || gridSize < 2 || gridSize > 3) {
        return result;
    }

    int minR = gridSize, maxR = -1;
    int minC = gridSize, maxC = -1;
    uint8_t nonNullItems[9];
    int nonNullCount = 0;

    for (int r = 0; r < gridSize; r++) {
        for (int c = 0; c < gridSize; c++) {
            if (!ItemStack_IsEmpty(&grid[r][c])) {
                if (r < minR) minR = r;
                if (r > maxR) maxR = r;
                if (c < minC) minC = c;
                if (c > maxC) maxC = c;
                nonNullItems[nonNullCount++] = grid[r][c].itemId;
            }
        }
    }

    if (nonNullCount == 0) {
        return result;
    }

    /* 1. Shapeless recipe: 1 Wood Log -> 4 Wood Planks */
    if (nonNullCount == 1 && nonNullItems[0] == ITEM_WOOD_LOG) {
        result.itemId = ITEM_WOOD_PLANKS;
        result.count = 4;
        result.maxStack = DEFAULT_MAX_STACK_BLOCK;
        result.durability = 0;
        return result;
    }

    /* 2. Shapeless recipe: 1 Coal + 1 Stick -> 4 Torches */
    if (nonNullCount == 2) {
        if ((nonNullItems[0] == ITEM_COAL && nonNullItems[1] == ITEM_STICK) ||
            (nonNullItems[0] == ITEM_STICK && nonNullItems[1] == ITEM_COAL)) {
            result.itemId = ITEM_TORCH;
            result.count = 4;
            result.maxStack = DEFAULT_MAX_STACK_BLOCK;
            result.durability = 0;
            return result;
        }
    }

    int subH = maxR - minR + 1;
    int subW = maxC - minC + 1;

    /* 3. Shaped recipe: 2 Wood Planks vertically (1x2) -> 4 Sticks */
    if (subH == 2 && subW == 1) {
        if (grid[minR][minC].itemId == ITEM_WOOD_PLANKS &&
            grid[minR + 1][minC].itemId == ITEM_WOOD_PLANKS &&
            nonNullCount == 2) {
            result.itemId = ITEM_STICK;
            result.count = 4;
            result.maxStack = DEFAULT_MAX_STACK_BLOCK;
            result.durability = 0;
            return result;
        }
    }

    /* 4. Shaped recipe: 4 Wood Planks (2x2) -> 1 Crafting Table */
    if (subH == 2 && subW == 2 && nonNullCount == 4) {
        if (grid[minR][minC].itemId == ITEM_WOOD_PLANKS &&
            grid[minR][minC + 1].itemId == ITEM_WOOD_PLANKS &&
            grid[minR + 1][minC].itemId == ITEM_WOOD_PLANKS &&
            grid[minR + 1][minC + 1].itemId == ITEM_WOOD_PLANKS) {
            result.itemId = ITEM_CRAFTING_TABLE;
            result.count = 1;
            result.maxStack = DEFAULT_MAX_STACK_BLOCK;
            result.durability = 0;
            return result;
        }
    }

    /* 5. Shaped recipes: 3x3 Pickaxes */
    if (subH == 3 && subW == 3 && nonNullCount == 5) {
        uint8_t top0 = grid[minR][minC].itemId;
        uint8_t top1 = grid[minR][minC + 1].itemId;
        uint8_t top2 = grid[minR][minC + 2].itemId;
        uint8_t mid0 = grid[minR + 1][minC].itemId;
        uint8_t mid1 = grid[minR + 1][minC + 1].itemId;
        uint8_t mid2 = grid[minR + 1][minC + 2].itemId;
        uint8_t bot0 = grid[minR + 2][minC].itemId;
        uint8_t bot1 = grid[minR + 2][minC + 1].itemId;
        uint8_t bot2 = grid[minR + 2][minC + 2].itemId;

        if (mid0 == ITEM_AIR && mid2 == ITEM_AIR &&
            bot0 == ITEM_AIR && bot2 == ITEM_AIR &&
            mid1 == ITEM_STICK && bot1 == ITEM_STICK &&
            top0 == top1 && top1 == top2) {

            if (top0 == ITEM_WOOD_PLANKS) {
                result.itemId = ITEM_WOODEN_PICKAXE;
                result.count = 1;
                result.maxStack = DEFAULT_MAX_STACK_TOOL;
                result.durability = Item_GetDefaultDurability(ITEM_WOODEN_PICKAXE);
                return result;
            } else if (top0 == ITEM_COBBLESTONE) {
                result.itemId = ITEM_STONE_PICKAXE;
                result.count = 1;
                result.maxStack = DEFAULT_MAX_STACK_TOOL;
                result.durability = Item_GetDefaultDurability(ITEM_STONE_PICKAXE);
                return result;
            } else if (top0 == ITEM_IRON_INGOT) {
                result.itemId = ITEM_IRON_PICKAXE;
                result.count = 1;
                result.maxStack = DEFAULT_MAX_STACK_TOOL;
                result.durability = Item_GetDefaultDurability(ITEM_IRON_PICKAXE);
                return result;
            }
        }
    }

    /* 6. Shaped recipe: 8 Cobblestone ring (3x3) -> 1 Furnace */
    if (subH == 3 && subW == 3 && nonNullCount == 8) {
        bool isFurnace = true;
        for (int r = 0; r < 3; r++) {
            for (int c = 0; c < 3; c++) {
                if (r == 1 && c == 1) {
                    if (grid[minR + r][minC + c].itemId != ITEM_AIR) isFurnace = false;
                } else {
                    if (grid[minR + r][minC + c].itemId != ITEM_COBBLESTONE) isFurnace = false;
                }
            }
        }
        if (isFurnace) {
            result.itemId = ITEM_FURNACE;
            result.count = 1;
            result.maxStack = DEFAULT_MAX_STACK_BLOCK;
            result.durability = 0;
            return result;
        }
    }

    return result;
}

ItemStack Crafting_Craft(ItemStack grid[3][3], int gridSize) {
    ItemStack result = Crafting_Match((const ItemStack (*)[3])grid, gridSize);
    if (!ItemStack_IsEmpty(&result)) {
        for (int r = 0; r < gridSize; r++) {
            for (int c = 0; c < gridSize; c++) {
                if (!ItemStack_IsEmpty(&grid[r][c])) {
                    grid[r][c].count--;
                    if (grid[r][c].count == 0) {
                        ItemStack_Clear(&grid[r][c]);
                    }
                }
            }
        }
    }
    return result;
}
