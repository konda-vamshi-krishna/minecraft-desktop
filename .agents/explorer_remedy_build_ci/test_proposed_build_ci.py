"""
Automated Verification Suite for Proposed Build System & CI/CD Remediations.
Validates proposed_CMakeLists.txt, proposed_Makefile, and proposed_build_and_release.yml.
"""

import os
import re
import unittest
import yaml

class TestProposedBuildCI(unittest.TestCase):
    AGENT_DIR = os.path.dirname(os.path.abspath(__file__))

    def setUp(self):
        self.cmake_path = os.path.join(self.AGENT_DIR, "proposed_CMakeLists.txt")
        self.makefile_path = os.path.join(self.AGENT_DIR, "proposed_Makefile")
        self.workflow_path = os.path.join(self.AGENT_DIR, "proposed_build_and_release.yml")

        with open(self.cmake_path, "r", encoding="utf-8") as f:
            self.cmake_content = f.read()

        with open(self.makefile_path, "r", encoding="utf-8") as f:
            self.makefile_content = f.read()

        with open(self.workflow_path, "r", encoding="utf-8") as f:
            self.workflow_content = f.read()

    def test_01_all_proposed_files_exist(self):
        self.assertTrue(os.path.isfile(self.cmake_path))
        self.assertTrue(os.path.isfile(self.makefile_path))
        self.assertTrue(os.path.isfile(self.workflow_path))

    def test_02_cmake_translation_units_and_includes(self):
        # 1. C99 Standard
        self.assertIn("set(CMAKE_C_STANDARD 99)", self.cmake_content)
        self.assertIn("set(CMAKE_C_STANDARD_REQUIRED ON)", self.cmake_content)

        # 2. Include directory
        self.assertIn("include_directories(src)", self.cmake_content)

        # 3. All 11 subsystem translation units
        subsystems = [
            "src/core/runtime.c",
            "src/platform/platform_desktop.c",
            "src/world/terrain.c",
            "src/world/chunk.c",
            "src/world/mesher.c",
            "src/gameplay/physics.c",
            "src/gameplay/raycast.c",
            "src/gameplay/interaction.c",
            "src/gameplay/inventory.c",
            "src/assets/assets.c",
            "src/audio/synthesizer.c"
        ]
        for src in subsystems:
            self.assertIn(src, self.cmake_content, f"CMake must include {src}")

        # 4. Main file and headless target
        self.assertIn("src/main.c", self.cmake_content)
        self.assertIn("add_executable(minecraft_headless", self.cmake_content)
        self.assertIn("HEADLESS_ONLY", self.cmake_content)
        self.assertIn("add_test(NAME TestM1 COMMAND minecraft_headless --test-m1)", self.cmake_content)

    def test_03_makefile_translation_units_and_flags(self):
        # 1. CFLAGS standard and include path
        self.assertIn("-std=c99", self.makefile_content)
        self.assertIn("-Isrc", self.makefile_content)

        # 2. All 11 subsystem translation units
        subsystems = [
            "src/core/runtime.c",
            "src/platform/platform_desktop.c",
            "src/world/terrain.c",
            "src/world/chunk.c",
            "src/world/mesher.c",
            "src/gameplay/physics.c",
            "src/gameplay/raycast.c",
            "src/gameplay/interaction.c",
            "src/gameplay/inventory.c",
            "src/assets/assets.c",
            "src/audio/synthesizer.c"
        ]
        for src in subsystems:
            self.assertIn(src, self.makefile_content, f"Makefile must include {src}")

        # 3. Targets and definitions
        self.assertIn("HEADLESS_ONLY", self.makefile_content)
        self.assertIn("minecraft_headless", self.makefile_content)
        self.assertIn("$(TARGET_HEADLESS) --test-m1", self.makefile_content)

        # 4. OS libraries
        for lib in ["-lopengl32", "-lgdi32", "-lwinmm", "-luser32", "-lshell32"]:
            self.assertIn(lib, self.makefile_content)
        for lib in ["-lGL", "-lm", "-lpthread", "-ldl", "-lrt", "-lX11"]:
            self.assertIn(lib, self.makefile_content)

    def test_04_ci_yaml_matrix_and_triggers(self):
        data = yaml.safe_load(self.workflow_content)
        self.assertEqual(data["name"], "Build & Universal Distribution Release")
        triggers = data.get("on") or data.get(True)
        self.assertIn("push", triggers)
        self.assertIn("pull_request", triggers)
        self.assertIn("v*", triggers["push"]["tags"])

        # Matrix platforms
        matrix = data["jobs"]["build"]["strategy"]["matrix"]["include"]
        self.assertEqual(len(matrix), 3)
        targets = {m["target-name"]: m for m in matrix}
        self.assertIn("windows-x64", targets)
        self.assertIn("linux-x64", targets)
        self.assertIn("macos-universal", targets)

    def test_05_ci_no_invalid_lib_or_raylib_paths(self):
        # Must have zero references to non-existent lib/ directory
        self.assertNotIn("-Llib", self.workflow_content)
        self.assertNotIn("lib/windows", self.workflow_content)
        self.assertNotIn("lib/linux", self.workflow_content)
        self.assertNotIn("lib/macos", self.workflow_content)

        # Must have zero references to -lraylib since raylib is not installed
        self.assertNotIn("-lraylib", self.workflow_content)

    def test_06_ci_source_expansion_and_headless_defines(self):
        expected_sources = "src/main.c src/core/*.c src/platform/*.c src/world/*.c src/gameplay/*.c src/assets/*.c src/audio/*.c"
        # Windows step
        self.assertIn(expected_sources, self.workflow_content)
        # Headless define
        self.assertIn("-DHEADLESS_ONLY", self.workflow_content)
        # Platform desktop define
        self.assertIn("-DPLATFORM_DESKTOP", self.workflow_content)
        # Include flag
        self.assertIn("-Isrc", self.workflow_content)

    def test_07_ci_test_execution_gate(self):
        # Must have test execution step
        self.assertIn("Run Test Suites & Binary Verification", self.workflow_content)
        self.assertIn("--test-m1", self.workflow_content)
        self.assertIn("tests/test_runner.py", self.workflow_content)
        self.assertIn("python -m unittest", self.workflow_content)

    def test_08_ci_platform_specific_audits_and_libraries(self):
        # Windows static CRT and libs
        self.assertIn("-static-libgcc -static", self.workflow_content)
        for lib in ["-lopengl32", "-lgdi32", "-lwinmm", "-luser32", "-lshell32"]:
            self.assertIn(lib, self.workflow_content)
        self.assertTrue("dumpbin /dependents" in self.workflow_content or "objdump -p" in self.workflow_content)

        # Linux libs and ldd
        for lib in ["-lGL", "-lm", "-lpthread", "-ldl", "-lrt", "-lX11"]:
            self.assertIn(lib, self.workflow_content)
        self.assertIn("ldd build/minecraft", self.workflow_content)

        # macOS targets and lipo
        self.assertIn("target x86_64-apple-macos11.0", self.workflow_content)
        self.assertIn("target arm64-apple-macos11.0", self.workflow_content)
        self.assertIn("lipo -create", self.workflow_content)
        self.assertIn("strip -x build/minecraft", self.workflow_content)
        self.assertIn("lipo -info", self.workflow_content)
        self.assertIn("otool -L", self.workflow_content)

    def test_09_ponytail_comments_present(self):
        self.assertIn("ponytail:", self.cmake_content)
        self.assertIn("ponytail:", self.makefile_content)
        self.assertIn("ponytail:", self.workflow_content)

if __name__ == "__main__":
    unittest.main()
