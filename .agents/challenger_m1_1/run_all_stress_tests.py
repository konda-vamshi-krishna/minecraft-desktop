"""
Master Stress Test Harness for Milestone 1 Empirical Challenge.
Executes all 4 stress and fuzzing harnesses:
1. Vector/Matrix Math & Extreme Floating-Point Inputs (stress_math.py)
2. Euler Pitch Clamping & Gimbal Lock Fuzzing (stress_camera_gimbal.py)
3. 60Hz Accumulator State Machine & Spiral-of-Death (stress_accumulator.py)
4. Frustum Extraction & Fast AABB Culling Fuzzing (stress_frustum_culling.py)

Generates aggregated empirical telemetry for handoff.md.
"""

import sys
import time
import json
import os

# Ensure local directory is on import path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from stress_math import run_stress_tests as run_math_tests
from stress_camera_gimbal import run_camera_stress_tests
from stress_accumulator import run_accumulator_stress_tests
from stress_frustum_culling import run_frustum_stress_tests

def main():
    print("\n" + "=" * 80)
    print("      MINECRAFT DESKTOP -- EMPIRICAL CHALLENGER M1 STRESS SUITE       ")
    print("=" * 80)
    start_total = time.perf_counter()

    suites = [
        ("Task 1: Vector/Matrix Math & Extreme Floats", run_math_tests),
        ("Task 2: Camera Pitch Clamping & Gimbal Lock", run_camera_stress_tests),
        ("Task 3: 60Hz Accumulator & Spiral-of-Death", run_accumulator_stress_tests),
        ("Task 4: Frustum Extraction & AABB Culling", run_frustum_stress_tests),
    ]

    all_results = {}
    total_passed = 0
    total_failed = 0
    total_groups = 0

    for name, runner in suites:
        t0 = time.perf_counter()
        res = runner()
        dt = time.perf_counter() - t0
        res["duration_seconds"] = round(dt, 4)
        all_results[name] = res
        total_passed += res["passed"]
        total_failed += res["failed"]
        total_groups += res["tests_run"]

    elapsed_total = time.perf_counter() - start_total

    print("\n" + "=" * 80)
    print("                        OVERALL EMPIRICAL SUMMARY                     ")
    print("=" * 80)
    for name, r in all_results.items():
        status = "PASS" if r["failed"] == 0 else "FAIL"
        print(f"{name:<50} | {r['passed']}/{r['tests_run']} Passed | {r['duration_seconds']:>6.3f}s | {status}")

    print("-" * 80)
    verdict = "APPROVE" if total_failed == 0 else "REQUEST_CHANGES"
    print(f"TOTAL TEST GROUPS: {total_groups} | PASSED: {total_passed} | FAILED: {total_failed}")
    print(f"EXECUTION TIME:    {elapsed_total:.3f} seconds")
    print(f"VERDICT:           {verdict}")
    print("=" * 80 + "\n")

    report_path = os.path.join(CURRENT_DIR, "empirical_results.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump({
            "verdict": verdict,
            "total_groups": total_groups,
            "total_passed": total_passed,
            "total_failed": total_failed,
            "total_duration_s": round(elapsed_total, 4),
            "suites": all_results
        }, f, indent=2)
    print(f"Aggregated results saved to {report_path}")

    return 0 if total_failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
