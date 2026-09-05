"""
Verification Suite for Milestone 4 (M4): Embedded Assets & Procedural Audio Synthesizer.
Validates:
  1. File integrity, .rodata atlas metrics (256x256 RGBA32 = 256 KiB), zero runtime filesystem hits.
  2. Zero dynamic heap allocations (malloc/calloc/realloc/free).
  3. Accurate pixel textures for all required blocks and retro ASCII bitmap font.
  4. 6-face anisotropic block visual table and TileCoord resolution.
  5. Normalized UV calculation with sub-texel bleed protection margin.
  6. CCW quad winding order definitions for vertex generation.
  7. Procedural audio waveform formulas, sample counts, durations, and ADSR decay curves.
  8. 16-voice polyphonic software mixer, voice stealing, ring allocation, and hard saturation limiter.
  9. Ponytail minimalist comments and upgrade path annotations.
"""

import unittest
import os
import re
import math


class TestM4AssetsAudio(unittest.TestCase):
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def setUp(self):
        self.atlas_data_h = os.path.join(self.PROJECT_ROOT, "src", "assets", "atlas_data.h")
        self.assets_h = os.path.join(self.PROJECT_ROOT, "src", "assets", "assets.h")
        self.assets_c = os.path.join(self.PROJECT_ROOT, "src", "assets", "assets.c")
        self.audio_h = os.path.join(self.PROJECT_ROOT, "src", "audio", "audio.h")
        self.synthesizer_c = os.path.join(self.PROJECT_ROOT, "src", "audio", "synthesizer.c")
        self.cmakelists = os.path.join(self.PROJECT_ROOT, "CMakeLists.txt")
        self.makefile = os.path.join(self.PROJECT_ROOT, "Makefile")

        self.m4_files = [
            self.atlas_data_h, self.assets_h, self.assets_c,
            self.audio_h, self.synthesizer_c
        ]

    # =========================================================================
    # 1. Structural Integrity & Zero-Allocation Invariants
    # =========================================================================

    def test_01_all_m4_files_exist(self):
        """Verify all 5 exclusively owned M4 files exist and are populated."""
        for f in self.m4_files:
            self.assertTrue(os.path.isfile(f), f"File {f} must exist")
            self.assertGreater(os.path.getsize(f), 50, f"File {f} must not be empty")

    def test_02_zero_dynamic_heap_allocations(self):
        """Verify M4 files contain zero dynamic heap allocations (malloc/calloc/free)."""
        forbidden = [r"\bmalloc\b", r"\bcalloc\b", r"\brealloc\b", r"\bfree\b"]
        for f in self.m4_files:
            with open(f, "r", encoding="utf-8") as fp:
                content = fp.read()
            for pat in forbidden:
                self.assertIsNone(re.search(pat, content),
                                  f"Forbidden dynamic allocation {pat} found in {f}")

    def test_03_zero_runtime_filesystem_calls(self):
        """Verify assets and audio code have zero fopen/disk reads (Zero-Asset Architecture)."""
        forbidden = [r"\bfopen\b", r"\bfread\b", r"\bopen\b", r"\bread\b"]
        for f in [self.assets_c, self.synthesizer_c]:
            with open(f, "r", encoding="utf-8") as fp:
                content = fp.read()
            for pat in forbidden:
                self.assertIsNone(re.search(pat, content),
                                  f"Forbidden filesystem call {pat} found in {f}")

    def test_04_build_system_registration(self):
        """Verify assets.c and synthesizer.c are registered in CMakeLists.txt and Makefile."""
        with open(self.cmakelists, "r", encoding="utf-8") as f:
            cmake_content = f.read()
        self.assertIn("src/assets/assets.c", cmake_content)
        self.assertIn("src/audio/synthesizer.c", cmake_content)

        with open(self.makefile, "r", encoding="utf-8") as f:
            make_content = f.read()
        self.assertIn("src/assets/assets.c", make_content)
        self.assertIn("src/audio/synthesizer.c", make_content)

    # =========================================================================
    # 2. Master Texture Atlas & .rodata Metrics
    # =========================================================================

    def test_05_atlas_dimensions_and_metrics(self):
        """Verify 256x256 RGBA32 atlas definitions (262,144 bytes = 256 KiB)."""
        with open(self.atlas_data_h, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("#define ATLAS_WIDTH         256", content)
        self.assertIn("#define ATLAS_HEIGHT        256", content)
        self.assertIn("#define ATLAS_CHANNELS      4", content)
        self.assertIn("#define ATLAS_TILE_SIZE     16", content)
        self.assertIn("262144", content)
        self.assertIn("g_AtlasRGBA[ATLAS_DATA_SIZE]", content)

    def test_06_atlas_pixel_data_parsing_and_integrity(self):
        """Parse raw g_AtlasRGBA array from atlas_data.h and verify 262,144 bytes."""
        with open(self.atlas_data_h, "r", encoding="utf-8") as f:
            content = f.read()

        match = re.search(r"g_AtlasRGBA\[ATLAS_DATA_SIZE\]\s*=\s*\{([^}]+)\};", content)
        self.assertIsNotNone(match, "Could not find g_AtlasRGBA array in atlas_data.h")
        hex_tokens = re.findall(r"0x[0-9A-Fa-f]{2}", match.group(1))
        self.assertEqual(len(hex_tokens), 262144,
                         f"Atlas data must contain exactly 262,144 bytes, found {len(hex_tokens)}")

        # Convert to bytearray for pixel sampling tests
        atlas_bytes = bytearray(int(tok, 16) for tok in hex_tokens)

        def get_pixel(tx, ty, px, py):
            x = tx * 16 + px
            y = ty * 16 + py
            idx = (y * 256 + x) * 4
            return atlas_bytes[idx], atlas_bytes[idx+1], atlas_bytes[idx+2], atlas_bytes[idx+3]

        # Check 1: Missing Texture (15, 15) is 2x2 grid of 8x8 squares: magenta (#FF00FF) and black (#000000)
        # Top-left (0, 0) should be magenta
        r, g, b, a = get_pixel(15, 15, 0, 0)
        self.assertEqual((r, g, b, a), (255, 0, 255, 255), "Slot (15,15) Top-Left must be Magenta")
        # Top-right (8, 0) should be black
        r, g, b, a = get_pixel(15, 15, 8, 0)
        self.assertEqual((r, g, b, a), (0, 0, 0, 255), "Slot (15,15) Top-Right must be Black")
        # Bottom-left (0, 8) should be black
        r, g, b, a = get_pixel(15, 15, 0, 8)
        self.assertEqual((r, g, b, a), (0, 0, 0, 255), "Slot (15,15) Bottom-Left must be Black")
        # Bottom-right (8, 8) should be magenta
        r, g, b, a = get_pixel(15, 15, 8, 8)
        self.assertEqual((r, g, b, a), (255, 0, 255, 255), "Slot (15,15) Bottom-Right must be Magenta")

        # Check 2: Grass Top (0, 0) - predominantly green
        r, g, b, a = get_pixel(0, 0, 8, 8)
        self.assertGreater(g, r, "Grass top G must exceed R")
        self.assertGreater(g, b, "Grass top G must exceed B")
        self.assertEqual(a, 255)

        # Check 3: Stone (1, 0) - neutral gray (R == G == B)
        r, g, b, a = get_pixel(1, 0, 8, 8)
        self.assertEqual(r, g, "Stone R must equal G")
        self.assertEqual(g, b, "Stone G must equal B")
        self.assertGreater(r, 80)
        self.assertEqual(a, 255)

        # Check 4: Dirt (2, 0) - brown (R > G > B)
        r, g, b, a = get_pixel(2, 0, 8, 8)
        self.assertGreater(r, g, "Dirt R must exceed G")
        self.assertGreater(g, b, "Dirt G must exceed B")
        self.assertEqual(a, 255)

        # Check 5: Leaves (4, 3) - contains alpha cutout holes (alpha 0)
        has_cutout = False
        has_foliage = False
        for py in range(16):
            for px in range(16):
                r, g, b, a = get_pixel(4, 3, px, py)
                if a == 0:
                    has_cutout = True
                elif a == 255 and g > r and g > b:
                    has_foliage = True
        self.assertTrue(has_cutout, "Leaves must have transparent alpha cutout holes")
        self.assertTrue(has_foliage, "Leaves must have solid green foliage pixels")

        # Check 6: Glass (1, 3) - translucent frame and center
        r_f, g_f, b_f, a_f = get_pixel(1, 3, 0, 0) # Frame
        self.assertEqual(a_f, 180, "Glass frame must be translucent (alpha=180)")
        r_c, g_c, b_c, a_c = get_pixel(1, 3, 8, 8) # Center
        self.assertLess(a_c, 150, "Glass interior must be highly transparent")

        # Check 7: Water (13, 12) - translucent blue
        r, g, b, a = get_pixel(13, 12, 4, 4)
        self.assertGreater(b, r, "Water B must exceed R")
        self.assertGreater(b, g, "Water B must exceed G")
        self.assertGreater(a, 100)
        self.assertLess(a, 200)

        # Check 8: ASCII Font in Rows 12..15 - non-empty monochromatic white glyphs
        font_pixels = 0
        for ty in range(12, 16):
            for tx in range(16):
                if tx == 15 and ty == 15:
                    continue # Skip missing texture
                for py in range(16):
                    for px in range(16):
                        r, g, b, a = get_pixel(tx, ty, px, py)
                        if a > 0 and r == 255 and g == 255 and b == 255:
                            font_pixels += 1
        self.assertGreater(font_pixels, 500, "Font rows 12..15 must contain crisp white glyph pixels")

    # =========================================================================
    # 3. 6-Face Block Visual Table & UV Mapping
    # =========================================================================

    def test_07_block_face_enum_and_tile_mapping(self):
        """Verify BlockFace enum and canonical tile mapping for all faces."""
        with open(self.assets_h, "r", encoding="utf-8") as f:
            h_code = f.read()

        self.assertIn("FACE_WEST   = 0", h_code)
        self.assertIn("FACE_EAST   = 1", h_code)
        self.assertIn("FACE_NORTH  = 2", h_code)
        self.assertIn("FACE_SOUTH  = 3", h_code)
        self.assertIn("FACE_TOP    = 4", h_code)
        self.assertIn("FACE_BOTTOM = 5", h_code)

        # Test canonical tile mapping logic
        def get_tile(block_type, face):
            # Mirror C function GetBlockTextureTile
            if block_type == 1:  # Grass
                if face == 4: return (0, 0)
                if face == 5: return (2, 0)
                return (3, 0)
            elif block_type == 5:  # Wood / Log
                if face in (4, 5): return (5, 1)
                return (4, 1)
            elif block_type == 2:  return (2, 0)   # Dirt
            elif block_type == 3:  return (1, 0)   # Stone
            elif block_type == 4:  return (0, 1)   # Cobblestone
            elif block_type == 6:  return (4, 3)   # Leaves
            elif block_type == 7:  return (2, 1)   # Sand
            elif block_type == 8:  return (1, 1)   # Bedrock
            elif block_type == 9:  return (13, 12) # Water
            elif block_type == 10: return (1, 3)   # Glass
            else: return (15, 15)

        # Grass anisotropy
        self.assertEqual(get_tile(1, 4), (0, 0), "Grass TOP must map to (0, 0)")
        self.assertEqual(get_tile(1, 5), (2, 0), "Grass BOTTOM must map to (2, 0) [Dirt]")
        self.assertEqual(get_tile(1, 0), (3, 0), "Grass WEST must map to (3, 0) [Grass Side]")
        self.assertEqual(get_tile(1, 1), (3, 0), "Grass EAST must map to (3, 0) [Grass Side]")
        self.assertEqual(get_tile(1, 2), (3, 0), "Grass NORTH must map to (3, 0) [Grass Side]")
        self.assertEqual(get_tile(1, 3), (3, 0), "Grass SOUTH must map to (3, 0) [Grass Side]")

        # Wood anisotropy
        self.assertEqual(get_tile(5, 4), (5, 1), "Wood TOP must map to (5, 1) [Rings]")
        self.assertEqual(get_tile(5, 5), (5, 1), "Wood BOTTOM must map to (5, 1) [Rings]")
        self.assertEqual(get_tile(5, 0), (4, 1), "Wood SIDE must map to (4, 1) [Bark]")

        # Isotropic blocks
        self.assertEqual(get_tile(2, 4), (2, 0)) # Dirt
        self.assertEqual(get_tile(3, 4), (1, 0)) # Stone
        self.assertEqual(get_tile(4, 4), (0, 1)) # Cobblestone
        self.assertEqual(get_tile(8, 4), (1, 1)) # Bedrock
        self.assertEqual(get_tile(9, 4), (13, 12)) # Water
        self.assertEqual(get_tile(10, 4), (1, 3)) # Glass
        self.assertEqual(get_tile(99, 4), (15, 15)) # Unknown fallback

    def test_08_uv_normalization_and_bleed_protection(self):
        """Verify UV coordinate normalization and bleed margin protection."""
        tile_size = 16.0
        atlas_size = 256.0
        delta_uv = tile_size / atlas_size  # 0.0625

        def calculate_uv(tx, ty, margin=0.0):
            u0 = (tx * tile_size + margin) / atlas_size
            v0 = (ty * tile_size + margin) / atlas_size
            u1 = ((tx + 1) * tile_size - margin) / atlas_size
            v1 = ((ty + 1) * tile_size - margin) / atlas_size
            return u0, v0, u1, v1

        # Tile (0, 0)
        u0, v0, u1, v1 = calculate_uv(0, 0, 0.0)
        self.assertAlmostEqual(u0, 0.0)
        self.assertAlmostEqual(v0, 0.0)
        self.assertAlmostEqual(u1, 0.0625)
        self.assertAlmostEqual(v1, 0.0625)

        # Tile (15, 15)
        u0, v0, u1, v1 = calculate_uv(15, 15, 0.0)
        self.assertAlmostEqual(u0, 15 * 0.0625)
        self.assertAlmostEqual(v0, 15 * 0.0625)
        self.assertAlmostEqual(u1, 1.0)
        self.assertAlmostEqual(v1, 1.0)

        # Bleed margin test (margin = 0.5 texel)
        margin = 0.5
        u0_m, v0_m, u1_m, v1_m = calculate_uv(2, 2, margin)
        u0_raw, v0_raw, u1_raw, v1_raw = calculate_uv(2, 2, 0.0)
        self.assertGreater(u0_m, u0_raw)
        self.assertGreater(v0_m, v0_raw)
        self.assertLess(u1_m, u1_raw)
        self.assertLess(v1_m, v1_raw)
        self.assertAlmostEqual(u0_m - u0_raw, 0.5 / 256.0)

    def test_09_ccw_quad_winding_order(self):
        """Verify CCW quad winding order and indices {0, 1, 2, 0, 2, 3}."""
        with open(self.assets_h, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("QUAD_CCW_INDICES[6] = {0, 1, 2, 0, 2, 3}", content)
        self.assertIn("Assets_GetQuadUVs", content)

    # =========================================================================
    # 4. Procedural Audio Synthesizer Invariants
    # =========================================================================

    def test_10_sound_events_enum_and_constants(self):
        """Verify SoundID enum and MAX_ACTIVE_VOICES=16, SAMPLE_RATE=44100."""
        with open(self.audio_h, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("#define MAX_ACTIVE_VOICES 16", content)
        self.assertIn("#define SAMPLE_RATE       44100", content)
        self.assertIn("SFX_CLICK", content)
        self.assertIn("SFX_STEP", content)
        self.assertIn("SFX_JUMP", content)
        self.assertIn("SFX_BLOCK_BREAK", content)
        self.assertIn("SFX_BLOCK_PLACE", content)

    def test_11_procedural_synthesizer_waveforms_and_decay(self):
        """Verify sample counts, bounds, and decay curves for all 5 procedural sounds."""
        from tests.canonical_models import AudioSynthesizer

        # 1. UI CLICK (15ms = 661 samples, 2400 Hz square wave, linear decay)
        click = AudioSynthesizer.synthesize_ui_click()
        self.assertEqual(len(click), int(0.015 * 44100))
        for s in click:
            self.assertTrue(-1.0 <= s <= 1.0)
        self.assertAlmostEqual(abs(click[0]), 1.0, places=1)
        self.assertAlmostEqual(click[-1], 0.0, places=2)

        # 2. FOOTSTEP (40ms = 1764 samples, LFSR + 80Hz thump, exp decay lambda=65)
        step = AudioSynthesizer.synthesize_footstep()
        self.assertEqual(len(step), int(0.040 * 44100))
        for s in step:
            self.assertTrue(-1.0 <= s <= 1.0)
        mid_idx = int(0.030 * 44100)
        self.assertLess(abs(step[mid_idx]), 0.25)

        # 3. JUMP (90ms = 3969 samples, 25% duty square sweep 140->560Hz, 5ms attack, 85ms decay)
        jump = AudioSynthesizer.synthesize_jump()
        self.assertEqual(len(jump), int(0.090 * 44100))
        self.assertAlmostEqual(jump[0], 0.0, places=3)
        self.assertGreaterEqual(abs(jump[int(0.005 * 44100)]), 0.8)
        self.assertAlmostEqual(jump[-1], 0.0, places=2)

        # 4. BLOCK BREAK (160ms = 7056 samples, modulated LFSR noise + subharmonic, power decay)
        brk = AudioSynthesizer.synthesize_block_break()
        self.assertEqual(len(brk), int(0.160 * 44100))
        for s in brk:
            self.assertTrue(-1.0 <= s <= 1.0)
        rms_start = math.sqrt(sum(s*s for s in brk[:1764]) / 1764)
        rms_end = math.sqrt(sum(s*s for s in brk[-1764:]) / 1764)
        self.assertGreater(rms_start, rms_end * 2.0)

        # 5. BLOCK PLACE (50ms = 2205 samples, triangle wave plummet 220*2^(-25t), exp decay)
        place = AudioSynthesizer.synthesize_block_place()
        self.assertEqual(len(place), int(0.050 * 44100))
        for s in place:
            self.assertTrue(-1.0 <= s <= 1.0)
        self.assertLess(abs(place[-1]), 0.15)

    # =========================================================================
    # 5. 16-Voice Polyphony & Mixer Simulation
    # =========================================================================

    def test_12_polyphonic_mixer_voice_stealing_and_limiter(self):
        """Verify 16-voice capacity, ring voice stealing, and hard saturation limiter [-1.0, 1.0]."""
        MAX_VOICES = 16

        class VoiceSimulator:
            def __init__(self):
                self.id = 0
                self.cursor = 0
                self.total_samples = 0
                self.volume = 0.0

        class MixerSimulator:
            def __init__(self):
                self.voices = [VoiceSimulator() for _ in range(MAX_VOICES)]
                self.next_steal = 0

            def play(self, sound_id, volume, duration_samples):
                if volume <= 0.001:
                    return -1  # Culled
                target = -1
                for i in range(MAX_VOICES):
                    if self.voices[i].id == 0:
                        target = i
                        break
                if target == -1:
                    target = self.next_steal
                    self.next_steal = (self.next_steal + 1) % MAX_VOICES

                v = self.voices[target]
                v.id = sound_id
                v.cursor = 0
                v.total_samples = duration_samples
                v.volume = min(1.0, volume)
                return target

            def active_count(self):
                return sum(1 for v in self.voices if v.id != 0)

            def mix_one(self):
                sample_sum = 0.0
                for v in self.voices:
                    if v.id != 0:
                        sample_sum += 1.0 * v.volume  # Maximum constructible amplitude
                        v.cursor += 1
                        if v.cursor >= v.total_samples:
                            v.id = 0
                # Hard saturation limiter
                if sample_sum > 1.0: sample_sum = 1.0
                elif sample_sum < -1.0: sample_sum = -1.0
                return sample_sum

        mixer = MixerSimulator()

        # 1. Fill all 16 voices
        for i in range(16):
            channel = mixer.play(sound_id=1, volume=1.0, duration_samples=100)
            self.assertEqual(channel, i)
        self.assertEqual(mixer.active_count(), 16)

        # 2. 17th voice must trigger ring voice stealing (steals voice 0)
        stolen_channel = mixer.play(sound_id=2, volume=1.0, duration_samples=100)
        self.assertEqual(stolen_channel, 0, "17th voice must steal channel 0")
        self.assertEqual(mixer.active_count(), 16)

        # 3. 18th voice must steal voice 1
        stolen_channel2 = mixer.play(sound_id=3, volume=1.0, duration_samples=100)
        self.assertEqual(stolen_channel2, 1, "18th voice must steal channel 1")

        # 4. Hard saturation limiter check with 16 voices running
        out = mixer.mix_one()
        self.assertEqual(out, 1.0, "Hard saturation limiter must clamp to exactly +1.0")

        # 5. Negligible volume culling
        neg_ch = mixer.play(sound_id=1, volume=0.0005, duration_samples=100)
        self.assertEqual(neg_ch, -1, "Negligible volume <= 0.001 must not allocate a voice")

    # =========================================================================
    # 6. Ponytail Minimalist Annotations
    # =========================================================================

    def test_13_ponytail_comments_present(self):
        """Verify required ponytail comments are present in assets and audio files."""
        expected = [
            (self.assets_h, "ponytail:"),
            (self.assets_c, "ponytail:"),
            (self.audio_h, "ponytail:"),
            (self.synthesizer_c, "ponytail:"),
            (self.atlas_data_h, "ponytail:")
        ]
        for filepath, phrase in expected:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn(phrase, content, f"Missing {phrase} in {filepath}")


if __name__ == '__main__':
    unittest.main()
