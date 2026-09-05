"""
Mathematical Verification Script for Amanatides-Woo DDA C99 Implementation.
Tests the exact logic of the proposed C99 raycast implementation against
canonical_models.py and verifies all mathematical invariants and edge cases.
"""

import math
import sys
import os
import unittest
from typing import Tuple, Callable, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))



class Vec3i:
    def __init__(self, x: int, y: int, z: int):
        self.x = int(x)
        self.y = int(y)
        self.z = int(z)

    def as_tuple(self) -> Tuple[int, int, int]:
        return (self.x, self.y, self.z)

    def __eq__(self, other) -> bool:
        if isinstance(other, tuple):
            return (self.x, self.y, self.z) == other
        return self.x == other.x and self.y == other.y and self.z == other.z

    def __repr__(self) -> str:
        return f"Vec3i({self.x}, {self.y}, {self.z})"


class ProposedRaycastResult:
    def __init__(self):
        self.hit = False
        self.target_block = Vec3i(0, 0, 0)
        self.place_block = Vec3i(0, 0, 0)
        self.face_normal = Vec3i(0, 0, 0)
        self.distance = 0.0
        self.block_id = 0


def c99_proposed_raycast(
    origin: Tuple[float, float, float],
    dir_vec: Tuple[float, float, float],
    max_reach: float,
    is_solid_fn: Callable[[int, int, int], bool]
) -> ProposedRaycastResult:
    """
    Python transcription of our proposed C99 Raycast_Traverse function.
    Matches C99 types, floorf, fabsf, IEEE 754 INFINITY, and branchless tie breaking.
    """
    res = ProposedRaycastResult()
    ox, oy, oz = origin
    dx, dy, dz = dir_vec

    len_sq = dx * dx + dy * dy + dz * dz
    if len_sq < 1e-14 or not math.isfinite(len_sq):
        return res

    inv_len = 1.0 / math.sqrt(len_sq)
    dx *= inv_len
    dy *= inv_len
    dz *= inv_len

    # Floored integer coordinates (matches (int)floorf())
    x = int(math.floor(ox))
    y = int(math.floor(oy))
    z = int(math.floor(oz))

    # Initial block occupancy test
    if is_solid_fn(x, y, z):
        res.hit = True
        res.target_block = Vec3i(x, y, z)
        res.face_normal = Vec3i(0, 1, 0)  # Default up normal
        res.place_block = Vec3i(x, y + 1, z)
        res.distance = 0.0
        return res

    step_x = 1 if dx > 0.0 else (-1 if dx < 0.0 else 0)
    step_y = 1 if dy > 0.0 else (-1 if dy < 0.0 else 0)
    step_z = 1 if dz > 0.0 else (-1 if dz < 0.0 else 0)

    inf = float('inf')
    t_delta_x = abs(1.0 / dx) if step_x != 0 else inf
    t_delta_y = abs(1.0 / dy) if step_y != 0 else inf
    t_delta_z = abs(1.0 / dz) if step_z != 0 else inf

    # Boundary distances
    t_max_x = (math.floor(ox) + 1.0 - ox) * t_delta_x if step_x > 0 else \
              (ox - math.floor(ox)) * t_delta_x if step_x < 0 else inf
    t_max_y = (math.floor(oy) + 1.0 - oy) * t_delta_y if step_y > 0 else \
              (oy - math.floor(oy)) * t_delta_y if step_y < 0 else inf
    t_max_z = (math.floor(oz) + 1.0 - oz) * t_delta_z if step_z > 0 else \
              (oz - math.floor(oz)) * t_delta_z if step_z < 0 else inf

    current_t = 0.0
    normal = Vec3i(0, 0, 0)

    max_steps = 64
    for _ in range(max_steps):
        if t_max_x < t_max_y:
            if t_max_x < t_max_z:
                current_t = t_max_x
                t_max_x += t_delta_x
                x += step_x
                normal = Vec3i(-step_x, 0, 0)
            else:
                current_t = t_max_z
                t_max_z += t_delta_z
                z += step_z
                normal = Vec3i(0, 0, -step_z)
        else:
            if t_max_y < t_max_z:
                current_t = t_max_y
                t_max_y += t_delta_y
                y += step_y
                normal = Vec3i(0, -step_y, 0)
            else:
                current_t = t_max_z
                t_max_z += t_delta_z
                z += step_z
                normal = Vec3i(0, 0, -step_z)

        if current_t > max_reach:
            break

        if is_solid_fn(x, y, z):
            res.hit = True
            res.target_block = Vec3i(x, y, z)
            res.face_normal = normal
            res.place_block = Vec3i(x + normal.x, y + normal.y, z + normal.z)
            res.distance = current_t
            return res

    return res


class TestProposedRaycastVerification(unittest.TestCase):
    def test_cardinal_invariants(self):
        from tests.canonical_models import fast_voxel_traversal
        origin = (5.5, 64.5, 5.5)
        dirs = [
            ((1.0, 0.0, 0.0), (8, 64, 5), (-1, 0, 0), (7, 64, 5)),
            ((-1.0, 0.0, 0.0), (2, 64, 5), (1, 0, 0), (3, 64, 5)),
            ((0.0, 1.0, 0.0), (5, 67, 5), (0, -1, 0), (5, 66, 5)),
            ((0.0, -1.0, 0.0), (5, 62, 5), (0, 1, 0), (5, 63, 5)),
            ((0.0, 0.0, 1.0), (5, 64, 8), (0, 0, -1), (5, 64, 7)),
            ((0.0, 0.0, -1.0), (5, 64, 2), (0, 0, 1), (5, 64, 3)),
        ]
        for d, target, expected_norm, expected_place in dirs:
            c99_res = c99_proposed_raycast(origin, d, 5.0, lambda x, y, z: (x, y, z) == target)
            canon_res = fast_voxel_traversal(origin, d, 5.0, lambda x, y, z: (x, y, z) == target)
            self.assertTrue(c99_res.hit)
            self.assertEqual(c99_res.target_block.as_tuple(), target)
            self.assertEqual(c99_res.face_normal.as_tuple(), expected_norm)
            self.assertEqual(c99_res.place_block.as_tuple(), expected_place)
            self.assertAlmostEqual(c99_res.distance, canon_res.distance, places=5)

    def test_negative_coordinates(self):
        origin = (-10.5, 64.5, -20.5)
        target = (-13, 64, -21)
        c99_res = c99_proposed_raycast(origin, (-1.0, 0.0, 0.0), 5.0, lambda x, y, z: (x, y, z) == target)
        self.assertTrue(c99_res.hit)
        self.assertEqual(c99_res.target_block.as_tuple(), target)
        self.assertEqual(c99_res.face_normal.as_tuple(), (1, 0, 0))
        self.assertEqual(c99_res.place_block.as_tuple(), (-12, 64, -21))
        self.assertAlmostEqual(c99_res.distance, 1.5, places=5)


    def test_manhattan_stepping_sequence(self):
        origin = (0.1, 0.1, 0.1)
        direction = (1.0, 2.0, 3.0)
        visited = []

        def recorder(x, y, z):
            visited.append((x, y, z))
            return False

        c99_proposed_raycast(origin, direction, 4.0, recorder)
        self.assertGreater(len(visited), 5)
        for i in range(len(visited) - 1):
            c1 = visited[i]
            c2 = visited[i + 1]
            manhattan = abs(c2[0] - c1[0]) + abs(c2[1] - c1[1]) + abs(c2[2] - c1[2])
            self.assertEqual(manhattan, 1, f"Step skipped lattice cells: {c1} -> {c2}")

    def test_randomized_differential_fuzzing(self):
        """Differential fuzzing: compare c99_proposed_raycast against canonical_models.fast_voxel_traversal."""
        from tests.canonical_models import fast_voxel_traversal
        import random
        rng = random.Random(42)

        for trial in range(100):
            ox = rng.uniform(-100.0, 100.0)
            oy = rng.uniform(1.0, 250.0)
            oz = rng.uniform(-100.0, 100.0)
            dx = rng.uniform(-1.0, 1.0)
            dy = rng.uniform(-1.0, 1.0)
            dz = rng.uniform(-1.0, 1.0)
            reach = rng.uniform(1.0, 6.0)

            # Define a target block along the ray direction at distance ~ 3.0m
            t_rand = rng.uniform(0.5, 4.0)
            tx = int(math.floor(ox + dx * t_rand))
            ty = int(math.floor(oy + dy * t_rand))
            tz = int(math.floor(oz + dz * t_rand))
            target = (tx, ty, tz)

            is_solid = lambda x, y, z: (x, y, z) == target

            c99_res = c99_proposed_raycast((ox, oy, oz), (dx, dy, dz), reach, is_solid)
            canon_res = fast_voxel_traversal((ox, oy, oz), (dx, dy, dz), reach, is_solid)

            self.assertEqual(c99_res.hit, canon_res.hit, f"Trial {trial} hit mismatch: c99={c99_res.hit}, canon={canon_res.hit}")
            if c99_res.hit:
                self.assertEqual(c99_res.target_block.as_tuple(), canon_res.target_block)
                self.assertEqual(c99_res.face_normal.as_tuple(), canon_res.face_normal)
                self.assertEqual(c99_res.place_block.as_tuple(), canon_res.place_block)
                self.assertAlmostEqual(c99_res.distance, canon_res.distance, places=4)

    def test_boundary_start_negative_step(self):
        origin = (5.0, 64.0, 5.0)
        target = (4, 64, 5)
        c99_res = c99_proposed_raycast(origin, (-1.0, 0.0, 0.0), 5.0, lambda x, y, z: (x, y, z) == target)
        self.assertTrue(c99_res.hit)
        self.assertEqual(c99_res.target_block.as_tuple(), target)
        self.assertEqual(c99_res.face_normal.as_tuple(), (1, 0, 0))
        self.assertEqual(c99_res.distance, 0.0)

    def test_zero_vector_guard(self):
        c99_res = c99_proposed_raycast((0, 0, 0), (0, 0, 0), 5.0, lambda x, y, z: True)
        self.assertFalse(c99_res.hit)

    def test_reach_cutoff(self):
        origin = (0.5, 64.5, 0.5)
        target = (5, 64, 0)
        hit_survival = c99_proposed_raycast(origin, (1.0, 0.0, 0.0), 4.0, lambda x, y, z: (x, y, z) == target)
        self.assertFalse(hit_survival.hit)
        hit_creative = c99_proposed_raycast(origin, (1.0, 0.0, 0.0), 5.0, lambda x, y, z: (x, y, z) == target)
        self.assertTrue(hit_creative.hit)

    def test_inside_solid_start(self):
        origin = (5.5, 64.5, 5.5)
        hit = c99_proposed_raycast(origin, (1.0, 0.0, 0.0), 5.0, lambda x, y, z: (x, y, z) == (5, 64, 5))
        self.assertTrue(hit.hit)
        self.assertEqual(hit.distance, 0.0)
        self.assertEqual(hit.target_block.as_tuple(), (5, 64, 5))
        self.assertEqual(hit.face_normal.as_tuple(), (0, 1, 0))
        self.assertEqual(hit.place_block.as_tuple(), (5, 65, 5))




if __name__ == '__main__':
    unittest.main()
