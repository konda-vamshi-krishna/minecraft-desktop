# 02. Core Gameplay Features & Voxel Physics Specification

**Document Version:** 1.0.0  
**Architect:** Gameplay Systems & Voxel Physics Engineering (Ponytail Senior Architecture / Max-Pro Polymath Directives)  
**Target Architecture:** Custom C++20 / OpenGL 4.5 Core Voxel Engine  
**Workspace Root:** `g:/minecraft_desktop`  

---

## 1. Executive System Architecture & Simulation Mechanics

### 1.1 Architectural Philosophy: Pure Voxel Engine (YAGNI / Zero Third-Party Physics)
Traditional 3D game engines offload kinematic simulation to generalized third-party physics packages (PhysX, Havok, Bullet, Jolt). In a uniform cubic lattice world, importing a general-purpose continuous rigid-body engine is an anti-pattern. A voxel world **is already its own discrete spatial acceleration structure** ($O(1)$ uniform grid). 

By exploiting discrete integer block occupancy, we eliminate:
- Broad-phase dynamic bounding volume hierarchies (BVH/AABB trees).
- Arbitrary convex polyhedra Minkowski sum solvers (GJK / EPA).
- Dynamic constraint graph solvers, island managers, and numerical drift.

All kinematic movement, ray traversal, and collision detection are executed directly against chunk voxel memory in $O(1)$ spatial lookups with zero heap allocations during the physics tick.

### 1.2 Coordinate System, Units, & Timestep Pipeline
- **Coordinate Space:** Right-handed Cartesian coordinate system:
  - $+X$: East
  - $+Y$: Up (Zenith)
  - $+Z$: South
- **Units:** $1.0\text{ unit} = 1.0\text{ meter} = 1.0\text{ block width}$.
- **Angles:** Yaw ($\psi$) in degrees $[0^\circ, 360^\circ)$ or radians; Pitch ($\theta$) in degrees $[-89.0^\circ, +89.0^\circ]$.
- **Time Stepping:** Fixed Timestep Simulation at $60\text{ Hz}$ ($\Delta t = \frac{1}{60}\text{s} \approx 0.016667\text{s}$).
- **State Interpolation:** Rendering frames sample the interpolated state between previous tick position $\mathbf{p}_{\text{prev}}$ and current tick position $\mathbf{p}_{\text{curr}}$ using render alpha $\alpha \in [0.0, 1.0)$:
  $$\mathbf{p}_{\text{render}} = (1 - \alpha)\mathbf{p}_{\text{prev}} + \alpha \mathbf{p}_{\text{curr}}$$

```
+---------------------------------------------------------------------------------------+
|                                    FRAME PIPELINE                                     |
+---------------------------------------------------------------------------------------+
|  [Raw Mouse / GLFW Events] -> Raw Delta Accumulation                                  |
|                                     |                                                 |
|  [Engine Tick (Fixed 60Hz)]         v                                                 |
|   ├── Input Poll: Forward/Strafe/Jump/Sneak/Sprint Vectors                           |
|   ├── Kinematic Integration: Acceleration, Gravity, Drag                             |
|   ├── Collision Pipeline: Axis-Decoupled Voxel Sweep (Y -> X -> Z)                   |
|   ├── Auto-Step Elevation Resolver (Obstacle step-up <= 0.5m)                         |
|   ├── Ground Contact & Ledge Fall-off Prevention (Sneaking)                          |
|   ├── Amanatides-Woo DDA Raycast (5.0m reach)                                        |
|   ├── Block Destruction / Placement FSM                                              |
|   └── Celestial Time Clock (Sun Orbit & Directional Lighting Vector)                 |
|                                     |                                                 |
|  [Render Pass (Variable Hz)]        v                                                 |
|   ├── Camera Transformation (Eye Lerp + View Matrix)                                 |
|   └── Frustum Voxel Mesh Dispatch with Face Shading Uniforms                         |
+---------------------------------------------------------------------------------------+
```

---

## 2. First-Person Controller Mechanics

### 2.1 Camera Kinematics & Mouse Capture
The camera operates as a standard first-person 2-DOF spherical coordinate system (Euler Pitch-Yaw). Roll is strictly locked to $0.0$ to eliminate vestibular disorientation.

#### 2.1.1 Mouse Delta & Pitch Clamping
Raw mouse input is ingested via OS-level captured/disabled cursor mode (e.g., `glfwSetInputMode(window, GLFW_CURSOR, GLFW_CURSOR_DISABLED)`). Mouse offsets $(\Delta x, \Delta y)$ are scaled by sensitivity scalar $\kappa$:

$$\Delta \psi = \Delta x \cdot \kappa, \quad \Delta \theta = -\Delta y \cdot \kappa$$
$$\psi \leftarrow (\psi + \Delta \psi) \pmod{360^\circ}$$
$$\theta \leftarrow \text{clamp}(\theta + \Delta \theta, -89.0^\circ, +89.0^\circ)$$

> **Singularity Avoidance:** Pitch is bounded strictly to $\pm 89.0^\circ$ ($\pm 1.5533\text{ rad}$) to prevent the camera forward vector from aligning collinearly with the world up vector $\mathbf{u} = (0, 1, 0)$, thereby preventing Gimbal lock in the View Matrix cross product.

#### 2.1.2 Direction Vectors
$$\mathbf{F}_{\text{look}} = \begin{pmatrix} \cos(\theta)\sin(\psi) \\ \sin(\theta) \\ -\cos(\theta)\cos(\psi) \end{pmatrix}, \quad 
\mathbf{F}_{\text{planar}} = \frac{\begin{pmatrix} \sin(\psi) \\ 0 \\ -\cos(\psi) \end{pmatrix}}{\left\|\begin{pmatrix} \sin(\psi) \\ 0 \\ -\cos(\psi) \end{pmatrix}\right\|}, \quad
\mathbf{R}_{\text{planar}} = \begin{pmatrix} \cos(\psi) \\ 0 \\ \sin(\psi) \end{pmatrix}$$

```cpp
// ponytail: [No quaternions/slerp camera] -> [Quaternion camera if 6-DOF flight or roll mechanics added]
struct CameraOrientation {
    float yawDeg   = 0.0f;  // 0 deg = Facing -Z (North)
    float pitchDeg = 0.0f;  // 0 deg = Level Horizon

    glm::vec3 GetForward() const {
        float pitchRad = glm::radians(pitchDeg);
        float yawRad   = glm::radians(yawDeg);
        return glm::normalize(glm::vec3(
            std::cos(pitchRad) * std::sin(yawRad),
            std::sin(pitchRad),
            -std::cos(pitchRad) * std::cos(yawRad)
        ));
    }

    glm::vec3 GetPlanarForward() const {
        float yawRad = glm::radians(yawDeg);
        return glm::vec3(std::sin(yawRad), 0.0f, -std::cos(yawRad));
    }

    glm::vec3 GetPlanarRight() const {
        float yawRad = glm::radians(yawDeg);
        return glm::vec3(std::cos(yawRad), 0.0f, std::sin(yawRad));
    }
};
```

### 2.2 Movement Vector Calculation & State Machine

#### 2.2.1 Input Normalization
Raw keyboard inputs generate a raw directional vector $\mathbf{i} = (i_x, 0, i_z) \in \{-1, 0, 1\}^2$.
To prevent the classic $\sqrt{2} \approx 1.414$ diagonal speed exploit, $\mathbf{i}$ is strictly normalized:

$$\mathbf{d}_{\text{wish}} = \begin{cases} \frac{i_x \mathbf{R}_{\text{planar}} + i_z \mathbf{F}_{\text{planar}}}{\|i_x \mathbf{R}_{\text{planar}} + i_z \mathbf{F}_{\text{planar}}\|} & \text{if } \|\mathbf{i}\| > 0 \\ \mathbf{0} & \text{otherwise} \end{cases}$$

#### 2.2.2 Movement Modifiers
Movement speed is governed by the state multiplier $S_{\text{state}}$:
- **Base Walking Speed:** $v_{\text{walk}} = 4.317\text{ m/s}$
- **Sprinting:** $v_{\text{sprint}} = 1.30 \times v_{\text{walk}} \approx 5.612\text{ m/s}$ (Disabled if hunger/exhaustion triggers or player moves backward: $\mathbf{d}_{\text{wish}} \cdot \mathbf{F}_{\text{planar}} < 0$).
- **Sneaking:** $v_{\text{sneak}} = 0.30 \times v_{\text{walk}} \approx 1.295\text{ m/s}$ (Activates ledge-clamp logic; player cannot fall off surfaces).

#### 2.2.3 Dynamic Field of View (FOV)
Camera FOV dynamically responds to velocity state transitions via an exponential asymptotic decay:

$$\text{FOV}_{\text{target}} = \begin{cases} \text{FOV}_{\text{base}} \times 1.15 & \text{if sprinting} \\ \text{FOV}_{\text{base}} \times 0.90 & \text{if sneaking} \\ \text{FOV}_{\text{base}} & \text{default} \end{cases}$$

$$\text{FOV}_{\text{current}} \leftarrow \text{FOV}_{\text{current}} + (\text{FOV}_{\text{target}} - \text{FOV}_{\text{current}}) \cdot (1 - e^{-\lambda \Delta t})$$
*(where convergence rate $\lambda = 12.0\text{ s}^{-1}$)*.

---

## 3. Amanatides-Woo Fast Voxel Traversal (DDA Raycasting)

### 3.1 Mathematical Derivation
For player-world interactions (block targeted for breaking, adjacent face targeted for placement), we employ the **Amanatides-Woo (1987) 3D Fast Voxel Traversal Algorithm**. It eliminates all ray-AABB intersection iterations across candidate voxels, guaranteeing an exact discrete step through every intersected voxel in continuous parametric ray space.

Let the camera eye ray be:
$$\mathbf{R}(t) = \mathbf{P}_0 + t \cdot \hat{\mathbf{d}}, \quad t \ge 0$$
where $\mathbf{P}_0 = (x_0, y_0, z_0)$ is the player eye origin, and $\hat{\mathbf{d}} = (d_x, d_y, d_z)$ is the unit look vector.

```
       Y-Axis (Block Grid)
         |
    3.0 -+-------+-------+-------+
         |       |       |   X   |  <-- Target Block Hit
    2.0 -+-------+-------+---+---+
         |       |   X   | /     |
    1.0 -+-------+---+---+-------+
         |   X   | /     |       |
    0.0 -+---o---+-------+-------+--> X-Axis
         P0 (Ray Origin)
```

#### 3.1.1 Grid Setup & Step Directions
Current voxel coordinates:
$$X = \lfloor x_0 \rfloor, \quad Y = \lfloor y_0 \rfloor, \quad Z = \lfloor z_0 \rfloor$$

Step directions per axis:
$$\text{step}_x = \operatorname{sgn}(d_x) = \begin{cases} 1 & d_x > 0 \\ -1 & d_x < 0 \\ 0 & d_x = 0 \end{cases}, \quad \text{step}_y = \operatorname{sgn}(d_y), \quad \text{step}_z = \operatorname{sgn}(d_z)$$

#### 3.1.2 Parametric Step Sizes ($t_{\Delta}$)
The parametric distance $t$ the ray must advance to traverse exactly 1.0 unit along each axis:
$$t_{\Delta x} = \begin{cases} \left|\frac{1}{d_x}\right| & d_x \ne 0 \\ \infty & d_x = 0 \end{cases}, \quad 
t_{\Delta y} = \begin{cases} \left|\frac{1}{d_y}\right| & d_y \ne 0 \\ \infty & d_y = 0 \end{cases}, \quad 
t_{\Delta z} = \begin{cases} \left|\frac{1}{d_z}\right| & d_z \ne 0 \\ \infty & d_z = 0 \end{cases}$$

#### 3.1.3 Initial Boundary Distances ($t_{\text{Max}}$)
Distance along the ray to the first integer voxel grid boundary:
$$t_{\text{Max}x} = \begin{cases} 
\frac{(\lfloor x_0 \rfloor + 1) - x_0}{d_x} & d_x > 0 \\
\frac{x_0 - \lfloor x_0 \rfloor}{|d_x|} & d_x < 0 \\
\infty & d_x = 0
\end{cases}$$
*(Equivalent definitions apply for $t_{\text{Max}y}$ and $t_{\text{Max}z}$)*.

### 3.2 Traversal Loop & Face Normal Invariant
In each iteration of the DDA loop:
1. Identify the minimum axis component among $(t_{\text{Max}x}, t_{\text{Max}y}, t_{\text{Max}z})$.
2. Advance the coordinate along that axis by $\text{step}_i$.
3. The surface normal of the entered face is **the negative of the stepping direction along that axis**:
   $$\mathbf{n} = -\text{step}_i \cdot \hat{\mathbf{e}}_i$$
4. Update $t_{\text{Max}i} \leftarrow t_{\text{Max}i} + t_{\Delta i}$.
5. Sample voxel grid at $(X, Y, Z)$. If non-air, terminate traversal.

```cpp
// ponytail: [Synchronous direct array access] -> [Chunk octree / LOD traversal if world height expands]
struct RaycastResult {
    bool hit = false;
    glm::ivec3 targetBlock = glm::ivec3(0);
    glm::ivec3 placeBlock  = glm::ivec3(0);
    glm::ivec3 faceNormal  = glm::ivec3(0);
    float distance = 0.0f;
};

RaycastResult FastVoxelTraversal(
    const glm::vec3& rayOrigin,
    const glm::vec3& rayDir,
    float maxReach,
    const std::function<bool(int, int, int)>& isSolidVoxel
) {
    RaycastResult result;
    
    // Initial integer voxel coordinate
    int x = static_cast<int>(std::floor(rayOrigin.x));
    int y = static_cast<int>(std::floor(rayOrigin.y));
    int z = static_cast<int>(std::floor(rayOrigin.z));

    int stepX = (rayDir.x > 0.0f) ? 1 : ((rayDir.x < 0.0f) ? -1 : 0);
    int stepY = (rayDir.y > 0.0f) ? 1 : ((rayDir.y < 0.0f) ? -1 : 0);
    int stepZ = (rayDir.z > 0.0f) ? 1 : ((rayDir.z < 0.0f) ? -1 : 0);

    const float INF = std::numeric_limits<float>::infinity();
    float tDeltaX = (stepX != 0) ? std::abs(1.0f / rayDir.x) : INF;
    float tDeltaY = (stepY != 0) ? std::abs(1.0f / rayDir.y) : INF;
    float tDeltaZ = (stepZ != 0) ? std::abs(1.0f / rayDir.z) : INF;

    float tMaxX = (stepX > 0) ? ((std::floor(rayOrigin.x) + 1.0f - rayOrigin.x) * tDeltaX)
                              : ((rayOrigin.x - std::floor(rayOrigin.x)) * tDeltaX);
    float tMaxY = (stepY > 0) ? ((std::floor(rayOrigin.y) + 1.0f - rayOrigin.y) * tDeltaY)
                              : ((rayOrigin.y - std::floor(rayOrigin.y)) * tDeltaY);
    float tMaxZ = (stepZ > 0) ? ((std::floor(rayOrigin.z) + 1.0f - rayOrigin.z) * tDeltaZ)
                              : ((rayOrigin.z - std::floor(rayOrigin.z)) * tDeltaZ);

    glm::ivec3 faceNormal(0);
    float currentT = 0.0f;

    // Check starting block (e.g. player inside water/block)
    if (isSolidVoxel(x, y, z)) {
        result.hit = true;
        result.targetBlock = glm::ivec3(x, y, z);
        result.faceNormal  = glm::ivec3(0, 1, 0); // Default fallback
        result.placeBlock  = result.targetBlock + result.faceNormal;
        result.distance    = 0.0f;
        return result;
    }

    while (currentT <= maxReach) {
        if (tMaxX < tMaxY) {
            if (tMaxX < tMaxZ) {
                currentT = tMaxX;
                tMaxX += tDeltaX;
                x += stepX;
                faceNormal = glm::ivec3(-stepX, 0, 0);
            } else {
                currentT = tMaxZ;
                tMaxZ += tDeltaZ;
                z += stepZ;
                faceNormal = glm::ivec3(0, 0, -stepZ);
            }
        } else {
            if (tMaxY < tMaxZ) {
                currentT = tMaxY;
                tMaxY += tDeltaY;
                y += stepY;
                faceNormal = glm::ivec3(0, -stepY, 0);
            } else {
                currentT = tMaxZ;
                tMaxZ += tDeltaZ;
                z += stepZ;
                faceNormal = glm::ivec3(0, 0, -stepZ);
            }
        }

        if (currentT > maxReach) break;

        if (isSolidVoxel(x, y, z)) {
            result.hit = true;
            result.targetBlock = glm::ivec3(x, y, z);
            result.faceNormal  = faceNormal;
            result.placeBlock  = result.targetBlock + faceNormal;
            result.distance    = currentT;
            return result;
        }
    }

    return result;
}
```

---

## 4. Custom Voxel Physics & Collision System

### 4.1 Player Bounding Volume Geometry
The player is parameterized as a rigid, axis-aligned bounding box (AABB) centered on horizontal coordinates $(x, z)$ with base at $y$:
- **Width ($w$):** $0.6\text{ m}$ (Extent $e_x = e_z = 0.3\text{ m}$)
- **Height ($h$):** $1.8\text{ m}$ (Standing), $1.5\text{ m}$ (Sneaking)
- **Eye Height:** $1.62\text{ m}$ (Standing), $1.35\text{ m}$ (Sneaking) above base position $\mathbf{P}_{\text{base}}$
- **Mathematical Definition:**
  $$\text{AABB}_{\text{player}}(\mathbf{P}) = \left[ \mathbf{P} + \begin{pmatrix} -0.3 \\ 0.0 \\ -0.3 \end{pmatrix}, \mathbf{P} + \begin{pmatrix} 0.3 \\ 1.8 \\ 0.3 \end{pmatrix} \right]$$

```
          +-----------------------+  Y_max = base.y + 1.8
          |                       |
          |       O Camera        |  Y_eye = base.y + 1.62
          |      -|-              |
          |       |               |
          |      / \              |
          +-----------------------+  Y_min = base.y
        X_min                   X_max
     base.x - 0.3            base.x + 0.3
```

### 4.2 Axis-Decoupled Collision Resolution Pipeline
Continuous swept collision against an arbitrary polyhedral soup requires iterative Minkowski root finding. However, in a cubic lattice, resolving **axis-by-axis ($Y \to X \to Z$)** is exact, non-penetrating, and mathematically optimal.

#### 4.2.1 Why Order $Y \to X \to Z$?
1. **Vertical Primacy:** Resolving $Y$ first guarantees that landing on surfaces immediately sets `isGrounded = true` before horizontal integration occurs.
2. **Ground Friction Stability:** Friction and auto-stepping depend entirely on the presence of ground support beneath the player's feet.
3. **Corner Gliding:** Moving diagonally into a wall does not stick; remaining unconstrained axes retain their full displacement component.

#### 4.2.2 Query Extents
For any axis displacement vector $\Delta \mathbf{r}$, the candidate voxel query bounds are clamped integer intervals:
$$X_{\min} = \lfloor \text{AABB}_{\min}.x \rfloor, \quad X_{\max} = \lfloor \text{AABB}_{\max}.x \rfloor$$
$$Y_{\min} = \lfloor \text{AABB}_{\min}.y \rfloor, \quad Y_{\max} = \lfloor \text{AABB}_{\max}.y \rfloor$$
$$Z_{\min} = \lfloor \text{AABB}_{\min}.z \rfloor, \quad Z_{\max} = \lfloor \text{AABB}_{\max}.z \rfloor$$

At most, a $0.6 \times 1.8 \times 0.6$ bounding box overlaps a $2 \times 3 \times 2 = 12$ voxel neighborhood at rest, and up to $3 \times 4 \times 3 = 36$ voxels during dynamic displacement.

### 4.3 Kinematic Equations & Environmental Dynamics

#### 4.3.1 Acceleration, Gravity, and Terminal Velocity
Let velocity $\mathbf{v} = (v_x, v_y, v_z)$:
- **Gravity Acceleration:** $g = -32.0\text{ m/s}^2$ (applied directly to $v_y$ each tick: $\Delta v_y = g \cdot \Delta t$).
- **Terminal Velocity:** $v_{\text{term}} = -78.4\text{ m/s}$ ($v_y \leftarrow \max(v_y, v_{\text{term}})$).
- **Jump Impulse:** Instantaneous upward velocity when on ground and Jump key pressed:
  $$v_{\text{jump}} = \sqrt{2 \cdot |g| \cdot h_{\text{jump}}} \approx \sqrt{2 \cdot 32.0 \cdot 1.25} \approx 8.944\text{ m/s}$$
  *(Guarantees clearing a $1.25\text{ m}$ elevation hurdle)*.

#### 4.3.2 Drag & Momentum Dissipation
Horizontal drag models deceleration when no input is supplied:
$$\mathbf{v}_{xz} \leftarrow \mathbf{v}_{xz} \cdot (1.0 - \mu_{\text{drag}})^{\Delta t \cdot 60}$$
- Ground Drag: $\mu_{\text{ground}} = 0.40$ (Rapid stop within $\approx 0.15\text{s}$)
- Air Drag: $\mu_{\text{air}} = 0.08$ (Conservation of ballistic trajectory)

### 4.4 Auto-Step Algorithm (0.5m / 0.6m Step-Up Resolution)
Minecraft allows stepping up slabs ($0.5\text{m}$) without jumping.
When horizontal movement along $X$ or $Z$ is impeded by a solid block face:
1. If the player is **not grounded**, auto-stepping is aborted (no mid-air wall climbing).
2. The engine executes a speculative collision probe:
   - Offset test AABB vertically upward by step height: $h_{\text{step}} = 0.55\text{ m}$ (0.5m slab + 0.05m clearance tolerance).
   - If the upward offset intersects a ceiling block, abort step.
   - Sweep horizontally across the remaining displacement vector $\Delta \mathbf{r}_{xz}$.
   - Sweep downward back onto the step surface until contact is re-established.
3. If the horizontal progress achieved via the stepped path exceeds the flat path, commit the stepped position.

```
Step Resolution Mechanics:
        Ceiling Check: [Is headspace clear?]
                 |
        +--[Up +0.55m]---> [Forward dx, dz]
        |                        |
     Obstacle (0.5m)        [Step Down onto Obstacle]
        |                        |
Player (Ground)              Committed!
```

### 4.5 Sneak Ledge-Falloff Prevention
While sneaking (`isSneaking == true` and `isGrounded == true`):
Before applying horizontal displacement $\Delta x$ or $\Delta z$:
1. Construct speculative bounding box at $(\mathbf{P}_x + \Delta x, \mathbf{P}_y, \mathbf{P}_z + \Delta z)$.
2. Probe downward by $0.05\text{ m}$:
   $$\text{AABB}_{\text{ground\_probe}} = \left[ \mathbf{P}_{\min} + \begin{pmatrix} \Delta x \\ -0.05 \\ \Delta z \end{pmatrix}, \mathbf{P}_{\max} + \begin{pmatrix} \Delta x \\ 0.0 \\ \Delta z \end{pmatrix} \right]$$
3. If no solid voxels intersect the probe box, clamp $\Delta x = 0$ and $\Delta z = 0$ along the offending axis. The player safely glides along the edge without falling.

### 4.6 Complete Physics Update Routine (C++20 Implementation)

```cpp
// ponytail: [Discrete per-axis resolution] -> [Continuous swept volume hull if speeds exceed 60 m/s]
struct AABB {
    glm::vec3 min;
    glm::vec3 max;

    bool Intersects(const AABB& other) const {
        return (min.x < other.max.x && max.x > other.min.x) &&
               (min.y < other.max.y && max.y > other.min.y) &&
               (min.z < other.max.z && max.z > other.min.z);
    }
};

class VoxelPhysicsController {
public:
    static constexpr float PLAYER_WIDTH      = 0.6f;
    static constexpr float PLAYER_HEIGHT     = 1.8f;
    static constexpr float SNEAK_HEIGHT      = 1.5f;
    static constexpr float EYE_OFFSET        = 1.62f;
    static constexpr float SNEAK_EYE_OFFSET  = 1.35f;
    static constexpr float STEP_HEIGHT       = 0.55f;
    static constexpr float GRAVITY           = -32.0f;
    static constexpr float TERMINAL_VELOCITY = -78.4f;
    static constexpr float JUMP_IMPULSE      = 8.944f;

    glm::vec3 position     = glm::vec3(0.0f, 64.0f, 0.0f);
    glm::vec3 velocity     = glm::vec3(0.0f);
    bool      isGrounded   = false;
    bool      isSprinting  = false;
    bool      isSneaking   = false;

    AABB GetCurrentAABB(const glm::vec3& pos) const {
        float h = isSneaking ? SNEAK_HEIGHT : PLAYER_HEIGHT;
        float halfW = PLAYER_WIDTH * 0.5f;
        return AABB{
            pos + glm::vec3(-halfW, 0.0f, -halfW),
            pos + glm::vec3( halfW, h,     halfW)
        };
    }

    void PhysicsTick(
        float dt,
        const glm::vec3& wishDir,
        bool jumpRequested,
        const std::function<bool(int, int, int)>& isSolid
    ) {
        // 1. Horizontal Acceleration
        float baseSpeed = isSneaking ? 1.295f : (isSprinting ? 5.612f : 4.317f);
        glm::vec3 targetVelXZ = wishDir * baseSpeed;

        float accelRate = isGrounded ? 15.0f : 4.0f; // Snappy ground, inertial air
        velocity.x += (targetVelXZ.x - velocity.x) * std::min(accelRate * dt, 1.0f);
        velocity.z += (targetVelXZ.z - velocity.z) * std::min(accelRate * dt, 1.0f);

        // 2. Vertical Jump & Gravity
        if (jumpRequested && isGrounded) {
            velocity.y = JUMP_IMPULSE;
            isGrounded = false;
        }

        velocity.y += GRAVITY * dt;
        if (velocity.y < TERMINAL_VELOCITY) {
            velocity.y = TERMINAL_VELOCITY;
        }

        // 3. Compute Displacement
        glm::vec3 displacement = velocity * dt;

        // 4. Ledge Safety (Sneaking)
        if (isSneaking && isGrounded) {
            ApplyLedgeClamp(displacement, isSolid);
        }

        // 5. Collision Resolution: Y-Axis (Vertical)
        isGrounded = false;
        ResolveAxisMovement(1, displacement.y, isSolid);

        // 6. Collision Resolution: Horizontal with Auto-Stepping
        ResolveHorizontalWithStep(displacement.x, displacement.z, isSolid);
    }

private:
    void ResolveAxisMovement(
        int axis,
        float delta,
        const std::function<bool(int, int, int)>& isSolid
    ) {
        if (std::abs(delta) < 1e-6f) return;

        position[axis] += delta;
        AABB box = GetCurrentAABB(position);

        int minX = static_cast<int>(std::floor(box.min.x));
        int maxX = static_cast<int>(std::floor(box.max.x));
        int minY = static_cast<int>(std::floor(box.min.y));
        int maxY = static_cast<int>(std::floor(box.min.y + (box.max.y - box.min.y)));
        int minZ = static_cast<int>(std::floor(box.min.z));
        int maxZ = static_cast<int>(std::floor(box.max.z));

        for (int x = minX; x <= maxX; ++x) {
            for (int y = minY; y <= maxY; ++y) {
                for (int z = minZ; z <= maxZ; ++z) {
                    if (!isSolid(x, y, z)) continue;

                    AABB blockBox{
                        glm::vec3(x, y, z),
                        glm::vec3(x + 1, y + 1, z + 1)
                    };

                    if (box.Intersects(blockBox)) {
                        if (axis == 1) { // Y-Axis
                            if (delta > 0.0f) { // Head bump
                                position.y = blockBox.min.y - (box.max.y - box.min.y);
                                velocity.y = 0.0f;
                            } else { // Landed on floor
                                position.y = blockBox.max.y;
                                velocity.y = 0.0f;
                                isGrounded = true;
                            }
                        } else if (axis == 0) { // X-Axis
                            position.x = (delta > 0.0f) ? (blockBox.min.x - PLAYER_WIDTH * 0.5f)
                                                        : (blockBox.max.x + PLAYER_WIDTH * 0.5f);
                            velocity.x = 0.0f;
                        } else if (axis == 2) { // Z-Axis
                            position.z = (delta > 0.0f) ? (blockBox.min.z - PLAYER_WIDTH * 0.5f)
                                                        : (blockBox.max.z + PLAYER_WIDTH * 0.5f);
                            velocity.z = 0.0f;
                        }
                        box = GetCurrentAABB(position);
                    }
                }
            }
        }
    }

    void ResolveHorizontalWithStep(
        float dx,
        float dz,
        const std::function<bool(int, int, int)>& isSolid
    ) {
        glm::vec3 initialPos = position;

        // Try standard flat resolution
        ResolveAxisMovement(0, dx, isSolid);
        ResolveAxisMovement(2, dz, isSolid);

        // Check if movement was blocked and auto-step is viable
        bool wasBlocked = (std::abs(position.x - (initialPos.x + dx)) > 1e-4f) ||
                          (std::abs(position.z - (initialPos.z + dz)) > 1e-4f);

        if (wasBlocked && isGrounded) {
            glm::vec3 flatResult = position;

            // Revert to initial position and attempt vertical step
            position = initialPos;
            
            // 1. Move up by STEP_HEIGHT
            ResolveAxisMovement(1, STEP_HEIGHT, isSolid);
            
            // 2. Move horizontally at stepped elevation
            ResolveAxisMovement(0, dx, isSolid);
            ResolveAxisMovement(2, dz, isSolid);

            // 3. Move down to snap back onto ground
            ResolveAxisMovement(1, -STEP_HEIGHT, isSolid);

            // If stepping did not advance beyond flat resolution, revert to flat
            float flatDistSq = glm::distance2(initialPos, flatResult);
            float stepDistSq = glm::distance2(initialPos, position);

            if (stepDistSq <= flatDistSq + 1e-4f) {
                position = flatResult;
            }
        }
    }

    void ApplyLedgeClamp(
        glm::vec3& disp,
        const std::function<bool(int, int, int)>& isSolid
    ) {
        // Test X displacement
        if (std::abs(disp.x) > 0.0f) {
            glm::vec3 probePos = position + glm::vec3(disp.x, -0.1f, 0.0f);
            if (!HasGroundSupport(probePos, isSolid)) {
                disp.x = 0.0f;
            }
        }
        // Test Z displacement
        if (std::abs(disp.z) > 0.0f) {
            glm::vec3 probePos = position + glm::vec3(0.0f, -0.1f, disp.z);
            if (!HasGroundSupport(probePos, isSolid)) {
                disp.z = 0.0f;
            }
        }
    }

    bool HasGroundSupport(
        const glm::vec3& pos,
        const std::function<bool(int, int, int)>& isSolid
    ) const {
        AABB box = GetCurrentAABB(pos);
        int minX = static_cast<int>(std::floor(box.min.x));
        int maxX = static_cast<int>(std::floor(box.max.x));
        int minY = static_cast<int>(std::floor(box.min.y - 0.1f));
        int minZ = static_cast<int>(std::floor(box.min.z));
        int maxZ = static_cast<int>(std::floor(box.max.z));

        for (int x = minX; x <= maxX; ++x) {
            for (int z = minZ; z <= maxZ; ++z) {
                if (isSolid(x, minY, z)) return true;
            }
        }
        return false;
    }
};
```

---

## 5. Block Interaction Loop (Break, Place, Validate)

```
                       RAYCAST (Reach: 5.0m)
                                |
               +----------------+----------------+
               | Hit Solid Voxel?                 |
               NO                                YES
               |                                  |
            [IDLE]             +------------------+------------------+
                               |                                     |
                         [LEFT MOUSE]                          [RIGHT MOUSE]
                               |                                     |
                       Start/Tick Breaking                 Placement Target:
                               |                           P = Target + Normal
                       Progress >= Hardness?                         |
                       NO             YES                  Intersects Player AABB?
                       |               |                   YES            NO
                  Show Cracks    Destroy Block;            |              |
                  (Stages 0-9)   Spawn Drop / Air       [REJECT]     Place Block;
                                                                     Decrement Stack
```

### 5.1 Reach Distance & Targeting
- **Maximum Reach Constraint:** $d_{\text{reach}} = 5.0\text{ meters}$.
- Euclidean distance measured from the camera eye position:
  $$\|\mathbf{P}_{\text{target\_voxel}} + 0.5 - \mathbf{P}_{\text{eye}}\| \le 5.0$$
- If the DDA ray traversal exceeds $t_{\text{Max}} > 5.0$, `RaycastResult.hit = false`, resetting active interaction timers.

### 5.2 Block Breaking Mechanism (Destruction FSM)
Block destruction requires continuous left-mouse depression while maintaining crosshair lock on the identical target voxel coordinate.

#### 5.2.1 Block Hardness & Break Time Formula
Each block type possesses a base hardness constant $H_{\text{block}}$:
- **Instant (Air, Tall Grass):** $H = 0.0\text{s}$
- **Dirt / Sand:** $H = 0.5\text{s}$
- **Wood Planks:** $H = 2.0\text{s}$
- **Cobblestone / Stone:** $H = 1.5\text{s}$
- **Obsidian:** $H = 50.0\text{s}$
- **Bedrock:** $H = -1.0$ (Indestructible; early out)

$$\Delta \text{Progress} = \frac{\Delta t \cdot M_{\text{tool}}}{H_{\text{block}}}$$
*(where $M_{\text{tool}}$ is the tool efficiency multiplier; default bare hands $= 1.0$)*.

#### 5.2.2 Crack Animation Stages
Break progress is normalized to $P \in [0.0, 1.0]$. The visual overlay crack stage is an integer $S \in [0..9]$ mapped via:
$$S = \min\left(9, \lfloor P \cdot 10.0 \rfloor\right)$$

#### 5.2.3 Cancellation Semantics
Breaking progress instantly resets to $0.0$ if:
1. The left mouse button is released.
2. The DDA raycast target coordinate changes:
   $$\mathbf{P}_{\text{target}}(t) \ne \mathbf{P}_{\text{target}}(t - \Delta t)$$
3. The player moves outside the $5.0\text{m}$ maximum reach envelope.

### 5.3 Block Placement & Anti-Suffocation Validation
When the right mouse button is triggered:
1. Retrieve placement coordinate:
   $$\mathbf{P}_{\text{place}} = \mathbf{P}_{\text{target}} + \mathbf{n}_{\text{face}}$$
2. **World Boundary Check:** Verify $0 \le \mathbf{P}_{\text{place}}.y < 256$ (Chunk height bounds).
3. **Occupancy Check:** Verify target cell is currently replaceable (Air or Fluid).
4. **Player AABB Self-Intersection Invariant:**
   Placing a block inside the player's own bounding box causes camera jitter, suffocation damage, and physics entanglement. Placement is **strictly rejected** if the proposed voxel AABB overlaps the player:

$$\text{AABB}_{\text{block}} = \left[ \mathbf{P}_{\text{place}}, \mathbf{P}_{\text{place}} + \begin{pmatrix} 1 \\ 1 \\ 1 \end{pmatrix} \right]$$
$$\text{If } \text{Intersects}(\text{AABB}_{\text{player}}, \text{AABB}_{\text{block}}) \implies \text{ABORT PLACEMENT}$$

```cpp
// ponytail: [Synchronous single-block placement] -> [Networked prediction/rollback buffer for MP]
bool TryPlaceBlock(
    const RaycastResult& hit,
    const VoxelPhysicsController& player,
    uint8_t blockTypeToPlace,
    std::function<void(const glm::ivec3&, uint8_t)> setWorldBlock,
    std::function<uint8_t(const glm::ivec3&)> getWorldBlock
) {
    if (!hit.hit || blockTypeToPlace == 0) return false;

    glm::ivec3 placePos = hit.placeBlock;

    // 1. World vertical height bounds
    if (placePos.y < 0 || placePos.y >= 256) return false;

    // 2. Cell must be empty (Air)
    if (getWorldBlock(placePos) != 0) return false;

    // 3. Player intersection validation
    AABB blockBox{
        glm::vec3(placePos),
        glm::vec3(placePos) + glm::vec3(1.0f)
    };

    if (blockBox.Intersects(player.GetCurrentAABB(player.position))) {
        return false; // Placement rejected: inside player volume
    }

    // 4. Commit block mutation
    setWorldBlock(placePos, blockTypeToPlace);
    return true;
}
```

---

## 6. Hotbar & Inventory Data Structure

### 6.1 Data Model & Memory Layout
In accordance with the Ponytail lazy senior developer standard: no dynamic container trees, no polymorphic item slots, and no redundant heap wrappers. A fixed-size contiguous array models the active hotbar.

```
       0       1       2       3       4       5       6       7       8
   +-------+-------+-------+-------+-------+-------+-------+-------+-------+
   | DIRT  | STONE | COBBLE| WOOD  | GLASS | BRICK | SAND  | TORCH | EMPTY |
   |  x64  |  x32  |  x64  |  x16  |  x8   |  x64  |  x12  |  x4   |  x0   |
   +-------+-------+-------+-------+-------+-------+-------+-------+-------+
               ^
          [Active Slot: 1]
```

```cpp
// ponytail: [9-slot fixed hotbar array] -> [36-slot full inventory + crafting matrix + chest container]
enum class BlockType : uint8_t {
    Air         = 0,
    Stone       = 1,
    Dirt        = 2,
    GrassBlock  = 3,
    Cobblestone = 4,
    WoodPlank   = 5,
    Glass       = 6,
    Brick       = 7,
    Sand        = 8,
    Bedrock     = 9,
    Count
};

struct ItemStack {
    BlockType type     = BlockType::Air;
    uint16_t  count    = 0;
    uint16_t  maxStack = 64;

    bool IsEmpty() const {
        return type == BlockType::Air || count == 0;
    }

    bool Decrement(uint16_t amount = 1) {
        if (count < amount) return false;
        count -= amount;
        if (count == 0) type = BlockType::Air;
        return true;
    }
};

class HotbarModel {
public:
    static constexpr size_t SLOT_COUNT = 9;
    std::array<ItemStack, SLOT_COUNT> slots;
    uint8_t selectedSlot = 0;

    void SelectSlot(uint8_t index) {
        if (index < SLOT_COUNT) {
            selectedSlot = index;
        }
    }

    void HandleScroll(float scrollDelta) {
        // Standard Minecraft scroll convention: scroll down moves slot index right
        int next = static_cast<int>(selectedSlot) - static_cast<int>(scrollDelta);
        while (next < 0) next += SLOT_COUNT;
        selectedSlot = static_cast<uint8_t>(next % SLOT_COUNT);
    }

    ItemStack& GetActiveItem() {
        return slots[selectedSlot];
    }

    const ItemStack& GetActiveItem() const {
        return slots[selectedSlot];
    }
};
```

---

## 7. Day/Night Cycle & Voxel Lighting Model

### 7.1 Celestial Mechanics & Sun Trajectory
The celestial cycle is parameterized by the world clock time $t_{\text{world}} \in [0, T_{\text{day}})$.
- **Standard Day Period:** $T_{\text{day}} = 1200\text{ seconds}$ ($20\text{ minutes}$).
- **Daylight/Night Breakdown:** $10\text{ min}$ Day, $7\text{ min}$ Night, $1.5\text{ min}$ Dawn/Dusk transitions.

#### 7.1.1 Celestial Orbit Vector
The sun and moon rotate about an inclined axial plane ($\delta = 10.0^\circ$ tilt to create natural shadows along $Z$):
$$\phi(t) = 2\pi \cdot \frac{t_{\text{world}}}{T_{\text{day}}}$$

$$\hat{\mathbf{L}}_{\text{sun}} = \begin{pmatrix} \cos(\phi) \\ \sin(\phi)\cos(\delta) \\ \sin(\phi)\sin(\delta) \end{pmatrix}, \quad \hat{\mathbf{L}}_{\text{moon}} = -\hat{\mathbf{L}}_{\text{sun}}$$

```
                       ZENITH (+Y)
                          ^
                          |       * Noon (phi = pi/2)
                          |      /
      Sunset (phi = pi)   |     /
   <----------------------+----------------------> Horizon (+X)
                          |   /
                          |  /
                          v * Midnight (phi = 3pi/2)
```

### 7.2 Directional Diffuse Voxel Face Tinting
Because voxel meshes consist exclusively of axis-aligned faces ($\pm X, \pm Y, \pm Z$), standard per-fragment normal evaluation is unnecessary. Normal lighting factors are statically evaluated per face normal or computed in the vertex shader.

#### 7.2.1 Classic Directional Face Occlusion Shading
To preserve depth readability even under flat ambient light, each cube face applies an empirical occlusion factor:
- **Top (+Y):** $K_{\text{face}} = 1.00$ (Direct zenith exposure)
- **Bottom (-Y):** $K_{\text{face}} = 0.50$ (Max occlusion / ground shadow)
- **North/South ($\pm Z$):** $K_{\text{face}} = 0.80$ (Transverse shadow)
- **East/West ($\pm X$):** $K_{\text{face}} = 0.60$ (Longitudinal shadow)

```cpp
float GetVoxelFaceOcclusion(const glm::ivec3& faceNormal) {
    if (faceNormal.y > 0) return 1.00f; // Top
    if (faceNormal.y < 0) return 0.50f; // Bottom
    if (faceNormal.z != 0) return 0.80f; // North / South
    if (faceNormal.x != 0) return 0.60f; // East / West
    return 1.00f;
}
```

#### 7.2.2 Ambient & Sun Color Interpolation
Sun elevation $E = \hat{\mathbf{L}}_{\text{sun}}.y$:
$$\alpha_{\text{day}} = \operatorname{smoothstep}(-0.20, 0.20, E)$$
$$\mathbf{C}_{\text{ambient}} = (1 - \alpha_{\text{day}})\mathbf{C}_{\text{night}} + \alpha_{\text{day}}\mathbf{C}_{\text{day}}$$
$$\mathbf{C}_{\text{sun}} = \mathbf{C}_{\text{sun\_color}} \cdot \max(0.0f, E)$$

#### 7.2.3 Final Surface Luminance
For a given face normal $\mathbf{n}$ and block material base color $\mathbf{C}_{\text{albedo}}$:
$$I_{\text{diffuse}} = \max\left(0.0, \mathbf{n} \cdot \hat{\mathbf{L}}_{\text{sun}}\right)$$
$$\mathbf{C}_{\text{final}} = \mathbf{C}_{\text{albedo}} \cdot K_{\text{face}} \cdot \left( \mathbf{C}_{\text{ambient}} + I_{\text{diffuse}} \mathbf{C}_{\text{sun}} \right)$$

```cpp
// ponytail: [Uniform vertex tint + directional sun] -> [Full 4-bit chunk light propagation (sky + block light)]
struct CelestialLighting {
    float timeOfDaySec = 300.0f; // 0 to 1200
    const float DAY_CYCLE_SEC = 1200.0f;

    glm::vec3 GetSunDirection() const {
        float phi = (timeOfDaySec / DAY_CYCLE_SEC) * glm::two_pi<float>();
        float tilt = glm::radians(10.0f);
        return glm::normalize(glm::vec3(
            std::cos(phi),
            std::sin(phi) * std::cos(tilt),
            std::sin(phi) * std::sin(tilt)
        ));
    }

    glm::vec3 GetSkyColor() const {
        float sunY = GetSunDirection().y;
        float dayFactor = glm::smoothstep(-0.2f, 0.2f, sunY);
        glm::vec3 daySky(0.5f, 0.7f, 1.0f);
        glm::vec3 nightSky(0.02f, 0.02f, 0.05f);
        return glm::mix(nightSky, daySky, dayFactor);
    }
};
```

---

## 8. Ponytail Engineering Ledger (Pragmatic Ceilings & Upgrade Paths)

Every architectural decision balances minimal initial complexity (YAGNI) with clean upgrade interfaces. The table below codifies every deliberate ceiling embedded in this specification.

| Subsystem | Implemented Architecture | Explicit Limitation / Ceiling | Trigger for Upgrade | Upgrade Path |
| :--- | :--- | :--- | :--- | :--- |
| **Camera** | Pitch/Yaw Euler Clamping | No camera roll or acrobatic 6-DOF movement. | Elytra flight, underwater swimming rotation. | Convert `CameraOrientation` to quaternion representation ($Slerp$). |
| **Raycast** | Linear Amanatides-Woo DDA | Traverses every single empty voxel air cell up to 5.0m reach. | Extended reach (>32m), raytraced shadow casting. | Implement Hierarchical DDA / Octree skip traversal. |
| **Physics** | Axis-Decoupled Discrete Sweep ($Y \to X \to Z$) | Tunneling possible if velocity exceeds $1.0\text{ block/tick}$ ($>60\text{ m/s}$). | High-speed explosions, Elytra flight, rail carts. | Sub-step physics ticks ($\Delta t / N$) or continuous swept AABB Minkowski solver. |
| **Collision Hull** | Single Rigid AABB ($0.6 \times 1.8\text{m}$) | Cannot rotate hull; no crawling or diagonal sliding hulls. | Crawling through 1-block crawlspaces or boats. | Multi-box composite collision hierarchy. |
| **Stepping** | Speculative Step Resolver ($0.55\text{m}$) | Only resolves single rectangular step-ups; no smooth slope climbs. | Non-voxel terrain meshes or custom stairs geometry. | Generalized swept upward ramp tester. |
| **Interaction** | Synchronous Local State Mutation | Single-player authoritative; mutations apply immediately to RAM. | Multiplayer server integration. | Client-side optimistic prediction with server reconciliation queue. |
| **Inventory** | Fixed 9-Slot Linear Array | No drag-and-drop slots, inventory paging, or 2x2 crafting grid. | Survival crafting and container chests. | `InventoryContainer` base class with slot capability interfaces. |
| **Lighting** | Empirical Directional Normal Shading | No light diffusion through caves; dark indoors during daytime. | Underground exploration, torches, interior structures. | 16-level cellular automata BFS light propagation grid. |

---

## 9. Architectural Verification & Edge Cases

### 9.1 Boundary Value Edge Cases
1. **DDA Division by Zero:** When look vector components $d_x, d_y, \text{ or } d_z = 0$, $t_{\Delta i}$ evaluates to IEEE 754 $+\infty$. The loop safely avoids selection of that axis via standard comparison (`tMax < INF`), ensuring zero branching penalties.
2. **Player Straddling Chunk Boundaries:** Because physics checks sample world integer voxel coordinates directly rather than local chunk indices, chunk boundaries ($X \pmod{16} == 0$) are transparent to the collision resolver.
3. **Corner Ledge Sneak Trap:** Sneaking along an exterior convex corner tests both $X$ and $Z$ axes independently. Clamping applies to individual axes, allowing the player to safely trace the perimeter of a 1-block pillar without stalling movement.
4. **Auto-Step into Low Ceiling:** If an obstacle is $0.5\text{m}$ high but the ceiling clearance above it is $< 1.8\text{m}$, the speculative vertical sweep hits the ceiling block, immediately aborting the step and preventing suffocation clipping.

---

### Max-Pro Intellectual Probe
> *With our axis-decoupled $Y \to X \to Z$ collision resolver guaranteeing zero tunneling up to $60\text{ m/s}$, consider what happens when a player falls into a vertical 1x1 shaft and hits an auto-step slab at terminal velocity ($-78.4\text{ m/s}$). Given that $\Delta y = -78.4 \times \frac{1}{60} = -1.306\text{ meters}$, which exceeds the $1.0\text{m}$ single-voxel lattice thickness, how would you design an adaptive sub-stepping invariant in `PhysicsTick` that maintains strict $O(1)$ efficiency without incurring arbitrary loop overhead during normal walking?*
