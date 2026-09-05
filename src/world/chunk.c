#include "world.h"
#include "terrain.h"
#include "mesher.h"
#include "../assets/assets.h"
#include "../assets/atlas_data.h"
#include <string.h>
#include <stdlib.h>
#include <stdio.h>

#if !defined(HEADLESS_ONLY) && (defined(HAVE_RAYLIB) || (defined(__has_include) && __has_include(<raylib.h>)))
    #define USE_RAYLIB 1
    #include <raylib.h>
    #include <rlgl.h>
#else
    #define USE_RAYLIB 0
#endif

// ponytail: [world grid: 17x17 toroidal BSS] -> [infinite dynamic chunk hash table if infinite world exploration requested]
// ponytail: [chunk storage: static BSS memory] -> [memory-mapped disk cache if render distance >= 32]

typedef struct GpuVertex {
    float x, y, z;
    float u, v;
    uint8_t r, g, b, a;
} GpuVertex;

#if USE_RAYLIB
static GpuVertex s_GpuScratchVertices[MESHER_MAX_VERTICES];
static uint16_t  s_GpuScratchIndices[MESHER_MAX_INDICES];
static Texture2D s_AtlasTexture = { 0 };
static bool s_AtlasLoaded = false;

static void EnsureAtlasTextureLoaded(void) {
    if (s_AtlasLoaded) return;
    Image img = {
        .data = (void*)g_AtlasRGBA,
        .width = ATLAS_WIDTH,
        .height = ATLAS_HEIGHT,
        .mipmaps = 1,
        .format = PIXELFORMAT_UNCOMPRESSED_R8G8B8A8
    };
    s_AtlasTexture = LoadTextureFromImage(img);
    SetTextureFilter(s_AtlasTexture, TEXTURE_FILTER_POINT);
    s_AtlasLoaded = true;
}
#endif

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

void Chunk_UploadGPU(Chunk* chunk, const ChunkMesh* mesh) {
#if USE_RAYLIB
    if (!chunk || !mesh) return;

    Chunk_UnloadGPU(chunk);

    if (mesh->vertexCount == 0 || mesh->indexCount == 0 || mesh->vertexCount > 65535) {
        return;
    }

    for (uint32_t i = 0; i < mesh->vertexCount; i++) {
        uint32_t vx = 0, vy = 0, vz = 0, normal = 0, ao = 0, blockId = 0;
        uint32_t u = 0, v = 0, w = 0, h = 0;
        Vertex_Unpack(mesh->vertices[i], &vx, &vy, &vz, &normal, &ao, &blockId, &u, &v, &w, &h);

        s_GpuScratchVertices[i].x = (float)(chunk->chunkX * CHUNK_WIDTH + (int)vx);
        s_GpuScratchVertices[i].y = (float)vy;
        s_GpuScratchVertices[i].z = (float)(chunk->chunkZ * CHUNK_DEPTH + (int)vz);

        TileCoord tile = Assets_GetWorldBlockTextureTile((uint8_t)blockId, (BlockFace)normal);
        float u0 = (float)tile.tx * 0.0625f;
        float v0 = (float)tile.ty * 0.0625f;
        float u1 = u0 + 0.0625f;
        float v1 = v0 + 0.0625f;

        s_GpuScratchVertices[i].u = (u == 0) ? u0 : u1;
        s_GpuScratchVertices[i].v = (v == 0) ? v0 : v1;

        float faceLight = 0.85f;
        if (normal == FACE_POS_Y) faceLight = 1.0f;
        else if (normal == FACE_NEG_Y) faceLight = 0.5f;
        else if (normal == FACE_POS_Z || normal == FACE_NEG_Z) faceLight = 0.70f;

        float aoFactor = 0.55f + (float)ao * 0.15f;
        float finalLight = faceLight * aoFactor;
        uint8_t brightness = (uint8_t)(255.0f * (finalLight > 1.0f ? 1.0f : finalLight));

        s_GpuScratchVertices[i].r = brightness;
        s_GpuScratchVertices[i].g = brightness;
        s_GpuScratchVertices[i].b = brightness;
        s_GpuScratchVertices[i].a = 255;
    }

    for (uint32_t i = 0; i < mesh->indexCount; i++) {
        s_GpuScratchIndices[i] = (uint16_t)mesh->indices[i];
    }

    chunk->vaoId = rlLoadVertexArray();
    rlEnableVertexArray(chunk->vaoId);

    chunk->vboId = rlLoadVertexBuffer(s_GpuScratchVertices, (int)(mesh->vertexCount * sizeof(GpuVertex)), false);
    rlSetVertexAttribute(0, 3, RL_FLOAT, false, sizeof(GpuVertex), 0);
    rlEnableVertexAttribute(0);
    rlSetVertexAttribute(1, 2, RL_FLOAT, false, sizeof(GpuVertex), (const void*)12);
    rlEnableVertexAttribute(1);
    rlSetVertexAttribute(3, 4, RL_UNSIGNED_BYTE, true, sizeof(GpuVertex), (const void*)20);
    rlEnableVertexAttribute(3);

    chunk->iboId = rlLoadVertexBufferElement(s_GpuScratchIndices, (int)(mesh->indexCount * sizeof(uint16_t)), false);

    rlDisableVertexArray();

    chunk->vertexCount = mesh->vertexCount;
    chunk->indexCount = mesh->indexCount;
#else
    (void)chunk;
    (void)mesh;
#endif
}

void Chunk_UnloadGPU(Chunk* chunk) {
    if (!chunk) return;
#if USE_RAYLIB
    if (chunk->vaoId != 0) {
        rlUnloadVertexArray(chunk->vaoId);
        chunk->vaoId = 0;
    }
    if (chunk->vboId != 0) {
        rlUnloadVertexBuffer(chunk->vboId);
        chunk->vboId = 0;
    }
    if (chunk->iboId != 0) {
        rlUnloadVertexBuffer(chunk->iboId);
        chunk->iboId = 0;
    }
    chunk->vertexCount = 0;
    chunk->indexCount = 0;
#else
    chunk->vboId = 0;
    chunk->vaoId = 0;
    chunk->iboId = 0;
    chunk->vertexCount = 0;
    chunk->indexCount = 0;
#endif
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
#if USE_RAYLIB
    if (s_AtlasLoaded) {
        UnloadTexture(s_AtlasTexture);
        s_AtlasLoaded = false;
    }
#endif
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
    (void)renderAlpha;
#if USE_RAYLIB
    if (!camera) return;
    EnsureAtlasTextureLoaded();

    // 1. Clear background to Minecraft sky blue
    ClearBackground((Color){ 135, 206, 235, 255 });

    // 2. Setup 3D camera
    Camera3D rayCam = { 0 };
    rayCam.position = (Vector3){ camera->position.x, camera->position.y, camera->position.z };
    rayCam.target = (Vector3){ camera->position.x + camera->forward.x,
                               camera->position.y + camera->forward.y,
                               camera->position.z + camera->forward.z };
    rayCam.up = (Vector3){ camera->up.x, camera->up.y, camera->up.z };
    rayCam.fovy = camera->currentFov;
    rayCam.projection = CAMERA_PERSPECTIVE;

    BeginMode3D(rayCam);

    // 3. Draw active chunks with frustum culling
    rlEnableShader(rlGetShaderIdDefault());
    rlSetTexture(s_AtlasTexture.id);

    for (int i = 0; i < WORLD_ACTIVE_CHUNKS; ++i) {
        Chunk* chunk = &s_WorldGrid.chunks[i];
        if (!chunk->isLoaded || chunk->vaoId == 0 || chunk->indexCount == 0) continue;

        AABB chunkBox = {
            .minX = (float)(chunk->chunkX * CHUNK_WIDTH),
            .minY = 0.0f,
            .minZ = (float)(chunk->chunkZ * CHUNK_DEPTH),
            .maxX = (float)((chunk->chunkX + 1) * CHUNK_WIDTH),
            .maxY = (float)CHUNK_HEIGHT,
            .maxZ = (float)((chunk->chunkZ + 1) * CHUNK_DEPTH)
        };
        if (Frustum_TestAABB(&camera->frustum, &chunkBox) == CULL_OUTSIDE) {
            continue;
        }

        rlEnableVertexArray(chunk->vaoId);
        rlDrawVertexArrayElements(0, (int)chunk->indexCount, 0);
    }

    rlDisableVertexArray();
    rlSetTexture(0);

    EndMode3D();
#else
    (void)camera;
#endif
}

void World_RenderSelectionBox(int x, int y, int z) {
#if USE_RAYLIB
    Vector3 center = { (float)x + 0.5f, (float)y + 0.5f, (float)z + 0.5f };
    DrawCubeWires(center, 1.002f, 1.002f, 1.002f, (Color){ 0, 0, 0, 180 });
#else
    (void)x; (void)y; (void)z;
#endif
}
