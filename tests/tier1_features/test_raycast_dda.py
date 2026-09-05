"""
Tier 1: Amanatides-Woo Fast Voxel Traversal (DDA Raycast) Tests.
Verifies parametric stepping, entered face normal invariant, reach distance thresholds,
collinear axis alignment, and target/placement coordinate resolution.
"""

import unittest
import math
from tests.canonical_models import fast_voxel_traversal, RaycastHit


class TestRaycastDDA(unittest.TestCase):

    def test_01_cardinal_raycast_face_normal_invariants(self):
        """Verify entered face normal is strictly the negative step direction across all 6 cardinal directions."""
        origin = (5.5, 64.5, 5.5)

        # 1. Look +X (East): should hit face (-1, 0, 0)
        target_east = (8, 64, 5)
        hit_east = fast_voxel_traversal(origin, (1.0, 0.0, 0.0), 5.0,
                                        lambda x, y, z: (x, y, z) == target_east)
        self.assertTrue(hit_east.hit)
        self.assertEqual(hit_east.target_block, target_east)
        self.assertEqual(hit_east.face_normal, (-1, 0, 0))
        self.assertEqual(hit_east.place_block, (7, 64, 5))

        # 2. Look -X (West): should hit face (+1, 0, 0)
        target_west = (2, 64, 5)
        hit_west = fast_voxel_traversal(origin, (-1.0, 0.0, 0.0), 5.0,
                                        lambda x, y, z: (x, y, z) == target_west)
        self.assertTrue(hit_west.hit)
        self.assertEqual(hit_west.face_normal, (1, 0, 0))
        self.assertEqual(hit_west.place_block, (3, 64, 5))

        # 3. Look +Y (Up): should hit bottom face (0, -1, 0)
        target_up = (5, 67, 5)
        hit_up = fast_voxel_traversal(origin, (0.0, 1.0, 0.0), 5.0,
                                      lambda x, y, z: (x, y, z) == target_up)
        self.assertTrue(hit_up.hit)
        self.assertEqual(hit_up.face_normal, (0, -1, 0))
        self.assertEqual(hit_up.place_block, (5, 66, 5))

        # 4. Look -Y (Down): should hit top face (0, 1, 0)
        target_down = (5, 62, 5)
        hit_down = fast_voxel_traversal(origin, (0.0, -1.0, 0.0), 5.0,
                                        lambda x, y, z: (x, y, z) == target_down)
        self.assertTrue(hit_down.hit)
        self.assertEqual(hit_down.face_normal, (0, 1, 0))
        self.assertEqual(hit_down.place_block, (5, 63, 5))

        # 5. Look +Z (South): should hit face (0, 0, -1)
        target_south = (5, 64, 8)
        hit_south = fast_voxel_traversal(origin, (0.0, 0.0, 1.0), 5.0,
                                         lambda x, y, z: (x, y, z) == target_south)
        self.assertTrue(hit_south.hit)
        self.assertEqual(hit_south.face_normal, (0, 0, -1))
        self.assertEqual(hit_south.place_block, (5, 64, 7))

        # 6. Look -Z (North): should hit face (0, 0, 1)
        target_north = (5, 64, 2)
        hit_north = fast_voxel_traversal(origin, (0.0, 0.0, -1.0), 5.0,
                                         lambda x, y, z: (x, y, z) == target_north)
        self.assertTrue(hit_north.hit)
        self.assertEqual(hit_north.face_normal, (0, 0, 1))
        self.assertEqual(hit_north.place_block, (5, 64, 3))

    def test_02_reach_distance_thresholds(self):
        """Verify reach cutoff: hits within max_reach succeed; blocks beyond max_reach report miss."""
        origin = (0.5, 64.5, 0.5)
        target = (4, 64, 0)  # distance = 3.5 to near face, 4.5 to far face
        
        # Test within 4.0m reach
        hit_reach_4 = fast_voxel_traversal(origin, (1.0, 0.0, 0.0), 4.0,
                                           lambda x, y, z: (x, y, z) == target)
        self.assertTrue(hit_reach_4.hit)
        self.assertEqual(hit_reach_4.target_block, target)

        # Target placed at x=6 (distance = 5.5 to near face)
        target_far = (6, 64, 0)
        hit_creative_limit = fast_voxel_traversal(origin, (1.0, 0.0, 0.0), 5.0,
                                                  lambda x, y, z: (x, y, z) == target_far)
        self.assertFalse(hit_creative_limit.hit)

        # Target at x=5 (near face at 4.5) -> Hits with creative reach 5.0m, misses with survival reach 4.0m
        target_edge = (5, 64, 0)
        hit_survival = fast_voxel_traversal(origin, (1.0, 0.0, 0.0), 4.0,
                                            lambda x, y, z: (x, y, z) == target_edge)
        self.assertFalse(hit_survival.hit)

        hit_creative = fast_voxel_traversal(origin, (1.0, 0.0, 0.0), 5.0,
                                            lambda x, y, z: (x, y, z) == target_edge)
        self.assertTrue(hit_creative.hit)

    def test_03_diagonal_3d_ray_traversal_order(self):
        """Verify diagonal 3D ray traverses every discrete lattice cell along the trajectory."""
        origin = (0.1, 0.1, 0.1)
        direction = (1.0, 1.0, 1.0)
        
        visited_cells = []
        def recorder(x, y, z):
            visited_cells.append((x, y, z))
            return False  # keep ray marching

        fast_voxel_traversal(origin, direction, 3.0, recorder)

        # Ray must start in cell (0, 0, 0)
        self.assertIn((0, 0, 0), visited_cells)
        # Ray traversing (1, 1, 1) must sequentially cross intermediate single-step cells
        self.assertIn((1, 1, 1), visited_cells)
        # Check no teleporting: successive visited cells differ by exactly 1 Manhattan step
        for i in range(len(visited_cells) - 1):
            c1 = visited_cells[i]
            c2 = visited_cells[i + 1]
            manhattan = abs(c2[0] - c1[0]) + abs(c2[1] - c1[1]) + abs(c2[2] - c1[2])
            self.assertEqual(manhattan, 1, f"Step from {c1} to {c2} skipped cells!")

    def test_04_collinear_axis_zero_components(self):
        """Verify raycast handles zero look components (e.g. dy=0, dz=0) without division-by-zero crashes."""
        origin = (10.2, 65.0, 20.7)
        # Purely along X, zero in Y and Z
        direction = (1.0, 0.0, 0.0)

        hit = fast_voxel_traversal(origin, direction, 5.0,
                                   lambda x, y, z: (x, y, z) == (13, 65, 20))
        self.assertTrue(hit.hit)
        self.assertEqual(hit.target_block, (13, 65, 20))
        self.assertEqual(hit.face_normal, (-1, 0, 0))

    def test_05_immediate_inside_solid_block(self):
        """Verify if eye origin is already inside a solid block, DDA detects hit at distance 0."""
        origin = (5.5, 64.5, 5.5)
        hit = fast_voxel_traversal(origin, (1.0, 0.0, 0.0), 5.0,
                                   lambda x, y, z: (x, y, z) == (5, 64, 5))
        self.assertTrue(hit.hit)
        self.assertEqual(hit.distance, 0.0)
        self.assertEqual(hit.target_block, (5, 64, 5))


if __name__ == '__main__':
    unittest.main()
