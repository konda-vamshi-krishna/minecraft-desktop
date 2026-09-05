/**
 * @file terrain.h
 * @brief Milestone 2: Procedural World Generation Engine Specification.
 *
 * Implements:
 * - Multi-octave 2D Simplex noise with fractional Brownian motion (fBM)
 * - Dual-parameter Whittaker biome matrix (Temperature & Moisture fields)
 * - 3D volumetric density terrain with overhangs, arches, and cliffs
 * - Dual 3D Simplex noise cave worm carve-out (|N1| < 0.05 && |N2| < 0.05)
 * - Deterministic SplitMix64 coordinate PRNG and cellular feature stamping
 * - Single-chunk boundary safety: zero cascading chunk mutation deadlocks
 *
 * Adheres strictly to Ponytail simplicity (C99, zero dynamic heap allocations,
 * 64-byte aligned flat memory buffers, cacheline-coherent Y-stride-1 traversal).
 */

#ifndef MINECRAFT_WORLD_TERRAIN_H
#define MINECRAFT_WORLD_TERRAIN_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ========================================================================= */
/* 1. Dimensions, Blocks, and Biomes                                         */
/* ========================================================================= */

#define CHUNK_SIZE_X 16
#define CHUNK_SIZE_Y 256
#define CHUNK_SIZE_Z 16
#define CHUNK_TOTAL_VOXELS (CHUNK_SIZE_X * CHUNK_SIZE_Y * CHUNK_SIZE_Z) /* 65536 bytes */

#define TERRAIN_SEA_LEVEL 62
#define TERRAIN_BEDROCK_DEPTH 4
#define TERRAIN_SNOW_LINE 130

/* Canonical Block IDs matching docs/03 §2.2 */
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

/* Dual-parameter Whittaker Biome Matrix Classification */
typedef enum BiomeType {
    BIOME_PLAINS     = 0,
    BIOME_DESERT     = 1,
    BIOME_MOUNTAINS  = 2,
    BIOME_FOREST     = 3,
    BIOME_COUNT      = 4
} BiomeType;

/* ========================================================================= */
/* 2. Deterministic Hash & Simplex Noise Interfaces                          */
/* ========================================================================= */

/**
 * @brief Computes a deterministic 64-bit coordinate hash (SplitMix64 derivative).
 */
uint64_t Terrain_HashCoords(int64_t x, int64_t z, uint64_t seed);

/**
 * @brief Advances a 64-bit SplitMix64 PRNG state and returns a pseudorandom integer.
 */
uint64_t Terrain_SplitMix64Next(uint64_t* state);

/**
 * @brief Initializes a 512-byte Simplex permutation table from a 64-bit seed.
 */
void Terrain_InitPermutation(uint64_t seed, uint8_t perm[512]);

/**
 * @brief Evaluates continuous 2D Simplex noise in range [-1.0, 1.0].
 */
float Terrain_Simplex2D(float xin, float yin, const uint8_t perm[512]);

/**
 * @brief Evaluates continuous 3D Simplex noise in range [-1.0, 1.0].
 */
float Terrain_Simplex3D(float xin, float yin, float zin, const uint8_t perm[512]);

/**
 * @brief Multi-octave 2D fractional Brownian motion (fBM) noise.
 */
float Terrain_Simplex2D_fBM(float x, float y, int octaves, float freq,
                            float amp, float pers, float lac,
                            const uint8_t perm[512]);

/**
 * @brief Multi-octave 3D fractional Brownian motion (fBM) noise.
 */
float Terrain_Simplex3D_fBM(float x, float y, float z, int octaves, float freq,
                            float amp, float pers, float lac,
                            const uint8_t perm[512]);

/* ========================================================================= */
/* 3. Biome & Terrain Generation Engine                                      */
/* ========================================================================= */

/**
 * @brief Classifies a biome from continuous Temperature and Moisture fields in [0.0, 1.0].
 */
BiomeType Terrain_ClassifyBiome(float temperature, float moisture);

/**
 * @brief Initializes global terrain generation permutation tables with the given world seed.
 */
void Terrain_Init(uint64_t worldSeed);

/**
 * @brief Generates a complete 64 KiB chunk voxel buffer for chunk coordinates (CX, CZ).
 *
 * Output buffer layout: Y-internal stride 1 (Index = ly + lx*256 + lz*4096).
 * Must be at least 65536 bytes (CHUNK_TOTAL_VOXELS).
 *
 * Guarantees:
 * - y=0 is 100% solid BLOCK_BEDROCK.
 * - y in [1, 4] contains non-traversable bedrock noise; caves never pierce y < 5.
 * - Caves carve out tubular corridors (|N1| < 0.05 && |N2| < 0.05) for y in [5, 128].
 * - Non-solid voxels with y <= 62 are filled with BLOCK_WATER.
 * - Surface decoration stamps strictly within local coords [2, 13] x [2, 13] with
 *   canopy radius <= 2, guaranteeing zero cascading chunk loading mutations.
 */
void Terrain_GenerateChunk(int chunkX, int chunkZ, uint64_t worldSeed, uint8_t* outVoxels);

#ifdef __cplusplus
}
#endif

#endif /* MINECRAFT_WORLD_TERRAIN_H */
