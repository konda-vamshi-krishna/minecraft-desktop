/**
 * @file assets.c
 * @brief Implementation of Embedded Asset Pipeline & Block Visual Table.
 *
 * ponytail: [embedded assets: compile-time .rodata array] -> [external resource pack loader]
 * ponytail: [block registry: compile-time switch lookup] -> [dynamic data-driven JSON registry for modding]
 */

#include "assets.h"
#include "atlas_data.h"

/* ============================================================================
 * Block Visual Mapping Table (docs/04 §5.2)
 * ============================================================================ */

TileCoord GetBlockTextureTile(uint8_t blockType, BlockFace face) {
    switch (blockType) {
        case 1: /* Grass */
            if (face == FACE_TOP)    return (TileCoord){0, 0};
            if (face == FACE_BOTTOM) return (TileCoord){2, 0};
            return (TileCoord){3, 0}; /* Sides: West, East, North, South */

        case 5: /* Wood / Log */
            if (face == FACE_TOP || face == FACE_BOTTOM) return (TileCoord){5, 1}; /* Rings */
            return (TileCoord){4, 1}; /* Bark */

        case 2:  return (TileCoord){2, 0};   /* Dirt */
        case 3:  return (TileCoord){1, 0};   /* Stone */
        case 4:  return (TileCoord){0, 1};   /* Cobblestone */
        case 6:  return (TileCoord){4, 3};   /* Leaves */
        case 7:  return (TileCoord){2, 1};   /* Sand */
        case 8:  return (TileCoord){1, 1};   /* Bedrock */
        case 9:  return (TileCoord){13, 12}; /* Water */
        case 10: return (TileCoord){1, 3};   /* Glass */

        default: return (TileCoord){15, 15}; /* Magenta/Black missing texture */
    }
}

TileCoord Assets_GetWorldBlockTextureTile(uint8_t worldBlockId, BlockFace face) {
    switch (worldBlockId) {
        case 1: /* BLOCK_STONE */
            return (TileCoord){1, 0};

        case 2: /* BLOCK_DIRT */
            return (TileCoord){2, 0};

        case 3: /* BLOCK_GRASS */
            if (face == FACE_TOP)    return (TileCoord){0, 0};
            if (face == FACE_BOTTOM) return (TileCoord){2, 0};
            return (TileCoord){3, 0};

        case 4: /* BLOCK_SAND */
            return (TileCoord){2, 1};

        case 5: /* BLOCK_SANDSTONE */
            return (TileCoord){0, 2};

        case 6: /* BLOCK_SNOW */
            if (face == FACE_BOTTOM) return (TileCoord){2, 0};
            return (TileCoord){2, 3};

        case 7: /* BLOCK_WOOD */
            if (face == FACE_TOP || face == FACE_BOTTOM) return (TileCoord){5, 1};
            return (TileCoord){4, 1};

        case 8: /* BLOCK_LEAVES */
            return (TileCoord){4, 3};

        case 9: /* BLOCK_BEDROCK */
            return (TileCoord){1, 1};

        case 10: /* BLOCK_WATER */
            return (TileCoord){13, 12};

        case 11: /* BLOCK_CACTUS */
            if (face == FACE_TOP || face == FACE_BOTTOM) return (TileCoord){6, 4};
            return (TileCoord){5, 4};

        case 12: /* BLOCK_FLOWER */
            return (TileCoord){12, 0};

        case 13: /* BLOCK_TALLGRASS */
            return (TileCoord){7, 2};

        case 14: /* Synthetic BLOCK_GLASS */
            return (TileCoord){1, 3};

        default:
            return (TileCoord){15, 15}; /* Missing texture slot */
    }
}

/* ============================================================================
 * UV Calculation & Bleed Protection
 * ============================================================================ */

FaceUV CalculateFaceUVWithBleed(uint8_t blockType, BlockFace face, float margin) {
    TileCoord tile = GetBlockTextureTile(blockType, face);
    const float atlasSize = (float)ATLAS_WIDTH;
    const float tileSize  = (float)ATLAS_TILE_SIZE;

    FaceUV uv;
    uv.u0 = (tile.tx * tileSize + margin) / atlasSize;
    uv.v0 = (tile.ty * tileSize + margin) / atlasSize;
    uv.u1 = ((tile.tx + 1.0f) * tileSize - margin) / atlasSize;
    uv.v1 = ((tile.ty + 1.0f) * tileSize - margin) / atlasSize;
    return uv;
}

FaceUV CalculateFaceUV(uint8_t blockType, BlockFace face) {
    /* ponytail: nearest-neighbor with zero bleed margin -> sub-texel half-margin inset if mipmapping enabled */
    return CalculateFaceUVWithBleed(blockType, face, 0.0f);
}

FaceUV Assets_GetFontGlyphUV(char c) {
    uint8_t ch = (uint8_t)c;
    if (ch > 127) {
        ch = (uint8_t)'?';
    }

    int cell = (int)ch / 2;
    int tx = cell % 16;
    int ty = 12 + (cell / 16);
    int subCol = (int)ch % 2;

    FaceUV uv;
    uv.u0 = (tx * 16.0f + subCol * 8.0f) / (float)ATLAS_WIDTH;
    uv.u1 = (tx * 16.0f + (subCol + 1) * 8.0f) / (float)ATLAS_WIDTH;
    uv.v0 = (ty * 16.0f) / (float)ATLAS_HEIGHT;
    uv.v1 = ((ty + 1.0f) * 16.0f) / (float)ATLAS_HEIGHT;
    return uv;
}

/* ============================================================================
 * Texture Initialization & In-Memory Data Access
 * ============================================================================ */

const uint8_t* Assets_GetAtlasData(size_t* outWidth, size_t* outHeight) {
    if (outWidth)  *outWidth  = ATLAS_WIDTH;
    if (outHeight) *outHeight = ATLAS_HEIGHT;
    return g_AtlasRGBA;
}

uint32_t LoadEmbeddedAtlas(void) {
    /* Headless standalone mode returns 1 (non-zero valid texture ID) */
    return 1;
}
