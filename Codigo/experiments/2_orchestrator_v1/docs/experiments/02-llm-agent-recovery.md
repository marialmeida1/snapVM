# Experiment 2: LLM Agent Recovery and Token Efficiency (V2 Live)

This experiment advances the project from deterministic mocks (V1) to live LLM-driven orchestration (V2). We measure how physical state restoration (Firecracker) impacts the cognitive load, token cost, and recovery speed of a live AI agent compared to traditional filesystem-only rollbacks (Git).

## Goal
Quantitatively demonstrate that Firecracker's full-state restoration eliminates the "hallucination retry loop" and reduces token consumption by providing the agent with a perfectly consistent environment state immediately after a failure.

## 1. Experimental Setup & Orchestration

The experiment is managed by a Python **Orchestrator** that controls both the hardware lifecycle and the AI agent's perception.

### The Agent Harness
The agent operates within a **ReAct loop** (Reasoning + Acting) and is equipped with a suite of capability tools:
*   `query_db(sql)`: Executes SQL directly against the guest PostgreSQL.
*   `execute_bash(command)`: Runs shell commands via a guest agent.
*   `check_health()`: Probes the HTTP `/health` endpoint (queries the `users` table).

### The Complete Workflow
1.  **Task Initiation:** The Orchestrator prompts the agent to create the `users` table. The agent uses `query_db` and verifies success.
2.  **Milestone Capture:**
    *   **Git:** Performs a `git commit` of the filesystem.
    *   **Firecracker:** Pauses the VM and dumps 256MB of RAM + CPU state to disk.
3.  **Failure Injection:** The Orchestrator bypasses the agent and executes `DROP TABLE users;` directly against the database to simulate a stateful corruption/hallucination.
4.  **Rollback & Conditional Recovery:**
    *   The Orchestrator executes the baseline rollback (`git reset` or `snapshot restore`).
    *   **The Health Probe:** The Orchestrator calls `check_health()`.
    *   **Branching Logic:**
        *   **Baseline A (Git):** The health check **fails** (the DB is still broken). The Orchestrator sends a **Recovery Prompt**: *"The state was reset via Git, but the DB may still be corrupted. Please fix it."* The agent must then spend tokens to debug and repair the DB.
        *   **Baseline B (Firecracker):** The health check **passes** instantly (the DB memory was restored). The trial ends. The agent spends **zero** additional tokens.


## 2. Statistical Results (20 Iterations)

The following metrics represent the averages across 20 independent trials for each baseline.

| Metric | Baseline A (Git) | Baseline B (Firecracker) | Improvement |
|--------|------------------|--------------------------|-------------|
| **Capture Latency** | 0.030s | 0.484s | -1513% |
| **Restore Latency (Total)** | 6.572s | 0.184s | **3471%** |
| **Penalty Time (LLM Repair)** | 6.570s | 0.000s | **100%** |
| **Token Consumption** | 2860.3 | 549.2 | **5.2x Lower** |
| **Context Pollution** | 456.1 | 165.6 | **2.7x Lower** |
| **Storage Overhead** | 27.4 KB | 268.4 MB | -979,000% |

## 3. Analysis & Findings

### The "Hallucination Retry Loop" in Git
In Baseline A, `git reset --hard` successfully reverted the code and migrations on disk, but the **PostgreSQL memory and disk state remained corrupted**. The agent consumed an average of **2,311 additional tokens** per trial just to:
1.  Check the health endpoint.
2.  Observe the 500 error.
3.  Query the database to find the missing table.
4.  Re-run the migration or SQL command.
5.  Verify the fix.

This "recovery tax" resulted in an average penalty of **6.57 seconds** of wall-clock time per failure.

### Zero-Penalty Recovery with Firecracker
In Baseline B, the Firecracker snapshot restored the entire process tree, including the open file descriptors and memory pages of the PostgreSQL daemon. 
*   **Immediate Health:** The `/health` endpoint passed immediately upon restoration.
*   **Cognitive Load:** The agent required **zero additional messages** to repair the environment, as the environment was returned to a known-good state.
*   **Efficiency:** Firecracker reduced the total token burn by **80.8%**.

## 4. Conclusion
While Firecracker requires significantly more storage (~268MB vs ~27KB) and slightly more capture time (~0.48s vs ~0.03s), these costs are negligible compared to the massive savings in LLM API costs and the elimination of agentic failure modes. For high-stakes stateful workflows, hardware-level snapshots are the superior rollback mechanism.
