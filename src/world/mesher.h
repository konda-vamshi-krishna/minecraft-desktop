#ifndef MINECRAFT_WORLD_MESHER_H
#define MINECRAFT_WORLD_MESHER_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include "world.h"

#ifdef __cplusplus
extern "C" {
#endif

/* Maximum theoretical limits for chunk scratch buffers */
#define MESHER_MAX_QUADS 32768
#define MESHER_MAX_VERTICES (MESHER_MAX_QUADS * 4) /* 131072 vertices = 1024 KiB */
#define MESHER_MAX_INDICES  (MESHER_MAX_QUADS * 6) /* 196608 indices  = 768 KiB */

/* Face Normal Indices (0..5) */
typedef enum FaceNormal {
    FACE_NEG_X = 0, /* -X (West)   */
    FACE_POS_X = 1, /* +X (East)   */
    FACE_NEG_Y = 2, /* -Y (Bottom) */
    FACE_POS_Y = 3, /* +Y (Top)    */
    FACE_NEG_Z = 4, /* -Z (North)  */
    FACE_POS_Z = 5  /* +Z (South)  */
} FaceNormal;

/*
 * Packed Vertex Format (8 bytes total):
 *
 * data0 (32 bits):
 *   Bits  0..4  (5 bits): X coordinate in chunk (0..16)
 *   Bits  5..13 (9 bits): Y coordinate in chunk (0..256)
 *   Bits 14..18 (5 bits): Z coordinate in chunk (0..16)
 *   Bits 19..21 (3 bits): Normal face index (0..5)
 *   Bits 22..23 (2 bits): Ambient Occlusion (0..3)
 *   Bits 24..31 (8 bits): Block ID (0..255)
 *
 * data1 (32 bits):
 *   Bits  0..7  (8 bits): U texture coordinate (0..255)
 *   Bits  8..15 (8 bits): V texture coordinate (0..255)
 *   Bits 16..23 (8 bits): Quad Width W (1..255)
 *   Bits 24..31 (8 bits): Quad Height H (1..255)
 */
typedef struct PackedVertex {
    uint32_t data0;
    uint32_t data1;
} PackedVertex;

/* Neighbor chunk pointers for boundary face culling */
typedef ChunkNeighbors NeighborChunks;

/* CPU Mesh Buffer for scratch generation and GPU upload */
typedef struct ChunkMesh {
    PackedVertex* vertices;
    uint32_t* indices;
    uint32_t vertexCount;
    uint32_t indexCount;
    uint32_t maxVertices;
    uint32_t maxIndices;
} ChunkMesh;

/* Core Mesher API */
static inline PackedVertex Vertex_Pack(
    uint32_t x, uint32_t y, uint32_t z,
    uint32_t normal, uint32_t ao, uint32_t blockId,
    uint32_t u, uint32_t v, uint32_t w, uint32_t h
) {
    PackedVertex vert;
    vert.data0 = (x & 0x1FU) |
                 ((y & 0x1FFU) << 5) |
                 ((z & 0x1FU)  << 14) |
                 ((normal & 0x7U) << 19) |
                 ((ao & 0x3U) << 22) |
                 ((blockId & 0xFFU) << 24);
    vert.data1 = (u & 0xFFU) |
                 ((v & 0xFFU) << 8) |
                 ((w & 0xFFU) << 16) |
                 ((h & 0xFFU) << 24);
    return vert;
}

static inline void Vertex_Unpack(
    PackedVertex vert,
    uint32_t* outX, uint32_t* outY, uint32_t* outZ,
    uint32_t* outNormal, uint32_t* outAO, uint32_t* outBlockId,
    uint32_t* outU, uint32_t* outV, uint32_t* outW, uint32_t* outH
) {
    if (outX)       *outX       = vert.data0 & 0x1FU;
    if (outY)       *outY       = (vert.data0 >> 5) & 0x1FFU;
    if (outZ)       *outZ       = (vert.data0 >> 14) & 0x1FU;
    if (outNormal)  *outNormal  = (vert.data0 >> 19) & 0x7U;
    if (outAO)      *outAO      = (vert.data0 >> 22) & 0x3U;
    if (outBlockId) *outBlockId = (vert.data0 >> 24) & 0xFFU;

    if (outU) *outU = vert.data1 & 0xFFU;
    if (outV) *outV = (vert.data1 >> 8) & 0xFFU;
    if (outW) *outW = (vert.data1 >> 16) & 0xFFU;
    if (outH) *outH = (vert.data1 >> 24) & 0xFFU;
}

bool Mesher_IsOpaque(uint8_t blockId);
uint8_t Mesher_SampleVoxel(const Chunk* chunk, const NeighborChunks* neighbors, int x, int y, int z);
uint8_t Mesher_ComputeVertexAO(const Chunk* chunk, const NeighborChunks* neighbors,
                               int bx, int by, int bz, int normalIdx, int du_ao, int dv_ao);
void Mesher_BuildMesh(const Chunk* chunk, const NeighborChunks* neighbors, ChunkMesh* outMesh);

/* Budget-Capped Meshing Queue API */
typedef struct MesherQueue {
    Chunk* queue[WORLD_ACTIVE_CHUNKS];
    int count;
    int maxChunksPerFrame;
    double timeBudgetMs;
} MesherQueue;

void MesherQueue_Init(MesherQueue* mq, int maxChunksPerFrame, double timeBudgetMs);
void MesherQueue_Push(MesherQueue* mq, Chunk* chunk);
int MesherQueue_Process(MesherQueue* mq, int playerChunkX, int playerChunkZ);

#ifdef __cplusplus
}
#endif

#endif /* MINECRAFT_WORLD_MESHER_H */
