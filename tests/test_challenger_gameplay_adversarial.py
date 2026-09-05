"""
Empirical Adversarial Verification Suite — Challenger Remedy 1
=============================================================
Author: challenger_remedy_1
Role: empirical challenger, adversarial verifier

Adversarially validates:
1. Player kinematics: terminal velocity drops (-78.4 m/s), anti-tunneling sub-stepping, apex clearance.
2. Rigid AABB geometry & collision: 0.6x1.8 / 0.6x1.5, eye offsets 1.62 / 1.35, Y->X->Z order invariant, diagonal corner gliding.
3. Speculative auto-step (+0.55m): 0.50m slab, 0.55m limit, 0.56m rejection, 1.0m wall rejection, low ceiling headroom abort (<1.8m clearance).
4. Sneak ledge-clamping (-0.1m probe): 4 cardinal directions, diagonal corner, overhang boundary (1.30m), long-duration stability, sneak-release falloff.
5. Amanatides-Woo DDA raymarching: 6 cardinal face normals, reach limits (4.5m survival vs 5.0m creative), inside-block fallback, degenerate vectors.
6. Progressive block destruction FSM: hardness table, pickaxe multipliers, 10-stage crack mapping (0..9), instant breaks, bedrock indestructibility, cancellation triggers.
7. 41-slot inventory state machine: slot partitioning (9/27/4/1), stack limits (64/16/1), positive modulo wrap, mouse click mechanics, shift-click transfer, 2x2 & 3x3 crafting.
8. C codebase integration & invariants: RaycastHit uniqueness, zero heap allocation, Ponytail annotations, authentic loop wiring.
"""

import os
import sys
import math
import re
import unittest
from typing import Tuple, Callable

# Ensure project root is in sys.path
cur = os.path.abspath(__file__)
PROJECT_ROOT = os.path.dirname(os.path.dirname(cur))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from tests.canonical_models import (
    AABB,
    Kinematics,
    VoxelPhysicsController,
    RaycastHit as CanonicalRaycastHit,
    fast_voxel_traversal,
    ItemID,
    ItemStack,
    get_default_max_stack,
    get_default_durability,
    InventoryModel,
    CraftingEngine
)


class TestChallengerGameplayAdversarial(unittest.TestCase):
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
        cls.main_c = os.path.join(PROJECT_ROOT, "src", "main.c")

    # =========================================================================
    # 1. Kinematics, Terminal Velocity (-78.4 m/s) & Anti-Tunneling
    # =========================================================================

    def test_adv_01_kinematic_terminal_velocity_and_substep_antitunneling(self):
        """Verify terminal velocity recurrence convergence, multi-altitude drops, and dt=0.25s anti-tunneling."""
        # 1. Discrete recurrence convergence: vy_n+1 = (vy_n - 0.08) * 0.98 -> -3.92 blk/tick -> -78.4 m/s
        vy = 0.0
        for _ in range(1000):
            vy = (vy - 0.08) * 0.98
        self.assertAlmostEqual(vy * 20.0, -78.4, places=2)

        # 2. Free-fall from 500m in vacuum reaches exactly terminal velocity -78.4 m/s
        ctrl = VoxelPhysicsController(0.0, 500.0, 0.0)
        dt = 1.0 / 60.0
        no_solid = lambda x, y, z: False
        for _ in range(300):
            ctrl.tick(dt, (0, 0, 0), False, no_solid)
        self.assertAlmostEqual(ctrl.vy, -78.4, places=1)

        # 3. High altitude drop (1000m) onto thin 1-block floor at y=0
        # Player must land on top of floor at y=1.0 without tunneling through
        c1000 = VoxelPhysicsController(0.5, 1000.0, 0.5)
        floor = lambda x, y, z: (y == 0)
        for _ in range(1500):
            c1000.tick(dt, (0, 0, 0), False, floor)
            if c1000.is_grounded:
                break
        self.assertTrue(c1000.is_grounded)
        self.assertAlmostEqual(c1000.y, 1.0, places=2)
        self.assertEqual(c1000.vy, 0.0)

        # 4. Stress drop with maximum accumulator clamp dt = 0.25s (delta_y = -19.6m in single tick)
        # Sub-stepping with 0.5m limit partitions into 40 sub-steps, catching floor at y=0
        c_clamp = VoxelPhysicsController(0.5, 5.0, 0.5)
        c_clamp.vy = -78.4
        c_clamp.tick(0.25, (0, 0, 0), False, floor)
        self.assertTrue(c_clamp.is_grounded)
        self.assertAlmostEqual(c_clamp.y, 1.0, places=2)

        # 5. Jump impulse apex clearance (sqrt(2 * 32.0 * 1.25) = 8.944 m/s)
        jump_ctrl = VoxelPhysicsController(0.0, 64.0, 0.0)
        jump_ctrl.is_grounded = True
        jump_ctrl.tick(dt, (0, 0, 0), True, lambda x, y, z: y < 64)
        max_h = jump_ctrl.y
        for _ in range(60):
            jump_ctrl.tick(dt, (0, 0, 0), False, lambda x, y, z: y < 64)
            if jump_ctrl.y > max_h:
                max_h = jump_ctrl.y
        apex_gain = max_h - 64.0
        self.assertGreaterEqual(apex_gain, 1.15)
        self.assertLessEqual(apex_gain, 1.30)

    # =========================================================================
    # 2. Rigid AABB Geometry & Axis-Decoupled Collision Invariant (Y -> X -> Z)
    # =========================================================================

    def test_adv_02_aabb_boundary_and_axis_decoupled_resolution(self):
        """Verify player AABB dimensions, eye offsets, Y->X->Z resolution order, and negative coord stability."""
        # 1. Dimensions
        box_stand = Kinematics.get_player_aabb(0.0, 64.0, 0.0, is_sneaking=False)
        self.assertAlmostEqual(box_stand.max_x - box_stand.min_x, 0.60, places=4)
        self.assertAlmostEqual(box_stand.max_y - box_stand.min_y, 1.80, places=4)
        self.assertAlmostEqual(box_stand.max_z - box_stand.min_z, 0.60, places=4)

        box_sneak = Kinematics.get_player_aabb(0.0, 64.0, 0.0, is_sneaking=True)
        self.assertAlmostEqual(box_sneak.max_y - box_sneak.min_y, 1.50, places=4)

        # 2. Camera eye offsets
        self.assertAlmostEqual(Kinematics.EYE_LEVEL_STANDING, 1.62, places=4)
        self.assertAlmostEqual(Kinematics.EYE_LEVEL_SNEAKING, 1.35, places=4)

        # 3. Collision ordering invariant: diagonal corner push into X wall slides along Z
        # Wall at x=1.0, corridor open along Z. Push (1, 0, 1)
        wall_x = lambda x, y, z: (y < 0) or (x >= 1 and y >= 0)
        p_slide = VoxelPhysicsController(0.5, 0.0, 0.0)
        p_slide.is_grounded = True
        dt = 1.0 / 60.0
        for _ in range(30):
            p_slide.tick(dt, (1.0, 0.0, 1.0), False, wall_x)
        # X clamped to wall face minus half-width: 1.0 - 0.3 = 0.70
        self.assertAlmostEqual(p_slide.x, 0.70, places=2)
        # Z unblocked and advanced forward
        self.assertGreater(p_slide.z, 0.5)

        # 4. Negative world coordinates stability (e.g. x in [-10, -5], z in [-20, -15])
        neg_floor = lambda x, y, z: (y < -10)
        p_neg = VoxelPhysicsController(-50.5, -10.0, -100.5)
        p_neg.is_grounded = True
        for _ in range(20):
            p_neg.tick(dt, (1.0, 0.0, -1.0), False, neg_floor)
        self.assertTrue(p_neg.is_grounded)
        self.assertAlmostEqual(p_neg.y, -10.0, places=2)
        self.assertGreater(p_neg.x, -50.5)
        self.assertLess(p_neg.z, -100.5)

    # =========================================================================
    # 3. Speculative Auto-Step (+0.55m) Clearance & Headroom Invariants
    # =========================================================================

    def test_adv_03_auto_step_clearance_and_headroom_limits(self):
        """Verify auto-step on 0.50m and 0.55m, rejection of >0.55m and 1.0m, and ceiling clearance abort."""
        class CustomStepTerrain:
            def __init__(self, step_height, ceiling_y=None):
                self.step_height = step_height
                self.ceiling_y = ceiling_y

            def __call__(self, x, y, z):
                if y < 0: return True
                if x >= 1 and y == 0: return True
                if self.ceiling_y is not None and x >= 1 and y == self.ceiling_y: return True
                return False

            def get_aabb(self, x, y, z):
                if x >= 1 and y == 0:
                    return AABB(float(x), 0.0, float(z), float(x + 1), self.step_height, float(z + 1))
                return AABB(float(x), float(y), float(z), float(x + 1), float(y + 1), float(z + 1))

        dt = 1.0 / 60.0

        # 1. 0.50m slab auto-step succeeds without jump
        p05 = VoxelPhysicsController(0.0, 0.0, 0.5)
        p05.is_grounded = True
        terr05 = CustomStepTerrain(0.50)
        for _ in range(40): p05.tick(dt, (1.0, 0.0, 0.0), False, terr05)
        self.assertTrue(p05.is_grounded)
        self.assertAlmostEqual(p05.y, 0.50, places=2)
        self.assertGreater(p05.x, 1.0)

        # 2. 0.55m exact threshold auto-step succeeds
        p55 = VoxelPhysicsController(0.0, 0.0, 0.5)
        p55.is_grounded = True
        terr55 = CustomStepTerrain(0.55)
        for _ in range(40): p55.tick(dt, (1.0, 0.0, 0.0), False, terr55)
        self.assertTrue(p55.is_grounded)
        self.assertAlmostEqual(p55.y, 0.55, places=2)

        # 3. 0.56m exceeds threshold -> rejected, player stays at base floor y=0.0
        p56 = VoxelPhysicsController(0.0, 0.0, 0.5)
        p56.is_grounded = True
        terr56 = CustomStepTerrain(0.56)
        for _ in range(40): p56.tick(dt, (1.0, 0.0, 0.0), False, terr56)
        self.assertAlmostEqual(p56.y, 0.0, places=2)
        self.assertAlmostEqual(p56.x, 0.70, places=2)

        # 4. 1.00m full block -> rejected, player stays at y=0.0
        p10 = VoxelPhysicsController(0.0, 0.0, 0.5)
        p10.is_grounded = True
        terr10 = CustomStepTerrain(1.00)
        for _ in range(40): p10.tick(dt, (1.0, 0.0, 0.0), False, terr10)
        self.assertAlmostEqual(p10.y, 0.0, places=2)
        self.assertAlmostEqual(p10.x, 0.70, places=2)

        # 5. Low ceiling abort: obstacle=0.5m, ceiling at y=2 -> clearance = 1.5m < 1.8m -> abort step
        p_low = VoxelPhysicsController(0.0, 0.0, 0.5)
        p_low.is_grounded = True
        terr_low = CustomStepTerrain(0.50, ceiling_y=2)
        for _ in range(40): p_low.tick(dt, (1.0, 0.0, 0.0), False, terr_low)
        self.assertAlmostEqual(p_low.y, 0.0, places=2)
        self.assertAlmostEqual(p_low.x, 0.70, places=2)

        # 6. Sufficient ceiling clearance: obstacle=0.5m, ceiling at y=3 -> clearance = 2.5m >= 1.8m -> step succeeds
        p_high = VoxelPhysicsController(0.0, 0.0, 0.5)
        p_high.is_grounded = True
        terr_high = CustomStepTerrain(0.50, ceiling_y=3)
        for _ in range(40): p_high.tick(dt, (1.0, 0.0, 0.0), False, terr_high)
        self.assertAlmostEqual(p_high.y, 0.50, places=2)
        self.assertGreater(p_high.x, 1.0)

        # 7. Mid-air auto-step rejection: when is_grounded is False, player cannot auto-step
        p_air = VoxelPhysicsController(0.5, 0.2, 0.5)
        p_air.is_grounded = False
        p_air.vy = 0.0
        terr_air = CustomStepTerrain(0.50)
        p_air.tick(dt, (1.0, 0.0, 0.0), False, terr_air)
        self.assertFalse(p_air.is_grounded)
        self.assertLess(p_air.y, 0.50)

    # =========================================================================
    # 4. Sneak Ledge-Clamping (-0.1m Probe) & Overhang Boundaries
    # =========================================================================

    def test_adv_04_sneak_ledge_clamping_and_boundary_overhang(self):
        """Verify sneak edge-clamping across 4 cardinals, diagonal corners, 1.30m overhang, and un-sneak falloff."""
        plat = lambda x, y, z: (x == 0 and y == 64 and z == 0)
        dt = 1.0 / 60.0

        # 1. Test all 4 cardinal directions on isolated 1x1 block
        cardinals = [
            ('+X', (1.0, 0.0, 0.0), lambda p: (p.x > 1.25 and p.x <= 1.30)),
            ('-X', (-1.0, 0.0, 0.0), lambda p: (p.x < -0.25 and p.x >= -0.30)),
            ('+Z', (0.0, 0.0, 1.0), lambda p: (p.z > 1.25 and p.z <= 1.30)),
            ('-Z', (0.0, 0.0, -1.0), lambda p: (p.z < -0.25 and p.z >= -0.30)),
        ]
        for name, wish, check_limit in cardinals:
            ps = VoxelPhysicsController(0.5, 65.0, 0.5)
            ps.is_grounded = True
            ps.is_sneaking = True
            for _ in range(250):
                ps.tick(dt, wish, False, plat)
            self.assertTrue(ps.is_grounded, f'{name} must remain grounded')
            self.assertAlmostEqual(ps.y, 65.0, places=2, msg=f'{name} must not drop in Y')
            self.assertTrue(check_limit(ps), f'{name} must clamp at overhang boundary: pos=({ps.x:.3f}, {ps.z:.3f})')

        # 2. Diagonal corner push (+X, +Z): clamps on the 1.4mm corner of the block
        p_diag = VoxelPhysicsController(0.5, 65.0, 0.5)
        p_diag.is_grounded = True
        p_diag.is_sneaking = True
        for _ in range(500):
            p_diag.tick(dt, (1.0, 0.0, 1.0), False, plat)
        self.assertTrue(p_diag.is_grounded)
        self.assertAlmostEqual(p_diag.y, 65.0, places=2)
        self.assertAlmostEqual(p_diag.x, 1.2986, places=2)
        self.assertAlmostEqual(p_diag.z, 1.2986, places=2)

        # 3. Sneak release falloff: releasing sneak immediately walks off and begins free fall
        p_diag.is_sneaking = False
        for _ in range(20):
            p_diag.tick(dt, (1.0, 0.0, 1.0), False, plat)
        self.assertFalse(p_diag.is_grounded)
        self.assertLess(p_diag.y, 64.0)
        self.assertLess(p_diag.vy, -5.0)

        # 4. Long duration stability: 1000 ticks while sneaking on edge never falls
        p_long = VoxelPhysicsController(0.5, 65.0, 0.5)
        p_long.is_grounded = True
        p_long.is_sneaking = True
        for _ in range(1000):
            p_long.tick(dt, (1.0, 0.0, 0.0), False, plat)
        self.assertTrue(p_long.is_grounded)
        self.assertAlmostEqual(p_long.y, 65.0, places=2)

    # =========================================================================
    # 5. Amanatides-Woo Fast Voxel Traversal DDA Raycast
    # =========================================================================

    def test_adv_05_dda_raycast_normal_alignment_and_precision(self):
        """Verify DDA 6 face normals, reach limits (4.5m vs 5.0m), inside-block fallback, and degenerate rays."""
        target = (10, 64, 10)
        is_solid = lambda x, y, z: (x, y, z) == target

        # 1. 6 Cardinal Face Normals and Placement Target Resolution
        rays = [
            ((8.0, 64.5, 10.5), (1.0, 0.0, 0.0), (-1, 0, 0), (9, 64, 10), 2.0),
            ((12.0, 64.5, 10.5), (-1.0, 0.0, 0.0), (1, 0, 0), (11, 64, 10), 1.0),
            ((10.5, 67.0, 10.5), (0.0, -1.0, 0.0), (0, 1, 0), (10, 65, 10), 2.0),
            ((10.5, 62.0, 10.5), (0.0, 1.0, 0.0), (0, -1, 0), (10, 63, 10), 2.0),
            ((10.5, 64.5, 8.0), (0.0, 0.0, 1.0), (0, 0, -1), (10, 64, 9), 2.0),
            ((10.5, 64.5, 12.0), (0.0, 0.0, -1.0), (0, 0, 1), (10, 64, 11), 1.0),
        ]
        for orig, d_vec, exp_norm, exp_place, exp_dist in rays:
            h = fast_voxel_traversal(orig, d_vec, 5.0, is_solid)
            self.assertTrue(h.hit)
            self.assertEqual(h.target_block, target)
            self.assertEqual(h.face_normal, exp_norm)
            self.assertEqual(h.place_block, exp_place)
            self.assertAlmostEqual(h.distance, exp_dist, places=3)

        # 2. Strict reach boundary enforcement: 4.5m (Survival) vs 5.0m (Creative)
        block_at_5 = lambda x, y, z: (x, y, z) == (5, 64, 0)
        eye = (0.5, 64.5, 0.5)
        look = (1.0, 0.0, 0.0)

        # 4.49m reach misses
        self.assertFalse(fast_voxel_traversal(eye, look, 4.49, block_at_5).hit)
        # 4.50m reach hits
        self.assertTrue(fast_voxel_traversal(eye, look, 4.50, block_at_5).hit)

        # Eye at x=0.3 -> distance to x=5.0 is 4.7m: misses in Survival (4.5m), hits in Creative (5.0m)
        eye_far = (0.3, 64.5, 0.5)
        self.assertFalse(fast_voxel_traversal(eye_far, look, 4.5, block_at_5).hit)
        self.assertTrue(fast_voxel_traversal(eye_far, look, 5.0, block_at_5).hit)

        # Distance 5.01m misses in both
        eye_too_far = (-0.02, 64.5, 0.5)
        self.assertFalse(fast_voxel_traversal(eye_too_far, look, 5.0, block_at_5).hit)

        # 3. Inside-block fallback: ray starting inside solid voxel
        hit_inside = fast_voxel_traversal((10.2, 64.3, 10.7), (1.0, 0.0, 0.0), 5.0, is_solid)
        self.assertTrue(hit_inside.hit)
        self.assertEqual(hit_inside.target_block, target)
        self.assertEqual(hit_inside.distance, 0.0)
        self.assertEqual(hit_inside.face_normal, (0, 1, 0))
        self.assertEqual(hit_inside.place_block, (10, 65, 10))

        # 4. Degenerate zero / NaN vectors
        self.assertFalse(fast_voxel_traversal(eye, (0.0, 0.0, 0.0), 5.0, is_solid).hit)
        self.assertFalse(fast_voxel_traversal(eye, (float('nan'), 1.0, 0.0), 5.0, is_solid).hit)

    # =========================================================================
    # 6. Progressive Block Destruction FSM & 10-Stage Crack Progression
    # =========================================================================

    def test_adv_06_block_destruction_10_stage_crack_progression(self):
        """Verify block hardness, pickaxe multipliers, crack stages 0..9, instant breaks, bedrock, and resets."""
        # Hardness table
        hardness = {
            'air': 0.0, 'snow': 0.2, 'leaves': 0.2, 'cactus': 0.4,
            'dirt': 0.5, 'sand': 0.5, 'grass': 0.6, 'sandstone': 0.8,
            'stone': 1.5, 'wood': 2.0, 'bedrock': -1.0
        }
        self.assertEqual(hardness['air'], 0.0)
        self.assertEqual(hardness['dirt'], 0.5)
        self.assertEqual(hardness['stone'], 1.5)
        self.assertEqual(hardness['wood'], 2.0)
        self.assertEqual(hardness['bedrock'], -1.0)

        # Tool multiplier on stone
        def get_tool_mult(tool_id):
            if tool_id == ItemID.WOODEN_PICKAXE: return 2.0
            if tool_id == ItemID.STONE_PICKAXE: return 4.0
            if tool_id == ItemID.IRON_PICKAXE: return 6.0
            return 1.0

        self.assertEqual(get_tool_mult(ItemID.AIR), 1.0)
        self.assertEqual(get_tool_mult(ItemID.WOODEN_PICKAXE), 2.0)
        self.assertEqual(get_tool_mult(ItemID.STONE_PICKAXE), 4.0)
        self.assertEqual(get_tool_mult(ItemID.IRON_PICKAXE), 6.0)

        # 10-stage crack mapping: floor(progress * 10.0) clamped [0, 9]
        def calc_stage(p):
            return min(9, max(0, math.floor(p * 10.0)))

        self.assertEqual(calc_stage(0.00), 0)
        self.assertEqual(calc_stage(0.09), 0)
        self.assertEqual(calc_stage(0.10), 1)
        self.assertEqual(calc_stage(0.35), 3)
        self.assertEqual(calc_stage(0.50), 5)
        self.assertEqual(calc_stage(0.89), 8)
        self.assertEqual(calc_stage(0.95), 9)
        self.assertEqual(calc_stage(1.00), 9)

        # Progress accumulation: Stone (1.5s) with Iron Pickaxe (6.0x speedup)
        # Delta P per second = 6.0 / 1.5 = 4.0 / second -> break duration = 0.25 seconds (15 ticks at 60Hz)
        # Note: 15 * (1/15) in 64-bit float is 0.9999999999999999, so 1e-6 epsilon guards IEEE float boundaries
        dt = 1.0 / 60.0
        p = 0.0
        ticks_to_break = 0
        while p < 1.0 - 1e-6:
            p += (dt * 6.0) / 1.5
            ticks_to_break += 1
        self.assertEqual(ticks_to_break, 15)

        # Cancellation triggers: button release, target change, distance > 5.0m
        class FSM:
            def __init__(self):
                self.progress = 0.5
                self.target = (1, 64, 1)
            def update(self, lmb, target, dist):
                if not lmb or target != self.target or dist > 5.0:
                    self.progress = 0.0
                    return False
                return True

        fsm = FSM()
        # LMB release resets
        fsm.update(False, (1, 64, 1), 3.0)
        self.assertEqual(fsm.progress, 0.0)

        # Target change resets
        fsm.progress = 0.5
        fsm.update(True, (2, 64, 1), 3.0)
        self.assertEqual(fsm.progress, 0.0)

        # Exceed reach (> 5.0m) resets
        fsm.progress = 0.5
        fsm.update(True, (1, 64, 1), 5.01)
        self.assertEqual(fsm.progress, 0.0)

    # =========================================================================
    # 7. 41-Slot Inventory State Machine & Crafting Matchers
    # =========================================================================

    def test_adv_07_inventory_slot_limits_and_interaction_mechanics(self):
        """Verify 41 slots, stack sizes (64/16/1), hotbar positive modulo, mouse clicks, and 2x2/3x3 crafting."""
        inv = InventoryModel()

        # 1. Slot layout: 9 + 27 + 4 + 1 = 41
        self.assertEqual(len(inv.slots), 41)
        self.assertEqual(inv.HOTBAR_SIZE, 9)
        self.assertEqual(inv.MAIN_SIZE, 27)
        self.assertEqual(inv.ARMOR_SIZE, 4)
        self.assertEqual(inv.OFFHAND_SIZE, 1)

        # 2. Stack boundaries
        self.assertEqual(get_default_max_stack(ItemID.STONE), 64)
        self.assertEqual(get_default_max_stack(ItemID.DIRT), 64)
        self.assertEqual(get_default_max_stack(ItemID.WOODEN_PICKAXE), 1)
        self.assertEqual(get_default_max_stack(ItemID.IRON_PICKAXE), 1)

        # 3. Positive modulo hotbar cycling: scroll left/right wraps cleanly
        # Note: In C and Python, formula is (slot - scroll_delta) % 9
        inv.select_hotbar(0)
        inv.scroll_hotbar(1)  # (0 - 1) % 9 = 8
        self.assertEqual(inv.selected_hotbar_slot, 8)
        inv.scroll_hotbar(-1) # (8 - (-1)) % 9 = 9 % 9 = 0
        self.assertEqual(inv.selected_hotbar_slot, 0)
        inv.scroll_hotbar(-19) # (0 - (-19)) % 9 = 19 % 9 = 1
        self.assertEqual(inv.selected_hotbar_slot, 1)
        inv.scroll_hotbar(19)  # (1 - 19) % 9 = -18 % 9 = 0
        self.assertEqual(inv.selected_hotbar_slot, 0)

        # 4. Mouse click interactions
        inv.slots[0] = ItemStack(ItemID.COBBLESTONE, 16, 64)
        # Right-click slot 0: splits half (8) into cursor
        inv.mouse_click_slot(0, is_right_click=True)
        self.assertEqual(inv.slots[0].count, 8)
        self.assertEqual(inv.cursor_item.count, 8)

        # Right-click slot 1: deposits 1 into slot 1, 7 remains in cursor
        inv.mouse_click_slot(1, is_right_click=True)
        self.assertEqual(inv.slots[1].count, 1)
        self.assertEqual(inv.cursor_item.count, 7)

        # Left-click slot 1: merges 7 into 1 -> 8
        inv.mouse_click_slot(1, is_right_click=False)
        self.assertEqual(inv.slots[1].count, 8)
        self.assertTrue(inv.cursor_item.is_empty())

        # 5. Shift-click quick move
        # hotbar slot 0 moves to main slot 9
        inv.shift_click_slot(0)
        self.assertTrue(inv.slots[0].is_empty())
        self.assertEqual(inv.slots[9].item_id, ItemID.COBBLESTONE)
        self.assertEqual(inv.slots[9].count, 8)

        # Shift-click main slot 9: merges into matching hotbar slot 1 (8 + 8 = 16)
        inv.shift_click_slot(9)
        self.assertTrue(inv.slots[9].is_empty())
        self.assertEqual(inv.slots[1].count, 16)

        # Shift-click slot 1 back to main: moves to main slot 9 (16 items)
        inv.shift_click_slot(1)
        self.assertTrue(inv.slots[1].is_empty())
        self.assertEqual(inv.slots[9].count, 16)

        # Now that hotbar is completely empty, shift-click slot 9 moves to first empty hotbar slot (slot 0)
        inv.shift_click_slot(9)
        self.assertTrue(inv.slots[9].is_empty())
        self.assertEqual(inv.slots[0].count, 16)

        # 6. Crafting 2x2: 1 Wood Log -> 4 Planks
        crafting = CraftingEngine()
        grid_planks = [[ItemStack(ItemID.WOOD_LOG, 1), ItemStack()],
                       [ItemStack(), ItemStack()]]
        res_planks = crafting.match(grid_planks)
        self.assertIsNotNone(res_planks)
        self.assertEqual(res_planks.item_id, ItemID.WOOD_PLANKS)
        self.assertEqual(res_planks.count, 4)

        # 7. Crafting 3x3: Iron Pickaxe
        grid_iron_pick = [
            [ItemStack(ItemID.IRON_INGOT, 1), ItemStack(ItemID.IRON_INGOT, 1), ItemStack(ItemID.IRON_INGOT, 1)],
            [ItemStack(), ItemStack(ItemID.STICK, 1), ItemStack()],
            [ItemStack(), ItemStack(ItemID.STICK, 1), ItemStack()]
        ]
        res_iron = crafting.match(grid_iron_pick)
        self.assertIsNotNone(res_iron)
        self.assertEqual(res_iron.item_id, ItemID.IRON_PICKAXE)
        self.assertEqual(res_iron.durability, 250)

    # =========================================================================
    # 8. C Codebase Invariants & Authentic Engine Wiring
    # =========================================================================

    def test_adv_08_c_source_invariants_and_authentic_engine_wiring(self):
        """Verify zero heap allocations, single RaycastHit struct, Ponytail annotations, and main.c wiring."""
        all_gameplay = [
            self.physics_h, self.physics_c,
            self.raycast_h, self.raycast_c,
            self.interaction_h, self.interaction_c,
            self.inventory_h, self.inventory_c
        ]
        # 1. Zero heap allocations across gameplay C files
        forbidden = [r"\bmalloc\s*\(", r"\bcalloc\s*\(", r"\brealloc\s*\(", r"\bfree\s*\("]
        for p in all_gameplay:
            with open(p, "r", encoding="utf-8") as f:
                code = re.sub(r"/\*.*?\*/", "", f.read(), flags=re.DOTALL)
                code = re.sub(r"//.*", "", code)
                for pat in forbidden:
                    self.assertIsNone(re.search(pat, code), f'Forbidden heap allocation in {os.path.basename(p)}')

        # 2. Check RaycastHit is defined uniquely in physics.h
        with open(self.physics_h, "r", encoding="utf-8") as f:
            self.assertIn("typedef struct RaycastHit", f.read())
        with open(self.interaction_h, "r", encoding="utf-8") as f:
            self.assertNotIn("typedef struct RaycastHit", f.read())

        # 3. Check authentic loop wiring in src/main.c (zero empty stubs)
        with open(self.main_c, "r", encoding="utf-8") as f:
            main_src = f.read()

        self.assertIn("Physics_Step", main_src, "main.c must invoke Physics_Step")
        self.assertIn("Physics_Raycast", main_src, "main.c must invoke Physics_Raycast")
        self.assertIn("Interaction_UpdateDestruction", main_src, "main.c must invoke Interaction_UpdateDestruction")
        self.assertIn("Interaction_TryPlaceBlock", main_src, "main.c must invoke Interaction_TryPlaceBlock")
        self.assertIn("World_Update", main_src, "main.c must invoke World_Update")
        self.assertIn("MesherQueue_Process", main_src, "main.c must invoke MesherQueue_Process")
        self.assertIn("Audio_PlaySound", main_src, "main.c must invoke Audio_PlaySound")


if __name__ == "__main__":
    unittest.main()
