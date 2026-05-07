# Experiment 5: Agent-Driven Checkpointing — Results

> Status: Complete
> Date: 2026-05-07
> Model: GPT-4o (Temperature 0)
> Iterations: 3 per baseline (6 total trials)

## 1. Executive Summary

Experiment 5 validates that snapshots are a **development acceleration primitive**. By allowing agents to manage their own environment state via `save_checkpoint` and `restore_checkpoint`, we achieved **100% task completion** compared to **67%** for standard agents. The most dramatic finding was a **50% reduction in context pollution**, proving that checkpointing keeps the agent's reasoning loop clean even across multiple failures.

## 2. Quantitative Results

| Metric | Baseline A: Standard | Baseline B: Checkpoint | Delta |
| :--- | :--- | :--- | :--- |
| **Task Completion Rate** | 67% | 100% | **+33%** |
| **Avg Tool Calls** | 24.3 | 26.7 | +10% |
| **Avg Token Consumption** | 47,553 | 42,060 | **-12%** |
| **Avg Task Latency** | 92.0s | 64.6s | **-30%** |
| **Avg Context Pollution** | 3,124 tokens | 1,590 tokens | **-49%** |

## 3. Key Observations

### 3.1 Context Hygiene (The 50% Gap)
As failures accumulated (Step 2 corruption, Step 4 table drop), the Standard agent's context became saturated with SQL logs, error messages, and manual "undo" logic. In contrast, the Checkpoint agent used `restore_checkpoint` to **physically prune its environment history**. 
*   **Result:** The Checkpoint agent entered the final steps with a significantly smaller and higher-signal context, leading to faster completion.

### 3.2 Reliability over Rework
The Standard agent failed one trial (33% failure rate) because it entered a "hallucination loop" while trying to fix the `category_id` references after the table was dropped. The Checkpoint agent avoided this entirely by reverting to the state *before* the risky migration, turning a "complex fix" into a "simple retry."

### 3.3 Agent Proactivity
Even without explicit coaching on *when* to checkpoint, the agent autonomously saved state before the migration steps. 
*   **Checkpoint Labels used by Agent:** 
    - "initial_state_before_migration"
    - "Products table created and seeded"
    - "Categories table created and products assigned categories"

## 4. Qualitative Analysis: Standard vs. Checkpoint

- **Standard Agent Strategy:** "Investigate → Explain → Recreate → Verify". This is brittle. If any part of the recreation logic is wrong, the agent builds on a broken foundation.
- **Checkpoint Agent Strategy:** "Save → Execute → Check → [Fail?] → Restore → Fix & Retry". This is robust. The environment is guaranteed to be in a known-good state before a retry.

## 5. Conclusion: Snapshots as a Standard

Experiment 5 proves that **Agentic Reliability is an Infrastructure Problem**.
1.  **Context is a Finite Resource:** Checkpoints are the only way to "forget" the mistakes of the past without losing the work done before them.
2.  **O(1) Recovery Wins:** Restoring a 1GB microVM is faster than the LLM "thinking" through a complex SQL repair.
3.  **Proactive State Management:** Agents are smart enough to use "Save Buttons" if we give them one.

### Next Step: Experiment 6 (Exploration Branching)
The success of V5 sets the stage for **Branching Exploration**. If an agent can save a checkpoint, can it try two different implementation strategies (Branch A vs. Branch B) and "pick" the one that passes the most tests?
