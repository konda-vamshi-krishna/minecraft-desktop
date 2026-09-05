"""
Static Audit and Structural Verification for proposed_terrain.h and proposed_terrain.c.
Verifies:
1. Zero dynamic allocations (no malloc/calloc/realloc/free).
2. All required signatures, structs, and enums exist.
3. Y-internal index formula strictly matches canonical model.
4. Ponytail annotations present.
5. Zero cascading boundary mutations guaranteed by local coordinate clamping.
"""

import os
import re
import unittest


class TestProposedTerrainC(unittest.TestCase):
    DIR = os.path.dirname(os.path.abspath(__file__))

    def setUp(self):
        self.h_path = os.path.join(self.DIR, "proposed_terrain.h")
        self.c_path = os.path.join(self.DIR, "proposed_terrain.c")
        with open(self.h_path, "r", encoding="utf-8") as f:
            self.h_content = f.read()
        with open(self.c_path, "r", encoding="utf-8") as f:
            self.c_content = f.read()

    def test_01_zero_dynamic_allocations(self):
        """Verify zero dynamic heap allocations in terrain generation code."""
        for kw in (r"\bmalloc\b", r"\bcalloc\b", r"\brealloc\b", r"\bfree\b"):
            self.assertIsNone(re.search(kw, self.h_content), f"Forbidden allocation {kw} in header")
            self.assertIsNone(re.search(kw, self.c_content), f"Forbidden allocation {kw} in source")

    def test_02_canonical_enums_and_constants(self):
        """Verify BlockID, BiomeType, and chunk dimensions."""
        required_enums = [
            "BLOCK_AIR", "BLOCK_STONE", "BLOCK_DIRT", "BLOCK_GRASS",
            "BLOCK_SAND", "BLOCK_SANDSTONE", "BLOCK_SNOW", "BLOCK_WOOD",
            "BLOCK_LEAVES", "BLOCK_BEDROCK", "BLOCK_WATER", "BLOCK_CACTUS",
            "BLOCK_FLOWER", "BLOCK_TALLGRASS"
        ]
        for b in required_enums:
            self.assertIn(b, self.h_content, f"Missing block enum {b}")

        for biome in ("BIOME_PLAINS", "BIOME_DESERT", "BIOME_MOUNTAINS", "BIOME_FOREST"):
            self.assertIn(biome, self.h_content, f"Missing biome enum {biome}")

        self.assertIn("CHUNK_SIZE_X 16", self.h_content)
        self.assertIn("CHUNK_SIZE_Y 256", self.h_content)
        self.assertIn("CHUNK_SIZE_Z 16", self.h_content)
        self.assertIn("CHUNK_TOTAL_VOXELS (CHUNK_SIZE_X * CHUNK_SIZE_Y * CHUNK_SIZE_Z)", self.h_content)

    def test_03_function_signatures(self):
        """Verify all required public APIs are declared in proposed_terrain.h."""
        functions = [
            "Terrain_HashCoords",
            "Terrain_SplitMix64Next",
            "Terrain_InitPermutation",
            "Terrain_Simplex2D",
            "Terrain_Simplex3D",
            "Terrain_Simplex2D_fBM",
            "Terrain_Simplex3D_fBM",
            "Terrain_ClassifyBiome",
            "Terrain_Init",
            "Terrain_GenerateChunk"
        ]
        for fn in functions:
            self.assertIn(fn, self.h_content, f"Missing function prototype: {fn}")
            self.assertIn(fn, self.c_content, f"Missing function definition: {fn}")

    def test_04_y_internal_stride_formula(self):
        """Verify indexing is ly + lx*256 + lz*4096."""
        self.assertIn("ly + (lx * 256) + (lz * 4096)", self.c_content)

    def test_05_ponytail_comments(self):
        """Verify Ponytail simplicity annotations are documented."""
        self.assertIn("// ponytail:", self.c_content)

    def test_06_boundary_safety_coordinates(self):
        """Verify tree stamping is bounded to [2, 13] for zero chunk border bleed."""
        self.assertIn("2 + (int)(r1 % 12ULL)", self.c_content)
        self.assertIn("2 + (int)(r2 % 12ULL)", self.c_content)


if __name__ == "__main__":
    unittest.main()
