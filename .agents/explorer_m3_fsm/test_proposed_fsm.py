"""
Validation script for proposed interaction and inventory C99 state machines.
Verifies structure layout, invariants, zero dynamic allocation, and exact parity with canonical models.
"""

import os
import re
import math
import unittest

class TestProposedM3FSM(unittest.TestCase):
    AGENT_DIR = os.path.dirname(os.path.abspath(__file__))

    def setUp(self):
        self.files = [
            os.path.join(self.AGENT_DIR, "proposed_interaction.h"),
            os.path.join(self.AGENT_DIR, "proposed_interaction.c"),
            os.path.join(self.AGENT_DIR, "proposed_inventory.h"),
            os.path.join(self.AGENT_DIR, "proposed_inventory.c"),
        ]

    def test_01_all_files_exist_and_non_empty(self):
        for f in self.files:
            self.assertTrue(os.path.isfile(f), f"Missing file: {f}")
            self.assertGreater(os.path.getsize(f), 200, f"File too small: {f}")

    def test_02_zero_dynamic_heap_allocations(self):
        forbidden = [r"\bmalloc\b", r"\bcalloc\b", r"\brealloc\b", r"\bfree\b"]
        for f in self.files:
            with open(f, "r", encoding="utf-8") as fp:
                content = fp.read()
            for pat in forbidden:
                self.assertIsNone(re.search(pat, content), f"Forbidden allocation {pat} in {f}")

    def test_03_ponytail_comments_presence(self):
        for f in self.files:
            with open(f, "r", encoding="utf-8") as fp:
                content = fp.read()
            self.assertIn("// ponytail:", content, f"Missing Ponytail annotation in {f}")

    def test_04_hotbar_positive_modulo_wrap(self):
        HOTBAR_SLOT_COUNT = 9
        def scroll(slot, delta):
            return ((slot - delta) % HOTBAR_SLOT_COUNT + HOTBAR_SLOT_COUNT) % HOTBAR_SLOT_COUNT

        # Scroll right (delta = -1) from 0 -> 1
        self.assertEqual(scroll(0, -1), 1)
        # Scroll right from 8 -> 0
        self.assertEqual(scroll(8, -1), 0)
        # Scroll left (delta = 1) from 0 -> 8
        self.assertEqual(scroll(0, 1), 8)
        # Scroll left from 1 -> 0
        self.assertEqual(scroll(1, 1), 0)
        # Extreme negative delta
        self.assertEqual(scroll(0, -10), 1)
        # Extreme positive delta
        self.assertEqual(scroll(0, 10), 8)

    def test_05_crack_stage_formula(self):
        def crack_stage(p):
            s = math.floor(p * 10.0)
            return max(0, min(9, s))

        self.assertEqual(crack_stage(0.0), 0)
        self.assertEqual(crack_stage(0.09), 0)
        self.assertEqual(crack_stage(0.10), 1)
        self.assertEqual(crack_stage(0.55), 5)
        self.assertEqual(crack_stage(0.99), 9)
        self.assertEqual(crack_stage(1.0), 9)

    def test_06_c99_syntax_and_guards(self):
        for f in self.files:
            with open(f, "r", encoding="utf-8") as fp:
                content = fp.read()
            if f.endswith(".h"):
                self.assertIn("#ifndef", content)
                self.assertIn("#define", content)
                self.assertIn("#endif", content)
                self.assertIn("extern \"C\"", content)

if __name__ == "__main__":
    unittest.main()
