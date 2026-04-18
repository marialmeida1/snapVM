# Orchestrator V1 Implementation Roadmap (Deterministic Mock)

This roadmap defines the technical implementation steps for building the V1 Python Orchestrator. 

**CRITICAL SCOPE BOUNDARY FOR V1:** 
This initial implementation is strictly a **Deterministic Mock**. 
*   **NO LLM Integration:** Do not integrate OpenAI, Anthropic, or any LLM APIs.
*   **NO AI Metrics:** Do not attempt to calculate Token Consumption, Context Window Pollution, or Prompt lengths.
*   **Simulated Penalties:** The recovery time cost of an agent repairing state manually is simulated via a deterministically timed "Penalty Routine" (a hardcoded script execution).

The primary goal of V1 is to prove the physical infrastructure mechanics (Firecracker snapshots vs. Git resets) and measure infrastructure latencies (capture time, restore time, storage footprint, and binary state fidelity).

---

## Phase 1: Firecracker Client & Lifecycle Management
**Objective:** Establish programatic control over the Firecracker daemon via its UNIX socket.

*   **Task 1.1: Environment & Dependency Setup**
    *   Initialize a Python virtual environment.
    *   Install required packages: `requests-unixsocket` (or `httpx` with unix socket support) for API communication, and `psycopg2-binary` for database interactions.
*   **Task 1.2: The Firecracker API Wrapper (`firecracker_client.py`)**
    *   Implement a `FirecrackerClient` class.
    *   Write methods to configure the microVM over the UNIX socket (`/machine-config` for vCPU/RAM).
    *   Write methods to attach the boot source (`/boot-source` for `vmlinux`).
    *   Write methods to attach block devices (`/drives` for `rootfs.ext4`).
*   **Task 1.3: Boot & Teardown Execution**
    *   Implement the `InstanceStart` API call (`PUT /actions`).
    *   Implement a teardown method that gracefully halts the microVM or forcefully kills the underlying `firecracker` host process and cleans up the UNIX socket file.

## Phase 2: Host Networking & State-Diff Contract
**Objective:** Enable the Python host to communicate with the PostgreSQL daemon running inside the guest microVM to verify state.

*   **Task 2.1: TAP Interface Provisioning (`network.py`)**
    *   Write a Python utility using `subprocess` to dynamically create (`ip tuntap add mode tap vmtap0`), configure (`ip addr add`), and bring up (`ip link set dev vmtap0 up`) a TAP interface on the bare-metal host.
    *   Implement teardown logic to destroy the TAP interface on exit.
*   **Task 2.2: MicroVM Network Attachment**
    *   Update `firecracker_client.py` to add a `/network-interfaces` API call, binding the guest microVM to the host's `vmtap0`.
*   **Task 2.3: The State-Diff Contract (`contract.py`)**
    *   Implement a `verify_database_integrity(ip_address)` function.
    *   Use `psycopg2` to establish a TCP connection to the guest's PostgreSQL port.
    *   Execute a `SELECT 1 FROM users LIMIT 1;` query.
    *   Return a boolean indicating if the active state (the database table) is healthy and accessible.

## Phase 3: The Snapshot Engine (Core Innovation)
**Objective:** Implement the state-freezing and CoW restoration mechanics.

*   **Task 3.1: Snapshot Capture**
    *   Implement `pause_vm()` (`PUT /machine-config` -> `state: Paused`).
    *   Implement `create_snapshot(mem_path, disk_path)` (`PUT /snapshot/create`). This must serialize the active VM to `memory.gz`, `disk.delta.gz`, and `vmstate` files.
*   **Task 3.2: Snapshot Restoration (Copy-on-Write)**
    *   Implement `load_snapshot(mem_path, disk_path)` (`PUT /snapshot/load`).
    *   Ensure the `resume_vm()` API call is executed.
*   **Task 3.3: Snapshot Storage Telemetry**
    *   Write a utility using `os.stat()` to measure and log the combined physical byte size of the snapshot files (`memory.gz` + `disk.delta.gz` + `vmstate`).

## Phase 4: The Deterministic State Machine & CLI
**Objective:** Wire the components together into a reproducible, CLI-driven experimental pipeline.

*   **Task 4.1: Command Line Interface (`main.py`)**
    *   Implement `argparse` with commands: `setup`, `run --baseline [git|firecracker|all]`, and `clean`.
*   **Task 4.2: Mock Agent Actions**
    *   Write `simulate_agent_success()`: Uses `psycopg2` to execute `CREATE TABLE users (id serial PRIMARY KEY);`.
    *   Write `simulate_agent_failure()`: Uses `psycopg2` to execute `DROP TABLE users;`.
*   **Task 4.3: Baseline A Implementation (Git)**
    *   Implement the Git milestone: `subprocess.run(["git", "init/add/commit"])`.
    *   Implement the Git rollback: `subprocess.run(["git", "reset", "--hard", "HEAD"])`.
    *   Implement the **Penalty Routine**: Since `git reset` will fail the State-Diff contract (DB table is still dropped), execute a timed, hardcoded Python script that re-runs `CREATE TABLE users`. Record this duration as "Simulated Agent Penalty Time".
*   **Task 4.4: Baseline B Implementation (Firecracker)**
    *   Implement the Firecracker milestone: Trigger the Snapshot Capture (Task 3.1).
    *   Implement the Firecracker rollback: Destroy the corrupted VM, trigger Snapshot Restoration (Task 3.2).
    *   Verify the State-Diff Contract passes immediately without a Penalty Routine.
*   **Task 4.5: Telemetry & Reporting Engine**
    *   Wrap milestones and rollbacks in `time.perf_counter()` to capture `State Capture Latency` and `Restoration Latency`.
    *   Output a structured JSON report summarizing the metrics of both isolated trials.
