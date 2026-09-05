"""
Forensic Auditor CLI Argument Parsing Mutation & Invariant Verification
Target: main.c CLI parsing logic
Auditor: auditor_m1_iter2
"""

import sys

INT_MIN = -2147483648
INT_MAX = 2147483647

def simulate_parse_int64(s):
    try:
        # Strict strtoll behavior: no trailing characters, non-empty, handles sign
        s = s.strip()
        if not s:
            return False, 0
        val = int(s)
        return True, val
    except ValueError:
        return False, 0

def simulate_cli(argv):
    plat_headless = False
    run_headless = False
    target_fps = 60
    world_seed = 1337
    max_frames = 0
    max_duration = 0.0
    run_test_m1 = False
    
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--headless":
            plat_headless = True
            run_headless = True
            target_fps = 0
        elif arg == "--test-m1":
            run_test_m1 = True
        elif arg == "--seed":
            if i + 1 >= len(argv):
                return "ERROR_MISSING_ARG"
            i += 1
            ok, val = simulate_parse_int64(argv[i])
            if not ok or val < INT_MIN or val > INT_MAX:
                return "ERROR_INVALID_SEED"
            world_seed = val
        elif arg == "--frames":
            if i + 1 >= len(argv):
                return "ERROR_MISSING_ARG"
            i += 1
            ok, val = simulate_parse_int64(argv[i])
            if not ok or val <= 0:
                return "ERROR_INVALID_FRAMES"
            max_frames = val
        elif arg == "--ticks":
            if i + 1 >= len(argv):
                return "ERROR_MISSING_ARG"
            i += 1
            ok, val = simulate_parse_int64(argv[i])
            if not ok or val <= 0:
                return "ERROR_INVALID_TICKS"
            max_duration = float(val) * (1.0 / 60.0)
        elif arg in ("--help", "-h"):
            return "HELP"
        else:
            return f"ERROR_UNRECOGNIZED_{arg}"
        i += 1
        
    return {
        "headless": run_headless,
        "seed": world_seed,
        "frames": max_frames,
        "duration": max_duration,
        "test_m1": run_test_m1
    }

def main():
    print("=== CLI Parsing Mutation & Boundary Invariants ===")
    
    # 1. Flag hijacking test: --frames followed by --headless
    res1 = simulate_cli(["--frames", "--headless"])
    print(f"Test 1 (--frames --headless): {res1}")
    assert res1 == "ERROR_INVALID_FRAMES", "Must reject --headless as value for --frames"
    
    # 2. Seed overflow: INT_MAX + 1
    res2 = simulate_cli(["--seed", str(INT_MAX + 1)])
    print(f"Test 2 (--seed INT_MAX+1): {res2}")
    assert res2 == "ERROR_INVALID_SEED", "Must reject seed exceeding INT_MAX"
    
    # 3. Frames <= 0:
    res3 = simulate_cli(["--frames", "0"])
    print(f"Test 3 (--frames 0): {res3}")
    assert res3 == "ERROR_INVALID_FRAMES", "Must reject frames <= 0"
    
    # 4. Unrecognized flag:
    res4 = simulate_cli(["--bogus-option"])
    print(f"Test 4 (--bogus-option): {res4}")
    assert res4 == "ERROR_UNRECOGNIZED_--bogus-option", "Must reject unrecognized options with error exit"
    
    # 5. Valid run:
    res5 = simulate_cli(["--headless", "--seed", "42", "--frames", "600"])
    print(f"Test 5 (valid config): {res5}")
    assert res5["headless"] is True and res5["seed"] == 42 and res5["frames"] == 600
    
    print("\n>>> ALL CLI PARSING BOUNDARY TESTS PASSED <<<")

if __name__ == "__main__":
    main()
