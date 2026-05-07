# Experiment 4.1: Complex Stateful Failures — Results

> Status: Complete
> Date: 2026-05-07
> Model: GPT-4o (Temperature 0)
> Iterations: 4 per scenario (40 total trials)

## 1. Executive Summary

Experiment 4.1 tested SnapVM's recovery efficiency against **multi-layered, complex failures**. While the infrastructure proved capable of constant-time recovery, the **autonomous behavior of the agent** emerged as a key variable. The agent chose manual repair over snapshot restoration in **65% of trials**, significantly dampening the theoretical token savings.

## 2. Quantitative Results (Overall)

| Metric | Standard (Manual) | SnapVM (Autonomous) | Delta |
| :--- | :--- | :--- | :--- |
| **Success Rate** | 100% | 100% | - |
| **Avg Tool Calls** | 2.2 | 1.9 | **-14%** |
| **Avg Token Consumption** | 1,349.5 | 1,174.1 | **-13%** |
| **Avg Recovery Latency** | 2.85s | 2.14s | **-25%** |
| **Avg Context Pollution** | 276.1 tokens | 263.3 tokens | **-5%** |

## 3. Per-Scenario Breakdown

| Scenario | Std Calls | Snap Calls | Std Tokens | Snap Tokens | Snap Strategy |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **F1: Multi-table** | 3.0 | 3.0 | 1751 | 1688 | 50% Restore / 50% Manual |
| **F2: Process & Config** | 3.0 | 2.0 | 1758 | 1036 | 75% Restore / 25% Manual |
| **F3: Schema & Data** | 1.0 | 1.0 | 740 | 818 | 100% Manual |
| **F4: Permissions** | 3.0 | 2.5 | 1757 | 1514 | 50% Restore / 50% Manual |
| **F5: Cascade** | 1.0 | 1.0 | 742 | 816 | 100% Manual |

## 4. Key Observations

### 4.1 The "Sunk Cost" of Investigation
In scenarios F3 and F5, the agent chose to investigate the error and found a "simple" fix (or what it perceived as one) in the first call. This led to **0% snapshot usage** for these specific failure types.
*   **Insight:** If the error message is too descriptive, the agent's "helpful engineer" persona overrides the "efficiency-focused restorer" goal.

### 4.2 Scaling with Complexity
In scenarios F1, F2, and F4 (the "hardest" ones), when the agent *did* choose to restore, the cost was indeed **O(1)** (1 call, ~400 tokens). In contrast, the standard agent consistently required 3+ calls to diagnose and repair.
*   **Insight:** The "Scissors Chart" is visible but muted by the agent's autonomy.

### 4.3 Reliability vs. State-of-Mind
Standard manual repair is highly sensitive to hallucinations. While GPT-4o succeeded in 100% of these trials, the context was significantly more cluttered with SQL logs and bash output compared to the clean state following a snapshot restore.

## 5. Disruptive Standard: Lessons for V5

To make SnapVM a disruptive standard, we must address the **Decision Logic gap**:

1.  **Priority-Weighting Tools:** Future agents should be given meta-instructions that define `restore_last_snapshot` as a "Priority 0" recovery path.
2.  **Cost-Aware Agents:** Integrate token/latency costs into the agent's observation space so it can "see" that manual repair is 2-4x more expensive.
3.  **Heuristic Restoration:** In V5, we should test an "Auto-Restore" mode where the Orchestrator forces a snapshot restore if a health check fails, and the agent only acts to *validate* the restoration.

## 6. Infrastructure Improvements
During this experiment, we identified and fixed two critical infrastructure issues:
- **Trial Isolation:** Updated `_boot_vm` to use a temporary copy of the rootfs, ensuring one trial's corruption doesn't leak into the next.
- **Firecracker Restore Flow:** Corrected the resource configuration sequence in `snapshot.restore` to avoid "boot-specific resource" errors.

## 7. Conclusion
Experiment 4.1 confirms that while SnapVM infrastructure is ready for complex recovery, **Agent Psychology** is the next frontier. We have the "Time Machine" built; now we must teach the "Time Traveler" to use it.
