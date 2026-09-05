# Dispatch for explorer_m1_iter2_cli

You are explorer_m1_iter2_cli.
Working Directory: g:/minecraft_desktop/.agents/explorer_m1_iter2_cli/
Project Root: g:/minecraft_desktop

Context & Mandatory References:
- Read g:/minecraft_desktop/ORIGINAL_REQUEST.md
- Read g:/minecraft_desktop/.agents/orchestrator/PROJECT.md
- Read g:/minecraft_desktop/.agents/challenger_m1_2/handoff.md
- Read g:/minecraft_desktop/.agents/reviewer_m1_2/handoff.md

Task:
Analyze CLI argument handling defects in `src/main.c`:
1. Argument Hijacking / Flag Collision: In `src/main.c:304-309`, running `minecraft --frames --headless` causes `--frames` to consume `--headless` as its numerical value (`strtoull` returns 0). The `--headless` flag is swallowed, headless mode is never activated, and the engine attempts to open a desktop window. The same issue exists for `--seed --headless` and `--ticks --headless`.
2. Missing Trailing Arguments: If a flag that expects a value is passed as the last argument (e.g. `minecraft --seed`), `i + 1 < argc` is false, and it is silently ignored.
3. Unrecognized Flags: If a user passes an unknown flag (e.g. `--invalid-flag`), it hits no `else` and is silently ignored. Should print usage/error and exit with non-zero code or handle properly.
4. Negative Numbers: Passing negative values like `--frames -1` causes wrap to 18 quintillion.

Rules & Constraints:
- Read-only exploration! Do NOT edit source files.
- Produce `analysis.md` and `handoff.md` in your working directory.
- Provide concrete, concise C99 code diffs and recommendations adhering to Ponytail minimal complexity.
- When finished, send a message to parent with your handoff summary.
