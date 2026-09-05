"""
Tier 2: Sneak Ledge-Falloff Prevention & Edge-Clamping Tests.
Verifies downward probe, clamping unsupported axis, 2D convex corner gliding,
and falling when sneak is released.
"""

import unittest
from tests.canonical_models import Kinematics, VoxelPhysicsController


class TestSneakLedgeClamp(unittest.TestCase):

    def setUp(self):
        # 1-block pillar: only voxel at (5, 63, 5) exists; void all around
        self.single_pillar_world = lambda x, y, z: (x == 5 and y == 63 and z == 5)

    def test_01_sneak_prevents_walking_off_edge_x(self):
        """Verify sneaking player on isolated 1x1 block cannot fall off towards +X."""
        controller = VoxelPhysicsController(5.5, 64.0, 5.5)
        controller.is_grounded = True
        controller.is_sneaking = True
        dt = 1.0 / 60.0

        # Push East (+X) for 30 ticks
        for _ in range(30):
            controller.tick(dt, (1.0, 0.0, 0.0), jump_requested=False,
                            is_solid_voxel=self.single_pillar_world)

        # Player must remain on top of the block: x in [5.0, 6.3], y = 64.0
        self.assertAlmostEqual(controller.y, 64.0, places=3)
        self.assertLess(controller.x, 6.3)
        self.assertTrue(controller.is_grounded)

    def test_02_sneak_prevents_walking_off_edge_z(self):
        """Verify sneaking player on isolated 1x1 block cannot fall off towards +Z."""
        controller = VoxelPhysicsController(5.5, 64.0, 5.5)
        controller.is_grounded = True
        controller.is_sneaking = True
        dt = 1.0 / 60.0

        # Push South (+Z) for 30 ticks
        for _ in range(30):
            controller.tick(dt, (0.0, 0.0, 1.0), jump_requested=False,
                            is_solid_voxel=self.single_pillar_world)

        self.assertAlmostEqual(controller.y, 64.0, places=3)
        self.assertLess(controller.z, 6.3)
        self.assertTrue(controller.is_grounded)

    def test_03_convex_corner_diagonal_clamping(self):
        """Verify diagonal movement into a convex corner clamps both axes safely at edge."""
        controller = VoxelPhysicsController(5.5, 64.0, 5.5)
        controller.is_grounded = True
        controller.is_sneaking = True
        dt = 1.0 / 60.0

        # Push diagonally (+X, +Z)
        for _ in range(30):
            controller.tick(dt, (0.707, 0.0, 0.707), jump_requested=False,
                            is_solid_voxel=self.single_pillar_world)

        self.assertAlmostEqual(controller.y, 64.0, places=3)
        self.assertLess(controller.x, 6.3)
        self.assertLess(controller.z, 6.3)
        self.assertTrue(controller.is_grounded)

    def test_04_sliding_along_edge_parallel_axis_unblocked(self):
        """Verify clamping along X (cliff edge) does not block movement along Z (supported pathway)."""
        # Runway extending along Z: (x=5, y=63, z in [0..10])
        runway_world = lambda x, y, z: (x == 5 and y == 63 and 0 <= z <= 10)

        controller = VoxelPhysicsController(5.5, 64.0, 2.0)
        controller.is_grounded = True
        controller.is_sneaking = True
        dt = 1.0 / 60.0

        # Move diagonally towards +X (cliff) and +Z (pathway)
        for _ in range(30):
            controller.tick(dt, (0.707, 0.0, 0.707), jump_requested=False,
                            is_solid_voxel=runway_world)

        # X is clamped at cliff edge (< 6.3)
        self.assertLess(controller.x, 6.3)
        # Z advances freely down the pathway (> 2.3)
        self.assertGreater(controller.z, 2.3)
        self.assertTrue(controller.is_grounded)

    def test_05_releasing_sneak_allows_falling(self):
        """Verify releasing sneak (is_sneaking=False) allows player to walk off edge and fall."""
        controller = VoxelPhysicsController(5.5, 64.0, 5.5)
        controller.is_grounded = True
        controller.is_sneaking = False  # NOT sneaking
        dt = 1.0 / 60.0

        # Walk East off pillar
        for _ in range(30):
            controller.tick(dt, (1.0, 0.0, 0.0), jump_requested=False,
                            is_solid_voxel=self.single_pillar_world)

        # Player has fallen off pillar: x > 6.0 and y < 64.0
        self.assertGreater(controller.x, 6.0)
        self.assertLess(controller.y, 64.0)
        self.assertFalse(controller.is_grounded)


if __name__ == '__main__':
    unittest.main()
