"""
Tier 1: Fixed 60Hz Game Loop & Render Interpolation Alpha Tests.
Verifies fixed-timestep physics updates, accumulator accumulation,
spiral of death clamping (max 0.25s), and sub-frame state interpolation alpha.
"""

import unittest


class GameLoopSimulator:
    PHYSICS_HZ = 60
    FIXED_DT = 1.0 / 60.0
    MAX_FRAME_TIME = 0.25

    def __init__(self):
        self.accumulator = 0.0
        self.physics_ticks_executed = 0
        self.render_alpha = 0.0
        self.pos_prev = 0.0
        self.pos_curr = 0.0

    def update_frame(self, elapsed_wall_clock: float, speed: float = 1.0):
        frame_time = min(elapsed_wall_clock, self.MAX_FRAME_TIME)
        self.accumulator += frame_time

        while self.accumulator >= self.FIXED_DT:
            # Step physics
            self.pos_prev = self.pos_curr
            self.pos_curr += speed * self.FIXED_DT
            self.physics_ticks_executed += 1
            self.accumulator -= self.FIXED_DT

        self.render_alpha = self.accumulator / self.FIXED_DT

    def get_render_position(self) -> float:
        return (1.0 - self.render_alpha) * self.pos_prev + self.render_alpha * self.pos_curr


class TestFixedLoopTiming(unittest.TestCase):

    def setUp(self):
        self.loop = GameLoopSimulator()

    def test_01_exact_single_physics_tick(self):
        """Verify elapsed time equal to fixed dt (1/60s) triggers exactly 1 physics tick and alpha=0.0."""
        self.loop.update_frame(1.0 / 60.0)
        self.assertEqual(self.loop.physics_ticks_executed, 1)
        self.assertAlmostEqual(self.loop.render_alpha, 0.0, places=4)
        self.assertAlmostEqual(self.loop.accumulator, 0.0, places=4)

    def test_02_sub_frame_accumulator_and_render_alpha(self):
        """Verify frame time shorter than dt (e.g. 120 FPS, dt/2) produces 0 ticks and alpha=0.5."""
        half_dt = (1.0 / 60.0) / 2.0
        self.loop.update_frame(half_dt)
        self.assertEqual(self.loop.physics_ticks_executed, 0)
        self.assertAlmostEqual(self.loop.render_alpha, 0.5, places=4)

        # Second half-dt frame brings total to dt -> 1 tick executes, alpha resets to 0.0
        self.loop.update_frame(half_dt)
        self.assertEqual(self.loop.physics_ticks_executed, 1)
        self.assertAlmostEqual(self.loop.render_alpha, 0.0, places=4)

    def test_03_spiral_of_death_clamp(self):
        """Verify massive lag spike or pause (e.g. 2.0s) clamps to MAX_FRAME_TIME (0.25s)."""
        self.loop.update_frame(2.0)  # 2.0s frame lag
        # At 0.25s / (1/60s) = exactly 15 physics ticks (not 120 ticks!)
        self.assertEqual(self.loop.physics_ticks_executed, 15)
        self.assertLess(self.loop.accumulator, self.loop.FIXED_DT)

    def test_04_render_interpolation_alpha_bounds(self):
        """Verify alpha remains strictly within interval [0.0, 1.0) under arbitrary frame timings."""
        test_frame_deltas = [0.001, 0.012, 0.016667, 0.033, 0.05, 0.071, 0.20, 0.25]
        for delta in test_frame_deltas:
            self.loop.update_frame(delta)
            self.assertGreaterEqual(self.loop.render_alpha, 0.0)
            self.assertLess(self.loop.render_alpha, 1.0)

    def test_05_smooth_position_lerp(self):
        """Verify render position interpolates smoothly between previous and current physics ticks."""
        speed = 6.0  # 6 m/s
        # Advance 1 full tick
        self.loop.update_frame(1.0 / 60.0, speed=speed)
        # Advance 1/4 tick
        self.loop.update_frame((1.0 / 60.0) * 0.25, speed=speed)
        self.assertAlmostEqual(self.loop.render_alpha, 0.25, places=3)

        expected_lerp = 0.75 * self.loop.pos_prev + 0.25 * self.loop.pos_curr
        self.assertAlmostEqual(self.loop.get_render_position(), expected_lerp, places=4)


if __name__ == '__main__':
    unittest.main()
