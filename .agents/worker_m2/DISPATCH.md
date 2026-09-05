# Dispatch — worker_m2

## 2026-09-03T09:00:00Z
**Mission**: Implement Milestone 2 (World Generation, Chunks & Meshing) in `src/world/` adhering to the complete specifications from `explorer_m2_chunk`, `explorer_m2_terrain`, and `explorer_m2_mesher`.

**Working Directory**: `g:/minecraft_desktop/.agents/worker_m2/`
**Authoritative Sources**:
- `g:/minecraft_desktop/ORIGINAL_REQUEST.md`
- `g:/minecraft_desktop/docs/03_WORLD_GENERATION_AND_CHUNKS.md`
- `g:/minecraft_desktop/.agents/orchestrator/PROJECT.md`
- `g:/minecraft_desktop/.agents/explorer_m2_chunk/handoff.md`
- `g:/minecraft_desktop/.agents/explorer_m2_terrain/handoff.md`
- `g:/minecraft_desktop/.agents/explorer_m2_mesher/handoff.md`

**Exclusive Write Ownership**:
- `src/world/world.h`
- `src/world/chunk.c`
- `src/world/terrain.h`
- `src/world/terrain.c`
- `src/world/mesher.h`
- `src/world/mesher.c`
- `tests/test_m2_chunk_invariants.py`
- `tests/test_m2_terrain_spec.py`
- `tests/test_m2_mesher_invariants.py`

**Mandatory Integrity Warning**:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

**Key Requirements**:
1. Implement `src/world/world.h` and `src/world/chunk.c`:
   - 64 KiB flat contiguous chunk memory layout (`uint8_t voxels[65536]`, 64-byte alignment).
   - Y-internal index formula `y + 256*x + 4096*z`.
   - Floored coordinate transformations (`w >> 4` and `w & 15`).
   - 17x17 toroidal active chunk grid (289 chunks, BSS/static memory).
   - Canonical 14-block palette enum (`BLOCK_AIR=0` through `BLOCK_TALLGRASS=13`) with branchless bitmask opacity queries.
2. Implement `src/world/terrain.h` and `src/world/terrain.c`:
   - Multi-octave 2D Simplex noise with fBM (4-6 octaves, persistence 0.5, lacunarity 2.0, base sea level offset y=64).
   - Dual-parameter Whittaker biome matrix (Temperature & Moisture fields) mapping Plains, Desert, Mountains, Forest with canonical stratigraphy (bedrock y=0..4, stone core, dirt/sand sub-surface, topsoil grass/sand/snow, water y<=62).
   - 3D volumetric density and cave carve-out via dual 3D Simplex noise (|N1| < 0.05 and |N2| < 0.05 for y in [5, 128]).
   - Deterministic SplitMix64 coordinate PRNG and cellular tree/vegetation stamping within local [2, 13] bounds.
3. Implement `src/world/mesher.h` and `src/world/mesher.c`:
   - 3-axis Lysenko Greedy Meshing algorithm across X, Y, Z slice planes with 2D comparison mask with signed block IDs.
   - Clamp quad height along Y to H <= 255 to prevent 8-bit overflow in packed vertices.
   - Cross-chunk boundary neighbor face culling using adjacent chunk pointers (negX, posX, negZ, posZ).
   - 8-byte packed vertex format (data0: X:5, Y:9, Z:5, Normal:3, AO:2, BlockID:8; data1: U:8, V:8, W:8, H:8).
   - 4-level vertex ambient occlusion (0..3) with quad diagonal index flip guard (`AO0 + AO2 > AO1 + AO3`).
   - Counter-clockwise (CCW) winding preserved on all 6 faces.
4. Testing & Verification:
   - Provide comprehensive Python invariant tests (`test_m2_chunk_invariants.py`, `test_m2_terrain_spec.py`, `test_m2_mesher_invariants.py`).
   - Run verification commands: `python -m unittest tests/test_m2_chunk_invariants.py`, `python -m unittest tests/test_m2_terrain_spec.py`, `python -m unittest tests/test_m2_mesher_invariants.py`, and `python tests/test_runner.py --tier all`.
   - Strictly adhere to Ponytail principles (zero host binary downloads, zero unnecessary abstractions, pure Python test-runner verification).
5. Document all actions, tool outputs, and verification results in `g:/minecraft_desktop/.agents/worker_m2/handoff.md`.
