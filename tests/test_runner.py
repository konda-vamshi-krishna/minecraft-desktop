#!/usr/bin/env python3
"""
Master E2E & Invariant Test Runner for Minecraft Desktop — Universal 1-Click Native Edition.
Executes test suites across all architectural milestones and verification tiers:
  Tier 1: Functional Feature Verification (tests/tier1_features)
  Tier 2: Boundary Value Analysis & Corner Cases (tests/tier2_boundaries)
  Tier 3: Pairwise Cross-Feature Interactions (tests/tier3_interactions)
  Tier 4: Real-World Workload Scenarios (tests/tier4_workloads)
  Milestones & Challengers: M1-M5 Invariants, Adversarial & Empirical Stress Suites

CLI Usage:
  python tests/test_runner.py [--tier 1,2,3,4] [--all] [--milestones] [--verbose] [--headless] [--json-report [PATH]]
"""

import argparse
import glob
import json
import os
import sys
import time
import unittest
from datetime import datetime, timezone
from typing import Dict, List, Any


# ANSI Color Codes
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

# Windows color support check
if sys.platform == "win32":
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        # Enable ENABLE_VIRTUAL_TERMINAL_PROCESSING
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except Exception:
        pass


TIER_CONFIG = {
    1: {
        "name": "Tier 1: Functional Features",
        "dir": "tests/tier1_features",
        "description": "Core physics kinematics, DDA raycast, 41-slot inventory, crafting, audio formulas, base-path resolver"
    },
    2: {
        "name": "Tier 2: Boundary & Corner Cases",
        "dir": "tests/tier2_boundaries",
        "description": "Negative coordinates, terminal velocity anti-tunneling, auto-step ceiling abort, sneak ledge-clamp, bedrock"
    },
    3: {
        "name": "Tier 3: Pairwise Interactions",
        "dir": "tests/tier3_interactions",
        "description": "Sprint-jumping + exhaustion, DDA mining + drops, crafting table lifecycle, auto-step + sneak cornering"
    },
    4: {
        "name": "Tier 4: Real-World Workloads",
        "dir": "tests/tier4_workloads",
        "description": "First Day Survival 14-step progression, fatal fall death/respawn, 1200s celestial diurnal cycle"
    }
}

MILESTONE_MODULES = [
    ("Milestone 1 Invariants", "tests/test_m1_c_invariants.py"),
    ("Milestone 2 Invariants", "tests/test_m2_c_invariants.py"),
    ("Milestone 2 Chunk Invariants", "tests/test_m2_chunk_invariants.py"),
    ("Milestone 2 Mesher Canonical", "tests/test_mesher_canonical.py"),
    ("Milestone 3 Gameplay Suite", "tests/test_m3_gameplay.py"),
    ("Milestone 3 Invariants", "tests/test_m3_gameplay_invariants.py"),
    ("Milestone 4 Assets & Audio", "tests/test_m4_assets_audio.py"),
    ("Milestone 4 Adversarial", "tests/test_adversarial_m4.py"),
    ("Milestone 5 Packaging", "tests/test_m5_packaging_invariants.py"),
    ("Milestone 5 Adversarial", "tests/test_m5_adversarial_challenge.py"),
    ("CLI Parsing Empirical Stress", "tests/test_cli_empirical_stress.py"),
    ("Platform Challenger Suite", "tests/test_challenger_platform.py"),
    ("Gameplay Challenger Suite", "tests/test_challenger_gameplay_adversarial.py"),
    ("Remedy 2 Adversarial Suite", "tests/test_challenger_adversarial_remedy_2.py"),
]


class CustomTestResult(unittest.TestResult):
    def __init__(self, verbose: bool = False):
        super().__init__()
        self.verbose = verbose
        self.successes: List[Any] = []
        self.test_records: List[Dict[str, Any]] = []
        self._current_start_time = 0.0

    def startTest(self, test):
        super().startTest(test)
        self._current_start_time = time.perf_counter()
        if self.verbose:
            doc = (test.shortDescription() or "").strip()
            print(f"  {CYAN}[RUN]{RESET} {test.id()} {DIM}- {doc}{RESET}")

    def addSuccess(self, test):
        super().addSuccess(test)
        duration = time.perf_counter() - self._current_start_time
        self.successes.append(test)
        self.test_records.append({
            "id": test.id(),
            "name": getattr(test, "_testMethodName", str(test)),
            "status": "PASS",
            "duration": duration,
            "description": test.shortDescription() or ""
        })
        if self.verbose:
            print(f"  {GREEN}[PASS]{RESET} {test.id()} ({duration*1000:.1f}ms)")

    def addFailure(self, test, err):
        super().addFailure(test, err)
        duration = time.perf_counter() - self._current_start_time
        self.test_records.append({
            "id": test.id(),
            "name": getattr(test, "_testMethodName", str(test)),
            "status": "FAIL",
            "duration": duration,
            "error": self._exc_info_to_string(err, test),
            "description": test.shortDescription() or ""
        })
        if self.verbose:
            print(f"  {RED}[FAIL]{RESET} {test.id()}")

    def addError(self, test, err):
        super().addError(test, err)
        duration = time.perf_counter() - self._current_start_time
        self.test_records.append({
            "id": test.id(),
            "name": getattr(test, "_testMethodName", str(test)),
            "status": "ERROR",
            "duration": duration,
            "error": self._exc_info_to_string(err, test),
            "description": test.shortDescription() or ""
        })
        if self.verbose:
            print(f"  {RED}[ERROR]{RESET} {test.id()}")


def parse_tier_arg(val: str) -> List[int]:
    """Parses '1,2,3' or '1' or 'all' into list of tier integers."""
    if not val or val.lower() == 'all':
        return [1, 2, 3, 4]
    tiers = []
    for part in val.replace(',', ' ').split():
        try:
            t = int(part)
            if t in TIER_CONFIG:
                tiers.append(t)
            else:
                raise argparse.ArgumentTypeError(f"Invalid tier: {t}. Must be 1, 2, 3, or 4.")
        except ValueError:
            raise argparse.ArgumentTypeError(f"Invalid tier argument: '{part}'.")
    return sorted(list(set(tiers)))


def run_tier(tier_num: int, verbose: bool = False) -> tuple[CustomTestResult, float]:
    cfg = TIER_CONFIG[tier_num]
    suite_dir = os.path.join(os.path.dirname(__file__), f"tier{tier_num}_" + cfg["dir"].split("_")[1])
    
    # Ensure package import path
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    loader = unittest.TestLoader()
    suite = loader.discover(suite_dir, pattern="test_*.py")

    result = CustomTestResult(verbose=verbose)
    start_time = time.perf_counter()
    suite.run(result)
    total_time = time.perf_counter() - start_time

    return result, total_time


def run_single_file(filepath: str, verbose: bool = False) -> tuple[CustomTestResult, float]:
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    rel_path = os.path.relpath(filepath, project_root).replace('\\', '/')
    mod_name = rel_path[:-3].replace('/', '.')

    loader = unittest.TestLoader()
    try:
        suite = loader.loadTestsFromName(mod_name)
    except Exception as e:
        # Fallback to direct load
        suite = loader.discover(os.path.dirname(filepath), pattern=os.path.basename(filepath))

    result = CustomTestResult(verbose=verbose)
    start_time = time.perf_counter()
    suite.run(result)
    total_time = time.perf_counter() - start_time

    return result, total_time


def print_banner(mode_str: str, headless: bool):
    print(f"\n{BOLD}{CYAN}================================================================================{RESET}")
    print(f"{BOLD}{CYAN}      MINECRAFT DESKTOP -- OPAQUE-BOX REQUIREMENT-DRIVEN E2E TEST RUNNER         {RESET}")
    print(f"{BOLD}{CYAN}================================================================================{RESET}")
    print(f"{DIM}Timestamp: {datetime.now(timezone.utc).isoformat()}{RESET}")
    print(f"{DIM}Headless Mode: {GREEN}ENABLED{RESET}{DIM} | Scope: {YELLOW}{mode_str}{RESET}")
    print(f"{DIM}Zero Third-Party Dependencies: Pure Python 3 Standard Library{RESET}\n")


def print_summary_table(track_results: Dict[str, tuple[CustomTestResult, float]]):
    print(f"\n{BOLD}--------------------------------------------------------------------------------{RESET}")
    print(f"{BOLD}{'Track':<10} {'Scope / Feature Track':<36} {'Tests':<8} {'Pass':<8} {'Fail':<8} {'Duration':<10} {'Status':<10}{RESET}")
    print(f"--------------------------------------------------------------------------------")

    grand_total = 0
    grand_passed = 0
    grand_failed = 0
    grand_duration = 0.0

    for track_key, (res, duration) in track_results.items():
        total = res.testsRun
        passed = len(res.successes)
        failed = len(res.failures) + len(res.errors)
        status_color = GREEN if failed == 0 and total > 0 else RED
        status_text = "PASS" if failed == 0 and total > 0 else "FAIL"

        grand_total += total
        grand_passed += passed
        grand_failed += failed
        grand_duration += duration

        track_label = track_key.split(":")[0].strip() if ":" in track_key else track_key
        scope = track_key.split(":")[1].strip() if ":" in track_key else track_key

        print(f"{BOLD}{track_label:<10}{RESET} {scope:<36} {total:<8} {passed:<8} {failed:<8} {duration*1000:>6.1f}ms   {status_color}{BOLD}{status_text:<10}{RESET}")

    print(f"--------------------------------------------------------------------------------")
    pass_pct = (grand_passed / grand_total * 100.0) if grand_total > 0 else 0.0
    overall_color = GREEN if grand_failed == 0 and grand_total > 0 else RED
    overall_status = "ALL TESTS PASSED (100%)" if grand_failed == 0 and grand_total > 0 else "FAILURES DETECTED"

    print(f"{BOLD}{'TOTAL':<47} {grand_total:<8} {grand_passed:<8} {grand_failed:<8} {grand_duration*1000:>6.1f}ms   {overall_color}{BOLD}{overall_status}{RESET}")
    print(f"{BOLD}Pass Rate: {overall_color}{pass_pct:.1f}%{RESET} | Total Execution Time: {grand_duration:.3f}s\n")


def generate_json_report(filepath: str, track_results: Dict[str, tuple[CustomTestResult, float]]):
    grand_total = 0
    grand_passed = 0
    grand_failed = 0
    grand_duration = 0.0
    tracks_data = {}

    for track_key, (res, duration) in track_results.items():
        total = res.testsRun
        passed = len(res.successes)
        failed = len(res.failures) + len(res.errors)
        grand_total += total
        grand_passed += passed
        grand_failed += failed
        grand_duration += duration

        tracks_data[track_key] = {
            "name": track_key,
            "total_tests": total,
            "passed": passed,
            "failed": failed,
            "duration_seconds": round(duration, 4),
            "status": "PASS" if failed == 0 and total > 0 else "FAIL",
            "tests": res.test_records
        }

    report = {
        "report_type": "Minecraft Desktop E2E & Invariant Test Suite Execution Report",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total_tests": grand_total,
            "passed": grand_passed,
            "failed": grand_failed,
            "pass_rate_percent": round((grand_passed / grand_total * 100.0) if grand_total > 0 else 0.0, 2),
            "duration_seconds": round(grand_duration, 4),
            "status": "PASS" if grand_failed == 0 and grand_total > 0 else "FAIL"
        },
        "tracks": tracks_data
    }

    report_dir = os.path.dirname(os.path.abspath(filepath))
    if report_dir and not os.path.exists(report_dir):
        os.makedirs(report_dir, exist_ok=True)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"{CYAN}[REPORT]{RESET} Machine-readable JSON test report saved to: {BOLD}{filepath}{RESET}")


def main():
    parser = argparse.ArgumentParser(
        description="Minecraft Desktop Opaque-Box E2E & Invariant Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--tier",
        type=parse_tier_arg,
        default=None,
        help="Specific tier(s) to execute, e.g. --tier 1,2 or --tier 4."
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all test suites across all tiers, milestones, and challenger stress tests."
    )
    parser.add_argument(
        "--milestones",
        action="store_true",
        help="Run milestone invariants and challenger adversarial stress test suites."
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show detailed per-test execution logging."
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=True,
        help="Run in headless execution mode (default: True)."
    )
    parser.add_argument(
        "--json-report",
        nargs="?",
        const="test_report.json",
        default=None,
        help="Export machine-readable JSON report to specified path (default: test_report.json)."
    )

    args = parser.parse_args()

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    run_all = args.all
    run_milestones = args.milestones
    active_tiers = args.tier if args.tier is not None else ([1, 2, 3, 4] if not run_milestones else [])

    mode_description = []
    if run_all:
        mode_description.append("All Tiers + Milestones + Challengers (Comprehensive)")
    else:
        if active_tiers:
            mode_description.append(f"Tiers {active_tiers}")
        if run_milestones:
            mode_description.append("Milestone Invariants & Challengers")

    print_banner(", ".join(mode_description) if mode_description else "Default Tiers [1, 2, 3, 4]", args.headless)

    track_results = {}
    any_failures = False

    # Execute Tiers
    if run_all or active_tiers:
        tiers_to_run = [1, 2, 3, 4] if run_all else active_tiers
        for t in tiers_to_run:
            cfg = TIER_CONFIG[t]
            print(f"{BOLD}>>> Running {cfg['name']}...{RESET}")
            res, duration = run_tier(t, verbose=args.verbose)
            track_key = f"Tier {t}: {cfg['name'].split(':')[1].strip()}"
            track_results[track_key] = (res, duration)
            if len(res.failures) > 0 or len(res.errors) > 0:
                any_failures = True
                for test, err in res.failures + res.errors:
                    print(f"{RED}[FAIL]{RESET} {test.id()}:\n{err}")

    # Execute Milestones & Challengers
    if run_all or run_milestones:
        for title, rel_path in MILESTONE_MODULES:
            abs_path = os.path.join(project_root, rel_path)
            if not os.path.isfile(abs_path):
                continue
            print(f"{BOLD}>>> Running {title} ({rel_path})...{RESET}")
            res, duration = run_single_file(abs_path, verbose=args.verbose)
            track_key = f"M-Suite: {title}"
            track_results[track_key] = (res, duration)
            if len(res.failures) > 0 or len(res.errors) > 0:
                any_failures = True
                for test, err in res.failures + res.errors:
                    print(f"{RED}[FAIL]{RESET} {test.id()}:\n{err}")

    print_summary_table(track_results)

    if args.json_report:
        generate_json_report(args.json_report, track_results)

    if any_failures:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
