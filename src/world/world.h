#ifndef MINECRAFT_WORLD_WORLD_H
#define MINECRAFT_WORLD_WORLD_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include "../core/math_utils.h"

#ifdef __cplusplus
extern "C" {
#endif

// =============================================================================
// Chunk Dimension Constants (Canonical Minecraft Architecture)
// =============================================================================
#define CHUNK_WIDTH         16
#define CHUNK_HEIGHT        256
#define CHUNK_DEPTH         16
#define CHUNK_VOXEL_COUNT   (CHUNK_WIDTH * CHUNK_HEIGHT * CHUNK_DEPTH) // 65536 voxels (64 KiB)

// 17x17 active chunk grid: radius R=8 -> (2*8 + 1) = 17
#define WORLD_GRID_RADIUS   8
#define WORLD_GRID_DIAMETER (2 * WORLD_GRID_RADIUS + 1) // 17
#define WORLD_ACTIVE_CHUNKS (WORLD_GRID_DIAMETER * WORLD_GRID_DIAMETER) // 289 chunks

// =============================================================================
// Portable 64-Byte Cacheline Alignment Macro
// =============================================================================
#if defined(__STDC_VERSION__) && __STDC_VERSION__ >= 201112L
    #include <stdalign.h>
    #define CHUNK_ALIGN alignas(64)
#elif defined(_MSC_VER)
    #define CHUNK_ALIGN __declspec(align(64))
#elif defined(__GNUC__) || defined(__clang__)
    #define CHUNK_ALIGN __attribute__((aligned(64)))
#else
    #define CHUNK_ALIGN
#endif

// =============================================================================
// Canonical Block Palette Enum (docs/03 §2.2)
// =============================================================================
typedef enum BlockID {
    BLOCK_AIR        = 0,
    BLOCK_STONE      = 1,
    BLOCK_DIRT       = 2,
    BLOCK_GRASS      = 3,
    BLOCK_SAND       = 4,
    BLOCK_SANDSTONE  = 5,
    BLOCK_SNOW       = 6,
    BLOCK_WOOD       = 7,
    BLOCK_LEAVES     = 8,
    BLOCK_BEDROCK    = 9,
    BLOCK_WATER      = 10,
    BLOCK_CACTUS     = 11,
    BLOCK_FLOWER     = 12,
    BLOCK_TALLGRASS  = 13,
    BLOCK_COUNT      = 14
} BlockID;

// ponytail: [block palette: uint8_t 14 vanilla blocks] -> [uint16_t if modding or custom blocks added]

// =============================================================================
// Block Properties Query Helpers (Branchless Bitmask Operations)
// =============================================================================
// Opaque blocks completely obscure adjacent faces (STONE, DIRT, GRASS, SAND, SANDSTONE, SNOW, WOOD, BEDROCK)
#define BLOCK_OPAQUE_MASK ( \
    (1U << BLOCK_STONE)     | \
    (1U << BLOCK_DIRT)      | \
    (1U << BLOCK_GRASS)     | \
    (1U << BLOCK_SAND)      | \
    (1U << BLOCK_SANDSTONE) | \
    (1U << BLOCK_SNOW)      | \
    (1U << BLOCK_WOOD)      | \
    (1U << BLOCK_BEDROCK)   )

// Solid blocks participate in player AABB collision
#define BLOCK_SOLID_MASK ( \
    BLOCK_OPAQUE_MASK       | \
    (1U << BLOCK_LEAVES)    | \
    (1U << BLOCK_CACTUS)    )

// Liquid blocks (WATER)
#define BLOCK_LIQUID_MASK (1U << BLOCK_WATER)

// Foliage / billboard vegetation (FLOWER, TALLGRASS)
#define BLOCK_VEGETATION_MASK ( \
    (1U << BLOCK_FLOWER)    | \
    (1U << BLOCK_TALLGRASS) )

static inline bool Block_IsOpaque(uint8_t id) {
    return (id < 32) && ((BLOCK_OPAQUE_MASK & (1U << id)) != 0);
}

static inline bool Block_IsSolid(uint8_t id) {
    return (id < 32) && ((BLOCK_SOLID_MASK & (1U << id)) != 0);
}

static inline bool Block_IsLiquid(uint8_t id) {
    return (id == BLOCK_WATER);
}

static inline bool Block_IsVegetation(uint8_t id) {
    return (id < 32) && ((BLOCK_VEGETATION_MASK & (1U << id)) != 0);
}

// =============================================================================
// Contiguous 64 KiB Chunk Memory Structure
// =============================================================================
typedef struct Chunk {
    CHUNK_ALIGN uint8_t voxels[CHUNK_VOXEL_COUNT]; // Exactly 65536 bytes (64 KiB)
    int chunkX;                                    // World chunk X coordinate
    int chunkZ;                                    // World chunk Z coordinate
    bool isLoaded;                                 // True if slot contains active world data
    bool isModified;                               // True if modified by player (needs disk save)
    bool isMeshDirty;                              // True if voxels changed (needs remesh)
    bool inQueue;                                  // True if currently queued in mesher queue
    uint32_t vboId;                                // OpenGL VBO handle
    uint32_t vaoId;                                // OpenGL VAO handle
    uint32_t iboId;                                // OpenGL IBO / EBO handle
    uint32_t vertexCount;                          // Active vertex count
    uint32_t indexCount;                           // Active element index count
} Chunk;

// 4 Orthogonal Neighbor Chunks for boundary face sampling and greedy meshing
typedef struct ChunkNeighbors {
    const Chunk* negX; // chunkX - 1, chunkZ
    const Chunk* posX; // chunkX + 1, chunkZ
    const Chunk* negZ; // chunkX, chunkZ - 1
    const Chunk* posZ; // chunkX, chunkZ + 1
} ChunkNeighbors;

// =============================================================================
// World Subsystem API Signatures (runtime.h ↔ world.h)
// =============================================================================
void World_Init(int seed);
void World_Shutdown(void);
void World_Update(float playerX, float playerZ, double dt);
uint8_t World_GetBlock(int worldX, int worldY, int worldZ);
bool World_SetBlock(int worldX, int worldY, int worldZ, uint8_t blockId);
void World_Render(const Camera* camera, float renderAlpha);
void World_RenderSelectionBox(int x, int y, int z);

// Chunk Access & Toroidal Ring Management
Chunk* World_GetChunk(int chunkX, int chunkZ);
void World_GetChunkNeighbors(int chunkX, int chunkZ, ChunkNeighbors* outNeighbors);
uint8_t World_SampleNeighborVoxel(const Chunk* chunk, const ChunkNeighbors* neighbors, int localX, int y, int localZ);

// Internal Chunk Operations (chunk.c)
struct ChunkMesh;
void Chunk_Init(Chunk* chunk, int cx, int cz);
void Chunk_Reset(Chunk* chunk);
void Chunk_UploadGPU(Chunk* chunk, const struct ChunkMesh* mesh);
void Chunk_UnloadGPU(Chunk* chunk);

static inline uint8_t Chunk_GetVoxel(const Chunk* chunk, int lx, int ly, int lz) {
    return chunk->voxels[ChunkVoxelIndex(lx, ly, lz)];
}

static inline void Chunk_SetVoxel(Chunk* chunk, int lx, int ly, int lz, uint8_t id) {
    chunk->voxels[ChunkVoxelIndex(lx, ly, lz)] = id;
    chunk->isModified = true;
    chunk->isMeshDirty = true;
}

#ifdef __cplusplus
}
#endif

#endif // MINECRAFT_WORLD_WORLD_H
