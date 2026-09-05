"""
Canonical Specification Models & Invariant Oracles for Minecraft Desktop E2E Tests.
Derived strictly from ORIGINAL_REQUEST.md, PROJECT.md, and docs/01 through docs/06.
Pure Python 3 standard library implementation.
"""

import math
from typing import List, Tuple, Optional, Dict, Set, Callable


# ============================================================================
# 1. KINEMATIC & COLLISION SYSTEM
# ============================================================================

class AABB:
    """Axis-Aligned Bounding Box."""
    def __init__(self, min_x: float, min_y: float, min_z: float,
                 max_x: float, max_y: float, max_z: float):
        self.min_x = min_x
        self.min_y = min_y
        self.min_z = min_z
        self.max_x = max_x
        self.max_y = max_y
        self.max_z = max_z

    def intersects(self, other: 'AABB', epsilon: float = 1e-6) -> bool:
        """Strict intersection test (exclusive of tangential touching)."""
        return (self.min_x < other.max_x - epsilon and self.max_x > other.min_x + epsilon and
                self.min_y < other.max_y - epsilon and self.max_y > other.min_y + epsilon and
                self.min_z < other.max_z - epsilon and self.max_z > other.min_z + epsilon)

    def contains_point(self, x: float, y: float, z: float) -> bool:
        return (self.min_x <= x <= self.max_x and
                self.min_y <= y <= self.max_y and
                self.min_z <= z <= self.max_z)

    def offset(self, dx: float, dy: float, dz: float) -> 'AABB':
        return AABB(self.min_x + dx, self.min_y + dy, self.min_z + dz,
                    self.max_x + dx, self.max_y + dy, self.max_z + dz)

    def __repr__(self) -> str:
        return f"AABB(({self.min_x:.3f}, {self.min_y:.3f}, {self.min_z:.3f}) -> ({self.max_x:.3f}, {self.max_y:.3f}, {self.max_z:.3f}))"


class Kinematics:
    """Canonical kinematic constants and equations from docs/02 and docs/06."""
    PLAYER_WIDTH = 0.6
    PLAYER_HEIGHT_STANDING = 1.8
    PLAYER_HEIGHT_SNEAKING = 1.5
    EYE_LEVEL_STANDING = 1.62
    EYE_LEVEL_SNEAKING = 1.35
    STEP_HEIGHT = 0.55
    GRAVITY = -32.0  # m/s^2 (at 60Hz: -0.5333 m/s per tick)
    TERMINAL_VELOCITY = -78.4  # m/s
    JUMP_IMPULSE = 8.944  # m/s (clears >= 1.25m)
    
    BASE_WALK_SPEED = 4.317  # m/s
    SPRINT_SPEED = 5.612  # m/s (1.30x walk)
    SNEAK_SPEED = 1.295  # m/s (0.30x walk)

    GROUND_FRICTION_FACTOR = 0.546  # Minecraft 0.6 * 0.91
    AIR_DRAG_FACTOR = 0.98

    @staticmethod
    def get_player_aabb(x: float, y: float, z: float, is_sneaking: bool = False) -> AABB:
        half_w = Kinematics.PLAYER_WIDTH * 0.5
        height = Kinematics.PLAYER_HEIGHT_SNEAKING if is_sneaking else Kinematics.PLAYER_HEIGHT_STANDING
        return AABB(x - half_w, y, z - half_w,
                    x + half_w, y + height, z + half_w)


class VoxelPhysicsController:
    """
    Simulates the axis-decoupled (Y -> X -> Z) voxel collision and movement solver
    as specified in docs/02 §4.
    """
    def __init__(self, x: float = 0.0, y: float = 64.0, z: float = 0.0):
        self.x = x
        self.y = y
        self.z = z
        self.vx = 0.0
        self.vy = 0.0
        self.vz = 0.0
        self.is_grounded = False
        self.is_sneaking = False
        self.is_sprinting = False

    def get_aabb(self) -> AABB:
        return Kinematics.get_player_aabb(self.x, self.y, self.z, self.is_sneaking)

    def tick(self, dt: float, wish_dir: Tuple[float, float, float],
             jump_requested: bool,
             is_solid_voxel: Callable[[int, int, int], bool]):
        """Executes a single fixed-timestep physics tick."""
        # 1. Target horizontal velocity
        if self.is_sneaking:
            base_speed = Kinematics.SNEAK_SPEED
        elif self.is_sprinting:
            base_speed = Kinematics.SPRINT_SPEED
        else:
            base_speed = Kinematics.BASE_WALK_SPEED

        wx, wy, wz = wish_dir
        target_vx = wx * base_speed
        target_vz = wz * base_speed

        accel_rate = 15.0 if self.is_grounded else 4.0
        blend = min(accel_rate * dt, 1.0)
        self.vx += (target_vx - self.vx) * blend
        self.vz += (target_vz - self.vz) * blend

        # 2. Jump & Gravity
        if jump_requested and self.is_grounded:
            self.vy = Kinematics.JUMP_IMPULSE
            self.is_grounded = False

        self.vy += Kinematics.GRAVITY * dt
        if self.vy < Kinematics.TERMINAL_VELOCITY:
            self.vy = Kinematics.TERMINAL_VELOCITY

        # 3. Compute displacement
        dx = self.vx * dt
        dy = self.vy * dt
        dz = self.vz * dt

        # 4. Sneak Ledge-Falloff Clamp
        if self.is_sneaking and self.is_grounded:
            dx, dz = self._apply_ledge_clamp(dx, dz, is_solid_voxel)

        # 5. Collision: Y-Axis (Vertical) with Anti-Tunneling Sub-Step
        self.is_grounded = False
        self._resolve_axis_with_substepping(1, dy, is_solid_voxel)

        # 6. Collision: Horizontal with Auto-Stepping
        self._resolve_horizontal_with_step(dx, dz, is_solid_voxel)

    def _resolve_axis_with_substepping(self, axis: int, delta: float,
                                       is_solid: Callable[[int, int, int], bool]):
        """
        Anti-tunneling guarantee: if |delta| > 0.5 blocks (e.g. falling at terminal velocity
        where delta = -78.4 * (1/60) = -1.306m), sub-step the displacement to ensure
        the AABB sweeps continuously across intermediate voxels without skipping.
        """
        step_limit = 0.5
        total_dist = abs(delta)
        if total_dist < 1e-7:
            return

        steps = max(1, math.ceil(total_dist / step_limit))
        step_delta = delta / steps

        for _ in range(steps):
            hit = self._resolve_axis(axis, step_delta, is_solid)
            if hit:
                break

    def _resolve_axis(self, axis: int, delta: float,
                      is_solid: Callable[[int, int, int], bool]) -> bool:
        if abs(delta) < 1e-7:
            return False

        if axis == 0:
            self.x += delta
        elif axis == 1:
            self.y += delta
        elif axis == 2:
            self.z += delta

        box = self.get_aabb()
        min_x = math.floor(box.min_x)
        max_x = math.floor(box.max_x)
        min_y = math.floor(box.min_y)
        max_y = math.floor(box.max_y)
        min_z = math.floor(box.min_z)
        max_z = math.floor(box.max_z)

        hit = False
        for bx in range(min_x, max_x + 1):
            for by in range(min_y, max_y + 1):
                for bz in range(min_z, max_z + 1):
                    if not is_solid(bx, by, bz):
                        continue
                    if hasattr(is_solid, 'get_aabb'):
                        block_box = is_solid.get_aabb(bx, by, bz)
                    else:
                        block_box = AABB(bx, by, bz, bx + 1.0, by + 1.0, bz + 1.0)
                    if box.intersects(block_box):
                        hit = True
                        if axis == 1:  # Y-Axis
                            if delta > 0.0:  # Head bump
                                self.y = block_box.min_y - (box.max_y - box.min_y)
                                self.vy = 0.0
                            else:  # Floor landing
                                self.y = block_box.max_y
                                self.vy = 0.0
                                self.is_grounded = True
                        elif axis == 0:  # X-Axis
                            if delta > 0.0:
                                self.x = block_box.min_x - Kinematics.PLAYER_WIDTH * 0.5
                            else:
                                self.x = block_box.max_x + Kinematics.PLAYER_WIDTH * 0.5
                            self.vx = 0.0
                        elif axis == 2:  # Z-Axis
                            if delta > 0.0:
                                self.z = block_box.min_z - Kinematics.PLAYER_WIDTH * 0.5
                            else:
                                self.z = block_box.max_z + Kinematics.PLAYER_WIDTH * 0.5
                            self.vz = 0.0
                        box = self.get_aabb()
        return hit

    def _resolve_horizontal_with_step(self, dx: float, dz: float,
                                      is_solid: Callable[[int, int, int], bool]):
        initial_x = self.x
        initial_z = self.z
        initial_y = self.y

        # Standard flat resolution
        self._resolve_axis(0, dx, is_solid)
        self._resolve_axis(2, dz, is_solid)

        flat_blocked = (abs(self.x - (initial_x + dx)) > 1e-4) or (abs(self.z - (initial_z + dz)) > 1e-4)

        if flat_blocked and self.is_grounded:
            flat_x = self.x
            flat_z = self.z

            # Revert to start and attempt auto-step
            self.x = initial_x
            self.y = initial_y
            self.z = initial_z

            # 1. Speculative upward probe
            head_bump = self._resolve_axis(1, Kinematics.STEP_HEIGHT, is_solid)
            if not head_bump:
                # 2. Horizontal sweep at elevated height
                self._resolve_axis(0, dx, is_solid)
                self._resolve_axis(2, dz, is_solid)

                # 3. Snap down to floor
                self._resolve_axis(1, -Kinematics.STEP_HEIGHT, is_solid)

                dist_sq_flat = (flat_x - initial_x)**2 + (flat_z - initial_z)**2
                dist_sq_step = (self.x - initial_x)**2 + (self.z - initial_z)**2

                if dist_sq_step <= dist_sq_flat + 1e-4:
                    # Stepping yielded no progress; revert to flat
                    self.x = flat_x
                    self.y = initial_y
                    self.z = flat_z
            else:
                # Ceiling collision aborted auto-step
                self.x = flat_x
                self.y = initial_y
                self.z = flat_z

    def _apply_ledge_clamp(self, dx: float, dz: float,
                           is_solid: Callable[[int, int, int], bool]) -> Tuple[float, float]:
        """Sneak ledge-falloff prevention: clamps dx/dz if no ground support beneath."""
        clamped_dx = dx
        clamped_dz = dz

        if abs(dx) > 1e-7:
            probe_x = self.x + dx
            if not self._has_ground_support(probe_x, self.y, self.z, is_solid):
                clamped_dx = 0.0

        if abs(dz) > 1e-7:
            probe_z = self.z + dz
            if not self._has_ground_support(self.x, self.y, probe_z, is_solid):
                clamped_dz = 0.0

        return clamped_dx, clamped_dz

    def _has_ground_support(self, x: float, y: float, z: float,
                            is_solid: Callable[[int, int, int], bool]) -> bool:
        """Probes a downward layer under player feet [-0.1m] for solid voxels."""
        half_w = Kinematics.PLAYER_WIDTH * 0.5
        box = AABB(x - half_w, y - 0.1, z - half_w,
                   x + half_w, y, z + half_w)
        min_x = math.floor(box.min_x)
        max_x = math.floor(box.max_x)
        min_z = math.floor(box.min_z)
        max_z = math.floor(box.max_z)
        probe_y = math.floor(y - 0.1)

        for bx in range(min_x, max_x + 1):
            for bz in range(min_z, max_z + 1):
                if is_solid(bx, probe_y, bz):
                    return True
        return False


# ============================================================================
# 2. AMANATIDES-WOO FAST VOXEL TRAVERSAL (DDA RAYCAST)
# ============================================================================

class RaycastHit:
    def __init__(self, hit: bool,
                 target_block: Tuple[int, int, int] = (0, 0, 0),
                 place_block: Tuple[int, int, int] = (0, 0, 0),
                 face_normal: Tuple[int, int, int] = (0, 0, 0),
                 distance: float = 0.0):
        self.hit = hit
        self.target_block = target_block
        self.place_block = place_block
        self.face_normal = face_normal
        self.distance = distance

    def __repr__(self) -> str:
        if not self.hit:
            return "RaycastHit(miss)"
        return (f"RaycastHit(target={self.target_block}, normal={self.face_normal}, "
                f"place={self.place_block}, dist={self.distance:.3f})")


def fast_voxel_traversal(
    ray_origin: Tuple[float, float, float],
    ray_dir: Tuple[float, float, float],
    max_reach: float,
    is_solid_voxel: Callable[[int, int, int], bool]
) -> RaycastHit:
    """
    Exact Amanatides-Woo DDA algorithm conforming to docs/02 §3.
    """
    x0, y0, z0 = ray_origin
    dx, dy, dz = ray_dir

    length = math.sqrt(dx * dx + dy * dy + dz * dz)
    if length > 1e-9:
        dx /= length
        dy /= length
        dz /= length
    else:
        return RaycastHit(False)

    x = math.floor(x0)
    y = math.floor(y0)
    z = math.floor(z0)

    # If starting block is solid
    if is_solid_voxel(x, y, z):
        return RaycastHit(
            hit=True,
            target_block=(x, y, z),
            place_block=(x, y + 1, z),
            face_normal=(0, 1, 0),
            distance=0.0
        )

    step_x = 1 if dx > 0 else (-1 if dx < 0 else 0)
    step_y = 1 if dy > 0 else (-1 if dy < 0 else 0)
    step_z = 1 if dz > 0 else (-1 if dz < 0 else 0)

    inf = float('inf')
    t_delta_x = abs(1.0 / dx) if step_x != 0 else inf
    t_delta_y = abs(1.0 / dy) if step_y != 0 else inf
    t_delta_z = abs(1.0 / dz) if step_z != 0 else inf

    t_max_x = ((math.floor(x0) + 1.0 - x0) * t_delta_x) if step_x > 0 else ((x0 - math.floor(x0)) * t_delta_x) if step_x < 0 else inf
    t_max_y = ((math.floor(y0) + 1.0 - y0) * t_delta_y) if step_y > 0 else ((y0 - math.floor(y0)) * t_delta_y) if step_y < 0 else inf
    t_max_z = ((math.floor(z0) + 1.0 - z0) * t_delta_z) if step_z > 0 else ((z0 - math.floor(z0)) * t_delta_z) if step_z < 0 else inf

    current_t = 0.0
    face_normal = (0, 0, 0)

    while current_t <= max_reach:
        if t_max_x < t_max_y:
            if t_max_x < t_max_z:
                current_t = t_max_x
                t_max_x += t_delta_x
                x += step_x
                face_normal = (-step_x, 0, 0)
            else:
                current_t = t_max_z
                t_max_z += t_delta_z
                z += step_z
                face_normal = (0, 0, -step_z)
        else:
            if t_max_y < t_max_z:
                current_t = t_max_y
                t_max_y += t_delta_y
                y += step_y
                face_normal = (0, -step_y, 0)
            else:
                current_t = t_max_z
                t_max_z += t_delta_z
                z += step_z
                face_normal = (0, 0, -step_z)

        if current_t > max_reach:
            break

        if is_solid_voxel(x, y, z):
            place_pos = (x + face_normal[0], y + face_normal[1], z + face_normal[2])
            return RaycastHit(
                hit=True,
                target_block=(x, y, z),
                place_block=place_pos,
                face_normal=face_normal,
                distance=current_t
            )

    return RaycastHit(False)


# ============================================================================
# 3. COORDINATE TRANSFORMS & CHUNK MATH
# ============================================================================

class CoordinateMath:
    """Canonical coordinate transformations as specified in docs/03 §2.4."""

    @staticmethod
    def world_to_chunk_coord(world_coord: int) -> int:
        """Floored division by 16 preserving negative two's complement."""
        return world_coord >> 4

    @staticmethod
    def world_to_local_coord(world_coord: int) -> int:
        """Local voxel coordinate in [0, 15] across negative and positive realms."""
        return world_coord & 15

    @staticmethod
    def chunk_voxel_index(lx: int, ly: int, lz: int) -> int:
        """Y-internal flat chunk indexing: Index = y + 256*x + 4096*z."""
        assert 0 <= lx < 16 and 0 <= ly < 256 and 0 <= lz < 16
        return ly + (lx * 256) + (lz * 4096)


# ============================================================================
# 4. INVENTORY & ITEM STACK
# ============================================================================

class ItemID:
    AIR = 0
    STONE = 1
    DIRT = 2
    GRASS_BLOCK = 3
    COBBLESTONE = 4
    WOOD_LOG = 5
    WOOD_PLANKS = 6
    STICK = 7
    CRAFTING_TABLE = 8
    FURNACE = 9
    COAL = 10
    TORCH = 11
    WOODEN_PICKAXE = 12
    STONE_PICKAXE = 13
    IRON_PICKAXE = 14
    IRON_INGOT = 15
    BEDROCK = 16


class ItemStack:
    def __init__(self, item_id: int = ItemID.AIR, count: int = 0,
                 max_stack: int = 64, durability: int = 0):
        self.item_id = item_id
        self.count = count if item_id != ItemID.AIR else 0
        self.max_stack = max_stack
        self.durability = durability

    def is_empty(self) -> bool:
        return self.item_id == ItemID.AIR or self.count <= 0

    def copy(self) -> 'ItemStack':
        return ItemStack(self.item_id, self.count, self.max_stack, self.durability)

    def can_stack_with(self, other: 'ItemStack') -> bool:
        if self.is_empty() or other.is_empty():
            return True
        return (self.item_id == other.item_id and
                self.max_stack > 1 and
                other.max_stack > 1 and
                self.durability == other.durability)

    def __repr__(self) -> str:
        if self.is_empty():
            return "Empty"
        return f"Item({self.item_id}, x{self.count}, max={self.max_stack})"


def get_default_max_stack(item_id: int) -> int:
    """Canonical stack size hierarchy: 1 (tools), 16 (compact), 64 (blocks/items)."""
    if item_id in (ItemID.WOODEN_PICKAXE, ItemID.STONE_PICKAXE, ItemID.IRON_PICKAXE):
        return 1
    return 64


def get_default_durability(item_id: int) -> int:
    if item_id == ItemID.WOODEN_PICKAXE:
        return 59
    if item_id == ItemID.STONE_PICKAXE:
        return 131
    if item_id == ItemID.IRON_PICKAXE:
        return 250
    return 0


class InventoryModel:
    """
    41-slot flat inventory layout:
    0..8: Hotbar (9 slots)
    9..35: Main storage (27 slots)
    36..39: Armor (4 slots)
    40: Offhand (1 slot)
    """
    HOTBAR_SIZE = 9
    MAIN_SIZE = 27
    ARMOR_SIZE = 4
    OFFHAND_SIZE = 1
    TOTAL_SLOTS = 41

    def __init__(self):
        self.slots: List[ItemStack] = [ItemStack() for _ in range(self.TOTAL_SLOTS)]
        self.selected_hotbar_slot: int = 0
        self.cursor_item: ItemStack = ItemStack()

    def select_hotbar(self, index: int):
        self.selected_hotbar_slot = index % self.HOTBAR_SIZE

    def scroll_hotbar(self, scroll_delta: int):
        self.selected_hotbar_slot = (self.selected_hotbar_slot - scroll_delta) % self.HOTBAR_SIZE

    def get_selected_item(self) -> ItemStack:
        return self.slots[self.selected_hotbar_slot]

    def add_item(self, item: ItemStack) -> int:
        """
        Adds item into inventory (hotbar first, then main).
        Returns count of remaining items that could not fit.
        """
        if item.is_empty():
            return 0

        rem = item.count
        max_stk = item.max_stack if item.max_stack > 0 else get_default_max_stack(item.item_id)

        # 1. Fill existing matching stacks
        if max_stk > 1:
            for idx in range(self.HOTBAR_SIZE + self.MAIN_SIZE):
                slot = self.slots[idx]
                if slot.item_id == item.item_id and slot.count < max_stk:
                    space = max_stk - slot.count
                    to_add = min(space, rem)
                    slot.count += to_add
                    rem -= to_add
                    if rem == 0:
                        return 0

        # 2. Put into empty slots
        for idx in range(self.HOTBAR_SIZE + self.MAIN_SIZE):
            slot = self.slots[idx]
            if slot.is_empty():
                to_add = min(max_stk, rem)
                self.slots[idx] = ItemStack(item.item_id, to_add, max_stk, item.durability)
                rem -= to_add
                if rem == 0:
                    return 0

        return rem

    def mouse_click_slot(self, slot_idx: int, is_right_click: bool = False):
        """Standard mouse interaction with slot."""
        assert 0 <= slot_idx < self.TOTAL_SLOTS
        slot = self.slots[slot_idx]

        if not is_right_click:
            # Left Click: Pickup, Place, or Swap
            if self.cursor_item.is_empty():
                if not slot.is_empty():
                    self.cursor_item = slot.copy()
                    self.slots[slot_idx] = ItemStack()
            else:
                if slot.is_empty():
                    self.slots[slot_idx] = self.cursor_item.copy()
                    self.cursor_item = ItemStack()
                elif slot.item_id == self.cursor_item.item_id and slot.max_stack > 1:
                    space = slot.max_stack - slot.count
                    to_add = min(space, self.cursor_item.count)
                    slot.count += to_add
                    self.cursor_item.count -= to_add
                    if self.cursor_item.count == 0:
                        self.cursor_item = ItemStack()
                else:
                    # Swap
                    self.cursor_item, self.slots[slot_idx] = slot.copy(), self.cursor_item.copy()
        else:
            # Right Click: Place single item or split slot
            if self.cursor_item.is_empty():
                if not slot.is_empty():
                    # Pick up half
                    half = math.ceil(slot.count / 2.0)
                    rem = slot.count - half
                    self.cursor_item = ItemStack(slot.item_id, half, slot.max_stack, slot.durability)
                    slot.count = rem
                    if slot.count == 0:
                        self.slots[slot_idx] = ItemStack()
            else:
                # Place 1 item from cursor into slot
                if slot.is_empty():
                    self.slots[slot_idx] = ItemStack(self.cursor_item.item_id, 1,
                                                     self.cursor_item.max_stack, self.cursor_item.durability)
                    self.cursor_item.count -= 1
                    if self.cursor_item.count == 0:
                        self.cursor_item = ItemStack()
                elif slot.item_id == self.cursor_item.item_id and slot.count < slot.max_stack:
                    slot.count += 1
                    self.cursor_item.count -= 1
                    if self.cursor_item.count == 0:
                        self.cursor_item = ItemStack()

    def shift_click_slot(self, slot_idx: int):
        """Quick transfer between hotbar and main inventory."""
        slot = self.slots[slot_idx]
        if slot.is_empty():
            return

        target_range = (range(self.HOTBAR_SIZE, self.HOTBAR_SIZE + self.MAIN_SIZE)
                        if slot_idx < self.HOTBAR_SIZE
                        else range(0, self.HOTBAR_SIZE))

        # First try to merge
        rem = slot.count
        if slot.max_stack > 1:
            for t in target_range:
                dest = self.slots[t]
                if dest.item_id == slot.item_id and dest.count < dest.max_stack:
                    space = dest.max_stack - dest.count
                    add = min(space, rem)
                    dest.count += add
                    rem -= add
                    if rem == 0:
                        self.slots[slot_idx] = ItemStack()
                        return

        # Then find first empty
        for t in target_range:
            dest = self.slots[t]
            if dest.is_empty():
                self.slots[t] = ItemStack(slot.item_id, rem, slot.max_stack, slot.durability)
                self.slots[slot_idx] = ItemStack()
                return

        slot.count = rem


# ============================================================================
# 5. CRAFTING SYSTEM (2x2 & 3x3)
# ============================================================================

class CraftingRecipe:
    def __init__(self, result: ItemStack, is_shaped: bool,
                 pattern: Optional[List[List[int]]] = None,
                 shapeless_ingredients: Optional[List[int]] = None):
        self.result = result
        self.is_shaped = is_shaped
        self.pattern = pattern or []
        self.shapeless_ingredients = sorted(shapeless_ingredients or [])


class CraftingEngine:
    def __init__(self):
        self.recipes: List[CraftingRecipe] = []
        self._init_canonical_recipes()

    def _init_canonical_recipes(self):
        # 1. Wood Log -> 4 Planks (shapeless)
        self.recipes.append(CraftingRecipe(
            result=ItemStack(ItemID.WOOD_PLANKS, 4),
            is_shaped=False,
            shapeless_ingredients=[ItemID.WOOD_LOG]
        ))
        # 2. 2 Planks vertical -> 4 Sticks (shaped 1x2)
        self.recipes.append(CraftingRecipe(
            result=ItemStack(ItemID.STICK, 4),
            is_shaped=True,
            pattern=[[ItemID.WOOD_PLANKS],
                     [ItemID.WOOD_PLANKS]]
        ))
        # 3. 4 Planks -> 1 Crafting Table (shaped 2x2)
        self.recipes.append(CraftingRecipe(
            result=ItemStack(ItemID.CRAFTING_TABLE, 1),
            is_shaped=True,
            pattern=[[ItemID.WOOD_PLANKS, ItemID.WOOD_PLANKS],
                     [ItemID.WOOD_PLANKS, ItemID.WOOD_PLANKS]]
        ))
        # 4. Wooden Pickaxe: 3 Planks top, 2 Sticks center (shaped 3x3)
        self.recipes.append(CraftingRecipe(
            result=ItemStack(ItemID.WOODEN_PICKAXE, 1, max_stack=1, durability=59),
            is_shaped=True,
            pattern=[[ItemID.WOOD_PLANKS, ItemID.WOOD_PLANKS, ItemID.WOOD_PLANKS],
                     [0, ItemID.STICK, 0],
                     [0, ItemID.STICK, 0]]
        ))
        # 5. Stone Pickaxe: 3 Cobble top, 2 Sticks center (shaped 3x3)
        self.recipes.append(CraftingRecipe(
            result=ItemStack(ItemID.STONE_PICKAXE, 1, max_stack=1, durability=131),
            is_shaped=True,
            pattern=[[ItemID.COBBLESTONE, ItemID.COBBLESTONE, ItemID.COBBLESTONE],
                     [0, ItemID.STICK, 0],
                     [0, ItemID.STICK, 0]]
        ))
        # 6. Iron Pickaxe: 3 Iron top, 2 Sticks center (shaped 3x3)
        self.recipes.append(CraftingRecipe(
            result=ItemStack(ItemID.IRON_PICKAXE, 1, max_stack=1, durability=250),
            is_shaped=True,
            pattern=[[ItemID.IRON_INGOT, ItemID.IRON_INGOT, ItemID.IRON_INGOT],
                     [0, ItemID.STICK, 0],
                     [0, ItemID.STICK, 0]]
        ))
        # 7. Furnace: 8 Cobblestone hollow ring (shaped 3x3)
        self.recipes.append(CraftingRecipe(
            result=ItemStack(ItemID.FURNACE, 1),
            is_shaped=True,
            pattern=[[ItemID.COBBLESTONE, ItemID.COBBLESTONE, ItemID.COBBLESTONE],
                     [ItemID.COBBLESTONE, 0, ItemID.COBBLESTONE],
                     [ItemID.COBBLESTONE, ItemID.COBBLESTONE, ItemID.COBBLESTONE]]
        ))
        # 8. Torches: 1 Coal + 1 Stick (shaped 1x2 or shapeless)
        self.recipes.append(CraftingRecipe(
            result=ItemStack(ItemID.TORCH, 4),
            is_shaped=False,
            shapeless_ingredients=[ItemID.COAL, ItemID.STICK]
        ))

    def match(self, grid: List[List[ItemStack]]) -> Optional[ItemStack]:
        """Matches a 2x2 or 3x3 grid against known recipes."""
        rows = len(grid)
        cols = len(grid[0]) if rows > 0 else 0

        # Extract non-empty bounding box for shaped matching
        min_r, max_r = rows, -1
        min_c, max_c = cols, -1
        non_empty_items = []

        for r in range(rows):
            for c in range(cols):
                item = grid[r][c]
                if not item.is_empty():
                    min_r = min(min_r, r)
                    max_r = max(max_r, r)
                    min_c = min(min_c, c)
                    max_c = max(max_c, c)
                    non_empty_items.append(item.item_id)

        if not non_empty_items:
            return None

        # 1. Try shapeless matching
        sorted_inputs = sorted(non_empty_items)
        for rec in self.recipes:
            if not rec.is_shaped and rec.shapeless_ingredients == sorted_inputs:
                return rec.result.copy()

        # 2. Try shaped matching
        sub_h = max_r - min_r + 1
        sub_w = max_c - min_c + 1
        subgrid = [[grid[r][c].item_id for c in range(min_c, max_c + 1)]
                   for r in range(min_r, max_r + 1)]

        for rec in self.recipes:
            if rec.is_shaped:
                pat_h = len(rec.pattern)
                pat_w = len(rec.pattern[0])
                if pat_h == sub_h and pat_w == sub_w:
                    if rec.pattern == subgrid:
                        return rec.result.copy()

        return None

    def craft(self, grid: List[List[ItemStack]]) -> Optional[ItemStack]:
        """Matches recipe, decrements 1 item from each occupied cell, and returns product."""
        res = self.match(grid)
        if res is None:
            return None

        for r in range(len(grid)):
            for c in range(len(grid[r])):
                if not grid[r][c].is_empty():
                    grid[r][c].count -= 1
                    if grid[r][c].count <= 0:
                        grid[r][c] = ItemStack()
        return res


# ============================================================================
# 6. PROCEDURAL AUDIO SYNTHESIZER
# ============================================================================

class AudioSynthesizer:
    SAMPLE_RATE = 44100

    @staticmethod
    def synthesize_ui_click() -> List[float]:
        """15ms, 2400 Hz square wave, linear decay."""
        duration = 0.015
        total_samples = int(duration * AudioSynthesizer.SAMPLE_RATE)
        samples = []
        freq = 2400.0
        for i in range(total_samples):
            t = i / AudioSynthesizer.SAMPLE_RATE
            phase = (freq * t) % 1.0
            square = 1.0 if phase < 0.5 else -1.0
            envelope = 1.0 - (i / total_samples)
            samples.append(square * envelope)
        return samples

    @staticmethod
    def synthesize_footstep() -> List[float]:
        """40ms, LFSR noise + 80Hz thump, exponential decay (lambda=65)."""
        duration = 0.040
        total_samples = int(duration * AudioSynthesizer.SAMPLE_RATE)
        samples = []
        lfsr = 0xACE1
        for i in range(total_samples):
            t = i / AudioSynthesizer.SAMPLE_RATE
            bit = ((lfsr >> 0) ^ (lfsr >> 2) ^ (lfsr >> 3) ^ (lfsr >> 5)) & 1
            lfsr = (lfsr >> 1) | (bit << 15)
            noise = (lfsr / 32767.5) - 1.0
            thump_phase = (80.0 * t) % 1.0
            thump = 4.0 * abs(thump_phase - 0.5) - 1.0
            env = math.exp(-65.0 * t)
            samples.append((0.7 * noise + 0.3 * thump) * env)
        return samples

    @staticmethod
    def synthesize_jump() -> List[float]:
        """90ms, 25% duty square sweep 140->560 Hz, linear attack/decay."""
        duration = 0.090
        total_samples = int(duration * AudioSynthesizer.SAMPLE_RATE)
        samples = []
        phase = 0.0
        for i in range(total_samples):
            t = i / AudioSynthesizer.SAMPLE_RATE
            f_t = 140.0 + (420.0 * (t / duration))
            phase = (phase + f_t / AudioSynthesizer.SAMPLE_RATE) % 1.0
            sq = 1.0 if phase < 0.25 else -1.0
            # 5ms attack, 85ms decay
            if t < 0.005:
                env = t / 0.005
            else:
                env = 1.0 - ((t - 0.005) / 0.085)
            samples.append(sq * env)
        return samples

    @staticmethod
    def synthesize_block_break() -> List[float]:
        """160ms, LFSR noise + pitch-falling square subharmonic (120 Hz)."""
        duration = 0.160
        total_samples = int(duration * AudioSynthesizer.SAMPLE_RATE)
        samples = []
        lfsr = 0x1337
        phase = 0.0
        for i in range(total_samples):
            t = i / AudioSynthesizer.SAMPLE_RATE
            bit = ((lfsr >> 0) ^ (lfsr >> 2) ^ (lfsr >> 3) ^ (lfsr >> 5)) & 1
            lfsr = (lfsr >> 1) | (bit << 15)
            noise = (lfsr / 32767.5) - 1.0
            f_sub = 120.0 * (1.0 - t / duration)
            phase = (phase + f_sub / AudioSynthesizer.SAMPLE_RATE) % 1.0
            sq = 1.0 if phase < 0.5 else -1.0
            env = max(0.0, 1.0 - (t / duration)**0.7)
            samples.append((0.85 * noise + 0.15 * sq) * env)
        return samples

    @staticmethod
    def synthesize_block_place() -> List[float]:
        """50ms, triangle wave with pitch plummet f(t)=220*2^(-25t), exp decay."""
        duration = 0.050
        total_samples = int(duration * AudioSynthesizer.SAMPLE_RATE)
        samples = []
        phase = 0.0
        for i in range(total_samples):
            t = i / AudioSynthesizer.SAMPLE_RATE
            f_t = 220.0 * (2.0 ** (-25.0 * t))
            phase = (phase + f_t / AudioSynthesizer.SAMPLE_RATE) % 1.0
            tri = 4.0 * abs(phase - 0.5) - 1.0
            env = math.exp(-50.0 * t)
            samples.append(tri * env)
        return samples


# ============================================================================
# 7. SURVIVAL, HUNGER & COMBAT
# ============================================================================

class PlayerSurvivalState:
    MAX_HEALTH = 20.0
    MAX_HUNGER = 20.0
    MAX_SATURATION = 20.0

    def __init__(self):
        self.health: float = self.MAX_HEALTH
        self.hunger: float = self.MAX_HUNGER
        self.saturation: float = 5.0
        self.exhaustion: float = 0.0
        self.is_alive: bool = True

    def add_exhaustion(self, amount: float):
        self.exhaustion += amount
        while self.exhaustion >= 4.0:
            self.exhaustion -= 4.0
            if self.saturation > 0.0:
                self.saturation = max(0.0, self.saturation - 1.0)
            elif self.hunger > 0.0:
                self.hunger = max(0.0, self.hunger - 1.0)

    def can_sprint(self) -> bool:
        return self.hunger > 6.0 and self.is_alive

    def apply_fall_damage(self, fall_distance: float, in_water: bool = False):
        if in_water or fall_distance <= 3.0:
            return
        damage = math.ceil(fall_distance - 3.0)
        self.take_damage(damage)

    def take_damage(self, damage: float):
        self.health = max(0.0, self.health - damage)
        if self.health <= 0.0:
            self.is_alive = False

    def respawn(self):
        self.health = self.MAX_HEALTH
        self.hunger = self.MAX_HUNGER
        self.saturation = 5.0
        self.exhaustion = 0.0
        self.is_alive = True
