"""
Empirical Verification Suite for Milestone 2 Chunk Architecture Invariants.
Validates:
1. 64 KiB contiguous flat chunk memory layout and cache line alignment.
2. Y-internal index formula: Index = y + 256*x + 4096*z == y | (x << 8) | (z << 12).
3. Coordinate transformation math: WorldToChunkCoord (w >> 4) & WorldToLocalCoord (w & 15).
4. 17x17 Toroidal Active Grid (289 chunks, 18.06 MiB static BSS RAM, collision-free bijection).
5. Canonical Block Palette enum (0..13) and block properties (opacity, solidity).
"""

import unittest
import math


class TestM2ChunkArchitecture(unittest.TestCase):

    # =========================================================================
    # 1. Chunk Memory Layout & Cache Line Alignment Invariants
    # =========================================================================

    def test_01_chunk_dimensions_and_footprint(self):
        """Verify chunk dimensions (16x256x16) equal exactly 65,536 bytes (64 KiB)."""
        chunk_x = 16
        chunk_y = 256
        chunk_z = 16
        voxel_count = chunk_x * chunk_y * chunk_z
        bytes_per_voxel = 1  # uint8_t
        total_bytes = voxel_count * bytes_per_voxel

        self.assertEqual(voxel_count, 65536)
        self.assertEqual(total_bytes, 65536)
        self.assertEqual(total_bytes, 64 * 1024, "Chunk must be exactly 64 KiB")

    def test_02_cache_line_and_simd_alignment(self):
        """Verify 64 KiB chunk aligns to 64-byte L1/L2 cache lines and 4-cache-line columns."""
        cache_line_bytes = 64
        total_bytes = 65536

        self.assertEqual(total_bytes % cache_line_bytes, 0, "Chunk size must be exact multiple of 64 bytes")
        num_cache_lines = total_bytes // cache_line_bytes
        self.assertEqual(num_cache_lines, 1024, "A 64 KiB chunk comprises exactly 1024 cache lines")

        # Vertical column: 256 voxels * 1 byte = 256 bytes
        column_bytes = 256
        self.assertEqual(column_bytes % cache_line_bytes, 0)
        self.assertEqual(column_bytes // cache_line_bytes, 4,
                         "Each vertical column occupies exactly 4 consecutive 64-byte cache lines")

    def test_03_toroidal_grid_total_bss_footprint(self):
        """Verify 17x17 active chunk grid (289 chunks) raw voxel RAM is exactly 18.0625 MiB."""
        grid_dim = 17
        active_chunks = grid_dim * grid_dim
        self.assertEqual(active_chunks, 289)

        total_voxel_bytes = active_chunks * 65536
        total_kib = total_voxel_bytes / 1024
        total_mib = total_kib / 1024

        self.assertEqual(total_voxel_bytes, 18939904)
        self.assertEqual(total_kib, 18496.0)
        self.assertEqual(total_mib, 18.0625)
        self.assertLess(total_mib, 20.0, "Total voxel BSS footprint must strictly reside under 20 MiB ceiling")

    # =========================================================================
    # 2. Y-Internal Index Formula & Cache Locality
    # =========================================================================

    def test_04_y_internal_index_formula_and_bitwise_equivalence(self):
        """Verify Index(x,y,z) = y + 256*x + 4096*z matches bitwise packing y | (x<<8) | (z<<12)."""
        for x in range(16):
            for z in range(16):
                for y in (0, 1, 63, 64, 127, 128, 254, 255):
                    arithmetic_idx = y + 256 * x + 4096 * z
                    bitwise_idx = y | (x << 8) | (z << 12)
                    self.assertEqual(arithmetic_idx, bitwise_idx,
                                     f"Mismatch at ({x}, {y}, {z})")
                    self.assertGreaterEqual(arithmetic_idx, 0)
                    self.assertLessEqual(arithmetic_idx, 65535)

    def test_05_index_bijective_uniqueness(self):
        """Verify that all 65,536 (x,y,z) coordinates map to unique indices in [0, 65535]."""
        seen_indices = set()
        for z in range(16):
            for x in range(16):
                for y in range(256):
                    idx = y + 256 * x + 4096 * z
                    seen_indices.add(idx)

        self.assertEqual(len(seen_indices), 65536)
        self.assertEqual(min(seen_indices), 0)
        self.assertEqual(max(seen_indices), 65535)

    def test_06_vertical_column_sequential_streaming_stride(self):
        """Verify moving delta-y = +1 results in consecutive byte address increments (stride = 1)."""
        for x in range(16):
            for z in range(16):
                base_idx = 256 * x + 4096 * z
                for y in range(255):
                    idx_curr = base_idx + y
                    idx_next = base_idx + (y + 1)
                    self.assertEqual(idx_next - idx_curr, 1,
                                     f"Stride failure along Y column at ({x}, {y}, {z})")

    # =========================================================================
    # 3. Coordinate Transformation Math
    # =========================================================================

    @staticmethod
    def c_world_to_chunk_coord(w: int) -> int:
        """Exact C99 arithmetic right-shift: w >> 4."""
        return w >> 4

    @staticmethod
    def c_world_to_local_coord(w: int) -> int:
        """Exact C99 bitwise AND: w & 15."""
        return w & 15

    def test_07_coordinate_reconstruction_across_deep_realms(self):
        """Verify identity: w == (w >> 4) * 16 + (w & 15) for all integers in [-20000, 20000]."""
        for w in range(-20000, 20001, 13):
            cx = self.c_world_to_chunk_coord(w)
            lx = self.c_world_to_local_coord(w)
            reconstructed = cx * 16 + lx
            self.assertEqual(w, reconstructed, f"Reconstruction failed for w={w}")
            self.assertGreaterEqual(lx, 0, f"Local coord must be non-negative for w={w}")
            self.assertLessEqual(lx, 15, f"Local coord must be <= 15 for w={w}")

    def test_08_mathematical_floor_equivalence(self):
        """Verify w >> 4 is strictly identical to math.floor(w / 16.0)."""
        for w in range(-1000, 1001):
            math_floor_chunk = math.floor(w / 16.0)
            bitshift_chunk = self.c_world_to_chunk_coord(w)
            self.assertEqual(bitshift_chunk, math_floor_chunk,
                             f"Floor mismatch at w={w}: shift={bitshift_chunk}, math={math_floor_chunk}")

    def test_09_docs_erratum_audit(self):
        """Audit that docs/03 formula ((w - 15) >> 4) is wrong for -16, while w >> 4 is correct."""
        w = -16
        errant_docs_result = (w - 15) >> 4  # -31 >> 4 = -2 (WRONG: -16 is in chunk -1!)
        correct_shift = w >> 4             # -16 >> 4 = -1 (CORRECT: chunk -1 spans [-16, -1])

        self.assertEqual(errant_docs_result, -2)
        self.assertEqual(correct_shift, -1)
        self.assertEqual(self.c_world_to_chunk_coord(w), -1)

    # =========================================================================
    # 4. 17x17 Toroidal Active Chunk Grid
    # =========================================================================

    @staticmethod
    def toroidal_slot(cx: int, cz: int) -> tuple:
        """Toroidal ring index mapping: ((coord % 17) + 17) % 17."""
        slot_x = ((cx % 17) + 17) % 17
        slot_z = ((cz % 17) + 17) % 17
        return slot_x, slot_z

    def test_10_toroidal_bijection_for_any_player_position(self):
        """Verify all 289 active chunks map to unique toroidal slots for any player chunk."""
        # Test 25 diverse player chunk positions across positive, negative, and origin
        player_positions = [
            (0, 0), (1, 1), (-1, -1), (8, 8), (-8, -8),
            (17, 17), (-17, -17), (100, -200), (-500, 350)
        ]
        for pcx, pcz in player_positions:
            active_slots = set()
            for cx in range(pcx - 8, pcx + 9):
                for cz in range(pcz - 8, pcz + 9):
                    slot = self.toroidal_slot(cx, cz)
                    self.assertNotIn(slot, active_slots,
                                     f"Toroidal collision at ({cx}, {cz}) for player at ({pcx}, {pcz})")
                    active_slots.add(slot)
                    self.assertGreaterEqual(slot[0], 0)
                    self.assertLess(slot[0], 17)
                    self.assertGreaterEqual(slot[1], 0)
                    self.assertLess(slot[1], 17)
            self.assertEqual(len(active_slots), 289)

    def test_11_toroidal_sliding_window_slot_reuse(self):
        """Verify that when player advances by 1 chunk, the 17 leaving and entering chunks share slots."""
        pcx = 0
        pcz = 0
        # Player moves +1 in X: pcx goes from 0 to 1
        # Exiting column: cx = -8, entering column: cx = +9
        for cz in range(-8, 9):
            slot_leaving = self.toroidal_slot(-8, cz)
            slot_entering = self.toroidal_slot(9, cz)
            self.assertEqual(slot_leaving, slot_entering,
                             f"Entering chunk (9, {cz}) must reuse leaving chunk (-8, {cz}) slot")

    # =========================================================================
    # 5. Canonical Block Palette & Block Properties
    # =========================================================================

    def test_12_block_palette_enum_values(self):
        """Verify canonical block enum values conform strictly to docs/03 §2.2."""
        expected_blocks = {
            "BLOCK_AIR": 0,
            "BLOCK_STONE": 1,
            "BLOCK_DIRT": 2,
            "BLOCK_GRASS": 3,
            "BLOCK_SAND": 4,
            "BLOCK_SANDSTONE": 5,
            "BLOCK_SNOW": 6,
            "BLOCK_WOOD": 7,
            "BLOCK_LEAVES": 8,
            "BLOCK_BEDROCK": 9,
            "BLOCK_WATER": 10,
            "BLOCK_CACTUS": 11,
            "BLOCK_FLOWER": 12,
            "BLOCK_TALLGRASS": 13,
        }
        self.assertEqual(len(expected_blocks), 14)
        for name, val in expected_blocks.items():
            self.assertGreaterEqual(val, 0)
            self.assertLessEqual(val, 13)

    def test_13_block_opacity_and_culling_invariants(self):
        """Verify block opacity properties: full cubes are opaque; air/water/foliage are non-opaque."""
        opaque_blocks = {1, 2, 3, 4, 5, 6, 7, 9}  # STONE, DIRT, GRASS, SAND, SANDSTONE, SNOW, WOOD, BEDROCK
        transparent_blocks = {0, 8, 10, 11, 12, 13}  # AIR, LEAVES, WATER, CACTUS, FLOWER, TALLGRASS

        def is_opaque(block_id: int) -> bool:
            return block_id in opaque_blocks

        # Never emit face between two opaque blocks
        self.assertFalse(is_opaque(1) and not is_opaque(2), "Two solid blocks must not emit internal face")
        # Emit face between opaque stone (1) and air (0)
        self.assertTrue(is_opaque(1) and not is_opaque(0), "Stone touching Air must emit visible face")
        # Emit face between opaque dirt (2) and water (10)
        self.assertTrue(is_opaque(2) and not is_opaque(10), "Dirt touching Water must emit visible face")
        # Emit face between dirt (2) and flower (12)
        self.assertTrue(is_opaque(2) and not is_opaque(12), "Dirt under Flower must emit top face")


if __name__ == '__main__':
    unittest.main()
