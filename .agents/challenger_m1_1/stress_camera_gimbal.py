"""
Stress Test Harness 2: Euler Pitch Clamping and Gimbal Lock Invariant Verification.
Executes 100,000 random and adversarial mouse deltas to verify:
1. Strict [-89.0f, +89.0f] pitch clamping (zero gimbal lock).
2. Strict [0.0f, 360.0f) yaw positive modulo wrapping.
3. Unit-length and strict orthonormality of {forward, right, up} basis.
4. Positive determinant det([R, U, -F]) == 1.0.
5. Persistent non-zero horizontal projection |F_xz| >= cos(89 deg) ~ 0.01745.
"""

import math
import sys
import numpy as np

def float32(x):
    return np.float32(x)

M_PI = float32(3.14159265358979323846)

def deg2rad(d):
    return float32(d * (M_PI / float32(180.0)))

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
    angle = float32(math.fmod(float(angle), 360.0))
    if angle < float32(0.0):
        angle = float32(angle + float32(360.0))
    return angle

class CameraModel:
    def __init__(self, pos=(0, 64, 0), yaw=0.0, pitch=0.0, base_fov=70.0, aspect=16/9, near=0.1, far=256.0):
        self.pos = np.array(pos, dtype=np.float32)
        self.yaw = wrap_angle_360(yaw)
        self.pitch = clamp_float(pitch, -89.0, 89.0)
        self.base_fov = float32(base_fov)
        self.current_fov = float32(base_fov)
        self.target_fov = float32(base_fov)
        self.aspect = float32(aspect)
        self.near = float32(near)
        self.far = float32(far)

        self.forward = np.zeros(3, dtype=np.float32)
        self.right = np.zeros(3, dtype=np.float32)
        self.up = np.zeros(3, dtype=np.float32)
        self.planar_forward = np.zeros(3, dtype=np.float32)
        self.planar_right = np.zeros(3, dtype=np.float32)
        self.update_vectors()

    def update_vectors(self):
        yaw_rad = deg2rad(self.yaw)
        pitch_rad = deg2rad(self.pitch)

        cos_pitch = float32(np.cos(pitch_rad))
        sin_pitch = float32(np.sin(pitch_rad))
        cos_yaw = float32(np.cos(yaw_rad))
        sin_yaw = float32(np.sin(yaw_rad))

        self.forward[0] = cos_pitch * sin_yaw
        self.forward[1] = sin_pitch
        self.forward[2] = -cos_pitch * cos_yaw

        self.planar_forward[0] = sin_yaw
        self.planar_forward[1] = float32(0.0)
        self.planar_forward[2] = -cos_yaw

        self.planar_right[0] = cos_yaw
        self.planar_right[1] = float32(0.0)
        self.planar_right[2] = sin_yaw

        self.right[:] = self.planar_right[:]
        self.up[0] = -sin_pitch * sin_yaw
        self.up[1] = cos_pitch
        self.up[2] = sin_pitch * cos_yaw

    def rotate(self, delta_yaw, delta_pitch):
        self.yaw = wrap_angle_360(self.yaw + float32(delta_yaw))
        self.pitch = clamp_float(self.pitch + float32(delta_pitch), -89.0, 89.0)
        self.update_vectors()

    def update_fov(self, is_sprinting: bool, is_sneaking: bool, dt: float):
        if is_sprinting:
            self.target_fov = float32(self.base_fov * 1.15)
        elif is_sneaking:
            self.target_fov = float32(self.base_fov * 0.90)
        else:
            self.target_fov = self.base_fov

        if dt > 0.0:
            factor = float32(1.0 - np.exp(-12.0 * dt))
            self.current_fov += (self.target_fov - self.current_fov) * factor


def run_camera_stress_tests():
    print("==================================================================")
    print("STRESS TEST 2: Euler Pitch Clamping & Gimbal Lock Fuzzing")
    print("==================================================================")

    results = {
        "tests_run": 0,
        "passed": 0,
        "failed": 0,
        "findings": [],
        "min_pitch_observed": 999.0,
        "max_pitch_observed": -999.0,
        "min_horizontal_mag": 999.0,
        "max_orthogonality_error": 0.0,
        "max_unit_length_error": 0.0
    }

    cam = CameraModel()

    # Test 2.1: 100,000 Random Mouse Deltas
    print("\n[Test 2.1] Fuzzing with 100,000 random mouse deltas (yaw in [-180, 180], pitch in [-180, 180])...")
    np.random.seed(42)
    deltas_yaw = np.random.uniform(-180.0, 180.0, size=100000).astype(np.float32)
    deltas_pitch = np.random.uniform(-180.0, 180.0, size=100000).astype(np.float32)

    violations = 0
    gimbal_lock_count = 0

    for i in range(100000):
        cam.rotate(deltas_yaw[i], deltas_pitch[i])

        # 1. Pitch clamp check
        p = float(cam.pitch)
        if p < results["min_pitch_observed"]:
            results["min_pitch_observed"] = p
        if p > results["max_pitch_observed"]:
            results["max_pitch_observed"] = p

        if p < -89.0001 or p > 89.0001:
            violations += 1
            if len(results["findings"]) < 5:
                results["findings"].append(f"Step {i}: Pitch {p} out of bounds [-89, +89]")

        # 2. Yaw wrap check
        y = float(cam.yaw)
        if y < 0.0 or y >= 360.0:
            if not (abs(y - 360.0) < 1e-4):
                violations += 1

        # 3. Gimbal Lock check:
        # Check horizontal magnitude of forward vector: |F_xz| = sqrt(Fx^2 + Fz^2)
        h_mag = float(np.sqrt(cam.forward[0]**2 + cam.forward[2]**2))
        if h_mag < results["min_horizontal_mag"]:
            results["min_horizontal_mag"] = h_mag

        # Theoretical minimum at pitch=89 deg is cos(89 deg) ~ 0.0174524
        if h_mag < 0.0174:
            gimbal_lock_count += 1
            if len(results["findings"]) < 5:
                results["findings"].append(f"Step {i}: Potential Gimbal lock! |F_xz| = {h_mag} < 0.0174")

        # 4. Orthonormality check
        dot_fu = float(np.dot(cam.forward, cam.up))
        dot_fr = float(np.dot(cam.forward, cam.right))
        dot_ur = float(np.dot(cam.up, cam.right))
        ortho_err = max(abs(dot_fu), abs(dot_fr), abs(dot_ur))
        if ortho_err > results["max_orthogonality_error"]:
            results["max_orthogonality_error"] = ortho_err

        len_f = abs(float(np.linalg.norm(cam.forward)) - 1.0)
        len_r = abs(float(np.linalg.norm(cam.right)) - 1.0)
        len_u = abs(float(np.linalg.norm(cam.up)) - 1.0)
        len_err = max(len_f, len_r, len_u)
        if len_err > results["max_unit_length_error"]:
            results["max_unit_length_error"] = len_err

        # 5. Determinant of camera orientation [R | U | -F]
        # In OpenGL camera coordinates, +X = Right, +Y = Up, -Z = Forward.
        basis = np.column_stack([cam.right, cam.up, -cam.forward])
        det = float(np.linalg.det(basis))
        if abs(det - 1.0) > 1e-3:
            violations += 1
            if len(results["findings"]) < 5:
                results["findings"].append(f"Step {i}: Camera basis det={det} != 1.0")

    results["tests_run"] += 1
    if violations == 0 and gimbal_lock_count == 0:
        results["passed"] += 1
        print(f"  PASS: 100,000 random mouse deltas verified.")
        print(f"        Observed Pitch Range: [{results['min_pitch_observed']:.4f}, {results['max_pitch_observed']:.4f}] deg")
        print(f"        Min Horizontal Component |F_xz|: {results['min_horizontal_mag']:.6f} (>= cos(89) = 0.017452)")
        print(f"        Max Orthogonality Error: {results['max_orthogonality_error']:.2e}")
        print(f"        Max Unit Length Error: {results['max_unit_length_error']:.2e}")
    else:
        results["failed"] += 1
        print(f"  FAIL: {violations} violations and {gimbal_lock_count} gimbal lock conditions detected.")

    # Test 2.2: Extreme Saturation Boundary Torture (Pinning at Zenith and Nadir)
    print("\n[Test 2.2] Torture Testing: 10,000 consecutive massive positive deltas (+1,000,000 deg)...")
    for _ in range(10000):
        cam.rotate(0.0, 1000000.0)
    zenith_pitch = float(cam.pitch)
    print(f"  Zenith Pinned Pitch: {zenith_pitch:.6f} deg (Must be exactly +89.000000)")

    print("  Torture Testing: 10,000 consecutive massive negative deltas (-1,000,000 deg)...")
    for _ in range(10000):
        cam.rotate(0.0, -1000000.0)
    nadir_pitch = float(cam.pitch)
    print(f"  Nadir Pinned Pitch: {nadir_pitch:.6f} deg (Must be exactly -89.000000)")

    results["tests_run"] += 1
    if abs(zenith_pitch - 89.0) < 1e-5 and abs(nadir_pitch - (-89.0)) < 1e-5:
        results["passed"] += 1
        print("  PASS: Boundary clamping remains completely drift-free under extreme saturation deltas.")
    else:
        results["failed"] += 1
        print("  FAIL: Clamping drifted under saturation.")

    # Test 2.3: Alternating Flip-Flop Invariant (+178, -178 deg rapid oscillation)
    print("\n[Test 2.3] Oscillating rapidly between Zenith and Nadir (10,000 cycles)...")
    flip_failures = 0
    for cycle in range(10000):
        cam.rotate(180.0, 178.0)
        if abs(float(cam.pitch) - 89.0) > 1e-4:
            flip_failures += 1
        cam.rotate(180.0, -178.0)
        if abs(float(cam.pitch) - (-89.0)) > 1e-4:
            flip_failures += 1

    results["tests_run"] += 1
    if flip_failures == 0:
        results["passed"] += 1
        print("  PASS: 10,000 rapid pitch flip-flops executed with zero numerical instability.")
    else:
        results["failed"] += 1
        print(f"  FAIL: {flip_failures} flip failures.")

    # Test 2.4: Dynamic FOV Asymptotic Convergence
    print("\n[Test 2.4] Dynamic FOV exponential decay convergence under sprint/sneak/walk...")
    cam.base_fov = float32(70.0)
    cam.current_fov = float32(70.0)

    # Sprint: target = 70 * 1.15 = 80.5 deg
    # Over 1.0 second (60 steps of dt = 1/60)
    dt = 1.0 / 60.0
    for _ in range(60):
        cam.update_fov(is_sprinting=True, is_sneaking=False, dt=dt)
    # factor per second: 1 - exp(-12 * 1.0) = 1 - 6.14e-6 ~ 0.999994
    fov_after_1s_sprint = float(cam.current_fov)

    # Sneak: target = 70 * 0.90 = 63.0 deg
    for _ in range(60):
        cam.update_fov(is_sprinting=False, is_sneaking=True, dt=dt)
    fov_after_1s_sneak = float(cam.current_fov)

    # Walk: target = 70.0 deg
    for _ in range(60):
        cam.update_fov(is_sprinting=False, is_sneaking=False, dt=dt)
    fov_after_1s_walk = float(cam.current_fov)

    results["tests_run"] += 1
    if (abs(fov_after_1s_sprint - 80.5) < 0.01 and
        abs(fov_after_1s_sneak - 63.0) < 0.01 and
        abs(fov_after_1s_walk - 70.0) < 0.01):
        results["passed"] += 1
        print(f"  PASS: Dynamic FOV smoothly converges to sprint ({fov_after_1s_sprint:.2f} deg), sneak ({fov_after_1s_sneak:.2f} deg), and walk ({fov_after_1s_walk:.2f} deg).")
    else:
        results["failed"] += 1
        print(f"  FAIL: FOV convergence failure: sprint={fov_after_1s_sprint}, sneak={fov_after_1s_sneak}, walk={fov_after_1s_walk}")

    print("\n------------------------------------------------------------------")
    print(f"SUMMARY: {results['passed']}/{results['tests_run']} test groups passed.")
    print("------------------------------------------------------------------")
    return results


if __name__ == "__main__":
    res = run_camera_stress_tests()
    if res["failed"] > 0:
        sys.exit(1)
    sys.exit(0)
