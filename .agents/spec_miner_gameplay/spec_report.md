# Canonical Gameplay & Voxel Mechanics Specification Report
**Project:** Minecraft Desktop — Universal 1-Click Native Edition  
**Miner Archetype:** spec_miner_gameplay  
**Working Directory:** g:/minecraft_desktop/.agents/spec_miner_gameplay/  
**Authority Sources:**
- ORIGINAL_REQUEST.md
- docs/02_CORE_GAMEPLAY_FEATURES.md
- docs/06_OFFICIAL_MINECRAFT_CANONICAL_SPEC.md
- docs/01_ARCHITECTURE_AND_RUNTIME.md
- docs/03_WORLD_GENERATION_AND_CHUNKS.md
- docs/04_ASSET_PIPELINE_AND_AUDIO.md
- Decompiled Official Minecraft Java Edition Kinematic & Gameplay Standard

---

## 1. Executive Summary

This specification report documents the complete canonical gameplay mechanics, physics equations, discrete kinematic constants, interaction state machines, inventory architectures, crafting recipes, and survival systems required for full behavioral fidelity with official Minecraft Java Edition. Every formula and constant is grounded in authoritative project specifications and official decompiled reference standards, adhering strictly to Ponytail minimalist principles (zero unnecessary abstractions, O(1) spatial queries, cache-aligned data structures).

---

## 2. Features Discovered

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|----------|---------|-------------|--------|---------|----------------|----------------|
| 1 | Physics | Axis-Decoupled Collision (Y -> X -> Z) | Resolves player AABB collisions against integer voxel lattice axis-by-axis, guaranteeing ground contact before horizontal integration | Displaced AABB P + v*dt, voxel query | New non-penetrating position P', zeroed velocity component on collision | Clamps to integer block face boundary; zero tunneling <= 60 m/s | 02_CORE_GAMEPLAY_FEATURES.md:300 |
| 2 | Physics | Player Hitbox Dimensions | AABB dimensions for standing and sneaking states | Player stance state (isSneaking) | Standing: 0.6 x 1.8 x 0.6m; Sneaking: 0.6 x 1.5 x 0.6m | Non-rotatable AABB aligned strictly to world axes | 02_CORE_GAMEPLAY_FEATURES.md:280, 06_CANONICAL_SPEC:48 |
| 3 | Physics | Eye Height & Camera Offset | Vertical distance from player base position to camera lens | Stance state (isSneaking) | Standing: +1.62m; Sneaking: +1.35m | Clamped to pitch [-89 deg, +89 deg] to prevent gimbal singularity | 02_CORE_GAMEPLAY_FEATURES.md:284, 06_CANONICAL_SPEC:49 |
| 4 | Physics | Gravity & Vertical Drag | Gravitational downward acceleration with exponential terminal velocity damping | Tick dt, vertical velocity v_y | v_y <- (v_y - 0.08) * 0.98 per tick (g = 0.08 blk/tick^2 = 32.0 m/s^2) | Clamped at terminal velocity v_term = -3.92 blk/tick (-78.4 m/s) | 06_CANONICAL_SPEC:50-53, 02_CORE_GAMEPLAY:318 |
| 5 | Physics | Ground Friction & Air Damping | Horizontal momentum dissipation per tick | Ground contact state (isGrounded), v_x, v_z | Ground: v_xz * 0.546; Air: v_xz * 0.98 per tick | In continuous 60Hz mode: Ground drag mu=0.40, Air drag mu=0.08 | 06_CANONICAL_SPEC:51-52, 02_CORE_GAMEPLAY:326 |
| 6 | Physics | Jump Impulse | Instantaneous vertical velocity impulse applied when jumping from ground | Jump keypress, isGrounded == true | v_y = 0.42 blk/tick = 8.4 m/s (8.944 m/s at 60Hz); reaches 1.25m apex | Ignored if isGrounded == false (no mid-air double jump) | 06_CANONICAL_SPEC:54, 02_CORE_GAMEPLAY:323 |
| 7 | Physics | Auto-Step Resolution | Allows stepping up 0.5m / 0.6m obstacles (slabs/blocks) without jumping | Horizontal obstruction collision, isGrounded == true | Speculative upward probe +0.55m / 0.6m, advance, snap down | Aborts if upward probe hits ceiling (<1.8m clearance) or if in mid-air | 02_CORE_GAMEPLAY_FEATURES.md:332, 06_CANONICAL_SPEC:55 |
| 8 | Physics | Sneak Ledge-Clamp | Prevents player from falling off edges of blocks while sneaking | Sneak input (isSneaking == true), wish displacement | Downward probe -0.05m at candidate position; clamps dx=0 or dz=0 if unsupported | Independent per axis; enables tracing convex corners safely | 02_CORE_GAMEPLAY_FEATURES.md:354 |
| 9 | Physics | Dynamic FOV Warping | Dynamic FOV adjustment reflecting movement velocity state | Velocity state (walk, sprint, sneak) | FOV multiplier: Sprint = 1.15x, Sneak = 0.90x, Base = 1.0x; decay rate lambda = 12.0 s^-1 | Clamped within safe FOV bounds | 02_CORE_GAMEPLAY_FEATURES.md:119 |
| 10 | Interaction | Amanatides-Woo DDA Raycast | 3D parametric fast voxel traversal stepping through every intersected lattice cell | Eye origin P_0, unit direction d, reach limit | Target block (X,Y,Z), face normal n, distance t | Div by zero handles t_delta = inf; terminates at reach distance | 02_CORE_GAMEPLAY_FEATURES.md:128 |
| 11 | Interaction | Reach Distance Constraint | Maximum interaction envelope from camera eye | Player game mode | Survival: 4.5 blocks; Creative: 5.0 blocks | Ray traversal drops hit if t > d_reach | 06_CANONICAL_SPEC:56, 02_CORE_GAMEPLAY:607 |
| 12 | Interaction | Face Normal Invariant | Surface normal of block face entered during raycast | DDA axis step direction step_i | n = -step_i * e_i; placement position P_place = P_target + n | Identifies exact placement orientation among +-X, +-Y, +-Z | 02_CORE_GAMEPLAY_FEATURES.md:176 |
| 13 | Interaction | Block Destruction FSM | Progressive block breaking via continuous Left Mouse depression on same target | Target voxel, elapsed tick dt, tool efficiency M_tool | Break progress P in [0.0, 1.0], visual crack stages 0..9 | Instant reset to 0.0 on target shift, mouse release, or reach breach | 02_CORE_GAMEPLAY_FEATURES.md:612 |
| 14 | Interaction | Block Hardness & Break Times | Material-specific breaking resistance and tool tier calculation | Block type, active tool, harvestability flag | dP = (dt * M_tool) / (Hardness * divisor); destroys when P >= 1.0 | Bedrock (H = -1.0) is indestructible; Air (H = 0.0) breaks in 1 tick | 02_CORE_GAMEPLAY_FEATURES.md:615, 06_CANONICAL_SPEC:106 |
| 15 | Interaction | Anti-Suffocation Block Placement | Rejects placing a solid block inside the player's own bounding box | Right Mouse click, placement target P_place, player AABB | Block placed and inventory stack decremented by 1 if valid | Rejects if Intersects(AABB_player, AABB_block) == true or Y not in [0, 255] | 02_CORE_GAMEPLAY_FEATURES.md:638 |
| 16 | Inventory | Hotbar 9-Slot Fixed Array | Immediate access item slots mapped to keyboard 1-9 and mouse scroll | Key numeric 1-9, mouse wheel scroll +-1 | Active selected slot index [0..8], held item stack | Index wraps modulo 9: (slot - delta) mod 9 | 02_CORE_GAMEPLAY_FEATURES.md:688 |
| 17 | Inventory | Full Inventory Hierarchy | Complete player item container structure | Inventory GUI toggle ('E' key) | 9 hotbar slots + 27 main storage slots + 4 armor slots + 1 offhand slot | Out-of-bounds clicks drop item onto ground | 02_CORE_GAMEPLAY:703, Canonical Java Standard |
| 18 | Inventory | Item Stack Size Limits | Maximum allowable item count per discrete inventory slot | Item definition / type | Blocks/materials: 64; Snowballs/buckets/eggs/pearls: 16; Tools/armor: 1 | Cannot exceed maxStack; extra items overflow to next available slot | 02_CORE_GAMEPLAY:721, Canonical Java Standard |
| 19 | Inventory | Slot Drag & Split Mechanics | Mouse drag distribution across multiple inventory slots | Left-drag (split evenly) or Right-drag (place 1 each) | Distributes held stack evenly or 1-per-slot across touched slots | Remainder stays in mouse cursor if not evenly divisible | Canonical Minecraft GUI Specification |
| 20 | Crafting | 2x2 Player Inventory Matrix | Embedded 4-slot crafting grid in player inventory screen | 4 input slots (2 x 2), recipe pattern matcher | 1 output slot containing crafted item(s) | Output disabled if no recipe matches; takes 1 from each input on take | Canonical Java Specification |
| 21 | Crafting | 3x3 Crafting Table Matrix | 9-slot crafting grid accessed by right-clicking Crafting Table block | 9 input slots (3 x 3), recipe pattern matcher | 1 output slot; unlocks advanced tools, armor, mechanisms | Unused inputs remain in grid; dropping grid contents on GUI close | Canonical Java Specification |
| 22 | Survival | Health & Damage Immunity | 20 HP health pool with invulnerability frames | Damage source (fall, suffocation, void, attack) | HP deduction; 10-tick (0.5s) post-hit damage immunity; red flash | HP clamped [0, 20]; player death triggered at HP <= 0 | Canonical Java Specification |
| 23 | Survival | Hunger & Exhaustion System | Food level, saturation pool, and exhaustion tracking | Activity (sprint, jump, mine), eating food items | Exhaustion accumulation [0.0, 4.0]; deducts saturation then food | Sprint disabled when hunger <= 6; starvation damage when hunger == 0 | Canonical Java Specification |
| 24 | Survival | Fall Damage Calculation | Kinetic impact damage from falling from heights | Fall distance d_fall (blocks fallen without landing) | Damage = max(0, ceil(d_fall - 3.0)) | Water landing of depth >= 1 resets d_fall = 0 (zero damage) | Canonical Java Specification |
| 25 | Survival | World Item Drop Entity | Floating, rotating, bobbing 3D item entity in world space | Item dropped by player (Q key) or block destruction | Entity position, sine bobbing 0.1*sin(pi*t), rotation 180 deg/s | Pickup delay 10-40 ticks; pickup radius 1.5-2.0m; despawns in 5 min | ORIGINAL_REQUEST:48, Canonical Java Standard |
| 26 | Visuals | Hand Swing Animation | First-person arm swing rotation on tool use/mining | Left click (attack/break) or Right click (place/use) | 6-tick (0.3s) sinusoidal pitch/yaw swing of player arm model | Can re-trigger continuously on hold | Canonical Java Specification |
| 27 | Game Modes | Creative vs. Survival Rules | Behavioral rules differentiating play styles | Mode toggle (gamemode creative/survival) | Survival: finite HP, mining times, item consumption; Creative: instant break, invulnerable, flying | Creative reach 5.0m, Survival reach 4.5m | 06_CANONICAL_SPEC:56, ORIGINAL_REQUEST:20 |
| 28 | Environment | Day/Night Celestial Cycle | 20-minute world clock driving sun/moon orbit and lighting | World time t in [0, 1200s] | Orbit vector L_sun with 10 deg axial tilt, dynamic ambient/sky color | Smooth day/night transition via smoothstep(-0.2, 0.2, E) | 02_CORE_GAMEPLAY_FEATURES.md:769 |
| 29 | Environment | Directional Face Shading | Static occlusion shading based on cube face normal | Quad normal n in {+-X, +-Y, +-Z} | Top: 1.00, Bottom: 0.50, North/South: 0.80, East/West: 0.60 | Invariant across all solid blocks; preserves 3D depth perception | 02_CORE_GAMEPLAY_FEATURES.md:795 |
| 30 | Audio | Procedural Sound Synthesizer | Real-time procedural math waveforms for game events | Sound event trigger (Click, Step, Jump, Break, Place) | 44.1 kHz PCM audio stream: square, triangle, LFSR noise | Zero loose .wav files; 16-voice polyphonic software mixer | 04_ASSET_PIPELINE_AND_AUDIO.md:358 |

---

## 3. Edge Cases & Boundary Behaviors

| # | Feature | Input / Condition | Observed Canonical Behavior |
|---|---------|-------------------|-----------------------------|
| 1 | DDA Raycast | Look vector parallel to coordinate axis (dx = 0 or dy = 0 or dz = 0) | t_delta_i = 1.0 / |d_i| = inf. Loop condition t_Max_i < inf ensures axis is never stepped, preventing zero-division crash. |
| 2 | Collision Resolution | Player falling at terminal velocity (-78.4 m/s) | Single tick displacement dy = -78.4 * 0.05 = -3.92m (1.306m at 60Hz). Query checks candidate voxel interval [floor(y + dy), ceil(y)], snapping player to top of highest solid floor without tunneling. |
| 3 | Auto-Step | Obstacle height 0.5m, but ceiling height above is < 1.8m | Speculative upward probe hits ceiling block. Auto-step immediately aborts; player remains at flat obstructed position without clipping into ceiling. |
| 4 | Auto-Step | Player is in mid-air (isGrounded == false) and collides with block edge | Auto-step logic requires isGrounded == true. Mid-air auto-step is skipped; player falls down block face normally without wall-climbing. |
| 5 | Sneak Ledge-Clamp | Player sneaks backward off a 1-block pillar | Downward probe at (P + delta_r) detects no solid support beneath feet. Displacement along both X and Z is clamped to 0. Player cannot walk off ledge. |
| 6 | Sneak Ledge-Clamp | Player sneaks around a convex corner of a ledge | Axes are tested independently. If X is unsupported but Z remains supported, X displacement is clamped while Z displacement proceeds, enabling smooth corner tracing. |
| 7 | Block Placement | Player looks straight down at feet and right-clicks with block in hand | Candidate placement AABB [P, P + 1] directly overlaps player's standing AABB. Placement is rejected (Intersects == true). Player is not suffocated or glitched into block. |
| 8 | Block Placement | Player attempts placement at Y = 256 or Y = -1 | World height bounds check (0 <= Y < 256) fails. Placement is silently rejected. |
| 9 | Block Breaking | Player moves crosshair off target block mid-mining or releases mouse | Breaking progress P immediately resets to 0.0. Crack animation stages clear to 0. |
| 10 | Block Breaking | Player attempts to break Bedrock (H = -1.0) in Survival | Hardness check detects negative value. Break progress increment is 0. Bedrock is unbreakable in Survival mode. |
| 11 | Inventory Drag | Dragging stack of 7 items across 3 empty slots with left-mouse held | 7 / 3 = 2 items per slot. 2 items placed in each of the 3 slots (total 6). 1 remainder item stays in player's mouse cursor stack. |
| 12 | Fall Damage | Player falls 3.0 blocks or less | ceil(3.0 - 3.0) = 0. Exactly zero fall damage taken. |
| 13 | Fall Damage | Player falls 23 blocks onto solid ground | Damage = ceil(23.0 - 3.0) = 20 HP. Deals 20 damage (10 full hearts), causing instant player death. |
| 14 | Fall Damage | Player falls 50 blocks into a 1-block deep water pool | Contact with water resets vertical velocity and fall distance accumulator to 0.0. Zero damage received regardless of fall height. |
| 15 | Inventory Quick Transfer | Shift-clicking an item in Hotbar while Main Inventory is full | Target container has no available slot matching item type with space. Shift-click is a no-op; item remains in current slot. |
| 16 | Diagonal Movement | Player presses 'W' and 'D' simultaneously | Raw input (+-1, 0, +-1) has norm sqrt(2) ~ 1.414. Wish direction is normalized to unit length ||d_wish|| = 1.0, preventing diagonal speed exploit. |
| 17 | Chunk Boundary Traversal | Player walks across chunk boundary (X = 15 -> 16) | Collision queries operate on world global integer coordinates; chunk boundary is mathematically transparent with zero physics hitch. |

---

## 4. Deep-Dive: Canonical Player Kinematics & Physics Engine

### 4.1 Coordinate Space, Units & Units Conversion
- **Coordinate Space:** Right-Handed Cartesian System
  - +X: East
  - +Y: Up (Zenith / Elevation)
  - +Z: South
- **Base Spatial Unit:** 1.0 unit = 1.0 meter = 1.0 block width.
- **Angles:** Yaw $\psi \in [0^\circ, 360^\circ)$, Pitch $\theta \in [-89.0^\circ, +89.0^\circ]$.
- **Camera Vector Mathematics:**
  $\mathbf{F}_{\text{look}} = \begin{pmatrix} \cos(\theta)\sin(\psi) \\ \sin(\theta) \\ -\cos(\theta)\cos(\psi) \end{pmatrix}$
  $\mathbf{F}_{\text{planar}} = \begin{pmatrix} \sin(\psi) \\ 0 \\ -\cos(\psi) \end{pmatrix}, \quad \mathbf{R}_{\text{planar}} = \begin{pmatrix} \cos(\psi) \\ 0 \\ \sin(\psi) \end{pmatrix}$

### 4.2 Player Hitbox Geometry
- **Standing AABB:**
  - Width: 0.6m (Extent [-0.3m, +0.3m] along X and Z)
  - Height: 1.8m ([0.0m, +1.8m] along Y)
  - Eye Height: +1.62m above base position ($\mathbf{P}_{\text{eye}} = \mathbf{P}_{\text{base}} + (0, 1.62, 0)$)
  - Bounding Box Definition: $\text{AABB}_{\text{standing}}(\mathbf{P}) = [\mathbf{P} + (-0.3, 0.0, -0.3), \mathbf{P} + (0.3, 1.8, 0.3)]$
- **Sneaking AABB:**
  - Width: 0.6m (Extent [-0.3m, +0.3m] along X and Z)
  - Height: 1.5m ([0.0m, +1.5m] along Y)
  - Eye Height: +1.35m above base position ($\mathbf{P}_{\text{eye}} = \mathbf{P}_{\text{base}} + (0, 1.35, 0)$)
  - Bounding Box Definition: $\text{AABB}_{\text{sneaking}}(\mathbf{P}) = [\mathbf{P} + (-0.3, 0.0, -0.3), \mathbf{P} + (0.3, 1.5, 0.3)]$
- **Auto-Step Clearance:** 0.6m canonical (0.55m implementation clearance for 0.5m half-slabs).

### 4.3 Locomotion Kinematic Speeds
- **Base Walking Speed:** $v_{\text{walk}} = 4.317\text{ m/s} = 0.21585\text{ blk/tick}$ (at 20 TPS).
- **Sprinting Speed:** $v_{\text{sprint}} = 1.30 \times v_{\text{walk}} \approx 5.612\text{ m/s} = 0.2806\text{ blk/tick}$.
  - Requires hunger level > 6 (> 3 food shanks).
  - Cancelled if wish direction moves backward ($\mathbf{d}_{\text{wish}} \cdot \mathbf{F}_{\text{planar}} < 0$).
- **Sneaking Speed:** $v_{\text{sneak}} = 0.30 \times v_{\text{walk}} \approx 1.295\text{ m/s} = 0.0648\text{ blk/tick}$.
- **Input Direction Normalization:**
  Raw keyboard input $\mathbf{i} = (i_x, 0, i_z) \in \{-1, 0, 1\}^2$ is normalized to unit length to prevent diagonal speed exploit:
  $\mathbf{d}_{\text{wish}} = \frac{i_x \mathbf{R}_{\text{planar}} + i_z \mathbf{F}_{\text{planar}}}{\|i_x \mathbf{R}_{\text{planar}} + i_z \mathbf{F}_{\text{planar}}\|}$ (if $\|\mathbf{i}\| > 0$, else $\mathbf{0}$).
- **Dynamic Field of View (FOV) Formula:**
  $\text{FOV}_{\text{target}} = \begin{cases} \text{FOV}_{\text{base}} \times 1.15 & \text{if sprinting} \\ \text{FOV}_{\text{base}} \times 0.90 & \text{if sneaking} \\ \text{FOV}_{\text{base}} & \text{standard} \end{cases}$
  $\text{FOV}(t + \Delta t) = \text{FOV}(t) + (\text{FOV}_{\text{target}} - \text{FOV}(t)) \cdot (1 - e^{-\lambda \Delta t}), \quad \lambda = 12.0\text{ s}^{-1}$

### 4.4 Gravitation, Friction & Jump Impulses
- **Canonical Tick Model (20 TPS, $\Delta t = 0.05\text{s}$):**
  - **Gravity:** Applied to $v_y$ each tick:
    $v_y \leftarrow (v_y - 0.08) \times 0.98$
  - **Terminal Falling Velocity:**
    $v_{\text{term}} = \frac{-0.08 \times 0.98}{1 - 0.98} = -3.92\text{ blk/tick} = -78.4\text{ m/s}$
  - **Horizontal Drag (Air):** $v_{x,z} \leftarrow v_{x,z} \times 0.98$.
  - **Ground Friction:** $v_{x,z} \leftarrow v_{x,z} \times (S \times 0.91)$, where standard block friction $S = 0.6 \implies 0.546$. Slippery ice is $S = 0.98 \implies 0.8918$.
  - **Jump Velocity:** Instantaneous upward velocity when grounded:
    $v_y = 0.42\text{ blk/tick} = 8.4\text{ m/s}$
    When sprinting, horizontal velocity receives an additional vector boost of +0.2 blk/tick in wish direction.
    Jump apex reaches 1.252m, clearing 1-block obstacles and half-slabs cleanly.
- **Continuous Engine Model (60 Hz Fixed Timestep, $\Delta t = 1/60\text{s}$):**
  - Gravity: $g = -32.0\text{ m/s}^2$ ($v_y \leftarrow \max(v_y + g \Delta t, -78.4\text{ m/s})$).
  - Ground Drag: $\mu_{\text{ground}} = 0.40$; Air Drag: $\mu_{\text{air}} = 0.08$.
  - Ground Acceleration: $15.0\text{ s}^{-1}$; Air Acceleration: $4.0\text{ s}^{-1}$.
  - Jump Impulse: $v_{\text{jump}} = \sqrt{2 \cdot 32.0 \cdot 1.25} \approx 8.944\text{ m/s}$.

### 4.5 Collision Resolution Pipeline (Y -> X -> Z)
1. **Vertical (Y) Sweep First:**
   - Displace player by $\Delta y = v_y \Delta t$.
   - Query integer blocks in candidate range $[\lfloor x - 0.3 \rfloor .. \lceil x + 0.3 \rceil] \times [\lfloor y \rfloor .. \lceil y + 1.8 \rceil] \times [\lfloor z - 0.3 \rfloor .. \lceil z + 0.3 \rceil]$.
   - If downward collision detected: set $y = \text{block}_{\text{top}}$, $v_y = 0$, isGrounded = true.
   - If upward collision detected (head bump): set $y = \text{block}_{\text{bottom}} - 1.8$, $v_y = 0$.
2. **Horizontal (X then Z) Sweep with Auto-Step:**
   - Attempt flat displacement $\Delta x, \Delta z$.
   - If horizontal collision encountered AND isGrounded == true:
     - Test speculative step: move up by +0.55m (verify headroom clearance).
     - Move horizontally across full displacement $\Delta x, \Delta z$.
     - Move down -0.55m to rest upon obstacle surface.
     - If stepped horizontal progress exceeds flat resolution, commit stepped position; otherwise retain flat collision result.
3. **Ledge Fall-Off Prevention (Sneaking):**
   - If isSneaking == true and isGrounded == true:
     - For candidate $\Delta x$: probe downward at $y - 0.05\text{m}$. If unsupported, set $\Delta x = 0$.
     - For candidate $\Delta z$: probe downward at $y - 0.05\text{m}$. If unsupported, set $\Delta z = 0$.

---

## 5. Deep-Dive: Voxel Interaction & Raymarching Mechanics

### 5.1 Amanatides-Woo Fast Voxel Traversal Derivation
Given eye ray $\mathbf{R}(t) = \mathbf{P}_0 + t \cdot \hat{\mathbf{d}}$ where $\|\hat{\mathbf{d}}\| = 1.0$:
- Initial integer cell: $X = \lfloor x_0 \rfloor, Y = \lfloor y_0 \rfloor, Z = \lfloor z_0 \rfloor$.
- Step directions: $\text{step}_i = \operatorname{sgn}(d_i) \in \{-1, 0, 1\}$.
- Parametric increments: $t_{\Delta i} = |1 / d_i|$ (IEEE 754 evaluates 1/0 as infinity).
- Initial boundary distance:
  $t_{\text{Max}i} = \begin{cases} \frac{(\lfloor p_i \rfloor + 1) - p_i}{d_i} & \text{if } d_i > 0 \\ \frac{p_i - \lfloor p_i \rfloor}{|d_i|} & \text{if } d_i < 0 \\ \infty & \text{if } d_i = 0 \end{cases}$
- Iteration step: Select axis with minimum $t_{\text{Max}}$. Advance coordinate $X_i \leftarrow X_i + \text{step}_i$, record face normal $\mathbf{n} = -\text{step}_i \hat{\mathbf{e}}_i$, and update $t_{\text{Max}i} \leftarrow t_{\text{Max}i} + t_{\Delta i}$.
- Max Reach Cutoff: $t \le 4.5\text{m}$ (Survival) or $t \le 5.0\text{m}$ (Creative).

### 5.2 Block Hardness, Tool Multipliers & Break Time Formulas
- **Block Hardness Values (H):**
  - Air / Plant / Flower: 0.0 (Instant break, 1 tick)
  - Leaves: 0.2
  - Dirt / Grass / Sand / Gravel: 0.5
  - Wood Logs / Wood Planks: 2.0
  - Stone: 1.5
  - Cobblestone: 2.0
  - Iron Ore: 3.0
  - Obsidian: 50.0
  - Bedrock: -1.0 (Indestructible in Survival)
- **Tool Multipliers ($M_{\text{tool}}$):**
  - Hand / Unarmed: 1.0x
  - Wooden Tool: 2.0x
  - Stone Tool: 4.0x
  - Iron Tool: 6.0x
  - Diamond Tool: 8.0x
  - Gold Tool: 12.0x
  - Netherite Tool: 9.0x
- **Break Time Formula (Official Java Edition):**
  $\text{Damage Per Tick} = \frac{M_{\text{tool}}}{\text{Hardness} \times \text{divisor}}$
  where:
  - divisor = 30 if the tool is the correct tool type AND meets the harvest tier requirement.
  - divisor = 100 if incorrect tool or cannot harvest drops.
  $\text{Break Time (seconds)} = \frac{\text{Hardness} \times \text{divisor}}{20 \times M_{\text{tool}}}$
- **Representative Break Times (Seconds):**
  | Block | Hardness | Bare Hand | Wood Tool | Stone Tool | Iron Tool | Diamond Tool |
  | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
  | **Dirt / Sand** | 0.5 | 0.75s | 0.40s (Shovel) | 0.20s (Shovel) | 0.15s (Shovel) | 0.10s (Shovel) |
  | **Wood Planks** | 2.0 | 3.00s | 1.50s (Axe) | 0.75s (Axe) | 0.50s (Axe) | 0.40s (Axe) |
  | **Cobblestone** | 2.0 | 10.00s* | 1.50s (Pickaxe) | 0.75s (Pickaxe) | 0.50s (Pickaxe) | 0.40s (Pickaxe) |
  | **Stone** | 1.5 | 7.50s* | 1.15s (Pickaxe) | 0.60s (Pickaxe) | 0.40s (Pickaxe) | 0.30s (Pickaxe) |
  | **Obsidian** | 50.0 | 250.0s* | 125.0s* | 62.5s* | 41.7s* | 9.40s (Diamond) |
  *(Note: An asterisk indicates block breaks but drops no item because harvest tier is insufficient).*

### 5.3 Break Crack Animation Stages & Destruction FSM
- Normalized Break Progress: $P \in [0.0, 1.0)$.
- Crack Stage Mapping: Integer $S \in [0..9]$ mapped via:
  $S = \min(9, \lfloor P \times 10.0 \rfloor)$
- **Cancellation Invariants:**
  - Progress instantly resets to 0.0 if left mouse button is released.
  - Progress instantly resets to 0.0 if crosshair moves off target voxel coordinate.
  - Progress instantly resets to 0.0 if player moves beyond maximum reach distance.

### 5.4 Block Placement & Anti-Suffocation Validation
1. Target Placement Position: $\mathbf{P}_{\text{place}} = \mathbf{P}_{\text{target}} + \mathbf{n}_{\text{face}}$.
2. Height Bound: $0 \le \mathbf{P}_{\text{place}}.y < 256$.
3. Cell Occupancy: World block at $\mathbf{P}_{\text{place}}$ must be air or replaceable fluid.
4. **Anti-Suffocation Invariant:**
   $\text{AABB}_{\text{block}} = [\mathbf{P}_{\text{place}}, \mathbf{P}_{\text{place}} + (1, 1, 1)]$
   If $\text{Intersects}(\text{AABB}_{\text{block}}, \text{AABB}_{\text{player}}) \implies \text{ABORT PLACEMENT}$

---

## 6. Deep-Dive: Inventory, Container & Item Systems

### 6.1 Slot Architecture & Memory Layout
In accordance with Ponytail minimalist principles, the entire inventory is laid out as a flat, contiguous array of fixed-size ItemStack structs with zero dynamic container allocations:

`
+-----------------------------------------------------------------------+
|                       PLAYER INVENTORY LAYOUT                         |
+-----------------------------------------------------------------------+
|  [Armor: 4 slots]  (Helmet: 39, Chestplate: 38, Leggings: 37, Boots: 36)|
|  [Offhand: 1 slot] (Shield / Torches: 40)                             |
|  [Crafting 2x2: 4 input slots (0-3) -> 1 output slot (result: 4)]     |
|                                                                       |
|  Main Inventory: 27 slots (Indices 9 to 35, 3 rows of 9)              |
|  +----+----+----+----+----+----+----+----+----+                       |
|  |  9 | 10 | 11 | 12 | 13 | 14 | 15 | 16 | 17 |  (Row 1)             |
|  | 18 | 19 | 20 | 21 | 22 | 23 | 24 | 25 | 26 |  (Row 2)             |
|  | 27 | 28 | 29 | 30 | 31 | 32 | 33 | 34 | 35 |  (Row 3)             |
|  +----+----+----+----+----+----+----+----+----+                       |
|                                                                       |
|  Hotbar: 9 slots (Indices 0 to 8, mapped to keys 1-9 / Mouse Wheel)   |
|  +----+----+----+----+----+----+----+----+----+                       |
|  |  0 |  1 |  2 |  3 |  4 |  5 |  6 |  7 |  8 |                       |
|  +----+----+----+----+----+----+----+----+----+                       |
+-----------------------------------------------------------------------+
`

### 6.2 Stack Limit Hierarchy
- **Stack Size 64:** Standard building blocks (Dirt, Stone, Cobble, Wood Planks, Sand, Glass, Bricks), bulk raw resources (Coal, Iron Ingots, Gold Ingots, Diamonds, Redstone, Sticks, Wheat).
- **Stack Size 16:** Compact items (Snowballs, Ender Pearls, Buckets (empty), Eggs, Signs, Honey Bottles).
- **Stack Size 1 (Non-stackable):** Tools (Pickaxes, Axes, Shovels, Swords, Hoes), Armor pieces (Helmets, Chestplates, Leggings, Boots), Filled Buckets (Water, Lava, Milk), Bows, Crossbows, Potions, Boats.

### 6.3 Mouse Slot Interactions State Machine
- **Left-Click on Slot:**
  - Cursor Empty: Picks up the entire stack from the target slot.
  - Cursor Holding Stack, Slot Empty: Deposits the entire held stack into the slot.
  - Cursor Holding Matching Item: Merges held items into the slot up to maxStack. Any overflow remainder stays in the cursor stack.
  - Cursor Holding Different Item: Swaps the cursor stack and the slot stack.
- **Right-Click on Slot:**
  - Cursor Empty: Picks up half of the slot stack ($\lceil N / 2 \rceil$).
  - Cursor Holding Stack: Deposits exactly 1 item from the cursor stack into the slot (if empty or matching with space).
- **Shift + Left-Click (Quick Move):**
  - Hotbar slot -> Main Inventory (first available empty slot or matching stack with space).
  - Main Inventory slot -> Hotbar (first available hotbar slot).
  - Inventory slot -> Armor slot (if item matches armor type and armor slot is empty).
  - Container / Crafting slot -> Inventory.
- **Drag Operations:**
  - Left-Mouse Drag: Distributes held stack evenly among all dragged-over slots ($\lfloor N / \text{slot\_count} \rfloor$ per slot; remainder stays in cursor).
  - Right-Mouse Drag: Places exactly 1 item from held stack into each dragged-over slot.
- **Item Drop Action ('Q' Key):**
  - 'Q' keypress: Drops 1 item from the active hotbar slot into the world.
  - 'Ctrl + Q' keypress: Drops the entire stack from the active hotbar slot into the world.

---

## 7. Deep-Dive: Crafting Matrix & Canonical Recipe Registry

### 7.1 Crafting Mechanics & Recipe Resolution
- **2x2 Inventory Crafting Grid:** 4 input slots indexed [0..3], 1 output slot. Available anywhere from player inventory screen.
- **3x3 Crafting Table Grid:** 9 input slots indexed [0..8], 1 output slot. Accessed by right-clicking a placed Crafting Table block.
- **Shaped vs. Shapeless Matching:**
  - Shaped recipes require an exact 2D bounding matrix pattern (can be placed anywhere within the grid as long as relative arrangement is preserved).
  - Shapeless recipes match unordered ingredient sets (e.g. 1 Log -> 4 Planks; 1 Coal + 1 Stick -> 4 Torches).
- **Consumption Invariant:** When the player removes the crafted item from the result slot, exactly 1 item is decremented from each populated input slot.

### 7.2 Canonical Recipe Catalog
1. **Wood Planks (Shapeless, 2x2 or 3x3):**
   - Input: $1 \times \text{Wood Log}$ (any type) -> Output: $4 \times \text{Wood Planks}$.
2. **Sticks (Shaped, 2x2 or 3x3):**
   - Input: $2 \times \text{Wood Planks}$ stacked vertically (1x2) -> Output: $4 \times \text{Sticks}$.
3. **Crafting Table (Shaped, 2x2 or 3x3):**
   - Input: $4 \times \text{Wood Planks}$ in a 2x2 square -> Output: $1 \times \text{Crafting Table}$.
4. **Torches (Shaped, 2x2 or 3x3):**
   - Input: $1 \times \text{Coal / Charcoal}$ vertically above $1 \times \text{Stick}$ (1x2) -> Output: $4 \times \text{Torches}$.
5. **Wooden / Stone / Iron Pickaxe (Shaped, 3x3):**
   - Row 1: $[\text{Material}, \text{Material}, \text{Material}]$
   - Row 2: $[\text{Empty}, \text{Stick}, \text{Empty}]$
   - Row 3: $[\text{Empty}, \text{Stick}, \text{Empty}]$
   - Output: $1 \times \text{Pickaxe}$ (Wooden, Stone, or Iron).
6. **Wooden / Stone / Iron Axe (Shaped, 3x3):**
   - Row 1: $[\text{Material}, \text{Material}, \text{Empty}]$
   - Row 2: $[\text{Material}, \text{Stick}, \text{Empty}]$
   - Row 3: $[\text{Empty}, \text{Stick}, \text{Empty}]$
   - Output: $1 \times \text{Axe}$.
7. **Wooden / Stone / Iron Shovel (Shaped, 3x3):**
   - Row 1: $[\text{Empty}, \text{Material}, \text{Empty}]$
   - Row 2: $[\text{Empty}, \text{Stick}, \text{Empty}]$
   - Row 3: $[\text{Empty}, \text{Stick}, \text{Empty}]$
   - Output: $1 \times \text{Shovel}$.
8. **Wooden / Stone / Iron Sword (Shaped, 3x3 or 2x2 vertical):**
   - Row 1: $[\text{Material}]$
   - Row 2: $[\text{Material}]$
   - Row 3: $[\text{Stick}]$
   - Output: $1 \times \text{Sword}$.
9. **Wooden / Stone / Iron Hoe (Shaped, 3x3):**
   - Row 1: $[\text{Material}, \text{Material}, \text{Empty}]$
   - Row 2: $[\text{Empty}, \text{Stick}, \text{Empty}]$
   - Row 3: $[\text{Empty}, \text{Stick}, \text{Empty}]$
   - Output: $1 \times \text{Hoe}$.
10. **Furnace (Shaped, 3x3):**
    - Outer 8 slots: $\text{Cobblestone}$ (Center slot empty) -> Output: $1 \times \text{Furnace}$.
11. **Chest (Shaped, 3x3):**
    - Outer 8 slots: $\text{Wood Planks}$ (Center slot empty) -> Output: $1 \times \text{Chest}$.
12. **Ladders (Shaped, 3x3):**
    - Columns: Left $[\text{Stick}, \text{Stick}, \text{Stick}]$, Right $[\text{Stick}, \text{Stick}, \text{Stick}]$, Center $[\text{Empty}, \text{Stick}, \text{Empty}]$ -> Output: $3 \times \text{Ladders}$.
13. **Wooden Door (Shaped, 3x3):**
    - Left 2 columns: $2 \times 3$ filled with $\text{Wood Planks}$ -> Output: $3 \times \text{Wooden Doors}$.
14. **Trapdoor (Shaped, 3x3):**
    - Bottom 2 rows: $3 \times 2$ filled with $\text{Wood Planks}$ -> Output: $2 \times \text{Trapdoors}$.
15. **Slabs (Shaped, 3x3):**
    - Any row: $[\text{Material}, \text{Material}, \text{Material}]$ (Cobblestone, Stone, or Planks) -> Output: $6 \times \text{Slabs}$.
16. **Stairs (Shaped, 3x3):**
    - Row 1: $[\text{Material}, \text{Empty}, \text{Empty}]$
    - Row 2: $[\text{Material}, \text{Material}, \text{Empty}]$
    - Row 3: $[\text{Material}, \text{Material}, \text{Material}]$
    - Output: $4 \times \text{Stairs}$.

---

## 8. Deep-Dive: Health, Damage, Hunger, Fall Damage & Survival Systems

### 8.1 Health System
- **Total Health Pool:** 20.0 HP (10 hearts; 1 heart = 2 HP).
- **Damage Invulnerability Window:** 10 ticks (0.5s) post-hit. Any incoming damage during this window is ignored unless greater than the original damage, in which case only the delta is deducted. Red damage flash shader applied.
- **Natural Health Regeneration:**
  - Standard Regen: Hunger >= 18 (9 shanks) restores 1 HP every 4.0s (80 ticks), consuming 6.0 exhaustion points.
  - Saturation Burst: Hunger = 20 with Saturation > 0 restores 1 HP every 0.5s (10 ticks), consuming 6.0 exhaustion points.

### 8.2 Hunger & Exhaustion System
- **Food Pool:** 20.0 points (10 food shanks).
- **Saturation Pool:** 0.0 to 20.0 (starts at 5.0, capped at current food level).
- **Exhaustion Counter:** Accumulates from 0.0 to 4.0:
  - Sprinting: +0.1 per meter.
  - Jumping: +0.05 per jump.
  - Sprint-Jumping: +0.2 per jump.
  - Mining Block: +0.005 per block.
  - Taking Damage: +0.1 per HP lost.
  - When Exhaustion >= 4.0: Exhaustion resets to 0.0, and 1.0 point is deducted from Saturation (or Hunger if Saturation is zero).
- **Starvation Mechanics:**
  - At Hunger = 0: Deals 1 HP damage every 4.0s (80 ticks).
  - Hard Mode: Starvation can reduce HP to 0 (lethal).
  - Normal Mode: Starvation caps at 1 HP (half a heart).
  - Easy Mode: Starvation caps at 10 HP (5 hearts).
  - Peaceful Mode: Hunger never depletes; continuous health regeneration.

### 8.3 Fall Damage Formula
- **Safe Fall Distance:** 3.0 blocks.
- **Damage Formula:**
  $\text{Damage} = \max\left(0, \lceil d_{\text{fall}} - 3.0 \rceil\right)$
  Each additional block fallen inflicts 1.0 HP of physical damage.
- **Water Landing:** Any water layer >= 1 block depth completely resets $d_{\text{fall}} = 0$ upon entry, negating all fall damage.

### 8.4 World Item Drop Entity
- **Kinematics:** Floating 3D item sprite with sinusoidal levitation:
  $y(t) = y_{\text{base}} + 0.1 \cdot \sin(\pi \cdot t)$
  Yaw rotation rate $\omega = 180^\circ/\text{s}$ (1 revolution every 2.0s).
- **Pickup Radius:** 1.5 to 2.0 meters from player AABB center.
- **Pickup Delay:** 10 to 40 ticks (0.5 to 2.0s) upon spawning, preventing instant re-pickup by throwing player.
- **Despawn Lifetime:** 6000 ticks = 300 seconds = 5.0 minutes.

### 8.5 Hand Swing Animation
- **Duration:** 6 ticks = 0.30 seconds.
- **Rotation:** Pitch swing from 0 deg -> -30 deg -> +60 deg -> 0 deg accompanied by -20 deg inward yaw rotation.

### 8.6 Game Modes: Creative vs. Survival Matrix
| Dimension | Survival Mode | Creative Mode |
| :--- | :--- | :--- |
| **Player Health** | 20.0 HP (Vulnerable) | Invulnerable (infinite HP; void Y < -64 kills) |
| **Hunger & Exhaustion** | Active (0--20) | Disabled (Always full, infinite sprint) |
| **Block Breaking** | Hardness-timed with tool tiers | Instant (1 click, 0 delay, no cracks) |
| **Block Drops** | Drops item entity if harvestable | No drops (destroyed into void) |
| **Block Placement** | Consumes stack from hotbar | Infinite (stack not decremented) |
| **Flight** | Disabled (standard jumping only) | Enabled (double-tap Space; Space up, Shift down) |
| **Reach Distance** | 4.5 meters | 5.0 meters |
| **Inventory UI** | Survival Inventory + Crafting | Creative Tab Palette (All blocks infinite) |

---

## 9. Deep-Dive: Environmental Lighting & Procedural Audio Synthesizer

### 9.1 Celestial Clock & Lighting Parameters
- **Day Cycle Duration:** $T_{\text{day}} = 1200\text{ seconds} = 20.0\text{ minutes}$.
  - Daytime: 10 minutes (600s).
  - Nighttime: 7 minutes (420s).
  - Dawn / Dusk Transitions: 1.5 minutes (90s) each.
- **Solar Trajectory Vector:**
  $\phi(t) = 2\pi \frac{t_{\text{world}}}{T_{\text{day}}}, \quad \delta = 10.0^\circ \text{ (axial tilt)}$
  $\hat{\mathbf{L}}_{\text{sun}} = \begin{pmatrix} \cos(\phi) \\ \sin(\phi)\cos(\delta) \\ \sin(\phi)\sin(\delta) \end{pmatrix}, \quad \hat{\mathbf{L}}_{\text{moon}} = -\hat{\mathbf{L}}_{\text{sun}}$
- **Directional Face Occlusion Shading:**
  - Top Face (+Y): 1.00
  - Bottom Face (-Y): 0.50
  - North / South Faces (+-Z): 0.80
  - East / West Faces (+-X): 0.60

### 9.2 Procedural Audio Synthesizer Formulas
1. **UI Click:**
   - Duration: 15 ms.
   - Waveform: 50% square wave at 2400 Hz.
   - Formula: $s(t) = \operatorname{sgn}(\sin(2\pi \cdot 2400 \cdot t)) \cdot (1.0 - t / 0.015)$.
2. **Footstep:**
   - Duration: 40 ms.
   - Waveform: Galois 16-bit LFSR pseudo-random noise + 80 Hz triangle wave thud.
   - Formula: $s(t) = [0.7 \cdot \text{Noise}() + 0.3 \cdot \text{Tri}(80)] \cdot e^{-65 t}$.
3. **Jump:**
   - Duration: 90 ms.
   - Waveform: 25% duty cycle square wave frequency sweep:
     $f(t) = 140\text{ Hz} + 420\left(\frac{t}{0.090}\right)\text{ Hz}$
   - Formula: $s(t) = \text{Square}(f(t), d = 0.25) \cdot E(t)$.
4. **Block Break:**
   - Duration: 160 ms.
   - Waveform: LFSR noise + pitch-falling square sub-harmonic ($120\text{ Hz} \cdot (1 - t/0.160)$).
   - Formula: $s(t) = [0.85 \cdot \text{Noise}() + 0.15 \cdot \text{Square}(f_{\text{sub}}(t))] \cdot (1.0 - (t / 0.160)^{0.7})$.
5. **Block Place:**
   - Duration: 50 ms.
   - Waveform: Triangle wave with exponential pitch drop:
     $f(t) = 220.0 \cdot 2^{-25.0 t} \text{ Hz}$
   - Formula: $s(t) = \text{Tri}(f(t)) \cdot e^{-50 t}$.

---

## 10. Implementation Recommendations & Ponytail Ledger

| Subsystem | Implemented Architecture | Explicit Limitation / Ceiling | Trigger for Upgrade | Upgrade Path |
| :--- | :--- | :--- | :--- | :--- |
| **Physics** | Axis-decoupled sweep (Y -> X -> Z) | Tunneling possible if speed > 60 m/s | High-speed explosions, Elytra flight | Continuous swept AABB Minkowski solver |
| **Camera** | Pitch/Yaw Euler Clamping | No camera roll or 6-DOF movement | Elytra flight, swimming rotation | Quaternion camera (Slerp) |
| **Raycast** | Linear Amanatides-Woo DDA | Traverses every empty cell up to 5.0m | Extended reach (>32m), shadow casting | Hierarchical DDA / Octree skip |
| **Collision** | Single Rigid AABB (0.6x1.8m) | Non-rotatable hull; no crawling | Crawling in 1-block spaces | Multi-box composite collision hierarchy |
| **Stepping** | Speculative Step Resolver (0.55m) | Only resolves rectangular step-ups | Non-voxel terrain or custom stairs | Swept upward ramp tester |
| **Inventory** | Fixed contiguous array (9+27+4+1) | Static slot indices | Modded containers, bags | Container base interface |
| **Audio** | Real-time procedural waveforms | 16-voice polyphonic mixer | Orchestral background music | Ogg Vorbis streaming background thread |
