## 2026-09-03T06:54:27Z
You are spec_miner_world_assets.
Your working directory is: g:/minecraft_desktop/.agents/spec_miner_world_assets/
MANDATORY: Read g:/minecraft_desktop/ORIGINAL_REQUEST.md before starting work.
Also thoroughly read:
- g:/minecraft_desktop/docs/03_WORLD_GENERATION_AND_CHUNKS.md
- g:/minecraft_desktop/docs/04_ASSET_PIPELINE_AND_AUDIO.md

Your mission:
1. Extract and document all specifications, constraints, and requirements regarding:
   - World representation: chunk dimensions (e.g. 16x16x256 or 16x16x64), chunk indexing, coordinate systems (world vs local), chunk storage data structures.
   - World generation: Perlin/Simplex noise generation, octaves, persistence, scale, heightmaps, biomes (Plains, Forest, Mountains, Desert, etc.), tree placement, ore veins, cave generation, seed determinism.
   - Voxel meshing: face culling (omitting faces between opaque blocks), greedy meshing or quad generation, vertex attributes, transparent/translucent pass (water, glass) vs opaque pass.
   - Lighting & shading: ambient occlusion calculation (per-vertex AO from neighbor voxels), sunlight / block light propagation or directional shading.
   - Asset pipeline: canonical block textures (dirt, grass, stone, wood, leaves, etc.), procedural texture synthesis or zero-external-dependency embedded textures/atlas, UV mapping.
   - Audio engine: procedural audio synthesis or embedded WAV/OGG, sound events (footsteps by block type, block break, block place, click), zero-dependency audio output.
   - HUD & Menus: crosshair, hotbar UI, health hearts, inventory screen, pause menu.
2. Structure your findings into clear feature requirements, data formats, and performance constraints.
3. Write your detailed report to g:/minecraft_desktop/.agents/spec_miner_world_assets/spec_report.md and write a complete self-contained handoff.md in your working directory.
4. When done, send a message to parent summarizing your findings and pointing to your report.
Note: You are a read-only specification miner. Do not write or modify source code or documentation files. Write only to your working directory.
