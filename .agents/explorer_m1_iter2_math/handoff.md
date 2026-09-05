# Handoff Report: Mathematical & Camera Invariant Analysis
**Milestone:** M1 Hardening & M2/M3 Mathematical Invariants  
**Author:** `explorer_m1_iter2_math` (investigator, math specialist)  
**Recipient:** `parent` (orchestrator: `fd432488-815b-45be-9bfc-410c7c8c8f4c`)  
**Date:** 2026-09-03  
**Working Directory:** `g:/minecraft_desktop/.agents/explorer_m1_iter2_math`  
**Target File Audited:** `src/core/math_utils.h`  

---

## 1. Observation

1. **`WrapAngle360` Float32 Rounding Anomaly:**
   - Location: `src/core/math_utils.h:116-122`
   - Verbatim Code:
     ```c
     static inline float WrapAngle360(float angle) {
         angle = fmodf(angle, 360.0f);
         if (angle < 0.0f) {
             angle += 360.0f;
         }
         return angle;
     }
     ```
   - Direct Empirical Tool Result:
     ```powershell
     python -c "import ctypes, math; c_float = ctypes.c_float; a = c_float(-1e-6).value; a = c_float(math.fmod(a, 360.0)).value; a = c_float(a + 360.0).value; print(a)"
     ```
     Output: `360.0` (Hex: `0x1.6800000000000p+8`).
   - Boundary Interval: For any input angle in $[-2^{-16}, 0.0) = [-1.52587890625 \times 10^{-5}, 0.0)$, float32 round-to-nearest-ties-to-even rounds $360.0f + angle$ up to $360.0f$.
   - Contract Violation: The returned value $360.0f$ violates the half-open range contract $[0.0, 360.0)$ defined in `math_utils.h:84`.

2. **`Camera_UpdateFov` Sprint vs. Sneak Priority Order:**
   - Location: `src/core/math_utils.h:341-348`
   - Verbatim Code:
     ```c
     static inline void Camera_UpdateFov(Camera* cam, bool isSprinting, bool isSneaking, float dt) {
         if (isSprinting) {
             cam->targetFov = cam->baseFov * 1.15f;
         } else if (isSneaking) {
             cam->targetFov = cam->baseFov * 0.90f;
         } else {
             cam->targetFov = cam->baseFov;
         }
     ```
   - Conflicting Canonical Invariants:
     - `docs/02_CORE_GAMEPLAY_FEATURES.md:411`: `float baseSpeed = isSneaking ? 1.295f : (isSprinting ? 5.612f : 4.317f);`
     - `tests/canonical_models.py:96-100`: `if self.is_sneaking: base_speed = Kinematics.SNEAK_SPEED elif self.is_sprinting: base_speed = Kinematics.SPRINT_SPEED ...`
   - Discrepancy: When both `isSprinting` and `isSneaking` are true, `Camera_UpdateFov` expands the view cone ($1.15\times$ base FOV), while player kinematics restricts speed to sneak ($0.30\times$ base speed).

3. **`Ray_Create` Directional Sign Inversion:**
   - Location: `src/core/math_utils.h:467-469`
   - Verbatim Code:
     ```c
     r.invDir.x = (fabsf(r.dir.x) > 1e-8f) ? (1.0f / r.dir.x) : 1e8f;
     r.invDir.y = (fabsf(r.dir.y) > 1e-8f) ? (1.0f / r.dir.y) : 1e8f;
     r.invDir.z = (fabsf(r.dir.z) > 1e-8f) ? (1.0f / r.dir.z) : 1e8f;
     ```
   - Discrepancy: For a ray with a direction component nearly parallel to an axis in the negative direction, e.g. $dir.x \in (-10^{-8}, 0.0)$, `fabsf(r.dir.x) <= 1e-8f` results in `+1e8f`, discarding the negative direction sign and inverting slab bounds in `Ray_IntersectAABB`.

4. **`Mat4_Perspective` Zero/Negative Aspect Ratio Exposure:**
   - Location: `src/core/math_utils.h:275`
   - Verbatim Code: `p.m[0] = f / aspect;`
   - Discrepancy: Window minimization or collapse can pass `aspect <= 0.0f`, generating `Inf` or `NaN` into projection matrix column 0, corrupting all frustum planes.

5. **Test Suite Baseline Telemetry:**
   - Command: `python tests/test_runner.py --tier all` -> 105 passed, 0 failed (100.0% in 0.040s).
   - Command: `python -m unittest tests/test_m1_c_invariants.py` -> 9 passed, 0 failed (100.0% in 0.005s).
   - Command: `python .agents/challenger_m1_1/run_all_stress_tests.py` -> 20/20 test groups passed.
   - Masking Bug in Challenger Suite: `.agents/challenger_m1_1/stress_math.py:308` contained `or abs(w - 360.0) < 1e-4`, which masked `w == 360.0` from registering as a failure.

---

## 2. Logic Chain

1. **Step 1 (Float32 Representation Limits):**
   - Observation 1.1 establishes that float32 has a 24-bit significand. At $360.0f$, $1\text{ ULP} = 2^{-15}$.
   - For any negative increment $|x| \le 2^{-16} = 1.52587890625 \times 10^{-5}$, the exact real difference $360.0 - |x|$ lies at or above the round-to-even midpoint $360.0 - 2^{-16}$.
   - Consequently, in IEEE 754 float32 arithmetic, $360.0f + x$ evaluates to $360.0f$.
   - Because `WrapAngle360` does not clamp or re-evaluate after addition, it outputs $360.0f$.
   - Therefore, a post-addition check `if (angle >= 360.0f) angle = 0.0f;` is mathematically necessary and sufficient to restore the invariant $[0.0, 360.0)$.

2. **Step 2 (Camera FOV vs Kinematics Alignment):**
   - Observation 1.2 proves that `docs/02_CORE_GAMEPLAY_FEATURES.md` and `tests/canonical_models.py` prioritize sneak over sprint.
   - Sneaking physically constrains player movement to $1.295\text{ m/s}$ ($0.30\times$) and shrinks the hitbox from $1.8\text{m}$ to $1.5\text{m}$.
   - Evaluating sprint before sneak in `Camera_UpdateFov` causes an optical-kinematic divergence when both keys are engaged.
   - Inverting the evaluation sequence in `Camera_UpdateFov` (`if (isSneaking) ... else if (isSprinting) ...`) guarantees that the camera FOV matches the player's actual kinematic state under all input combinations.

3. **Step 3 (Numerical Robustness for Raycasting & Projection):**
   - Observation 1.3 demonstrates that `1e8f` without sign propagation reverses interval order for negative near-zero ray directions. Replacing it with `(r.dir.x < 0.0f ? -1e8f : 1e8f)` preserves directional fidelity.
   - Observation 1.4 confirms that clamping `aspect` to a positive floor ($0.0001f$) in `Mat4_Perspective` prevents catastrophic `NaN` propagation into the view-projection matrix and frustum culling subsystem.

4. **Step 4 (Readiness for Milestone 2 & Milestone 3):**
   - Mathematical invariants for Milestone 2 (floored bitshifts, Y-stride 1 chunk indexing, 4-byte packed vertex layout, AO diagonal triangulation flip) and Milestone 3 ($Y \to X \to Z$ collision, $+0.55\text{m}$ auto-step, $-0.05\text{m}$ sneak clamp, Amanatides-Woo DDA) have been validated and documented in `analysis.md`.

---

## 3. Caveats

1. **Host-Compiler Execution Policy:** In accordance with the user safety directive (2026-09-03T07:33:28Z), no native compilers were downloaded or executed on the host. All empirical simulations were performed via bit-accurate Python 3 standard library and ctypes IEEE 754 models.
2. **Double-Precision Upgrade Ceiling:** Per Ponytail minimalist principles, `math_utils.h` retains float32 scalar arithmetic. If planetary or double-precision coordinates are ever required, camera-relative local origins will be used rather than refactoring to `double`.

---

## 4. Conclusion

The audit is complete. All identified edge cases in `src/core/math_utils.h` have clear, minimal-complexity root causes with zero-overhead C99 remediations.

### Recommended C99 Patch (`math_utils.h`)
```diff
--- a/src/core/math_utils.h
+++ b/src/core/math_utils.h
@@ -118,6 +118,10 @@ static inline float WrapAngle360(float angle) {
     if (angle < 0.0f) {
         angle += 360.0f;
     }
+    /* Guard against IEEE 754 precision rounding up to 360.0f for small negative inputs in [-2^-16, 0.0) */
+    if (angle >= 360.0f) {
+        angle = 0.0f;
+    }
     return angle;
 }
 
@@ -270,6 +274,8 @@ static inline Mat4 Mat4_Perspective(float fovRad, float aspect, float zNear, fl
     Mat4 p;
     memset(p.m, 0, sizeof(p.m));
     float tanHalfFov = tanf(fovRad * 0.5f);
+    /* Defensive guard against window minimization or collapsed dimensions */
+    if (aspect <= 0.0001f) aspect = 1.0f;
     float f = 1.0f / tanHalfFov;
 
     p.m[0]  = f / aspect;
@@ -341,10 +347,11 @@ static inline void Camera_Rotate(Camera* cam, float deltaYaw, float deltaPitch)
 
 /* Dynamic FOV with exponential asymptotic decay (Sprint 1.15x, Sneak 0.90x, lambda = 12.0 s^-1) */
 static inline void Camera_UpdateFov(Camera* cam, bool isSprinting, bool isSneaking, float dt) {
-    if (isSprinting) {
-        cam->targetFov = cam->baseFov * 1.15f;
-    } else if (isSneaking) {
+    /* Sneak takes strict precedence over sprint per canonical Minecraft kinematics */
+    if (isSneaking) {
         cam->targetFov = cam->baseFov * 0.90f;
+    } else if (isSprinting) {
+        cam->targetFov = cam->baseFov * 1.15f;
     } else {
         cam->targetFov = cam->baseFov;
     }
@@ -465,9 +472,10 @@ static inline bool AABB_ContainsPoint(const AABB* b, Vec3 p) {
 static inline Ray Ray_Create(Vec3 origin, Vec3 dir) {
     Ray r;
     r.origin = origin;
     r.dir = Vec3_Normalize(dir);
-    r.invDir.x = (fabsf(r.dir.x) > 1e-8f) ? (1.0f / r.dir.x) : 1e8f;
-    r.invDir.y = (fabsf(r.dir.y) > 1e-8f) ? (1.0f / r.dir.y) : 1e8f;
-    r.invDir.z = (fabsf(r.dir.z) > 1e-8f) ? (1.0f / r.dir.z) : 1e8f;
+    /* Preserve ray directional sign even when axis-parallel to prevent slab orientation inversion */
+    r.invDir.x = (fabsf(r.dir.x) > 1e-8f) ? (1.0f / r.dir.x) : (r.dir.x < 0.0f ? -1e8f : 1e8f);
+    r.invDir.y = (fabsf(r.dir.y) > 1e-8f) ? (1.0f / r.dir.y) : (r.dir.y < 0.0f ? -1e8f : 1e8f);
+    r.invDir.z = (fabsf(r.dir.z) > 1e-8f) ? (1.0f / r.dir.z) : (r.dir.z < 0.0f ? -1e8f : 1e8f);
     return r;
 }
```

---

## 5. Verification Method

1. **Verify Existing E2E Test Suite (Zero Regressions):**
   ```powershell
   python tests/test_runner.py --tier all
   ```
   *Expected:* 105 tests, 105 passed, 0 failures.

2. **Verify M1 C Structural & Invariant Suite:**
   ```powershell
   python -m unittest tests/test_m1_c_invariants.py
   ```
   *Expected:* 9 tests, 9 passed, 0 failures.

3. **Verify Strict `WrapAngle360` Float Precision Rounding Fix:**
   ```powershell
   python -c "import ctypes, math; c_float = ctypes.c_float;
   def wrap(angle):
       a = c_float(math.fmod(angle, 360.0)).value
       if a < 0.0: a = c_float(a + 360.0).value
       if a >= 360.0: a = 0.0
       return a
   for v in [-1e-6, -1e-5, -1.5e-5, -1.5258789e-5, -1.5259e-5]:
       res = wrap(v)
       assert 0.0 <= res < 360.0, f'Failed at {v}: {res}'
   print('WrapAngle360 guard verified successfully.')"
   ```

4. **Verify FOV Priority Inversion:**
   Inspect `Camera_UpdateFov` in `src/core/math_utils.h` to confirm `if (isSneaking)` precedes `if (isSprinting)`.

5. **Invalidation Conditions:**
   - Any test input producing `WrapAngle360(theta) >= 360.0f`.
   - Simultaneous `isSprinting = true` and `isSneaking = true` setting `targetFov > baseFov`.
