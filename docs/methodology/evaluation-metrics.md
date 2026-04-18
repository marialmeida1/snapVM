# Evaluation Metrics

During each isolated trial (Git vs. Firecracker), the Python orchestrator's telemetry engine records two primary categories of quantitative metrics. These metrics are designed to highlight the trade-offs between physical storage footprint and LLM context/compute efficiency.

## 1. Infrastructure Performance Metrics

These metrics evaluate the physical overhead and speed of the state management operations.

*   **State Capture Latency:** The system wall-clock time required to freeze and serialize the environment at the milestone. (e.g., running `git commit` vs. flushing memory to disk via Firecracker API).
*   **Restoration Latency:** The precise millisecond duration required to resurrect the environment and resume the process tree from the moment of rollback initiation to the moment the State-Diff Contract passes.
*   **Storage Overhead:** The physical disk space footprint required to maintain the milestone captures. This compares the lightweight delta of a `.git` folder against Firecracker's raw memory dumps (`memory.gz`, `disk.delta.gz`, `vmstate`).

## 2. Agentic Efficiency Metrics

These metrics evaluate the economic and operational impact of the rollback mechanism on the AI Agent's performance.

*   **Recovery Rate (State Fidelity):** A binary pass/fail metric determining the percentage of trials where the PostgreSQL database and Node.js server successfully survived the rollback *without* requiring manual agent intervention to repair connections or schemas.
*   **LLM Token Consumption:** The exact number of prompt and completion tokens consumed from the moment the failure is injected until the task is successfully resolved. This measures the cost of "hallucinated retry loops" in Baseline A.
*   **Context Window Pollution:** The total token length of the agent's conversational memory at task completion. This measures how much debugging "noise" was accumulated during the recovery phase.
*   **End-to-End Task Latency:** The total wall-clock time from the injected failure to successful resolution. This determines whether slower snapshot captures (Firecracker) are ultimately offset by faster, token-efficient recoveries compared to manual agent debugging.
