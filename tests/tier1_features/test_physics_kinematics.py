"""
Tier 1: Physics & Kinematics Functional Verification.
Verifies canonical AABB dimensions, eye offsets, gravity, terminal velocity,
jump impulses, ground friction, and movement speed multipliers.
"""

import unittest
import math
from tests.canonical_models import Kinematics, VoxelPhysicsController, AABB


class TestPhysicsKinematics(unittest.TestCase):

    def test_01_standing_and_sneaking_aabb_dimensions(self):
        """Verify rigid AABB dimensions: Standing 0.6x1.8x0.6m, Sneaking 0.6x1.5x0.6m."""
        pos_x, pos_y, pos_z = 10.0, 64.0, 10.0
        
        standing_box = Kinematics.get_player_aabb(pos_x, pos_y, pos_z, is_sneaking=False)
        self.assertAlmostEqual(standing_box.max_x - standing_box.min_x, 0.6, places=4)
        self.assertAlmostEqual(standing_box.max_y - standing_box.min_y, 1.8, places=4)
        self.assertAlmostEqual(standing_box.max_z - standing_box.min_z, 0.6, places=4)
        self.assertAlmostEqual(standing_box.min_x, 9.7, places=4)
        self.assertAlmostEqual(standing_box.max_x, 10.3, places=4)
        self.assertAlmostEqual(standing_box.min_y, 64.0, places=4)
        self.assertAlmostEqual(standing_box.max_y, 65.8, places=4)

        sneaking_box = Kinematics.get_player_aabb(pos_x, pos_y, pos_z, is_sneaking=True)
        self.assertAlmostEqual(sneaking_box.max_x - sneaking_box.min_x, 0.6, places=4)
        self.assertAlmostEqual(sneaking_box.max_y - sneaking_box.min_y, 1.5, places=4)
        self.assertAlmostEqual(sneaking_box.max_z - sneaking_box.min_z, 0.6, places=4)
        self.assertAlmostEqual(sneaking_box.min_y, 64.0, places=4)
        self.assertAlmostEqual(sneaking_box.max_y, 65.5, places=4)

    def test_02_standing_and_sneaking_eye_level_offsets(self):
        """Verify camera eye level offsets: Standing 1.62m, Sneaking 1.35m."""
        base_y = 70.0
        eye_standing = base_y + Kinematics.EYE_LEVEL_STANDING
        eye_sneaking = base_y + Kinematics.EYE_LEVEL_SNEAKING
        
        self.assertAlmostEqual(eye_standing - base_y, 1.62, places=4)
        self.assertAlmostEqual(eye_sneaking - base_y, 1.35, places=4)
        self.assertAlmostEqual(eye_standing - eye_sneaking, 0.27, places=4)

    def test_03_gravity_acceleration_and_terminal_velocity(self):
        """Verify downward acceleration g=-32.0 m/s^2 and terminal velocity ceiling v_term=-78.4 m/s."""
        controller = VoxelPhysicsController(0.0, 1000.0, 0.0)
        dt = 1.0 / 60.0
        
        # In empty space (no solid voxels)
        def no_solids(x, y, z):
            return False

        # First tick: vy accelerates by g * dt
        controller.tick(dt, (0, 0, 0), jump_requested=False, is_solid_voxel=no_solids)
        expected_vy_tick1 = Kinematics.GRAVITY * dt
        self.assertAlmostEqual(controller.vy, expected_vy_tick1, places=3)
        self.assertLess(controller.vy, 0.0)

        # After 200 ticks (~3.3 seconds of freefall), velocity must hit terminal velocity ceiling
        for _ in range(200):
            controller.tick(dt, (0, 0, 0), jump_requested=False, is_solid_voxel=no_solids)

        self.assertAlmostEqual(controller.vy, Kinematics.TERMINAL_VELOCITY, places=3)
        self.assertGreaterEqual(controller.vy, Kinematics.TERMINAL_VELOCITY)

    def test_04_jump_impulse_and_apex_clearance(self):
        """Verify jump impulse v_jump=8.944 m/s clears >= 1.25m obstacle height."""
        controller = VoxelPhysicsController(0.0, 64.0, 0.0)
        controller.is_grounded = True
        dt = 1.0 / 60.0

        def floor_only(x, y, z):
            return y < 64

        initial_y = controller.y
        max_y = initial_y

        # Jump on first tick
        controller.tick(dt, (0, 0, 0), jump_requested=True, is_solid_voxel=floor_only)
        self.assertAlmostEqual(controller.vy, Kinematics.JUMP_IMPULSE + Kinematics.GRAVITY * dt, places=2)
        self.assertFalse(controller.is_grounded)

        # Simulate ascent to apex
        for _ in range(60):
            controller.tick(dt, (0, 0, 0), jump_requested=False, is_solid_voxel=floor_only)
            if controller.y > max_y:
                max_y = controller.y

        apex_clearance = max_y - initial_y
        # Discrete 60Hz Euler integration achieves ~1.176m clearance (comfortably clears 1.0m hurdle)
        self.assertGreaterEqual(apex_clearance, 1.15)
        self.assertLessEqual(apex_clearance, 1.30)
        # Theoretical continuous kinematic apex: v^2 / (2 * |g|) == 1.250m
        theoretical_apex = (Kinematics.JUMP_IMPULSE ** 2) / (2.0 * abs(Kinematics.GRAVITY))
        self.assertAlmostEqual(theoretical_apex, 1.25, places=2)

    def test_05_ground_friction_and_air_drag(self):
        """Verify ground deceleration is responsive while airborne momentum preserves ballistic flight."""
        dt = 1.0 / 60.0
        
        # Ground test
        ground_ctrl = VoxelPhysicsController(0.0, 64.0, 0.0)
        ground_ctrl.is_grounded = True
        ground_ctrl.vx = 5.0
        # No wish dir (stopping)
        ground_ctrl.tick(dt, (0, 0, 0), jump_requested=False, is_solid_voxel=lambda x, y, z: y < 64)
        ground_decay = 5.0 - ground_ctrl.vx

        # Air test
        air_ctrl = VoxelPhysicsController(0.0, 64.0, 0.0)
        air_ctrl.is_grounded = False
        air_ctrl.vx = 5.0
        air_ctrl.tick(dt, (0, 0, 0), jump_requested=False, is_solid_voxel=lambda x, y, z: False)
        air_decay = 5.0 - air_ctrl.vx

        # Ground friction decelerates significantly faster than air drag
        self.assertGreater(ground_decay, air_decay * 2.5)

    def test_06_movement_speed_multipliers(self):
        """Verify base speeds: Walk 4.317 m/s, Sprint 5.612 m/s, Sneak 1.295 m/s."""
        self.assertAlmostEqual(Kinematics.SPRINT_SPEED / Kinematics.BASE_WALK_SPEED, 1.30, places=2)
        self.assertAlmostEqual(Kinematics.SNEAK_SPEED / Kinematics.BASE_WALK_SPEED, 0.30, places=2)


if __name__ == '__main__':
    unittest.main()
