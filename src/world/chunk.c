#include "world.h"
#include "terrain.h"
#include <string.h>
#include <stdlib.h>
#include <stdio.h>

// ponytail: [world grid: 17x17 toroidal BSS] -> [infinite dynamic chunk hash table if infinite world exploration requested]
// ponytail: [chunk storage: static BSS memory] -> [memory-mapped disk cache if render distance >= 32]

/* =============================================================================
 * Static BSS Memory Allocation (~18.06 MiB voxel RAM + metadata)
 * ============================================================================= */
typedef struct WorldGrid {
    Chunk chunks[WORLD_ACTIVE_CHUNKS]; /* 289 contiguous chunks in BSS */
    int centerChunkX;
    int centerChunkZ;
    int worldSeed;
    bool isInitialized;
} WorldGrid;

static WorldGrid s_WorldGrid;

/* Fast toroidal index formula: ((coord % 17) + 17) % 17 */
static inline int ToroidalIndex(int coord) {
    int mod = coord % WORLD_GRID_DIAMETER;
    return (mod < 0) ? (mod + WORLD_GRID_DIAMETER) : mod;
}

static inline int ToroidalSlot(int cx, int cz) {
    return ToroidalIndex(cz) * WORLD_GRID_DIAMETER + ToroidalIndex(cx);
}

/* =============================================================================
 * Chunk Lifecycle
 * ============================================================================= */
void Chunk_Init(Chunk* chunk, int cx, int cz) {
    chunk->chunkX = cx;
    chunk->chunkZ = cz;
    chunk->isLoaded = true;
    chunk->isModified = false;
    chunk->isMeshDirty = true;
    chunk->inQueue = false;
    chunk->vboId = 0;
    chunk->vaoId = 0;
    chunk->iboId = 0;
    chunk->vertexCount = 0;
    chunk->indexCount = 0;
    memset(chunk->voxels, BLOCK_AIR, sizeof(chunk->voxels));
    Terrain_GenerateChunk(cx, cz, (uint64_t)s_WorldGrid.worldSeed, chunk->voxels);
}

void Chunk_Reset(Chunk* chunk) {
    Chunk_UnloadGPU(chunk);
    chunk->isLoaded = false;
    chunk->isModified = false;
    chunk->isMeshDirty = false;
    chunk->inQueue = false;
    chunk->chunkX = 0;
    chunk->chunkZ = 0;
}

void Chunk_UnloadGPU(Chunk* chunk) {
    // ponytail: [GPU buffers: Raylib / raw OpenGL VAO/VBO delete] -> [deferred deletion ring if driver stalls]
    if (chunk->vboId != 0 || chunk->vaoId != 0 || chunk->iboId != 0) {
        chunk->vboId = 0;
        chunk->vaoId = 0;
        chunk->iboId = 0;
        chunk->vertexCount = 0;
        chunk->indexCount = 0;
    }
}

/* =============================================================================
 * World Subsystem Implementation
 * ============================================================================= */
void World_Init(int seed) {
    memset(&s_WorldGrid, 0, sizeof(s_WorldGrid));
    s_WorldGrid.worldSeed = seed;
    s_WorldGrid.centerChunkX = 0;
    s_WorldGrid.centerChunkZ = 0;
    s_WorldGrid.isInitialized = true;

    Terrain_Init((uint64_t)seed);

    /* Initialize all 289 chunks around origin (0, 0) */
    for (int cz = -WORLD_GRID_RADIUS; cz <= WORLD_GRID_RADIUS; ++cz) {
        for (int cx = -WORLD_GRID_RADIUS; cx <= WORLD_GRID_RADIUS; ++cx) {
            int slot = ToroidalSlot(cx, cz);
            Chunk* chunk = &s_WorldGrid.chunks[slot];
            Chunk_Init(chunk, cx, cz);
        }
    }
}

void World_Shutdown(void) {
    for (int i = 0; i < WORLD_ACTIVE_CHUNKS; ++i) {
        Chunk* chunk = &s_WorldGrid.chunks[i];
        if (chunk->isLoaded) {
            if (chunk->isModified) {
                /* World_SaveChunk(chunk); // Save to disk in saves/ */
            }
            Chunk_UnloadGPU(chunk);
            chunk->isLoaded = false;
        }
    }
    s_WorldGrid.isInitialized = false;
}

Chunk* World_GetChunk(int chunkX, int chunkZ) {
    int slot = ToroidalSlot(chunkX, chunkZ);
    Chunk* chunk = &s_WorldGrid.chunks[slot];
    if (chunk->isLoaded && chunk->chunkX == chunkX && chunk->chunkZ == chunkZ) {
        return chunk;
    }
    return NULL;
}

void World_GetChunkNeighbors(int chunkX, int chunkZ, ChunkNeighbors* outNeighbors) {
    if (!outNeighbors) return;
    outNeighbors->negX = World_GetChunk(chunkX - 1, chunkZ);
    outNeighbors->posX = World_GetChunk(chunkX + 1, chunkZ);
    outNeighbors->negZ = World_GetChunk(chunkX, chunkZ - 1);
    outNeighbors->posZ = World_GetChunk(chunkX, chunkZ + 1);
}

uint8_t World_SampleNeighborVoxel(const Chunk* chunk, const ChunkNeighbors* neighbors, int localX, int y, int localZ) {
    if (y < 0 || y >= CHUNK_HEIGHT) return BLOCK_AIR;
    if (localX < 0) {
        if (!neighbors || !neighbors->negX) return BLOCK_AIR;
        return Chunk_GetVoxel(neighbors->negX, localX + CHUNK_WIDTH, y, localZ);
    }
    if (localX >= CHUNK_WIDTH) {
        if (!neighbors || !neighbors->posX) return BLOCK_AIR;
        return Chunk_GetVoxel(neighbors->posX, localX - CHUNK_WIDTH, y, localZ);
    }
    if (localZ < 0) {
        if (!neighbors || !neighbors->negZ) return BLOCK_AIR;
        return Chunk_GetVoxel(neighbors->negZ, localX, y, localZ + CHUNK_DEPTH);
    }
    if (localZ >= CHUNK_DEPTH) {
        if (!neighbors || !neighbors->posZ) return BLOCK_AIR;
        return Chunk_GetVoxel(neighbors->posZ, localX, y, localZ - CHUNK_DEPTH);
    }
    if (!chunk) return BLOCK_AIR;
    return Chunk_GetVoxel(chunk, localX, y, localZ);
}

uint8_t World_GetBlock(int worldX, int worldY, int worldZ) {
    if (worldY < 0 || worldY >= CHUNK_HEIGHT) return BLOCK_AIR;
    int cx = WorldToChunkCoord(worldX);
    int cz = WorldToChunkCoord(worldZ);
    Chunk* chunk = World_GetChunk(cx, cz);
    if (!chunk) return BLOCK_AIR;
    int lx = WorldToLocalCoord(worldX);
    int lz = WorldToLocalCoord(worldZ);
    return Chunk_GetVoxel(chunk, lx, worldY, lz);
}

bool World_SetBlock(int worldX, int worldY, int worldZ, uint8_t blockId) {
    if (worldY < 0 || worldY >= CHUNK_HEIGHT) return false;
    int cx = WorldToChunkCoord(worldX);
    int cz = WorldToChunkCoord(worldZ);
    Chunk* chunk = World_GetChunk(cx, cz);
    if (!chunk) return false;

    int lx = WorldToLocalCoord(worldX);
    int lz = WorldToLocalCoord(worldZ);
    int idx = ChunkVoxelIndex(lx, worldY, lz);
    if (chunk->voxels[idx] == blockId) return true;

    chunk->voxels[idx] = blockId;
    chunk->isModified = true;
    chunk->isMeshDirty = true;

    // Boundary neighbor mesh dirty propagation
    if (lx == 0) {
        Chunk* n = World_GetChunk(cx - 1, cz);
        if (n) n->isMeshDirty = true;
    } else if (lx == CHUNK_WIDTH - 1) {
        Chunk* n = World_GetChunk(cx + 1, cz);
        if (n) n->isMeshDirty = true;
    }

    if (lz == 0) {
        Chunk* n = World_GetChunk(cx, cz - 1);
        if (n) n->isMeshDirty = true;
    } else if (lz == CHUNK_DEPTH - 1) {
        Chunk* n = World_GetChunk(cx, cz + 1);
        if (n) n->isMeshDirty = true;
    }

    return true;
}

void World_Update(float playerX, float playerZ, double dt) {
    (void)dt;
    int playerChunkX = WorldToChunkCoord(FloorToInt(playerX));
    int playerChunkZ = WorldToChunkCoord(FloorToInt(playerZ));

    if (playerChunkX == s_WorldGrid.centerChunkX && playerChunkZ == s_WorldGrid.centerChunkZ) {
        return; /* Player remains within the same central chunk; active grid window is unchanged */
    }

    s_WorldGrid.centerChunkX = playerChunkX;
    s_WorldGrid.centerChunkZ = playerChunkZ;

    int minCx = playerChunkX - WORLD_GRID_RADIUS;
    int maxCx = playerChunkX + WORLD_GRID_RADIUS;
    int minCz = playerChunkZ - WORLD_GRID_RADIUS;
    int maxCz = playerChunkZ + WORLD_GRID_RADIUS;

    /* 1. Unload chunks that fell outside the new active window */
    for (int i = 0; i < WORLD_ACTIVE_CHUNKS; ++i) {
        Chunk* chunk = &s_WorldGrid.chunks[i];
        if (chunk->isLoaded) {
            if (chunk->chunkX < minCx || chunk->chunkX > maxCx ||
                chunk->chunkZ < minCz || chunk->chunkZ > maxCz) {
                if (chunk->isModified) {
                    /* World_SaveChunk(chunk); */
                }
                Chunk_UnloadGPU(chunk);
                chunk->isLoaded = false;
            }
        }
    }

    /* 2. Load or generate chunks entering the active window */
    for (int cz = minCz; cz <= maxCz; ++cz) {
        for (int cx = minCx; cx <= maxCx; ++cx) {
            int slot = ToroidalSlot(cx, cz);
            Chunk* chunk = &s_WorldGrid.chunks[slot];
            if (!chunk->isLoaded || chunk->chunkX != cx || chunk->chunkZ != cz) {
                if (chunk->isLoaded && chunk->isModified) {
                    /* World_SaveChunk(chunk); */
                }
                Chunk_UnloadGPU(chunk);
                Chunk_Init(chunk, cx, cz);
            }
        }
    }
}

void World_Render(const Camera* camera, float renderAlpha) {
    (void)camera;
    (void)renderAlpha;
    /* Dispatched to mesher / renderer */
}
