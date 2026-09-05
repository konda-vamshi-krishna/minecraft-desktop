# Global Swarm Timer & Scheduling Policy (Refined)

> Enforced globally across Main Agent, Subagents, Orchestrators, Sentinels, and Workers.

## Mandatory Timing Invariants:
1. **Mandatory Pre-Estimate:** Before scheduling any timer or cron, the agent MUST explicitly estimate the expected workload duration.
2. **Standard & Moderate Workloads [100s to 300s]:**
   - **Lightweight / Quick Liveness Checks:** 100 seconds (1m 40s).
   - **Standard Iterations & Module Gating:** 180 seconds to 300 seconds (3 to 5 minutes).
3. **Heavy Workload Exception [300s to 600s]:**
   - **Condition:** ONLY permitted when an empirical estimate proves the task will exceed 5 minutes (e.g., massive multi-platform compiles, exhaustive fuzzing sweeps, full project rebuilds).
   - **Timeframe:** Strictly between 5 minutes and 10 minutes (300s to 600s).
4. **Absolute Hard Ceiling Forever:**
   - **Under 10 minutes (<600 seconds) strictly.** Timers of 10 minutes or longer are permanently banned under all circumstances.
