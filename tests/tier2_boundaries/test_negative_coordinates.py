"""
Tier 2: Negative Coordinate Bitshifts & Chunk Boundary Math Tests.
Verifies floored division across negative chunk boundaries, local voxel index wrapping,
round-trip coordinate reconstruction, and YZX chunk memory packing.
"""

import unittest
from tests.canonical_models import CoordinateMath


class TestNegativeCoordinates(unittest.TestCase):

    def test_01_boundary_around_zero(self):
        """Verify chunk and local coordinates across zero boundary: X=0 vs X=-1."""
        # X = 0 -> Chunk 0, Local 0
        self.assertEqual(CoordinateMath.world_to_chunk_coord(0), 0)
        self.assertEqual(CoordinateMath.world_to_local_coord(0), 0)

        # X = -1 -> Chunk -1, Local 15
        self.assertEqual(CoordinateMath.world_to_chunk_coord(-1), -1)
        self.assertEqual(CoordinateMath.world_to_local_coord(-1), 15)

    def test_02_negative_chunk_boundary_16_to_17(self):
        """Verify chunk transition from chunk -1 to chunk -2 at X=-16 and X=-17."""
        # X = -16 -> Chunk -1, Local 0
        self.assertEqual(CoordinateMath.world_to_chunk_coord(-16), -1)
        self.assertEqual(CoordinateMath.world_to_local_coord(-16), 0)

        # X = -17 -> Chunk -2, Local 15
        self.assertEqual(CoordinateMath.world_to_chunk_coord(-17), -2)
        self.assertEqual(CoordinateMath.world_to_local_coord(-17), 15)

    def test_03_deep_negative_coordinate_bitshifts(self):
        """Verify large negative coordinates map accurately to chunk and local coordinates."""
        # -32 -> Chunk -2, Local 0
        self.assertEqual(CoordinateMath.world_to_chunk_coord(-32), -2)
        self.assertEqual(CoordinateMath.world_to_local_coord(-32), 0)

        # -33 -> Chunk -3, Local 15
        self.assertEqual(CoordinateMath.world_to_chunk_coord(-33), -3)
        self.assertEqual(CoordinateMath.world_to_local_coord(-33), 15)

        # -1000 -> Chunk -63, Local 8 (since -63 * 16 + 8 = -1008 + 8 = -1000)
        self.assertEqual(CoordinateMath.world_to_chunk_coord(-1000), -63)
        self.assertEqual(CoordinateMath.world_to_local_coord(-1000), 8)

    def test_04_roundtrip_coordinate_reconstruction_invariant(self):
        """Verify roundtrip identity: WorldCoord == ChunkCoord * 16 + LocalCoord across [-5000, 5000]."""
        for w in range(-5000, 5001, 17):  # Test across arbitrary stepped intervals
            cx = CoordinateMath.world_to_chunk_coord(w)
            lx = CoordinateMath.world_to_local_coord(w)
            reconstructed = cx * 16 + lx
            self.assertEqual(w, reconstructed, f"Mismatch for world coordinate {w}")
            self.assertGreaterEqual(lx, 0)
            self.assertLessEqual(lx, 15)

    def test_05_flat_chunk_voxel_index_bounds(self):
        """Verify 3D YZX index (ly + lx*256 + lz*4096) is strictly in [0, 65535] (64 KiB)."""
        # Corner min (0, 0, 0)
        self.assertEqual(CoordinateMath.chunk_voxel_index(0, 0, 0), 0)
        # Corner max (15, 255, 15)
        max_idx = CoordinateMath.chunk_voxel_index(15, 255, 15)
        self.assertEqual(max_idx, 65535)

        # Verify Y is stride 1 (cacheline sequential scan)
        idx_y0 = CoordinateMath.chunk_voxel_index(5, 100, 5)
        idx_y1 = CoordinateMath.chunk_voxel_index(5, 101, 5)
        self.assertEqual(idx_y1 - idx_y0, 1)


if __name__ == '__main__':
    unittest.main()
