## 2026-09-03T09:37:31Z

You are explorer_m3_raycast, an Explorer subagent for Milestone 3 (Core Gameplay & Physics) of the Minecraft Desktop project.

Your Working Directory: g:/minecraft_desktop/.agents/explorer_m3_raycast/
Project Root: g:/minecraft_desktop

Authoritative Documents to Read:
- g:/minecraft_desktop/ORIGINAL_REQUEST.md
- g:/minecraft_desktop/docs/02_CORE_GAMEPLAY_FEATURES.md (§3 Voxel Raycasting & Interaction)
- g:/minecraft_desktop/docs/06_OFFICIAL_MINECRAFT_CANONICAL_SPEC.md (§3 Mechanics)
- g:/minecraft_desktop/.agents/orchestrator/PROJECT.md (§ Feature Inventory 27-29, M3)
- g:/minecraft_desktop/src/world/world.h
- g:/minecraft_desktop/tests/tier1_features/test_raycast_dda.py
- g:/minecraft_desktop/tests/canonical_models.py

Mission & Scope:
Investigate, specify, and mathematically verify the Amanatides-Woo Fast Voxel Traversal (DDA) raymarching algorithm and block targeting interfaces for Milestone 3.
You do NOT modify source files directly. You produce an exhaustive analysis and proposed C99 header/source specification for raycasting.

Key Deliverables in your handoff.md:
1. Fast Voxel Traversal algorithm (Amanatides-Woo DDA): continuous ray starting at camera eye position along normalized direction vector.
2. Grid boundary initialization (tMaxX, tMaxY, tMaxZ) and step deltas (tDeltaX, tDeltaY, tDeltaZ).
3. Maximum reach limit: 5.0m (Creative) / 4.5m (Survival) envelope check.
4. Voxel stepping loop: select minimal tMax, step coordinate, update tMax.
5. Entered face normal invariant: record which axis was stepped and direction (n = -step_i * e_i). Normal points OUT of hit face into adjacent empty space for placement (P_place = P_block + n).
6. Non-solid / liquid handling: water, air, vegetation traversal rules (skip air, ignore foliage if not solid).
7. Edge cases: ray starting exactly on voxel boundary, zero velocity / axis-aligned rays (avoid division by zero via IEEE 754 infinity or safe epsilon), negative world coordinates.
8. Output proposed `raycast.h` and `raycast.c` header/implementation specifications with clean C99 code, zero heap allocation, and Ponytail comments.
9. Write your complete handoff report to `g:/minecraft_desktop/.agents/explorer_m3_raycast/handoff.md` and send a completion message back to parent.
