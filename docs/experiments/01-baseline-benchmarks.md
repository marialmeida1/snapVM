# Experiment 1: Benchmarking Rollback Mechanisms in Stateful Workflows

## Goal
Quantitatively measure the viability of full-state hardware isolation (Firecracker snapshots) against filesystem tracking (Git) during a complex, stateful AI agentic failure.

To prevent cross-contamination of metrics, the orchestration control plane executes the entire experimental scenario in completely independent, isolated trials for each baseline.

## 1. The Core Execution Scenario

We utilize a deterministic workflow involving a backend refactoring task backed by an active **PostgreSQL** database. This ensures standard Git rollbacks natively fail to preserve execution state (such as TCP connection pools and database schemas).

*   **Milestone Initialization:** The AI agent boots a sandbox environment containing an active Node.js web server and a populated PostgreSQL database. The agent successfully writes a new API route. The orchestrator registers this success and triggers the state capture for the specific baseline being tested.
*   **Controlled Failure Injection:** Relying on an agent to fail organically is insufficient for rigorous benchmarking. We implement a systematic failure injection methodology where the agent is deliberately prompted to execute a hallucinated SQL migration command. This injected failure drops a critical user table (`DROP TABLE users;`) and causes a fatal crash in the active web server.

## 2. Isolated Baseline Trials & Rollback Execution

Upon detecting the injected failure, the system triggers a rollback based on the active baseline:

*   **Baseline A (Git):** The orchestrator runs `git reset --hard` to revert the code modifications back to the milestone commit. The system measures how long it takes for the agent to realize the PostgreSQL database and background server are still corrupted, and how many tokens it consumes trying to manually fix the running state.
*   **Baseline B (Firecracker):** At the milestone, the orchestrator calls the Firecracker API to generate the `vmstate`, `memory.gz`, and `disk.delta.gz` files. When the injected failure crashes the server, the microVM is destroyed. The orchestrator then restores a fresh microVM using `MAP_PRIVATE` Copy-on-Write memory mapping to instantly resume the exact execution state, including the active Node.js memory and PostgreSQL daemon state.

## 3. The Rollback and Replan Strategy

To prevent a "semantic rollback attack"—where the restored agent blindly repeats the flawed execution—the orchestrator implements a strict replanning phase post-rollback:

1.  **Truncate Context:** Rewind the agent's conversational memory (the LLM prompt history array) back to the exact moment the snapshot/commit was taken.
2.  **Inject Failure Context:** Inject a system message detailing the failure that would have happened (e.g., *"Attempting the previous SQL migration caused the server to crash. Formulate an alternative approach."*).
3.  **Verify via State-Diff Contract:** The orchestrator runs an external, deterministic Python script over the TAP network interface. It checks the physical reality of the environment (e.g., executing SQL queries via HTTP to confirm the table exists and pinging the network port) rather than relying on the LLM to self-report recovery.
