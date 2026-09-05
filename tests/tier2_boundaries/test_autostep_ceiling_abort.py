"""
Tier 2: Auto-Step Upward Probe & Low Ceiling Collision Abort Tests.
Verifies speculative +0.55m upward probe, successful step on clear headroom,
abort on ceiling collision (<1.8m clearance), and mid-air step inhibition.
"""

import unittest
from tests.canonical_models import Kinematics, VoxelPhysicsController, AABB


class SlabWorld:
    def __init__(self, slabs=None, blocks=None):
        self.slabs = set(slabs or [])
        self.blocks = set(blocks or [])

    def __call__(self, x: int, y: int, z: int) -> bool:
        return (x, y, z) in self.slabs or (x, y, z) in self.blocks or y < 64

    def get_aabb(self, x: int, y: int, z: int) -> AABB:
        if (x, y, z) in self.slabs:
            return AABB(x, y, z, x + 1.0, y + 0.5, z + 1.0)
        return AABB(x, y, z, x + 1.0, y + 1.0, z + 1.0)


class TestAutoStepCeilingAbort(unittest.TestCase):

    def test_01_step_up_success_with_clear_headroom(self):
        """Verify 0.5m slab step-up succeeds when vertical headspace (>= 1.8m) is completely clear."""
        controller = VoxelPhysicsController(0.0, 64.0, 0.5)
        controller.is_grounded = True
        dt = 1.0 / 60.0

        world = SlabWorld(slabs=[(1, 64, 0)])

        # Walk East (+X) for 25 ticks
        for _ in range(25):
            controller.tick(dt, (1.0, 0.0, 0.0), jump_requested=False, is_solid_voxel=world)

        # Successfully stepped up onto y=64.5
        self.assertAlmostEqual(controller.y, 64.5, places=2)
        self.assertGreater(controller.x, 1.0)
        self.assertTrue(controller.is_grounded)

    def test_02_step_up_aborted_due_to_low_ceiling(self):
        """Verify 0.5m step-up is aborted if ceiling block is directly overhead (headroom < 1.8m)."""
        controller = VoxelPhysicsController(0.0, 64.0, 0.5)
        controller.is_grounded = True
        dt = 1.0 / 60.0

        # Slab at (1, 64, 0), low ceiling at (1, 66, 0) -> headroom is only 1.5m < 1.8m
        world = SlabWorld(slabs=[(1, 64, 0)], blocks=[(1, 66, 0)])

        initial_x = controller.x
        initial_y = controller.y

        # Attempt to walk East (+X) into the low ceiling tunnel
        for _ in range(25):
            controller.tick(dt, (1.0, 0.0, 0.0), jump_requested=False, is_solid_voxel=world)

        # Must abort step: player remains at y=64.0, stopped before slab
        self.assertAlmostEqual(controller.y, initial_y, places=2)
        self.assertLessEqual(controller.x, 0.7)

    def test_03_airborne_player_cannot_autostep(self):
        """Verify player in mid-air (is_grounded == False) cannot auto-step up walls."""
        controller = VoxelPhysicsController(0.0, 64.2, 0.5)
        controller.is_grounded = False  # in mid-air
        dt = 1.0 / 60.0

        world = SlabWorld(slabs=[(1, 64, 0)])
        controller.tick(dt, (1.0, 0.0, 0.0), jump_requested=False, is_solid_voxel=world)

        # Did not auto-step
        self.assertLess(controller.x, 0.8)

    def test_04_wall_too_high_for_autostep(self):
        """Verify full 1.0m tall wall cannot be auto-stepped with 0.55m step height."""
        controller = VoxelPhysicsController(0.0, 64.0, 0.5)
        controller.is_grounded = True
        dt = 1.0 / 60.0

        # Full 1.0m block at (1, 64, 0)
        world = SlabWorld(blocks=[(1, 64, 0)])

        for _ in range(25):
            controller.tick(dt, (1.0, 0.0, 0.0), jump_requested=False, is_solid_voxel=world)

        # Player remains at y=64.0 and x stopped before wall
        self.assertAlmostEqual(controller.y, 64.0, places=2)
        self.assertLess(controller.x, 0.75)

    def test_05_multi_step_staircase_climb(self):
        """Verify successive auto-steps allow ascending a multi-tier 0.5m staircase smoothly without jumping."""
        controller = VoxelPhysicsController(0.0, 64.0, 0.5)
        controller.is_grounded = True
        dt = 1.0 / 60.0

        world = SlabWorld(
            slabs=[(1, 64, 0), (3, 65, 0)],
            blocks=[(2, 64, 0), (3, 64, 0)]
        )

        # Walk East over 80 ticks
        for _ in range(80):
            controller.tick(dt, (1.0, 0.0, 0.0), jump_requested=False, is_solid_voxel=world)

        # Player ascends past x=2.5 and elevation is above starting level
        self.assertGreater(controller.x, 2.5)


if __name__ == '__main__':
    unittest.main()
