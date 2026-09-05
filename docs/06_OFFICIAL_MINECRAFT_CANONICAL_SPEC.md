# 06. Official Minecraft Canonical Architecture & Asset Specification

## 1. Executive Architecture Audit: Official Mojang Engine vs. 1-Click Native Target

To achieve authentic Minecraft gameplay mechanics and visual aesthetics while fulfilling the user's hard constraint—**a zero-setup, universal single-click standalone desktop executable from GitHub**—we audit the official Minecraft engine architecture and isolate canonical standards from historical engine debt.

```
Official Mojang Java Engine Architecture (Historical Bloat)
[ JRE Virtual Machine / GC Pauses ]
  └── [ Heavy NBT Serialization Layer (Gzip/Zlib on disk) ]
        └── [ Dynamic JSON Model Parser & BakedModel Dispatch ]
              └── [ Loose Assets in .minecraft/assets/indexes/ ]

Ponytail Lean Native Architecture (Target Engine)
[ Zero-Dependency Statically Linked Native Binary (<15MB) ]
  └── [ Direct Cacheline-Aligned Binary Chunk Sections ]
        └── [ In-Memory Pre-Baked Texture Atlas & Face Tables (.rodata) ]
              └── [ Instant Cold-Boot (<80ms), Zero Missing Assets ]
```

---

## 2. Canonical World & Chunk Storage Specification

### 2.1 The Anvil Format & Section Architecture
Official Minecraft Java Edition utilizes the **Anvil File Format** (`.mca` region files).
- **Region Matrix:** Each `.mca` file contains $32 \times 32$ chunks ($1,024$ chunks covering a $512 \times 512$ block area).
- **Header:** Exact $8\text{ KiB}$ file preamble:
  1. $4\text{ KiB}$ Chunk Location Table ($1,024$ entries $\times 4\text{ bytes}$: 3-byte sector offset, 1-byte sector count).
  2. $4\text{ KiB}$ Timestamp Table ($1,024$ entries $\times 4\text{ bytes}$ Unix epoch timestamps).
- **Sub-Chunk Sections:** Chunks are vertically partitioned into $16 \times 16 \times 16$ voxel sections (16 sections total spanning $Y = 0$ to $Y = 255$ in classic format, or 24 sections $Y = -64$ to $319$ in 1.18+).
- **Sparse Section Optimization (Critical Ponytail Rule):** Empty air sections are **never** allocated in RAM or written to disk. A world over flat plains consumes $\le 4$ active sections per chunk instead of 16, saving $>75\%$ memory.

### 2.2 Voxel Coordinate & Index Ordering
Inside each $16 \times 16 \times 16$ section, Minecraft Java Edition organizes block storage in **YZX ordering**:
$$\text{Index} = (y \times 16 + z) \times 16 + x = y \cdot 256 + z \cdot 16 + x$$
- **Rationale:** Compressing columns of identical air or stone produces long sequential runs, dramatically maximizing RLE (Run-Length Encoding) and DEFLATE compression ratios.

---

## 3. Canonical Physics & Kinematic Constants

To make the movement and gameplay feel indistinguishable from authentic Minecraft, the engine must implement the exact mathematical constants extracted from the official decompiled game loop:

| Parameter | Official Value | Physical Equivalent | Engine Implementation |
| :--- | :--- | :--- | :--- |
| **Physics Tick Rate** | $20\text{ TPS}$ | $\Delta t = 0.05\text{ s}$ | Fixed sub-step loop ($3\text{ ticks / frame}$ at 60Hz or $20\text{Hz}$ fixed accumulator) |
| **Player Bounding Box** | $0.6 \times 1.8 \times 0.6\text{ m}$ | Rigid AABB | Centered horizontally: $[-0.3, +0.3]$ on $X/Z$, $[0, 1.8]$ on $Y$ |
| **Eye Level** | $1.62\text{ m}$ | Camera height | $y_{\text{cam}} = y_{\text{feet}} + 1.62\text{ m}$ |
| **Downward Gravity** | $0.08\text{ blk/tick}^2$ | $32.0\text{ m/s}^2$ | $v_y \gets (v_y - 0.08) \times 0.98$ per tick |
| **Horizontal Air Drag** | $0.98$ factor / tick | Air damping | $v_x \gets v_x \times 0.98$, $v_z \gets v_z \times 0.98$ |
| **Ground Friction** | $0.6 \times 0.91 = 0.546$ | Ground traction | $v_{x,z} \gets v_{x,z} \times 0.546$ when grounded |
| **Terminal Falling Velocity** | $-3.92\text{ blk/tick}$ | $-78.4\text{ m/s}$ | Asymptotic ceiling from $(v_y - 0.08) \times 0.98$ |
| **Jump Velocity** | $0.42\text{ blk/tick}$ | $8.4\text{ m/s}$ ($1.25\text{m}$ leap) | $v_y \gets 0.42$ on jump keypress when grounded |
| **Auto-Step Height** | $0.6\text{ m}$ | Half-slab/stair | Allows smooth $0.5\text{m}$ step climbing without jumping |
| **Reach Distance** | $5.0\text{ blocks}$ (Creative), $4.5\text{m}$ (Survival) | Raycast limit | DDA traversal cut-off at $t_{\text{max}} = 5.0$ |

---

## 4. Official Asset Architecture & Representation

### 4.1 Block Model Schema (`assets/minecraft/models/block/`)
In canonical Minecraft, block geometry is decoupled into JSON models:
```json
{
  "parent": "minecraft:block/cube",
  "textures": {
    "particle": "minecraft:block/grass_block_side",
    "bottom": "minecraft:block/dirt",
    "top": "minecraft:block/grass_block_top",
    "side": "minecraft:block/grass_block_side"
  },
  "elements": [
    {
      "from": [0, 0, 0],
      "to": [16, 16, 16],
      "faces": {
        "down":  { "uv": [0, 0, 16, 16], "texture": "#bottom", "cullface": "down" },
        "up":    { "uv": [0, 0, 16, 16], "texture": "#top",    "cullface": "up" },
        "north": { "uv": [0, 0, 16, 16], "texture": "#side",   "cullface": "north" },
        "south": { "uv": [0, 0, 16, 16], "texture": "#side",   "cullface": "south" },
        "west":  { "uv": [0, 0, 16, 16], "texture": "#side",   "cullface": "west" },
        "east":  { "uv": [0, 0, 16, 16], "texture": "#side",   "cullface": "east" }
      }
    }
  ]
}
```

### 4.2 Ponytail Asset Inlining (Eliminating Loose File Dependencies)
In the native universal application, parsing JSON models at runtime is explicitly eliminated (**Ponytail Ladder Rule 1: YAGNI**).
Instead, standard cube models are pre-compiled into a constant $C$ lookup table in `.rodata`:

```c
typedef struct {
    uint8_t tex_top;
    uint8_t tex_bottom;
    uint8_t tex_north;
    uint8_t tex_south;
    uint8_t tex_west;
    uint8_t tex_east;
    uint8_t is_transparent;
    uint8_t hardness_ticks;
} BlockVisualDef;

static const BlockVisualDef BLOCK_REGISTRY[256] = {
    [BLOCK_AIR]         = { 0, 0, 0, 0, 0, 0, 1, 0 },
    [BLOCK_STONE]       = { TEX_STONE, TEX_STONE, TEX_STONE, TEX_STONE, TEX_STONE, TEX_STONE, 0, 30 },
    [BLOCK_GRASS_BLOCK] = { TEX_GRASS_TOP, TEX_DIRT, TEX_GRASS_SIDE, TEX_GRASS_SIDE, TEX_GRASS_SIDE, TEX_GRASS_SIDE, 0, 12 },
    [BLOCK_DIRT]        = { TEX_DIRT, TEX_DIRT, TEX_DIRT, TEX_DIRT, TEX_DIRT, TEX_DIRT, 0, 10 },
    [BLOCK_COBBLESTONE] = { TEX_COBBLE, TEX_COBBLE, TEX_COBBLE, TEX_COBBLE, TEX_COBBLE, TEX_COBBLE, 0, 40 },
    [BLOCK_WOOD_PLANKS] = { TEX_PLANKS, TEX_PLANKS, TEX_PLANKS, TEX_PLANKS, TEX_PLANKS, TEX_PLANKS, 0, 30 },
    [BLOCK_BEDROCK]     = { TEX_BEDROCK, TEX_BEDROCK, TEX_BEDROCK, TEX_BEDROCK, TEX_BEDROCK, TEX_BEDROCK, 0, 255 },
    [BLOCK_WATER]       = { TEX_WATER, TEX_WATER, TEX_WATER, TEX_WATER, TEX_WATER, TEX_WATER, 1, 200 },
    [BLOCK_GLASS]       = { TEX_GLASS, TEX_GLASS, TEX_GLASS, TEX_GLASS, TEX_GLASS, TEX_GLASS, 1, 6 }
};
```

### 4.3 Audio & Sound Events (`sounds.json`)
Official Minecraft requires **single-channel mono** audio streams for 3D positional sound attenuation:
- Inverse distance law: $\text{Volume} = \frac{V_0}{1.0 + d / d_0}$.
- Our embedded procedural audio synthesizer produces mathematically equivalent waveforms directly to the platform audio buffer without shipping multi-megabyte sound libraries.

---

## 5. Official Lighting Engine Parity

Minecraft uses a dual-channel 4-bit nibble lighting system ($0$ to $15$ brightness):
1. **Block Light ($0\text{--}15$):** Emitted by local sources (Torches $= 14$, Lava $= 15$, Glowstone $= 15$). Decays by $1$ unit per block along taxicab/Manhattan distance.
2. **Sky Light ($0\text{--}15$):** Propagates directly downward from the top of the world with no decay until it hits an opaque block, then decays by $1$ unit per block horizontally.

**Light Attenuation Equation:**
$$I = 0.8^{\,15 - L}$$
Where $L = \max(\text{SkyLight} \times \text{SunAngle}, \text{BlockLight})$.

*Ponytail Simplification:*
`// ponytail: dynamic 3D BFS flood-fill lighting -> ambient occlusion + directional face shading + vertex daylight factor [upgrade path: compute shader BFS light propagation]`
