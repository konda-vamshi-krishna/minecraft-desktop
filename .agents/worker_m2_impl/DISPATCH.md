# Worker M2 Implementation Dispatch

Milestone: Milestone 2 (World Generation, Chunks & Meshing)
Role: teamwork_preview_worker
Working Directory: g:/minecraft_desktop/.agents/worker_m2_impl/
Project Root: g:/minecraft_desktop/

## 2026-09-03T09:10:02Z
You are worker_m2_impl (teamwork_preview_worker) implementing Milestone 2: World Generation, Chunks & Greedy Meshing for the standalone desktop Minecraft clone.

Working Directory: g:/minecraft_desktop/.agents/worker_m2_impl/
Project Root: g:/minecraft_desktop/
Original User Request: g:/minecraft_desktop/ORIGINAL_REQUEST.md
Project Scope Document: g:/minecraft_desktop/.agents/orchestrator/PROJECT.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

STRICT CONSTRAINT:
NEVER download external binary toolchains (such as w64devkit, MinGW zips, compilers, or foreign executables) to the host machine. Delegate all native cross-platform compilation to GitHub Actions CI/CD matrix (.github/workflows/build_and_release.yml). Conduct local verification strictly via pure Python test runners (tests/test_runner.py, Python invariant scripts) and static code audits without downloading external binaries.

Ponytail Principles:
- Zero unrequested abstractions, zero unneeded dependencies, canonical mechanics, concise code.
- Mark intentional simplifications with // ponytail: comments.

Context & Reference Reports:
Read and implement the complete technical specifications from the 3 Milestone 2 Explorer handoffs:
1. Terrain Generation:
   - Report: g:/minecraft_desktop/.agents/explorer_m2_terrain/handoff.md
   - Reference code: g:/minecraft_desktop/.agents/explorer_m2_terrain/proposed_terrain.h and proposed_terrain.c
   - Test scripts: g:/minecraft_desktop/.agents/explorer_m2_terrain/test_terrain_empirical.py, test_m2_terrain_spec.py, test_proposed_terrain_static.py
2. Chunk Architecture & Toroidal Grid:
   - Report: g:/minecraft_desktop/.agents/explorer_m2_chunk/handoff.md
   - Test script: tests/test_m2_chunk_invariants.py
3. Greedy Mesher:
   - Report: g:/minecraft_desktop/.agents/explorer_m2_mesher/handoff.md
   - Test model: tests/test_mesher_canonical.py (described in handoff.md)

Your Tasks:
1. Implement / finalize in src/world/:
   - src/world/terrain.h & src/world/terrain.c: multi-octave 2D Simplex terrain (5 octaves, base f=0.005, A=32, B=64), Whittaker biomes (Plains, Desert, Mountains, Forest), water at y<=62, bedrock at y=0, randomized bedrock at y=1..4, 3D cave carve-out (|N1|<0.05 && |N2|<0.05 for y in [5, 128]), SplitMix64 coordinate PRNG, zero cascading chunk mutations (tree stamping strictly in local [2, 13]).
   - src/world/world.h & src/world/chunk.c: flat 64 KiB contiguous chunk memory (uint8_t voxels[65536], aligned to 64 bytes), Y-internal index formula y + 256*x + 4096*z, coordinate transforms WorldToChunkCoord (w >> 4) and WorldToLocalCoord (w & 15), 17x17 toroidal active grid (radius R=8, 289 chunks in BSS memory ~18.06 MiB, zero heap allocations in loop), block get/set with neighbor boundary dirtiness, neighbor sampling.
   - src/world/mesher.h & src/world/mesher.c: 3-axis Lysenko greedy meshing with normal face scanning, 8-byte packed vertices (PackedVertex: data0 and data1, with width and height clamped to <= 255 to prevent 8-bit overflow), 4-level ambient occlusion with diagonal triangulation flip guard ((ao0+ao2) > (ao1+ao3)) preserving CCW winding, boundary face culling with 4 orthogonal neighbor chunks, time-budgeted priority mesher queue.
2. Update CMakeLists.txt and Makefile to include the new src/world/*.c source files in the build lists (without running native build on host).
3. Ensure 	ests/test_mesher_canonical.py is present in 	ests/ and run all verification scripts:
   - python tests/test_runner.py (must pass 105/105)
   - python tests/test_m2_chunk_invariants.py (must pass 13/13)
   - python .agents/explorer_m2_terrain/test_terrain_empirical.py (must pass 6/6)
   - python .agents/explorer_m2_terrain/test_m2_terrain_spec.py (must pass 6/6)
   - python .agents/explorer_m2_terrain/test_proposed_terrain_static.py (must pass 6/6)
   - python tests/test_mesher_canonical.py (must pass all tests)
4. Write your complete handoff report to g:/minecraft_desktop/.agents/worker_m2_impl/handoff.md with:
   - Observation
   - Logic Chain
   - Caveats
   - Conclusion
   - Verification Method (commands and outputs)
5. Send a completion message back to the caller (orchestrator) with the handoff file path and summary.
