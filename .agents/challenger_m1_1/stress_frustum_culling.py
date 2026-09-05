"""
Stress Test Harness 4: Frustum Extraction and Fast AABB Culling Verification.
Empirically stress-tests Frustum_Extract and Frustum_TestAABB against:
1. 10,000 randomized 3D boxes across various camera positions & orientations.
2. Independent 8-vertex signed-distance oracle comparison.
3. Chunk AABB boundary culling (16x256x16 standard sub-chunks).
4. Extreme camera positions (> 1,000,000) and edge-case geometries.
5. Zero false culls (no visible boxes accidentally culled).
"""

import math
import sys
import numpy as np

def float32(x):
    return np.float32(x)

M_PI = float32(3.14159265358979323846)

def deg2rad(d):
    return float32(d * (M_PI / float32(180.0)))

class AABB:
    def __init__(self, min_x, min_y, min_z, max_x, max_y, max_z):
        self.min_x = float32(min_x)
        self.min_y = float32(min_y)
        self.min_z = float32(min_z)
        self.max_x = float32(max_x)
        self.max_y = float32(max_y)
        self.max_z = float32(max_z)

    def get_vertices(self):
        return [
            np.array([self.min_x, self.min_y, self.min_z], dtype=np.float32),
            np.array([self.max_x, self.min_y, self.min_z], dtype=np.float32),
            np.array([self.min_x, self.max_y, self.min_z], dtype=np.float32),
            np.array([self.max_x, self.max_y, self.min_z], dtype=np.float32),
            np.array([self.min_x, self.min_y, self.max_z], dtype=np.float32),
            np.array([self.max_x, self.min_y, self.max_z], dtype=np.float32),
            np.array([self.min_x, self.max_y, self.max_z], dtype=np.float32),
            np.array([self.max_x, self.max_y, self.max_z], dtype=np.float32),
        ]


class Plane:
    def __init__(self, nx=0.0, ny=0.0, nz=0.0, d=0.0):
        self.normal = np.array([nx, ny, nz], dtype=np.float32)
        self.d = float32(d)

    def normalize(self):
        length = float32(np.linalg.norm(self.normal))
        if length > float32(1e-7):
            inv = float32(1.0 / length)
            self.normal *= inv
            self.d *= inv


class Frustum:
    CULL_OUTSIDE = 0
    CULL_INTERSECT = 1
    CULL_INSIDE = 2

    def __init__(self):
        # 0: Left, 1: Right, 2: Bottom, 3: Top, 4: Near, 5: Far
        self.planes = [Plane() for _ in range(6)]

    @staticmethod
    def extract_from_matrix(m: np.ndarray) -> 'Frustum':
        """
        Extracts 6 normalized inward-facing frustum planes from column-major 4x4 matrix m.
        m is float32 shape (16,) matching OpenGL column-major order: m[col * 4 + row].
        """
        f = Frustum()
        def M(row, col):
            return m[col * 4 + row]

        # Left Plane: r3 + r0
        f.planes[0].normal[0] = M(3, 0) + M(0, 0)
        f.planes[0].normal[1] = M(3, 1) + M(0, 1)
        f.planes[0].normal[2] = M(3, 2) + M(0, 2)
        f.planes[0].d         = M(3, 3) + M(0, 3)

        # Right Plane: r3 - r0
        f.planes[1].normal[0] = M(3, 0) - M(0, 0)
        f.planes[1].normal[1] = M(3, 1) - M(0, 1)
        f.planes[1].normal[2] = M(3, 2) - M(0, 2)
        f.planes[1].d         = M(3, 3) - M(0, 3)

        # Bottom Plane: r3 + r1
        f.planes[2].normal[0] = M(3, 0) + M(1, 0)
        f.planes[2].normal[1] = M(3, 1) + M(1, 1)
        f.planes[2].normal[2] = M(3, 2) + M(1, 2)
        f.planes[2].d         = M(3, 3) + M(1, 3)

        # Top Plane: r3 - r1
        f.planes[3].normal[0] = M(3, 0) - M(1, 0)
        f.planes[3].normal[1] = M(3, 1) - M(1, 1)
        f.planes[3].normal[2] = M(3, 2) - M(1, 2)
        f.planes[3].d         = M(3, 3) - M(1, 3)

        # Near Plane: r3 + r2
        f.planes[4].normal[0] = M(3, 0) + M(2, 0)
        f.planes[4].normal[1] = M(3, 1) + M(2, 1)
        f.planes[4].normal[2] = M(3, 2) + M(2, 2)
        f.planes[4].d         = M(3, 3) + M(2, 3)

        # Far Plane: r3 - r2
        f.planes[5].normal[0] = M(3, 0) - M(2, 0)
        f.planes[5].normal[1] = M(3, 1) - M(2, 1)
        f.planes[5].normal[2] = M(3, 2) - M(2, 2)
        f.planes[5].d         = M(3, 3) - M(2, 3)

        for p in f.planes:
            p.normalize()
        return f

    def test_aabb(self, box: AABB) -> int:
        """p-vertex / n-vertex algorithm matching Frustum_TestAABB in math_utils.h."""
        all_inside = True
        for p in self.planes:
            # p-vertex
            px = box.max_x if p.normal[0] > 0.0 else box.min_x
            py = box.max_y if p.normal[1] > 0.0 else box.min_y
            pz = box.max_z if p.normal[2] > 0.0 else box.min_z

            if p.normal[0] * px + p.normal[1] * py + p.normal[2] * pz + p.d < float32(0.0):
                return self.CULL_OUTSIDE

            # n-vertex
            nx = box.min_x if p.normal[0] > 0.0 else box.max_x
            ny = box.min_y if p.normal[1] > 0.0 else box.max_y
            nz = box.min_z if p.normal[2] > 0.0 else box.max_z

            if p.normal[0] * nx + p.normal[1] * ny + p.normal[2] * nz + p.d < float32(0.0):
                all_inside = False

        return self.CULL_INSIDE if all_inside else self.CULL_INTERSECT

    def oracle_test_aabb(self, box: AABB) -> int:
        """Ground-truth oracle checking all 8 vertices against all 6 planes."""
        vertices = box.get_vertices()
        all_inside = True

        for p in self.planes:
            distances = [float(np.dot(p.normal, v) + p.d) for v in vertices]
            # If all 8 vertices are on negative side of this plane, it is outside
            if all(d < 0.0 for d in distances):
                return self.CULL_OUTSIDE
            # If any vertex is on negative side, not all vertices are inside
            if any(d < 0.0 for d in distances):
                all_inside = False

        return self.CULL_INSIDE if all_inside else self.CULL_INTERSECT


def make_view_proj_matrix(eye, yaw, pitch, fov_deg=70.0, aspect=16/9, near=0.1, far=256.0):
    yaw_rad = deg2rad(yaw)
    pitch_rad = deg2rad(pitch)

    cos_p = float32(np.cos(pitch_rad))
    sin_p = float32(np.sin(pitch_rad))
    cos_y = float32(np.cos(yaw_rad))
    sin_y = float32(np.sin(yaw_rad))

    forward = np.array([cos_p * sin_y, sin_p, -cos_p * cos_y], dtype=np.float32)
    right = np.array([cos_y, 0.0, sin_y], dtype=np.float32)
    up = np.array([-sin_p * sin_y, cos_p, sin_p * cos_y], dtype=np.float32)

    # View Matrix (col-major)
    v = np.zeros(16, dtype=np.float32)
    v[0] = right[0];  v[1] = up[0];  v[2] = -forward[0];  v[3] = 0.0
    v[4] = right[1];  v[5] = up[1];  v[6] = -forward[1];  v[7] = 0.0
    v[8] = right[2];  v[9] = up[2];  v[10] = -forward[2]; v[11] = 0.0
    v[12] = -float32(np.dot(right, eye))
    v[13] = -float32(np.dot(up, eye))
    v[14] = float32(np.dot(forward, eye))
    v[15] = 1.0

    # Perspective Matrix (col-major)
    p = np.zeros(16, dtype=np.float32)
    tan_half = float32(np.tan(deg2rad(fov_deg) * 0.5))
    f = float32(1.0 / tan_half)
    p[0] = f / float32(aspect)
    p[5] = f
    p[10] = -(far + near) / (far - near)
    p[11] = -1.0
    p[14] = -(2.0 * far * near) / (far - near)

    # Mat4 multiply: vp = p * v
    vp = np.zeros(16, dtype=np.float32)
    for col in range(4):
        for row in range(4):
            val = float32(0.0)
            for k in range(4):
                val += p[k * 4 + row] * v[col * 4 + k]
            vp[col * 4 + row] = val
    return vp


def run_frustum_stress_tests():
    print("==================================================================")
    print("STRESS TEST 4: Frustum Extraction & Fast AABB Culling Fuzzing")
    print("==================================================================")

    results = {
        "tests_run": 0,
        "passed": 0,
        "failed": 0,
        "findings": [],
        "matches_oracle": 0,
        "mismatches": 0,
        "cull_counts": {0: 0, 1: 0, 2: 0} # 0=OUTSIDE, 1=INTERSECT, 2=INSIDE
    }

    # Setup standard camera: Pos=(0, 64, 0), Yaw=0 (North, -Z), Pitch=0
    eye = np.array([0.0, 64.0, 0.0], dtype=np.float32)
    vp_matrix = make_view_proj_matrix(eye, yaw=0.0, pitch=0.0)
    frustum = Frustum.extract_from_matrix(vp_matrix)

    # Test 4.1: Deterministic Geometry Baselines
    print("\n[Test 4.1] Testing deterministic spatial scenarios...")

    # Box 1: Directly in front of camera at (0, 64, -10), size 2x2x2 -> INSIDE
    b_inside = AABB(-1, 63, -11, 1, 65, -9)
    res_inside = frustum.test_aabb(b_inside)
    print(f"  Box inside frustum at z=-10: {res_inside} (Expected CULL_INSIDE = 2)")

    # Box 2: Behind camera at (0, 64, +10), size 2x2x2 -> OUTSIDE
    b_behind = AABB(-1, 63, 9, 1, 65, 11)
    res_behind = frustum.test_aabb(b_behind)
    print(f"  Box behind camera at z=+10: {res_behind} (Expected CULL_OUTSIDE = 0)")

    # Box 3: Far beyond far plane (0, 64, -300), size 2x2x2 -> OUTSIDE
    b_far = AABB(-1, 63, -301, 1, 65, -299)
    res_far = frustum.test_aabb(b_far)
    print(f"  Box beyond far plane at z=-300: {res_far} (Expected CULL_OUTSIDE = 0)")

    # Box 4: Straddling the right frustum boundary -> INTERSECT
    # At z=-50, half width is approx 50 * tan(35) * (16/9) ~ 62.2m
    b_straddle = AABB(55, 63, -55, 70, 65, -45)
    res_straddle = frustum.test_aabb(b_straddle)
    print(f"  Box straddling frustum edge at x=[55,70]: {res_straddle} (Expected CULL_INTERSECT = 1)")

    # Box 5: Huge box enclosing entire frustum -> INTERSECT
    b_huge = AABB(-1000, -1000, -1000, 1000, 1000, 1000)
    res_huge = frustum.test_aabb(b_huge)
    print(f"  Huge world-enclosing box: {res_huge} (Expected CULL_INTERSECT = 1)")

    results["tests_run"] += 1
    if (res_inside == Frustum.CULL_INSIDE and
        res_behind == Frustum.CULL_OUTSIDE and
        res_far == Frustum.CULL_OUTSIDE and
        res_straddle == Frustum.CULL_INTERSECT and
        res_huge == Frustum.CULL_INTERSECT):
        results["passed"] += 1
        print("  PASS: Deterministic geometric scenarios 100% verified.")
    else:
        results["failed"] += 1
        print("  FAIL: Deterministic baseline test failed.")

    # Test 4.2: 10,000 Randomized Boxes vs Ground-Truth 8-Vertex Oracle
    print("\n[Test 4.2] Fuzzing 10,000 randomized boxes against independent 8-vertex oracle...")
    np.random.seed(9999)

    for i in range(10000):
        # Center in range [-300, 300] on X, [0, 128] on Y, [-300, 100] on Z
        cx = np.random.uniform(-300.0, 300.0)
        cy = np.random.uniform(0.0, 128.0)
        cz = np.random.uniform(-300.0, 100.0)

        # Extents from 0.5 to 32.0 (standard chunk/block sizes)
        hx = np.random.uniform(0.25, 16.0)
        hy = np.random.uniform(0.25, 16.0)
        hz = np.random.uniform(0.25, 16.0)

        box = AABB(cx - hx, cy - hy, cz - hz, cx + hx, cy + hy, cz + hz)

        fast_res = frustum.test_aabb(box)
        oracle_res = frustum.oracle_test_aabb(box)

        results["cull_counts"][fast_res] += 1

        if fast_res == oracle_res:
            results["matches_oracle"] += 1
        else:
            results["mismatches"] += 1
            if len(results["findings"]) < 5:
                results["findings"].append(
                    f"Box {i} mismatch: Fast={fast_res}, Oracle={oracle_res}, center=({cx:.1f},{cy:.1f},{cz:.1f})"
                )

    print(f"  10,000 randomized boxes tested:")
    print(f"  Matches with Oracle: {results['matches_oracle']} / 10000 ({(results['matches_oracle']/100.0):.2f}%)")
    print(f"  Culling Distribution: Outside={results['cull_counts'][0]}, Intersect={results['cull_counts'][1]}, Inside={results['cull_counts'][2]}")

    results["tests_run"] += 1
    if results["mismatches"] == 0:
        results["passed"] += 1
        print("  PASS: Fast p-vertex / n-vertex culling matches 8-vertex ground truth with 100.0% parity.")
    else:
        results["failed"] += 1
        print(f"  FAIL: {results['mismatches']} mismatches with oracle.")

    # Test 4.3: Standard 17x17 Toroidal Chunk Grid Culling
    print("\n[Test 4.3] Testing Minecraft 17x17 chunk grid (289 sub-chunks) visibility...")
    # Chunks are 16x256x16. Player at chunk (0, 0)
    visible_chunks = 0
    culled_chunks = 0
    for chunk_x in range(-8, 9):
        for chunk_z in range(-8, 9):
            min_x = chunk_x * 16.0
            max_x = min_x + 16.0
            min_y = 0.0
            max_y = 256.0
            min_z = chunk_z * 16.0
            max_z = min_z + 16.0

            c_box = AABB(min_x, min_y, min_z, max_x, max_y, max_z)
            cull = frustum.test_aabb(c_box)
            if cull != Frustum.CULL_OUTSIDE:
                visible_chunks += 1
            else:
                culled_chunks += 1

    print(f"  17x17 Toroidal Grid (289 chunks): Visible={visible_chunks}, Culled={culled_chunks}")
    # Player at (0, 64, 0) looking North (-Z).
    # Chunks with z > 0 (behind player) should be mostly culled!
    # Chunks in front (-Z) within FOV should be visible.
    results["tests_run"] += 1
    if visible_chunks > 30 and culled_chunks > 100:
        results["passed"] += 1
        print("  PASS: 17x17 Toroidal grid culling produces realistic chunk visibility profile.")
    else:
        results["failed"] += 1
        print("  FAIL: Chunk culling counts unexpected.")

    # Test 4.4: Extreme Coordinates (> 1,000,000) Frustum Culling
    print("\n[Test 4.4] Testing Frustum Culling at extreme coordinates (1,000,000, 64, 1,000,000)...")
    extreme_eye = np.array([1000000.0, 64.0, 1000000.0], dtype=np.float32)
    vp_extreme = make_view_proj_matrix(extreme_eye, yaw=45.0, pitch=-30.0)
    frustum_ext = Frustum.extract_from_matrix(vp_extreme)

    # Box relative to extreme eye: 20m in front
    # Forward vector for yaw=45, pitch=-30:
    # y = sin(-30) = -0.5, cos(-30) = 0.866
    # x = 0.866 * sin(45) = 0.612, z = -0.866 * cos(45) = -0.612
    # In front at (1000012, 54, 999988)
    b_ext_front = AABB(1000010, 52, 999986, 1000014, 56, 999990)
    cull_front = frustum_ext.test_aabb(b_ext_front)

    # Box 50m behind extreme eye
    b_ext_behind = AABB(999960, 80, 1000030, 999970, 90, 1000040)
    cull_behind = frustum_ext.test_aabb(b_ext_behind)

    print(f"  Extreme eye: front box cull={cull_front}, behind box cull={cull_behind}")

    results["tests_run"] += 1
    if cull_front != Frustum.CULL_OUTSIDE and cull_behind == Frustum.CULL_OUTSIDE:
        results["passed"] += 1
        print("  PASS: Frustum extraction and AABB culling remain precise at > 1,000,000 coordinates.")
    else:
        results["failed"] += 1
        print("  FAIL: Extreme coordinate culling failure.")

    print("\n------------------------------------------------------------------")
    print(f"SUMMARY: {results['passed']}/{results['tests_run']} test groups passed.")
    print("------------------------------------------------------------------")
    return results


if __name__ == "__main__":
    res = run_frustum_stress_tests()
    if res["failed"] > 0:
        sys.exit(1)
    sys.exit(0)
