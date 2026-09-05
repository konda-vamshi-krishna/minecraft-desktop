#!/usr/bin/env python3
"""
Master E2E Test Runner for Minecraft Desktop — Universal 1-Click Native Edition.
Executes 4-Tier test suite:
  Tier 1: Functional Feature Verification (tests/tier1_features)
  Tier 2: Boundary Value Analysis & Corner Cases (tests/tier2_boundaries)
  Tier 3: Pairwise Cross-Feature Interactions (tests/tier3_interactions)
  Tier 4: Real-World Workload Scenarios (tests/tier4_workloads)

CLI Usage:
  python tests/test_runner.py [--tier 1,2,3,4] [--verbose] [--headless] [--json-report [PATH]]
"""

import argparse
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
            "name": test._testMethodName,
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
            "name": test._testMethodName,
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
            "name": test._testMethodName,
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


def print_banner(tiers: List[int], headless: bool):
    print(f"\n{BOLD}{CYAN}================================================================================{RESET}")
    print(f"{BOLD}{CYAN}      MINECRAFT DESKTOP -- OPAQUE-BOX REQUIREMENT-DRIVEN E2E TEST RUNNER         {RESET}")
    print(f"{BOLD}{CYAN}================================================================================{RESET}")
    print(f"{DIM}Timestamp: {datetime.now(timezone.utc).isoformat()}{RESET}")
    print(f"{DIM}Headless Mode: {GREEN}ENABLED{RESET}{DIM} | Active Tiers: {YELLOW}{tiers}{RESET}")
    print(f"{DIM}Zero Third-Party Dependencies: Pure Python 3 Standard Library{RESET}\n")


def print_summary_table(tier_results: Dict[int, tuple[CustomTestResult, float]]):
    print(f"\n{BOLD}--------------------------------------------------------------------------------{RESET}")
    print(f"{BOLD}{'Tier':<8} {'Scope / Feature Track':<32} {'Tests':<8} {'Pass':<8} {'Fail':<8} {'Duration':<10} {'Status':<10}{RESET}")
    print(f"--------------------------------------------------------------------------------")

    grand_total = 0
    grand_passed = 0
    grand_failed = 0
    grand_duration = 0.0

    for tier_num, (res, duration) in tier_results.items():
        total = res.testsRun
        passed = len(res.successes)
        failed = len(res.failures) + len(res.errors)
        status_color = GREEN if failed == 0 and total > 0 else RED
        status_text = "PASS" if failed == 0 and total > 0 else "FAIL"

        grand_total += total
        grand_passed += passed
        grand_failed += failed
        grand_duration += duration

        tier_title = f"Tier {tier_num}"
        scope = TIER_CONFIG[tier_num]["name"].split(":")[1].strip()

        print(f"{BOLD}{tier_title:<8}{RESET} {scope:<32} {total:<8} {passed:<8} {failed:<8} {duration*1000:>6.1f}ms   {status_color}{BOLD}{status_text:<10}{RESET}")

    print(f"--------------------------------------------------------------------------------")
    pass_pct = (grand_passed / grand_total * 100.0) if grand_total > 0 else 0.0
    overall_color = GREEN if grand_failed == 0 and grand_total > 0 else RED
    overall_status = "ALL TESTS PASSED (100%)" if grand_failed == 0 and grand_total > 0 else "FAILURES DETECTED"

    print(f"{BOLD}{'TOTAL':<41} {grand_total:<8} {grand_passed:<8} {grand_failed:<8} {grand_duration*1000:>6.1f}ms   {overall_color}{BOLD}{overall_status}{RESET}")
    print(f"{BOLD}Pass Rate: {overall_color}{pass_pct:.1f}%{RESET} | Total Execution Time: {grand_duration:.3f}s\n")


def generate_json_report(filepath: str, tier_results: Dict[int, tuple[CustomTestResult, float]]):
    grand_total = 0
    grand_passed = 0
    grand_failed = 0
    grand_duration = 0.0
    tiers_data = {}

    for tier_num, (res, duration) in tier_results.items():
        total = res.testsRun
        passed = len(res.successes)
        failed = len(res.failures) + len(res.errors)
        grand_total += total
        grand_passed += passed
        grand_failed += failed
        grand_duration += duration

        tiers_data[f"tier{tier_num}"] = {
            "name": TIER_CONFIG[tier_num]["name"],
            "description": TIER_CONFIG[tier_num]["description"],
            "total_tests": total,
            "passed": passed,
            "failed": failed,
            "duration_seconds": round(duration, 4),
            "status": "PASS" if failed == 0 and total > 0 else "FAIL",
            "tests": res.test_records
        }

    report = {
        "report_type": "Minecraft Desktop E2E Test Suite Execution Report",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total_tests": grand_total,
            "passed": grand_passed,
            "failed": grand_failed,
            "pass_rate_percent": round((grand_passed / grand_total * 100.0) if grand_total > 0 else 0.0, 2),
            "duration_seconds": round(grand_duration, 4),
            "status": "PASS" if grand_failed == 0 and grand_total > 0 else "FAIL"
        },
        "tiers": tiers_data
    }

    report_dir = os.path.dirname(os.path.abspath(filepath))
    if report_dir and not os.path.exists(report_dir):
        os.makedirs(report_dir, exist_ok=True)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"{CYAN}[REPORT]{RESET} Machine-readable JSON test report saved to: {BOLD}{filepath}{RESET}")


def main():
    parser = argparse.ArgumentParser(
        description="Minecraft Desktop Opaque-Box E2E Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--tier",
        type=parse_tier_arg,
        default=[1, 2, 3, 4],
        help="Specific tier(s) to execute, e.g. --tier 1,2 or --tier 4. Default: all (1,2,3,4)."
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

    print_banner(args.tier, args.headless)

    tier_results = {}
    any_failures = False

    for t in args.tier:
        print(f"{BOLD}>>> Running {TIER_CONFIG[t]['name']}...{RESET}")
        res, duration = run_tier(t, verbose=args.verbose)
        tier_results[t] = (res, duration)
        if len(res.failures) > 0 or len(res.errors) > 0:
            any_failures = True
            for test, err in res.failures + res.errors:
                print(f"{RED}[FAIL]{RESET} {test.id()}:\n{err}")

    print_summary_table(tier_results)

    if args.json_report:
        generate_json_report(args.json_report, tier_results)

    if any_failures:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
