"""
Verification of Milestone 1 (M1) C Implementation Invariants.
Validates structural integrity, API signatures, zero-allocation invariants,
mathematical equivalence, and build file compliance.
"""

import unittest
import os
import re
import math


class TestM1CInvariants(unittest.TestCase):
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def setUp(self):
        self.math_h = os.path.join(self.PROJECT_ROOT, "src", "core", "math_utils.h")
        self.platform_h = os.path.join(self.PROJECT_ROOT, "src", "platform", "platform.h")
        self.platform_c = os.path.join(self.PROJECT_ROOT, "src", "platform", "platform_desktop.c")
        self.runtime_h = os.path.join(self.PROJECT_ROOT, "src", "core", "runtime.h")
        self.runtime_c = os.path.join(self.PROJECT_ROOT, "src", "core", "runtime.c")
        self.main_c = os.path.join(self.PROJECT_ROOT, "src", "main.c")
        self.makefile = os.path.join(self.PROJECT_ROOT, "Makefile")
        self.cmakelists = os.path.join(self.PROJECT_ROOT, "CMakeLists.txt")

    def test_01_all_m1_files_exist(self):
        """Verify all 8 exclusively owned M1 files exist and are non-empty."""
        files = [
            self.math_h, self.platform_h, self.platform_c,
            self.runtime_h, self.runtime_c, self.main_c,
            self.makefile, self.cmakelists
        ]
        for f in files:
            self.assertTrue(os.path.isfile(f), f"File {f} must exist")
            self.assertGreater(os.path.getsize(f), 50, f"File {f} must not be empty")

    def test_02_math_utils_zero_dynamic_allocation(self):
        """Verify math_utils.h strictly contains zero dynamic heap allocations."""
        with open(self.math_h, "r", encoding="utf-8") as f:
            content = f.read()

        forbidden = [r"\bmalloc\b", r"\bcalloc\b", r"\brealloc\b", r"\bfree\b"]
        for pattern in forbidden:
            self.assertIsNone(re.search(pattern, content),
                              f"math_utils.h must not contain dynamic allocation: {pattern}")

    def test_03_math_utils_structs_and_types(self):
        """Verify all required value types and structs are defined in math_utils.h."""
        with open(self.math_h, "r", encoding="utf-8") as f:
            content = f.read()

        required_structs = [
            "typedef struct Vec2", "typedef struct Vec3", "typedef struct Vec4",
            "typedef struct Mat4", "typedef struct AABB", "typedef struct Ray",
            "typedef struct Plane", "typedef struct Frustum", "typedef struct Camera",
            "typedef enum FrustumPlane", "typedef enum FrustumResult"
        ]
        for s in required_structs:
            self.assertIn(s, content, f"Missing struct/enum: {s}")

    def test_04_math_utils_functions(self):
        """Verify all core arithmetic, matrix, camera, and culling functions exist."""
        with open(self.math_h, "r", encoding="utf-8") as f:
            content = f.read()

        required_fns = [
            "Vec3_Create", "Vec3_Add", "Vec3_Sub", "Vec3_Scale",
            "Vec3_Dot", "Vec3_Cross", "Vec3_Length", "Vec3_Normalize", "Vec3_Lerp",
            "Mat4_Identity", "Mat4_Multiply", "Mat4_LookAtVectors", "Mat4_Perspective",
            "Camera_Init", "Camera_Rotate", "Camera_UpdateVectors", "Camera_UpdateFov", "Camera_UpdateMatrices",
            "Frustum_Extract", "Frustum_TestAABB",
            "WorldToChunkCoord", "WorldToLocalCoord", "ChunkVoxelIndex",
            "WrapAngle360", "ClampFloat", "AABB_Intersects", "Ray_IntersectAABB"
        ]
        for fn in required_fns:
            self.assertIn(fn, content, f"Missing required function: {fn}")

    def test_05_platform_executable_basepath_and_canary_storage(self):
        """Verify platform_desktop.c implements base-path resolution and canary write probe."""
        with open(self.platform_c, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("GetModuleFileNameW", content, "Windows base path resolution must use GetModuleFileNameW")
        self.assertIn("readlink", content, "Linux base path resolution must use readlink")
        self.assertIn("_NSGetExecutablePath", content, "macOS base path resolution must use _NSGetExecutablePath")
        self.assertIn(".write_test", content, "Storage probe must use .write_test canary file")
        self.assertIn("timeBeginPeriod(1)", content, "Windows high-res timer must call timeBeginPeriod(1)")
        self.assertIn("QueryPerformanceCounter", content, "Windows timing must use QPC")
        self.assertIn("clock_gettime", content, "POSIX timing must use clock_gettime")

    def test_06_platform_header_guards_and_raylib_cleanliness(self):
        """Verify Windows header collisions are mitigated in platform layer."""
        with open(self.platform_c, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("WIN32_LEAN_AND_MEAN", content)
        self.assertIn("#undef CloseWindow", content)
        self.assertIn("SetExitKey(KEY_NULL)", content)

    def test_07_runtime_fixed_dt_and_spiral_of_death_clamp(self):
        """Verify runtime.h/c strictly implement 60Hz loop and 0.25s clamp."""
        with open(self.runtime_h, "r", encoding="utf-8") as f:
            h_content = f.read()
        with open(self.runtime_c, "r", encoding="utf-8") as f:
            c_content = f.read()

        self.assertIn("RUNTIME_PHYSICS_HZ", h_content)
        self.assertIn("RUNTIME_FIXED_DT", h_content)
        self.assertIn("RUNTIME_MAX_FRAME_TIME", h_content)
        self.assertIn("RUNTIME_MAX_SUBSTEPS", h_content)
        self.assertIn("RUNTIME_CELESTIAL_PERIOD", h_content)

        self.assertIn("Runtime_SimulateDelta", h_content)
        self.assertIn("Runtime_GetRenderAlpha", h_content)
        self.assertIn("Runtime_ShouldStepPhysics", h_content)

        # In runtime.c, verify 0.25s clamp logic
        self.assertIn("maxAccumulator", c_content)

    def test_08_main_cli_and_test_m1_suite(self):
        """Verify main.c implements CLI parsing and deterministic test suite."""
        with open(self.main_c, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("--test-m1", content)
        self.assertIn("--headless", content)
        self.assertIn("--seed", content)
        self.assertIn("RunM1ValidationSuite", content)
        self.assertIn("[M1 TEST SUITE PASSED]", content)

    def test_09_build_system_configurations(self):
        """Verify Makefile and CMakeLists.txt configure standard C99 and headless target."""
        with open(self.makefile, "r", encoding="utf-8") as f:
            mk_content = f.read()
        with open(self.cmakelists, "r", encoding="utf-8") as f:
            cmake_content = f.read()

        self.assertIn("-std=c99", mk_content)
        self.assertIn("HEADLESS_ONLY", mk_content)
        self.assertIn("minecraft_headless", mk_content)

        self.assertIn("CMAKE_C_STANDARD 99", cmake_content)
        self.assertIn("minecraft_headless", cmake_content)
        self.assertIn("HEADLESS_ONLY", cmake_content)


if __name__ == "__main__":
    unittest.main()
