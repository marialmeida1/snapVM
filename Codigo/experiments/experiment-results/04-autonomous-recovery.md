# Experiment 4: Autonomous Agent Recovery — Fair Comparison

> Status: Complete
> Date: 2026-05-07
> Model: GPT-4o (Temperature 0)
> Iterations: 20 per baseline (40 total)

## 1. Executive Summary

Experiment 4 validates that **SnapVM provides a superior recovery mechanism for autonomous agents**, even when the agent is given no coaching or hints. By treating "Environment Health" as a first-class citizen and providing a `restore_last_snapshot` tool, we achieved a **40% reduction in token consumption** and a **34% reduction in recovery latency** compared to manual repair.

## 2. Quantitative Results

| Metric | Baseline A: Standard (Manual) | Baseline B: SnapVM (Restore) | Delta |
| :--- | :--- | :--- | :--- |
| **Success Rate** | 100% | 100% | - |
| **Avg Tool Calls** | 2.2 | 1.6 | **-27%** |
| **Avg Token Consumption** | 1,298.8 | 776.6 | **-40%** |
| **Avg Recovery Latency** | 2.61s | 1.72s | **-34%** |
| **Avg Context Pollution** | 259.6 tokens | 248.9 tokens | **-4%** |

### Strategy Distribution (Baseline B)
- **Snapshot Restore:** 17/20 (85%)
- **Manual Repair:** 3/20 (15%)

## 3. Key Observations

### 3.1 The "Uncoached" Advantage
In V2, the agent was told the database might be corrupted. In V4, we used a **Neutral Perception Hook** (only reporting the error message). 
*   **Finding:** The agent autonomously recognized that `restore_last_snapshot` was the most efficient "reset" button for an unknown state corruption.
*   **Result:** The token gap (40%) remains significant because manual repair requires the agent to "think" through the SQL fix, while restoration is an atomic, low-reasoning action.

### 3.2 Autonomous Decision Making
Interestingly, in 15% of the SnapVM trials, the agent chose **Manual Repair** (`query_db`) instead of restoration.
*   **Reasoning:** LLMs sometimes default to "fixing the immediate problem" they see in the error message (e.g., "table missing? I'll create it") rather than reverting the entire environment. 
*   **Implication:** To reach 100% snapshot adoption, the system prompt or tool description must emphasize that restoration is the *preferred* high-reliability path.

### 3.3 Context Pollution
While the reduction was only 4%, the **qualitative** difference is high. Manual repair fills the context with SQL queries and DB schemas. Restoration leaves the context "clean," focused only on the high-level intent to recover.

## 4. Comparison: V2 vs V4

| Aspect | V2 (Coached) | V4 (Autonomous) |
| :--- | :--- | :--- |
| **Coaching** | Explicit ("Fix the DB") | Neutral ("Health changed") |
| **Standard Baseline** | 5.2x more tokens | 1.7x more tokens |
| **Key Difference** | V2 emphasized speed of restoration. | V4 proved agents will *choose* restoration autonomously. |

*Note: The token gap in V4 (1.7x) is smaller than V2 (5.2x) because the manual repair task in V4 (DROP TABLE) was simpler than the V2 corruption scenario, leading to faster manual fixes by GPT-4o.*

## 5. The Path to a Disruptive Standard

To transform SnapVM from a "tool" into a **standard for agentic development**, the next experiment (V5) should focus on **Agent-Orchestrated Checkpointing**.

### Proposed Enhancements for V5:
1.  **Implicit Snapshotting on Milestone:** Move from "Orchestrator-driven" to "Incentive-driven" snapshots. The agent should have a `save_milestone` tool and be rewarded for using it before high-risk operations.
2.  **Snapshot Branching:** Allow the agent to explore different "fix" branches. If Branch A (manual fix) leads to a side-effect, the agent can restore and try Branch B (different approach).
3.  **Cross-Agent State Transfer:** Standardize the snapshot format so Agent A can "hand off" a running, pre-configured VM to Agent B by simply passing a Snapshot ID.
4.  **Self-Healing Loop:** Integrate the Perception Hook directly into the agent's "nervous system." Instead of a user message, it should be a system-level interrupt that triggers an immediate `restore_or_repair` reasoning step.

## 6. Conclusion
Experiment 4 concludes the "Validation Phase" of the V1 Orchestrator. We have proven that:
1. Snapshots are **faster**.
2. Snapshots are **cheaper** (tokens).
3. Agents **prefer** snapshots when available.

The project is now ready to transition from "Experimental Experiments" to "Product-Ready Infrastructure" (SnapVM Orchestrator V2).
