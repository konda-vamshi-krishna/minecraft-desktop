## 2026-11-06 - Mesher SampleVoxel Optimization
**Learning:** The greedy voxel mesher is heavily bottlenecked by bounds checking and function call overheads in its innermost loops. Performance optimizations in this path should rely on `static inline` functions.
**Action:** Moving `Mesher_SampleVoxel` from `mesher.c` to `mesher.h` and making it `static inline` improves mesher performance by eliminating function call overhead in a heavily called path.
