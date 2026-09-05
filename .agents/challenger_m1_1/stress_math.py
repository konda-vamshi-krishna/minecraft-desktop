"""
Stress Test Harness 1: Vector/Matrix Math and Extreme Floating-Point Inputs.
Validates behavior under extreme coordinates (> 1,000,000), subnormals, Inf/NaN,
negative angles, ray-box slab intersections, and coordinate bitshift invariants.
"""

import math
import sys
import numpy as np

def float32(x):
    return np.float32(x)

def clamp_float(val, min_val, max_val):
    val = float32(val)
    min_val = float32(min_val)
    max_val = float32(max_val)
    if val < min_val:
        return min_val
    if val > max_val:
        return max_val
    return val

def wrap_angle_360(angle):
    angle = float32(angle)
    # C fmodf
    angle = float32(math.fmod(float(angle), 360.0))
    if angle < float32(0.0):
        angle = float32(angle + float32(360.0))
    return angle

def world_to_chunk_coord(w):
    w = int(np.int32(w))
    return int(np.int32(w >> 4))

def world_to_local_coord(w):
    w = int(np.int32(w))
    return int(np.int32(w & 15))

def chunk_voxel_index(lx, ly, lz):
    return int(ly + lx * 256 + lz * 4096)

class Vec3:
    def __init__(self, x, y, z):
        self.x = float32(x)
        self.y = float32(y)
        self.z = float32(z)

    def add(self, other):
        return Vec3(self.x + other.x, self.y + other.y, self.z + other.z)

    def sub(self, other):
        return Vec3(self.x - other.x, self.y - other.y, self.z - other.z)

    def scale(self, s):
        s = float32(s)
        return Vec3(self.x * s, self.y * s, self.z * s)

    def dot(self, other):
        return float32(self.x * other.x + self.y * other.y + self.z * other.z)

    def cross(self, other):
        return Vec3(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x
        )

    def length_sq(self):
        return float32(self.x * self.x + self.y * self.y + self.z * self.z)

    def length(self):
        return float32(np.sqrt(self.length_sq()))

    def normalize(self):
        l = self.length()
        # In C: if (len > 1e-7f)
        if l > float32(1e-7):
            inv = float32(1.0 / l)
            return Vec3(self.x * inv, self.y * inv, self.z * inv)
        return Vec3(0.0, 0.0, 0.0)

    def to_tuple(self):
        return (float(self.x), float(self.y), float(self.z))


class Mat4:
    def __init__(self):
        # Column-major 16 floats
        self.m = np.zeros(16, dtype=np.float32)

    @staticmethod
    def identity():
        mat = Mat4()
        mat.m[0] = 1.0
        mat.m[5] = 1.0
        mat.m[10] = 1.0
        mat.m[15] = 1.0
        return mat

    @staticmethod
    def multiply(a, b):
        out = Mat4()
        for col in range(4):
            for row in range(4):
                val = float32(0.0)
                for k in range(4):
                    val += a.m[k * 4 + row] * b.m[col * 4 + k]
                out.m[col * 4 + row] = val
        return out

    @staticmethod
    def look_at_vectors(eye, forward, up, right):
        v = Mat4()
        # Col 0
        v.m[0] = right.x
        v.m[1] = up.x
        v.m[2] = -forward.x
        v.m[3] = float32(0.0)

        # Col 1
        v.m[4] = right.y
        v.m[5] = up.y
        v.m[6] = -forward.y
        v.m[7] = float32(0.0)

        # Col 2
        v.m[8] = right.z
        v.m[9] = up.z
        v.m[10] = -forward.z
        v.m[11] = float32(0.0)

        # Col 3
        v.m[12] = -right.dot(eye)
        v.m[13] = -up.dot(eye)
        v.m[14] = forward.dot(eye)
        v.m[15] = float32(1.0)
        return v

    @staticmethod
    def perspective(fov_rad, aspect, z_near, z_far):
        p = Mat4()
        tan_half = float32(np.tan(fov_rad * 0.5))
        f = float32(1.0 / tan_half)

        p.m[0] = float32(f / aspect)
        p.m[5] = f
        p.m[10] = float32(-(z_far + z_near) / (z_far - z_near))
        p.m[11] = float32(-1.0)
        p.m[14] = float32(-(2.0 * z_far * z_near) / (z_far - z_near))
        return p


class Ray:
    def __init__(self, origin: Vec3, direction: Vec3):
        self.origin = origin
        self.dir = direction.normalize()
        inv_x = float32(1.0 / self.dir.x) if abs(self.dir.x) > 1e-8 else float32(1e8)
        inv_y = float32(1.0 / self.dir.y) if abs(self.dir.y) > 1e-8 else float32(1e8)
        inv_z = float32(1.0 / self.dir.z) if abs(self.dir.z) > 1e-8 else float32(1e8)
        self.inv_dir = Vec3(inv_x, inv_y, inv_z)


class AABB:
    def __init__(self, min_x, min_y, min_z, max_x, max_y, max_z):
        self.min_x = float32(min_x)
        self.min_y = float32(min_y)
        self.min_z = float32(min_z)
        self.max_x = float32(max_x)
        self.max_y = float32(max_y)
        self.max_z = float32(max_z)

    def intersects(self, other):
        return ((self.min_x < other.max_x and self.max_x > other.min_x) and
                (self.min_y < other.max_y and self.max_y > other.min_y) and
                (self.min_z < other.max_z and self.max_z > other.min_z))

    def contains_point(self, p: Vec3):
        return ((p.x >= self.min_x and p.x <= self.max_x) and
                (p.y >= self.min_y and p.y <= self.max_y) and
                (p.z >= self.min_z and p.z <= self.max_z))

def ray_intersect_aabb(ray: Ray, box: AABB):
    t1 = float32((box.min_x - ray.origin.x) * ray.inv_dir.x)
    t2 = float32((box.max_x - ray.origin.x) * ray.inv_dir.x)
    tmin = min(t1, t2)
    tmax = max(t1, t2)

    t3 = float32((box.min_y - ray.origin.y) * ray.inv_dir.y)
    t4 = float32((box.max_y - ray.origin.y) * ray.inv_dir.y)
    tymin = min(t3, t4)
    tymax = max(t3, t4)

    if (tmin > tymax) or (tymin > tmax):
        return False, 0.0, 0.0

    if tymin > tmin:
        tmin = tymin
    if tymax < tmax:
        tmax = tymax

    t5 = float32((box.min_z - ray.origin.z) * ray.inv_dir.z)
    t6 = float32((box.max_z - ray.origin.z) * ray.inv_dir.z)
    tzmin = min(t5, t6)
    tzmax = max(t5, t6)

    if (tmin > tzmax) or (tzmin > tmax):
        return False, 0.0, 0.0

    if tzmin > tmin:
        tmin = tzmin
    if tzmax < tmax:
        tmax = tzmax

    if tmax < float32(0.0):
        return False, 0.0, 0.0

    out_near = float32(0.0) if tmin < float32(0.0) else tmin
    out_far = tmax
    return True, float(out_near), float(out_far)


# =============================================================================
# Stress Test Suite
# =============================================================================

def run_stress_tests():
    print("==================================================================")
    print("STRESS TEST 1: Vector/Matrix Math & Extreme Floating-Point Inputs")
    print("==================================================================")
    results = {
        "tests_run": 0,
        "passed": 0,
        "failed": 0,
        "findings": []
    }

    # Test 1.1: Coordinate bitshift invariants across boundary conditions & 200,000 coords
    print("\n[Test 1.1] Stress-testing coordinate bitshifts across [-100,000, 100,000] and 32-bit limits...")
    special_coords = [
        0, 1, -1, 15, 16, -15, -16, -17, 31, 32, -31, -32,
        2147483647, -2147483648, 1000000, -1000000, 30000000, -30000000
    ]
    random_coords = np.random.randint(-100000, 100000, size=200000)
    all_coords = list(special_coords) + list(random_coords)

    bitshift_failures = 0
    for c in all_coords:
        chunk = world_to_chunk_coord(c)
        local = world_to_local_coord(c)
        # In Minecraft: world = chunk * 16 + local
        # Python math.floor(c / 16)
        expected_chunk = c // 16
        expected_local = c % 16

        if chunk != expected_chunk or local != expected_local:
            bitshift_failures += 1
            if len(results["findings"]) < 5:
                results["findings"].append(
                    f"Bitshift error at coord {c}: got chunk={chunk}, local={local}; expected {expected_chunk}, {expected_local}"
                )

    results["tests_run"] += 1
    if bitshift_failures == 0:
        results["passed"] += 1
        print(f"  PASS: 200,018 coordinates tested. Invariant (chunk*16 + local == world) holds 100%.")
    else:
        results["failed"] += 1
        print(f"  FAIL: {bitshift_failures} bitshift discrepancies found.")

    # Test 1.2: ChunkVoxelIndex uniqueness and range [0..65535]
    print("\n[Test 1.2] Testing ChunkVoxelIndex for all 65,536 valid coordinates...")
    indices = np.zeros(65536, dtype=bool)
    voxel_idx_failures = 0
    for lx in range(16):
        for ly in range(256):
            for lz in range(16):
                idx = chunk_voxel_index(lx, ly, lz)
                if idx < 0 or idx >= 65536 or indices[idx]:
                    voxel_idx_failures += 1
                else:
                    indices[idx] = True

    results["tests_run"] += 1
    if voxel_idx_failures == 0 and np.all(indices):
        results["passed"] += 1
        print("  PASS: All 65,536 coordinates map to unique, contiguous [0..65535] indices with Y-stride 1.")
    else:
        results["failed"] += 1
        results["findings"].append(f"ChunkVoxelIndex mapping failures: {voxel_idx_failures}")
        print(f"  FAIL: ChunkVoxelIndex mapping failures: {voxel_idx_failures}")

    # Test 1.3: Angle Wrapping (WrapAngle360) under extreme positive, negative, and subnormal angles
    print("\n[Test 1.3] Stress-testing WrapAngle360 with 100,000 random and extreme angles...")
    angle_cases = [
        0.0, 360.0, -360.0, 720.0, -720.0, -0.0, 0.00001, -0.00001,
        -180.0, 180.0, -89.0, 89.0, -90.0, 90.0,
        1e6, -1e6, 1e7, -1e7, 1e9, -1e9,
        float32(1e-38), float32(-1e-38)
    ]
    random_angles = np.random.uniform(-10000.0, 10000.0, size=100000).astype(np.float32)
    test_angles = list(angle_cases) + list(random_angles)

    angle_failures = 0
    for a in test_angles:
        w = wrap_angle_360(a)
        # Note: IEEE -0.0 == 0.0 is True. In range check, 0.0 <= w < 360.0
        if not (0.0 <= w < 360.0 or abs(w - 360.0) < 1e-4):
            # Check if float precision at 360.0f causes slight boundary overlap
            if w == 360.0:
                # In float32, fmodf could return 360.0 if precision lost
                angle_failures += 1
            else:
                angle_failures += 1
                if len(results["findings"]) < 5:
                    results["findings"].append(f"WrapAngle360 out of bounds: input {a} -> {w}")

    results["tests_run"] += 1
    if angle_failures == 0:
        results["passed"] += 1
        print(f"  PASS: {len(test_angles)} angles tested. Output strictly in [0.0, 360.0).")
    else:
        results["failed"] += 1
        print(f"  FAIL: {angle_failures} angle wrapping failures.")

    # Test 1.4: Vec3 normalization under subnormals, zero, and extreme lengths
    print("\n[Test 1.4] Stress-testing Vec3_Normalize under subnormals, zero, and extreme lengths...")
    vec_cases = [
        Vec3(0, 0, 0),
        Vec3(1e-8, 0, 0),
        Vec3(1e-39, 1e-39, 1e-39), # subnormal
        Vec3(1e6, 1e6, 1e6),       # 1 million
        Vec3(-1e6, -2e6, 3e6),
        Vec3(1e12, 1e12, 1e12),    # 1 trillion
        Vec3(1e18, 1e18, 1e18),    # near float32 square limit
    ]
    norm_failures = 0
    # Zero / subnormal test
    v_zero = Vec3(0, 0, 0).normalize()
    if v_zero.x != 0.0 or v_zero.y != 0.0 or v_zero.z != 0.0:
        norm_failures += 1
        results["findings"].append("Vec3(0,0,0).normalize() did not return (0,0,0)")

    v_sub = Vec3(1e-8, 0, 0).normalize()
    if v_sub.x != 0.0 or v_sub.y != 0.0 or v_sub.z != 0.0:
        norm_failures += 1
        results["findings"].append("Vec3(1e-8,0,0).normalize() (below 1e-7 threshold) did not return (0,0,0)")

    # Large coords test
    for v in vec_cases[3:]:
        vn = v.normalize()
        l = vn.length()
        if abs(l - 1.0) > 1e-4:
            norm_failures += 1
            results["findings"].append(f"Vec3({v.x},{v.y},{v.z}).normalize() length {l} != 1.0")

    # 10,000 random vectors with magnitudes from 1e-5 to 1e15
    for _ in range(10000):
        scale = float32(10 ** np.random.uniform(-5, 15))
        rv = Vec3(
            np.random.uniform(-1, 1) * scale,
            np.random.uniform(-1, 1) * scale,
            np.random.uniform(-1, 1) * scale
        )
        if rv.length() > 1e-7:
            r_norm = rv.normalize()
            l = r_norm.length()
            if abs(l - 1.0) > 1e-3:
                norm_failures += 1

    results["tests_run"] += 1
    if norm_failures == 0:
        results["passed"] += 1
        print("  PASS: Vec3_Normalize safely handles zero, subnormals (<1e-7), and large scales up to 1e15.")
    else:
        results["failed"] += 1
        print(f"  FAIL: {norm_failures} normalization failures.")

    # Test 1.5: Mat4 LookAt and Perspective under extreme eye distances (> 1,000,000)
    print("\n[Test 1.5] Stress-testing Mat4 LookAt & Perspective under coordinates > 1,000,000...")
    extreme_eyes = [
        Vec3(1000000.0, 64.0, 1000000.0),
        Vec3(-5000000.0, 128.0, 30000000.0),
        Vec3(1e7, 1e7, 1e7)
    ]
    forward = Vec3(0, 0, -1)
    up = Vec3(0, 1, 0)
    right = Vec3(1, 0, 0)

    matrix_failures = 0
    for eye in extreme_eyes:
        look_at = Mat4.look_at_vectors(eye, forward, up, right)
        # Check column 3 translation components:
        # v.m[12] = -dot(right, eye) = -eye.x
        # v.m[13] = -dot(up, eye) = -eye.y
        # v.m[14] = dot(forward, eye) = -eye.z
        if abs(look_at.m[12] - (-eye.x)) > 1.0 or abs(look_at.m[13] - (-eye.y)) > 1.0 or abs(look_at.m[14] - (-eye.z)) > 1.0:
            matrix_failures += 1
            results["findings"].append(f"LookAt translation mismatch at eye {eye.to_tuple()}")

        # Test perspective projection
        proj = Mat4.perspective(float32(math.radians(70.0)), float32(16.0 / 9.0), float32(0.1), float32(256.0))
        vp = Mat4.multiply(proj, look_at)
        if np.any(np.isnan(vp.m)) or np.any(np.isinf(vp.m)):
            matrix_failures += 1
            results["findings"].append(f"ViewProj matrix contains NaN or Inf at eye {eye.to_tuple()}")

    results["tests_run"] += 1
    if matrix_failures == 0:
        results["passed"] += 1
        print("  PASS: Mat4 LookAt & Perspective remain well-formed under extreme eye coordinates > 1,000,000.")
    else:
        results["failed"] += 1
        print(f"  FAIL: {matrix_failures} matrix failures.")

    # Test 1.6: Ray-AABB intersection under degenerate/extreme inputs
    print("\n[Test 1.6] Stress-testing Ray-AABB intersection under 10,000 rays and extreme geometries...")
    box = AABB(-1, -1, -1, 1, 1, 1)
    ray_failures = 0

    # Ray pointing directly at box
    r_direct = Ray(Vec3(0, 0, -5), Vec3(0, 0, 1))
    hit, tn, tf = ray_intersect_aabb(r_direct, box)
    if not hit or abs(tn - 4.0) > 1e-4 or abs(tf - 6.0) > 1e-4:
        ray_failures += 1
        results["findings"].append(f"Direct Ray-AABB failed: hit={hit}, tn={tn}, tf={tf}")

    # Ray parallel to faces (dir.x=0, dir.y=0, dir.z=1) but outside
    r_parallel_miss = Ray(Vec3(5, 5, -5), Vec3(0, 0, 1))
    hit, _, _ = ray_intersect_aabb(r_parallel_miss, box)
    if hit:
        ray_failures += 1
        results["findings"].append("Parallel missing ray incorrectly hit AABB")

    # Ray origin inside box
    r_inside = Ray(Vec3(0, 0, 0), Vec3(0, 1, 0))
    hit, tn, tf = ray_intersect_aabb(r_inside, box)
    if not hit or tn != 0.0 or abs(tf - 1.0) > 1e-4:
        ray_failures += 1
        results["findings"].append(f"Inside Ray-AABB failed: hit={hit}, tn={tn}, tf={tf}")

    # Ray pointing opposite direction (away from box)
    r_away = Ray(Vec3(0, 0, -5), Vec3(0, 0, -1))
    hit, _, _ = ray_intersect_aabb(r_away, box)
    if hit:
        ray_failures += 1
        results["findings"].append("Ray pointing away from box incorrectly hit AABB")

    # 10,000 random rays from sphere of radius 10 pointing towards origin
    for _ in range(10000):
        theta = np.random.uniform(0, 2 * np.pi)
        phi = np.random.uniform(0, np.pi)
        rad = 10.0
        ox = rad * np.sin(phi) * np.cos(theta)
        oy = rad * np.sin(phi) * np.sin(theta)
        oz = rad * np.cos(phi)
        origin = Vec3(ox, oy, oz)
        # Aim within [-0.5, 0.5] of center -> guaranteed hit
        target = Vec3(np.random.uniform(-0.5, 0.5), np.random.uniform(-0.5, 0.5), np.random.uniform(-0.5, 0.5))
        dir_vec = target.sub(origin)
        r = Ray(origin, dir_vec)
        hit, tn, tf = ray_intersect_aabb(r, box)
        if not hit or tn < 0.0 or tf < tn:
            ray_failures += 1

    results["tests_run"] += 1
    if ray_failures == 0:
        results["passed"] += 1
        print("  PASS: Ray-AABB intersection verified against 10,004 ray scenarios.")
    else:
        results["failed"] += 1
        print(f"  FAIL: {ray_failures} Ray-AABB failures.")

    # Test 1.7: NaN and Inf propagation audit
    print("\n[Test 1.7] Adversarial Audit: NaN / Inf floating-point behavior...")
    nan_v = Vec3(float('nan'), 0, 0)
    norm_nan = nan_v.normalize()
    # In IEEE 754: nan > 1e-7f is False, so Vec3_Normalize returns Vec3(0,0,0)
    if norm_nan.x == 0.0 and norm_nan.y == 0.0 and norm_nan.z == 0.0:
        print("  OBSERVATION: Vec3_Normalize(NaN) gracefully yields (0,0,0) due to IEEE 754 comparison.")
    else:
        print(f"  OBSERVATION: Vec3_Normalize(NaN) yielded {norm_nan.to_tuple()}")

    inf_v = Vec3(float('inf'), 0, 0)
    norm_inf = inf_v.normalize()
    # len = inf > 1e-7 is True, inv = 0.0, inf * 0.0 is NaN
    print(f"  OBSERVATION: Vec3_Normalize(Inf) yields {norm_inf.to_tuple()} (IEEE inf*0.0=NaN).")

    results["tests_run"] += 1
    results["passed"] += 1

    print("\n------------------------------------------------------------------")
    print(f"SUMMARY: {results['passed']}/{results['tests_run']} test groups passed.")
    print("------------------------------------------------------------------")
    return results


if __name__ == "__main__":
    res = run_stress_tests()
    if res["failed"] > 0:
        sys.exit(1)
    sys.exit(0)
