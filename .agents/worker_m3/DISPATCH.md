## 2026-09-03T15:23:51+05:30
You are worker_m3, the Implementation Worker for Milestone 3 (Core Gameplay & Physics) of the Minecraft Desktop project.

Your Working Directory: g:/minecraft_desktop/.agents/worker_m3/
Project Root: g:/minecraft_desktop

Authoritative Documents & Explorer Handoffs:
- g:/minecraft_desktop/ORIGINAL_REQUEST.md (MANDATORY TO READ FIRST)
- g:/minecraft_desktop/.agents/orchestrator/PROJECT.md
- g:/minecraft_desktop/.agents/explorer_m3_raycast/handoff.md
- g:/minecraft_desktop/.agents/explorer_m3_raycast/proposed_raycast.h
- g:/minecraft_desktop/.agents/explorer_m3_raycast/proposed_raycast.c
- g:/minecraft_desktop/.agents/explorer_m3_physics/handoff.md
- g:/minecraft_desktop/.agents/explorer_m3_physics/proposed_physics.h
- g:/minecraft_desktop/.agents/explorer_m3_physics/proposed_physics.c
- g:/minecraft_desktop/.agents/explorer_m3_fsm/handoff.md
- g:/minecraft_desktop/.agents/explorer_m3_fsm/proposed_interaction.h
- g:/minecraft_desktop/.agents/explorer_m3_fsm/proposed_interaction.c
- g:/minecraft_desktop/.agents/explorer_m3_fsm/proposed_inventory.h
- g:/minecraft_desktop/.agents/explorer_m3_fsm/proposed_inventory.c
- g:/minecraft_desktop/src/world/world.h
- g:/minecraft_desktop/tests/test_runner.py
- g:/minecraft_desktop/tests/canonical_models.py

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

STRICT CONSTRAINTS (Ponytail Minimalism):
1. Zero external binary/toolchain downloads to host machine.
2. Zero dynamic heap allocation (no malloc/calloc/realloc/free). Contiguous static or stack structures only.
3. Strict C99 compatibility.
4. Mark intentional simplifications with a `// ponytail: [limitation/ceiling] -> [upgrade path]` comment in every source file.
5. All local verification must be conducted via pure Python test runners (e.g. `python tests/test_runner.py`, `python tests/test_m3_gameplay_invariants.py`).

Your Scope of Work & Exclusive Write Ownership:
1. Implement in `src/gameplay/`:
   - `src/gameplay/raycast.h` & `src/gameplay/raycast.c`: Amanatides-Woo Fast Voxel Traversal, 5.0m reach, face normal invariant (n = -step_i * e_i), IEEE 754 infinity safe boundary math.
   - `src/gameplay/physics.h` & `src/gameplay/physics.c`: Swept AABB player physics (0.6x1.8m standing, 0.6x1.5m sneaking, eye level 1.62m/1.35m), canonical constants (g=0.08, drag=0.98, friction=0.546, jump=0.42), axis-decoupled collision (Y -> X -> Z), anti-tunneling sub-steps, auto-step (0.55-0.6m), sneak ledge-clamp.
   - `src/gameplay/interaction.h` & `src/gameplay/interaction.c`: Progressive block destruction FSM (0..9 crack stages, canonical hardness table, tool multipliers, bedrock guard H=-1.0, instant break H=0.0), block placement validation (adjacent face, height 0..255, anti-suffocation player AABB intersection rejection).
   - `src/gameplay/inventory.h` & `src/gameplay/inventory.c`: 9-slot hotbar state machine with modulo scroll wrap-around `((slot - delta) % 9 + 9) % 9`, number keys 1..9, 41-slot inventory flat array, stack limits (64/16/1).
   - `src/gameplay/gameplay.h`: Subsystem coordinator header exposing the unified gameplay API.
2. Update build configurations:
   - `CMakeLists.txt`: add `src/gameplay/raycast.c`, `src/gameplay/physics.c`, `src/gameplay/interaction.c`, `src/gameplay/inventory.c` to `CORE_SOURCES`.
   - `Makefile`: add gameplay source files to `SRCS_CORE`.
3. Create invariant verification test:
   - `tests/test_m3_gameplay_invariants.py`: comprehensive unittest verifying file existence, zero heap allocations, canonical constants, structure sizes, API signatures, and Ponytail comments (analogous to `test_m2_c_invariants.py`).
4. Verification:
   - Run `python -m unittest tests/test_m3_gameplay_invariants.py`
   - Run `python tests/test_runner.py` (ensure all tiers pass 100%)
   - Run `python tests/test_m1_c_invariants.py`, `python tests/test_m2_c_invariants.py`, `python tests/test_m2_chunk_invariants.py`, `python tests/test_mesher_canonical.py`
5. Documentation & Handoff:
   - Write comprehensive `handoff.md` in `g:/minecraft_desktop/.agents/worker_m3/handoff.md` with: Observation, Logic Chain, Files Modified/Created, Verification Commands and Outputs, Caveats, Conclusion.
   - Send completion message to parent when done.
