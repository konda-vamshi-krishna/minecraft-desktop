#ifndef MINECRAFT_CORE_MATH_UTILS_H
#define MINECRAFT_CORE_MATH_UTILS_H

#include <stdbool.h>
#include <stdint.h>
#include <math.h>
#include <string.h>

#ifndef M_PI
#define M_PI 3.14159265358979323846f
#endif

#define DEG2RAD(d) ((float)((d) * (M_PI / 180.0f)))
#define RAD2DEG(r) ((float)((r) * (180.0f / M_PI)))

// ponytail: [matrix pipeline: column-major float Mat4] -> [double-precision camera-relative origin if planetary scale requested]
// ponytail: [frustum culling: Gribb-Hartmann p-vertex AABB test] -> [hierarchical Z-buffer or occlusion culling if render distance >= 32]
// ponytail: [dynamic FOV: exponential decay lambda=12] -> [critically damped spring-damper solver]

/* ========================================================================= */
/* 1. Basic Vector & Matrix Data Structures                                 */
/* ========================================================================= */

typedef struct Vec2 {
    float x, y;
} Vec2;

typedef struct Vec3 {
    float x, y, z;
} Vec3;

typedef struct Vec4 {
    float x, y, z, w;
} Vec4;

/* 4x4 Matrix stored in column-major order matching OpenGL / Raylib: m[col * 4 + row] */
typedef struct Mat4 {
    float m[16];
} Mat4;

/* Axis-Aligned Bounding Box (AABB) */
typedef struct AABB {
    float minX, minY, minZ;
    float maxX, maxY, maxZ;
} AABB;

/* 3D Ray with precomputed inverse direction for branchless slab intersection */
typedef struct Ray {
    Vec3 origin;
    Vec3 dir;     /* Normalized unit direction vector */
    Vec3 invDir;  /* 1.0f / dir */
} Ray;

/* Geometric Plane: dot(normal, X) + d = 0 */
typedef struct Plane {
    Vec3 normal;  /* Normalized unit normal pointing inward to frustum */
    float d;      /* Plane distance constant */
} Plane;

/* 6-Plane Viewing Frustum */
typedef enum FrustumPlane {
    PLANE_LEFT = 0,
    PLANE_RIGHT,
    PLANE_BOTTOM,
    PLANE_TOP,
    PLANE_NEAR,
    PLANE_FAR,
    PLANE_COUNT
} FrustumPlane;

typedef struct Frustum {
    Plane planes[6];
} Frustum;

typedef enum FrustumResult {
    CULL_OUTSIDE = 0,
    CULL_INTERSECT = 1,
    CULL_INSIDE = 2
} FrustumResult;

/* Full Camera State */
typedef struct Camera {
    Vec3 position;
    float yaw;          /* [0.0, 360.0) degrees: 0 = -Z (North), 90 = +X (East) */
    float pitch;        /* [-89.0, +89.0] degrees: 0 = Horizon, +89 = Zenith, -89 = Nadir */

    Vec3 forward;       /* 3D view direction (unit length) */
    Vec3 right;         /* 3D camera right (unit length, co-planar with XZ) */
    Vec3 up;            /* 3D true camera up (unit length, orthogonal to forward & right) */
    Vec3 planarForward; /* 2D XZ forward (unit length) */
    Vec3 planarRight;   /* 2D XZ right (unit length) */

    float baseFov;      /* Base vertical Field of View (e.g. 70.0 deg) */
    float currentFov;   /* Current interpolated vertical FOV */
    float targetFov;    /* Target FOV (sprint 1.15x, sneak 0.90x, walk 1.0x) */
    float aspectRatio;  /* Viewport width / height */
    float nearPlane;    /* Near clipping plane distance (e.g. 0.1m) */
    float farPlane;     /* Far clipping plane distance (e.g. 256.0m) */

    Mat4 viewMatrix;     /* World-to-view transform */
    Mat4 projMatrix;     /* View-to-clip transform (OpenGL NDC [-1, +1]) */
    Mat4 viewProjMatrix; /* Combined projMatrix * viewMatrix */
    Frustum frustum;    /* 6 normalized inward-facing frustum planes */
} Camera;

/* ========================================================================= */
/* 2. Scalar Math & Bitshift Utilities                                       */
/* ========================================================================= */

static inline float ClampFloat(float val, float minVal, float maxVal) {
    if (val < minVal) return minVal;
    if (val > maxVal) return maxVal;
    return val;
}

static inline float WrapAngle360(float angle) {
    angle = fmodf(angle, 360.0f);
    if (angle < 0.0f) {
        angle += 360.0f;
    }
    /* Guard against IEEE 754 precision rounding up to 360.0f for small negative inputs in [-2^-16, 0.0) */
    if (angle >= 360.0f) {
        angle = 0.0f;
    }
    return angle;
}

static inline int FloorToInt(float f) {
    return (int)floorf(f);
}

/* Fast bitshift coordinate transformations (canonical Minecraft arithmetic) */
/* Two's-complement arithmetic right-shift guarantees floored division for negative coordinates */
static inline int WorldToChunkCoord(int worldCoord) {
    return worldCoord >> 4;
}

static inline int WorldToLocalCoord(int worldCoord) {
    return worldCoord & 15;
}

/* 3D Chunk voxel index with Y-stride 1 for optimal column cacheline traversal: [0..65535] */
static inline int ChunkVoxelIndex(int lx, int ly, int lz) {
    return ly + lx * 256 + lz * 4096;
}

/* ========================================================================= */
/* 3. 3D Vector Math Helpers                                                 */
/* ========================================================================= */

static inline Vec3 Vec3_Create(float x, float y, float z) {
    Vec3 v;
    v.x = x;
    v.y = y;
    v.z = z;
    return v;
}

static inline Vec3 Vec3_Add(Vec3 a, Vec3 b) {
    return Vec3_Create(a.x + b.x, a.y + b.y, a.z + b.z);
}

static inline Vec3 Vec3_Sub(Vec3 a, Vec3 b) {
    return Vec3_Create(a.x - b.x, a.y - b.y, a.z - b.z);
}

static inline Vec3 Vec3_Scale(Vec3 v, float s) {
    return Vec3_Create(v.x * s, v.y * s, v.z * s);
}

static inline float Vec3_Dot(Vec3 a, Vec3 b) {
    return a.x * b.x + a.y * b.y + a.z * b.z;
}

static inline Vec3 Vec3_Cross(Vec3 a, Vec3 b) {
    return Vec3_Create(
        a.y * b.z - a.z * b.y,
        a.z * b.x - a.x * b.z,
        a.x * b.y - a.y * b.x
    );
}

static inline float Vec3_LengthSq(Vec3 v) {
    return v.x * v.x + v.y * v.y + v.z * v.z;
}

static inline float Vec3_Length(Vec3 v) {
    return sqrtf(Vec3_LengthSq(v));
}

static inline Vec3 Vec3_Normalize(Vec3 v) {
    float len = Vec3_Length(v);
    if (len > 1e-7f) {
        float inv = 1.0f / len;
        return Vec3_Create(v.x * inv, v.y * inv, v.z * inv);
    }
    return Vec3_Create(0.0f, 0.0f, 0.0f);
}

static inline Vec3 Vec3_Lerp(Vec3 a, Vec3 b, float t) {
    return Vec3_Create(
        a.x + (b.x - a.x) * t,
        a.y + (b.y - a.y) * t,
        a.z + (b.z - a.z) * t
    );
}

/* ========================================================================= */
/* 4. 4x4 Matrix Math Helpers (Column-Major)                                 */
/* ========================================================================= */

static inline Mat4 Mat4_Identity(void) {
    Mat4 r;
    memset(r.m, 0, sizeof(r.m));
    r.m[0]  = 1.0f;
    r.m[5]  = 1.0f;
    r.m[10] = 1.0f;
    r.m[15] = 1.0f;
    return r;
}

static inline Mat4 Mat4_Multiply(const Mat4* a, const Mat4* b) {
    Mat4 out;
    for (int col = 0; col < 4; col++) {
        for (int row = 0; row < 4; row++) {
            out.m[col * 4 + row] =
                a->m[0 * 4 + row] * b->m[col * 4 + 0] +
                a->m[1 * 4 + row] * b->m[col * 4 + 1] +
                a->m[2 * 4 + row] * b->m[col * 4 + 2] +
                a->m[3 * 4 + row] * b->m[col * 4 + 3];
        }
    }
    return out;
}

/* LookAt Matrix derived directly from eye, forward, up, and right vectors:
   V = [  Rx   Ry   Rz  -dot(R,P) ]
       [  Ux   Uy   Uz  -dot(U,P) ]
       [ -Fx  -Fy  -Fz   dot(F,P) ]
       [   0    0    0          1 ]
   Stored in column-major order: m[col * 4 + row] */
static inline Mat4 Mat4_LookAtVectors(Vec3 eye, Vec3 forward, Vec3 up, Vec3 right) {
    Mat4 v;
    /* Column 0 */
    v.m[0] = right.x;
    v.m[1] = up.x;
    v.m[2] = -forward.x;
    v.m[3] = 0.0f;

    /* Column 1 */
    v.m[4] = right.y;
    v.m[5] = up.y;
    v.m[6] = -forward.y;
    v.m[7] = 0.0f;

    /* Column 2 */
    v.m[8] = right.z;
    v.m[9] = up.z;
    v.m[10] = -forward.z;
    v.m[11] = 0.0f;

    /* Column 3 */
    v.m[12] = -Vec3_Dot(right, eye);
    v.m[13] = -Vec3_Dot(up, eye);
    v.m[14] = Vec3_Dot(forward, eye);
    v.m[15] = 1.0f;

    return v;
}

/* Symmetric Perspective Projection Matrix mapping to OpenGL NDC [-1.0, +1.0]
   Stored in column-major order */
static inline Mat4 Mat4_Perspective(float fovRad, float aspect, float zNear, float zFar) {
    Mat4 p;
    memset(p.m, 0, sizeof(p.m));
    /* Defensive guard against window minimization or collapsed dimensions */
    if (aspect <= 0.0001f) aspect = 1.0f;
    float tanHalfFov = tanf(fovRad * 0.5f);
    float f = 1.0f / tanHalfFov;

    p.m[0]  = f / aspect;
    p.m[5]  = f;
    p.m[10] = -(zFar + zNear) / (zFar - zNear);
    p.m[11] = -1.0f;
    p.m[14] = -(2.0f * zFar * zNear) / (zFar - zNear);
    return p;
}

/* ========================================================================= */
/* 5. Direction Vectors & Camera System Implementation                       */
/* ========================================================================= */

/* Closed-form directional vectors calculated in 0 runtime square roots */
static inline void Camera_UpdateVectors(Camera* cam) {
    float yawRad   = DEG2RAD(cam->yaw);
    float pitchRad = DEG2RAD(cam->pitch);

    float cosPitch = cosf(pitchRad);
    float sinPitch = sinf(pitchRad);
    float cosYaw   = cosf(yawRad);
    float sinYaw   = sinf(yawRad);

    /* Canonical look vector F_look:
       Yaw=0 -> (0, 0, -1) North; Yaw=90 -> (1, 0, 0) East */
    cam->forward.x = cosPitch * sinYaw;
    cam->forward.y = sinPitch;
    cam->forward.z = -cosPitch * cosYaw;

    /* Planar horizontal vectors in XZ plane */
    cam->planarForward.x = sinYaw;
    cam->planarForward.y = 0.0f;
    cam->planarForward.z = -cosYaw;

    cam->planarRight.x = cosYaw;
    cam->planarRight.y = 0.0f;
    cam->planarRight.z = sinYaw;

    /* Camera right & true orthogonal up vector */
    cam->right = cam->planarRight;
    cam->up.x = -sinPitch * sinYaw;
    cam->up.y = cosPitch;
    cam->up.z = sinPitch * cosYaw;
}

static inline void Camera_Init(Camera* cam, Vec3 pos, float yaw, float pitch,
                               float baseFov, float aspect, float nearPlane, float farPlane) {
    memset(cam, 0, sizeof(Camera));
    cam->position = pos;
    cam->yaw = WrapAngle360(yaw);
    cam->pitch = ClampFloat(pitch, -89.0f, +89.0f);
    cam->baseFov = baseFov;
    cam->currentFov = baseFov;
    cam->targetFov = baseFov;
    cam->aspectRatio = aspect;
    cam->nearPlane = nearPlane;
    cam->farPlane = farPlane;
    Camera_UpdateVectors(cam);
}

static inline void Camera_Rotate(Camera* cam, float deltaYaw, float deltaPitch) {
    cam->yaw = WrapAngle360(cam->yaw + deltaYaw);
    cam->pitch = ClampFloat(cam->pitch + deltaPitch, -89.0f, +89.0f);
    Camera_UpdateVectors(cam);
}

/* Dynamic FOV with exponential asymptotic decay (Sprint 1.15x, Sneak 0.90x, lambda = 12.0 s^-1) */
static inline void Camera_UpdateFov(Camera* cam, bool isSprinting, bool isSneaking, float dt) {
    /* Sneak takes strict precedence over sprint per canonical Minecraft kinematics */
    if (isSneaking) {
        cam->targetFov = cam->baseFov * 0.90f;
    } else if (isSprinting) {
        cam->targetFov = cam->baseFov * 1.15f;
    } else {
        cam->targetFov = cam->baseFov;
    }

    if (dt > 0.0f) {
        float factor = 1.0f - expf(-12.0f * dt);
        cam->currentFov += (cam->targetFov - cam->currentFov) * factor;
    }
}

/* ========================================================================= */
/* 6. Frustum Extraction & Fast AABB p-Vertex Culling                        */
/* ========================================================================= */

static inline void Frustum_Extract(Frustum* f, const Mat4* m) {
    #define M(row, col) (m->m[(col) * 4 + (row)])

    /* Left Plane: r3 + r0 */
    f->planes[PLANE_LEFT].normal.x = M(3, 0) + M(0, 0);
    f->planes[PLANE_LEFT].normal.y = M(3, 1) + M(0, 1);
    f->planes[PLANE_LEFT].normal.z = M(3, 2) + M(0, 2);
    f->planes[PLANE_LEFT].d        = M(3, 3) + M(0, 3);

    /* Right Plane: r3 - r0 */
    f->planes[PLANE_RIGHT].normal.x = M(3, 0) - M(0, 0);
    f->planes[PLANE_RIGHT].normal.y = M(3, 1) - M(0, 1);
    f->planes[PLANE_RIGHT].normal.z = M(3, 2) - M(0, 2);
    f->planes[PLANE_RIGHT].d        = M(3, 3) - M(0, 3);

    /* Bottom Plane: r3 + r1 */
    f->planes[PLANE_BOTTOM].normal.x = M(3, 0) + M(1, 0);
    f->planes[PLANE_BOTTOM].normal.y = M(3, 1) + M(1, 1);
    f->planes[PLANE_BOTTOM].normal.z = M(3, 2) + M(1, 2);
    f->planes[PLANE_BOTTOM].d        = M(3, 3) + M(1, 3);

    /* Top Plane: r3 - r1 */
    f->planes[PLANE_TOP].normal.x = M(3, 0) - M(1, 0);
    f->planes[PLANE_TOP].normal.y = M(3, 1) - M(1, 1);
    f->planes[PLANE_TOP].normal.z = M(3, 2) - M(1, 2);
    f->planes[PLANE_TOP].d        = M(3, 3) - M(1, 3);

    /* Near Plane: r3 + r2 */
    f->planes[PLANE_NEAR].normal.x = M(3, 0) + M(2, 0);
    f->planes[PLANE_NEAR].normal.y = M(3, 1) + M(2, 1);
    f->planes[PLANE_NEAR].normal.z = M(3, 2) + M(2, 2);
    f->planes[PLANE_NEAR].d        = M(3, 3) + M(2, 3);

    /* Far Plane: r3 - r2 */
    f->planes[PLANE_FAR].normal.x = M(3, 0) - M(2, 0);
    f->planes[PLANE_FAR].normal.y = M(3, 1) - M(2, 1);
    f->planes[PLANE_FAR].normal.z = M(3, 2) - M(2, 2);
    f->planes[PLANE_FAR].d        = M(3, 3) - M(2, 3);

    #undef M

    /* Normalize all 6 planes to unit length normals */
    for (int i = 0; i < 6; i++) {
        float len = Vec3_Length(f->planes[i].normal);
        if (len > 1e-7f) {
            float inv = 1.0f / len;
            f->planes[i].normal = Vec3_Scale(f->planes[i].normal, inv);
            f->planes[i].d *= inv;
        }
    }
}

static inline void Camera_UpdateMatrices(Camera* cam) {
    cam->viewMatrix = Mat4_LookAtVectors(cam->position, cam->forward, cam->up, cam->right);
    cam->projMatrix = Mat4_Perspective(DEG2RAD(cam->currentFov), cam->aspectRatio,
                                       cam->nearPlane, cam->farPlane);
    cam->viewProjMatrix = Mat4_Multiply(&cam->projMatrix, &cam->viewMatrix);
    Frustum_Extract(&cam->frustum, &cam->viewProjMatrix);
}

/* Fast O(1) p-vertex / n-vertex AABB culling test against 6 normalized planes */
static inline FrustumResult Frustum_TestAABB(const Frustum* frustum, const AABB* box) {
    bool allInside = true;
    for (int i = 0; i < 6; i++) {
        const Plane* p = &frustum->planes[i];

        /* p-vertex (positive extreme point along plane normal) */
        float px = (p->normal.x > 0.0f) ? box->maxX : box->minX;
        float py = (p->normal.y > 0.0f) ? box->maxY : box->minY;
        float pz = (p->normal.z > 0.0f) ? box->maxZ : box->minZ;

        if (p->normal.x * px + p->normal.y * py + p->normal.z * pz + p->d < 0.0f) {
            return CULL_OUTSIDE;
        }

        /* n-vertex (negative extreme point along plane normal) */
        float nx = (p->normal.x > 0.0f) ? box->minX : box->maxX;
        float ny = (p->normal.y > 0.0f) ? box->minY : box->maxY;
        float nz = (p->normal.z > 0.0f) ? box->minZ : box->maxZ;

        if (p->normal.x * nx + p->normal.y * ny + p->normal.z * nz + p->d < 0.0f) {
            allInside = false;
        }
    }
    return allInside ? CULL_INSIDE : CULL_INTERSECT;
}

/* ========================================================================= */
/* 7. Collision & Ray Intersection Helpers                                   */
/* ========================================================================= */

static inline bool AABB_Intersects(const AABB* a, const AABB* b) {
    return (a->minX < b->maxX && a->maxX > b->minX) &&
           (a->minY < b->maxY && a->maxY > b->minY) &&
           (a->minZ < b->maxZ && a->maxZ > b->minZ);
}

static inline bool AABB_ContainsPoint(const AABB* b, Vec3 p) {
    return (p.x >= b->minX && p.x <= b->maxX) &&
           (p.y >= b->minY && p.y <= b->maxY) &&
           (p.z >= b->minZ && p.z <= b->maxZ);
}

static inline Ray Ray_Create(Vec3 origin, Vec3 dir) {
    Ray r;
    r.origin = origin;
    r.dir = Vec3_Normalize(dir);
    /* Preserve ray directional sign even when axis-parallel to prevent slab orientation inversion */
    r.invDir.x = (fabsf(r.dir.x) > 1e-8f) ? (1.0f / r.dir.x) : (r.dir.x < 0.0f ? -1e8f : 1e8f);
    r.invDir.y = (fabsf(r.dir.y) > 1e-8f) ? (1.0f / r.dir.y) : (r.dir.y < 0.0f ? -1e8f : 1e8f);
    r.invDir.z = (fabsf(r.dir.z) > 1e-8f) ? (1.0f / r.dir.z) : (r.dir.z < 0.0f ? -1e8f : 1e8f);
    return r;
}

/* Branchless Slab Ray-AABB intersection */
static inline bool Ray_IntersectAABB(const Ray* ray, const AABB* box, float* outTNear, float* outTFar) {
    float t1 = (box->minX - ray->origin.x) * ray->invDir.x;
    float t2 = (box->maxX - ray->origin.x) * ray->invDir.x;
    float tmin = (t1 < t2) ? t1 : t2;
    float tmax = (t1 > t2) ? t1 : t2;

    float t3 = (box->minY - ray->origin.y) * ray->invDir.y;
    float t4 = (box->maxY - ray->origin.y) * ray->invDir.y;
    float tymin = (t3 < t4) ? t3 : t4;
    float tymax = (t3 > t4) ? t3 : t4;

    if ((tmin > tymax) || (tymin > tmax)) return false;
    if (tymin > tmin) tmin = tymin;
    if (tymax < tmax) tmax = tymax;

    float t5 = (box->minZ - ray->origin.z) * ray->invDir.z;
    float t6 = (box->maxZ - ray->origin.z) * ray->invDir.z;
    float tzmin = (t5 < t6) ? t5 : t6;
    float tzmax = (t5 > t6) ? t5 : t6;

    if ((tmin > tzmax) || (tzmin > tmax)) return false;
    if (tzmin > tmin) tmin = tzmin;
    if (tzmax < tmax) tmax = tzmax;

    if (tmax < 0.0f) return false;

    if (outTNear) *outTNear = (tmin < 0.0f) ? 0.0f : tmin;
    if (outTFar) *outTFar = tmax;
    return true;
}

#endif /* MINECRAFT_CORE_MATH_UTILS_H */
