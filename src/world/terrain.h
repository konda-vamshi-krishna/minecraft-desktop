#ifndef MINECRAFT_WORLD_TERRAIN_H
#define MINECRAFT_WORLD_TERRAIN_H

#include "world.h"

#ifdef __cplusplus
extern "C" {
#endif

#ifndef CHUNK_SIZE_X
#define CHUNK_SIZE_X CHUNK_WIDTH
#define CHUNK_SIZE_Y CHUNK_HEIGHT
#define CHUNK_SIZE_Z CHUNK_DEPTH
#define CHUNK_TOTAL_VOXELS CHUNK_VOXEL_COUNT
#endif

#define TERRAIN_SEA_LEVEL 62
#define TERRAIN_BEDROCK_DEPTH 4
#define TERRAIN_SNOW_LINE 130

/* Dual-parameter Whittaker Biome Matrix Classification */
typedef enum BiomeType {
    BIOME_PLAINS     = 0,
    BIOME_DESERT     = 1,
    BIOME_MOUNTAINS  = 2,
    BIOME_FOREST     = 3,
    BIOME_COUNT      = 4
} BiomeType;

// ponytail: [Simplex: compile-time float constants] -> [AVX2 SIMD vector noise if generation latency > 5ms]
// ponytail: [feature decoration: local-chunk [2, 13] stamp] -> [two-phase boundary stitcher if multi-chunk structures added]
// ponytail: [biomes: 4 canonical Whittaker] -> [Voronoi cell graph for vanilla biome expansion]
// ponytail: [cave worms: dual 3D Simplex threshold] -> [3D Perlin noodle caves + cheese aquifers]

/* Deterministic Hash & Simplex Noise Interfaces */
uint64_t Terrain_HashCoords(int64_t x, int64_t z, uint64_t seed);
uint64_t Terrain_SplitMix64Next(uint64_t* state);
void Terrain_InitPermutation(uint64_t seed, uint8_t perm[512]);
float Terrain_Simplex2D(float xin, float yin, const uint8_t perm[512]);
float Terrain_Simplex3D(float xin, float yin, float zin, const uint8_t perm[512]);
float Terrain_Simplex2D_fBM(float x, float y, int octaves, float freq, float amp, float pers, float lac, const uint8_t perm[512]);
float Terrain_Simplex3D_fBM(float x, float y, float z, int octaves, float freq, float amp, float pers, float lac, const uint8_t perm[512]);

/* Biome & Terrain Generation Engine */
BiomeType Terrain_ClassifyBiome(float temperature, float moisture);
void Terrain_Init(uint64_t worldSeed);
void Terrain_GenerateChunk(int chunkX, int chunkZ, uint64_t worldSeed, uint8_t* outVoxels);

#ifdef __cplusplus
}
#endif

#endif /* MINECRAFT_WORLD_TERRAIN_H */
