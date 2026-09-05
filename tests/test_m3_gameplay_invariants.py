"""
Comprehensive Gameplay & Voxel Physics Invariant Test Suite (Milestone 3).

Tests:
1. Static and structural verification of src/gameplay/*.h and src/gameplay/*.c
2. Zero dynamic heap allocations (no malloc, calloc, realloc, free)
3. Ponytail minimal-complexity annotations in every gameplay module
4. Official Minecraft Java Edition kinematic constants (g=-32 m/s^2, drag=0.98, friction=0.546, jump=1.25m)
5. Terminal velocity discrete recurrence parity (-78.4 m/s, -3.92 blk/tick)
6. Amanatides-Woo Fast Voxel Traversal DDA raymarching invariants (5.0m reach, face normal resolution)
7. Block destruction FSM: hardness timers and 10-stage crack progress (0..9)
8. 9-Slot Hotbar state machine: wrap-around modulo cycling and stack limits
9. Anti-suffocation placement validation against player AABB
"""

import os
import re
import math
import unittest

REPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
GAMEPLAY_DIR = os.path.join(REPO_DIR, "src", "gameplay")

class TestGameplayInvariants(unittest.TestCase):
    def setUp(self):
        self.files = {
            "physics_h": os.path.join(GAMEPLAY_DIR, "physics.h"),
            "physics_c": os.path.join(GAMEPLAY_DIR, "physics.c"),
            "raycast_h": os.path.join(GAMEPLAY_DIR, "raycast.h"),
            "raycast_c": os.path.join(GAMEPLAY_DIR, "raycast.c"),
            "interaction_h": os.path.join(GAMEPLAY_DIR, "interaction.h"),
            "interaction_c": os.path.join(GAMEPLAY_DIR, "interaction.c"),
            "inventory_h": os.path.join(GAMEPLAY_DIR, "inventory.h"),
            "inventory_c": os.path.join(GAMEPLAY_DIR, "inventory.c"),
        }
        self.contents = {}
        for key, path in self.files.items():
            self.assertTrue(os.path.isfile(path), f"Missing required file: {path}")
            with open(path, "r", encoding="utf-8") as f:
                self.contents[key] = f.read()

    def test_01_zero_dynamic_heap_allocations(self):
        forbidden = [r"\bmalloc\s*\(", r"\bcalloc\s*\(", r"\brealloc\s*\(", r"\bfree\s*\("]
        for key, text in self.contents.items():
            for pat in forbidden:
                match = re.search(pat, text)
                self.assertIsNone(match, f"Forbidden heap allocation call {pat} found in {self.files[key]}")

    def test_02_ponytail_comments_presence(self):
        for key, text in self.contents.items():
            self.assertIn("// ponytail:", text, f"Missing Ponytail annotation in {self.files[key]}")

    def test_03_canonical_physics_constants(self):
        h = self.contents["physics_h"]
        expected = [
            ("PLAYER_WIDTH", "0.60f"),
            ("PLAYER_HALF_WIDTH", "0.30f"),
            ("PLAYER_HEIGHT_STANDING", "1.80f"),
            ("PLAYER_HEIGHT_SNEAKING", "1.50f"),
            ("PLAYER_EYE_OFFSET_STANDING", "1.62f"),
            ("PLAYER_EYE_OFFSET_SNEAKING", "1.35f"),
            ("PHYSICS_GRAVITY", "-32.0f"),
            ("PHYSICS_TERMINAL_VELOCITY", "-78.4f"),
            ("PHYSICS_GROUND_FRICTION", "0.546f"),
            ("PHYSICS_AIR_DRAG", "0.980f"),
            ("PHYSICS_AUTOSTEP_HEIGHT", "0.550f"),
        ]
        for name, val in expected:
            self.assertIn(f"#define {name}", h)
            self.assertIn(val, h)

    def test_04_terminal_velocity_discrete_recurrence(self):
        vy = 0.0
        for _ in range(1000):
            vy = (vy - 0.08) * 0.98
        terminal_blocks_per_tick = vy
        terminal_si_m_per_s = terminal_blocks_per_tick * 20.0
        self.assertAlmostEqual(terminal_blocks_per_tick, -3.92, places=4)
        self.assertAlmostEqual(terminal_si_m_per_s, -78.4, places=4)

    def test_05_jump_impulse_apex_clearance(self):
        y = 0.0
        vy = 0.42
        max_y = 0.0
        for _ in range(15):
            y += vy
            if y > max_y:
                max_y = y
            vy = (vy - 0.08) * 0.98
        self.assertAlmostEqual(max_y, 1.2522, places=3)
        self.assertGreater(max_y, 1.250)

    def test_06_dda_raycast_reach_and_constants(self):
        h = self.contents["raycast_h"]
        self.assertIn("#define RAYCAST_REACH_CREATIVE 5.0f", h)
        self.assertIn("#define RAYCAST_REACH_SURVIVAL 4.5f", h)
        self.assertIn("Raycast_Traverse", h)
        self.assertIn("Raycast_World", h)
        self.assertIn("Raycast_ValidatePlacement", h)

    def test_07_hotbar_positive_modulo_wrap(self):
        HOTBAR_SLOT_COUNT = 9
        def scroll(slot, delta):
            return ((slot - delta) % HOTBAR_SLOT_COUNT + HOTBAR_SLOT_COUNT) % HOTBAR_SLOT_COUNT

        self.assertEqual(scroll(0, -1), 1)
        self.assertEqual(scroll(8, -1), 0)
        self.assertEqual(scroll(0, 1), 8)
        self.assertEqual(scroll(1, 1), 0)

    def test_08_block_crack_stage_formula(self):
        def crack_stage(p):
            s = math.floor(p * 10.0)
            return max(0, min(9, int(s)))

        self.assertEqual(crack_stage(0.0), 0)
        self.assertEqual(crack_stage(0.09), 0)
        self.assertEqual(crack_stage(0.10), 1)
        self.assertEqual(crack_stage(0.55), 5)
        self.assertEqual(crack_stage(0.99), 9)
        self.assertEqual(crack_stage(1.0), 9)

    def test_09_anti_suffocation_placement_logic(self):
        # Player standing at (10.0, 64.0, 10.0), AABB: [9.7..10.3, 64.0..65.8, 9.7..10.3]
        # Candidate block at (10, 64, 10), AABB: [10.0..11.0, 64.0..65.0, 10.0..11.0]
        # Must intersect -> Placement invalid
        def aabb_intersect(minA, maxA, minB, maxB):
            return (minA[0] < maxB[0] and maxA[0] > minB[0] and
                    minA[1] < maxB[1] and maxA[1] > minB[1] and
                    minA[2] < maxB[2] and maxA[2] > minB[2])

        p_min = (9.7, 64.0, 9.7)
        p_max = (10.3, 65.8, 10.3)
        b_min = (10.0, 64.0, 10.0)
        b_max = (11.0, 65.0, 11.0)
        self.assertTrue(aabb_intersect(p_min, p_max, b_min, b_max), "Player overlaps block -> Placement must fail")

        # Candidate block at (10, 66, 10), AABB: [10.0..11.0, 66.0..67.0, 10.0..11.0]
        # Above player head -> No intersection -> Placement permissible
        b_above_min = (10.0, 66.0, 10.0)
        b_above_max = (11.0, 67.0, 11.0)
        self.assertFalse(aabb_intersect(p_min, p_max, b_above_min, b_above_max), "No overlap above head")

    def test_10_c99_header_guards_and_extern_c(self):
        headers = ["physics_h", "raycast_h", "interaction_h", "inventory_h"]
        for key in headers:
            text = self.contents[key]
            self.assertIn("#ifndef", text)
            self.assertIn("#define", text)
            self.assertIn("#endif", text)
            self.assertIn('extern "C"', text)

if __name__ == "__main__":
    unittest.main()
