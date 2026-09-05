## 2026-09-03T07:14:19Z
You are test_writer_e2e.
Your working directory is: g:/minecraft_desktop/.agents/test_writer_e2e/
Project Root: g:/minecraft_desktop

MANDATORY: Read g:/minecraft_desktop/ORIGINAL_REQUEST.md before starting work.
Also read:
- g:/minecraft_desktop/.agents/orchestrator/PROJECT.md
- g:/minecraft_desktop/docs/ (01 through 06)

Your mission:
You own the E2E Testing Track. You must design and build the comprehensive, opaque-box, requirement-driven test suite derived strictly from user requirements and specifications, not implementation internals.

Exclusively owned files:
- g:/minecraft_desktop/TEST_INFRA.md
- g:/minecraft_desktop/TEST_READY.md
- g:/minecraft_desktop/tests/ (test_runner.py, tier1_features/, tier2_boundaries/, tier3_interactions/, tier4_workloads/)

Execution steps:
1. Create g:/minecraft_desktop/TEST_INFRA.md following the specification in PROJECT.md and docs, documenting test architecture, runner usage, and coverage methodology (Category-Partition, BVA, Pairwise, Real-World Workloads).
2. Implement tests/test_runner.py in Python 3:
   - CLI flags: --tier 1,2,3,4, --verbose, --headless, --json-report
   - Return exit code 0 if all tests pass, non-zero if any test fails
   - Colorized summary table displaying Tier counts, pass/fail status, and coverage metrics
3. Implement Tier 1 Functional Tests (tests/tier1_features/):
   - At least 5 test cases per feature across the core gameplay, physics (gravity, terminal velocity, jump, AABB), raycast (DDA, reach), inventory (41 slots, stack sizes 64/16/1), crafting (2x2, 3x3, canonical recipes), audio formulas, and base-path resolver.
   - Design each test so it can verify pure canonical mathematical logic and component invariants directly or via CLI/subprocesses.
4. Implement Tier 2 Boundary & Corner Tests (tests/tier2_boundaries/):
   - At least 5 test cases per feature covering boundaries (coordinate bitshifts across negative chunk boundaries, terminal velocity falling without tunneling, auto-step ceiling collision abort, sneak ledge edge-clamp, anti-suffocation placement rejection, hardness <= 0 / bedrock, inventory remainder retention).
5. Implement Tier 3 Pairwise Cross-Feature Tests (tests/tier3_interactions/):
   - Pairwise interactions: Sprint-jumping + hunger exhaustion depletion; DDA raycast + progressive mining + inventory slot drop; crafting table right-click + 3x3 recipe + remainder drops on close; auto-step + sneak cornering.
6. Implement Tier 4 Real-World Application Scenarios (tests/tier4_workloads/):
   - Complete gameplay session workflows: "First Day Survival" (punch tree -> collect logs -> craft planks -> craft crafting table -> place table -> craft wooden pickaxe -> mine stone -> craft stone pickaxe -> craft furnace -> mine coal -> craft torches).
7. Run the test suite via python tests/test_runner.py to verify runner functionality and test correctness.
8. When complete and passing, publish g:/minecraft_desktop/TEST_READY.md with full coverage metrics.
9. Deliver handoff.md in your working directory and message parent (e598df24-3a79-45c8-8cc6-d95513d6c1f5).
