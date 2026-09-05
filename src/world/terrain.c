#include "terrain.h"
#include <math.h>
#include <string.h>
#include <stdlib.h>

// ponytail: [Simplex skew factors: compile-time float constants] -> [AVX2 FMA instructions if SIMD vectorized]
// ponytail: [feature decoration: local-chunk [2, 13] stamp] -> [two-phase boundary stitcher if multi-chunk structures added]
// ponytail: [biomes: 4 canonical Whittaker] -> [Voronoi cell graph for vanilla biome expansion]
// ponytail: [cave worms: dual 3D Simplex threshold] -> [3D Perlin noodle caves + cheese aquifers]

static const float F2 = 0.3660254037844386f; /* 0.5f * (sqrtf(3.0f) - 1.0f) */
static const float G2 = 0.2113248654051871f; /* (3.0f - sqrtf(3.0f)) / 6.0f */

static const float F3 = 0.3333333333333333f; /* 1.0f / 3.0f */
static const float G3 = 0.1666666666666667f; /* 1.0f / 6.0f */

/* 2D simplex gradients: 8 directions */
static const float GRAD2[8][2] = {
    { 1.0f,  1.0f}, {-1.0f,  1.0f}, { 1.0f, -1.0f}, {-1.0f, -1.0f},
    { 1.0f,  0.0f}, {-1.0f,  0.0f}, { 0.0f,  1.0f}, { 0.0f, -1.0f}
};

/* 3D simplex gradients: 12 edge directions of a cube */
static const float GRAD3[12][3] = {
    { 1.0f,  1.0f,  0.0f}, {-1.0f,  1.0f,  0.0f}, { 1.0f, -1.0f,  0.0f}, {-1.0f, -1.0f,  0.0f},
    { 1.0f,  0.0f,  1.0f}, {-1.0f,  0.0f,  1.0f}, { 1.0f,  0.0f, -1.0f}, {-1.0f,  0.0f, -1.0f},
    { 0.0f,  1.0f,  1.0f}, { 0.0f, -1.0f,  1.0f}, { 0.0f,  1.0f, -1.0f}, { 0.0f, -1.0f, -1.0f}
};

static inline int FastFloor(float x) {
    int ix = (int)x;
    return (x < (float)ix) ? (ix - 1) : ix;
}

/* Static permutation tables for noise channels */
static uint8_t s_permTerrain[512];
static uint8_t s_permTemp[512];
static uint8_t s_permMoist[512];
static uint8_t s_permCave1[512];
static uint8_t s_permCave2[512];
static uint8_t s_permDensity[512];
static uint64_t s_currentSeed = 0;
static bool s_initialized = false;

/* ========================================================================= */
/* 2. Deterministic PRNG & Permutation Tables                                */
/* ========================================================================= */

uint64_t Terrain_HashCoords(int64_t x, int64_t z, uint64_t seed) {
    uint64_t x_u = (uint64_t)x;
    uint64_t z_u = (uint64_t)z;
    uint64_t z_state = seed + 0x9E3779B97F4A7C15ULL;
    z_state = (z_state ^ (x_u * 0xBF58476D1CE4E5B9ULL)) ^ (z_u * 0x94D049BB133111EBULL);
    z_state = (z_state ^ (z_state >> 30)) * 0xBF58476D1CE4E5B9ULL;
    z_state = (z_state ^ (z_state >> 27)) * 0x94D049BB133111EBULL;
    return z_state ^ (z_state >> 31);
}

uint64_t Terrain_SplitMix64Next(uint64_t* state) {
    uint64_t z = (*state += 0x9E3779B97F4A7C15ULL);
    z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ULL;
    z = (z ^ (z >> 27)) * 0x94D049BB133111EBULL;
    return z ^ (z >> 31);
}

void Terrain_InitPermutation(uint64_t seed, uint8_t perm[512]) {
    uint8_t p[256];
    for (int i = 0; i < 256; i++) {
        p[i] = (uint8_t)i;
    }

    uint64_t state = seed;
    for (int i = 255; i > 0; i--) {
        uint64_t randVal = Terrain_SplitMix64Next(&state);
        int j = (int)(randVal % (uint64_t)(i + 1));
        uint8_t temp = p[i];
        p[i] = p[j];
        p[j] = temp;
    }

    for (int i = 0; i < 512; i++) {
        perm[i] = p[i & 255];
    }
}

/* ========================================================================= */
/* 3. Simplex Noise Implementations (2D & 3D)                                 */
/* ========================================================================= */

float Terrain_Simplex2D(float xin, float yin, const uint8_t perm[512]) {
    float s = (xin + yin) * F2;
    int i = FastFloor(xin + s);
    int j = FastFloor(yin + s);

    float t = (float)(i + j) * G2;
    float X0 = (float)i - t;
    float Y0 = (float)j - t;
    float x0 = xin - X0;
    float y0 = yin - Y0;

    int i1, j1;
    if (x0 > y0) {
        i1 = 1; j1 = 0;
    } else {
        i1 = 0; j1 = 1;
    }

    float x1 = x0 - (float)i1 + G2;
    float y1 = y0 - (float)j1 + G2;
    float x2 = x0 - 1.0f + 2.0f * G2;
    float y2 = y0 - 1.0f + 2.0f * G2;

    int ii = i & 255;
    int jj = j & 255;

    int gi0 = perm[ii + perm[jj]] & 7;
    int gi1 = perm[ii + i1 + perm[jj + j1]] & 7;
    int gi2 = perm[ii + 1 + perm[jj + 1]] & 7;

    float n0 = 0.0f;
    float t0 = 0.5f - x0 * x0 - y0 * y0;
    if (t0 > 0.0f) {
        t0 *= t0;
        n0 = t0 * t0 * (GRAD2[gi0][0] * x0 + GRAD2[gi0][1] * y0);
    }

    float n1 = 0.0f;
    float t1 = 0.5f - x1 * x1 - y1 * y1;
    if (t1 > 0.0f) {
        t1 *= t1;
        n1 = t1 * t1 * (GRAD2[gi1][0] * x1 + GRAD2[gi1][1] * y1);
    }

    float n2 = 0.0f;
    float t2 = 0.5f - x2 * x2 - y2 * y2;
    if (t2 > 0.0f) {
        t2 *= t2;
        n2 = t2 * t2 * (GRAD2[gi2][0] * x2 + GRAD2[gi2][1] * y2);
    }

    return 70.0f * (n0 + n1 + n2);
}

float Terrain_Simplex3D(float xin, float yin, float zin, const uint8_t perm[512]) {
    float s = (xin + yin + zin) * F3;
    int i = FastFloor(xin + s);
    int j = FastFloor(yin + s);
    int k = FastFloor(zin + s);

    float t = (float)(i + j + k) * G3;
    float X0 = (float)i - t;
    float Y0 = (float)j - t;
    float Z0 = (float)k - t;
    float x0 = xin - X0;
    float y0 = yin - Y0;
    float z0 = zin - Z0;

    int i1, j1, k1;
    int i2, j2, k2;

    if (x0 >= y0) {
        if (y0 >= z0) {
            i1 = 1; j1 = 0; k1 = 0; i2 = 1; j2 = 1; k2 = 0;
        } else if (x0 >= z0) {
            i1 = 1; j1 = 0; k1 = 0; i2 = 1; j2 = 0; k2 = 1;
        } else {
            i1 = 0; j1 = 0; k1 = 1; i2 = 1; j2 = 0; k2 = 1;
        }
    } else {
        if (y0 < z0) {
            i1 = 0; j1 = 0; k1 = 1; i2 = 0; j2 = 1; k2 = 1;
        } else if (x0 < z0) {
            i1 = 0; j1 = 1; k1 = 0; i2 = 0; j2 = 1; k2 = 1;
        } else {
            i1 = 0; j1 = 1; k1 = 0; i2 = 1; j2 = 1; k2 = 0;
        }
    }

    float x1 = x0 - (float)i1 + G3;
    float y1 = y0 - (float)j1 + G3;
    float z1 = z0 - (float)k1 + G3;
    float x2 = x0 - (float)i2 + 2.0f * G3;
    float y2 = y0 - (float)j2 + 2.0f * G3;
    float z2 = z0 - (float)k2 + 2.0f * G3;
    float x3 = x0 - 1.0f + 3.0f * G3;
    float y3 = y0 - 1.0f + 3.0f * G3;
    float z3 = z0 - 1.0f + 3.0f * G3;

    int ii = i & 255;
    int jj = j & 255;
    int kk = k & 255;

    int gi0 = perm[ii + perm[jj + perm[kk]]] % 12;
    int gi1 = perm[ii + i1 + perm[jj + j1 + perm[kk + k1]]] % 12;
    int gi2 = perm[ii + i2 + perm[jj + j2 + perm[kk + k2]]] % 12;
    int gi3 = perm[ii + 1 + perm[jj + 1 + perm[kk + 1]]] % 12;

    float n0 = 0.0f;
    float t0 = 0.6f - x0 * x0 - y0 * y0 - z0 * z0;
    if (t0 > 0.0f) {
        t0 *= t0;
        n0 = t0 * t0 * (GRAD3[gi0][0] * x0 + GRAD3[gi0][1] * y0 + GRAD3[gi0][2] * z0);
    }

    float n1 = 0.0f;
    float t1 = 0.6f - x1 * x1 - y1 * y1 - z1 * z1;
    if (t1 > 0.0f) {
        t1 *= t1;
        n1 = t1 * t1 * (GRAD3[gi1][0] * x1 + GRAD3[gi1][1] * y1 + GRAD3[gi1][2] * z1);
    }

    float n2 = 0.0f;
    float t2 = 0.6f - x2 * x2 - y2 * y2 - z2 * z2;
    if (t2 > 0.0f) {
        t2 *= t2;
        n2 = t2 * t2 * (GRAD3[gi2][0] * x2 + GRAD3[gi2][1] * y2 + GRAD3[gi2][2] * z2);
    }

    float n3 = 0.0f;
    float t3 = 0.6f - x3 * x3 - y3 * y3 - z3 * z3;
    if (t3 > 0.0f) {
        t3 *= t3;
        n3 = t3 * t3 * (GRAD3[gi3][0] * x3 + GRAD3[gi3][1] * y3 + GRAD3[gi3][2] * z3);
    }

    return 32.0f * (n0 + n1 + n2 + n3);
}

float Terrain_Simplex2D_fBM(float x, float y, int octaves, float freq,
                            float amp, float pers, float lac,
                            const uint8_t perm[512]) {
    float total = 0.0f;
    float curFreq = freq;
    float curAmp = amp;
    for (int i = 0; i < octaves; i++) {
        total += Terrain_Simplex2D(x * curFreq, y * curFreq, perm) * curAmp;
        curAmp *= pers;
        curFreq *= lac;
    }
    return total;
}

float Terrain_Simplex3D_fBM(float x, float y, float z, int octaves, float freq,
                            float amp, float pers, float lac,
                            const uint8_t perm[512]) {
    float total = 0.0f;
    float curFreq = freq;
    float curAmp = amp;
    for (int i = 0; i < octaves; i++) {
        total += Terrain_Simplex3D(x * curFreq, y * curFreq, z * curFreq, perm) * curAmp;
        curAmp *= pers;
        curFreq *= lac;
    }
    return total;
}

/* ========================================================================= */
/* 4. Whittaker Biome Classification                                         */
/* ========================================================================= */

BiomeType Terrain_ClassifyBiome(float temperature, float moisture) {
    if (temperature < 0.4f) {
        return BIOME_MOUNTAINS;
    }
    if (moisture < 0.35f) {
        return BIOME_DESERT;
    }
    if (moisture >= 0.6f && temperature <= 0.7f) {
        return BIOME_FOREST;
    }
    return BIOME_PLAINS;
}

void Terrain_Init(uint64_t worldSeed) {
    Terrain_InitPermutation(worldSeed, s_permTerrain);
    Terrain_InitPermutation(worldSeed ^ 0x5555555555555555ULL, s_permTemp);
    Terrain_InitPermutation(worldSeed ^ 0xAAAAAAAAAAAAAAAAULL, s_permMoist);
    Terrain_InitPermutation(worldSeed ^ 0x1234567890ABCDEFULL, s_permCave1);
    Terrain_InitPermutation(worldSeed ^ 0xFEDCBA0987654321ULL, s_permCave2);
    Terrain_InitPermutation(worldSeed ^ 0x9876543210FEDCBAULL, s_permDensity);
    s_currentSeed = worldSeed;
    s_initialized = true;
}

/* ========================================================================= */
/* 5. Complete Chunk Procedural Generation Pipeline                         */
/* ========================================================================= */

void Terrain_GenerateChunk(int chunkX, int chunkZ, uint64_t worldSeed, uint8_t* outVoxels) {
    if (!s_initialized || s_currentSeed != worldSeed) {
        Terrain_Init(worldSeed);
    }

    memset(outVoxels, BLOCK_AIR, CHUNK_VOXEL_COUNT);

    float heights[CHUNK_WIDTH][CHUNK_DEPTH];
    BiomeType biomes[CHUNK_WIDTH][CHUNK_DEPTH];

    /* Step 1: Precompute 2D Continental Heightmap & Biomes across 16x16 grid */
    for (int lz = 0; lz < CHUNK_DEPTH; lz++) {
        int wz = chunkZ * CHUNK_DEPTH + lz;
        for (int lx = 0; lx < CHUNK_WIDTH; lx++) {
            int wx = chunkX * CHUNK_WIDTH + lx;

            /* Base continental fBM heightmap (5 octaves, sea level base 64.0f) */
            float h = 64.0f + Terrain_Simplex2D_fBM((float)wx, (float)wz, 5, 0.005f, 32.0f, 0.5f, 2.0f, s_permTerrain);

            /* Temperature and Moisture fields normalized to [0.0, 1.0] */
            float t = 0.5f + 0.5f * Terrain_Simplex2D_fBM((float)wx, (float)wz, 2, 0.0015f, 1.0f, 0.5f, 2.0f, s_permTemp);
            if (t < 0.0f) t = 0.0f; else if (t > 1.0f) t = 1.0f;

            float m = 0.5f + 0.5f * Terrain_Simplex2D_fBM((float)wx, (float)wz, 2, 0.0015f, 1.0f, 0.5f, 2.0f, s_permMoist);
            if (m < 0.0f) m = 0.0f; else if (m > 1.0f) m = 1.0f;

            BiomeType b = Terrain_ClassifyBiome(t, m);
            if (b == BIOME_MOUNTAINS) {
                /* Mountain crags elevation boost */
                h += 30.0f + 20.0f * Terrain_Simplex2D((float)wx * 0.01f, (float)wz * 0.01f, s_permTerrain);
            }

            heights[lx][lz] = h;
            biomes[lx][lz] = b;
        }
    }

    /* Step 2: 3D Volumetric Density & Cave Carve-Out */
    for (int lz = 0; lz < CHUNK_DEPTH; lz++) {
        int wz = chunkZ * CHUNK_DEPTH + lz;
        for (int lx = 0; lx < CHUNK_WIDTH; lx++) {
            int wx = chunkX * CHUNK_WIDTH + lx;
            float baseH = heights[lx][lz];
            BiomeType biome = biomes[lx][lz];

            float amp3D = (biome == BIOME_MOUNTAINS) ? 16.0f : ((biome == BIOME_DESERT) ? 6.0f : 4.0f);

            for (int ly = 0; ly < CHUNK_HEIGHT; ly++) {
                int idx = ChunkVoxelIndex(lx, ly, lz);

                /* Invariant Bedrock Base */
                if (ly == 0) {
                    outVoxels[idx] = BLOCK_BEDROCK;
                    continue;
                } else if (ly < TERRAIN_BEDROCK_DEPTH + 1) {
                    uint64_t hVal = Terrain_HashCoords(wx, wz, worldSeed ^ (uint64_t)ly) % 100ULL;
                    if (hVal < (uint64_t)((5 - ly) * 20)) {
                        outVoxels[idx] = BLOCK_BEDROCK;
                        continue;
                    }
                }

                /* 3D Volumetric Density: rho = H_2D - y + Simplex3D * A */
                float densNoise = Terrain_Simplex3D((float)wx * 0.02f, (float)ly * 0.02f, (float)wz * 0.02f, s_permDensity);
                float rho = baseH - (float)ly + densNoise * amp3D;

                if (rho > 0.0f) {
                    /* Solid rock -> evaluate dual 3D Simplex caves for y in [5, 128] */
                    bool isCave = false;
                    if (ly >= 5 && ly <= 128) {
                        float c1 = Terrain_Simplex3D((float)wx * 0.025f, (float)ly * 0.025f, (float)wz * 0.025f, s_permCave1);
                        if (fabsf(c1) < 0.05f) {
                            float c2 = Terrain_Simplex3D((float)wx * 0.025f, (float)ly * 0.025f, (float)wz * 0.025f, s_permCave2);
                            if (fabsf(c2) < 0.05f) {
                                isCave = true;
                            }
                        }
                    }

                    if (isCave) {
                        outVoxels[idx] = BLOCK_AIR;
                    } else {
                        outVoxels[idx] = BLOCK_STONE;
                    }
                } else {
                    /* Air or Sea Level Water (y <= 62) */
                    if (ly <= TERRAIN_SEA_LEVEL) {
                        outVoxels[idx] = BLOCK_WATER;
                    } else {
                        outVoxels[idx] = BLOCK_AIR;
                    }
                }
            }
        }
    }

    /* Step 3: Biome Stratigraphy & Surface Dressing */
    for (int lz = 0; lz < CHUNK_DEPTH; lz++) {
        for (int lx = 0; lx < CHUNK_WIDTH; lx++) {
            BiomeType biome = biomes[lx][lz];

            /* Find topmost solid voxel from sky downward */
            int surfaceY = -1;
            for (int ly = CHUNK_HEIGHT - 1; ly >= 1; ly--) {
                if (outVoxels[ChunkVoxelIndex(lx, ly, lz)] == BLOCK_STONE) {
                    surfaceY = ly;
                    break;
                }
            }

            if (surfaceY < 1) continue;

            if (surfaceY > TERRAIN_SEA_LEVEL) {
                /* Subaerial surface */
                if (biome == BIOME_DESERT) {
                    outVoxels[ChunkVoxelIndex(lx, surfaceY, lz)] = BLOCK_SAND;
                    for (int dy = 1; dy <= 3; dy++) {
                        if (surfaceY - dy >= 5 && outVoxels[ChunkVoxelIndex(lx, surfaceY - dy, lz)] == BLOCK_STONE) {
                            outVoxels[ChunkVoxelIndex(lx, surfaceY - dy, lz)] = BLOCK_SAND;
                        }
                    }
                    for (int dy = 4; dy <= 6; dy++) {
                        if (surfaceY - dy >= 5 && outVoxels[ChunkVoxelIndex(lx, surfaceY - dy, lz)] == BLOCK_STONE) {
                            outVoxels[ChunkVoxelIndex(lx, surfaceY - dy, lz)] = BLOCK_SANDSTONE;
                        }
                    }
                } else if (biome == BIOME_MOUNTAINS) {
                    if (surfaceY > TERRAIN_SNOW_LINE) {
                        outVoxels[ChunkVoxelIndex(lx, surfaceY, lz)] = BLOCK_SNOW;
                    }
                    /* Lower mountain rock remains BLOCK_STONE */
                } else {
                    /* Plains & Forest: Topsoil Grass + Subsurface Dirt */
                    outVoxels[ChunkVoxelIndex(lx, surfaceY, lz)] = BLOCK_GRASS;
                    for (int dy = 1; dy <= 3; dy++) {
                        if (surfaceY - dy >= 5 && outVoxels[ChunkVoxelIndex(lx, surfaceY - dy, lz)] == BLOCK_STONE) {
                            outVoxels[ChunkVoxelIndex(lx, surfaceY - dy, lz)] = BLOCK_DIRT;
                        }
                    }
                }
            } else {
                /* Subaqueous river/lake bed */
                for (int dy = 0; dy <= 2; dy++) {
                    if (surfaceY - dy >= 5 && outVoxels[ChunkVoxelIndex(lx, surfaceY - dy, lz)] == BLOCK_STONE) {
                        outVoxels[ChunkVoxelIndex(lx, surfaceY - dy, lz)] = (biome == BIOME_DESERT) ? BLOCK_SAND : BLOCK_DIRT;
                    }
                }
            }
        }
    }

    /* Step 4: Deterministic Cellular Feature Decoration */
    /* Local coordinates stamped strictly within [2, 13] x [2, 13] to prevent cross-chunk mutation */
    uint64_t chunkSeed = Terrain_HashCoords(chunkX, chunkZ, worldSeed);
    uint64_t state = chunkSeed;
    BiomeType centerBiome = biomes[CHUNK_WIDTH / 2][CHUNK_DEPTH / 2];

    int treeCount = 0;
    if (centerBiome == BIOME_FOREST) {
        treeCount = 5 + (int)(chunkSeed % 4ULL); /* 5 to 8 trees */
    } else if (centerBiome == BIOME_PLAINS) {
        treeCount = (chunkSeed % 10ULL == 0) ? 1 : 0; /* 10% chance of 1 tree */
    } else if (centerBiome == BIOME_MOUNTAINS) {
        treeCount = (chunkSeed % 4ULL == 0) ? 1 : 0; /* 25% chance of 1 pine */
    }

    /* Stamp Trees */
    for (int t = 0; t < treeCount; t++) {
        uint64_t r1 = Terrain_SplitMix64Next(&state);
        uint64_t r2 = Terrain_SplitMix64Next(&state);
        int tx = 2 + (int)(r1 % 12ULL); /* Local X in [2, 13] */
        int tz = 2 + (int)(r2 % 12ULL); /* Local Z in [2, 13] */

        int ty = -1;
        for (int y = CHUNK_HEIGHT - 6; y > TERRAIN_SEA_LEVEL; y--) {
            if (outVoxels[ChunkVoxelIndex(tx, y, tz)] == BLOCK_GRASS) {
                ty = y;
                break;
            }
        }

        if (ty > TERRAIN_SEA_LEVEL && ty + 8 < CHUNK_HEIGHT) {
            uint64_t rh = Terrain_SplitMix64Next(&state);
            int th = 4 + (int)(rh % 3ULL); /* Height in [4, 6] */

            /* Trunk */
            outVoxels[ChunkVoxelIndex(tx, ty, tz)] = BLOCK_DIRT;
            for (int y = ty + 1; y <= ty + th; y++) {
                outVoxels[ChunkVoxelIndex(tx, y, tz)] = BLOCK_WOOD;
            }

            /* Lower Canopy: 5x5 square (radius 2) at height th-1 and th */
            for (int dy = th - 1; dy <= th; dy++) {
                int cy = ty + dy;
                for (int dx = -2; dx <= 2; dx++) {
                    for (int dz = -2; dz <= 2; dz++) {
                        if (abs(dx) == 2 && abs(dz) == 2) continue; /* Corner trim */
                        int lx = tx + dx;
                        int lz = tz + dz;
                        int idx = ChunkVoxelIndex(lx, cy, lz);
                        if (outVoxels[idx] == BLOCK_AIR) {
                            outVoxels[idx] = BLOCK_LEAVES;
                        }
                    }
                }
            }

            /* Upper Canopy: 3x3 square (radius 1) at height th+1 */
            int cy1 = ty + th + 1;
            for (int dx = -1; dx <= 1; dx++) {
                for (int dz = -1; dz <= 1; dz++) {
                    int lx = tx + dx;
                    int lz = tz + dz;
                    int idx = ChunkVoxelIndex(lx, cy1, lz);
                    if (outVoxels[idx] == BLOCK_AIR) {
                        outVoxels[idx] = BLOCK_LEAVES;
                    }
                }
            }

            /* Top Cap: cross of 5 leaves at height th+2 */
            int cy2 = ty + th + 2;
            const int capOffsets[5][2] = {{0, 0}, {1, 0}, {-1, 0}, {0, 1}, {0, -1}};
            for (int c = 0; c < 5; c++) {
                int lx = tx + capOffsets[c][0];
                int lz = tz + capOffsets[c][1];
                int idx = ChunkVoxelIndex(lx, cy2, lz);
                if (outVoxels[idx] == BLOCK_AIR) {
                    outVoxels[idx] = BLOCK_LEAVES;
                }
            }
        }
    }

    /* Stamp Desert Cacti */
    if (centerBiome == BIOME_DESERT) {
        uint64_t rc = Terrain_SplitMix64Next(&state);
        int cactusCount = 2 + (int)(rc % 3ULL); /* 2 to 4 cacti */
        for (int c = 0; c < cactusCount; c++) {
            uint64_t r1 = Terrain_SplitMix64Next(&state);
            uint64_t r2 = Terrain_SplitMix64Next(&state);
            int cx = 2 + (int)(r1 % 12ULL);
            int cz = 2 + (int)(r2 % 12ULL);

            for (int y = 200; y > TERRAIN_SEA_LEVEL; y--) {
                if (outVoxels[ChunkVoxelIndex(cx, y, cz)] == BLOCK_SAND) {
                    uint64_t rh = Terrain_SplitMix64Next(&state);
                    int ch = 1 + (int)(rh % 3ULL);
                    for (int cy = y + 1; cy <= y + ch && cy < CHUNK_HEIGHT; cy++) {
                        outVoxels[ChunkVoxelIndex(cx, cy, cz)] = BLOCK_CACTUS;
                    }
                    break;
                }
            }
        }
    }

    /* Stamp Plains & Forest Flowers & Tall Grass */
    if (centerBiome == BIOME_PLAINS || centerBiome == BIOME_FOREST) {
        int flowerCount = (centerBiome == BIOME_PLAINS) ? 12 : 4;
        for (int f = 0; f < flowerCount; f++) {
            uint64_t r1 = Terrain_SplitMix64Next(&state);
            uint64_t r2 = Terrain_SplitMix64Next(&state);
            int fx = 1 + (int)(r1 % 14ULL);
            int fz = 1 + (int)(r2 % 14ULL);

            for (int y = 250; y > TERRAIN_SEA_LEVEL; y--) {
                if (outVoxels[ChunkVoxelIndex(fx, y, fz)] == BLOCK_GRASS) {
                    int idxAbove = ChunkVoxelIndex(fx, y + 1, fz);
                    if (outVoxels[idxAbove] == BLOCK_AIR) {
                        uint64_t rf = Terrain_SplitMix64Next(&state);
                        outVoxels[idxAbove] = (rf % 3ULL == 0) ? BLOCK_FLOWER : BLOCK_TALLGRASS;
                    }
                    break;
                }
            }
        }
    }
}
