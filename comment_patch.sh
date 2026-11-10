sed -i '/static inline bool Mesher_IsOpaque/i \
/* [Bolt Optimization] Aggressive inlining of IsOpaque and SampleVoxel eliminates function call overhead \\n   in the innermost loops of the greedy mesher, improving mesh generation time. */\
' src/world/mesher.h
