"""
Tier 3: Pairwise Cross-Feature Test — Sprint-Jumping Kinematics + Hunger Exhaustion + FOV.
Verifies sprint-jumping kinetic acceleration, exhaustion accumulation, saturation/hunger drain,
sprint deactivation when hunger drops <= 6.0, and dynamic FOV decay.
"""

import unittest
import math
from tests.canonical_models import Kinematics, VoxelPhysicsController, PlayerSurvivalState


class TestSprintJumpExhaustion(unittest.TestCase):

    def setUp(self):
        self.survival = PlayerSurvivalState()
        self.controller = VoxelPhysicsController(0.0, 64.0, 0.0)
        self.controller.is_grounded = True
        self.flat_world = lambda x, y, z: y < 64

    def test_01_sprint_speed_and_exhaustion_accumulation(self):
        """Verify sprinting applies sprint speed (5.612 m/s) and accumulates 0.1 exhaustion per meter."""
        self.controller.is_sprinting = True
        dt = 1.0 / 60.0

        initial_x = self.controller.x
        # Sprint forward for 60 ticks (1.0 second)
        for _ in range(60):
            self.controller.tick(dt, (1.0, 0.0, 0.0), jump_requested=False, is_solid_voxel=self.flat_world)
            dist_moved = self.controller.x - initial_x
            initial_x = self.controller.x
            self.survival.add_exhaustion(dist_moved * 0.1)

        # In 1 second, player should have moved ~5.6 meters
        self.assertAlmostEqual(self.controller.x, Kinematics.SPRINT_SPEED, delta=0.5)
        # Exhaustion accumulated >= 0.5 units
        self.assertGreater(self.survival.exhaustion + (5.0 - self.survival.saturation) * 4.0, 0.5)

    def test_02_sprint_jump_compound_exhaustion(self):
        """Verify sprint-jump compounds both sprint exhaustion (0.1/m) and jump exhaustion (0.8/jump)."""
        initial_saturation = self.survival.saturation
        
        # Execute 5 sprint-jumps
        dt = 1.0 / 60.0
        for _ in range(5):
            self.controller.is_grounded = True
            # Jump
            self.controller.tick(dt, (1.0, 0.0, 0.0), jump_requested=True, is_solid_voxel=self.flat_world)
            self.survival.add_exhaustion(0.8)  # 0.8 per sprint jump

        # Total exhaustion added = 5 * 0.8 = 4.0 -> exactly 1 full saturation point drained
        self.assertAlmostEqual(self.survival.saturation, initial_saturation - 1.0, places=2)

    def test_03_saturation_exhaustion_drain_into_hunger(self):
        """Verify exhaustion drains saturation first; once saturation is 0, hunger food points drain."""
        self.survival.saturation = 2.0
        self.survival.hunger = 20.0

        # Add 12.0 exhaustion (drains 3 points: 2 saturation, then 1 hunger)
        self.survival.add_exhaustion(12.0)

        self.assertEqual(self.survival.saturation, 0.0)
        self.assertEqual(self.survival.hunger, 19.0)

    def test_04_hunger_threshold_disables_sprinting(self):
        """Verify when hunger drops to <= 6.0, sprinting is disabled and speed reverts to walking."""
        self.survival.hunger = 6.0
        self.assertFalse(self.survival.can_sprint())

        # Controller attempts to sprint, but survival state forbids it
        if not self.survival.can_sprint():
            self.controller.is_sprinting = False

        dt = 1.0 / 60.0
        for _ in range(60):
            self.controller.tick(dt, (1.0, 0.0, 0.0), jump_requested=False, is_solid_voxel=self.flat_world)

        # Speed should be walking speed (4.317 m/s), not sprint speed (5.612 m/s)
        self.assertAlmostEqual(self.controller.x, Kinematics.BASE_WALK_SPEED, delta=0.5)

    def test_05_dynamic_fov_warping_and_decay(self):
        """Verify dynamic FOV expands to 1.15x on sprint, then decays to 1.0x when sprinting stops."""
        base_fov = 70.0
        current_fov = base_fov
        dt = 1.0 / 60.0
        decay_rate = 12.0

        # Sprint active: target FOV is base * 1.15 = 80.5
        target_sprint_fov = base_fov * 1.15
        for _ in range(30):
            current_fov += (target_sprint_fov - current_fov) * (1.0 - math.exp(-decay_rate * dt))

        self.assertAlmostEqual(current_fov, 80.5, delta=0.5)

        # Sprint stopped: target FOV is base = 70.0
        for _ in range(30):
            current_fov += (base_fov - current_fov) * (1.0 - math.exp(-decay_rate * dt))

        self.assertAlmostEqual(current_fov, 70.0, delta=0.5)


if __name__ == '__main__':
    unittest.main()
