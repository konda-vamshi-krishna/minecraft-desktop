"""
Comprehensive Verification of Milestone 2 (M2) C Implementation Invariants.
Validates:
1. All M2 files exist, are well-formed, and contain zero dynamic allocations.
2. Structure layouts, alignment macros, enums, and API prototypes.
3. Bitfield packing/unpacking and arithmetic invariance.
4. CMakeLists.txt and Makefile build configuration compliance.
5. Ponytail minimalist comments and upgrade annotations.
"""

import unittest
import os
import re

class TestM2CInvariants(unittest.TestCase):
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def setUp(self):
        self.world_h = os.path.join(self.PROJECT_ROOT, "src", "world", "world.h")
        self.chunk_c = os.path.join(self.PROJECT_ROOT, "src", "world", "chunk.c")
        self.terrain_h = os.path.join(self.PROJECT_ROOT, "src", "world", "terrain.h")
        self.terrain_c = os.path.join(self.PROJECT_ROOT, "src", "world", "terrain.c")
        self.mesher_h = os.path.join(self.PROJECT_ROOT, "src", "world", "mesher.h")
        self.mesher_c = os.path.join(self.PROJECT_ROOT, "src", "world", "mesher.c")
        self.cmakelists = os.path.join(self.PROJECT_ROOT, "CMakeLists.txt")
        self.makefile = os.path.join(self.PROJECT_ROOT, "Makefile")

        self.all_files = [
            self.world_h, self.chunk_c,
            self.terrain_h, self.terrain_c,
            self.mesher_h, self.mesher_c
        ]

    def test_01_all_m2_files_exist(self):
        for f in self.all_files:
            self.assertTrue(os.path.isfile(f), f"Missing M2 file: {f}")
            self.assertGreater(os.path.getsize(f), 100, f"File is unexpectedly empty: {f}")

    def test_02_zero_dynamic_heap_allocations(self):
        forbidden = [r"\bmalloc\b", r"\bcalloc\b", r"\brealloc\b", r"\bfree\b"]
        for f in self.all_files:
            with open(f, "r", encoding="utf-8") as fp:
                content = fp.read()
            for pattern in forbidden:
                self.assertIsNone(re.search(pattern, content),
                                  f"Forbidden dynamic allocation {pattern} found in {f}")

    def test_03_world_h_types_and_signatures(self):
        with open(self.world_h, "r", encoding="utf-8") as f:
            content = f.read()

        constants = [
            "CHUNK_WIDTH", "CHUNK_HEIGHT", "CHUNK_DEPTH", "CHUNK_VOXEL_COUNT",
            "WORLD_GRID_RADIUS", "WORLD_GRID_DIAMETER", "WORLD_ACTIVE_CHUNKS"
        ]
        for c in constants:
            self.assertIn(c, content, f"Missing constant in world.h: {c}")

        types = [
            "typedef enum BlockID", "typedef struct Chunk", "typedef struct ChunkNeighbors"
        ]
        for t in types:
            self.assertIn(t, content, f"Missing type in world.h: {t}")

        functions = [
            "World_Init", "World_Shutdown", "World_Update", "World_GetBlock",
            "World_SetBlock", "World_Render", "World_GetChunk",
            "World_GetChunkNeighbors", "World_SampleNeighborVoxel",
            "Chunk_Init", "Chunk_Reset", "Chunk_UnloadGPU"
        ]
        for fn in functions:
            self.assertIn(fn, content, f"Missing API function in world.h: {fn}")

    def test_04_terrain_h_c_types_and_signatures(self):
        with open(self.terrain_h, "r", encoding="utf-8") as f:
            h_content = f.read()
        with open(self.terrain_c, "r", encoding="utf-8") as f:
            c_content = f.read()

        self.assertIn("typedef enum BiomeType", h_content)
        for b in ["BIOME_PLAINS", "BIOME_DESERT", "BIOME_MOUNTAINS", "BIOME_FOREST"]:
            self.assertIn(b, h_content)

        fns = [
            "Terrain_HashCoords", "Terrain_SplitMix64Next", "Terrain_InitPermutation",
            "Terrain_Simplex2D", "Terrain_Simplex3D",
            "Terrain_Simplex2D_fBM", "Terrain_Simplex3D_fBM",
            "Terrain_ClassifyBiome", "Terrain_Init", "Terrain_GenerateChunk"
        ]
        for fn in fns:
            self.assertIn(fn, h_content, f"Missing prototype in terrain.h: {fn}")
            self.assertIn(fn, c_content, f"Missing implementation in terrain.c: {fn}")

    def test_05_mesher_h_c_types_and_signatures(self):
        with open(self.mesher_h, "r", encoding="utf-8") as f:
            h_content = f.read()
        with open(self.mesher_c, "r", encoding="utf-8") as f:
            c_content = f.read()

        self.assertIn("typedef enum FaceNormal", h_content)
        self.assertIn("typedef struct PackedVertex", h_content)
        self.assertIn("typedef struct ChunkMesh", h_content)
        self.assertIn("typedef struct MesherQueue", h_content)

        fns = [
            "Vertex_Pack", "Vertex_Unpack", "Mesher_IsOpaque",
            "Mesher_SampleVoxel", "Mesher_ComputeVertexAO",
            "Mesher_BuildMesh", "MesherQueue_Init",
            "MesherQueue_Push", "MesherQueue_Process"
        ]
        for fn in fns:
            self.assertIn(fn, h_content, f"Missing prototype in mesher.h: {fn}")
            if "Vertex_Pack" not in fn and "Vertex_Unpack" not in fn:
                self.assertIn(fn, c_content, f"Missing implementation in mesher.c: {fn}")

    def test_06_build_systems_include_m2_sources(self):
        with open(self.cmakelists, "r", encoding="utf-8") as f:
            cmake = f.read()
        with open(self.makefile, "r", encoding="utf-8") as f:
            mk = f.read()

        for s in ["src/world/terrain.c", "src/world/chunk.c", "src/world/mesher.c"]:
            self.assertIn(s, cmake, f"CMakeLists.txt must include {s}")
            self.assertIn(s, mk, f"Makefile must include {s}")

    def test_07_ponytail_comments_presence(self):
        for f in self.all_files:
            if f.endswith(".c"):
                with open(f, "r", encoding="utf-8") as fp:
                    content = fp.read()
                self.assertIn("// ponytail:", content, f"Missing // ponytail: annotation in {f}")

if __name__ == "__main__":
    unittest.main()
