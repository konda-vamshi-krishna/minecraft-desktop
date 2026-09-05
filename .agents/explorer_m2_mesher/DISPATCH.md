# Dispatch — explorer_m2_mesher

## 2026-09-03T08:52:00Z
**Mission**: Investigate and design 3-axis Lysenko Greedy Meshing, packed vertex layout, boundary neighbor sampling, and vertex AO for Milestone 2.

**Working Directory**: `g:/minecraft_desktop/.agents/explorer_m2_mesher/`
**Authoritative Sources**:
- `g:/minecraft_desktop/ORIGINAL_REQUEST.md`
- `g:/minecraft_desktop/docs/03_WORLD_GENERATION_AND_CHUNKS.md` (§4)
- `g:/minecraft_desktop/.agents/orchestrator/PROJECT.md` (§ Feature Inventory 14-17, M2)
- `g:/minecraft_desktop/tests/canonical_models.py`

**Scope & Objectives**:
1. Exact formulation of the 3-axis Lysenko Greedy Meshing algorithm: sweep slice planes along X, Y, Z, generate 2D comparison mask with signed block IDs for face orientation (+d vs -d), scanline merge contiguous coplanar faces into maximal quads (width and height expansion).
2. Boundary neighbor sampling: cross-chunk face culling at x=0,15 and z=0,15 using adjacent chunk pointers (negX, posX, negZ, posZ).
3. 4-byte or 8-byte packed vertex format:
   - data0: X (5 bits: 0..16), Y (9 bits: 0..256), Z (5 bits: 0..16), Normal (3 bits: 0..5), AO (2 bits: 0..3), BlockID (8 bits: 0..255).
   - data1: U (8 bits), V (8 bits), Quad Width W (8 bits), Quad Height H (8 bits).
4. 4-level vertex ambient occlusion (0..3) based on corner/side neighbor solid voxel occupancy, with quad diagonal index flip guard: if AO(0)+AO(2) > AO(1)+AO(3), flip index triangulation to eliminate diagonal anisotropy artifacts.
5. Budget-capped meshing: time-budgeted chunk meshing queue (e.g. max 2 chunks per frame, <= 1.5ms) to prevent frame hitching.
6. Write your report to `g:/minecraft_desktop/.agents/explorer_m2_mesher/handoff.md`.
