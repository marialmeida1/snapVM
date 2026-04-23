# Experiment 1: Benchmarking Rollback Mechanisms in Stateful Workflows (V1 Mock)

**IMPORTANT NOTE FOR V1:** *This initial experiment is designed to establish our core infrastructure metrics without the unpredictable noise of live LLMs. In this phase (V1), there is **no actual LLM integration**. The orchestrator will use a deterministic State Machine to precisely mock an agent's actions, failures, and recovery penalties. Once the infrastructure baselines are proven, V2 will integrate live LLMs.*

## Goal
Quantitatively measure the viability of full-state hardware isolation (Firecracker snapshots) against filesystem tracking (Git) during a complex, stateful failure. 

To prevent cross-contamination of metrics, the orchestration control plane executes the entire experimental scenario in completely independent, isolated trials for each baseline.

## 1. The Core Execution Scenario (Deterministic Mock)

We utilize a deterministic workflow involving a backend refactoring task backed by an active **PostgreSQL** database.

*   **Milestone Initialization:** The orchestrator boots the sandbox environment. Instead of prompting an agent, a Python script directly connects to the DB and runs `CREATE TABLE users (id serial PRIMARY KEY);` to simulate successful agent work. The orchestrator registers this success and triggers the state capture (Git commit or Firecracker Snapshot).
*   **Controlled Failure Injection:** The orchestrator systematically injects a simulated agent hallucination by dropping the critical user table (`DROP TABLE users;`), which makes the running web server fail the health contract.

## 2. Isolated Baseline Trials & Rollback Execution

Upon detecting the injected failure, the system triggers a rollback based on the active baseline:

*   **Baseline A (Git):** The orchestrator runs `git reset --hard` to revert the filesystem back to the milestone commit. 
*   **Baseline B (Firecracker):** The orchestrator destroys the corrupted microVM and restores a fresh microVM from full-state snapshot artifacts (`memory.bin` + `vmstate`) using Copy-on-Write memory mapping.

## 3. Verification & The Agent Penalty Simulation

Because V1 uses no LLMs, we calculate token waste deterministically using a **Penalty Routine**.

1.  **State-Diff Contract Execution:** The orchestrator probes the guest `/health` endpoint over the TAP network interface. The endpoint internally runs `SELECT 1 FROM users LIMIT 1`, validating both API liveness and DB schema state.
2.  **Evaluate Baseline B (Firecracker):** The snapshot restoration will instantly pass the State-Diff contract because the DB daemon memory is restored. Time is recorded.
3.  **Evaluate Baseline A (Git):** `git reset` will fail the State-Diff contract (the DB is still broken). 
4.  **The Penalty Routine (Git only):** To mock the LLM trying to debug the Git failure, the orchestrator triggers a simulated "manual fix" script that repairs the DB. We record the wall-clock time required for this penalty routine to pass the contract. In V2, this penalty time is replaced by measuring actual LLM token consumption.

## 4. V1 Mock Results and Analysis

The Orchestrator V1 successfully executed the deterministic baselines. The resulting metrics perfectly illustrate the "Git Stateful Flaw" and validate the potential of the Firecracker CoW restoration.

**Raw V1 Metrics (Mock - Averages over 10 iterations):**
```text
=== Baseline A: Git ===
  Pre-failure contract: True — state-diff contract passed
  Injecting failure...
  Post-failure contract: False — unhealthy
  Post-git-reset contract: False — unhealthy
  Post-penalty contract: True — state-diff contract passed

=== Baseline B: Firecracker Snapshot ===
  Pre-failure contract: True — state-diff contract passed
  Injecting failure...
  Post-failure contract: False — unhealthy
  Post-restore contract: True — state-diff contract passed

── Summary (Averages) ──
  [git]          capture=0.008s  restore=0.006s  storage=27420B      contract=PASS  penalty=0.004s
  [firecracker]  capture=0.413s  restore=0.158s  storage=268449211B  contract=PASS  penalty=0.000s
```

**Key Takeaways (Extrapolating V1 to V2 Reality):**

1. **The Git Stateful Flaw (Baseline A):** As explicitly proven, `git reset` completely failed to restore the dropped PostgreSQL table (`Post-git-reset contract: False`). To satisfy the state-diff contract, Git required the **Penalty Routine** to manually write and execute the schema fix. While this hardcoded Python fix took `~0.004s` in our mock, an actual LLM (in V2) would burn significant tokens and seconds (reading logs, writing SQL, retrying) to achieve the same result.
2. **Firecracker Snapshotting (Baseline B):** The Copy-on-Write restoration flawlessly resumed the database daemon in the exact state before the table was dropped, requiring absolutely zero Penalty Routine (`penalty=0.0000s`). The restored agent instantly passes the health check.
3. **The Storage / Capture Bottleneck:** Firecracker's heavy state capture took `~0.41s` (vs Git's `~0.008s`) and required `~268 MB` of storage for the memory dumps (vs Git's `~27 KB`). These are the known hardware trade-offs for perfect state fidelity.
4. **Restoration Speed:** The actual CoW restoration of the Linux kernel, Node memory, and DB daemon took an incredible `~0.16 seconds`. In the real-world V2, trading 400 milliseconds of capture time and 268MB of storage to prevent tens of seconds of hallucinated agent retry loops and expensive API tokens is a massive net positive.
