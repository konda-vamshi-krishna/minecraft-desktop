## 2026-09-03T09:37:31Z
You are explorer_m3_fsm, an Explorer subagent for Milestone 3 (Core Gameplay & Physics) of the Minecraft Desktop project.

Your Working Directory: g:/minecraft_desktop/.agents/explorer_m3_fsm/
Project Root: g:/minecraft_desktop

Authoritative Documents to Read:
- g:/minecraft_desktop/ORIGINAL_REQUEST.md
- g:/minecraft_desktop/docs/02_CORE_GAMEPLAY_FEATURES.md (§5 Block Destruction & Placement, §6 Inventory)
- g:/minecraft_desktop/docs/06_OFFICIAL_MINECRAFT_CANONICAL_SPEC.md (§3 Mechanics, Block Hardness)
- g:/minecraft_desktop/.agents/orchestrator/PROJECT.md (§ Feature Inventory 30-38, M3, M4)
- g:/minecraft_desktop/src/world/world.h
- g:/minecraft_desktop/tests/canonical_models.py
- g:/minecraft_desktop/tests/tier1_features/test_inventory_system.py

Mission & Scope:
Investigate, specify, and design the Block Destruction FSM, Placement Validation, and 9-Slot Hotbar Item State Machine for Milestone 3.
You do NOT modify source files directly. You produce an exhaustive analysis and proposed C99 header/source specification for interaction and hotbar state machines.

Key Deliverables in your handoff.md:
1. Block Destruction FSM:
   - Target block tracking: coordinates (x, y, z) and current block ID. If cursor moves away, reset progress.
   - Destruction progress accumulation: Delta P = (Delta t * M_tool) / (Hardness * divisor).
   - Hardness table for canonical blocks (Stone, Dirt, Grass, Wood, Cobblestone, Bedrock is indestructible).
   - Crack animation stages 0..9 mapped from [0.0, 1.0) normalized progress.
   - On completion (P >= 1.0), set block to BLOCK_AIR, play break effect/sound trigger, and spawn item stack drop.
2. Block Placement Validation:
   - Target face normal n from raycast gives placement coordinate P_place = P_block + n.
   - Anti-suffocation / AABB intersection test: check if block AABB [P_place, P_place + (1,1,1)] intersects player AABB. Reject placement if true.
   - Check target voxel is air/replaceable.
   - Decrement active hotbar item stack count upon successful placement.
3. 9-Slot Hotbar State Machine:
   - Active slot index: 0..8.
   - Input selection: direct number keys 1..9 (slot = key - 1).
   - Scroll wheel selection: relative delta scroll with modulo wrap-around `(slot - delta) % 9` (proper positive modulo `((slot - delta) % 9 + 9) % 9`).
   - Item stack structure: `uint8_t itemId`, `uint8_t count`, `uint8_t maxStack` (typically 64 for blocks).
   - Hotbar array: 9 contiguous item stacks.
4. Output proposed `interaction.h`, `interaction.c`, `inventory.h`, `inventory.c` specifications with clean C99 code, zero heap allocations, and Ponytail comments.
5. Write your complete handoff report to `g:/minecraft_desktop/.agents/explorer_m3_fsm/handoff.md` and send a completion message back to parent.
