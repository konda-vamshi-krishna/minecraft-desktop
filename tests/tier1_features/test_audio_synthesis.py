"""
Tier 1: Procedural Audio Synthesizer Formula Verification.
Verifies sample rates, durations, waveform limits, and mathematical decay
for UI Click, Footstep, Jump, Block Break, and Block Place procedural sound FX.
"""

import unittest
import math
from tests.canonical_models import AudioSynthesizer


class TestAudioSynthesis(unittest.TestCase):

    def test_01_ui_click_duration_and_waveform(self):
        """Verify UI Click: 15ms duration (661 samples at 44.1kHz), square wave bounds [-1.0, 1.0], linear decay."""
        samples = AudioSynthesizer.synthesize_ui_click()
        expected_sample_count = int(0.015 * 44100)  # 661 samples
        self.assertEqual(len(samples), expected_sample_count)

        # Bounds check
        for s in samples:
            self.assertGreaterEqual(s, -1.0)
            self.assertLessEqual(s, 1.0)

        # Linear decay: first sample amplitude should be near 1.0, final sample near 0.0
        self.assertAlmostEqual(abs(samples[0]), 1.0, places=1)
        self.assertAlmostEqual(samples[-1], 0.0, places=2)

    def test_02_footstep_noise_and_exponential_thump(self):
        """Verify Footstep: 40ms duration (1764 samples), combined noise and 80Hz thump with rapid exponential decay."""
        samples = AudioSynthesizer.synthesize_footstep()
        expected_sample_count = int(0.040 * 44100)  # 1764 samples
        self.assertEqual(len(samples), expected_sample_count)

        for s in samples:
            self.assertGreaterEqual(s, -1.0)
            self.assertLessEqual(s, 1.0)

        # Exponential decay: tail samples after 30ms should be dampened by factor e^(-65 * 0.03) ~= 0.14
        mid_idx = int(0.030 * 44100)
        self.assertLess(abs(samples[mid_idx]), 0.25)

    def test_03_jump_frequency_sweep_and_adsr_envelope(self):
        """Verify Jump: 90ms duration (3969 samples), 25% duty square wave, linear attack (5ms) and decay (85ms)."""
        samples = AudioSynthesizer.synthesize_jump()
        expected_sample_count = int(0.090 * 44100)  # 3969 samples
        self.assertEqual(len(samples), expected_sample_count)

        # Attack at t=0 starts at 0.0
        self.assertAlmostEqual(samples[0], 0.0, places=3)

        # Peak amplitude reached around 5ms (sample ~220)
        attack_peak_sample = samples[int(0.005 * 44100)]
        self.assertGreaterEqual(abs(attack_peak_sample), 0.8)

        # End of sweep approaches 0.0
        self.assertAlmostEqual(samples[-1], 0.0, places=2)

    def test_04_block_break_crunch_shatter_envelope(self):
        """Verify Block Break: 160ms duration (7056 samples), LFSR noise + subharmonic decay."""
        samples = AudioSynthesizer.synthesize_block_break()
        expected_sample_count = int(0.160 * 44100)  # 7056 samples
        self.assertEqual(len(samples), expected_sample_count)

        for s in samples:
            self.assertGreaterEqual(s, -1.0)
            self.assertLessEqual(s, 1.0)

        # Power dissipation check: RMS of first 40ms > RMS of last 40ms
        rms_start = math.sqrt(sum(s*s for s in samples[:1764]) / 1764)
        rms_end = math.sqrt(sum(s*s for s in samples[-1764:]) / 1764)
        self.assertGreater(rms_start, rms_end * 2.0)

    def test_05_block_place_pitch_plummet_thud(self):
        """Verify Block Place: 50ms duration (2205 samples), triangle wave with pitch plummet 220*2^(-25t)."""
        samples = AudioSynthesizer.synthesize_block_place()
        expected_sample_count = int(0.050 * 44100)  # 2205 samples
        self.assertEqual(len(samples), expected_sample_count)

        for s in samples:
            self.assertGreaterEqual(s, -1.0)
            self.assertLessEqual(s, 1.0)

        # Exponential decay factor e^(-50 * 0.045) ~= 0.105
        tail_sample = abs(samples[-1])
        self.assertLess(tail_sample, 0.15)


if __name__ == '__main__':
    unittest.main()
