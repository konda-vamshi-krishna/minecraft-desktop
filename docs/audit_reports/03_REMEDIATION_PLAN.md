# 03. Engineering Remediation & Implementation Plan

**Date:** 2026-09-28  
**Author:** Team 1 — System Audit & Remediation Architecture  
**Executing Team:** Team 2 — Development & Core Engine Engineering  
**Target Completion Standard:** Zero Warnings under `-Wall -Wextra -Werror -pedantic -std=c99`, 100% Test Pass Rate across all 36 test modules.

---

## 1. Remediation Work Breakdown Structure (WBS)

```
[Phase 2: Development Team]
  │
  ├── Work Package 1: Build System & Linker Decoupling
  │     ├── Decouple HEADLESS_LIBS from WIN_LIBS / GUI libs in Makefile.
  │     └── Ensure `make`, `make headless`, and `make test` execute out of the box.
  │
  ├── Work Package 2: C99 Conformance & Warning Zeroing
  │     ├── Fix unused parameter warnings in `src/platform/platform_desktop.c`.
  │     ├── Fix strncpy truncation warnings in `src/platform/platform_desktop.c`.
  │     ├── Fix unused static function `App_GetItemShortName` in `src/main.c`.
  │     └── Fix `SoundID` enum conversions in `src/main.c`.
  │
  ├── Work Package 3: C99 Crafting Engine Implementation
  │     ├── Declare `Crafting_Match` and `Crafting_Craft` in `src/gameplay/inventory.h`.
  │     ├── Implement translation-invariant shaped matching & shapeless matching in `src/gameplay/inventory.c`.
  │     └── Verify zero heap allocation and Ponytail minimalist principles.
  │
  ├── Work Package 4: Complete Platform Challenger Test Suite
  │     ├── Implement full suite in `tests/test_challenger_platform.py`.
  │     └── Verify timer monotonic bounds, headless queries, storage path fallback.
  │
  ├── Work Package 5: Enhanced Master Test Runner & Launcher Script
  │     ├── Update `tests/test_runner.py` to support `--all` and multi-suite reporting.
  │     └── Make `launch_game.bat` resilient to directory structures.
```

---

## 2. Step-by-Step Implementation Strategy

### Step 1: Makefile Decoupling
Separate headless libraries (`-lm -lpthread -ldl -lrt` on Linux, `-lwinmm` on Windows) from full GUI libraries (`-lGL -lX11` / `-lraylib`).

### Step 2: Source Code Warning Elimination
Apply `(void)param;` macros and `snprintf` buffer operations across `platform_desktop.c` and `main.c`. Use canonical `SoundID` enum constants (`SFX_CLICK`, `SFX_STEP`, `SFX_JUMP`, `SFX_BLOCK_BREAK`, `SFX_BLOCK_PLACE`) in `main.c`.

### Step 3: Implement C Crafting Engine in `inventory.h` / `inventory.c`
Define `ItemStack Crafting_Match(const ItemStack grid[3][3], int gridSize)` and `ItemStack Crafting_Craft(ItemStack grid[3][3], int gridSize)` to evaluate 2x2 and 3x3 grids against vanilla recipe definitions:
- Wood Log $\to$ 4 Wood Planks
- 2 Vertical Planks $\to$ 4 Sticks
- 4 Planks $\to$ 1 Crafting Table
- 8 Cobblestones $\to$ 1 Furnace
- 3 Planks / Cobblestone / Iron Ingot + 2 Sticks $\to$ Wooden / Stone / Iron Pickaxe

### Step 4: Complete Platform Challenger Tests
Populate `tests/test_challenger_platform.py` with 10+ comprehensive test cases covering:
1. `Platform_GetTime` monotonic progression and non-negativity.
2. `Platform_Sleep` timing calibration and drift limits.
3. `Platform_ResolveBasePath` executable path discovery.
4. `Platform_ResolveTempSaveDir` fallback path generation.
5. Headless mode input queries return false/zero without crash.
6. Cursor capture toggle and query invariance.
7. Window dimension queries return positive defaults in headless mode.
8. Storage paths struct population and canary write probe.

### Step 5: Master Test Runner Upgrades
Extend `tests/test_runner.py` so that users and CI can run:
- `python tests/test_runner.py` (Default: Tier 1–4 E2E suites)
- `python tests/test_runner.py --all` (Runs all 36 test files, reporting 280+ tests)
- `python tests/test_runner.py --milestones` (Runs M1..M5 invariant & challenger suites)

---

## 3. Verification Gates

1. **Gate 1**: `gcc -std=c99 -Wall -Wextra -Werror -pedantic` builds without a single warning.
2. **Gate 2**: `./build/minecraft_headless --test-m1` exits 0 with all 5 validation checks passing.
3. **Gate 3**: `python3 tests/test_runner.py --all` executes and passes 100% of tests.
4. **Gate 4**: `scripts/package_release.py` generates release archive bundles cleanly.
