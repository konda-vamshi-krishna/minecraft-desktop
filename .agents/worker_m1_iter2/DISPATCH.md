# Dispatch for worker_m1_iter2

You are worker_m1_iter2.
Working Directory: g:/minecraft_desktop/.agents/worker_m1_iter2/
Project Root: g:/minecraft_desktop

Context & Mandatory References:
- Read g:/minecraft_desktop/ORIGINAL_REQUEST.md
- Read g:/minecraft_desktop/.agents/orchestrator/PROJECT.md
- Read g:/minecraft_desktop/.agents/explorer_m1_iter2_platform/handoff.md
- Read g:/minecraft_desktop/.agents/explorer_m1_iter2_cli/handoff.md
- Read g:/minecraft_desktop/.agents/explorer_m1_iter2_math/handoff.md

Write Ownership:
You have exclusive write ownership over:
- `src/platform/platform_desktop.c`
- `src/main.c`
- `src/core/math_utils.h`

Tasks to Implement:
1. `src/platform/platform_desktop.c`:
   - Implement iterative/recursive directory creation in `Platform_CreateDir` (`mkdir -p` semantics) so nested directories such as `%TEMP%\minecraft_desktop\saves` are created reliably.
   - Fix `Platform_TestDirWritable` on Windows: Convert UTF-8 canary path to UTF-16 wchar_t via `MultiByteToWideChar(CP_UTF8, ...)` and use `_wfopen(wideCanary, L"wb")` and `_wremove(wideCanary)`.
   - Fix root path truncation logic in `Platform_ResolveBasePath` to preserve root `/` on POSIX (`if (lastSlash == procPath) *(lastSlash + 1) = '\0'`) and root `\` on Windows (`if (lastSlash == widePath + 2 && widePath[1] == L':') *(lastSlash + 1) = L'\0'`), plus trailing slash check for `candidateSaveDir`.
   - Guard `Platform_GetWindowWidth` and `Platform_GetWindowHeight` to clamp returned dimensions to `>= 1` to prevent `Inf`/`NaN` in projection matrix when window is minimized.
2. `src/main.c`:
   - Refactor CLI argument parsing to prevent argument hijacking (e.g. `--frames --headless` swallowing `--headless`).
   - Implement `ParseInt64(const char* str, long long* outVal)` using `strtoll` and `errno`.
   - Validate numerical arguments for `--seed` (signed 32-bit int: `INT_MIN` to `INT_MAX`), `--frames` (positive integer > 0), and `--ticks` (positive integer > 0).
   - Add error handling for missing required flag arguments and unrecognized CLI flags via terminating `else` branch (print error to stderr, call `PrintHelp(argv[0])`, exit with code 1).
3. `src/core/math_utils.h`:
   - In `WrapAngle360`, add post-addition precision guard `if (angle >= 360.0f) angle = 0.0f;` to prevent IEEE 754 float32 round-to-nearest rounding to 360.0f for small negative angles in `[-2^-16, 0.0)`.
   - In `Camera_UpdateFov`, invert priority order so `if (isSneaking)` precedes `if (isSprinting)`, matching canonical Minecraft kinematics where sneaking takes strict precedence over sprinting.
   - In `Mat4_Perspective`, add defensive guard `if (aspect <= 0.0001f) aspect = 1.0f;`.
   - In `Ray_Create`, preserve ray directional sign for near-zero axis-parallel directions (`r.dir.x < 0.0f ? -1e8f : 1e8f`).

Verification:
- Run `python -m unittest tests/test_m1_c_invariants.py` (all 9 must pass).
- Run `python tests/test_runner.py --tier all` (all 105 must pass).
- Run challenger stress tests in `.agents/challenger_m1_2/` and `.agents/explorer_m1_iter2_platform/verify_platform_fixes.py` if present.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

When finished, produce `handoff.md` and send a message to parent with your results.

## 2026-09-03T08:16:59Z
You are worker_m1_iter2.
Working Directory: g:/minecraft_desktop/.agents/worker_m1_iter2/
Project Root: g:/minecraft_desktop

Read your DISPATCH.md at g:/minecraft_desktop/.agents/worker_m1_iter2/DISPATCH.md.
MANDATORY: Read g:/minecraft_desktop/ORIGINAL_REQUEST.md, g:/minecraft_desktop/.agents/orchestrator/PROJECT.md, and the three explorer handoffs:
- g:/minecraft_desktop/.agents/explorer_m1_iter2_platform/handoff.md
- g:/minecraft_desktop/.agents/explorer_m1_iter2_cli/handoff.md
- g:/minecraft_desktop/.agents/explorer_m1_iter2_math/handoff.md

Write Ownership:
You have exclusive write ownership over:
- src/platform/platform_desktop.c
- src/main.c
- src/core/math_utils.h

Implement the remediations across all three files as specified in DISPATCH.md.
Ensure all Ponytail comments are preserved or added.
Run verification tests (python -m unittest tests/test_m1_c_invariants.py and python tests/test_runner.py --tier all).

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Produce handoff.md in your working directory and notify parent via send_message when complete.
