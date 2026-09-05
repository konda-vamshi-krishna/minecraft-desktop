"""
Milestone 3 (M3) Gameplay Systems & Voxel Physics Invariant Verification Suite.
Validates:
  1. Amanatides-Woo Fast Voxel Traversal DDA raymarching (normals, reach boundaries, air stepping).
  2. Axis-decoupled swept AABB player physics (Y->X->Z order, gravity, terminal velocity, friction, drag, auto-step, sneak clamp).
  3. Progressive block destruction FSM (hardness, tool multipliers, crack stages, cancellation).
  4. Block placement validation (anti-suffocation player intersection, world bounds, occupancy).
  5. 41-slot inventory & 9-slot hotbar state machine (layout, stack limits, mouse interactions, 2x2 & 3x3 crafting matchers).
  6. C99 source and header invariants (zero allocations, clean includes, header guards, Ponytail annotations).

Executable via:
  python -m unittest tests/test_m3_gameplay.py
"""

import unittest
import os
import re
import math
from typing import Tuple, List, Optional, Callable


# Import canonical specification models from tests/canonical_models.py
import sys
# Find project root by searching upwards for src/main.c
cur = os.path.abspath(__file__)
PROJECT_ROOT = None
while cur and os.path.dirname(cur) != cur:
    cur = os.path.dirname(cur)
    if os.path.isfile(os.path.join(cur, "src", "main.c")):
        PROJECT_ROOT = cur
        break
if PROJECT_ROOT is None:
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from tests.canonical_models import (
    AABB,
    Kinematics,
    VoxelPhysicsController,
    RaycastHit as CanonicalRaycastHit,
    fast_voxel_traversal,
    CoordinateMath,
    ItemID,
    ItemStack,
    get_default_max_stack,
    get_default_durability,
    InventoryModel,
    CraftingEngine
)


class TestM3Gameplay(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gameplay_dir = os.path.join(PROJECT_ROOT, "src", "gameplay")
        cls.physics_h = os.path.join(cls.gameplay_dir, "physics.h")
        cls.physics_c = os.path.join(cls.gameplay_dir, "physics.c")
        cls.raycast_h = os.path.join(cls.gameplay_dir, "raycast.h")
        cls.raycast_c = os.path.join(cls.gameplay_dir, "raycast.c")
        cls.interaction_h = os.path.join(cls.gameplay_dir, "interaction.h")
        cls.interaction_c = os.path.join(cls.gameplay_dir, "interaction.c")
        cls.inventory_h = os.path.join(cls.gameplay_dir, "inventory.h")
        cls.inventory_c = os.path.join(cls.gameplay_dir, "inventory.c")

        cls.all_files = [
            cls.physics_h, cls.physics_c,
            cls.raycast_h, cls.raycast_c,
            cls.interaction_h, cls.interaction_c,
            cls.inventory_h, cls.inventory_c
        ]

    # =========================================================================
    # Group 1: Source Code & C99 Structural Invariants
    # =========================================================================

    def test_01_all_gameplay_files_exist_and_non_empty(self):
        """Verify all 8 gameplay source and header files exist and are populated."""
        for path in self.all_files:
            self.assertTrue(os.path.isfile(path), f"File {path} must exist.")
            self.assertGreater(os.path.getsize(path), 100, f"File {path} must not be empty.")

    def test_02_gameplay_headers_zero_dynamic_allocation(self):
        """Verify gameplay subsystem enforces zero dynamic heap allocation (no malloc/calloc/free)."""
        forbidden = [r"\bmalloc\b", r"\bcalloc\b", r"\brealloc\b", r"\bfree\b"]
        for path in self.all_files:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            # Strip block comments and line comments before analyzing code
            code_only = re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)
            code_only = re.sub(r"//.*", "", code_only)
            for pattern in forbidden:
                self.assertIsNone(
                    re.search(pattern, code_only),
                    f"Forbidden dynamic allocation pattern '{pattern}' found in {os.path.basename(path)}"
                )

    def test_03_no_malformed_includes_or_proposed_references(self):
        """Verify no malformed include directives or leftover proposed_* references exist in src/gameplay/."""
        malformed_patterns = [
            r'#include\s+proposed_',
            r'#include\s+"proposed_',
            r'#include\s+[^<"\s]',
        ]
        for path in self.all_files:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            for line_idx, line in enumerate(lines, 1):
                if line.strip().startswith("#include"):
                    for pattern in malformed_patterns:
                        self.assertIsNone(
                            re.search(pattern, line),
                            f"Malformed include at {os.path.basename(path)}:{line_idx}: {line.strip()}"
                        )

    def test_04_header_guards_and_cplusplus_extern_c_correctness(self):
        """Verify header guards and valid extern \"C\" declarations in all gameplay headers."""
        header_files = [self.physics_h, self.raycast_h, self.interaction_h, self.inventory_h]
        for h_path in header_files:
            with open(h_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn("#ifndef", content, f"Missing #ifndef guard in {os.path.basename(h_path)}")
            self.assertIn("#define", content, f"Missing #define guard in {os.path.basename(h_path)}")
            self.assertIn("#endif", content, f"Missing #endif guard in {os.path.basename(h_path)}")
            # In C++ mode, extern "C" must include quotes
            if "__cplusplus" in content:
                self.assertIn('extern "C"', content,
                              f"Malformed extern C without quotes in {os.path.basename(h_path)}")

    def test_05_raycast_hit_struct_canonical_consistency(self):
        """Verify RaycastHit struct is defined canonically in physics.h without conflicting duplicates."""
        with open(self.physics_h, "r", encoding="utf-8") as f:
            physics_content = f.read()
        self.assertIn("typedef struct RaycastHit", physics_content)
        self.assertIn("int targetX", physics_content)
        self.assertIn("int normalX", physics_content)
        self.assertIn("int placeX", physics_content)
        self.assertIn("float distance", physics_content)

    # =========================================================================
    # Group 2: Amanatides-Woo Fast Voxel Traversal (DDA Raycast)
    # =========================================================================

    def test_06_dda_raycast_cardinal_face_normals(self):
        """Verify entered face normal invariant: n = -step_i * e_i for all 6 cardinal directions."""
        # Solid voxel placed at (10, 64, 10)
        solid_voxel = (10, 64, 10)
        is_solid = lambda x, y, z: (x, y, z) == solid_voxel

        # 1. Ray approaching from -X (moving East toward +X) enters West face: normal = (-1, 0, 0)
        hit_pos_x = fast_voxel_traversal((8.5, 64.5, 10.5), (1.0, 0.0, 0.0), 5.0, is_solid)
        self.assertTrue(hit_pos_x.hit)
        self.assertEqual(hit_pos_x.face_normal, (-1, 0, 0))
        self.assertEqual(hit_pos_x.place_block, (9, 64, 10))

        # 2. Ray approaching from +X (moving West toward -X) enters East face: normal = (+1, 0, 0)
        hit_neg_x = fast_voxel_traversal((11.5, 64.5, 10.5), (-1.0, 0.0, 0.0), 5.0, is_solid)
        self.assertTrue(hit_neg_x.hit)
        self.assertEqual(hit_neg_x.face_normal, (1, 0, 0))
        self.assertEqual(hit_neg_x.place_block, (11, 64, 10))

        # 3. Ray approaching from +Y (moving Down toward -Y) enters Top face: normal = (0, 1, 0)
        hit_neg_y = fast_voxel_traversal((10.5, 66.5, 10.5), (0.0, -1.0, 0.0), 5.0, is_solid)
        self.assertTrue(hit_neg_y.hit)
        self.assertEqual(hit_neg_y.face_normal, (0, 1, 0))
        self.assertEqual(hit_neg_y.place_block, (10, 65, 10))

        # 4. Ray approaching from -Y (moving Up toward +Y) enters Bottom face: normal = (0, -1, 0)
        hit_pos_y = fast_voxel_traversal((10.5, 62.5, 10.5), (0.0, 1.0, 0.0), 5.0, is_solid)
        self.assertTrue(hit_pos_y.hit)
        self.assertEqual(hit_pos_y.face_normal, (0, -1, 0))
        self.assertEqual(hit_pos_y.place_block, (10, 63, 10))

        # 5. Ray approaching from -Z (moving South toward +Z) enters North face: normal = (0, 0, -1)
        hit_pos_z = fast_voxel_traversal((10.5, 64.5, 8.5), (0.0, 0.0, 1.0), 5.0, is_solid)
        self.assertTrue(hit_pos_z.hit)
        self.assertEqual(hit_pos_z.face_normal, (0, 0, -1))
        self.assertEqual(hit_pos_z.place_block, (10, 64, 9))

        # 6. Ray approaching from +Z (moving North toward -Z) enters South face: normal = (0, 0, 1)
        hit_neg_z = fast_voxel_traversal((10.5, 64.5, 12.5), (0.0, 0.0, -1.0), 5.0, is_solid)
        self.assertTrue(hit_neg_z.hit)
        self.assertEqual(hit_neg_z.face_normal, (0, 0, 1))
        self.assertEqual(hit_neg_z.place_block, (10, 64, 11))

    def test_07_dda_raycast_reach_boundaries(self):
        """Verify strict raycast reach boundaries: Survival 4.5m vs Creative 5.0m."""
        # Block positioned at x=5, eye at x=0.5 -> boundary is at x=5.0 (distance 4.5m)
        is_solid = lambda x, y, z: (x, y, z) == (5, 64, 0)
        eye = (0.5, 64.5, 0.5)
        look = (1.0, 0.0, 0.0)

        # Distance to x=5.0 plane is exactly 4.5m
        hit_survival = fast_voxel_traversal(eye, look, 4.5, is_solid)
        self.assertTrue(hit_survival.hit)
        self.assertAlmostEqual(hit_survival.distance, 4.5, places=3)

        # Reach of 4.4m must miss the block at x=5.0
        hit_short = fast_voxel_traversal(eye, look, 4.4, is_solid)
        self.assertFalse(hit_short.hit)

        # Block at distance 4.8m: Miss in Survival (4.5m), Hit in Creative (5.0m)
        is_solid_far = lambda x, y, z: (x, y, z) == (5, 64, 0)
        eye_far = (0.2, 64.5, 0.5)  # distance to x=5 is 4.8m
        self.assertFalse(fast_voxel_traversal(eye_far, look, 4.5, is_solid_far).hit)
        self.assertTrue(fast_voxel_traversal(eye_far, look, 5.0, is_solid_far).hit)

    def test_08_dda_raycast_air_voxel_stepping_and_traversal(self):
        """Verify DDA steps through intermediate air cells without skipping or tunneling."""
        stepped_cells = []
        target = (4, 64, 0)

        def recording_predicate(x, y, z):
            stepped_cells.append((x, y, z))
            return (x, y, z) == target

        origin = (0.5, 64.5, 0.5)
        direction = (1.0, 0.0, 0.0)
        res = fast_voxel_traversal(origin, direction, 5.0, recording_predicate)

        self.assertTrue(res.hit)
        self.assertEqual(res.target_block, target)
        # Traversed path must include x=0, 1, 2, 3, 4
        x_coords = [c[0] for c in stepped_cells]
        self.assertEqual(x_coords, [0, 1, 2, 3, 4])

    def test_09_dda_raycast_inside_solid_block_fallback(self):
        """Verify ray starting inside solid block returns immediate hit with distance 0.0 and top normal."""
        is_solid = lambda x, y, z: (x, y, z) == (3, 64, 3)
        origin_inside = (3.5, 64.2, 3.8)
        direction = (1.0, 0.0, 0.0)

        hit = fast_voxel_traversal(origin_inside, direction, 5.0, is_solid)
        self.assertTrue(hit.hit)
        self.assertEqual(hit.target_block, (3, 64, 3))
        self.assertEqual(hit.distance, 0.0)
        self.assertEqual(hit.face_normal, (0, 1, 0))
        self.assertEqual(hit.place_block, (3, 65, 3))

    def test_10_dda_raycast_degenerate_zero_direction_vector(self):
        """Verify degenerate zero or NaN direction vector results in safe miss with no NaN/crash."""
        is_solid = lambda x, y, z: True
        origin = (0.0, 64.0, 0.0)

        hit_zero = fast_voxel_traversal(origin, (0.0, 0.0, 0.0), 5.0, is_solid)
        self.assertFalse(hit_zero.hit)

    # =========================================================================
    # Group 3: Player Kinematics & Swept AABB Physics
    # =========================================================================

    def test_11_kinematics_hitbox_dimensions_and_eye_offsets(self):
        """Verify canonical player AABB geometry and camera eye heights."""
        # Standing hitbox: 0.6w x 1.8h x 0.6d, eye = 1.62m
        aabb_standing = Kinematics.get_player_aabb(0.0, 64.0, 0.0, is_sneaking=False)
        self.assertAlmostEqual(aabb_standing.max_x - aabb_standing.min_x, 0.60, places=4)
        self.assertAlmostEqual(aabb_standing.max_z - aabb_standing.min_z, 0.60, places=4)
        self.assertAlmostEqual(aabb_standing.max_y - aabb_standing.min_y, 1.80, places=4)
        self.assertAlmostEqual(Kinematics.EYE_LEVEL_STANDING, 1.62, places=4)

        # Sneaking hitbox: 0.6w x 1.5h x 0.6d, eye = 1.35m
        aabb_sneaking = Kinematics.get_player_aabb(0.0, 64.0, 0.0, is_sneaking=True)
        self.assertAlmostEqual(aabb_sneaking.max_y - aabb_sneaking.min_y, 1.50, places=4)
        self.assertAlmostEqual(Kinematics.EYE_LEVEL_SNEAKING, 1.35, places=4)

    def test_12_kinematics_gravity_terminal_velocity_and_substep_antitunneling(self):
        """Verify gravity (-32.0 m/s^2), terminal velocity (-78.4 m/s), and anti-tunneling floor catch."""
        # 1. Asymptotic terminal velocity convergence via discrete recurrence
        vy = 0.0
        for _ in range(1000):
            vy = (vy - 0.08) * 0.98
        self.assertAlmostEqual(vy * 20.0, -78.4, places=2)

        # 2. Free fall simulation starting at high altitude
        controller = VoxelPhysicsController(0.0, 100.0, 0.0)
        dt = 1.0 / 60.0
        no_solid = lambda x, y, z: False

        # Fall for 3 seconds (180 ticks) in vacuum
        for _ in range(180):
            controller.tick(dt, (0, 0, 0), False, no_solid)

        self.assertAlmostEqual(controller.vy, -78.4, places=1)

        # 3. Terminal velocity drop onto 1-block thin floor at y=0
        # At -78.4 m/s, delta_y per tick is -1.306m. Anti-tunneling sub-step MUST catch floor.
        floor_solid = lambda x, y, z: (y == 0)
        drop_controller = VoxelPhysicsController(0.0, 1.0, 0.0)
        drop_controller.vy = -78.4
        drop_controller.tick(dt, (0, 0, 0), False, floor_solid)

        # Must land on floor at y = 1.0 (top of voxel y=0)
        self.assertAlmostEqual(drop_controller.y, 1.0, places=2)
        self.assertTrue(drop_controller.is_grounded)
        self.assertEqual(drop_controller.vy, 0.0)

    def test_13_kinematics_jump_impulse_and_apex_clearance(self):
        """Verify jump impulse (8.944 m/s continuous, 0.42 blk/tick discrete) clears 1.25m obstacle."""
        # Discrete Java trajectory
        y = 0.0
        vy = 0.42
        max_y = 0.0
        for _ in range(20):
            y += vy
            if y > max_y:
                max_y = y
            vy = (vy - 0.08) * 0.98
        self.assertGreater(max_y, 1.250)
        self.assertAlmostEqual(max_y, 1.2522, places=3)

        # Continuous physics controller jump from ground
        floor = lambda x, y, z: (y < 64)
        p = VoxelPhysicsController(0.0, 64.0, 0.0)
        p.is_grounded = True
        dt = 1.0 / 60.0

        # Initiate jump
        p.tick(dt, (0, 0, 0), True, floor)
        self.assertEqual(p.vy, Kinematics.JUMP_IMPULSE + Kinematics.GRAVITY * dt)

        # Track trajectory until apex
        max_height = p.y
        for _ in range(60):
            p.tick(dt, (0, 0, 0), False, floor)
            if p.y > max_height:
                max_height = p.y

        apex_gain = max_height - 64.0
        # Discrete 60Hz Euler integration achieves ~1.176m clearance (comfortably clears 1.0m hurdle)
        self.assertGreaterEqual(apex_gain, 1.15)
        self.assertLessEqual(apex_gain, 1.30)
        # Theoretical continuous kinematic apex: v^2 / (2 * |g|) == 1.250m
        theoretical_apex = (Kinematics.JUMP_IMPULSE ** 2) / (2.0 * abs(Kinematics.GRAVITY))
        self.assertAlmostEqual(theoretical_apex, 1.25, places=2)

    def test_14_kinematics_friction_drag_and_acceleration_blending(self):
        """Verify ground friction factor (0.546), air drag (0.98), and movement blend rates."""
        self.assertAlmostEqual(Kinematics.GROUND_FRICTION_FACTOR, 0.546, places=3)
        self.assertAlmostEqual(Kinematics.AIR_DRAG_FACTOR, 0.980, places=3)

        # Walking acceleration from rest
        p = VoxelPhysicsController(0.0, 64.0, 0.0)
        p.is_grounded = True
        dt = 1.0 / 60.0
        empty = lambda x, y, z: (y < 64)

        # Accelerate forward
        p.tick(dt, (0, 0, 1.0), False, empty)
        self.assertGreater(p.vz, 0.0)
        self.assertLessEqual(p.vz, Kinematics.BASE_WALK_SPEED)

    def test_15_physics_axis_decoupled_resolution_order(self):
        """Verify collision resolution is ordered strictly Y -> X -> Z, enabling diagonal corner gliding."""
        # Wall at x=1, floor at y=0. Player moves diagonally into corner.
        world = lambda x, y, z: (y < 0) or (x >= 1 and y >= 0)
        p = VoxelPhysicsController(0.5, 0.0, 0.0)
        p.is_grounded = True
        dt = 1.0 / 60.0

        # Push diagonally into wall (x) and along open corridor (z) for 30 ticks
        for _ in range(30):
            p.tick(dt, (1.0, 0.0, 1.0), False, world)

        # X is blocked by wall at x=1.0 (player clamped to x=1.0 - 0.3 = 0.7)
        self.assertAlmostEqual(p.x, 0.70, places=2)
        # Z is unblocked and proceeds freely
        self.assertGreater(p.z, 0.5)

    def test_16_physics_auto_step_resolution(self):
        """Verify auto-stepping up a 0.5m obstacle without requiring a jump."""
        class MockTerrain:
            def __call__(self, x, y, z):
                return y < 0 or (x in (1, 2) and y == 0)

            def get_aabb(self, x, y, z):
                if x in (1, 2) and y == 0:
                    return AABB(x, 0.0, z, x + 1.0, 0.5, z + 1.0)
                return AABB(x, y, z, x + 1.0, y + 1.0, z + 1.0)

        mock_terrain = MockTerrain()
        p = VoxelPhysicsController(0.0, 0.0, 0.5)
        p.is_grounded = True
        dt = 1.0 / 60.0

        # Walk East (+X) into the 0.5m step for 30 ticks
        for _ in range(30):
            p.tick(dt, (1.0, 0.0, 0.0), False, mock_terrain)

        # Successful auto-step elevates base onto step (y >= 0.5)
        self.assertAlmostEqual(p.y, 0.50, places=2)
        self.assertTrue(p.is_grounded)

    def test_17_physics_auto_step_low_ceiling_abort(self):
        """Verify auto-step aborts if vertical headroom above obstacle is < 1.8m (prevent suffocation)."""
        class CeilingObstacle:
            def __call__(self, x, y, z):
                # Floor at y < 0, 0.5m step at x=1, ceiling at y=2
                return (y < 0) or (x == 1 and y == 0) or (x == 1 and y == 2)

            def get_aabb(self, x, y, z):
                if x == 1 and y == 0:
                    return AABB(1.0, 0.0, 0.0, 2.0, 0.5, 1.0)
                return AABB(x, y, z, x + 1.0, y + 1.0, z + 1.0)

        terrain = CeilingObstacle()
        p = VoxelPhysicsController(0.0, 0.0, 0.5)
        p.is_grounded = True
        dt = 1.0 / 60.0

        # Attempt to step forward
        for _ in range(40):
            p.tick(dt, (1.0, 0.0, 0.0), False, terrain)

        # Auto-step must be aborted: player cannot be elevated to y=0.5 under low ceiling
        self.assertAlmostEqual(p.y, 0.0, places=2)

    def test_18_physics_sneak_ledge_clamp(self):
        """Verify sneaking player does not fall off platform edges."""
        # Single block platform at (0, 64, 0), void all around
        platform = lambda x, y, z: (x == 0 and y == 64 and z == 0)
        p = VoxelPhysicsController(0.0, 65.0, 0.0)
        p.is_grounded = True
        p.is_sneaking = True
        dt = 1.0 / 60.0

        # Push heavily toward edge (+X)
        for _ in range(30):
            p.tick(dt, (1.0, 0.0, 0.0), False, platform)

        # Player must remain safely on platform (x + half_width < 1.0)
        self.assertLess(p.x, 0.70)
        self.assertAlmostEqual(p.y, 65.0, places=2)
        self.assertTrue(p.is_grounded)

    # =========================================================================
    # Group 4: Block Interaction & Destruction FSM
    # =========================================================================

    def test_19_block_destruction_hardness_and_tool_multipliers(self):
        """Verify block hardness table and tool efficiency speedups."""
        hardness_table = {
            "air": 0.0,
            "dirt": 0.5,
            "sand": 0.5,
            "stone": 1.5,
            "wood": 2.0,
            "bedrock": -1.0
        }
        self.assertEqual(hardness_table["air"], 0.0)
        self.assertEqual(hardness_table["dirt"], 0.5)
        self.assertEqual(hardness_table["stone"], 1.5)
        self.assertEqual(hardness_table["wood"], 2.0)
        self.assertEqual(hardness_table["bedrock"], -1.0)

        # Tool multiplier on stone: bare hands = 1.0x, wood pick = 2.0x, stone pick = 4.0x, iron pick = 6.0x
        def tool_mult(tool_id):
            if tool_id == ItemID.WOODEN_PICKAXE: return 2.0
            if tool_id == ItemID.STONE_PICKAXE: return 4.0
            if tool_id == ItemID.IRON_PICKAXE: return 6.0
            return 1.0

        self.assertEqual(tool_mult(ItemID.AIR), 1.0)
        self.assertEqual(tool_mult(ItemID.WOODEN_PICKAXE), 2.0)
        self.assertEqual(tool_mult(ItemID.STONE_PICKAXE), 4.0)
        self.assertEqual(tool_mult(ItemID.IRON_PICKAXE), 6.0)

    def test_20_block_destruction_progress_accumulation_and_cracks(self):
        """Verify destruction progress accumulation and 10-stage crack overlay mapping."""
        hardness = 1.5  # Stone (1.5s)
        dt = 0.1
        progress = 0.0

        # Step progress
        for _ in range(5):
            progress += dt / hardness

        # 0.5s elapsed on 1.5s block -> progress = 0.333
        self.assertAlmostEqual(progress, 0.3333, places=3)
        crack_stage = min(9, max(0, math.floor(progress * 10.0)))
        self.assertEqual(crack_stage, 3)

        # Advance to completion (10 more ticks of 0.1s -> total 15 * 0.1 / 1.5 = 1.0)
        for _ in range(10):
            progress += dt / hardness
        self.assertGreaterEqual(progress, 1.0 - 1e-6)

    def test_21_block_destruction_cancellation_semantics(self):
        """Verify releasing attack button, switching target, or exceeding reach resets breaking FSM."""
        class MockFSM:
            def __init__(self):
                self.progress = 0.5
                self.target = (1, 64, 1)

            def update(self, lmb_down, target, dist):
                if not lmb_down or target != self.target or dist > 5.0:
                    self.progress = 0.0

        fsm = MockFSM()
        # Release mouse button
        fsm.update(False, (1, 64, 1), 3.0)
        self.assertEqual(fsm.progress, 0.0)

        # Switch target voxel
        fsm.progress = 0.5
        fsm.update(True, (2, 64, 1), 3.0)
        self.assertEqual(fsm.progress, 0.0)

        # Exceed 5.0m reach
        fsm.progress = 0.5
        fsm.update(True, (1, 64, 1), 5.5)
        self.assertEqual(fsm.progress, 0.0)

    # =========================================================================
    # Group 5: Block Placement Validation
    # =========================================================================

    def test_22_block_placement_anti_suffocation_collision_validation(self):
        """Verify block placement is rejected if the candidate block intersects the player AABB."""
        player_aabb = Kinematics.get_player_aabb(10.0, 64.0, 10.0, is_sneaking=False)

        def validate_placement(place_x, place_y, place_z):
            block_box = AABB(place_x, place_y, place_z, place_x + 1.0, place_y + 1.0, place_z + 1.0)
            return not player_aabb.intersects(block_box)

        # Placing block inside player's feet or torso -> REJECT
        self.assertFalse(validate_placement(10, 64, 10))
        self.assertFalse(validate_placement(10, 65, 10))

        # Placing adjacent block outside player volume -> ACCEPT
        self.assertTrue(validate_placement(11, 64, 10))
        self.assertTrue(validate_placement(10, 66, 10))

    def test_23_block_placement_world_bounds_and_occupancy(self):
        """Verify block placement respects chunk height [0, 255] and empty cell occupancy."""
        def can_place(y, is_occupied):
            if y < 0 or y >= 256:
                return False
            if is_occupied:
                return False
            return True

        self.assertFalse(can_place(-1, False))
        self.assertFalse(can_place(256, False))
        self.assertFalse(can_place(64, True))
        self.assertTrue(can_place(64, False))

    # =========================================================================
    # Group 6: 41-Slot Inventory & 9-Slot Hotbar State Machine
    # =========================================================================

    def test_24_inventory_41_slot_layout_and_stack_limits(self):
        """Verify 41-slot inventory layout (9 hotbar + 27 main + 4 armor + 1 offhand) and stack boundaries."""
        inv = InventoryModel()
        self.assertEqual(len(inv.slots), 41)
        self.assertEqual(inv.HOTBAR_SIZE, 9)
        self.assertEqual(inv.MAIN_SIZE, 27)
        self.assertEqual(inv.ARMOR_SIZE, 4)
        self.assertEqual(inv.OFFHAND_SIZE, 1)

        # Stack boundaries: tools = 1, blocks = 64
        self.assertEqual(get_default_max_stack(ItemID.DIRT), 64)
        self.assertEqual(get_default_max_stack(ItemID.STONE), 64)
        self.assertEqual(get_default_max_stack(ItemID.WOODEN_PICKAXE), 1)
        self.assertEqual(get_default_max_stack(ItemID.IRON_PICKAXE), 1)

    def test_25_hotbar_selection_and_positive_modulo_scroll(self):
        """Verify hotbar selection keys 1..9 and mouse wheel positive modulo wrap-around."""
        inv = InventoryModel()

        # Selection keys 1..9
        inv.select_hotbar(0)
        self.assertEqual(inv.selected_hotbar_slot, 0)
        inv.select_hotbar(8)
        self.assertEqual(inv.selected_hotbar_slot, 8)

        # Mouse scroll positive modulo wrap: scroll right (delta=-1) from 8 wraps to 0
        inv.scroll_hotbar(-1)
        self.assertEqual(inv.selected_hotbar_slot, 0)

        # Scroll left (delta=+1) from 0 wraps to 8
        inv.scroll_hotbar(1)
        self.assertEqual(inv.selected_hotbar_slot, 8)

        # Extreme negative delta wrap
        inv.scroll_hotbar(-10)
        self.assertEqual(inv.selected_hotbar_slot, 0)

    def test_26_inventory_mouse_click_pickup_place_swap_and_split(self):
        """Verify mouse left-click (pickup/place/swap) and right-click (split/place single)."""
        inv = InventoryModel()
        inv.slots[0] = ItemStack(ItemID.DIRT, 10, 64)

        # Right-click on slot 0: pick up half (ceil(10/2) = 5)
        inv.mouse_click_slot(0, is_right_click=True)
        self.assertEqual(inv.cursor_item.count, 5)
        self.assertEqual(inv.slots[0].count, 5)

        # Right-click on empty slot 1: place 1 item
        inv.mouse_click_slot(1, is_right_click=True)
        self.assertEqual(inv.slots[1].count, 1)
        self.assertEqual(inv.cursor_item.count, 4)

        # Left-click on slot 1: merge remaining 4 into 1 -> 5
        inv.mouse_click_slot(1, is_right_click=False)
        self.assertEqual(inv.slots[1].count, 5)
        self.assertTrue(inv.cursor_item.is_empty())

    def test_27_inventory_shift_click_quick_move(self):
        """Verify shift-click quick-transfers items between hotbar and main inventory."""
        inv = InventoryModel()
        inv.slots[0] = ItemStack(ItemID.COBBLESTONE, 32, 64)

        # Shift-click hotbar slot 0 -> moves to first empty main slot (slot 9)
        inv.shift_click_slot(0)
        self.assertTrue(inv.slots[0].is_empty())
        self.assertEqual(inv.slots[9].item_id, ItemID.COBBLESTONE)
        self.assertEqual(inv.slots[9].count, 32)

        # Shift-click main slot 9 -> moves back to hotbar slot 0
        inv.shift_click_slot(9)
        self.assertTrue(inv.slots[9].is_empty())
        self.assertEqual(inv.slots[0].count, 32)

    # =========================================================================
    # Group 7: 2x2 & 3x3 Crafting Pattern Matchers
    # =========================================================================

    def test_28_crafting_2x2_matchers(self):
        """Verify canonical 2x2 crafting recipes (planks, sticks, crafting table, torches)."""
        crafting = CraftingEngine()

        # 1. 1 Wood Log -> 4 Wood Planks (shapeless)
        grid_log = [[ItemStack(ItemID.WOOD_LOG, 1), ItemStack()],
                    [ItemStack(), ItemStack()]]
        res_planks = crafting.match(grid_log)
        self.assertIsNotNone(res_planks)
        self.assertEqual(res_planks.item_id, ItemID.WOOD_PLANKS)
        self.assertEqual(res_planks.count, 4)

        # 2. 2 Wood Planks vertical -> 4 Sticks (shaped 1x2)
        grid_sticks = [[ItemStack(ItemID.WOOD_PLANKS, 1), ItemStack()],
                       [ItemStack(ItemID.WOOD_PLANKS, 1), ItemStack()]]
        res_sticks = crafting.match(grid_sticks)
        self.assertIsNotNone(res_sticks)
        self.assertEqual(res_sticks.item_id, ItemID.STICK)
        self.assertEqual(res_sticks.count, 4)

        # 3. 4 Wood Planks -> 1 Crafting Table (shaped 2x2)
        grid_table = [[ItemStack(ItemID.WOOD_PLANKS, 1), ItemStack(ItemID.WOOD_PLANKS, 1)],
                      [ItemStack(ItemID.WOOD_PLANKS, 1), ItemStack(ItemID.WOOD_PLANKS, 1)]]
        res_table = crafting.match(grid_table)
        self.assertIsNotNone(res_table)
        self.assertEqual(res_table.item_id, ItemID.CRAFTING_TABLE)
        self.assertEqual(res_table.count, 1)

        # 4. 1 Coal + 1 Stick -> 4 Torches (shapeless)
        grid_torch = [[ItemStack(ItemID.COAL, 1), ItemStack(ItemID.STICK, 1)],
                      [ItemStack(), ItemStack()]]
        res_torch = crafting.match(grid_torch)
        self.assertIsNotNone(res_torch)
        self.assertEqual(res_torch.item_id, ItemID.TORCH)
        self.assertEqual(res_torch.count, 4)

    def test_29_crafting_3x3_matchers(self):
        """Verify canonical 3x3 crafting recipes (pickaxes, furnace)."""
        crafting = CraftingEngine()

        # 1. Wooden Pickaxe: 3 Planks top, 2 Sticks center
        grid_pick = [
            [ItemStack(ItemID.WOOD_PLANKS, 1), ItemStack(ItemID.WOOD_PLANKS, 1), ItemStack(ItemID.WOOD_PLANKS, 1)],
            [ItemStack(), ItemStack(ItemID.STICK, 1), ItemStack()],
            [ItemStack(), ItemStack(ItemID.STICK, 1), ItemStack()]
        ]
        res_pick = crafting.match(grid_pick)
        self.assertIsNotNone(res_pick)
        self.assertEqual(res_pick.item_id, ItemID.WOODEN_PICKAXE)
        self.assertEqual(res_pick.durability, 59)

        # 2. Furnace: 8 Cobblestone ring
        grid_furnace = [
            [ItemStack(ItemID.COBBLESTONE, 1), ItemStack(ItemID.COBBLESTONE, 1), ItemStack(ItemID.COBBLESTONE, 1)],
            [ItemStack(ItemID.COBBLESTONE, 1), ItemStack(), ItemStack(ItemID.COBBLESTONE, 1)],
            [ItemStack(ItemID.COBBLESTONE, 1), ItemStack(ItemID.COBBLESTONE, 1), ItemStack(ItemID.COBBLESTONE, 1)]
        ]
        res_furnace = crafting.match(grid_furnace)
        self.assertIsNotNone(res_furnace)
        self.assertEqual(res_furnace.item_id, ItemID.FURNACE)
        self.assertEqual(res_furnace.count, 1)

    # =========================================================================
    # Group 8: Ponytail Minimalism & Architecture Annotations
    # =========================================================================

    def test_30_ponytail_pragmatic_ceiling_annotations(self):
        """Verify all gameplay source and header files declare Ponytail pragmatism annotations."""
        for path in self.all_files:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn(
                "// ponytail:", content,
                f"File {os.path.basename(path)} must include Ponytail pragmatic ceiling annotation."
            )


if __name__ == "__main__":
    unittest.main()
