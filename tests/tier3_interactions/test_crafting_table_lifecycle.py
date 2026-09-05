"""
Tier 3: Pairwise Cross-Feature Test — Crafting Table Lifecycle & Orphan Remainder Retention.
Verifies right-click interaction opening 3x3 grid, recipe crafting, ingredient consumption,
and returning leftover grid items to player inventory (or ground drops on full inventory) upon closing.
"""

import unittest
from tests.canonical_models import (
    CraftingEngine, InventoryModel, ItemStack, ItemID
)


class CraftingTableSession:
    def __init__(self, player_inv: InventoryModel):
        self.player_inv = player_inv
        self.engine = CraftingEngine()
        self.grid = [[ItemStack() for _ in range(3)] for _ in range(3)]
        self.is_open = True
        self.dropped_entities = []

    def set_slot(self, r: int, c: int, item: ItemStack):
        self.grid[r][c] = item

    def get_output(self) -> ItemStack:
        return self.engine.match(self.grid)

    def take_output(self) -> ItemStack:
        product = self.engine.craft(self.grid)
        return product

    def close(self):
        """When closing the crafting table, all leftover items in 3x3 grid must return to player inventory."""
        self.is_open = False
        for r in range(3):
            for c in range(3):
                item = self.grid[r][c]
                if not item.is_empty():
                    rem = self.player_inv.add_item(item)
                    if rem > 0:
                        # Overflow drops on ground
                        self.dropped_entities.append(ItemStack(item.item_id, rem, item.max_stack))
                    self.grid[r][c] = ItemStack()


class TestCraftingTableLifecycle(unittest.TestCase):

    def setUp(self):
        self.inv = InventoryModel()
        self.session = CraftingTableSession(self.inv)

    def test_01_open_table_3x3_grid_initial_state(self):
        """Verify opening crafting table initializes empty 3x3 matrix."""
        self.assertTrue(self.session.is_open)
        for r in range(3):
            for c in range(3):
                self.assertTrue(self.session.grid[r][c].is_empty())
        self.assertIsNone(self.session.get_output())

    def test_02_recipe_matching_furnace(self):
        """Verify populating 8 cobblestone around outer border detects Furnace in output slot."""
        for r in range(3):
            for c in range(3):
                if not (r == 1 and c == 1):
                    self.session.set_slot(r, c, ItemStack(ItemID.COBBLESTONE, 1))

        output = self.session.get_output()
        self.assertIsNotNone(output)
        self.assertEqual(output.item_id, ItemID.FURNACE)
        self.assertEqual(output.count, 1)

    def test_03_take_output_consumes_ingredients(self):
        """Verify taking crafted output decrements each ingredient slot by exactly 1."""
        # Arrange 8 cobblestone stacks of 5 each
        for r in range(3):
            for c in range(3):
                if not (r == 1 and c == 1):
                    self.session.set_slot(r, c, ItemStack(ItemID.COBBLESTONE, 5))

        product = self.session.take_output()
        self.assertEqual(product.item_id, ItemID.FURNACE)
        self.assertEqual(product.count, 1)

        # Each ingredient slot now has 4
        for r in range(3):
            for c in range(3):
                if not (r == 1 and c == 1):
                    self.assertEqual(self.session.grid[r][c].count, 4)

    def test_04_closing_table_returns_orphan_items_to_inventory(self):
        """Verify closing crafting table returns all remaining items in 3x3 grid to player inventory."""
        # Place 3 wood planks in grid
        self.session.set_slot(0, 0, ItemStack(ItemID.WOOD_PLANKS, 3))
        self.session.set_slot(1, 1, ItemStack(ItemID.STICK, 2))

        # Close session
        self.session.close()
        self.assertFalse(self.session.is_open)

        # Verify grid is empty
        for r in range(3):
            for c in range(3):
                self.assertTrue(self.session.grid[r][c].is_empty())

        # Verify items returned into player inventory
        self.assertEqual(self.inv.slots[0].item_id, ItemID.WOOD_PLANKS)
        self.assertEqual(self.inv.slots[0].count, 3)
        self.assertEqual(self.inv.slots[1].item_id, ItemID.STICK)
        self.assertEqual(self.inv.slots[1].count, 2)
        self.assertEqual(len(self.session.dropped_entities), 0)

    def test_05_overflow_drops_on_ground_when_inventory_full(self):
        """Verify if player inventory is full upon close, remaining items drop on ground without vanishing."""
        # Fill all 36 player slots
        for i in range(36):
            self.inv.slots[i] = ItemStack(ItemID.STONE, 64)

        # Place 10 iron ingots in crafting grid
        self.session.set_slot(0, 0, ItemStack(ItemID.IRON_INGOT, 10))

        # Close session
        self.session.close()

        # Item could not fit into inventory -> must be in dropped_entities
        self.assertEqual(len(self.session.dropped_entities), 1)
        self.assertEqual(self.session.dropped_entities[0].item_id, ItemID.IRON_INGOT)
        self.assertEqual(self.session.dropped_entities[0].count, 10)


if __name__ == '__main__':
    unittest.main()
