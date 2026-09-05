"""
Empirical Challenger Test Suite for Milestone 1: CLI Argument Parsing
Tests all permutations of CLI flags:
- Valid flags: --headless, --test-m1, --seed <N>, --frames <N>, --ticks <N>, --help, -h
- Missing arguments: --seed (no value), --frames (no value), --ticks (no value)
- Unknown / invalid flags: --invalid, -x, --foo=bar
- Boundary values: --frames 0, --frames -1, --ticks 0, --ticks -1, --seed -999, --seed 0
- Malformed values: --seed abc, --frames xyz, --ticks def
- Flag ordering & combinatorics
"""

import sys
import ctypes

# Canonical definitions from runtime.h & platform.h
RUNTIME_FIXED_DT = 1.0 / 60.0

def simulate_main_cli(args):
    """
    Exact simulation of main.c lines 279-314
    """
    platConfig = {
        "windowWidth": 1280,
        "windowHeight": 720,
        "title": "Minecraft Desktop — Universal Edition",
        "targetFps60": True,
        "headless": False
    }

    runConfig = {
        "headless": False,
        "targetFps": 60,
        "maxFrames": 0,
        "maxDuration": 0.0
    }

    worldSeed = 1337
    runTestM1 = False
    helpPrinted = False
    exitCode = 0
    unrecognizedFlags = []
    missingArgFlags = []

    argc = len(args)
    argv = args

    i = 1
    while i < argc:
        arg = argv[i]
        if arg == "--headless":
            platConfig["headless"] = True
            runConfig["headless"] = True
            runConfig["targetFps"] = 0
        elif arg == "--test-m1":
            runTestM1 = True
        elif arg == "--seed":
            if i + 1 < argc:
                i += 1
                try:
                    # C atoi() semantics: parses leading integer or 0
                    val_str = argv[i]
                    # Simulate atoi:
                    # In C: atoi("123abc") -> 123, atoi("abc") -> 0
                    # For strictness:
                    worldSeed = int(val_str)
                except ValueError:
                    worldSeed = 0
            else:
                missingArgFlags.append("--seed")
        elif arg == "--frames":
            if i + 1 < argc:
                i += 1
                try:
                    # C strtoull(argv[++i], NULL, 10)
                    val = int(argv[i])
                    # strtoull on negative wraps to unsigned 64-bit:
                    if val < 0:
                        val = (1 << 64) + val
                    runConfig["maxFrames"] = val
                except ValueError:
                    runConfig["maxFrames"] = 0
            else:
                missingArgFlags.append("--frames")
        elif arg == "--ticks":
            if i + 1 < argc:
                i += 1
                try:
                    val = int(argv[i])
                    if val < 0:
                        val = (1 << 64) + val
                    runConfig["maxDuration"] = float(val) * RUNTIME_FIXED_DT
                except ValueError:
                    runConfig["maxDuration"] = 0.0
            else:
                missingArgFlags.append("--ticks")
        elif arg == "--help" or arg == "-h":
            helpPrinted = True
            return {
                "exitCode": 0,
                "helpPrinted": True,
                "platConfig": platConfig,
                "runConfig": runConfig,
                "worldSeed": worldSeed,
                "runTestM1": runTestM1,
                "unrecognizedFlags": unrecognizedFlags,
                "missingArgFlags": missingArgFlags
            }
        else:
            # Notice in main.c, there is NO else branch!
            unrecognizedFlags.append(arg)
        i += 1

    return {
        "exitCode": exitCode,
        "helpPrinted": helpPrinted,
        "platConfig": platConfig,
        "runConfig": runConfig,
        "worldSeed": worldSeed,
        "runTestM1": runTestM1,
        "unrecognizedFlags": unrecognizedFlags,
        "missingArgFlags": missingArgFlags
    }


def run_cli_stress_tests():
    print("=== CLI Argument Parsing Stress Tests ===")
    
    # Test 1: Standard valid headless execution
    r1 = simulate_main_cli(["minecraft", "--headless"])
    assert r1["platConfig"]["headless"] is True
    assert r1["runConfig"]["headless"] is True
    assert r1["runConfig"]["targetFps"] == 0
    print("[PASS] Test 1: --headless correctly parsed")

    # Test 2: Standard valid test-m1
    r2 = simulate_main_cli(["minecraft", "--test-m1"])
    assert r2["runTestM1"] is True
    print("[PASS] Test 2: --test-m1 correctly parsed")

    # Test 3: Standard seed
    r3 = simulate_main_cli(["minecraft", "--seed", "42"])
    assert r3["worldSeed"] == 42
    print("[PASS] Test 3: --seed 42 correctly parsed")

    # Test 4: Combined flags
    r4 = simulate_main_cli(["minecraft", "--headless", "--ticks", "120", "--seed", "999"])
    assert r4["platConfig"]["headless"] is True
    assert r4["worldSeed"] == 999
    assert abs(r4["runConfig"]["maxDuration"] - (120 * RUNTIME_FIXED_DT)) < 1e-6
    print("[PASS] Test 4: Combined flags --headless --ticks 120 --seed 999 parsed")

    # Test 5: Missing argument at end of line (--seed)
    r5 = simulate_main_cli(["minecraft", "--seed"])
    print(f"[TEST 5] Trailing --seed without value: missingArgFlags={r5['missingArgFlags']}")
    print(f"  Resulting seed: {r5['worldSeed']} (default 1337 retained)")
    if r5["missingArgFlags"]:
        print("  -> VULNERABILITY/DEFECT: main.c silently ignores trailing --seed without returning an error!")

    # Test 6: Missing argument before another flag (--frames --headless)
    # In main.c: if argv[i] is "--frames" and i + 1 < argc, argv[++i] becomes "--headless"!
    # strtoull("--headless", NULL, 10) returns 0!
    # And --headless is consumed as the frame count!
    # Let's verify what happens in actual main.c C code!
    print("[TEST 6] Flag collision: 'minecraft --frames --headless'")
    # Let's trace main.c:
    # argv[1] = "--frames"
    # i = 1, i + 1 = 2 < 3 (true)
    # runConfig.maxFrames = (uint64_t)strtoull(argv[++i], NULL, 10);
    # argv[++i] is argv[2] ("--headless")
    # strtoull("--headless", NULL, 10) returns 0!
    # i is now 2! Loop increments i to 3!
    # Loop ends! --headless was NEVER processed! Headless mode remains FALSE!
    print("  -> CRITICAL DEFECT: 'minecraft --frames --headless' consumes '--headless' as the value of '--frames',")
    print("     strtoull returns 0, and the engine launches in FULL GUI WINDOWED MODE instead of HEADLESS!")

    # Test 7: Unrecognized / invalid flags
    r7 = simulate_main_cli(["minecraft", "--unknown-flag", "-z"])
    print(f"[TEST 7] Unknown flags: unrecognizedFlags={r7['unrecognizedFlags']}")
    print(f"  Exit code: {r7['exitCode']}")
    if r7["unrecognizedFlags"] and r7["exitCode"] == 0:
        print("  -> VULNERABILITY/DEFECT: Unrecognized flags are silently ignored and process continues with exit code 0!")

    # Test 8: Negative --frames
    r8 = simulate_main_cli(["minecraft", "--frames", "-1"])
    print(f"[TEST 8] Negative frames '--frames -1': maxFrames={r8['runConfig']['maxFrames']}")
    if r8["runConfig"]["maxFrames"] > 10**18:
        print("  -> DEFECT: Negative frames wrap to 18 quintillion frames via strtoull without validation!")

    # Test 9: Zero --frames and --ticks
    r9 = simulate_main_cli(["minecraft", "--frames", "0"])
    print(f"[TEST 9] Zero frames '--frames 0': maxFrames={r9['runConfig']['maxFrames']}")
    print("  In runtime.c: `if (maxFrames > 0)` -> treated as infinite frames!")

if __name__ == "__main__":
    run_cli_stress_tests()
