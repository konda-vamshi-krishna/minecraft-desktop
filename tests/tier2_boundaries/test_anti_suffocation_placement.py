"""
Tier 2: Block Placement Anti-Suffocation Validation Tests.
Verifies rejection of block placement intersecting player AABB (standing & sneaking),
vertical world boundary enforcement (Y in [0, 255]), and occupancy checks.
"""

import unittest
from tests.canonical_models import Kinematics, AABB


def try_place_block_validation(
    place_x: int, place_y: int, place_z: int,
    player_x: float, player_y: float, player_z: float,
    is_sneaking: bool,
    is_cell_empty: bool
) -> bool:
    """
    Placement validation invariant from docs/02 §5.3.
    """
    # 1. World height boundary check
    if place_y < 0 or place_y >= 256:
        return False

    # 2. Cell must be empty (air)
    if not is_cell_empty:
        return False

    # 3. Block AABB vs Player AABB self-intersection check
    block_box = AABB(place_x, place_y, place_z,
                     place_x + 1.0, place_y + 1.0, place_z + 1.0)
    player_box = Kinematics.get_player_aabb(player_x, player_y, player_z, is_sneaking)

    if block_box.intersects(player_box):
        return False  # REJECT: suffocation risk

    return True


class TestAntiSuffocationPlacement(unittest.TestCase):

    def test_01_placement_at_player_feet_rejected(self):
        """Verify placing a block directly inside player's lower body is rejected."""
        # Player at (5.0, 64.0, 5.0). Proposed block at (5, 64, 5).
        accepted = try_place_block_validation(
            place_x=5, place_y=64, place_z=5,
            player_x=5.0, player_y=64.0, player_z=5.0,
            is_sneaking=False, is_cell_empty=True
        )
        self.assertFalse(accepted, "Placement inside player feet should be rejected!")

    def test_02_placement_at_player_head_rejected(self):
        """Verify placing a block at player eye level (y=65) is rejected while standing."""
        accepted = try_place_block_validation(
            place_x=5, place_y=65, place_z=5,
            player_x=5.0, player_y=64.0, player_z=5.0,
            is_sneaking=False, is_cell_empty=True
        )
        self.assertFalse(accepted, "Placement inside player head should be rejected!")

    def test_03_placement_above_sneaking_player_accepted(self):
        """Verify placing block at y=66 above a sneaking player (height 1.5m -> top at 65.5m) is accepted."""
        # Sneaking player at y=64.0 has top at 65.5. Block at y=66 occupies [66.0, 67.0].
        accepted = try_place_block_validation(
            place_x=5, place_y=66, place_z=5,
            player_x=5.0, player_y=64.0, player_z=5.0,
            is_sneaking=True, is_cell_empty=True
        )
        self.assertTrue(accepted, "Placement above sneaking player headroom should be accepted!")

    def test_04_adjacent_placement_without_overlap_accepted(self):
        """Verify placing block immediately adjacent to player's bounding box is accepted."""
        # Player at (5.0, 64.0, 5.0), max_x = 5.3. Block at x=6 occupies [6.0, 7.0].
        accepted = try_place_block_validation(
            place_x=6, place_y=64, place_z=5,
            player_x=5.0, player_y=64.0, player_z=5.0,
            is_sneaking=False, is_cell_empty=True
        )
        self.assertTrue(accepted, "Placement adjacent to player should be accepted!")

    def test_05_world_height_boundaries(self):
        """Verify placement at y < 0 or y >= 256 is strictly rejected."""
        # Below world minimum
        self.assertFalse(try_place_block_validation(5, -1, 5, 5.0, 64.0, 5.0, False, True))
        # At world height ceiling y=256
        self.assertFalse(try_place_block_validation(5, 256, 5, 5.0, 64.0, 5.0, False, True))
        # Valid ceiling edge y=255
        self.assertTrue(try_place_block_validation(5, 255, 5, 5.0, 64.0, 5.0, False, True))

    def test_06_occupied_cell_rejection(self):
        """Verify placing into an already occupied block (not air) is rejected."""
        self.assertFalse(try_place_block_validation(6, 64, 5, 5.0, 64.0, 5.0, False, is_cell_empty=False))


if __name__ == '__main__':
    unittest.main()
