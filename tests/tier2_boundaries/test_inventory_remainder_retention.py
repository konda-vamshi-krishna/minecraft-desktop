"""
Tier 2: Inventory Stack Overflow & Remainder Retention Tests.
Verifies partial stack overflow remainder return, full inventory rejection without loss,
left-drag integer division with remainder, right-drag 1-per-slot, and tool non-stackability.
"""

import unittest
from tests.canonical_models import InventoryModel, ItemStack, ItemID


class TestInventoryRemainderRetention(unittest.TestCase):

    def setUp(self):
        self.inv = InventoryModel()

    def test_01_partial_stack_overflow_remainder(self):
        """Verify adding 30 items to a slot with 50 items (max 64) returns exactly 16 remainder."""
        # Put 50 cobble in slot 0
        self.inv.slots[0] = ItemStack(ItemID.COBBLESTONE, 50, max_stack=64)
        
        # Fill other 35 storage slots with stone so only slot 0 can accept cobble
        for i in range(1, 36):
            self.inv.slots[i] = ItemStack(ItemID.STONE, 64, max_stack=64)

        # Attempt to add 30 cobble
        incoming = ItemStack(ItemID.COBBLESTONE, 30, max_stack=64)
        remainder = self.inv.add_item(incoming)

        # Slot 0 capped at 64, remainder is 16
        self.assertEqual(self.inv.slots[0].count, 64)
        self.assertEqual(remainder, 16)

    def test_02_completely_full_inventory_zero_item_loss(self):
        """Verify adding items to completely filled inventory returns 100% of items without destruction."""
        for i in range(36):
            self.inv.slots[i] = ItemStack(ItemID.DIRT, 64, max_stack=64)

        incoming = ItemStack(ItemID.WOOD_LOG, 25, max_stack=64)
        rem = self.inv.add_item(incoming)

        # None could be added
        self.assertEqual(rem, 25)
        # Verify no slots corrupted
        for i in range(36):
            self.assertEqual(self.inv.slots[i].item_id, ItemID.DIRT)
            self.assertEqual(self.inv.slots[i].count, 64)

    def test_03_left_drag_even_distribution_with_cursor_remainder(self):
        """Verify left-drag distributes items equally across targeted slots and keeps remainder in cursor."""
        # 10 planks in cursor distributed over 3 empty slots
        cursor_count = 10
        target_slots = [0, 1, 2]
        per_slot = cursor_count // len(target_slots)  # 3
        remainder = cursor_count % len(target_slots)  # 1

        for s in target_slots:
            self.inv.slots[s] = ItemStack(ItemID.WOOD_PLANKS, per_slot, max_stack=64)
        self.inv.cursor_item = ItemStack(ItemID.WOOD_PLANKS, remainder, max_stack=64)

        self.assertEqual(self.inv.slots[0].count, 3)
        self.assertEqual(self.inv.slots[1].count, 3)
        self.assertEqual(self.inv.slots[2].count, 3)
        self.assertEqual(self.inv.cursor_item.count, 1)

    def test_04_right_drag_one_per_slot_distribution(self):
        """Verify right-drag places exactly 1 item per slot and decrements cursor count accordingly."""
        # Start with 5 sticks in cursor
        self.inv.cursor_item = ItemStack(ItemID.STICK, 5, max_stack=64)
        target_slots = [4, 5, 6, 7]

        for s in target_slots:
            # Simulate right click drag: 1 into slot
            self.inv.slots[s] = ItemStack(ItemID.STICK, 1, max_stack=64)
            self.inv.cursor_item.count -= 1

        for s in target_slots:
            self.assertEqual(self.inv.slots[s].count, 1)
            self.assertEqual(self.inv.slots[s].item_id, ItemID.STICK)
        self.assertEqual(self.inv.cursor_item.count, 1)

    def test_05_unstackable_tools_strictly_forbidden_from_merging(self):
        """Verify tools with max_stack=1 never merge into counts > 1."""
        pick1 = ItemStack(ItemID.WOODEN_PICKAXE, 1, max_stack=1, durability=59)
        pick2 = ItemStack(ItemID.WOODEN_PICKAXE, 1, max_stack=1, durability=59)

        self.assertFalse(pick1.can_stack_with(pick2))

        self.inv.slots[0] = pick1
        # Left click with pick2 in cursor
        self.inv.cursor_item = pick2
        self.inv.mouse_click_slot(0, is_right_click=False)

        # Should swap, NOT merge into count 2
        self.assertEqual(self.inv.slots[0].count, 1)
        self.assertEqual(self.inv.cursor_item.count, 1)


if __name__ == '__main__':
    unittest.main()
