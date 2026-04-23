# Trial Setup and Known Limitations

This document details the methodology for setting up isolated trials to compare the two state-recovery approaches: **Git-based Filesystem Resets (Baseline A)** and **Firecracker MicroVM Snapshots (Baseline B)**. It also outlines the known technical limitations and trade-offs of each approach that this experiment seeks to quantify.

## Trial Setup Methodology

To ensure statistically significant and uncontaminated results, each trial is executed sequentially in a completely isolated environment, managed deterministically by the Python Orchestrator V1.

### Baseline A: Git-Based Reset
1. **Environment Initialization:** A fresh Firecracker MicroVM is booted (same guest environment used by both baselines). The orchestrator initializes a Git workdir on the host and initializes the guest DB schema (`CREATE TABLE users;`).
2. **State Capture (Milestone):** A standard `git commit` captures host-side milestone artifacts in the workdir while the guest continues running.
3. **Failure Injection:** A simulated agent hallucination occurs by dropping the critical `users` table via SQL, which causes the guest health contract to fail.
4. **Recovery Execution:**
   - The orchestrator runs `git reset --hard` to instantly revert the code.
   - Because Git cannot restore the database state, the orchestrator triggers a **Penalty Routine**. This simulates an agent realizing the DB is broken and spending time/tokens writing and executing manual rollback migrations (`CREATE TABLE users;`).
5. **Metric Collection:** The system measures the near-zero capture latency of Git, but records the massive end-to-end task latency accrued during the multi-step Penalty Routine required to pass the State-Diff Contract.

### Baseline B: Firecracker Snapshot Restore
1. **Environment Initialization:** A fresh Firecracker MicroVM is booted using the uncompressed `vmlinux` kernel and the `rootfs.ext4` filesystem. The Node.js server and PostgreSQL daemon start automatically. The DB schema is initialized via the TAP network interface.
2. **State Capture (Milestone):** The orchestrator pauses the MicroVM and calls the Firecracker API (`PUT /snapshot/create`) to dump the full state (`memory.bin`, `vmstate`) to the host disk.
3. **Failure Injection:** The identical simulated failure is injected via the network TAP interface by dropping the `users` table, which makes the health contract fail.
4. **Recovery Execution:**
   - The orchestrator violently destroys the corrupted MicroVM process.
   - A new MicroVM is instantly booted using the `PUT /snapshot/load` API, restoring the exact memory, daemon state, and DB schema via Copy-on-Write (CoW).
5. **Metric Collection:** The system measures the significant I/O latency required to generate the snapshot files, but contrasts it against the near-instantaneous (millisecond) restoration latency required to pass the State-Diff Contract without any Penalty Routine.

---

## Known Limitations and Trade-offs to Explore

The core hypothesis of this research is that the upfront cost of full-state snapshotting is vastly outweighed by the speed and reliability of CoW restoration when dealing with unpredictable agent failures. We will actively measure and explore the following known limitations:

### 1. Firecracker Snapshots: Memory & I/O Bottlenecks
While restoring a Firecracker snapshot takes milliseconds, *creating* the snapshot is an intensive operation. We are exploring the upper bounds of this limitation:
*   **Heavy State Capture (I/O Latency):** Dumping active RAM and block device deltas to disk requires significant host I/O throughput. If an AI agent creates frequent milestones (e.g., saving after every single file edit), the constant pausing and dumping of memory could severely degrade the overall workflow speed.
*   **Storage Footprint:** Unlike Git, which only stores lightweight line-by-file deltas, Firecracker snapshots require storing raw memory dumps. We will track how quickly host storage requirements scale (in Gigabytes) over multiple task iterations compared to a lightweight `.git` directory (in Kilobytes).

### The "Conditional Prompting" Logic
To ensure an unbiased measurement of agent effort, the Orchestrator follows a strict protocol after every rollback:
1.  **The Health Probe:** The Orchestrator executes the `State-Diff Contract` (HTTP `/health`).
2.  **The Decision:**
    *   **If Contract PASSES:** The trial ends immediately. No further tokens are spent.
    *   **If Contract FAILS:** The Orchestrator sends a **Recovery Prompt** to the agent, triggering the ReAct loop to begin debugging and repair.

Because **Git** cannot restore the running memory or database schema, it **always fails** the initial health probe, thereby always incurring the "Penalty" of agent repair. Because **Firecracker** restores the entire process tree, it **always passes** the probe, thereby avoiding the penalty. This is not a bias in the prompt logic, but a measurement of the state fidelity of each baseline.

---

## The Fairness Paradox: Why Baseline A is "Harder"
A common critique is that we "force" the agent to work in the Git baseline while allowing Firecracker to finish "silently." This is intentional:
*   **Git's "Hardness" is a property of its failure:** In a real production environment, if a `git reset` doesn't fix a corrupted database, a human or agent *must* manually repair it. We are simply measuring the cost of that reality.
*   **Firecracker's "Ease" is a property of its success:** The hardware-level restoration removes the *need* for repair. The "unfairness" in token consumption is the exact metric this research seeks to prove.
