/**
 * @file proposed_inventory.h
 * @brief 9-Slot Hotbar & 41-Slot Player Inventory State Machine.
 *
 * Implements canonical inventory layout (9 hotbar + 27 main + 4 armor + 1 offhand),
 * stack size boundaries (64/16/1), key/mouse-wheel hotbar selection with positive modulo wrap,
 * mouse click interactions (pickup, place, swap, split), and shift-click quick transfers.
 *
 * Adheres strictly to C99 and Ponytail minimal-complexity principles:
 * - Zero dynamic heap allocations (pure contiguous value structs).
 * - Cache-friendly contiguous flat memory layout.
 */

#ifndef MINECRAFT_GAMEPLAY_INVENTORY_H
#define MINECRAFT_GAMEPLAY_INVENTORY_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include "../world/world.h"

#ifdef __cplusplus
extern "C" {
#endif

// =============================================================================
// Inventory Dimension Constants (Canonical Minecraft Architecture)
// =============================================================================
#define HOTBAR_SLOT_COUNT       9
#define MAIN_SLOT_COUNT         27
#define ARMOR_SLOT_COUNT        4
#define OFFHAND_SLOT_COUNT      1
#define TOTAL_SLOT_COUNT        (HOTBAR_SLOT_COUNT + MAIN_SLOT_COUNT + ARMOR_SLOT_COUNT + OFFHAND_SLOT_COUNT) // 41

#define HOTBAR_START_INDEX      0
#define MAIN_START_INDEX        9
#define ARMOR_START_INDEX       36
#define OFFHAND_START_INDEX     40

#define DEFAULT_MAX_STACK_BLOCK   64
#define DEFAULT_MAX_STACK_COMPACT 16
#define DEFAULT_MAX_STACK_TOOL    1

// ponytail: [41-slot fixed contiguous array] -> [container interface for chests/furnaces/crafting]

// =============================================================================
// Canonical Item ID Palette (docs/02 §6 & canonical_models.py)
// =============================================================================
typedef enum ItemID {
    ITEM_AIR            = 0,
    ITEM_STONE          = 1,
    ITEM_DIRT           = 2,
    ITEM_GRASS_BLOCK    = 3,
    ITEM_COBBLESTONE    = 4,
    ITEM_WOOD_LOG       = 5,
    ITEM_WOOD_PLANKS    = 6,
    ITEM_STICK          = 7,
    ITEM_CRAFTING_TABLE = 8,
    ITEM_FURNACE        = 9,
    ITEM_COAL           = 10,
    ITEM_TORCH          = 11,
    ITEM_WOODEN_PICKAXE = 12,
    ITEM_STONE_PICKAXE  = 13,
    ITEM_IRON_PICKAXE   = 14,
    ITEM_IRON_INGOT     = 15,
    ITEM_BEDROCK        = 16,
    ITEM_SAND           = 17,
    ITEM_SANDSTONE      = 18,
    ITEM_SNOW           = 19,
    ITEM_LEAVES         = 20,
    ITEM_CACTUS         = 21,
    ITEM_FLOWER         = 22,
    ITEM_TALLGRASS      = 23,
    ITEM_COUNT
} ItemID;

// =============================================================================
// Item Stack Data Structure
// =============================================================================
typedef struct ItemStack {
    uint8_t itemId;       // ItemID enum or BlockID enum
    uint8_t count;        // 0 if empty
    uint8_t maxStack;     // Typically 64 for blocks, 1 for tools
    uint16_t durability;  // 0 for non-tools, remaining durability for tools
} ItemStack;

// =============================================================================
// Player Inventory State Machine
// =============================================================================
typedef struct PlayerInventory {
    ItemStack slots[TOTAL_SLOT_COUNT];  // 0..8: Hotbar, 9..35: Main, 36..39: Armor, 40: Offhand
    int selectedHotbarSlot;             // 0..8 active selection index
    ItemStack cursorItem;               // Stack currently picked up by mouse cursor
} PlayerInventory;

// =============================================================================
// Item & Tool Property Queries
// =============================================================================
uint8_t  Item_GetDefaultMaxStack(uint8_t itemId);
uint16_t Item_GetDefaultDurability(uint8_t itemId);
bool     Item_IsTool(uint8_t itemId);
bool     Item_IsPlaceableBlock(uint8_t itemId);
uint8_t  Item_ToBlockId(uint8_t itemId);
uint8_t  Block_ToItemId(uint8_t blockId);

// =============================================================================
// Item Stack Helpers
// =============================================================================
static inline bool ItemStack_IsEmpty(const ItemStack* stack) {
    return (stack == NULL) || (stack->itemId == ITEM_AIR) || (stack->count == 0);
}

static inline void ItemStack_Clear(ItemStack* stack) {
    if (stack != NULL) {
        stack->itemId = ITEM_AIR;
        stack->count = 0;
        stack->maxStack = DEFAULT_MAX_STACK_BLOCK;
        stack->durability = 0;
    }
}

static inline bool ItemStack_CanStackWith(const ItemStack* a, const ItemStack* b) {
    if (ItemStack_IsEmpty(a) || ItemStack_IsEmpty(b)) return true;
    return (a->itemId == b->itemId) &&
           (a->maxStack > 1) &&
           (b->maxStack > 1) &&
           (a->durability == b->durability);
}

// =============================================================================
// Inventory Management API
// =============================================================================
void       Inventory_Init(PlayerInventory* inv);
ItemStack* Inventory_GetSlot(PlayerInventory* inv, int slotIndex);
const ItemStack* Inventory_GetSlotConst(const PlayerInventory* inv, int slotIndex);

// Hotbar selection
void       Inventory_SelectHotbar(PlayerInventory* inv, int slotIndex);
void       Inventory_SelectHotbarKey(PlayerInventory* inv, int keyNumber); // 1..9
void       Inventory_ScrollHotbar(PlayerInventory* inv, int scrollDelta);
ItemStack* Inventory_GetActiveItem(PlayerInventory* inv);
const ItemStack* Inventory_GetActiveItemConst(const PlayerInventory* inv);
bool       Inventory_DecrementActiveItem(PlayerInventory* inv, uint8_t amount);

// Storage operations
int        Inventory_AddItem(PlayerInventory* inv, const ItemStack* item); // returns remaining count
void       Inventory_MouseClickSlot(PlayerInventory* inv, int slotIndex, bool isRightClick);
void       Inventory_ShiftClickSlot(PlayerInventory* inv, int slotIndex);

#ifdef __cplusplus
}
#endif

#endif // MINECRAFT_GAMEPLAY_INVENTORY_H
