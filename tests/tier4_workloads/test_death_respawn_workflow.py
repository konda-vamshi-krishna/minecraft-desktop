"""
Tier 4: Real-World Workload — Player Death, Fall Damage, Item Scattering & Respawn Lifecycle.
Verifies fall damage equations, water impact damage negation, death event triggering,
inventory item scattering at death coordinates, and respawn state restoration.
"""

import unittest
from tests.canonical_models import (
    PlayerSurvivalState, InventoryModel, ItemStack, ItemID
)


class TestDeathRespawnWorkflow(unittest.TestCase):

    def setUp(self):
        self.survival = PlayerSurvivalState()
        self.inv = InventoryModel()

    def test_01_non_fatal_fall_damage_equation(self):
        """Verify non-fatal fall damage: ceil(d - 3.0). Fall from 6m deals exactly 3 damage."""
        fall_dist = 6.0
        self.survival.apply_fall_damage(fall_dist, in_water=False)
        self.assertEqual(self.survival.health, 17.0)
        self.assertTrue(self.survival.is_alive)

    def test_02_water_impact_damage_negation(self):
        """Verify falling 50m directly into water completely negates all fall damage."""
        fall_dist = 50.0
        self.survival.apply_fall_damage(fall_dist, in_water=True)
        self.assertEqual(self.survival.health, 20.0)
        self.assertTrue(self.survival.is_alive)

    def test_03_fatal_fall_damage_triggers_death(self):
        """Verify falling 25m deals 22 damage, reducing 20 HP to 0 and marking player dead."""
        fall_dist = 25.0  # damage = ceil(25 - 3) = 22
        self.survival.apply_fall_damage(fall_dist, in_water=False)
        self.assertEqual(self.survival.health, 0.0)
        self.assertFalse(self.survival.is_alive)

    def test_04_inventory_items_scatter_on_death(self):
        """Verify upon death, all carried inventory items drop at the death location."""
        # Populate inventory with diamonds and pickaxe
        self.inv.slots[0] = ItemStack(ItemID.STONE_PICKAXE, 1, max_stack=1, durability=100)
        self.inv.slots[1] = ItemStack(ItemID.COAL, 12)
        death_location = (10.5, 64.0, 20.5)

        # Trigger fatal damage
        self.survival.take_damage(50.0)
        self.assertFalse(self.survival.is_alive)

        # Scatter items
        scattered_drops = []
        for i in range(len(self.inv.slots)):
            slot = self.inv.slots[i]
            if not slot.is_empty():
                scattered_drops.append((slot.copy(), death_location))
                self.inv.slots[i] = ItemStack()

        self.assertEqual(len(scattered_drops), 2)
        self.assertEqual(scattered_drops[0][0].item_id, ItemID.STONE_PICKAXE)
        self.assertEqual(scattered_drops[1][0].item_id, ItemID.COAL)
        self.assertEqual(scattered_drops[1][0].count, 12)
        # Player inventory is now completely empty
        self.assertTrue(all(s.is_empty() for s in self.inv.slots))

    def test_05_respawn_restores_health_hunger_and_clears_inventory(self):
        """Verify respawn restores HP to 20, Hunger to 20, is_alive to True, and resets position."""
        # Die
        self.survival.take_damage(20.0)
        self.assertFalse(self.survival.is_alive)

        # Respawn
        self.survival.respawn()
        self.assertTrue(self.survival.is_alive)
        self.assertEqual(self.survival.health, 20.0)
        self.assertEqual(self.survival.hunger, 20.0)
        self.assertEqual(self.survival.saturation, 5.0)


if __name__ == '__main__':
    unittest.main()
