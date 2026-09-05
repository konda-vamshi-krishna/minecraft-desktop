# Milestone 1 (M1) CLI Parsing Exploration Handoff Report

**Agent:** explorer_m1_iter2_cli  
**Target:** `src/main.c:294-314` (CLI Argument Parsing Subsystem)  
**Parent Conversation ID:** `fd432488-815b-45be-9bfc-410c7c8c8f4c`  
**Working Directory:** `g:/minecraft_desktop/.agents/explorer_m1_iter2_cli/`  
**Handoff Type:** Hard (Task Complete)  

---

## 1. Observation

### 1.1 Direct Source Code Observations
In `src/main.c:294-313`:
```c
294:     for (int i = 1; i < argc; i++) {
295:         if (strcmp(argv[i], "--headless") == 0) {
296:             platConfig.headless = true;
297:             runConfig.headless = true;
298:             runConfig.targetFps = 0;
299:         } else if (strcmp(argv[i], "--test-m1") == 0) {
300:             runTestM1 = true;
301:         } else if (strcmp(argv[i], "--seed") == 0 && i + 1 < argc) {
302:             worldSeed = atoi(argv[++i]);
303:             (void)worldSeed;
304:         } else if (strcmp(argv[i], "--frames") == 0 && i + 1 < argc) {
305:             runConfig.maxFrames = (uint64_t)strtoull(argv[++i], NULL, 10);
306:         } else if (strcmp(argv[i], "--ticks") == 0 && i + 1 < argc) {
307:             uint64_t ticks = (uint64_t)strtoull(argv[++i], NULL, 10);
308:             runConfig.maxDuration = (double)ticks * RUNTIME_FIXED_DT;
309:         } else if (strcmp(argv[i], "--help") == 0 || strcmp(argv[i], "-h") == 0) {
310:             PrintHelp(argv[0]);
311:             return 0;
312:         }
313:     }
```

### 1.2 Tool Execution & Empirical Results
1. **Existing Test Suite Baseline:**
   - Command: `python tests/test_runner.py --tier all`
   - Result: 105 tests run, 105 passed (100% pass rate in 34.3ms).
   - Command: `python -m unittest tests/test_m1_c_invariants.py`
   - Result: 9 tests run, 9 passed (100% pass rate in 0.004s).
2. **Empirical Defect Reproduction:**
   - Executed empirical Python harness simulating `main.c:294-313` against standard C99 CRT conversions:
     - `minecraft --frames --headless`: `--frames` consumes `argv[2]` (`"--headless"`). `strtoull("--headless", NULL, 10)` returns `0ULL`. `i` is incremented to 2, and the loop terminates without evaluating `--headless`. `platConfig.headless` remains `false`.
     - `minecraft --seed`: `i + 1 < argc` is `false`. Condition fails, falls through all branches. No `else` exists. Silent pass-through with default seed 1337.
     - `minecraft --invalid-flag`: No branch matches, no `else` exists. Silently ignored, exits 0 or launches game.
     - `minecraft --frames -1`: `strtoull("-1", NULL, 10)` wraps via two's complement to `18446744073709551615ULL` (18.4 quintillion frames), running unbounded.
     - `minecraft --seed -999`: If a naive `argv[i + 1][0] != '-'` check were used, valid negative seed `-999` would be incorrectly rejected.

---

## 2. Logic Chain

1. **Premise 1 (Flag Collision):** In `main.c:304`, the branch condition requires `strcmp(argv[i], "--frames") == 0 && i + 1 < argc`. If another flag immediately follows (e.g. `--headless`), `i + 1 < argc` is satisfied.
2. **Inference 1.1:** Line 305 executes `argv[++i]`, advancing `i` and passing `"--headless"` to `strtoull`.
3. **Inference 1.2:** In C99, `strtoull` does not recognize leading `"--"` as digits, returning 0.
4. **Inference 1.3:** The for loop increments `i` past `"--headless"`. Therefore, `--headless` is never parsed, `platConfig.headless` remains `false`, and the engine tries to open a desktop GUI window in headless environments.
5. **Premise 2 (Missing Trailing Arguments):** If `--seed`, `--frames`, or `--ticks` is passed at the end of the argument list, `i + 1 < argc` evaluates to `false`.
6. **Inference 2.1:** Because flag matching is coupled with `i + 1 < argc`, the parser fails to recognize that `--seed` was provided at all.
7. **Inference 2.2:** In the absence of an `else` block, the missing parameter is ignored silently, running the game with default parameters.
8. **Premise 3 (Unrecognized Flags):** Any flag not matching the explicit `if / else if` conditions falls off the end of the loop without notification or error exit.
9. **Premise 4 (Negative & Zero Values):**
   - For `--frames` and `--ticks`, `strtoull` accepts negative numbers and wraps them to $\sim 18.4 \times 10^{18}$ without error.
   - For `--frames 0`, `runtime.c:196` checks `if (maxFrames > 0)`, meaning 0 runs indefinitely instead of terminating.
   - For `--seed`, negative numbers are valid Minecraft seeds (signed 32-bit integer).
10. **Deduction:** All 4 defects can be resolved cleanly without external dependencies by decoupling flag matching from value presence, implementing a single 12-line helper `ParseInt64(str, &val)` using C99 `strtoll` and `errno`, validating value bounds per flag, and adding a terminating `else` branch that prints an error, displays help, and exits with code 1.

---

## 3. Caveats

1. **Host-Environment Compiler Prohibition:** In accordance with explicit safety directives (`ORIGINAL_REQUEST.md`), no binary compilers were installed or invoked on the host machine. All validation was conducted via Python harnesses verifying standard C99 runtime behavior.
2. **Seeds Range:** World seeds are clamped to standard 32-bit signed integer range `[INT_MIN, INT_MAX]` (`[-2147483648, 2147483647]`).
3. **Code Modification Scope:** Per explorer read-only constraints, no modifications have been made to `src/main.c`. The proposed changes are documented as a ready-to-apply diff for `worker_m1`.

---

## 4. Conclusion

The CLI argument parser in `src/main.c` requires refactoring to resolve 4 distinct vulnerabilities (argument hijacking, missing trailing arguments, unrecognized flags, and negative value wrapping).

### Recommended Code Diff (`src/main.c`)

```diff
--- a/src/main.c
+++ b/src/main.c
@@ -5,6 +5,8 @@
 #include <stdlib.h>
 #include <string.h>
 #include <math.h>
+#include <errno.h>
+#include <limits.h>
 
 // ponytail: [entry: CLI arg parsing with strcmp] -> [getopt_long or dedicated CLI parser if complex flags added]
 
@@ -278,6 +280,18 @@ static void App_OnRenderFrame(float alpha) {
     Platform_EndFrame();
 }
 
+static bool ParseInt64(const char* str, long long* outVal) {
+    if (!str || *str == '\0') return false;
+    char* end = NULL;
+    errno = 0;
+    long long v = strtoll(str, &end, 10);
+    if (errno != 0 || end == str || *end != '\0') {
+        return false;
+    }
+    if (outVal) *outVal = v;
+    return true;
+}
+
 int main(int argc, char* argv[]) {
     PlatformConfig platConfig = {
         .windowWidth = 1280,
@@ -298,17 +312,47 @@ int main(int argc, char* argv[]) {
             runConfig.targetFps = 0;
         } else if (strcmp(argv[i], "--test-m1") == 0) {
             runTestM1 = true;
-        } else if (strcmp(argv[i], "--seed") == 0 && i + 1 < argc) {
-            worldSeed = atoi(argv[++i]);
+        } else if (strcmp(argv[i], "--seed") == 0) {
+            if (i + 1 >= argc) {
+                fprintf(stderr, "Error: %s requires an argument.\n", argv[i]);
+                PrintHelp(argv[0]);
+                return 1;
+            }
+            long long val = 0;
+            if (!ParseInt64(argv[++i], &val) || val < INT_MIN || val > INT_MAX) {
+                fprintf(stderr, "Error: %s requires an integer argument (got '%s').\n", argv[i - 1], argv[i]);
+                PrintHelp(argv[0]);
+                return 1;
+            }
+            worldSeed = (int)val;
             (void)worldSeed;
-        } else if (strcmp(argv[i], "--frames") == 0 && i + 1 < argc) {
-            runConfig.maxFrames = (uint64_t)strtoull(argv[++i], NULL, 10);
-        } else if (strcmp(argv[i], "--ticks") == 0 && i + 1 < argc) {
-            uint64_t ticks = (uint64_t)strtoull(argv[++i], NULL, 10);
-            runConfig.maxDuration = (double)ticks * RUNTIME_FIXED_DT;
+        } else if (strcmp(argv[i], "--frames") == 0) {
+            if (i + 1 >= argc) {
+                fprintf(stderr, "Error: %s requires an argument.\n", argv[i]);
+                PrintHelp(argv[0]);
+                return 1;
+            }
+            long long val = 0;
+            if (!ParseInt64(argv[++i], &val) || val <= 0) {
+                fprintf(stderr, "Error: %s requires a positive integer argument (got '%s').\n", argv[i - 1], argv[i]);
+                PrintHelp(argv[0]);
+                return 1;
+            }
+            runConfig.maxFrames = (uint64_t)val;
+        } else if (strcmp(argv[i], "--ticks") == 0) {
+            if (i + 1 >= argc) {
+                fprintf(stderr, "Error: %s requires an argument.\n", argv[i]);
+                PrintHelp(argv[0]);
+                return 1;
+            }
+            long long val = 0;
+            if (!ParseInt64(argv[++i], &val) || val <= 0) {
+                fprintf(stderr, "Error: %s requires a positive integer argument (got '%s').\n", argv[i - 1], argv[i]);
+                PrintHelp(argv[0]);
+                return 1;
+            }
+            runConfig.maxDuration = (double)val * RUNTIME_FIXED_DT;
         } else if (strcmp(argv[i], "--help") == 0 || strcmp(argv[i], "-h") == 0) {
             PrintHelp(argv[0]);
             return 0;
+        } else {
+            fprintf(stderr, "Error: unrecognized option '%s'\n", argv[i]);
+            PrintHelp(argv[0]);
+            return 1;
         }
     }
```

---

## 5. Verification Method

To independently verify the defects and validate the proposed remediation:

1. **Verify Invariant Preservation:**
   ```powershell
   python -m unittest tests/test_m1_c_invariants.py
   ```
   *Expected:* 9/9 PASS. Required substring checks for CLI flags and test runner remain intact.

2. **Verify Full E2E Test Suite:**
   ```powershell
   python tests/test_runner.py --tier all
   ```
   *Expected:* 105/105 PASS.

3. **Verify CLI Parser Permutation Suite:**
   Run the 25-case CLI simulator harness covering all combinations of valid flags, flag collisions (`--frames --headless`), missing trailing arguments, negative numbers, zero numbers, and unrecognized options.
   ```powershell
   python .agents/challenger_m1_2/test_cli_parsing.py
   ```
   *Expected:* Confirms that the proposed patch eliminates all 4 defect classes while correctly preserving negative seed handling.
