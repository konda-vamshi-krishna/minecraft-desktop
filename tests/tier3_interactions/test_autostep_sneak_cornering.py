"""
Tier 3: Pairwise Cross-Feature Test — Auto-Step + Sneak Ledge-Clamping on Elevated Platforms.
Verifies ascending a 0.5m slab via auto-step while sneaking, maintaining sneak state at elevated level,
engaging ledge clamp at the perimeter of the elevated slab, and navigating around convex ledge corners.
"""

import unittest
from tests.canonical_models import Kinematics, VoxelPhysicsController, AABB


class ElevatedLedgeWorld:
    """
    World layout:
    - Base floor at y < 64
    - L-shaped 0.5m elevated slab platform on top of y=64:
      covers (1, 64, 0), (2, 64, 0), (2, 64, 1), (2, 64, 2)
    - All other voxels at y >= 64 are void / air.
    """
    def __init__(self):
        self.slabs = {
            (1, 64, 0),
            (2, 64, 0),
            (2, 64, 1),
            (2, 64, 2)
        }

    def __call__(self, x: int, y: int, z: int) -> bool:
        if (x, y, z) in self.slabs:
            return True
        return y < 64

    def get_aabb(self, x: int, y: int, z: int) -> AABB:
        if (x, y, z) in self.slabs:
            return AABB(x, y, z, x + 1.0, y + 0.5, z + 1.0)
        return AABB(x, y, z, x + 1.0, y + 1.0, z + 1.0)


class TestAutoStepSneakCornering(unittest.TestCase):

    def setUp(self):
        self.world = ElevatedLedgeWorld()
        self.controller = VoxelPhysicsController(0.0, 64.0, 0.5)
        self.controller.is_grounded = True
        self.controller.is_sneaking = True
        self.dt = 1.0 / 60.0

    def test_01_sneaking_player_autosteps_onto_slab(self):
        """Verify player in sneak mode automatically steps up +0.5m onto slab at (1, 64, 0)."""
        # Walk East (+X) while sneaking for 60 ticks (1.0s)
        for _ in range(60):
            self.controller.tick(self.dt, (1.0, 0.0, 0.0), jump_requested=False, is_solid_voxel=self.world)

        # Player successfully ascended onto slab top (y = 64.5)
        self.assertAlmostEqual(self.controller.y, 64.5, places=2)
        self.assertTrue(self.controller.is_grounded)
        self.assertTrue(self.controller.is_sneaking)
        self.assertGreater(self.controller.x, 1.0)

    def test_02_elevation_retention_while_sneaking(self):
        """Verify sneaking player maintains elevated y=64.5 while moving across slab (1, 64, 0) to (2, 64, 0)."""
        # Start on slab (1, 64, 0)
        self.controller.x = 1.5
        self.controller.y = 64.5
        self.controller.z = 0.5

        # Move East towards slab (2, 64, 0) for 40 ticks
        for _ in range(40):
            self.controller.tick(self.dt, (1.0, 0.0, 0.0), jump_requested=False, is_solid_voxel=self.world)

        self.assertAlmostEqual(self.controller.y, 64.5, places=2)
        self.assertGreater(self.controller.x, 2.0)
        self.assertTrue(self.controller.is_grounded)

    def test_03_elevated_edge_clamp_prevents_falling_to_lower_floor(self):
        """Verify sneak ledge clamp prevents player from stepping off the elevated slab perimeter."""
        # Position at (2.5, 64.5, 0.5) on slab (2, 64, 0). North (Z < 0) is air.
        self.controller.x = 2.5
        self.controller.y = 64.5
        self.controller.z = 0.5

        # Push North (-Z) towards cliff edge for 30 ticks
        for _ in range(30):
            self.controller.tick(self.dt, (0.0, 0.0, -1.0), jump_requested=False, is_solid_voxel=self.world)

        # Z displacement clamped, player does not fall down
        self.assertAlmostEqual(self.controller.y, 64.5, places=2)
        self.assertTrue(self.controller.is_grounded)

    def test_04_sliding_along_elevated_l_shape(self):
        """Verify moving diagonally at edge clamps cliff axis while allowing progress down the L-track (+Z)."""
        self.controller.x = 2.5
        self.controller.y = 64.5
        self.controller.z = 0.5

        # Push East (+X cliff) and South (+Z runway)
        for _ in range(30):
            self.controller.tick(self.dt, (0.707, 0.0, 0.707), jump_requested=False, is_solid_voxel=self.world)

        # X is clamped at cliff edge (< 3.3)
        self.assertLess(self.controller.x, 3.3)
        # Z progresses freely along runway
        self.assertGreater(self.controller.z, 0.7)
        self.assertAlmostEqual(self.controller.y, 64.5, places=2)
        self.assertTrue(self.controller.is_grounded)

    def test_05_releasing_sneak_on_elevated_platform_drops_player(self):
        """Verify releasing sneak on elevated platform allows walking off and falling back down."""
        self.controller.x = 2.5
        self.controller.y = 64.5
        self.controller.z = 0.5
        self.controller.is_sneaking = False  # Release sneak

        # Walk North (-Z) off the slab
        for _ in range(30):
            self.controller.tick(self.dt, (0.0, 0.0, -1.0), jump_requested=False, is_solid_voxel=self.world)

        # Player stepped off slab and fell onto lower floor (y = 64.0)
        self.assertLess(self.controller.z, 0.0)
        self.assertAlmostEqual(self.controller.y, 64.0, places=2)


if __name__ == '__main__':
    unittest.main()
