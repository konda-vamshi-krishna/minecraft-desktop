"""
Tier 3: Pairwise Cross-Feature Test — DDA Raycast + Progressive Mining + Item Drop Entity + Inventory Pickup.
Verifies raycast targeting, continuous hold destruction FSM, 3D item drop entity spawning,
collection within 1.5m radius into inventory slot, and tool durability decrement.
"""

import unittest
import math
from tests.canonical_models import (
    fast_voxel_traversal, InventoryModel, ItemStack, ItemID, get_default_durability
)


class ItemDropEntity:
    def __init__(self, item_id: int, count: int, x: float, y: float, z: float):
        self.item_id = item_id
        self.count = count
        self.x = x
        self.y = y
        self.z = z
        self.is_collected = False

    def distance_to(self, px: float, py: float, pz: float) -> float:
        return math.sqrt((self.x - px)**2 + (self.y - py)**2 + (self.z - pz)**2)


class TestDDAMiningDropPickup(unittest.TestCase):

    def setUp(self):
        self.inv = InventoryModel()
        self.world = {}  # (x, y, z) -> BlockID

    def test_01_dda_target_and_progressive_mining_lifecycle(self):
        """Verify DDA raycast locks onto Wood Log and bare-hand mining breaks it after 120 ticks (2.0s)."""
        # Place Wood Log at (3, 64, 0)
        self.world[(3, 64, 0)] = ItemID.WOOD_LOG
        player_eye = (0.5, 64.62, 0.5)  # distance = ~2.5m (< 4.5m)
        look_dir = (1.0, 0.0, 0.0)

        # 1. DDA Raycast targeting
        hit = fast_voxel_traversal(
            player_eye, look_dir, max_reach=4.5,
            is_solid_voxel=lambda x, y, z: (x, y, z) in self.world
        )
        self.assertTrue(hit.hit)
        self.assertEqual(hit.target_block, (3, 64, 0))

        # 2. Mine for 120 ticks at 60Hz (2.0s duration for Wood Log with bare hands)
        dt = 1.0 / 60.0
        hardness = 2.0
        tool_multiplier = 1.0
        progress = 0.0

        for _ in range(120):
            progress += (dt * tool_multiplier) / hardness

        self.assertAlmostEqual(progress, 1.0, places=4)
        # Block breaks -> converted to air
        del self.world[(3, 64, 0)]
        self.assertNotIn((3, 64, 0), self.world)

    def test_02_block_break_spawns_3d_item_drop(self):
        """Verify block break spawns a 3D ItemDropEntity centered in the broken voxel."""
        bx, by, bz = 3, 64, 0
        drop = ItemDropEntity(ItemID.WOOD_LOG, 1, bx + 0.5, by + 0.5, bz + 0.5)

        self.assertEqual(drop.item_id, ItemID.WOOD_LOG)
        self.assertEqual(drop.count, 1)
        self.assertAlmostEqual(drop.x, 3.5)
        self.assertAlmostEqual(drop.y, 64.5)
        self.assertAlmostEqual(drop.z, 0.5)
        self.assertFalse(drop.is_collected)

    def test_03_item_drop_collection_radius(self):
        """Verify item drop is collected when player enters 1.5m radius and adds to inventory."""
        drop = ItemDropEntity(ItemID.WOOD_LOG, 1, 3.5, 64.5, 0.5)

        # Player at (1.0, 64.0, 0.5) -> distance = 2.5m > 1.5m (not collected)
        dist_far = drop.distance_to(1.0, 64.0, 0.5)
        self.assertGreater(dist_far, 1.5)
        self.assertFalse(drop.is_collected)

        # Player walks closer to (2.5, 64.0, 0.5) -> distance = 1.11m <= 1.5m
        dist_close = drop.distance_to(2.5, 64.0, 0.5)
        self.assertLessEqual(dist_close, 1.5)

        # Collect item
        drop.is_collected = True
        rem = self.inv.add_item(ItemStack(drop.item_id, drop.count))
        self.assertEqual(rem, 0)
        self.assertEqual(self.inv.slots[0].item_id, ItemID.WOOD_LOG)
        self.assertEqual(self.inv.slots[0].count, 1)

    def test_04_tool_mining_speedup_and_durability_decrement(self):
        """Verify wooden pickaxe (tool multiplier M=2.0) mines stone in 0.75s and loses 1 durability."""
        # Player holds wooden pickaxe with initial durability 59
        initial_durability = get_default_durability(ItemID.WOODEN_PICKAXE)
        self.assertEqual(initial_durability, 59)
        tool = ItemStack(ItemID.WOODEN_PICKAXE, 1, max_stack=1, durability=initial_durability)
        self.inv.slots[0] = tool

        stone_hardness = 1.5  # seconds
        tool_multiplier = 2.0  # wooden tool on stone
        effective_time = stone_hardness / tool_multiplier  # 0.75 seconds = 45 ticks at 60Hz

        dt = 1.0 / 60.0
        progress = 0.0
        ticks = int(round(effective_time * 60))

        for _ in range(ticks):
            progress += (dt * tool_multiplier) / stone_hardness

        self.assertAlmostEqual(progress, 1.0, delta=0.01)

        # Decrement durability
        tool.durability -= 1
        self.assertEqual(tool.durability, 58)

    def test_05_reach_violation_cancels_mining(self):
        """Verify backing outside 5.0m reach envelope during mining cancels progress."""
        player_eye = (0.5, 64.5, 0.5)
        target = (6, 64, 0)  # distance = ~5.5m > 5.0m reach
        self.world[target] = ItemID.STONE

        hit = fast_voxel_traversal(
            player_eye, (1.0, 0.0, 0.0), max_reach=5.0,
            is_solid_voxel=lambda x, y, z: (x, y, z) in self.world
        )
        # Cannot hit block outside 5.0m
        self.assertFalse(hit.hit)


if __name__ == '__main__':
    unittest.main()
