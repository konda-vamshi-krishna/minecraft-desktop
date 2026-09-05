# Minecraft Desktop — E2E Test Infrastructure & Specification

**Document Version:** 1.0.0  
**Author:** test_writer_e2e (Senior QA & Test Systems Architect)  
**Target Engine:** Minecraft Desktop — Universal 1-Click Native Edition  
**Specification References:** `ORIGINAL_REQUEST.md`, `PROJECT.md`, `docs/01` through `docs/06`

---

## 1. Executive Summary & Testing Philosophy

The **Minecraft Desktop End-to-End (E2E) Test Suite** provides rigorous, opaque-box, requirement-driven verification across all core gameplay mechanics, voxel physics, coordinate bitshifts, inventory state machines, crafting recipes, procedural audio formulas, and real-world survival workloads.

### 1.1 Opaque-Box & Requirement-Driven Architecture
Unlike white-box unit tests coupled to internal function symbols or private struct layouts, this test suite is derived strictly from:
1. The **User Requirements** in `ORIGINAL_REQUEST.md` (R1 Universal Distribution, R2 Canonical Physics & Voxel Interaction, R3 Anvil Chunk World Gen, R4 Embedded Asset & Audio Pipeline).
2. The **Canonical Game Specifications** in `docs/01_ARCHITECTURE_AND_RUNTIME.md` through `docs/06_OFFICIAL_MINECRAFT_CANONICAL_SPEC.md`.
3. The **Subsystem Contracts** codified in `PROJECT.md`.

Tests verify behavioral contracts, mathematical invariants, state transition rules, and end-to-end user journeys. The tests run cleanly in headless CI environments without requiring physical GPU contexts, display servers, or external third-party test dependencies.

---

## 2. Test Suite Architecture & Tier Hierarchy

The test infrastructure is structured into four distinct, progressive tiers designed to test components from pure isolated invariants up to complex multi-step survival sessions:

```
tests/
├── test_runner.py                 # Master Test Runner CLI (--tier, --verbose, --headless, --json-report)
├── canonical_models.py            # Canonical Specification Oracles & Mathematical Invariants
├── tier1_features/                # Functional Contract Tests (>=5 tests per feature)
│   ├── test_physics_kinematics.py
│   ├── test_raycast_dda.py
│   ├── test_inventory_system.py
│   ├── test_crafting_engine.py
│   ├── test_audio_synthesis.py
│   ├── test_basepath_resolver.py
│   └── test_fixed_loop_timing.py
├── tier2_boundaries/              # Boundary Value Analysis & Corner Case Tests (>=5 tests per boundary)
│   ├── test_negative_coordinates.py
│   ├── test_terminal_velocity_tunneling.py
│   ├── test_autostep_ceiling_abort.py
│   ├── test_sneak_ledge_clamp.py
│   ├── test_anti_suffocation_placement.py
│   ├── test_bedrock_indestructibility.py
│   └── test_inventory_remainder_retention.py
├── tier3_interactions/            # Pairwise Cross-Feature Integration Tests (>=5 tests per pair)
│   ├── test_sprint_jump_exhaustion.py
│   ├── test_dda_mining_drop_pickup.py
│   ├── test_crafting_table_lifecycle.py
│   └── test_autostep_sneak_cornering.py
└── tier4_workloads/               # Real-World Workload Scenarios & Play Sessions
    ├── test_first_day_survival.py
    ├── test_death_respawn_workflow.py
    └── test_celestial_day_night_workflow.py
```

### 2.1 Tier 1: Functional Feature Verification
Tier 1 establishes baseline behavioral conformance for every primary engine feature:
- **Physics Kinematics**: Gravity ($g = -32.0\text{ m/s}^2$), terminal velocity ($-78.4\text{ m/s}$), jump impulse ($8.944\text{ m/s}$ clearing $1.25\text{m}$), AABB bounding dimensions ($0.6 \times 1.8\text{m}$ standing, $0.6 \times 1.5\text{m}$ sneaking), camera eye levels ($1.62\text{m}$ standing, $1.35\text{m}$ sneaking), friction ($0.546$) and drag ($0.98$).
- **Amanatides-Woo DDA Raycast**: Discrete 3D voxel grid traversal, parametric step calculation ($t_{\Delta}, t_{\text{Max}}$), entered face normal invariant ($\mathbf{n} = -\text{step}_i \hat{\mathbf{e}}_i$), reach boundaries ($5.0\text{m}$ Creative, $4.5\text{m}$ Survival).
- **Inventory System**: 41 contiguous slots (9 hotbar + 27 main + 4 armor + 1 offhand), hotbar selection scroll modulo 9, canonical stack limits ($64, 16, 1$), cursor stack interactions.
- **Crafting Engine**: 2x2 player crafting grid, 3x3 crafting table grid, translation-invariant shaped recipe matching, order-independent shapeless matching, full canonical recipe catalog.
- **Procedural Audio Formulas**: Real-time synthesis of UI Click, Footstep (LFSR noise + 80Hz thump), Jump (140-560Hz sweep), Block Break (LFSR + sub-harmonic), and Block Place (pitch plummet $220 \cdot 2^{-25t}$).
- **Base-Path Resolver**: Discovery of executable base folder across Win32 (`GetModuleFileNameW`), Linux (`/proc/self/exe`), macOS (`_NSGetExecutablePath`), ensuring `./saves/` adjacency and read-only fallback.
- **Fixed 60Hz Loop Timing**: Sub-frame accumulator clamping ($0.25\text{s}$), render interpolation alpha ($\alpha \in [0.0, 1.0)$), position lerp.

### 2.2 Tier 2: Boundary Value Analysis (BVA) & Corner Tests
Tier 2 exercises singular stress points and mathematical boundary conditions:
- **Negative Coordinate Bitshifts**: Floored coordinate division across negative chunk boundaries ($X = -1 \implies CX = -1, lx = 15$; $X = -16 \implies CX = -1, lx = 0$; $X = -17 \implies CX = -2, lx = 15$).
- **Terminal Velocity Tunneling**: Falling at $-78.4\text{ m/s}$ ($\Delta y = -1.306\text{ m/tick}$) against 1-block and 0.5m-slab floors without tunneling through.
- **Auto-Step Ceiling Collision Abort**: Speculative $+0.55\text{m}$ upward probe aborting when headroom clearance is $< 1.8\text{m}$, preventing suffocation and ceiling phase.
- **Sneak Ledge Edge-Clamp**: Speculative $-0.05\text{m}$ / $-0.1\text{m}$ downward probe preventing fall-off while preserving 2D convex corner gliding.
- **Anti-Suffocation Placement Rejection**: Placement rejected if block AABB intersects standing or sneaking player AABB, or exceeds world height limits ($Y \notin [0, 255]$).
- **Bedrock / Hardness $\le 0$**: Bedrock indestructibility ($H = -1.0$ or $255$), instant-break blocks ($H = 0.0$), crack stage mapping $[0..9]$, break progress cancellation.
- **Inventory Remainder Retention**: Partial stack overflows, left-drag equal distribution with cursor remainder, right-drag 1-per-slot, full inventory rejection without item destruction.

### 2.3 Tier 3: Pairwise Cross-Feature Interactions
Tier 3 targets multi-system feedback loops and orthogonal feature interactions:
- **Sprint-Jumping + Exhaustion**: Kinematic sprint speed ($5.612\text{ m/s}$) and jump impulse draining hunger exhaustion; hunger dropping below 6 shanks disabling sprinting; dynamic FOV smoothly decaying from $1.15 \times$ to $1.0 \times$.
- **DDA Raycast + Progressive Mining + Item Drops + Inventory Pickup**: Raycasting target block, breaking block over hardness duration, spawning 3D bobbing item drop, moving into collection radius ($1.5\text{m}$), collecting into inventory slot.
- **Crafting Table Right-Click + 3x3 Recipe + Remainder Drops on Close**: Opening 3x3 interface, crafting complex multi-ingredient item (furnace / pickaxe), closing container with orphan items in matrix, verifying zero item duplication or loss.
- **Auto-Step + Sneak Cornering**: Ascending a 0.5m slab via auto-step while sneaking, approaching the elevated edge, engaging ledge clamp, and navigating around convex ledge corners safely.

### 2.4 Tier 4: Real-World Application Workloads
Tier 4 executes complete multi-minute play sessions and end-to-end user journeys:
- **First Day Survival**: Complete 14-step canonical workflow:
  Punch tree $\to$ collect 4 logs $\to$ 2x2 craft 16 planks $\to$ craft Crafting Table $\to$ place table in world $\to$ craft sticks $\to$ open table $\to$ 3x3 craft Wooden Pickaxe $\to$ mine 11 stone $\to$ craft Stone Pickaxe $\to$ craft Furnace $\to$ mine coal $\to$ craft 4 Torches $\to$ verify durability decrement, hunger exhaustion, and final inventory state.
- **Death & Respawn Lifecycle**: Taking fatal fall damage ($d = 25\text{m} \implies 22\text{ damage} \ge 20\text{ HP}$), scattering inventory drops, respawning at origin with reset HP and empty inventory.
- **Celestial Day/Night Progression**: Simulating 1200s (20 minute) world clock, verifying sun orbital trajectory, directional face occlusion shading ($1.0, 0.5, 0.8, 0.6$), and day/night sky transitions.

---

## 3. Test Runner CLI & Specification

The custom test runner is implemented in `tests/test_runner.py` using Python 3 standard library.

### 3.1 Command-Line Interface
```bash
python tests/test_runner.py [OPTIONS]
```

| Flag | Argument | Description |
| :--- | :--- | :--- |
| `--tier` | `1`, `2`, `3`, `4` (comma or space separated) | Run specific test tier(s). Default: all tiers. |
| `--verbose` | None | Enable verbose per-test output and execution timings. |
| `--headless` | None | Enforce headless execution mode (default true in CI). |
| `--json-report` | `[PATH]` | Output detailed machine-readable JSON report (default: `test_report.json`). |
| `-h`, `--help` | None | Display help and usage information. |

### 3.2 Exit Codes
- `0`: All executed test cases passed successfully.
- `1`: One or more test cases failed or errored.
- `2`: Invalid CLI arguments or configuration error.

### 3.3 Output Formatting
The runner outputs an ANSI colorized summary matrix:
- **Tier 1 (Features)**: Test count, Pass count, Fail count, Execution duration.
- **Tier 2 (Boundaries)**: Test count, Pass count, Fail count, Execution duration.
- **Tier 3 (Interactions)**: Test count, Pass count, Fail count, Execution duration.
- **Tier 4 (Workloads)**: Test count, Pass count, Fail count, Execution duration.
- **Total Suite Metrics**: Total tests, total assertions, overall status (`ALL PASS` in green or `FAILURES DETECTED` in red).

---

## 4. Coverage Methodology

| Methodology | Application in Minecraft Desktop Test Suite |
| :--- | :--- |
| **Category-Partition** | Partitioning inputs into disjoint classes: item stack limits (1, 16, 64), movement states (walk, sprint, sneak), face orientations (6 faces), block hardness tiers ($0.0$, $0.5$, $1.5$, $2.0$, $-1.0$). |
| **Boundary Value Analysis (BVA)** | Testing values strictly at, above, and below thresholds: reach distance ($4.99\text{m}, 5.00\text{m}, 5.01\text{m}$), world height ($-1, 0, 255, 256$), coordinate chunk boundaries ($-17, -16, -1, 0, 15, 16$), hunger exhaustion ($5.9, 6.0, 6.1$). |
| **Pairwise (All-Pairs)** | Testing combinations of orthogonal features (sprinting $\times$ jumping $\times$ starvation; mining $\times$ raycasting $\times$ drops; sneak $\times$ auto-step $\times$ cornering). |
| **Real-World Workloads** | Replicating authentic user behavior sequences over extended gameplay timeframes with state accumulation. |

---

## 5. Verification & Audit Trail

All test suites can be executed independently or through the unified runner:
```bash
python tests/test_runner.py --tier 1,2,3,4 --verbose --json-report
```
Machine-readable reports conform to the schema:
```json
{
  "timestamp": "2026-09-03T07:30:00Z",
  "summary": {
    "total_tests": 75,
    "passed": 75,
    "failed": 0,
    "errors": 0,
    "duration_seconds": 0.45
  },
  "tiers": {
    "tier1_features": { "tests": 35, "passed": 35, "failed": 0 },
    "tier2_boundaries": { "tests": 35, "passed": 35, "failed": 0 },
    "tier3_interactions": { "tests": 20, "passed": 20, "failed": 0 },
    "tier4_workloads": { "tests": 15, "passed": 15, "failed": 0 }
  }
}
```
