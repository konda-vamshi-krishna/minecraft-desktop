/**
 * @file assets.h
 * @brief Master Embedded Texture Atlas, Block Visual Table, Face UV Mapping & Font Glyphs.
 *
 * Implements:
 * 1. 6-face anisotropic block texture tile coordinate resolution.
 * 2. Normalized UV coordinate generation with sub-texel bleed protection.
 * 3. CCW quad winding order definitions for vertex generation.
 * 4. In-memory .rodata texture atlas access (zero runtime filesystem calls).
 * 5. Retro ASCII bitmap font UV layout.
 *
 * ponytail: [UV mapping: half-margin inset epsilon] -> [GL_TEXTURE_2D_ARRAY to eliminate texel bleed at mip levels]
 * ponytail: [block registry: compile-time switch lookup] -> [dynamic data-driven JSON registry for modding]
 */

#ifndef MINECRAFT_ASSETS_ASSETS_H
#define MINECRAFT_ASSETS_ASSETS_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ============================================================================
 * 1. Block Face Enumeration (docs/04 §5.2)
 * ============================================================================ */
typedef enum BlockFace {
    FACE_WEST   = 0, /* -X face */
    FACE_EAST   = 1, /* +X face */
    FACE_NORTH  = 2, /* -Z face */
    FACE_SOUTH  = 3, /* +Z face */
    FACE_TOP    = 4, /* +Y face */
    FACE_BOTTOM = 5  /* -Y face */
} BlockFace;

#define FACE_COUNT 6

/* Canonical Block Type IDs (docs/04 §5.1 table) */
typedef enum AssetBlockType {
    ASSET_BLOCK_AIR         = 0,
    ASSET_BLOCK_GRASS       = 1,
    ASSET_BLOCK_DIRT        = 2,
    ASSET_BLOCK_STONE       = 3,
    ASSET_BLOCK_COBBLESTONE = 4,
    ASSET_BLOCK_WOOD        = 5,
    ASSET_BLOCK_LEAVES      = 6,
    ASSET_BLOCK_SAND        = 7,
    ASSET_BLOCK_BEDROCK     = 8,
    ASSET_BLOCK_WATER       = 9,
    ASSET_BLOCK_GLASS       = 10
} AssetBlockType;

/* ============================================================================
 * 2. Tile Coordinates & Normalized UV Structures
 * ============================================================================ */
typedef struct TileCoord {
    uint8_t tx; /* Column in 16x16 grid [0..15] */
    uint8_t ty; /* Row in 16x16 grid [0..15] */
} TileCoord;

typedef struct FaceUV {
    float u0, v0; /* Bottom-Left UV */
    float u1, v1; /* Top-Right UV */
} FaceUV;

/* 2D UV coordinate for a single vertex */
typedef struct QuadVertexUV {
    float u;
    float v;
} QuadVertexUV;

/* ============================================================================
 * 3. CCW Quad Winding Order Definitions (docs/04 §5.3)
 *
 * Quad vertices layout:
 *   (u0, v1) [V1: Top-Left]     +-------+ [V2: Top-Right]    (u1, v1)
 *                               |       |
 *   (u0, v0) [V0: Bottom-Left]  +-------+ [V3: Bottom-Right] (u1, v0)
 *
 * Emits two CCW triangles: (0, 1, 2) and (0, 2, 3)
 * ============================================================================ */
static const uint16_t QUAD_CCW_INDICES[6] = {0, 1, 2, 0, 2, 3};

/**
 * @brief Computes UV coordinates for all 4 vertices of a quad in CCW order:
 *        Index 0: Bottom-Left  (u0, v0)
 *        Index 1: Top-Left     (u0, v1)
 *        Index 2: Top-Right    (u1, v1)
 *        Index 3: Bottom-Right (u1, v0)
 */
static inline void Assets_GetQuadUVs(FaceUV uv, QuadVertexUV outVerts[4]) {
    if (!outVerts) return;
    outVerts[0].u = uv.u0; outVerts[0].v = uv.v0;
    outVerts[1].u = uv.u0; outVerts[1].v = uv.v1;
    outVerts[2].u = uv.u1; outVerts[2].v = uv.v1;
    outVerts[3].u = uv.u1; outVerts[3].v = uv.v0;
}

/* ============================================================================
 * 4. Block Visual Table API
 * ============================================================================ */

/**
 * @brief Resolves 16x16 tile coordinates (tx, ty) for a block type and face.
 *        Implements exact docs/04 §5.2 mapping table.
 */
TileCoord GetBlockTextureTile(uint8_t blockType, BlockFace face);

/**
 * @brief Resolves 16x16 tile coordinates for world.h BlockID enum.
 */
TileCoord Assets_GetWorldBlockTextureTile(uint8_t worldBlockId, BlockFace face);

/**
 * @brief Calculates normalized UV coordinates [0.0, 1.0] for a block face.
 *        Uses nearest-neighbor sampling (zero bleed margin).
 */
FaceUV CalculateFaceUV(uint8_t blockType, BlockFace face);

/**
 * @brief Calculates normalized UV coordinates with configurable bleed protection margin.
 * @param margin Sub-texel inset in texels (e.g. 0.0f for nearest, 0.5f for linear).
 */
FaceUV CalculateFaceUVWithBleed(uint8_t blockType, BlockFace face, float margin);

/**
 * @brief Retrieves the normalized UV rectangle for an ASCII font character (0..127).
 */
FaceUV Assets_GetFontGlyphUV(char c);

/* ============================================================================
 * 5. Embedded Atlas In-Memory Access & Texture Initialization API
 * ============================================================================ */

/**
 * @brief Returns direct pointer to static decompressed RGBA32 atlas in .rodata.
 *        Zero runtime filesystem calls (fopen/disk reads).
 */
const uint8_t* Assets_GetAtlasData(size_t* outWidth, size_t* outHeight);

/**
 * @brief Loads embedded atlas into GPU texture or returns standalone texture handle.
 */
uint32_t LoadEmbeddedAtlas(void);

#ifdef __cplusplus
}
#endif

#endif /* MINECRAFT_ASSETS_ASSETS_H */
