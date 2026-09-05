"""
Tier 2: Bedrock Indestructibility & Hardness Boundary Tests.
Verifies bedrock resistance (H <= 0 / -1.0), instant-break blocks (H = 0.0),
crack visual stage mapping [0..9], and destruction progress cancellation.
"""

import unittest
import math


class BlockBreakingFSM:
    def __init__(self):
        self.target_block = None
        self.progress = 0.0
        self.is_holding_button = False

    def start_or_continue_break(self, block_pos: tuple[int, int, int],
                                hardness: float, tool_multiplier: float,
                                dt: float, player_distance: float) -> bool:
        """
        Advances block breaking FSM.
        Returns True if block has shattered/broken.
        """
        if player_distance > 5.0:
            self.reset()
            return False

        if hardness < 0.0:  # Bedrock / Indestructible
            return False

        if hardness == 0.0:  # Instant break (Air, Tallgrass)
            self.reset()
            return True

        # Check target change
        if self.target_block != block_pos:
            self.target_block = block_pos
            self.progress = 0.0

        # Increment progress
        delta_p = (dt * tool_multiplier) / hardness
        self.progress += delta_p

        if self.progress >= 1.0:
            self.reset()
            return True

        return False

    def get_crack_stage(self) -> int:
        return min(9, max(0, math.floor(self.progress * 10.0)))

    def reset(self):
        self.target_block = None
        self.progress = 0.0
        self.is_holding_button = False


class TestBedrockIndestructibility(unittest.TestCase):

    def setUp(self):
        self.fsm = BlockBreakingFSM()

    def test_01_bedrock_indestructible_under_extreme_tools(self):
        """Verify bedrock (H = -1.0) never breaks even with maximum tool multiplier over thousands of ticks."""
        bedrock_pos = (0, 0, 0)
        dt = 1.0 / 60.0
        tool_multiplier = 100.0  # Diamond/Efficiency extreme tool

        for _ in range(5000):
            broken = self.fsm.start_or_continue_break(
                bedrock_pos, hardness=-1.0, tool_multiplier=tool_multiplier,
                dt=dt, player_distance=2.0
            )
            self.assertFalse(broken)
            self.assertEqual(self.fsm.progress, 0.0)
            self.assertEqual(self.fsm.get_crack_stage(), 0)

    def test_02_instant_break_zero_hardness(self):
        """Verify blocks with H = 0.0 (tall grass, flowers) shatter on the very first tick."""
        flower_pos = (5, 64, 5)
        broken = self.fsm.start_or_continue_break(
            flower_pos, hardness=0.0, tool_multiplier=1.0,
            dt=1.0/60.0, player_distance=2.0
        )
        self.assertTrue(broken, "Zero hardness blocks should break immediately on tick 1!")

    def test_03_crack_stages_clamp_to_zero_through_nine(self):
        """Verify crack stages progress monotonically through 0..9 and never exceed 9."""
        wood_pos = (1, 64, 1)
        # Wood hardness = 2.0s, bare hands multiplier = 1.0
        # At progress 0.05 -> stage 0
        self.fsm.progress = 0.05
        self.assertEqual(self.fsm.get_crack_stage(), 0)

        # At progress 0.55 -> stage 5
        self.fsm.progress = 0.55
        self.assertEqual(self.fsm.get_crack_stage(), 5)

        # At progress 0.99 -> stage 9
        self.fsm.progress = 0.99
        self.assertEqual(self.fsm.get_crack_stage(), 9)

        # Near 1.0 -> must clamp to 9, not 10
        self.fsm.progress = 1.0
        self.assertEqual(self.fsm.get_crack_stage(), 9)

    def test_04_retargeting_adjacent_block_resets_progress(self):
        """Verify shifting crosshair from block A to block B resets break progress to 0."""
        block_a = (2, 64, 2)
        block_b = (3, 64, 2)
        dt = 1.0 / 60.0

        # Mine block A for 30 ticks (partial progress)
        for _ in range(30):
            self.fsm.start_or_continue_break(block_a, hardness=2.0, tool_multiplier=1.0, dt=dt, player_distance=2.0)

        self.assertGreater(self.fsm.progress, 0.2)
        initial_progress = self.fsm.progress

        # Now mine block B
        self.fsm.start_or_continue_break(block_b, hardness=2.0, tool_multiplier=1.0, dt=dt, player_distance=2.0)

        # Target block switched to B, progress reset to fresh single-tick increment
        self.assertEqual(self.fsm.target_block, block_b)
        self.assertLess(self.fsm.progress, initial_progress)

    def test_05_player_moving_out_of_reach_resets_progress(self):
        """Verify player backing away beyond 5.0m maximum reach aborts breaking and resets progress."""
        block_pos = (2, 64, 2)
        dt = 1.0 / 60.0

        # Mine for 30 ticks within 3.0m
        for _ in range(30):
            self.fsm.start_or_continue_break(block_pos, hardness=2.0, tool_multiplier=1.0, dt=dt, player_distance=3.0)
        self.assertGreater(self.fsm.progress, 0.2)

        # Player steps back to 5.5m (> 5.0m reach)
        broken = self.fsm.start_or_continue_break(block_pos, hardness=2.0, tool_multiplier=1.0, dt=dt, player_distance=5.5)
        self.assertFalse(broken)
        self.assertEqual(self.fsm.progress, 0.0)
        self.assertIsNone(self.fsm.target_block)


if __name__ == '__main__':
    unittest.main()
