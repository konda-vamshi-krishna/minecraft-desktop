"""
Tier 1: 41-Slot Inventory System & State Machine Tests.
Verifies slot layout, hotbar scroll modulo, stack size limits,
mouse click slot interactions, and shift-click quick move.
"""

import unittest
from tests.canonical_models import InventoryModel, ItemStack, ItemID, get_default_max_stack


class TestInventorySystem(unittest.TestCase):

    def setUp(self):
        self.inv = InventoryModel()

    def test_01_contiguous_41_slot_layout(self):
        """Verify 41-slot layout: 9 hotbar + 27 main + 4 armor + 1 offhand."""
        self.assertEqual(len(self.inv.slots), 41)
        self.assertEqual(InventoryModel.HOTBAR_SIZE, 9)
        self.assertEqual(InventoryModel.MAIN_SIZE, 27)
        self.assertEqual(InventoryModel.ARMOR_SIZE, 4)
        self.assertEqual(InventoryModel.OFFHAND_SIZE, 1)

        # All slots start empty
        for slot in self.inv.slots:
            self.assertTrue(slot.is_empty())

    def test_02_hotbar_selection_and_scroll_wrap(self):
        """Verify 9-slot selection maps keys 1-9 and mouse scroll with modulo wrap."""
        self.assertEqual(self.inv.selected_hotbar_slot, 0)

        # Scroll right (scrollDelta = -1) -> slot 1
        self.inv.scroll_hotbar(-1)
        self.assertEqual(self.inv.selected_hotbar_slot, 1)

        # Direct selection of slot 8
        self.inv.select_hotbar(8)
        self.assertEqual(self.inv.selected_hotbar_slot, 8)

        # Scroll right from 8 wraps to 0
        self.inv.scroll_hotbar(-1)
        self.assertEqual(self.inv.selected_hotbar_slot, 0)

        # Scroll left from 0 wraps to 8
        self.inv.scroll_hotbar(1)
        self.assertEqual(self.inv.selected_hotbar_slot, 8)

    def test_03_stack_size_hierarchy(self):
        """Verify canonical stack limits: 64 (blocks), 16 (compact), 1 (tools)."""
        self.assertEqual(get_default_max_stack(ItemID.STONE), 64)
        self.assertEqual(get_default_max_stack(ItemID.DIRT), 64)
        self.assertEqual(get_default_max_stack(ItemID.WOOD_PLANKS), 64)
        self.assertEqual(get_default_max_stack(ItemID.WOODEN_PICKAXE), 1)
        self.assertEqual(get_default_max_stack(ItemID.IRON_PICKAXE), 1)

        # Adding 70 stone creates 1 stack of 64 and 1 stack of 6
        rem = self.inv.add_item(ItemStack(ItemID.STONE, 70, max_stack=64))
        self.assertEqual(rem, 0)
        self.assertEqual(self.inv.slots[0].count, 64)
        self.assertEqual(self.inv.slots[0].item_id, ItemID.STONE)
        self.assertEqual(self.inv.slots[1].count, 6)
        self.assertEqual(self.inv.slots[1].item_id, ItemID.STONE)

    def test_04_mouse_click_pickup_place_swap(self):
        """Verify left click pickups, places into empty slot, and swaps mismatched items."""
        # Put 32 dirt in slot 0, 16 stone in slot 1
        self.inv.slots[0] = ItemStack(ItemID.DIRT, 32, max_stack=64)
        self.inv.slots[1] = ItemStack(ItemID.STONE, 16, max_stack=64)

        # 1. Left click on slot 0 picks up 32 dirt into cursor
        self.inv.mouse_click_slot(0, is_right_click=False)
        self.assertTrue(self.inv.slots[0].is_empty())
        self.assertEqual(self.inv.cursor_item.item_id, ItemID.DIRT)
        self.assertEqual(self.inv.cursor_item.count, 32)

        # 2. Left click on slot 1 (contains stone) swaps dirt in cursor with stone in slot 1
        self.inv.mouse_click_slot(1, is_right_click=False)
        self.assertEqual(self.inv.slots[1].item_id, ItemID.DIRT)
        self.assertEqual(self.inv.slots[1].count, 32)
        self.assertEqual(self.inv.cursor_item.item_id, ItemID.STONE)
        self.assertEqual(self.inv.cursor_item.count, 16)

        # 3. Left click on empty slot 0 places the 16 stone
        self.inv.mouse_click_slot(0, is_right_click=False)
        self.assertEqual(self.inv.slots[0].item_id, ItemID.STONE)
        self.assertEqual(self.inv.slots[0].count, 16)
        self.assertTrue(self.inv.cursor_item.is_empty())

    def test_05_mouse_right_click_single_place_and_split(self):
        """Verify right click places 1 item from cursor or picks up half from slot."""
        # Slot 0 has 10 wood planks
        self.inv.slots[0] = ItemStack(ItemID.WOOD_PLANKS, 10, max_stack=64)

        # 1. Right click on slot 0 picks up half (5) into cursor
        self.inv.mouse_click_slot(0, is_right_click=True)
        self.assertEqual(self.inv.slots[0].count, 5)
        self.assertEqual(self.inv.cursor_item.item_id, ItemID.WOOD_PLANKS)
        self.assertEqual(self.inv.cursor_item.count, 5)

        # 2. Right click on empty slot 2 places 1 plank
        self.inv.mouse_click_slot(2, is_right_click=True)
        self.assertEqual(self.inv.slots[2].item_id, ItemID.WOOD_PLANKS)
        self.assertEqual(self.inv.slots[2].count, 1)
        self.assertEqual(self.inv.cursor_item.count, 4)

        # 3. Right click on slot 2 again adds 1 plank (total 2)
        self.inv.mouse_click_slot(2, is_right_click=True)
        self.assertEqual(self.inv.slots[2].count, 2)
        self.assertEqual(self.inv.cursor_item.count, 3)

    def test_06_shift_click_quick_move(self):
        """Verify shift-click moves item instantly between hotbar (0-8) and main storage (9-35)."""
        # Place 64 cobble in hotbar slot 3
        self.inv.slots[3] = ItemStack(ItemID.COBBLESTONE, 64, max_stack=64)

        # Shift click moves it to main storage (first empty is slot 9)
        self.inv.shift_click_slot(3)
        self.assertTrue(self.inv.slots[3].is_empty())
        self.assertEqual(self.inv.slots[9].item_id, ItemID.COBBLESTONE)
        self.assertEqual(self.inv.slots[9].count, 64)

        # Shift click slot 9 moves it back to hotbar slot 0
        self.inv.shift_click_slot(9)
        self.assertTrue(self.inv.slots[9].is_empty())
        self.assertEqual(self.inv.slots[0].item_id, ItemID.COBBLESTONE)
        self.assertEqual(self.inv.slots[0].count, 64)


if __name__ == '__main__':
    unittest.main()
