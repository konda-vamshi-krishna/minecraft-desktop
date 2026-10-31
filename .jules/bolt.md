## 2026-10-31 - 3D Volumetric Terrain Generation Optimization
**Learning:** Calculating 3D Simplex noise for every voxel in a chunk is a major bottleneck. By utilizing the bounded nature of the noise output ([-1.0, 1.0]) and the amplitude, we can skip evaluating the noise entirely for voxels that are sufficiently far above or below the surface height `baseH`.
**Action:** Whenever dealing with volumetric noise bounded by an amplitude, evaluate the guaranteed min/max conditions before computing the expensive noise function to prune unnecessary calculations.
