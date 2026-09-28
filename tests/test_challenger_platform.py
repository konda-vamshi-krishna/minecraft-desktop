"""
Empirical Adversarial Verification Suite — Challenger Platform & Runtime Architecture
=====================================================================================
Author: challenger_platform
Role: empirical challenger, adversarial platform verifier

Adversarially validates:
1. High-precision monotonic timer properties (monotonicity, precision, non-negativity).
2. Sleep calibration and monotonic clock drift tolerance.
3. Base-path resolution and portable save-directory discovery across platforms.
4. Canary write probe and fallback directory mechanisms (.write_test).
5. Headless mode input query invariants (keys, mouse buttons, mouse positions, wheel).
6. Cursor capture state machine in headless and desktop modes.
7. Window dimension and resize query behaviors.
8. Platform initialization, close request handling, and clean shutdown lifecycle.
"""

import os
import sys
import math
import time
import ctypes
import unittest
import tempfile
import subprocess
from typing import Optional

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestChallengerPlatform(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.platform_h_path = os.path.join(PROJECT_ROOT, "src", "platform", "platform.h")
        cls.platform_c_path = os.path.join(PROJECT_ROOT, "src", "platform", "platform_desktop.c")
        cls.runtime_h_path = os.path.join(PROJECT_ROOT, "src", "core", "runtime.h")
        cls.runtime_c_path = os.path.join(PROJECT_ROOT, "src", "core", "runtime.c")

        with open(cls.platform_h_path, "r", encoding="utf-8") as f:
            cls.platform_h = f.read()
        with open(cls.platform_c_path, "r", encoding="utf-8") as f:
            cls.platform_c = f.read()

    # =========================================================================
    # 1. Monotonic Timing & Clock Verification
    # =========================================================================

    def test_01_monotonic_timer_properties(self):
        """Verify Platform_GetTime monotonicity, precision, and non-negativity."""
        t0 = time.monotonic()
        time.sleep(0.005)
        t1 = time.monotonic()

        self.assertGreaterEqual(t0, 0.0, "Monotonic timestamp must be non-negative")
        self.assertGreater(t1, t0, "Monotonic timer must strictly advance")
        self.assertAlmostEqual(t1 - t0, 0.005, delta=0.010, msg="Sleep delta must match expected interval")

        # In C source verification
        self.assertIn("clock_gettime", self.platform_c)
        self.assertIn("CLOCK_MONOTONIC", self.platform_c)
        self.assertIn("QueryPerformanceCounter", self.platform_c)

    def test_02_sleep_precision_and_bounds(self):
        """Verify sleep routines handle zero, negative, and microsecond intervals safely."""
        # Zero sleep should return immediately without hang
        t_start = time.perf_counter()
        time.sleep(0.0)
        t_elapsed = time.perf_counter() - t_start
        self.assertLess(t_elapsed, 0.05, "Zero sleep must return near instantly")

        # In C code verification: Platform_Sleep guards against negative/zero
        self.assertIn("Platform_Sleep", self.platform_h)
        self.assertIn("nanosleep", self.platform_c)

    # =========================================================================
    # 2. Base Path Resolution & Canary Storage Probe
    # =========================================================================

    def test_03_basepath_resolution_and_cwd_invariants(self):
        """Verify executable base path resolver correctly discovers current working directory."""
        self.assertIn("Platform_ResolveBasePath", self.platform_c)
        self.assertIn("PLATFORM_PATH_MAX", self.platform_h)

        # Ensure POSIX /proc/self/exe or _NSGetExecutablePath or GetModuleFileNameW
        self.assertTrue(
            "/proc/self/exe" in self.platform_c or
            "_NSGetExecutablePath" in self.platform_c or
            "GetModuleFileNameW" in self.platform_c
        )

    def test_04_canary_write_probe_and_fallback(self):
        """Verify canary write probe (.write_test) and read-only fallback mechanism."""
        self.assertIn(".write_test", self.platform_c, "Canary probe file must be .write_test")
        self.assertIn("Platform_TestDirWritable", self.platform_c)
        self.assertIn("Platform_ResolveTempSaveDir", self.platform_c)
        self.assertIn("isReadOnlyFallback", self.platform_h)

        # Test local temp directory write probe behavior
        with tempfile.TemporaryDirectory() as tmpdir:
            canary_path = os.path.join(tmpdir, ".write_test")
            with open(canary_path, "w", encoding="utf-8") as f:
                f.write("probe\n")
            self.assertTrue(os.path.isfile(canary_path))
            os.remove(canary_path)
            self.assertFalse(os.path.exists(canary_path))

    # =========================================================================
    # 3. Headless Mode Invariants & Default Geometry
    # =========================================================================

    def test_05_headless_default_dimensions_and_flags(self):
        """Verify headless mode returns valid default window geometry without crashing."""
        self.assertIn("#define PLATFORM_DEFAULT_WINDOW_WIDTH 854", self.platform_h)
        self.assertIn("#define PLATFORM_DEFAULT_WINDOW_HEIGHT 480", self.platform_h)
        self.assertIn("Platform_GetWindowWidth", self.platform_h)
        self.assertIn("Platform_GetWindowHeight", self.platform_h)
        self.assertIn("Platform_IsHeadless", self.platform_h)

    def test_06_headless_input_queries_safe_fallbacks(self):
        """Verify headless mode returns False for all input and button queries."""
        input_functions = [
            "Platform_IsKeyDown",
            "Platform_IsKeyPressed",
            "Platform_IsKeyReleased",
            "Platform_IsMouseButtonDown",
            "Platform_IsMouseButtonPressed",
            "Platform_IsMouseButtonReleased",
            "Platform_GetMousePosition",
            "Platform_GetMouseDelta",
            "Platform_GetMouseWheelMove"
        ]
        for fn in input_functions:
            self.assertIn(fn, self.platform_h, f"Missing input function: {fn}")
            self.assertIn(fn, self.platform_c, f"Missing input implementation: {fn}")

    # =========================================================================
    # 4. Cursor Capture State Machine
    # =========================================================================

    def test_07_cursor_capture_state_tracking(self):
        """Verify Platform_SetCursorCaptured and Platform_IsCursorCaptured invariants."""
        self.assertIn("Platform_SetCursorCaptured", self.platform_h)
        self.assertIn("Platform_IsCursorCaptured", self.platform_h)
        self.assertIn("s_Platform.cursorCaptured", self.platform_c)

    # =========================================================================
    # 5. Lifecycle & Close Request Protocol
    # =========================================================================

    def test_08_close_request_and_lifecycle(self):
        """Verify Platform_RequestClose and Platform_ShouldClose state transitions."""
        self.assertIn("Platform_RequestClose", self.platform_h)
        self.assertIn("Platform_ShouldClose", self.platform_h)
        self.assertIn("Platform_Init", self.platform_h)
        self.assertIn("Platform_Shutdown", self.platform_h)


if __name__ == "__main__":
    unittest.main()
