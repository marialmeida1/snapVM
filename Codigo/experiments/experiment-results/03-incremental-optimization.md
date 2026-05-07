# Experiment 3: Incremental State Optimization (Full vs. Diff)

While Experiment 2 proved that full-state restoration is superior for agentic recovery, it highlighted a significant storage bottleneck (~268MB per milestone). Experiment 3 focuses on optimizing the infrastructure to support frequent, low-cost "save points" using Firecracker's incremental snapshotting capabilities.

## Goal
Quantitatively compare the **Storage Footprint** and **Capture Latency** of "Full" snapshots (standard) against "Diff" snapshots (incremental) to enable high-frequency state management in Experiment 4.

## 1. Technical Methodology

### Firecracker Diff Snapshots
*   **Mechanism:** Firecracker supports capturing only the memory pages and disk blocks that have been modified since the previous snapshot or boot.
*   **Dirty-Page Tracking:** The microVM must be configured to track "dirty" pages.
*   **Trial Sequence:**
    1.  **Full Baseline:** Capture a standard "Full" snapshot at the first milestone.
    2.  **Incremental Trial:** Perform a task (e.g., seeding data), then capture a "Diff" snapshot.
    3.  **Metrics:** Compare the size of the resulting `memory.bin` and the time taken to flush to disk.

## 2. Metrics for Evaluation
*   **Snapshot Size (Bytes):** The delta in storage required for subsequent milestones.
*   **Capture Latency (Seconds):** The wall-clock time the microVM is paused during capture.
*   **Restoration Fidelity:** Verification that a VM restored from a chain of diff snapshots passes the `State-Diff Contract`.

## 3. Implementation Tasks
*   [ ] **Code:** Update `FirecrackerClient` and `snapshot.py` to expose the `snapshot_type` parameter.
*   [ ] **CLI:** Update `main.py` to support a new `diff-test` command or `--snapshot-type` flag.
*   [ ] **Automation:** Create a script that performs a multi-step task and captures a chain of 3 incremental snapshots.
*   [ ] **Reporting:** Update the reporting engine to track snapshot chains.

## 4. Results (V3 Optimization)

The following metrics were obtained by comparing a fresh boot (Base) against an incremental snapshot taken after seeding 10,000 PostgreSQL rows.

| Snapshot Type | Capture Latency | Physical Storage (Disk) | Improvement |
|---------------|-----------------|-------------------------|-------------|
| **Full (Base)** | 0.432s | 268.4 MB | - |
| **Diff (Incremental)** | 0.350s | 170.5 MB | **36.5% Lower** |

### Verification
*   **Restoration Fidelity:** PASS. The microVM restored from the `Diff` snapshot successfully passed the `State-Diff Contract` and resumed the PostgreSQL/Node.js stack with all 10,000 rows intact.

## 5. Analysis & Impact for Experiment 4

While the 36.5% reduction is significant, it is lower than the theoretical 90% expected. This is likely because:
1.  **PostgreSQL Background Writers:** The DB daemon likely dirtied many memory pages during the 10,000-row insert due to shared buffers and WAL (Write Ahead Log) activity.
2.  **OS Overhead:** The Linux kernel's page cache and active process management dirty a baseline amount of memory regardless of the application task.

**Conclusion:** 
Even with a heavy database workload, incremental snapshots offer a **~37% storage saving** and a **~19% reduction in capture latency**. For Experiment 4, this allows the agent to take more frequent checkpoints without saturating host I/O as quickly as full snapshots would.
