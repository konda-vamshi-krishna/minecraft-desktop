"""
Tier 1: 2x2 and 3x3 Crafting Engine Tests.
Verifies canonical recipe catalog, translation-invariant shaped matching,
order-independent shapeless matching, and ingredient decrement.
"""

import unittest
from tests.canonical_models import CraftingEngine, ItemStack, ItemID


class TestCraftingEngine(unittest.TestCase):

    def setUp(self):
        self.engine = CraftingEngine()

    def test_01_shapeless_log_to_planks(self):
        """Verify 1 Wood Log in any slot of 2x2 grid crafts 4 Wood Planks."""
        # Slot (0, 0)
        grid1 = [[ItemStack(ItemID.WOOD_LOG, 1), ItemStack()],
                 [ItemStack(), ItemStack()]]
        res1 = self.engine.match(grid1)
        self.assertIsNotNone(res1)
        self.assertEqual(res1.item_id, ItemID.WOOD_PLANKS)
        self.assertEqual(res1.count, 4)

        # Slot (1, 1)
        grid2 = [[ItemStack(), ItemStack()],
                 [ItemStack(), ItemStack(ItemID.WOOD_LOG, 1)]]
        res2 = self.engine.match(grid2)
        self.assertIsNotNone(res2)
        self.assertEqual(res2.item_id, ItemID.WOOD_PLANKS)
        self.assertEqual(res2.count, 4)

    def test_02_shaped_sticks_translation_invariance(self):
        """Verify 2 vertical planks craft 4 sticks regardless of column offset in 2x2 or 3x3."""
        # 2x2 left column
        grid_2x2_left = [[ItemStack(ItemID.WOOD_PLANKS, 1), ItemStack()],
                         [ItemStack(ItemID.WOOD_PLANKS, 1), ItemStack()]]
        res_left = self.engine.match(grid_2x2_left)
        self.assertIsNotNone(res_left)
        self.assertEqual(res_left.item_id, ItemID.STICK)
        self.assertEqual(res_left.count, 4)

        # 2x2 right column
        grid_2x2_right = [[ItemStack(), ItemStack(ItemID.WOOD_PLANKS, 1)],
                          [ItemStack(), ItemStack(ItemID.WOOD_PLANKS, 1)]]
        res_right = self.engine.match(grid_2x2_right)
        self.assertIsNotNone(res_right)
        self.assertEqual(res_right.item_id, ItemID.STICK)
        self.assertEqual(res_right.count, 4)

        # 3x3 right column (r: 1..2, c: 2)
        grid_3x3 = [[ItemStack(), ItemStack(), ItemStack()],
                    [ItemStack(), ItemStack(), ItemStack(ItemID.WOOD_PLANKS, 1)],
                    [ItemStack(), ItemStack(), ItemStack(ItemID.WOOD_PLANKS, 1)]]
        res_3x3 = self.engine.match(grid_3x3)
        self.assertIsNotNone(res_3x3)
        self.assertEqual(res_3x3.item_id, ItemID.STICK)
        self.assertEqual(res_3x3.count, 4)

    def test_03_crafting_table_2x2_and_furnace_3x3(self):
        """Verify 4 planks -> 1 Crafting Table (2x2) and 8 cobblestone ring -> 1 Furnace (3x3)."""
        # Crafting table
        table_grid = [[ItemStack(ItemID.WOOD_PLANKS, 1), ItemStack(ItemID.WOOD_PLANKS, 1)],
                      [ItemStack(ItemID.WOOD_PLANKS, 1), ItemStack(ItemID.WOOD_PLANKS, 1)]]
        table_res = self.engine.match(table_grid)
        self.assertIsNotNone(table_res)
        self.assertEqual(table_res.item_id, ItemID.CRAFTING_TABLE)
        self.assertEqual(table_res.count, 1)

        # Furnace: hollow ring of 8 cobble
        furnace_grid = [
            [ItemStack(ItemID.COBBLESTONE, 1), ItemStack(ItemID.COBBLESTONE, 1), ItemStack(ItemID.COBBLESTONE, 1)],
            [ItemStack(ItemID.COBBLESTONE, 1), ItemStack(),                      ItemStack(ItemID.COBBLESTONE, 1)],
            [ItemStack(ItemID.COBBLESTONE, 1), ItemStack(ItemID.COBBLESTONE, 1), ItemStack(ItemID.COBBLESTONE, 1)]
        ]
        furnace_res = self.engine.match(furnace_grid)
        self.assertIsNotNone(furnace_res)
        self.assertEqual(furnace_res.item_id, ItemID.FURNACE)
        self.assertEqual(furnace_res.count, 1)

    def test_04_tools_recipes_pickaxes_durability(self):
        """Verify wooden, stone, and iron pickaxe recipes with canonical durability (59, 131, 250)."""
        def make_pickaxe_grid(material_id):
            return [
                [ItemStack(material_id, 1), ItemStack(material_id, 1), ItemStack(material_id, 1)],
                [ItemStack(), ItemStack(ItemID.STICK, 1), ItemStack()],
                [ItemStack(), ItemStack(ItemID.STICK, 1), ItemStack()]
            ]

        wood_res = self.engine.match(make_pickaxe_grid(ItemID.WOOD_PLANKS))
        self.assertIsNotNone(wood_res)
        self.assertEqual(wood_res.item_id, ItemID.WOODEN_PICKAXE)
        self.assertEqual(wood_res.durability, 59)
        self.assertEqual(wood_res.max_stack, 1)

        stone_res = self.engine.match(make_pickaxe_grid(ItemID.COBBLESTONE))
        self.assertIsNotNone(stone_res)
        self.assertEqual(stone_res.item_id, ItemID.STONE_PICKAXE)
        self.assertEqual(stone_res.durability, 131)

        iron_res = self.engine.match(make_pickaxe_grid(ItemID.IRON_INGOT))
        self.assertIsNotNone(iron_res)
        self.assertEqual(iron_res.item_id, ItemID.IRON_PICKAXE)
        self.assertEqual(iron_res.durability, 250)

    def test_05_craft_action_ingredient_consumption(self):
        """Verify executing craft() decrements each ingredient by exactly 1 and clears exhausted slots."""
        grid = [
            [ItemStack(ItemID.WOOD_PLANKS, 3), ItemStack(ItemID.WOOD_PLANKS, 1)],
            [ItemStack(ItemID.WOOD_PLANKS, 2), ItemStack(ItemID.WOOD_PLANKS, 1)]
        ]
        crafted_item = self.engine.craft(grid)
        self.assertIsNotNone(crafted_item)
        self.assertEqual(crafted_item.item_id, ItemID.CRAFTING_TABLE)

        # Slot (0, 0): had 3, now 2
        self.assertEqual(grid[0][0].count, 2)
        # Slot (0, 1): had 1, now empty
        self.assertTrue(grid[0][1].is_empty())
        # Slot (1, 0): had 2, now 1
        self.assertEqual(grid[1][0].count, 1)
        # Slot (1, 1): had 1, now empty
        self.assertTrue(grid[1][1].is_empty())

    def test_06_invalid_recipes_return_none(self):
        """Verify non-matching or distorted patterns reject crafting."""
        # 3 planks in a row in 3x3 without sticks -> No recipe
        grid = [
            [ItemStack(ItemID.WOOD_PLANKS, 1), ItemStack(ItemID.WOOD_PLANKS, 1), ItemStack(ItemID.WOOD_PLANKS, 1)],
            [ItemStack(), ItemStack(), ItemStack()],
            [ItemStack(), ItemStack(), ItemStack()]
        ]
        self.assertIsNone(self.engine.match(grid))


if __name__ == '__main__':
    unittest.main()
