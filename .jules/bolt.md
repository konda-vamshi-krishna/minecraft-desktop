## 2024-03-24 - Inline fast path in mesher sampling
**Learning:** The greedy voxel mesher (`src/world/mesher.c`) is heavily bottlenecked by bounds checking and function call overheads in its innermost loops.
**Action:** In `Mesher_SampleVoxel`, use `static inline` and optimize the fast-path (inside the chunk bounds) to eliminate function call overhead and branch prediction misses.
