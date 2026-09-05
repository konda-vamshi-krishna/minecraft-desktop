"""
Stress Test Harness 3: 60Hz Fixed Timestep Accumulator State Machine Fuzzing.
Empirically stress-tests the accumulator state machine under:
1. Long freezes (5.0s, 60.0s, repeated 100x freezes).
2. Ultra-high FPS micro-deltas (0.0001s over 100,000 frames).
3. Chaotic/erratic frame times (100,000 frames with jitter, stalls, freezes).
4. Exact boundary conditions (0.25s, 0.0s, negative time jumps).
5. Verification that substeps NEVER exceed 15 and accumulator never explodes.
"""

import math
import sys
import numpy as np

RUNTIME_PHYSICS_HZ = 60
RUNTIME_FIXED_DT = 1.0 / float(RUNTIME_PHYSICS_HZ) # 0.016666666666666666
RUNTIME_MAX_FRAME_TIME = 0.25                      # 250 ms spiral-of-death clamp
RUNTIME_MAX_SUBSTEPS = 15                          # 0.25 / (1/60) = 15 steps max
RUNTIME_CELESTIAL_PERIOD = 1200.0

class RuntimeStateMachine:
    def __init__(self, fixed_dt=RUNTIME_FIXED_DT, max_accumulator=RUNTIME_MAX_FRAME_TIME, max_substeps=RUNTIME_MAX_SUBSTEPS):
        self.fixed_dt = float(fixed_dt)
        self.max_accumulator = float(max_accumulator)
        self.max_substeps = int(max_substeps)

        self.accumulator = 0.0
        self.substeps_this_frame = 0
        self.total_ticks = 0
        self.total_simulated_time = 0.0
        self.total_real_time = 0.0
        self.total_frames = 0
        self.render_alpha = 0.0
        self.is_paused = False
        self.time_of_day = 0.0

    def update_celestial_clock(self, dt: float):
        self.time_of_day += dt
        if self.time_of_day >= RUNTIME_CELESTIAL_PERIOD:
            self.time_of_day = math.fmod(self.time_of_day, RUNTIME_CELESTIAL_PERIOD)

    def begin_frame(self, frame_time: float):
        # Guard against system clock jumps backwards
        if frame_time < 0.0:
            frame_time = 0.0

        self.total_real_time += frame_time

        if self.is_paused:
            frame_time = 0.0

        # Spiral of death clamp on frame delta
        if frame_time > self.max_accumulator:
            frame_time = self.max_accumulator

        self.accumulator += frame_time

        # Clamp total accumulated time to prevent compounding spikes
        if self.accumulator > self.max_accumulator:
            self.accumulator = self.max_accumulator

        self.substeps_this_frame = 0

    def should_step_physics(self) -> bool:
        if self.accumulator >= self.fixed_dt and self.substeps_this_frame < self.max_substeps:
            self.accumulator -= self.fixed_dt
            self.substeps_this_frame += 1
            self.total_ticks += 1
            self.total_simulated_time += self.fixed_dt
            self.update_celestial_clock(self.fixed_dt)
            return True

        # Hard ceiling: if we reached max substeps, discard remainder
        if self.substeps_this_frame >= self.max_substeps:
            self.accumulator = 0.0
        return False

    def get_render_alpha(self) -> float:
        alpha = float(self.accumulator / self.fixed_dt)
        if alpha < 0.0:
            alpha = 0.0
        if alpha >= 1.0:
            alpha = 0.99999
        self.render_alpha = alpha
        return alpha

    def simulate_frame(self, frame_time: float) -> int:
        self.begin_frame(frame_time)
        steps = 0
        while self.should_step_physics():
            steps += 1
        self.get_render_alpha()
        self.total_frames += 1
        return steps


def run_accumulator_stress_tests():
    print("==================================================================")
    print("STRESS TEST 3: 60Hz Accumulator State Machine & Spiral-of-Death")
    print("==================================================================")

    results = {
        "tests_run": 0,
        "passed": 0,
        "failed": 0,
        "findings": [],
        "max_substeps_observed": 0,
        "max_accumulator_observed": 0.0,
        "min_alpha_observed": 1.0,
        "max_alpha_observed": 0.0
    }

    # Test 3.1: 5.0s Freeze and Repeated Freeze Torture
    print("\n[Test 3.1] Testing 5.0s frame freeze and 100 consecutive massive freezes...")
    rt = RuntimeStateMachine()

    # Single 5.0s freeze
    steps_5s = rt.simulate_frame(5.0)
    acc_after_5s = rt.accumulator
    alpha_after_5s = rt.render_alpha

    print(f"  5.0s freeze result: steps={steps_5s} (expected exactly 15), acc={acc_after_5s:.6f}, alpha={alpha_after_5s:.4f}")

    # 100 consecutive freezes
    freeze_violations = 0
    for _ in range(100):
        s = rt.simulate_frame(10.0)
        if s != 15 or rt.accumulator != 0.0:
            freeze_violations += 1

    results["tests_run"] += 1
    if steps_5s == 15 and acc_after_5s == 0.0 and freeze_violations == 0:
        results["passed"] += 1
        print("  PASS: Spiral-of-death strictly caps substeps to 15; accumulator never compounds across freezes.")
    else:
        results["failed"] += 1
        results["findings"].append(f"Freeze violation: steps_5s={steps_5s}, violations={freeze_violations}")
        print(f"  FAIL: Freeze violation: steps_5s={steps_5s}, violations={freeze_violations}")

    # Test 3.2: Ultra-High FPS Micro-Steps (0.0001s over 100,000 frames)
    print("\n[Test 3.2] Testing Ultra-High FPS (0.0001s = 10,000 FPS) over 100,000 frames...")
    rt = RuntimeStateMachine()
    micro_dt = 0.0001 # 0.1ms per frame
    # Total real time = 100,000 * 0.0001 = 10.0 seconds
    # Expected ticks = 10.0 * 60 = 600 ticks

    high_fps_violations = 0
    step_counts = {0: 0, 1: 0, "other": 0}

    for frame in range(100000):
        s = rt.simulate_frame(micro_dt)
        if s in step_counts:
            step_counts[s] += 1
        else:
            step_counts["other"] += 1
            high_fps_violations += 1

        if rt.accumulator > rt.fixed_dt + 1e-9:
            high_fps_violations += 1

        if rt.render_alpha < 0.0 or rt.render_alpha >= 1.0:
            high_fps_violations += 1

    print(f"  100,000 micro-frames completed:")
    print(f"  Total Real Time: {rt.total_real_time:.4f}s | Simulated Time: {rt.total_simulated_time:.4f}s")
    print(f"  Total Physics Ticks: {rt.total_ticks} (Expected ~600)")
    print(f"  Step distribution: 0-step frames: {step_counts[0]}, 1-step frames: {step_counts[1]}, >1: {step_counts['other']}")

    results["tests_run"] += 1
    if high_fps_violations == 0 and abs(rt.total_ticks - 600) <= 1:
        results["passed"] += 1
        print("  PASS: Ultra-high FPS maintains deterministic 60Hz physics rate with bounded remainder.")
    else:
        results["failed"] += 1
        results["findings"].append(f"High FPS violation: ticks={rt.total_ticks}, violations={high_fps_violations}")
        print(f"  FAIL: High FPS violations: {high_fps_violations}")

    # Test 3.3: 100,000 Chaotic / Erratic Frame Times
    print("\n[Test 3.3] Stress-testing 100,000 chaotic frame deltas (log-uniform 10us to 5.0s)...")
    rt = RuntimeStateMachine()
    np.random.seed(1337)

    # Generate chaotic mix: 80% normal (10-25ms), 10% micro (0.01-1ms), 7% stutter (30-200ms), 3% spike (0.25-5.0s)
    chaotic_deltas = []
    for _ in range(100000):
        r = np.random.random()
        if r < 0.80:
            dt = np.random.uniform(0.010, 0.025)
        elif r < 0.90:
            dt = np.random.uniform(0.00001, 0.001)
        elif r < 0.97:
            dt = np.random.uniform(0.030, 0.200)
        else:
            dt = np.random.uniform(0.250, 5.000)
        chaotic_deltas.append(dt)

    chaotic_violations = 0
    for frame_idx, dt in enumerate(chaotic_deltas):
        steps = rt.simulate_frame(dt)

        if steps > results["max_substeps_observed"]:
            results["max_substeps_observed"] = steps

        if rt.accumulator > results["max_accumulator_observed"]:
            results["max_accumulator_observed"] = rt.accumulator

        if rt.render_alpha < results["min_alpha_observed"]:
            results["min_alpha_observed"] = rt.render_alpha
        if rt.render_alpha > results["max_alpha_observed"]:
            results["max_alpha_observed"] = rt.render_alpha

        # Invariant 1: Substeps NEVER exceed 15
        if steps > 15:
            chaotic_violations += 1
            if len(results["findings"]) < 5:
                results["findings"].append(f"Frame {frame_idx}: Substeps {steps} > 15!")

        # Invariant 2: Accumulator NEVER exceeds maxAccumulator (0.25)
        if rt.accumulator > 0.25000001:
            chaotic_violations += 1
            if len(results["findings"]) < 5:
                results["findings"].append(f"Frame {frame_idx}: Accumulator {rt.accumulator} > 0.25!")

        # Invariant 3: Render alpha strictly in [0.0, 1.0)
        if rt.render_alpha < 0.0 or rt.render_alpha >= 1.0:
            chaotic_violations += 1
            if len(results["findings"]) < 5:
                results["findings"].append(f"Frame {frame_idx}: Alpha {rt.render_alpha} outside [0.0, 1.0)!")

    print(f"  Chaotic Fuzzing Results:")
    print(f"  Max Substeps Observed: {results['max_substeps_observed']} (Limit: 15)")
    print(f"  Max Accumulator Observed: {results['max_accumulator_observed']:.6f}s (Limit: 0.25s)")
    print(f"  Alpha Range Observed: [{results['min_alpha_observed']:.6f}, {results['max_alpha_observed']:.6f}]")

    results["tests_run"] += 1
    if chaotic_violations == 0 and results["max_substeps_observed"] <= 15:
        results["passed"] += 1
        print("  PASS: All invariants held over 100,000 chaotic frames. Zero accumulator explosion.")
    else:
        results["failed"] += 1
        print(f"  FAIL: {chaotic_violations} chaotic invariant violations.")

    # Test 3.4: Boundary Conditions & Negative System Clock Jumps
    print("\n[Test 3.4] Testing boundary conditions (exact 0.25s, negative clock deltas, pause)...")
    rt = RuntimeStateMachine()

    # Exact boundary 0.25s
    s_boundary = rt.simulate_frame(0.25)
    # 0.25 / (1/60) = 15.0
    if s_boundary != 15 or rt.accumulator != 0.0:
        results["findings"].append(f"Exact boundary 0.25s failed: steps={s_boundary}, acc={rt.accumulator}")

    # Negative delta (e.g. NTP backwards clock step)
    s_neg = rt.simulate_frame(-10.0)
    if s_neg != 0 or rt.accumulator != 0.0:
        results["findings"].append(f"Negative clock jump failed: steps={s_neg}, acc={rt.accumulator}")

    # Pause mode
    rt.is_paused = True
    ticks_before = rt.total_ticks
    for _ in range(60):
        rt.simulate_frame(0.016666)
    ticks_after = rt.total_ticks

    boundary_pass = (s_boundary == 15 and s_neg == 0 and ticks_before == ticks_after)
    results["tests_run"] += 1
    if boundary_pass:
        results["passed"] += 1
        print("  PASS: Exact 0.25s boundary, negative clock jumps, and pause state verified.")
    else:
        results["failed"] += 1
        print("  FAIL: Boundary condition failure.")

    # Test 3.5: Celestial Clock 20-minute Period Invariant
    print("\n[Test 3.5] Verifying 20-minute (1200s) Celestial Clock Periodicity...")
    rt = RuntimeStateMachine()
    # Advance exactly 1200 seconds (72,000 ticks)
    # 1200 / (1/60) = 72,000 ticks
    for _ in range(72000):
        rt.update_celestial_clock(rt.fixed_dt)

    # Time of day should be within nanoseconds of 0.0 or 1200.0 (circular distance)
    circ_dist = min(rt.time_of_day, abs(RUNTIME_CELESTIAL_PERIOD - rt.time_of_day))
    # And after 1 more tick, it must be exactly in [0, fixed_dt]
    rt.update_celestial_clock(rt.fixed_dt)
    wrapped_ok = (rt.time_of_day < rt.fixed_dt * 1.5)

    results["tests_run"] += 1
    if circ_dist < 1e-6 and wrapped_ok:
        results["passed"] += 1
        print(f"  PASS: Celestial cycle wraps precisely after 72,000 ticks (circular error = {circ_dist:.2e}s).")
    else:
        results["failed"] += 1
        print(f"  FAIL: Celestial cycle drift: circ_dist={circ_dist}s, tod={rt.time_of_day}s")

    print("\n------------------------------------------------------------------")
    print(f"SUMMARY: {results['passed']}/{results['tests_run']} test groups passed.")
    print("------------------------------------------------------------------")
    return results


if __name__ == "__main__":
    res = run_accumulator_stress_tests()
    if res["failed"] > 0:
        sys.exit(1)
    sys.exit(0)
