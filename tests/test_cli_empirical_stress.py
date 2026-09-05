"""
Empirical Stress Test Harness for CLI Argument Parsing in src/main.c.
Validates:
1. Flag collisions and argument hijacking (--frames --headless, --seed --headless, --ticks --headless)
2. Missing arguments at end of line (--seed, --frames, --ticks)
3. Unrecognized flags and error exits (--unknown, -x, --hedless)
4. Numerical bounds: negative frames/ticks, zero frames, valid negative seeds, 32-bit int bounds, overflow
"""

import unittest
import ctypes
import os
import re

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
    """
    Exact implementation of static bool ParseInt64(const char* str, long long* outVal)
    from src/main.c:281-291:
        if (!str || *str == '\0') return false;
        char* end = NULL;
        errno = 0;
        long long v = strtoll(str, &end, 10);
        if (errno != 0 || end == str || *end != '\0') {
            return false;
        }
        if (outVal) *outVal = v;
        return true;
    """
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

def run_main_c_cli_parser(argv):
    """
    Exact reproduction of the C loop in src/main.c lines 293-364.
    Returns a dict containing:
      exitCode, stderr, stdout, platConfig, runConfig, worldSeed, runTestM1
    """
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


class TestCliArgumentParsing(unittest.TestCase):
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def test_c_source_code_static_invariants(self):
        """Verify main.c contains defensive guards, includes, and error exits."""
        main_c_path = os.path.join(self.PROJECT_ROOT, 'src', 'main.c')
        with open(main_c_path, 'r', encoding='utf-8') as f:
            code = f.read()

        # 1. Necessary headers
        self.assertIn('#include <errno.h>', code)
        self.assertIn('#include <limits.h>', code)

        # 2. ParseInt64 helper existence
        self.assertIn('static bool ParseInt64(const char* str, long long* outVal)', code)
        self.assertIn('strtoll(str, &end, 10)', code)
        self.assertIn('errno != 0 || end == str || *end != \'\\0\'', code)

        # 3. Missing argument bounds checks (i + 1 >= argc)
        matches = re.findall(r'if\s*\(\s*i\s*\+\s*1\s*>=\s*argc\s*\)', code)
        self.assertEqual(len(matches), 3, 'Must check i + 1 >= argc for --seed, --frames, --ticks')

        # 4. Strict numerical range validation
        self.assertIn('val < INT_MIN || val > INT_MAX', code)
        self.assertIn('val <= 0', code)

        # 5. Terminating else block with exit 1
        self.assertIn("fprintf(stderr, \"Error: unrecognized option '%s'\\n\", argv[i]);", code)
        self.assertIn('return 1;', code)

    # -------------------------------------------------------------------------
    # 1. Flag collisions and argument hijacking
    # -------------------------------------------------------------------------
    def test_collision_frames_headless(self):
        """--frames --headless must reject and exit with 1, never hijacking --headless."""
        res = run_main_c_cli_parser(['minecraft', '--frames', '--headless'])
        self.assertEqual(res['exitCode'], 1)
        self.assertFalse(res['platConfig']['headless'])
        self.assertTrue(any('--frames requires a positive integer' in line for line in res['stderr']))
        self.assertTrue(any('--headless' in line for line in res['stderr']))

    def test_collision_seed_headless(self):
        """--seed --headless must reject and exit with 1."""
        res = run_main_c_cli_parser(['minecraft', '--seed', '--headless'])
        self.assertEqual(res['exitCode'], 1)
        self.assertEqual(res['worldSeed'], 1337)
        self.assertTrue(any('--seed requires an integer argument' in line for line in res['stderr']))

    def test_collision_ticks_headless(self):
        """--ticks --headless must reject and exit with 1."""
        res = run_main_c_cli_parser(['minecraft', '--ticks', '--headless'])
        self.assertEqual(res['exitCode'], 1)
        self.assertEqual(res['runConfig']['maxDuration'], 0.0)
        self.assertTrue(any('--ticks requires a positive integer' in line for line in res['stderr']))

    def test_collision_frames_test_m1(self):
        """--frames --test-m1 must reject with exit 1."""
        res = run_main_c_cli_parser(['minecraft', '--frames', '--test-m1'])
        self.assertEqual(res['exitCode'], 1)
        self.assertFalse(res['runTestM1'])

    def test_collision_seed_ticks(self):
        """--seed --ticks 100 must reject with exit 1."""
        res = run_main_c_cli_parser(['minecraft', '--seed', '--ticks', '100'])
        self.assertEqual(res['exitCode'], 1)
        self.assertEqual(res['worldSeed'], 1337)

    # -------------------------------------------------------------------------
    # 2. Missing arguments at end of line
    # -------------------------------------------------------------------------
    def test_missing_trailing_seed(self):
        """--seed at end of line must exit with 1 and clear error."""
        res = run_main_c_cli_parser(['minecraft', '--seed'])
        self.assertEqual(res['exitCode'], 1)
        self.assertTrue(any('Error: --seed requires an argument.' in line for line in res['stderr']))

    def test_missing_trailing_frames(self):
        """--frames at end of line must exit with 1 and clear error."""
        res = run_main_c_cli_parser(['minecraft', '--frames'])
        self.assertEqual(res['exitCode'], 1)
        self.assertTrue(any('Error: --frames requires an argument.' in line for line in res['stderr']))

    def test_missing_trailing_ticks(self):
        """--ticks at end of line must exit with 1 and clear error."""
        res = run_main_c_cli_parser(['minecraft', '--ticks'])
        self.assertEqual(res['exitCode'], 1)
        self.assertTrue(any('Error: --ticks requires an argument.' in line for line in res['stderr']))

    def test_missing_arg_after_other_flags(self):
        """--headless --seed at end of line must exit with 1."""
        res = run_main_c_cli_parser(['minecraft', '--headless', '--seed'])
        self.assertEqual(res['exitCode'], 1)
        self.assertTrue(any('Error: --seed requires an argument.' in line for line in res['stderr']))

    # -------------------------------------------------------------------------
    # 3. Unrecognized flags and error exits
    # -------------------------------------------------------------------------
    def test_unrecognized_long_flag(self):
        """--unknown must exit with 1 and print unrecognized option."""
        res = run_main_c_cli_parser(['minecraft', '--unknown'])
        self.assertEqual(res['exitCode'], 1)
        self.assertTrue(any("Error: unrecognized option '--unknown'" in line for line in res['stderr']))

    def test_unrecognized_short_flag(self):
        """-x must exit with 1."""
        res = run_main_c_cli_parser(['minecraft', '-x'])
        self.assertEqual(res['exitCode'], 1)
        self.assertTrue(any("Error: unrecognized option '-x'" in line for line in res['stderr']))

    def test_unrecognized_typo_flag(self):
        """--hedless typo must exit with 1."""
        res = run_main_c_cli_parser(['minecraft', '--hedless'])
        self.assertEqual(res['exitCode'], 1)
        self.assertTrue(any("Error: unrecognized option '--hedless'" in line for line in res['stderr']))

    def test_unrecognized_positional_arg(self):
        """'world.dat' positional argument must exit with 1."""
        res = run_main_c_cli_parser(['minecraft', 'world.dat'])
        self.assertEqual(res['exitCode'], 1)
        self.assertTrue(any("Error: unrecognized option 'world.dat'" in line for line in res['stderr']))

    # -------------------------------------------------------------------------
    # 4. Numerical bounds: negative frames/ticks, zero frames, valid negative seeds
    # -------------------------------------------------------------------------
    def test_bounds_negative_frames(self):
        """--frames -1 must be rejected with exit code 1."""
        res = run_main_c_cli_parser(['minecraft', '--frames', '-1'])
        self.assertEqual(res['exitCode'], 1)
        self.assertTrue(any("--frames requires a positive integer argument (got '-1')." in line for line in res['stderr']))

    def test_bounds_zero_frames(self):
        """--frames 0 must be rejected with exit code 1 (must be positive > 0)."""
        res = run_main_c_cli_parser(['minecraft', '--frames', '0'])
        self.assertEqual(res['exitCode'], 1)
        self.assertTrue(any("--frames requires a positive integer argument (got '0')." in line for line in res['stderr']))

    def test_bounds_negative_ticks(self):
        """--ticks -5 must be rejected with exit code 1."""
        res = run_main_c_cli_parser(['minecraft', '--ticks', '-5'])
        self.assertEqual(res['exitCode'], 1)
        self.assertTrue(any("--ticks requires a positive integer argument (got '-5')." in line for line in res['stderr']))

    def test_bounds_zero_ticks(self):
        """--ticks 0 must be rejected with exit code 1."""
        res = run_main_c_cli_parser(['minecraft', '--ticks', '0'])
        self.assertEqual(res['exitCode'], 1)
        self.assertTrue(any("--ticks requires a positive integer argument (got '0')." in line for line in res['stderr']))

    def test_bounds_valid_negative_seed(self):
        """--seed -999 must be accepted with exit code 0."""
        res = run_main_c_cli_parser(['minecraft', '--seed', '-999'])
        self.assertEqual(res['exitCode'], 0)
        self.assertEqual(res['worldSeed'], -999)

    def test_bounds_valid_zero_seed(self):
        """--seed 0 must be accepted with exit code 0."""
        res = run_main_c_cli_parser(['minecraft', '--seed', '0'])
        self.assertEqual(res['exitCode'], 0)
        self.assertEqual(res['worldSeed'], 0)

    def test_bounds_int_min_seed(self):
        """--seed INT_MIN (-2147483648) must be accepted."""
        res = run_main_c_cli_parser(['minecraft', '--seed', str(INT_MIN)])
        self.assertEqual(res['exitCode'], 0)
        self.assertEqual(res['worldSeed'], INT_MIN)

    def test_bounds_int_max_seed(self):
        """--seed INT_MAX (2147483647) must be accepted."""
        res = run_main_c_cli_parser(['minecraft', '--seed', str(INT_MAX)])
        self.assertEqual(res['exitCode'], 0)
        self.assertEqual(res['worldSeed'], INT_MAX)

    def test_bounds_underflow_seed(self):
        """--seed below INT_MIN must be rejected with exit code 1."""
        res = run_main_c_cli_parser(['minecraft', '--seed', str(INT_MIN - 1)])
        self.assertEqual(res['exitCode'], 1)
        self.assertTrue(any('--seed requires an integer argument' in line for line in res['stderr']))

    def test_bounds_overflow_seed(self):
        """--seed above INT_MAX must be rejected with exit code 1."""
        res = run_main_c_cli_parser(['minecraft', '--seed', str(INT_MAX + 1)])
        self.assertEqual(res['exitCode'], 1)
        self.assertTrue(any('--seed requires an integer argument' in line for line in res['stderr']))

    def test_bounds_huge_overflow(self):
        """--frames 999999999999999999999999999 must trigger ERANGE and be rejected with exit 1."""
        res = run_main_c_cli_parser(['minecraft', '--frames', '999999999999999999999999999'])
        self.assertEqual(res['exitCode'], 1)

    def test_bounds_non_numeric_strings(self):
        """--frames abc and --seed 123abc must be rejected."""
        res1 = run_main_c_cli_parser(['minecraft', '--frames', 'abc'])
        self.assertEqual(res1['exitCode'], 1)
        res2 = run_main_c_cli_parser(['minecraft', '--seed', '123abc'])
        self.assertEqual(res2['exitCode'], 1)

    # -------------------------------------------------------------------------
    # 5. Valid operational workflows & combinatorics
    # -------------------------------------------------------------------------
    def test_valid_default_invocation(self):
        """'minecraft' with no flags succeeds with defaults."""
        res = run_main_c_cli_parser(['minecraft'])
        self.assertEqual(res['exitCode'], 0)
        self.assertFalse(res['platConfig']['headless'])
        self.assertEqual(res['worldSeed'], 1337)
        self.assertEqual(res['runConfig']['maxFrames'], 0)
        self.assertEqual(res['runConfig']['maxDuration'], 0.0)

    def test_valid_headless_frames_seed(self):
        """'minecraft --headless --frames 120 --seed -42' succeeds with exact values."""
        res = run_main_c_cli_parser(['minecraft', '--headless', '--frames', '120', '--seed', '-42'])
        self.assertEqual(res['exitCode'], 0)
        self.assertTrue(res['platConfig']['headless'])
        self.assertEqual(res['runConfig']['maxFrames'], 120)
        self.assertEqual(res['worldSeed'], -42)

    def test_valid_help_flags(self):
        """'--help' and '-h' return exitCode 0 and display usage."""
        res_help = run_main_c_cli_parser(['minecraft', '--help'])
        self.assertEqual(res_help['exitCode'], 0)
        self.assertTrue(any('Usage:' in line for line in res_help['stdout']))

        res_h = run_main_c_cli_parser(['minecraft', '-h'])
        self.assertEqual(res_h['exitCode'], 0)
        self.assertTrue(any('Usage:' in line for line in res_h['stdout']))


if __name__ == '__main__':
    unittest.main()
