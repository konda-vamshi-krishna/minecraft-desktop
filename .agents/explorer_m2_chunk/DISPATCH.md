# Dispatch — explorer_m2_chunk

## 2026-09-03T08:52:00Z
**Mission**: Investigate and design chunk storage, coordinate transforms, active chunk grid, block palettes, and world interfaces for Milestone 2.

**Working Directory**: `g:/minecraft_desktop/.agents/explorer_m2_chunk/`
**Authoritative Sources**:
- `g:/minecraft_desktop/ORIGINAL_REQUEST.md`
- `g:/minecraft_desktop/docs/03_WORLD_GENERATION_AND_CHUNKS.md` (§2)
- `g:/minecraft_desktop/.agents/orchestrator/PROJECT.md` (§ Feature Inventory 7-9, Interface Contracts, M2)
- `g:/minecraft_desktop/tests/canonical_models.py`

**Scope & Objectives**:
1. Contiguous 64 KiB flat chunk memory layout (`uint8_t voxels[65536]`, 64-byte alignment).
2. Y-internal index formula: `Index(x, y, z) = y + 256*x + 4096*z` for optimal vertical cache line streaming.
3. Coordinate transformation math: `WorldToChunkCoord` (floored arithmetic shift for negative coordinates) and `WorldToLocalCoord` (`x & 15`).
4. 17x17 toroidal active chunk grid (289 chunks, ~18.06 MiB static BSS RAM) centered around player, chunk loading/unloading, and chunk modification dirty flags.
5. Canonical block palette enum (`BLOCK_AIR=0, BLOCK_STONE=1, BLOCK_DIRT=2, BLOCK_GRASS=3, BLOCK_SAND=4, BLOCK_SANDSTONE=5, BLOCK_SNOW=6, BLOCK_WOOD=7, BLOCK_LEAVES=8, BLOCK_BEDROCK=9, BLOCK_WATER=10, BLOCK_CACTUS=11, BLOCK_FLOWER=12, BLOCK_TALLGRASS=13`).
6. Interface contracts and data structures for `src/world/world.h` and `src/world/chunk.c`.
7. Write your report to `g:/minecraft_desktop/.agents/explorer_m2_chunk/handoff.md`.
