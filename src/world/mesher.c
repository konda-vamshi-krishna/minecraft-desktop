#include "mesher.h"
#include "../core/math_utils.h"
#include <string.h>
#include <stdlib.h>

// ponytail: [scratch buffers: static BSS scratchpad] -> [double-buffered ring if asynchronous worker thread meshing enabled]
// ponytail: [quad AO: macro-corner sampling] -> [sub-quad tessellation if per-block light gradients required]

/* Global Static Scratchpad Buffers (Allocated in .bss, zero heap allocations) */
static PackedVertex s_ScratchVertices[MESHER_MAX_VERTICES];
static uint32_t     s_ScratchIndices[MESHER_MAX_INDICES];

bool Mesher_IsOpaque(uint8_t blockId) {
    return (blockId != BLOCK_AIR) && (blockId != BLOCK_WATER);
}

uint8_t Mesher_SampleVoxel(const Chunk* chunk, const NeighborChunks* neighbors, int x, int y, int z) {
    if (y < 0 || y >= CHUNK_HEIGHT) {
        return BLOCK_AIR;
    }
    if (x < 0) {
        if (z < 0 || z >= CHUNK_DEPTH) return BLOCK_AIR;
        return (neighbors && neighbors->negX) ? neighbors->negX->voxels[ChunkVoxelIndex(x + CHUNK_WIDTH, y, z)] : BLOCK_AIR;
    }
    if (x >= CHUNK_WIDTH) {
        if (z < 0 || z >= CHUNK_DEPTH) return BLOCK_AIR;
        return (neighbors && neighbors->posX) ? neighbors->posX->voxels[ChunkVoxelIndex(x - CHUNK_WIDTH, y, z)] : BLOCK_AIR;
    }
    if (z < 0) {
        if (x < 0 || x >= CHUNK_WIDTH) return BLOCK_AIR;
        return (neighbors && neighbors->negZ) ? neighbors->negZ->voxels[ChunkVoxelIndex(x, y, z + CHUNK_DEPTH)] : BLOCK_AIR;
    }
    if (z >= CHUNK_DEPTH) {
        if (x < 0 || x >= CHUNK_WIDTH) return BLOCK_AIR;
        return (neighbors && neighbors->posZ) ? neighbors->posZ->voxels[ChunkVoxelIndex(x, y, z - CHUNK_DEPTH)] : BLOCK_AIR;
    }
    if (!chunk) return BLOCK_AIR;
    return chunk->voxels[ChunkVoxelIndex(x, y, z)];
}

uint8_t Mesher_ComputeVertexAO(const Chunk* chunk, const NeighborChunks* neighbors,
                               int bx, int by, int bz, int normalIdx, int du_ao, int dv_ao) {
    static const int s_Normals[6][3] = {
        {-1,  0,  0}, /* FACE_NEG_X */
        { 1,  0,  0}, /* FACE_POS_X */
        { 0, -1,  0}, /* FACE_NEG_Y */
        { 0,  1,  0}, /* FACE_POS_Y */
        { 0,  0, -1}, /* FACE_NEG_Z */
        { 0,  0,  1}  /* FACE_POS_Z */
    };

    int d = normalIdx / 2;
    int u = (d + 1) % 3;
    int v = (d + 2) % 3;

    int nx = s_Normals[normalIdx][0];
    int ny = s_Normals[normalIdx][1];
    int nz = s_Normals[normalIdx][2];

    int du_x = (u == 0) ? du_ao : 0;
    int du_y = (u == 1) ? du_ao : 0;
    int du_z = (u == 2) ? du_ao : 0;

    int dv_x = (v == 0) ? dv_ao : 0;
    int dv_y = (v == 1) ? dv_ao : 0;
    int dv_z = (v == 2) ? dv_ao : 0;

    /* Sample 2 orthogonal side blocks and 1 diagonal corner block in the air layer */
    int s1_x = bx + nx + du_x;
    int s1_y = by + ny + du_y;
    int s1_z = bz + nz + du_z;

    int s2_x = bx + nx + dv_x;
    int s2_y = by + ny + dv_y;
    int s2_z = bz + nz + dv_z;

    int c_x = bx + nx + du_x + dv_x;
    int c_y = by + ny + du_y + dv_y;
    int c_z = bz + nz + du_z + dv_z;

    bool s1 = Mesher_IsOpaque(Mesher_SampleVoxel(chunk, neighbors, s1_x, s1_y, s1_z));
    bool s2 = Mesher_IsOpaque(Mesher_SampleVoxel(chunk, neighbors, s2_x, s2_y, s2_z));
    bool c  = Mesher_IsOpaque(Mesher_SampleVoxel(chunk, neighbors, c_x,  c_y,  c_z));

    /* Corner rule: if both side walls are solid, light cannot penetrate the corner */
    if (s1 && s2) {
        return 0;
    }
    return (uint8_t)(3 - ((s1 ? 1 : 0) + (s2 ? 1 : 0) + (c ? 1 : 0)));
}

void Mesher_BuildMesh(const Chunk* chunk, const NeighborChunks* neighbors, ChunkMesh* outMesh) {
    if (!chunk || !outMesh) return;

    outMesh->vertices = s_ScratchVertices;
    outMesh->indices = s_ScratchIndices;
    outMesh->vertexCount = 0;
    outMesh->indexCount = 0;
    outMesh->maxVertices = MESHER_MAX_VERTICES;
    outMesh->maxIndices = MESHER_MAX_INDICES;

    int dims[3] = { CHUNK_WIDTH, CHUNK_HEIGHT, CHUNK_DEPTH };

    /* 3-axis Lysenko sweep: d = 0 (X), d = 1 (Y), d = 2 (Z) */
    for (int d = 0; d < 3; d++) {
        int u = (d + 1) % 3;
        int v = (d + 2) % 3;

        int uLimit = dims[u];
        int vLimit = dims[v];
        int dLimit = dims[d];

        int x[3] = { 0, 0, 0 };
        int q[3] = { 0, 0, 0 };
        q[d] = 1;

        /* Static 2D slice comparison mask (max 256 * 16 = 4096 elements) */
        int16_t mask[4096];

        for (x[d] = -1; x[d] < dLimit; ) {
            int n = 0;

            /* 1. Build signed comparison mask using direct neighbor sampling */
            for (x[v] = 0; x[v] < vLimit; x[v]++) {
                for (x[u] = 0; x[u] < uLimit; x[u]++) {
                    uint8_t b1 = Mesher_SampleVoxel(chunk, neighbors, x[0], x[1], x[2]);
                    uint8_t b2 = Mesher_SampleVoxel(chunk, neighbors, x[0] + q[0], x[1] + q[1], x[2] + q[2]);

                    bool op1 = Mesher_IsOpaque(b1);
                    bool op2 = Mesher_IsOpaque(b2);

                    if (op1 == op2) {
                        mask[n++] = 0;
                    } else if (op1) {
                        mask[n++] = (int16_t)b1;  /* Normal pointing +d */
                    } else {
                        mask[n++] = -(int16_t)b2; /* Normal pointing -d */
                    }
                }
            }

            x[d]++;
            n = 0;

            /* 2. Scanline merge contiguous coplanar faces */
            for (int j = 0; j < vLimit; j++) {
                for (int i = 0; i < uLimit; ) {
                    int16_t m = mask[i + j * uLimit];
                    if (m != 0) {
                        /* Width expansion (capped at 255 to fit 8-bit packing) */
                        int w = 1;
                        while ((i + w < uLimit) && (w < 255) && (mask[(i + w) + j * uLimit] == m)) {
                            w++;
                        }

                        /* Height expansion (capped at 255 to fit 8-bit packing) */
                        int h = 1;
                        bool done = false;
                        while ((j + h < vLimit) && (h < 255)) {
                            for (int k = 0; k < w; k++) {
                                if (mask[(i + k) + (j + h) * uLimit] != m) {
                                    done = true;
                                    break;
                                }
                            }
                            if (done) break;
                            h++;
                        }

                        /* Overflow safety guard */
                        if (outMesh->vertexCount + 4 > outMesh->maxVertices ||
                            outMesh->indexCount + 6 > outMesh->maxIndices) {
                            return;
                        }

                        /* 3. Emit Quad Geometry */
                        x[u] = i;
                        x[v] = j;

                        int du[3] = { 0, 0, 0 };
                        int dv[3] = { 0, 0, 0 };
                        du[u] = w;
                        dv[v] = h;

                        uint8_t blockId   = (uint8_t)(m > 0 ? m : -m);
                        uint8_t normalIdx = (uint8_t)(2 * d + (m > 0 ? 1 : 0));
                        uint32_t baseIdx  = outMesh->vertexCount;

                        /* Quad origin coordinates and AO evaluations */
                        uint8_t ao0, ao1, ao2, ao3;

                        if (m > 0) {
                            /* Face pointing +d: solid block is at x[d] - 1 */
                            int bx = (d == 0) ? (x[d] - 1) : x[0];
                            int by = (d == 1) ? (x[d] - 1) : x[1];
                            int bz = (d == 2) ? (x[d] - 1) : x[2];

                            /* 4 macro-quad corners in (u, v):
                               Corner 0: (i, j)
                               Corner 1: (i + w, j)
                               Corner 2: (i + w, j + h)
                               Corner 3: (i, j + h) */
                            ao0 = Mesher_ComputeVertexAO(chunk, neighbors,
                                (u==0 ? i : (v==0 ? j : bx)),
                                (u==1 ? i : (v==1 ? j : by)),
                                (u==2 ? i : (v==2 ? j : bz)), normalIdx, -1, -1);
                            ao1 = Mesher_ComputeVertexAO(chunk, neighbors,
                                (u==0 ? (i+w-1) : (v==0 ? j : bx)),
                                (u==1 ? (i+w-1) : (v==1 ? j : by)),
                                (u==2 ? (i+w-1) : (v==2 ? j : bz)), normalIdx, +1, -1);
                            ao2 = Mesher_ComputeVertexAO(chunk, neighbors,
                                (u==0 ? (i+w-1) : (v==0 ? (j+h-1) : bx)),
                                (u==1 ? (i+w-1) : (v==1 ? (j+h-1) : by)),
                                (u==2 ? (i+w-1) : (v==2 ? (j+h-1) : bz)), normalIdx, +1, +1);
                            ao3 = Mesher_ComputeVertexAO(chunk, neighbors,
                                (u==0 ? i : (v==0 ? (j+h-1) : bx)),
                                (u==1 ? i : (v==1 ? (j+h-1) : by)),
                                (u==2 ? i : (v==2 ? (j+h-1) : bz)), normalIdx, -1, +1);

                            /* Emit 4 CCW vertices */
                            outMesh->vertices[outMesh->vertexCount++] = Vertex_Pack(
                                (uint32_t)x[0], (uint32_t)x[1], (uint32_t)x[2], normalIdx, ao0, blockId, 0, 0, (uint32_t)w, (uint32_t)h);
                            outMesh->vertices[outMesh->vertexCount++] = Vertex_Pack(
                                (uint32_t)(x[0] + du[0]), (uint32_t)(x[1] + du[1]), (uint32_t)(x[2] + du[2]), normalIdx, ao1, blockId, (uint32_t)w, 0, (uint32_t)w, (uint32_t)h);
                            outMesh->vertices[outMesh->vertexCount++] = Vertex_Pack(
                                (uint32_t)(x[0] + du[0] + dv[0]), (uint32_t)(x[1] + du[1] + dv[1]), (uint32_t)(x[2] + du[2] + dv[2]), normalIdx, ao2, blockId, (uint32_t)w, (uint32_t)h, (uint32_t)w, (uint32_t)h);
                            outMesh->vertices[outMesh->vertexCount++] = Vertex_Pack(
                                (uint32_t)(x[0] + dv[0]), (uint32_t)(x[1] + dv[1]), (uint32_t)(x[2] + dv[2]), normalIdx, ao3, blockId, 0, (uint32_t)h, (uint32_t)w, (uint32_t)h);
                        } else {
                            /* Face pointing -d: solid block is at x[d] */
                            int bx = (d == 0) ? x[d] : x[0];
                            int by = (d == 1) ? x[d] : x[1];
                            int bz = (d == 2) ? x[d] : x[2];

                            /* 4 macro-quad corners in (u, v):
                               Corner 0: (i, j)
                               Corner 1: (i, j + h)
                               Corner 2: (i + w, j + h)
                               Corner 3: (i + w, j) */
                            ao0 = Mesher_ComputeVertexAO(chunk, neighbors,
                                (u==0 ? i : (v==0 ? j : bx)),
                                (u==1 ? i : (v==1 ? j : by)),
                                (u==2 ? i : (v==2 ? j : bz)), normalIdx, -1, -1);
                            ao1 = Mesher_ComputeVertexAO(chunk, neighbors,
                                (u==0 ? i : (v==0 ? (j+h-1) : bx)),
                                (u==1 ? i : (v==1 ? (j+h-1) : by)),
                                (u==2 ? i : (v==2 ? (j+h-1) : bz)), normalIdx, -1, +1);
                            ao2 = Mesher_ComputeVertexAO(chunk, neighbors,
                                (u==0 ? (i+w-1) : (v==0 ? (j+h-1) : bx)),
                                (u==1 ? (i+w-1) : (v==1 ? (j+h-1) : by)),
                                (u==2 ? (i+w-1) : (v==2 ? (j+h-1) : bz)), normalIdx, +1, +1);
                            ao3 = Mesher_ComputeVertexAO(chunk, neighbors,
                                (u==0 ? (i+w-1) : (v==0 ? j : bx)),
                                (u==1 ? (i+w-1) : (v==1 ? j : by)),
                                (u==2 ? (i+w-1) : (v==2 ? j : bz)), normalIdx, +1, -1);

                            /* Emit 4 CCW vertices */
                            outMesh->vertices[outMesh->vertexCount++] = Vertex_Pack(
                                (uint32_t)x[0], (uint32_t)x[1], (uint32_t)x[2], normalIdx, ao0, blockId, 0, 0, (uint32_t)w, (uint32_t)h);
                            outMesh->vertices[outMesh->vertexCount++] = Vertex_Pack(
                                (uint32_t)(x[0] + dv[0]), (uint32_t)(x[1] + dv[1]), (uint32_t)(x[2] + dv[2]), normalIdx, ao1, blockId, 0, (uint32_t)h, (uint32_t)w, (uint32_t)h);
                            outMesh->vertices[outMesh->vertexCount++] = Vertex_Pack(
                                (uint32_t)(x[0] + du[0] + dv[0]), (uint32_t)(x[1] + du[1] + dv[1]), (uint32_t)(x[2] + du[2] + dv[2]), normalIdx, ao2, blockId, (uint32_t)w, (uint32_t)h, (uint32_t)w, (uint32_t)h);
                            outMesh->vertices[outMesh->vertexCount++] = Vertex_Pack(
                                (uint32_t)(x[0] + du[0]), (uint32_t)(x[1] + du[1]), (uint32_t)(x[2] + du[2]), normalIdx, ao3, blockId, (uint32_t)w, 0, (uint32_t)w, (uint32_t)h);
                        }

                        /* 4. Quad Diagonal Triangulation Flip Guard */
                        if ((ao0 + ao2) > (ao1 + ao3)) {
                            /* Triangulate along diagonal (0, 2) */
                            outMesh->indices[outMesh->indexCount++] = baseIdx + 0;
                            outMesh->indices[outMesh->indexCount++] = baseIdx + 1;
                            outMesh->indices[outMesh->indexCount++] = baseIdx + 2;

                            outMesh->indices[outMesh->indexCount++] = baseIdx + 0;
                            outMesh->indices[outMesh->indexCount++] = baseIdx + 2;
                            outMesh->indices[outMesh->indexCount++] = baseIdx + 3;
                        } else {
                            /* Triangulate along diagonal (1, 3) */
                            outMesh->indices[outMesh->indexCount++] = baseIdx + 1;
                            outMesh->indices[outMesh->indexCount++] = baseIdx + 2;
                            outMesh->indices[outMesh->indexCount++] = baseIdx + 3;

                            outMesh->indices[outMesh->indexCount++] = baseIdx + 1;
                            outMesh->indices[outMesh->indexCount++] = baseIdx + 3;
                            outMesh->indices[outMesh->indexCount++] = baseIdx + 0;
                        }

                        /* 5. Clear merged region in mask */
                        for (int l = 0; l < h; l++) {
                            for (int k = 0; k < w; k++) {
                                mask[(i + k) + (j + l) * uLimit] = 0;
                            }
                        }

                        i += w;
                    } else {
                        i++;
                    }
                }
            }
        }
    }
}

/* ========================================================================= */
/* Budget-Capped Meshing Queue Implementation                                */
/* ========================================================================= */

void MesherQueue_Init(MesherQueue* mq, int maxChunksPerFrame, double timeBudgetMs) {
    if (!mq) return;
    mq->count = 0;
    mq->maxChunksPerFrame = (maxChunksPerFrame > 0) ? maxChunksPerFrame : 2;
    mq->timeBudgetMs = (timeBudgetMs > 0.0) ? timeBudgetMs : 1.5;
    memset(mq->queue, 0, sizeof(mq->queue));
}

void MesherQueue_Push(MesherQueue* mq, Chunk* chunk) {
    if (!mq || !chunk || chunk->inQueue || mq->count >= WORLD_ACTIVE_CHUNKS) return;
    chunk->inQueue = true;
    mq->queue[mq->count++] = chunk;
}

int MesherQueue_Process(MesherQueue* mq, int playerChunkX, int playerChunkZ) {
    if (!mq || mq->count == 0) return 0;

    int processed = 0;

    while (mq->count > 0 && processed < mq->maxChunksPerFrame) {
        /* Find closest chunk in queue by Manhattan distance */
        int bestIdx = 0;
        int bestDist = abs(mq->queue[0]->chunkX - playerChunkX) + abs(mq->queue[0]->chunkZ - playerChunkZ);

        for (int i = 1; i < mq->count; i++) {
            int dist = abs(mq->queue[i]->chunkX - playerChunkX) + abs(mq->queue[i]->chunkZ - playerChunkZ);
            if (dist < bestDist) {
                bestDist = dist;
                bestIdx = i;
            }
        }

        Chunk* targetChunk = mq->queue[bestIdx];

        /* Swap with last element and shrink count (O(1) pop) */
        mq->queue[bestIdx] = mq->queue[mq->count - 1];
        mq->count--;
        targetChunk->inQueue = false;

        /* Mesher execution and dirty clearing */
        ChunkNeighbors neighbors;
        World_GetChunkNeighbors(targetChunk->chunkX, targetChunk->chunkZ, &neighbors);
        ChunkMesh mesh;
        Mesher_BuildMesh(targetChunk, &neighbors, &mesh);
        targetChunk->vertexCount = mesh.vertexCount;
        targetChunk->indexCount = mesh.indexCount;
        targetChunk->isMeshDirty = false;
        Chunk_UploadGPU(targetChunk, &mesh);
        processed++;
    }

    return processed;
}
