"""
Tier 2: Terminal Velocity Falling & Anti-Tunneling Verification.
Verifies that falling at maximum terminal velocity (-78.4 m/s, dy=-1.306m/tick)
never tunnels through 1-block thick floors or 0.5m slabs.
"""

import unittest
from tests.canonical_models import Kinematics, VoxelPhysicsController, AABB


class TestTerminalVelocityTunneling(unittest.TestCase):

    def test_01_terminal_velocity_single_block_floor_landing(self):
        """Verify falling at terminal velocity (-78.4 m/s) does not tunnel through a 1-block thick floor."""
        controller = VoxelPhysicsController(0.0, 65.2, 0.0)
        controller.vy = Kinematics.TERMINAL_VELOCITY  # -78.4 m/s
        dt = 1.0 / 60.0  # displacement = -1.306m -> would reach 63.894 (inside block at y=64!)

        # Solid block at y=64 (occupies [64, 65])
        def floor_at_64(x, y, z):
            return y == 64

        controller.tick(dt, (0, 0, 0), jump_requested=False, is_solid_voxel=floor_at_64)

        # Must land exactly on top of block (y = 65.0), not tunnel through to y <= 64.0
        self.assertAlmostEqual(controller.y, 65.0, places=3)
        self.assertEqual(controller.vy, 0.0)
        self.assertTrue(controller.is_grounded)

    def test_02_terminal_velocity_thin_slab_landing(self):
        """Verify falling at terminal velocity onto a 1-block tall boundary stops cleanly on upper boundary."""
        controller = VoxelPhysicsController(5.0, 70.1, 5.0)
        controller.vy = Kinematics.TERMINAL_VELOCITY
        dt = 1.0 / 60.0

        def floor_at_69(x, y, z):
            return y == 69

        controller.tick(dt, (0, 0, 0), jump_requested=False, is_solid_voxel=floor_at_69)

        # Must be stopped at y = 70.0
        self.assertAlmostEqual(controller.y, 70.0, places=3)
        self.assertEqual(controller.vy, 0.0)
        self.assertTrue(controller.is_grounded)

    def test_03_high_speed_impact_preserves_horizontal_coordinates(self):
        """Verify vertical terminal velocity impact does not corrupt horizontal X/Z coordinates."""
        controller = VoxelPhysicsController(12.345, 80.5, 67.890)
        controller.vy = Kinematics.TERMINAL_VELOCITY
        dt = 1.0 / 60.0

        def floor_at_79(x, y, z):
            return y <= 79

        controller.tick(dt, (0, 0, 0), jump_requested=False, is_solid_voxel=floor_at_79)

        self.assertAlmostEqual(controller.x, 12.345, places=4)
        self.assertAlmostEqual(controller.z, 67.890, places=4)
        self.assertAlmostEqual(controller.y, 80.0, places=3)
        self.assertTrue(controller.is_grounded)

    def test_04_continuous_fall_through_shaft_to_bottom(self):
        """Verify falling 100 blocks through a 1x1 empty vertical shaft terminates safely on bottom bedrock."""
        controller = VoxelPhysicsController(0.5, 164.0, 0.5)
        dt = 1.0 / 60.0

        def shaft_voxels(x, y, z):
            # Walls around 1x1 opening at (0, 0), floor at y=64
            if y <= 64:
                return True
            if x != 0 or z != 0:
                return True
            return False

        # Drop until grounded
        for _ in range(200):
            controller.tick(dt, (0, 0, 0), jump_requested=False, is_solid_voxel=shaft_voxels)
            if controller.is_grounded:
                break

        self.assertTrue(controller.is_grounded)
        self.assertAlmostEqual(controller.y, 65.0, places=2)
        self.assertEqual(controller.vy, 0.0)

    def test_05_ceiling_bump_during_rapid_upward_trajectory(self):
        """Verify high upward velocity hitting a ceiling stops at ceiling bottom without tunneling through."""
        controller = VoxelPhysicsController(0.0, 64.0, 0.0)
        controller.vy = 20.0  # fast upward launch
        dt = 1.0 / 60.0

        # Ceiling at y=66 (standing height is 1.8 -> head at 64 + 1.8 = 65.8, ceiling at 66.0)
        def ceiling_at_66(x, y, z):
            return y >= 66

        controller.tick(dt, (0, 0, 0), jump_requested=False, is_solid_voxel=ceiling_at_66)

        # Head hits y=66.0 -> controller.y clamped to 66.0 - 1.8 = 64.2
        self.assertAlmostEqual(controller.y, 64.2, places=2)
        self.assertEqual(controller.vy, 0.0)


if __name__ == '__main__':
    unittest.main()
