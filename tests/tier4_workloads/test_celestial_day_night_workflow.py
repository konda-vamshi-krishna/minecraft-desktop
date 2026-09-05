"""
Tier 4: Real-World Workload — 1200s Celestial Day/Night Orbital Cycle & Voxel Lighting Simulation.
Verifies the 20-minute (1200s) diurnal cycle, orbital sun vectors, zenith noon,
midnight nadir, directional face shading factors (1.0, 0.5, 0.8, 0.6), and sky lighting transitions.
"""

import unittest
import math


class CelestialLightingSimulator:
    DAY_CYCLE_SEC = 1200.0  # 20 minutes

    def __init__(self):
        self.time_sec = 0.0  # 0 to 1200

    def set_time(self, t: float):
        self.time_sec = t % self.DAY_CYCLE_SEC

    def get_sun_direction(self) -> tuple[float, float, float]:
        """Calculates 3D unit sun vector with 10.0 degree axial tilt."""
        phi = (self.time_sec / self.DAY_CYCLE_SEC) * 2.0 * math.pi
        tilt_rad = math.radians(10.0)

        raw_x = math.cos(phi)
        raw_y = math.sin(phi) * math.cos(tilt_rad)
        raw_z = math.sin(phi) * math.sin(tilt_rad)

        mag = math.sqrt(raw_x*raw_x + raw_y*raw_y + raw_z*raw_z)
        return (raw_x / mag, raw_y / mag, raw_z / mag)

    def get_face_occlusion_factor(self, normal: tuple[int, int, int]) -> float:
        """Canonical directional face shading constants from docs/02 §7.2.1."""
        nx, ny, nz = normal
        if ny > 0:
            return 1.00  # Top face (+Y)
        if ny < 0:
            return 0.50  # Bottom face (-Y)
        if nz != 0:
            return 0.80  # North / South faces (+/- Z)
        if nx != 0:
            return 0.60  # East / West faces (+/- X)
        return 1.00

    def get_daylight_factor(self) -> float:
        sun_y = self.get_sun_direction()[1]
        # Smoothstep between -0.2 and 0.2
        if sun_y <= -0.2:
            return 0.0
        if sun_y >= 0.2:
            return 1.0
        norm = (sun_y - (-0.2)) / 0.4
        return norm * norm * (3.0 - 2.0 * norm)


class TestCelestialDayNightWorkflow(unittest.TestCase):

    def setUp(self):
        self.sim = CelestialLightingSimulator()

    def test_01_zenith_noon_sun_elevation(self):
        """Verify noon at t=300s (phi = pi/2) puts sun near zenith (+Y)."""
        self.sim.set_time(300.0)
        sx, sy, sz = self.sim.get_sun_direction()

        self.assertAlmostEqual(sx, 0.0, places=2)
        # sy near cos(10 deg) = 0.9848
        self.assertAlmostEqual(sy, math.cos(math.radians(10.0)), places=2)
        self.assertGreater(sy, 0.95)
        # Daylight factor is 1.0 (full noon daylight)
        self.assertAlmostEqual(self.sim.get_daylight_factor(), 1.0, places=4)

    def test_02_midnight_sun_nadir_and_night_darkness(self):
        """Verify midnight at t=900s (phi = 3pi/2) puts sun below horizon and daylight factor is 0.0."""
        self.sim.set_time(900.0)
        sx, sy, sz = self.sim.get_sun_direction()

        self.assertAlmostEqual(sx, 0.0, places=2)
        self.assertLess(sy, -0.95)  # deep nadir
        # Daylight factor is 0.0 (full pitch night)
        self.assertEqual(self.sim.get_daylight_factor(), 0.0)

    def test_03_dawn_and_dusk_horizons(self):
        """Verify sunrise (t=0s, phi=0) and sunset (t=600s, phi=pi) align with horizon."""
        # Sunrise: t=0s
        self.sim.set_time(0.0)
        sx, sy, sz = self.sim.get_sun_direction()
        self.assertAlmostEqual(sy, 0.0, places=2)
        self.assertAlmostEqual(sx, 1.0, places=2)

        # Sunset: t=600s
        self.sim.set_time(600.0)
        sx, sy, sz = self.sim.get_sun_direction()
        self.assertAlmostEqual(sy, 0.0, places=2)
        self.assertAlmostEqual(sx, -1.0, places=2)

    def test_04_directional_face_shading_factors(self):
        """Verify directional face occlusion constants: Top 1.00, Bottom 0.50, N/S 0.80, E/W 0.60."""
        self.assertEqual(self.sim.get_face_occlusion_factor((0, 1, 0)), 1.00)
        self.assertEqual(self.sim.get_face_occlusion_factor((0, -1, 0)), 0.50)
        self.assertEqual(self.sim.get_face_occlusion_factor((0, 0, 1)), 0.80)
        self.assertEqual(self.sim.get_face_occlusion_factor((0, 0, -1)), 0.80)
        self.assertEqual(self.sim.get_face_occlusion_factor((1, 0, 0)), 0.60)
        self.assertEqual(self.sim.get_face_occlusion_factor((-1, 0, 0)), 0.60)

    def test_05_smooth_24h_cycle_continuity(self):
        """Verify sun trajectory and daylight factor vary continuously without discontinuities over 1200s."""
        prev_y = self.sim.get_sun_direction()[1]
        for t in range(0, 1201, 10):
            self.sim.set_time(float(t))
            curr_y = self.sim.get_sun_direction()[1]
            # Max delta per 10s step should be small (< 0.1)
            self.assertLess(abs(curr_y - prev_y), 0.1)
            prev_y = curr_y

        # t=1200 wraps cleanly to t=0
        self.sim.set_time(1200.0)
        sx_1200, sy_1200, sz_1200 = self.sim.get_sun_direction()
        self.sim.set_time(0.0)
        sx_0, sy_0, sz_0 = self.sim.get_sun_direction()
        self.assertAlmostEqual(sx_1200, sx_0, places=4)
        self.assertAlmostEqual(sy_1200, sy_0, places=4)
        self.assertAlmostEqual(sz_1200, sz_0, places=4)


if __name__ == '__main__':
    unittest.main()
