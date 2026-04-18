# Experiment 1: Benchmarking Rollback Mechanisms in Stateful Workflows (V1 Mock)

**IMPORTANT NOTE FOR V1:** *This initial experiment is designed to establish our core infrastructure metrics without the unpredictable noise of live LLMs. In this phase (V1), there is **no actual LLM integration**. The orchestrator will use a deterministic State Machine to precisely mock an agent's actions, failures, and recovery penalties. Once the infrastructure baselines are proven, V2 will integrate live LLMs.*

## Goal
Quantitatively measure the viability of full-state hardware isolation (Firecracker snapshots) against filesystem tracking (Git) during a complex, stateful failure. 

To prevent cross-contamination of metrics, the orchestration control plane executes the entire experimental scenario in completely independent, isolated trials for each baseline.

## 1. The Core Execution Scenario (Deterministic Mock)

We utilize a deterministic workflow involving a backend refactoring task backed by an active **PostgreSQL** database.

*   **Milestone Initialization:** The orchestrator boots the sandbox environment. Instead of prompting an agent, a Python script directly connects to the DB and runs `CREATE TABLE users (id serial PRIMARY KEY);` to simulate successful agent work. The orchestrator registers this success and triggers the state capture (Git commit or Firecracker Snapshot).
*   **Controlled Failure Injection:** The orchestrator systematically injects a simulated agent hallucination. It drops the critical user table (`DROP TABLE users;`) and causes a fatal crash in the active web server.

## 2. Isolated Baseline Trials & Rollback Execution

Upon detecting the injected failure, the system triggers a rollback based on the active baseline:

*   **Baseline A (Git):** The orchestrator runs `git reset --hard` to revert the filesystem back to the milestone commit. 
*   **Baseline B (Firecracker):** The orchestrator destroys the corrupted microVM and restores a fresh microVM from the `memory.gz` and `disk.delta.gz` snapshots using `MAP_PRIVATE` Copy-on-Write memory mapping.

## 3. Verification & The Agent Penalty Simulation

Because V1 uses no LLMs, we calculate token waste deterministically using a **Penalty Routine**.

1.  **State-Diff Contract Execution:** The orchestrator runs an external Python script over the TAP network interface, attempting a `SELECT` query on the `users` table. 
2.  **Evaluate Baseline B (Firecracker):** The snapshot restoration will instantly pass the State-Diff contract because the DB daemon memory is restored. Time is recorded.
3.  **Evaluate Baseline A (Git):** `git reset` will fail the State-Diff contract (the DB is still broken). 
4.  **The Penalty Routine (Git only):** To mock the LLM trying to debug the Git failure, the orchestrator triggers a simulated "manual fix" script that repairs the DB. We record the wall-clock time required for this penalty routine to pass the contract. In V2, this penalty time is replaced by measuring actual LLM token consumption.
