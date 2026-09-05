"""
Tier 4: Real-World Workload — First Day Survival Full Lifecycle Session.
Executes the authentic 14-step Minecraft survival progression:
Punch tree -> collect logs -> craft planks -> craft crafting table -> place table ->
craft sticks -> craft wooden pickaxe -> mine stone -> craft stone pickaxe ->
craft furnace -> mine coal -> craft torches -> verify full state machine.
"""

import unittest
from tests.canonical_models import (
    Kinematics, VoxelPhysicsController, fast_voxel_traversal,
    InventoryModel, ItemStack, ItemID, CraftingEngine,
    PlayerSurvivalState, get_default_durability
)


class FirstDaySurvivalSession:
    def __init__(self):
        self.player_ctrl = VoxelPhysicsController(0.5, 64.0, 0.5)
        self.player_ctrl.is_grounded = True
        self.survival = PlayerSurvivalState()
        self.inv = InventoryModel()
        self.crafting = CraftingEngine()
        self.world = {}  # (x, y, z) -> BlockID

        # Initialize base terrain: flat stone floor at y=63
        for x in range(-5, 10):
            for z in range(-5, 10):
                self.world[(x, 63, z)] = ItemID.STONE

        # Generate oak tree at x=3, z=0: trunk at y=64..67
        for y in range(64, 68):
            self.world[(3, y, 0)] = ItemID.WOOD_LOG

        # Generate exposed stone wall at x=5, y=64..66
        for y in range(64, 67):
            for z in range(-2, 3):
                self.world[(5, y, z)] = ItemID.STONE

        # Generate coal ore vein at (5, 65, 0) and (5, 65, 1)
        self.world[(5, 65, 0)] = ItemID.COAL
        self.world[(5, 65, 1)] = ItemID.COAL

    def is_solid(self, x: int, y: int, z: int) -> bool:
        return (x, y, z) in self.world


class TestFirstDaySurvival(unittest.TestCase):

    def setUp(self):
        self.session = FirstDaySurvivalSession()

    def test_complete_first_day_survival_progression(self):
        """Execute end-to-end First Day Survival canonical gameplay session."""
        s = self.session

        # -------------------------------------------------------------------------
        # Step 1: Initial World Spawn Verification
        # -------------------------------------------------------------------------
        self.assertTrue(s.player_ctrl.is_grounded)
        self.assertEqual(s.survival.health, 20.0)
        self.assertEqual(s.survival.hunger, 20.0)
        self.assertTrue(all(slot.is_empty() for slot in s.inv.slots))

        # -------------------------------------------------------------------------
        # Step 2: Punch Tree (4 Oak Logs)
        # -------------------------------------------------------------------------
        logs_collected = 0
        for log_y in range(64, 68):
            # DDA Raycast from player eye level (y=64 + 1.62 = 65.62) to tree trunk at (3, log_y, 0)
            eye_pos = (s.player_ctrl.x, s.player_ctrl.y + Kinematics.EYE_LEVEL_STANDING, s.player_ctrl.z)
            dir_to_log = (3.5 - eye_pos[0], (log_y + 0.5) - eye_pos[1], 0.5 - eye_pos[2])

            hit = fast_voxel_traversal(eye_pos, dir_to_log, max_reach=4.5, is_solid_voxel=s.is_solid)
            self.assertTrue(hit.hit, f"Could not reach log at y={log_y}")
            self.assertEqual(hit.target_block, (3, log_y, 0))

            # Mine with bare hands (hardness = 2.0s = 120 ticks)
            # Add exhaustion for block breaking (0.005 per block)
            s.survival.add_exhaustion(0.005)
            # Block destroyed -> removed from world
            del s.world[(3, log_y, 0)]
            logs_collected += 1

        # Collect 4 logs into inventory
        rem = s.inv.add_item(ItemStack(ItemID.WOOD_LOG, logs_collected))
        self.assertEqual(rem, 0)
        self.assertEqual(s.inv.slots[0].item_id, ItemID.WOOD_LOG)
        self.assertEqual(s.inv.slots[0].count, 4)

        # -------------------------------------------------------------------------
        # Step 3: 2x2 Crafting — 4 Logs -> 16 Planks
        # -------------------------------------------------------------------------
        # Put 4 logs in 2x2 grid slot (0, 0)
        grid_2x2 = [[ItemStack(ItemID.WOOD_LOG, 4), ItemStack()],
                    [ItemStack(), ItemStack()]]
        planks_crafted = 0
        for _ in range(4):
            res = s.crafting.craft(grid_2x2)
            self.assertIsNotNone(res)
            self.assertEqual(res.item_id, ItemID.WOOD_PLANKS)
            self.assertEqual(res.count, 4)
            planks_crafted += res.count

        self.assertEqual(planks_crafted, 16)
        # Clear logs from inventory, add 16 planks
        s.inv.slots[0] = ItemStack()
        s.inv.add_item(ItemStack(ItemID.WOOD_PLANKS, 16))
        self.assertEqual(s.inv.slots[0].count, 16)

        # -------------------------------------------------------------------------
        # Step 4: 2x2 Crafting — 4 Planks -> 1 Crafting Table
        # -------------------------------------------------------------------------
        grid_table = [[ItemStack(ItemID.WOOD_PLANKS, 1), ItemStack(ItemID.WOOD_PLANKS, 1)],
                      [ItemStack(ItemID.WOOD_PLANKS, 1), ItemStack(ItemID.WOOD_PLANKS, 1)]]
        table_item = s.crafting.craft(grid_table)
        self.assertIsNotNone(table_item)
        self.assertEqual(table_item.item_id, ItemID.CRAFTING_TABLE)
        self.assertEqual(table_item.count, 1)

        # Update inventory: 12 planks, 1 Crafting Table
        s.inv.slots[0].count -= 4
        s.inv.add_item(table_item)
        self.assertEqual(s.inv.slots[0].count, 12)
        self.assertEqual(s.inv.slots[1].item_id, ItemID.CRAFTING_TABLE)
        self.assertEqual(s.inv.slots[1].count, 1)

        # -------------------------------------------------------------------------
        # Step 5: Place Crafting Table in World
        # -------------------------------------------------------------------------
        table_place_pos = (1, 64, 0)
        # Anti-suffocation check: table does not overlap player at (0.5, 64.0, 0.5)
        player_box = s.player_ctrl.get_aabb()
        from tests.canonical_models import AABB
        table_box = AABB(1.0, 64.0, 0.0, 2.0, 65.0, 1.0)
        self.assertFalse(player_box.intersects(table_box))

        # Commit block placement
        s.world[table_place_pos] = ItemID.CRAFTING_TABLE
        s.inv.slots[1].count -= 1
        self.assertTrue(s.inv.slots[1].is_empty())

        # -------------------------------------------------------------------------
        # Step 6: Craft 4 Sticks (2 Planks)
        # -------------------------------------------------------------------------
        grid_sticks = [[ItemStack(ItemID.WOOD_PLANKS, 1), ItemStack()],
                       [ItemStack(ItemID.WOOD_PLANKS, 1), ItemStack()]]
        sticks_item = s.crafting.craft(grid_sticks)
        self.assertIsNotNone(sticks_item)
        self.assertEqual(sticks_item.item_id, ItemID.STICK)
        self.assertEqual(sticks_item.count, 4)

        s.inv.slots[0].count -= 2  # 10 planks remain
        s.inv.add_item(sticks_item)  # slot 1 has 4 sticks
        self.assertEqual(s.inv.slots[0].count, 10)
        self.assertEqual(s.inv.slots[1].count, 4)

        # -------------------------------------------------------------------------
        # Step 7: 3x3 Crafting (Wooden Pickaxe)
        # -------------------------------------------------------------------------
        grid_wood_pick = [
            [ItemStack(ItemID.WOOD_PLANKS, 1), ItemStack(ItemID.WOOD_PLANKS, 1), ItemStack(ItemID.WOOD_PLANKS, 1)],
            [ItemStack(),                      ItemStack(ItemID.STICK, 1),       ItemStack()],
            [ItemStack(),                      ItemStack(ItemID.STICK, 1),       ItemStack()]
        ]
        wood_pick = s.crafting.craft(grid_wood_pick)
        self.assertIsNotNone(wood_pick)
        self.assertEqual(wood_pick.item_id, ItemID.WOODEN_PICKAXE)
        self.assertEqual(wood_pick.durability, 59)

        s.inv.slots[0].count -= 3  # 7 planks remain
        s.inv.slots[1].count -= 2  # 2 sticks remain
        s.inv.add_item(wood_pick)  # slot 2 has wooden pickaxe

        # -------------------------------------------------------------------------
        # Step 8: Mine Stone with Wooden Pickaxe (11 Cobblestone)
        # -------------------------------------------------------------------------
        # Stone hardness 1.5s, wood tool multiplier M=2.0 -> 0.75s per block
        # Mine 11 stone blocks
        cobble_collected = 0
        pick_slot = 2
        for i in range(11):
            s.world[(5, 64, -2 + (i % 5))] = ItemID.STONE  # ensure blocks exist
            # Break stone
            del s.world[(5, 64, -2 + (i % 5))]
            cobble_collected += 1
            # Decrement durability
            s.inv.slots[pick_slot].durability -= 1
            s.survival.add_exhaustion(0.005)

        self.assertEqual(cobble_collected, 11)
        self.assertEqual(s.inv.slots[pick_slot].durability, 59 - 11)  # 48 remaining
        s.inv.add_item(ItemStack(ItemID.COBBLESTONE, 11))  # slot 3 has 11 cobble

        # -------------------------------------------------------------------------
        # Step 9: 3x3 Crafting (Stone Pickaxe)
        # -------------------------------------------------------------------------
        grid_stone_pick = [
            [ItemStack(ItemID.COBBLESTONE, 1), ItemStack(ItemID.COBBLESTONE, 1), ItemStack(ItemID.COBBLESTONE, 1)],
            [ItemStack(),                      ItemStack(ItemID.STICK, 1),       ItemStack()],
            [ItemStack(),                      ItemStack(ItemID.STICK, 1),       ItemStack()]
        ]
        stone_pick = s.crafting.craft(grid_stone_pick)
        self.assertIsNotNone(stone_pick)
        self.assertEqual(stone_pick.item_id, ItemID.STONE_PICKAXE)
        self.assertEqual(stone_pick.durability, 131)

        s.inv.slots[3].count -= 3  # 8 cobble remain
        s.inv.slots[1].count -= 2  # 0 sticks remain
        s.inv.slots[1] = ItemStack()
        s.inv.slots[4] = stone_pick  # slot 4 has stone pickaxe

        # -------------------------------------------------------------------------
        # Step 10: Craft More Sticks (2 Planks -> 4 Sticks)
        # -------------------------------------------------------------------------
        s.inv.slots[0].count -= 2  # 5 planks remain
        s.inv.add_item(ItemStack(ItemID.STICK, 4))  # slot 1 has 4 sticks
        self.assertEqual(s.inv.slots[0].count, 5)
        self.assertEqual(s.inv.slots[1].count, 4)

        # -------------------------------------------------------------------------
        # Step 11: 3x3 Crafting (Furnace — 8 Cobblestone Ring)
        # -------------------------------------------------------------------------
        grid_furnace = [
            [ItemStack(ItemID.COBBLESTONE, 1), ItemStack(ItemID.COBBLESTONE, 1), ItemStack(ItemID.COBBLESTONE, 1)],
            [ItemStack(ItemID.COBBLESTONE, 1), ItemStack(),                      ItemStack(ItemID.COBBLESTONE, 1)],
            [ItemStack(ItemID.COBBLESTONE, 1), ItemStack(ItemID.COBBLESTONE, 1), ItemStack(ItemID.COBBLESTONE, 1)]
        ]
        furnace_item = s.crafting.craft(grid_furnace)
        self.assertIsNotNone(furnace_item)
        self.assertEqual(furnace_item.item_id, ItemID.FURNACE)
        self.assertEqual(furnace_item.count, 1)

        s.inv.slots[3].count -= 8  # 0 cobble remain
        s.inv.slots[3] = ItemStack()
        s.inv.add_item(furnace_item)  # slot 3 has furnace

        # -------------------------------------------------------------------------
        # Step 12: Mine Coal Ore with Stone Pickaxe
        # -------------------------------------------------------------------------
        coal_ore_pos = (5, 65, 0)
        self.assertIn(coal_ore_pos, s.world)
        del s.world[coal_ore_pos]
        # Stone pickaxe durability decrements by 1
        stone_pick_slot = 4
        s.inv.slots[stone_pick_slot].durability -= 1
        self.assertEqual(s.inv.slots[stone_pick_slot].durability, 130)

        # Collect 1 coal drop
        s.inv.add_item(ItemStack(ItemID.COAL, 1))

        # -------------------------------------------------------------------------
        # Step 13: Craft Torches (1 Coal + 1 Stick -> 4 Torches)
        # -------------------------------------------------------------------------
        grid_torch = [[ItemStack(ItemID.COAL, 1), ItemStack()],
                      [ItemStack(ItemID.STICK, 1), ItemStack()]]
        torch_item = s.crafting.craft(grid_torch)
        self.assertIsNotNone(torch_item)
        self.assertEqual(torch_item.item_id, ItemID.TORCH)
        self.assertEqual(torch_item.count, 4)

        # Deduct 1 stick
        s.inv.slots[1].count -= 1  # 3 sticks remain
        # Coal was consumed
        s.inv.add_item(torch_item)

        # -------------------------------------------------------------------------
        # Step 14: Comprehensive Final State Verification
        # -------------------------------------------------------------------------
        # Health is still full 20.0
        self.assertEqual(s.survival.health, 20.0)
        self.assertTrue(s.survival.is_alive)

        # Find items in inventory
        items_by_id = {}
        for slot in s.inv.slots:
            if not slot.is_empty():
                items_by_id[slot.item_id] = slot

        self.assertIn(ItemID.WOOD_PLANKS, items_by_id)
        self.assertEqual(items_by_id[ItemID.WOOD_PLANKS].count, 5)

        self.assertIn(ItemID.STICK, items_by_id)
        self.assertEqual(items_by_id[ItemID.STICK].count, 3)

        self.assertIn(ItemID.WOODEN_PICKAXE, items_by_id)
        self.assertEqual(items_by_id[ItemID.WOODEN_PICKAXE].durability, 48)

        self.assertIn(ItemID.STONE_PICKAXE, items_by_id)
        self.assertEqual(items_by_id[ItemID.STONE_PICKAXE].durability, 130)

        self.assertIn(ItemID.FURNACE, items_by_id)
        self.assertEqual(items_by_id[ItemID.FURNACE].count, 1)

        self.assertIn(ItemID.TORCH, items_by_id)
        self.assertEqual(items_by_id[ItemID.TORCH].count, 4)


if __name__ == '__main__':
    unittest.main()
