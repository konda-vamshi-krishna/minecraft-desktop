## 2026-09-03T07:14:19Z
You are explorer_m1_camera.
Your working directory is: g:/minecraft_desktop/.agents/explorer_m1_camera/
Project Root: g:/minecraft_desktop

MANDATORY: Read g:/minecraft_desktop/ORIGINAL_REQUEST.md before starting work.
Also read:
- g:/minecraft_desktop/.agents/orchestrator/PROJECT.md
- g:/minecraft_desktop/docs/01_ARCHITECTURE_AND_RUNTIME.md
- g:/minecraft_desktop/docs/02_CORE_GAMEPLAY_FEATURES.md
- g:/minecraft_desktop/.agents/spec_miner_gameplay/spec_report.md

Your mission:
Analyze the requirements and design the concrete implementation plan for Milestone 1 (M1) Camera System & Math Utilities:
1. 3D Camera data structures: Position $(x, y, z)$, Euler angles Yaw $[0, 360^\circ)$, Pitch $[-89.0^\circ, +89.0^\circ]$ clamping.
2. Canonical look direction vector calculation:
   $\mathbf{F}_{\text{look}} = (\cos\theta\sin\psi, \sin\theta, -\cos\theta\cos\psi)$
   Planar forward and right vectors:
   $\mathbf{F}_{\text{planar}} = (\sin\psi, 0, -\cos\psi), \quad \mathbf{R}_{\text{planar}} = (\cos\psi, 0, \sin\psi)$
3. View Matrix (LookAt) and Perspective Projection Matrix calculation with dynamic FOV (velocity multiplier: sprint 1.15x, sneak 0.90x, $\lambda = 12.0\text{ s}^{-1}$).
4. Frustum extraction (6 planes) for chunk AABB frustum culling.
5. Header design for `src/core/math_utils.h` (Vec3, Mat4, AABB, Ray, plane intersection helpers) with zero dynamic allocation.
6. Write your detailed analysis and recommended C implementation strategy to g:/minecraft_desktop/.agents/explorer_m1_camera/analysis.md and deliver handoff.md in your working directory. Send a message to parent when done. Do not modify or create source code outside your working directory.
