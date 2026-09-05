## 2026-09-03T10:56:07Z
You are worker_m4, the Implementation Worker for Milestone 4 (Embedded Assets & Audio) of the Minecraft Desktop project.

Your Working Directory: g:/minecraft_desktop/.agents/worker_m4/
Parent Conversation ID: f5d83ad6-c417-4430-a914-56dc22f5b569

Authoritative User Request: g:/minecraft_desktop/ORIGINAL_REQUEST.md
Specification References:
- g:/minecraft_desktop/docs/04_ASSET_PIPELINE_AND_AUDIO.md (Ratified asset & audio architecture)
- g:/minecraft_desktop/.agents/spec_miner_world_assets/spec_report.md (Mined specs)
- g:/minecraft_desktop/.agents/orchestrator/PROJECT.md (Project milestones & interfaces)
- g:/minecraft_desktop/tests/canonical_models.py (Canonical Python audio & asset models)
- g:/minecraft_desktop/tests/tier1_features/test_audio_synthesis.py (Tier 1 audio tests)

YOUR EXCLUSIVE WRITE OWNERSHIP:
- src/assets/atlas_data.h
- src/assets/assets.h
- src/assets/assets.c
- src/audio/audio.h
- src/audio/synthesizer.c
- tests/test_m4_assets_audio.py
- CMakeLists.txt and Makefile (register new source files)
- g:/minecraft_desktop/.agents/worker_m4/* (your state files: BRIEFING.md, progress.md, handoff.md)

IMPLEMENTATION REQUIREMENTS:
1. src/assets/:
   - Embedded 256x256 Master Texture Atlas in .rodata (atlas_data.h):
     * 16x16 grid of 16x16 pixel textures (256 KiB RGBA32 decompressed array in .rodata).
     * Zero loose files, zero runtime filesystem calls (fopen/disk reads).
     * Accurate pixel textures for blocks: Air (0), Grass Top (0,0), Stone (1,0), Dirt (2,0), Grass Side (3,0), Cobblestone (0,1), Bedrock (1,1), Sand (2,1), Wood Bark (4,1), Wood Rings (5,1), Leaves (4,3), Glass (1,3), Water (13,12), Missing Texture (15,15).
     * Rows 12-15 reserved for ASCII bitmap font.
   - 6-Face Block Visual Table (assets.h & assets.c):
     * BlockFace enum: FACE_WEST=0 (-X), FACE_EAST=1 (+X), FACE_NORTH=2 (-Z), FACE_SOUTH=3 (+Z), FACE_TOP=4 (+Y), FACE_BOTTOM=5 (-Y).
     * Tile mapping: TileCoord GetBlockTextureTile(uint8_t blockType, BlockFace face).
     * UV coordinate normalization with bleed protection: FaceUV CalculateFaceUV(uint8_t blockType, BlockFace face).
     * CCW quad winding order definitions for vertex generation.
     * Texture initialization API: GLuint LoadEmbeddedAtlas(void) or const uint8_t* Assets_GetAtlasData(size_t* outWidth, size_t* outHeight).
2. src/audio/:
   - Real-Time Procedural 8-Bit Sound Synthesizer (audio.h & synthesizer.c):
     * 16-voice polyphonic real-time software audio mixer (MAX_ACTIVE_VOICES 16, SAMPLE_RATE 44100).
     * Sound events (SoundID):
       - SFX_CLICK: UI Click (15ms, 2400 Hz square wave, linear decay).
       - SFX_STEP: Footstep (40ms, 16-bit Galois LFSR noise + 80 Hz triangle thump, exponential decay lambda=65).
       - SFX_JUMP: Jump (90ms, 25% duty square wave, 140 Hz -> 560 Hz ascending sweep, 5ms linear attack, 85ms decay).
       - SFX_BLOCK_BREAK: Block Break (160ms, modulated LFSR noise + pitch-falling square subharmonic 120 -> 0 Hz, power decay (1 - (t/0.160)^0.7)).
       - SFX_BLOCK_PLACE: Block Place (50ms, triangle wave pitch plummet 220*2^(-25t), exponential decay e^(-50t)).
     * Mixer functions:
       - void Audio_Init(int sampleRate);
       - void Audio_PlaySound(SoundID id, float volume);
       - void AudioMixerCallback(float* outputBuffer, int frameCount);
       - void Audio_Shutdown(void);
     * Voice stealing, idle voice channel ring allocation, hard saturation limiter [-1.0, 1.0].
3. Tests & Verification:
   - Create tests/test_m4_assets_audio.py verifying atlas dimensions, tile coordinates, UV mappings for all block faces, audio sound sample counts, durations, bounds [-1.0, 1.0], decay curves, and 16-voice polyphony.
   - Run python tests/test_runner.py and ensure 100% passing tests.
   - Update CMakeLists.txt and Makefile to include the new source files.

PONYTAIL PRINCIPLES:
- Zero host binary downloads: do NOT download external compilers or toolchains.
- Minimal code, zero unnecessary abstractions, pure Python test-runner verification.
- Include // ponytail: comments marking intentional simplifications and upgrade paths.
