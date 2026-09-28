# 02. Defect, Vulnerability, and Feature Gap Matrix

**Audit Date:** 2026-09-28  
**Auditing Subsystem:** Team 1 — Static Analysis & Code Audit  
**Classification Standard:** IEEE 1044 Defect Classification & ISO/IEC 25010 Quality Model  

---

## 1. Defect & Feature Gap Catalog

| Defect ID | Category | Affected File(s) | Severity | Description | Impact |
|:---|:---|:---|:---:|:---|:---|
| **DEF-01** | **Build System** | `Makefile` | **High** | Linux target unconditionally links `-lGL -lX11` even for `-DHEADLESS_ONLY`. | `make` fails on standard headless Linux servers or CI containers without GUI desktop libs. |
| **DEF-02** | **C99 Conformance** | `src/platform/platform_desktop.c` | **Medium** | Unused function parameters (`keyCode`, `button`) in 6 platform input query functions in headless mode. | Fails compilation under `-Wall -Wextra -Werror` (`-Wunused-parameter`). |
| **DEF-03** | **Memory & String Safety** | `src/platform/platform_desktop.c` | **Medium** | `strncpy` calls copying full buffer lengths trigger `-Wstringop-truncation` warnings. | Compiler warning / potential unbounded read if source is not null-terminated. |
| **DEF-04** | **C99 Conformance** | `src/main.c` | **Medium** | `App_GetItemShortName` is static and defined at top level but only referenced inside `#if USE_RAYLIB`. | `-Wunused-function` error when compiling headless with `-Werror`. |
| **DEF-05** | **Type Safety** | `src/main.c` | **Medium** | `SOUND_CLICK`, `SOUND_JUMP`, etc. (`enum SoundEvent`) passed directly to `Audio_PlaySound` (which expects `SoundID`). | `-Wenum-conversion` error under strict C99 compilation flags. |
| **DEF-06** | **Engine Logic** | `src/main.c` | **Low** | `World_SetBlock(..., BLOCK_AIR)` called twice on block break (once in `Interaction_UpdateDestruction` and once in `App_OnPhysicsTick`). | Redundant world state mutation and potential race condition if hit state changes. |
| **DEF-07** | **Feature Gap** | `src/gameplay/inventory.h`, `src/gameplay/inventory.c` | **Medium** | C codebase lacked native C99 Crafting Engine functions for 2x2 and 3x3 recipe matching and ingredient consumption. | Asymmetry between Python canonical specification model and C native runtime. |
| **DEF-08** | **Test Incompleteness** | `tests/test_challenger_platform.py` | **Medium** | File contains only `# test` (0 test cases implemented). | Platform layer edge cases (timer, basepath, input queries, fallback) lacked challenger verification. |
| **DEF-09** | **Test Infrastructure** | `tests/test_runner.py` | **Low** | Runner only executes Tier 1..4 (105 tests), omitting milestone invariant suites (174 tests). | Lack of single-command execution for all 279+ tests across the repository. |
| **DEF-10** | **Portability / UX** | `launch_game.bat` | **Low** | Launch script assumes `game\minecraft-desktop\minecraft.exe` fixed relative path. | Double-clicking `launch_game.bat` in root or build directory fails to find executable. |

---

## 2. Red Flag & Logical Error Deep-Dive

### 2.1 DEF-01: Makefile Headless Link Invariant Violation
- **Code in Question**:
  ```makefile
  ifeq ($(UNAME_S),Darwin)
      WIN_LIBS = -lm -framework IOKit -framework Cocoa -framework OpenGL -framework CoreVideo
  else
      WIN_LIBS = -lGL -lm -lpthread -ldl -lrt -lX11
  endif
  ...
  $(TARGET_HEADLESS): $(SRCS_CORE) $(SRCS_MAIN)
      @$(MKDIR)
      $(CC) $(CFLAGS) -DHEADLESS_ONLY $^ -o $@ $(LDFLAGS) $(WIN_LIBS)
  ```
- **Analysis**:
  The headless binary does not create an X11 window or initialize an OpenGL context. Linking `-lGL` and `-lX11` introduces unnecessary dependencies on desktop GUI packages. In Docker or headless cloud runners, this breaks `make` out of the box.

### 2.2 DEF-02 & DEF-03: Platform Layer Warnings
- In `src/platform/platform_desktop.c`:
  ```c
  bool Platform_IsKeyDown(int keyCode) {
      if (s_Platform.config.headless) return false;
  #if USE_RAYLIB
      return IsKeyDown(keyCode);
  #else
      return false;
  #endif
  }
  ```
  When `USE_RAYLIB` is 0, `keyCode` is never read, prompting `-Wunused-parameter`.
  Adding `(void)keyCode;` (and `(void)button;`) resolves this cleanly.
  Similarly, replacing `strncpy` with `snprintf(outPath, maxLen, "%s", procPath)` ensures null termination and suppresses truncation warnings.

### 2.3 DEF-07: Missing C99 Crafting Engine
- Canonical crafting recipes defined in `docs/02 §6` and `tests/canonical_models.py`:
  - 1 Wood Log $\to$ 4 Wood Planks (2x2 / 3x3 Shapeless)
  - 2 Wood Planks vertically $\to$ 4 Sticks (2x2 / 3x3 Shaped, translation-invariant)
  - 4 Wood Planks (2x2 square) $\to$ 1 Crafting Table (2x2 Shaped)
  - 8 Cobblestone (hollow ring) $\to$ 1 Furnace (3x3 Shaped)
  - 3 Material (Planks / Cobble / Iron) + 2 Sticks $\to$ Pickaxes (3x3 Shaped, durability 59 / 131 / 250)
- Implementing `Crafting_Match` and `Crafting_Craft` directly in `src/gameplay/inventory.c` fulfills functional parity with zero heap allocations.
