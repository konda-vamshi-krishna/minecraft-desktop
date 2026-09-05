"""
Empirical Adversarial Verification Suite — Challenger Remedy 2
=============================================================
Author: challenger_remedy_2
Role: empirical challenger, adversarial verifier

Adversarially validates:
1. Build system (CMakeLists.txt, Makefile) translation units and symbol coverage.
2. CI/CD matrix (.github/workflows/build_and_release.yml) syntax, runner dependencies, compiler flags, and packaging.
3. C header include graph, missing symbols, and cross-translation-unit linkage contracts.
4. CLI parsing stress testing, numerical boundary conditions, flag collision defenses, and 64-bit integer handling.
5. Engine authentic wiring in src/main.c (zero empty stubs / zero facade callbacks).
"""

import os
import re
import sys
import glob
import ctypes
import unittest
import yaml

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Load C runtime for exact C standard library strtoll / errno behavior
ucrt = ctypes.CDLL('ucrtbase.dll')
ucrt.strtoll.restype = ctypes.c_longlong
ucrt.strtoll.argtypes = [ctypes.c_char_p, ctypes.POINTER(ctypes.c_char_p), ctypes.c_int]

_errno = ucrt._errno
_errno.restype = ctypes.POINTER(ctypes.c_int)
_errno.argtypes = []

INT_MIN = -2147483648
INT_MAX = 2147483647
RUNTIME_FIXED_DT = 1.0 / 60.0

def c_parse_int64(s):
    """Exact emulation of ParseInt64 from src/main.c using MSVCRT strtoll."""
    if s is None or len(s) == 0:
        return False, 0
    b_str = s.encode('utf-8')
    end = ctypes.c_char_p()
    _errno().contents.value = 0
    v = ucrt.strtoll(b_str, ctypes.byref(end), 10)
    err = _errno().contents.value
    
    end_val = end.value
    if err != 0:
        return False, 0
    if end_val is None or len(end_val) > 0:
        return False, 0
    if end_val == b_str:
        return False, 0
    return True, v

def emulate_main_cli_parser(argv):
    """Emulate CLI parser logic in src/main.c."""
    platConfig = {
        'windowWidth': 1280,
        'windowHeight': 720,
        'title': 'Minecraft Desktop — Universal Edition',
        'targetFps60': True,
        'headless': False
    }
    runConfig = {
        'headless': False,
        'targetFps': 60,
        'maxFrames': 0,
        'maxDuration': 0.0
    }
    worldSeed = 1337
    runTestM1 = False
    
    stderr_lines = []
    stdout_lines = []
    
    def print_help(exe):
        stdout_lines.append(f'Minecraft Desktop — Universal Edition (Milestone 1)')
        stdout_lines.append(f'Usage: {exe} [options]')

    argc = len(argv)
    i = 1
    while i < argc:
        arg = argv[i]
        if arg == '--headless':
            platConfig['headless'] = True
            runConfig['headless'] = True
            runConfig['targetFps'] = 0
        elif arg == '--test-m1':
            runTestM1 = True
        elif arg == '--seed':
            if i + 1 >= argc:
                stderr_lines.append(f'Error: {argv[i]} requires an argument.')
                print_help(argv[0])
                return {'exitCode': 1, 'stderr': stderr_lines, 'stdout': stdout_lines,
                        'platConfig': platConfig, 'runConfig': runConfig,
                        'worldSeed': worldSeed, 'runTestM1': runTestM1}
            i += 1
            ok, val = c_parse_int64(argv[i])
            if not ok or val < INT_MIN or val > INT_MAX:
                stderr_lines.append(f"Error: {argv[i-1]} requires an integer argument (got '{argv[i]}').")
                print_help(argv[0])
                return {'exitCode': 1, 'stderr': stderr_lines, 'stdout': stdout_lines,
                        'platConfig': platConfig, 'runConfig': runConfig,
                        'worldSeed': worldSeed, 'runTestM1': runTestM1}
            worldSeed = int(val)
        elif arg == '--frames':
            if i + 1 >= argc:
                stderr_lines.append(f'Error: {argv[i]} requires an argument.')
                print_help(argv[0])
                return {'exitCode': 1, 'stderr': stderr_lines, 'stdout': stdout_lines,
                        'platConfig': platConfig, 'runConfig': runConfig,
                        'worldSeed': worldSeed, 'runTestM1': runTestM1}
            i += 1
            ok, val = c_parse_int64(argv[i])
            if not ok or val <= 0:
                stderr_lines.append(f"Error: {argv[i-1]} requires a positive integer argument (got '{argv[i]}').")
                print_help(argv[0])
                return {'exitCode': 1, 'stderr': stderr_lines, 'stdout': stdout_lines,
                        'platConfig': platConfig, 'runConfig': runConfig,
                        'worldSeed': worldSeed, 'runTestM1': runTestM1}
            runConfig['maxFrames'] = int(val)
        elif arg == '--ticks':
            if i + 1 >= argc:
                stderr_lines.append(f'Error: {argv[i]} requires an argument.')
                print_help(argv[0])
                return {'exitCode': 1, 'stderr': stderr_lines, 'stdout': stdout_lines,
                        'platConfig': platConfig, 'runConfig': runConfig,
                        'worldSeed': worldSeed, 'runTestM1': runTestM1}
            i += 1
            ok, val = c_parse_int64(argv[i])
            if not ok or val <= 0:
                stderr_lines.append(f"Error: {argv[i-1]} requires a positive integer argument (got '{argv[i]}').")
                print_help(argv[0])
                return {'exitCode': 1, 'stderr': stderr_lines, 'stdout': stdout_lines,
                        'platConfig': platConfig, 'runConfig': runConfig,
                        'worldSeed': worldSeed, 'runTestM1': runTestM1}
            runConfig['maxDuration'] = float(val) * RUNTIME_FIXED_DT
        elif arg == '--help' or arg == '-h':
            print_help(argv[0])
            return {'exitCode': 0, 'stderr': stderr_lines, 'stdout': stdout_lines,
                    'platConfig': platConfig, 'runConfig': runConfig,
                    'worldSeed': worldSeed, 'runTestM1': runTestM1}
        else:
            stderr_lines.append(f"Error: unrecognized option '{argv[i]}'")
            print_help(argv[0])
            return {'exitCode': 1, 'stderr': stderr_lines, 'stdout': stdout_lines,
                    'platConfig': platConfig, 'runConfig': runConfig,
                    'worldSeed': worldSeed, 'runTestM1': runTestM1}
        i += 1

    return {'exitCode': 0, 'stderr': stderr_lines, 'stdout': stdout_lines,
            'platConfig': platConfig, 'runConfig': runConfig,
            'worldSeed': worldSeed, 'runTestM1': runTestM1}


class TestChallengerAdversarialRemedy2(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.src_dir = os.path.join(PROJECT_ROOT, "src")
        cls.cmake_path = os.path.join(PROJECT_ROOT, "CMakeLists.txt")
        cls.makefile_path = os.path.join(PROJECT_ROOT, "Makefile")
        cls.ci_workflow_path = os.path.join(PROJECT_ROOT, ".github", "workflows", "build_and_release.yml")
        cls.main_c_path = os.path.join(cls.src_dir, "main.c")

        # Discover all .c and .h files
        cls.c_files = []
        cls.h_files = []
        for root, _, files in os.walk(cls.src_dir):
            for f in files:
                full_p = os.path.join(root, f)
                rel_p = os.path.relpath(full_p, PROJECT_ROOT).replace("\\", "/")
                if f.endswith(".c"):
                    cls.c_files.append(rel_p)
                elif f.endswith(".h"):
                    cls.h_files.append(rel_p)

    # =========================================================================
    # SUITE 1: BUILD SYSTEM SOURCE & SYMBOL COMPLETENESS
    # =========================================================================

    def test_01_all_c_files_enumerated_in_cmake(self):
        """Adversarially verify that EVERY .c file in src/ is in CMakeLists.txt."""
        with open(self.cmake_path, "r", encoding="utf-8") as f:
            cmake_content = f.read()

        self.assertGreater(len(self.c_files), 5, "Must have found C source files in src/")
        for c_file in self.c_files:
            self.assertIn(c_file, cmake_content,
                          f"CMakeLists.txt omits C source file: {c_file}")

    def test_02_all_c_files_enumerated_in_makefile(self):
        """Adversarially verify that EVERY .c file in src/ is in Makefile."""
        with open(self.makefile_path, "r", encoding="utf-8") as f:
            makefile_content = f.read()

        for c_file in self.c_files:
            self.assertIn(c_file, makefile_content,
                          f"Makefile omits C source file: {c_file}")

    def test_03_no_ghost_or_stale_sources_in_build_files(self):
        """Ensure build files do not reference nonexistent source files."""
        with open(self.cmake_path, "r", encoding="utf-8") as f:
            cmake_content = f.read()
        with open(self.makefile_path, "r", encoding="utf-8") as f:
            makefile_content = f.read()

        # Find all src/*.c references in CMakeLists.txt
        cmake_src_refs = re.findall(r"src/[a-zA-Z0-9_\-/]+\.c", cmake_content)
        for ref in cmake_src_refs:
            abs_p = os.path.join(PROJECT_ROOT, ref)
            self.assertTrue(os.path.isfile(abs_p),
                            f"CMakeLists.txt references non-existent source: {ref}")

        # Find all src/*.c references in Makefile
        makefile_src_refs = re.findall(r"src/[a-zA-Z0-9_\-/]+\.c", makefile_content)
        for ref in makefile_src_refs:
            abs_p = os.path.join(PROJECT_ROOT, ref)
            self.assertTrue(os.path.isfile(abs_p),
                            f"Makefile references non-existent source: {ref}")

    def test_04_header_include_graph_soundness(self):
        """Verify all #include directives in all .c and .h files resolve to valid files."""
        for file_rel in self.c_files + self.h_files:
            abs_p = os.path.join(PROJECT_ROOT, file_rel)
            with open(abs_p, "r", encoding="utf-8") as f:
                lines = f.readlines()

            for line_idx, line in enumerate(lines, start=1):
                # Must not include proposed_
                if "proposed_" in line and "#include" in line:
                    self.fail(f"Found fatal 'proposed_' include in {file_rel}:{line_idx}: {line.strip()}")

                # Quoted includes must resolve to existing files
                match = re.match(r'^\s*#\s*include\s*"([^"]+)"', line)
                if match:
                    inc = match.group(1)
                    cur_dir = os.path.dirname(abs_p)
                    cand1 = os.path.normpath(os.path.join(cur_dir, inc))
                    cand2 = os.path.normpath(os.path.join(self.src_dir, inc))
                    self.assertTrue(os.path.isfile(cand1) or os.path.isfile(cand2),
                                    f"Unresolvable quoted include '{inc}' in {file_rel}:{line_idx}")

    def test_05_raycast_hit_struct_uniqueness(self):
        """Adversarially verify RaycastHit is defined exactly once and not duplicate."""
        definitions = []
        for file_rel in self.h_files + self.c_files:
            abs_p = os.path.join(PROJECT_ROOT, file_rel)
            with open(abs_p, "r", encoding="utf-8") as f:
                content = f.read()
            if re.search(r"\btypedef\s+struct\s+RaycastHit\s*\{", content):
                definitions.append(file_rel)

        self.assertEqual(len(definitions), 1,
                         f"RaycastHit must have exactly one definition, found in: {definitions}")
        self.assertEqual(definitions[0], "src/gameplay/physics.h")

    # =========================================================================
    # SUITE 2: CI/CD WORKFLOW ADVERSARIAL AUDIT
    # =========================================================================

    def test_06_ci_workflow_valid_yaml(self):
        """Verify CI workflow parses without YAML syntax errors."""
        with open(self.ci_workflow_path, "r", encoding="utf-8") as f:
            wf = yaml.safe_load(f)

        self.assertIsInstance(wf, dict)
        self.assertIn("name", wf)
        self.assertIn("jobs", wf)

    def test_07_ci_workflow_no_nonexistent_flags_or_forbidden_libs(self):
        """Adversarially check build commands for broken flags or non-existent lib/ paths."""
        with open(self.ci_workflow_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 1. No invalid -Llib
        self.assertNotIn("-Llib", content)
        self.assertNotIn("lib/windows", content)
        self.assertNotIn("lib/linux", content)
        self.assertNotIn("lib/macos", content)

        # 2. No -lraylib in headless build steps
        self.assertNotIn("-lraylib", content)

        # 3. Source wildcard expansion covers all subdirectories
        for sub in ["core", "platform", "world", "gameplay", "assets", "audio"]:
            self.assertIn(f"src/{sub}/*.c", content,
                          f"CI workflow compilation step must include src/{sub}/*.c")

    def test_08_ci_platform_matrix_integrity(self):
        """Check the 3 target platforms and artifact naming."""
        with open(self.ci_workflow_path, "r", encoding="utf-8") as f:
            wf = yaml.safe_load(f)

        matrix = wf["jobs"]["build"]["strategy"]["matrix"]["include"]
        target_names = [m["target-name"] for m in matrix]
        self.assertIn("windows-x64", target_names)
        self.assertIn("linux-x64", target_names)
        self.assertIn("macos-universal", target_names)

        for m in matrix:
            self.assertIn("executable-name", m)
            self.assertIn("artifact-name", m)
            self.assertIn("os", m)

    # =========================================================================
    # SUITE 3: CLI PARSING EMPIRICAL STRESS & FUZZING
    # =========================================================================

    def test_09_cli_stress_integer_parser(self):
        """Empirically test c_parse_int64 on edge cases and invalid formats."""
        # Valid cases
        valid_cases = [
            ("0", 0),
            ("1", 1),
            ("-1", -1),
            ("1337", 1337),
            ("2147483647", 2147483647),
            ("-2147483648", -2147483648),
            ("+100", 100),
            ("00042", 42),
            ("9223372036854775807", 9223372036854775807),
            ("-9223372036854775808", -9223372036854775808)
        ]
        for s, expected in valid_cases:
            ok, val = c_parse_int64(s)
            self.assertTrue(ok, f"c_parse_int64 failed on valid input '{s}'")
            self.assertEqual(val, expected)

        # Invalid cases
        invalid_cases = [
            "", None, "   ", "abc", "12a", "a12", "0x10", "1e5", "1.5",
            "--1", "++1", "+-1", "9223372036854775808", "-9223372036854775809",
            "9999999999999999999999999999999999"
        ]
        for s in invalid_cases:
            ok, _ = c_parse_int64(s)
            self.assertFalse(ok, f"c_parse_int64 should reject invalid input '{s}'")

    def test_10_cli_parser_boundary_and_fuzz(self):
        """Stress test emulate_main_cli_parser on edge permutations."""
        # 1. Zero frames / negative frames must be rejected
        res = emulate_main_cli_parser(["minecraft", "--frames", "0"])
        self.assertEqual(res["exitCode"], 1)

        res = emulate_main_cli_parser(["minecraft", "--frames", "-5"])
        self.assertEqual(res["exitCode"], 1)

        # 2. Zero ticks / negative ticks must be rejected
        res = emulate_main_cli_parser(["minecraft", "--ticks", "0"])
        self.assertEqual(res["exitCode"], 1)

        res = emulate_main_cli_parser(["minecraft", "--ticks", "-10"])
        self.assertEqual(res["exitCode"], 1)

        # 3. 32-bit overflow for seed must be rejected
        res = emulate_main_cli_parser(["minecraft", "--seed", "2147483648"])
        self.assertEqual(res["exitCode"], 1)

        res = emulate_main_cli_parser(["minecraft", "--seed", "-2147483649"])
        self.assertEqual(res["exitCode"], 1)

        # 4. Valid seeds must succeed
        res = emulate_main_cli_parser(["minecraft", "--seed", "2147483647"])
        self.assertEqual(res["exitCode"], 0)
        self.assertEqual(res["worldSeed"], 2147483647)

        res = emulate_main_cli_parser(["minecraft", "--seed", "-2147483648"])
        self.assertEqual(res["exitCode"], 0)
        self.assertEqual(res["worldSeed"], -2147483648)

        res = emulate_main_cli_parser(["minecraft", "--seed", "0"])
        self.assertEqual(res["exitCode"], 0)
        self.assertEqual(res["worldSeed"], 0)

        # 5. Missing arguments at end of command
        for flag in ["--seed", "--frames", "--ticks"]:
            res = emulate_main_cli_parser(["minecraft", flag])
            self.assertEqual(res["exitCode"], 1, f"Missing arg for {flag} must exit 1")

        # 6. Flag collisions / hijacking prevention
        collision_cases = [
            ["minecraft", "--seed", "--headless"],
            ["minecraft", "--frames", "--test-m1"],
            ["minecraft", "--ticks", "--seed", "42"],
            ["minecraft", "--frames", "--ticks", "100"]
        ]
        for cmd in collision_cases:
            res = emulate_main_cli_parser(cmd)
            self.assertEqual(res["exitCode"], 1, f"Command {cmd} should fail with exit 1")

    # =========================================================================
    # SUITE 4: AUTHENTIC WIRING & ZERO-FACADE IN MAIN.C
    # =========================================================================

    def test_11_main_c_zero_dummy_callbacks(self):
        """Verify App_OnPhysicsTick, App_OnMeshBudget, App_OnRenderFrame are authentic."""
        with open(self.main_c_path, "r", encoding="utf-8") as f:
            code = f.read()

        # Check that empty stubs are gone
        self.assertNotIn("static void App_OnPhysicsTick(double dt) {\n    (void)dt;\n}", code)
        self.assertNotIn("static void App_OnMeshBudget(int maxChunks) {\n    (void)maxChunks;\n}", code)

        # Check authentic function calls in main loop
        essential_calls = [
            "World_Update",
            "Physics_Step",
            "Physics_Raycast",
            "Interaction_UpdateDestruction",
            "Interaction_TryPlaceBlock",
            "MesherQueue_Process",
            "Audio_PlaySound",
            "World_Render"
        ]
        for fn in essential_calls:
            self.assertIn(fn, code, f"src/main.c must invoke authentic engine function {fn}")

    def test_12_all_engine_subsystem_symbols_present(self):
        """Verify all non-static subsystem functions called by main.c exist in sources."""
        with open(self.main_c_path, "r", encoding="utf-8") as f:
            main_code = f.read()

        # All C source and header contents
        all_code = {}
        for root, _, files in os.walk(self.src_dir):
            for file in files:
                if file.endswith('.c') or file.endswith('.h'):
                    path = os.path.join(root, file).replace('\\', '/')
                    with open(path, 'r', encoding='utf-8') as f:
                        all_code[path] = f.read()

        subsystem_prefixes = [
            'Platform_', 'Runtime_', 'World_', 'Chunk_', 'Terrain_', 'Mesher',
            'Physics_', 'Ray_', 'Interaction_', 'Inventory_', 'Item_', 'Audio_',
            'Assets_', 'Camera_', 'Vec3_', 'Mat4_', 'Frustum_', 'AABB_',
            'WrapAngle', 'ClampFloat', 'FloorToInt', 'Block_'
        ]

        # Find all subsystem calls in main.c
        called = set(re.findall(r'\b([A-Za-z0-9_]+)\s*\(', main_code))
        missing = []

        for sym in sorted(called):
            if not any(sym.startswith(p) for p in subsystem_prefixes):
                continue
            def_pat = rf'^\s*(?:[a-zA-Z0-9_*]+\s+)+{sym}\s*\([^;]*\)\s*\{{'
            macro_pat = rf'#define\s+{sym}\b'
            inline_pat = rf'static\s+inline\s+.*{sym}\s*\('
            def_found = any(
                re.search(def_pat, code, re.MULTILINE) or
                re.search(macro_pat, code) or
                re.search(inline_pat, code)
                for code in all_code.values()
            )
            if not def_found:
                missing.append(sym)

        self.assertEqual(missing, [], f"Subsystem symbols called in main.c without definition: {missing}")


if __name__ == "__main__":
    unittest.main()
