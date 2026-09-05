# Dispatch for explorer_m1_iter2_platform

You are explorer_m1_iter2_platform.
Working Directory: g:/minecraft_desktop/.agents/explorer_m1_iter2_platform/
Project Root: g:/minecraft_desktop

Context & Mandatory References:
- Read g:/minecraft_desktop/ORIGINAL_REQUEST.md
- Read g:/minecraft_desktop/.agents/orchestrator/PROJECT.md
- Read g:/minecraft_desktop/.agents/challenger_m1_2/handoff.md
- Read g:/minecraft_desktop/.agents/reviewer_m1_2/handoff.md

Task:
Analyze platform & storage defects identified in M1:
1. Fallback Directory Creation: In `src/platform/platform_desktop.c`, `Platform_CreateDir` is non-recursive. When falling back to `%TEMP%\minecraft_desktop\saves`, `CreateDirectoryW` / `mkdir` fails with error code 3 (`ERROR_PATH_NOT_FOUND`) because intermediate directory `minecraft_desktop` is not created.
2. Unicode Directory Probe: In `src/platform/platform_desktop.c:93-103`, `Platform_TestDirWritable` calls ANSI standard `fopen` with a UTF-8 path string on Windows. On non-ANSI directories (Chinese, Japanese, Cyrillic, accented chars), `fopen` returns NULL, causing writable directories to be falsely diagnosed as read-only. Need `MultiByteToWideChar` + `_wfopen(wideCanary, L"wb")` on Windows.
3. POSIX root path truncation: If executable is in root `/minecraft`, `strrchr(procPath, '/')` truncates to empty string `""`. Ensure root `/` is preserved.
4. Window minimized height: Guard against window height == 0 resulting in Inf/NaN in aspect ratio division.

Rules & Constraints:
- Read-only exploration! Do NOT edit source files.
- Produce `analysis.md` and `handoff.md` in your working directory.
- Provide concrete, concise C99 code diffs and recommendations adhering to Ponytail minimal complexity.
- When finished, send a message to parent with your handoff summary.

## 2026-09-03T08:09:43Z
You are explorer_m1_iter2_platform.
Working Directory: g:/minecraft_desktop/.agents/explorer_m1_iter2_platform/
Project Root: g:/minecraft_desktop

Read your DISPATCH.md at g:/minecraft_desktop/.agents/explorer_m1_iter2_platform/DISPATCH.md.
MANDATORY: Read g:/minecraft_desktop/ORIGINAL_REQUEST.md, g:/minecraft_desktop/.agents/orchestrator/PROJECT.md, g:/minecraft_desktop/.agents/challenger_m1_2/handoff.md, and g:/minecraft_desktop/.agents/reviewer_m1_2/handoff.md.

Analyze platform & storage defects in src/platform/platform_desktop.c:
1. Fallback Directory Creation (nested intermediate directory creation for %TEMP%\minecraft_desktop\saves).
2. Windows Unicode canary probe (using _wfopen on Windows instead of ANSI fopen for UTF-8 paths).
3. POSIX root path truncation guard.
4. Window minimized height guard.

Produce analysis.md and handoff.md in your working directory. Send a message to parent when complete with your findings and recommended code diff.
