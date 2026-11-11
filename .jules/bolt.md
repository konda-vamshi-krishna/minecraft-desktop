## 2026-11-11 - Static Inline Declarations Must Not Span Header and Source Files
**Learning:** In C, placing a `static inline` declaration in a header file but keeping its definition in a single `.c` file breaks compilation for any other file including the header (or triggers warnings about unused static functions).
**Action:** When converting an internal function to `static inline` for a specific `.c` file, always remove the declaration from the `.h` file completely.

## 2026-11-11 - Prefer Code Readability over Trivial Arithmetic Micro-Optimizations
**Learning:** Hardcoding bitshifts for multidimensional array access (e.g., `y + (x << 8) + (z << 12)`) in place of existing readable math (or helper macros like `ChunkVoxelIndex`) sacrifices maintainability for no real performance gain, as modern compilers automatically transform constant multiplications into bitshifts.
**Action:** Preserve readable code constructs or macros when optimizing, relying on compiler optimizations for trivial mathematical equivalencies.
