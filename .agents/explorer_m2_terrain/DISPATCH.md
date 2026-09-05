# Dispatch — explorer_m2_terrain

## 2026-09-03T08:52:00Z
**Mission**: Investigate and design multi-octave 2D Simplex terrain generation, Whittaker biomes, 3D cave carve-out, and deterministic feature decoration for Milestone 2.

**Working Directory**: `g:/minecraft_desktop/.agents/explorer_m2_terrain/`
**Authoritative Sources**:
- `g:/minecraft_desktop/ORIGINAL_REQUEST.md`
- `g:/minecraft_desktop/docs/03_WORLD_GENERATION_AND_CHUNKS.md` (§3)
- `g:/minecraft_desktop/.agents/orchestrator/PROJECT.md` (§ Feature Inventory 10-13, M2)
- `g:/minecraft_desktop/tests/canonical_models.py`

**Scope & Objectives**:
1. Mathematical formulation of 2D Simplex noise with fractional Brownian motion (fBM: 4-6 octaves, persistence 0.5, lacunarity 2.0, base sea level offset y=64).
2. Dual-parameter Whittaker biome classification (Temperature & Moisture fields) mapping Plains, Desert, Mountains, Forest with canonical stratigraphy (bedrock y=0..4, stone core, dirt/sand sub-surface, topsoil grass/sand/snow, water y<=62).
3. 3D volumetric density and cave carve-out via dual 3D Simplex noise (|N1| < 0.05 and |N2| < 0.05 for y in [5, 128]).
4. Deterministic SplitMix64 coordinate PRNG and cellular tree/vegetation stamping (oak/pine, leaves canopy, cactus, flowers) without cascading chunk mutation.
5. Provide precise C99 implementation design, math algorithms, and verification tests for `src/world/terrain.c`.
6. Follow Ponytail minimalism (YAGNI, canonical mechanics, shortest clean code, // ponytail comments).
7. Write your report to `g:/minecraft_desktop/.agents/explorer_m2_terrain/handoff.md`.
