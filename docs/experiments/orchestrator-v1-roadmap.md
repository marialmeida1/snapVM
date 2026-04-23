# Orchestrator V1 Implementation Roadmap (Deterministic Mock)

This roadmap defines the technical implementation steps for building the V1 Python Orchestrator. 

**CRITICAL SCOPE BOUNDARY FOR V1:** 
This initial implementation is strictly a **Deterministic Mock**. 
*   **NO LLM Integration:** Do not integrate OpenAI, Anthropic, or any LLM APIs.
*   **NO AI Metrics:** Do not attempt to calculate Token Consumption, Context Window Pollution, or Prompt lengths.
*   **Simulated Penalties:** The recovery time cost of an agent repairing state manually is simulated via a deterministically timed "Penalty Routine" (a hardcoded script execution).

The primary goal of V1 is to prove the physical infrastructure mechanics (Firecracker snapshots vs. Git resets) and measure infrastructure latencies (capture time, restore time, storage footprint, and binary state fidelity).

---

## Implementation Status

| Phase | Status |
|-------|--------|
| Phase 1: Firecracker Client | ✅ Complete |
| Phase 2: Networking & Contract | ✅ Complete |
| Phase 3: Snapshot Engine | ✅ Complete |
| Phase 4: CLI & Baselines | ✅ Complete |

### Files Implemented
| File | Description |
|------|-------------|
| `src/server.js` | Minimal Express server with `/health` endpoint (queries `SELECT 1 FROM users LIMIT 1`) |
| `src/package.json` | Node.js dependencies: express 4.21.2, pg 8.13.3 |
| `Dockerfile` | Guest rootfs build — Debian bookworm-slim + PostgreSQL 15 + Node.js 20 + npm install |
| `init.sh` | MicroVM init script — mounts, guest network (172.16.0.2/24), starts PostgreSQL + Node.js |
| `requirements.txt` | Python deps: requests-unixsocket 0.4.1, psycopg2-binary 2.9.10 |
| `src/orchestrator/__init__.py` | Package marker |
| `src/orchestrator/firecracker_client.py` | `FirecrackerClient` class — UNIX socket API wrapper (config, boot, drives, network, actions, snapshots) |
| `src/orchestrator/network.py` | TAP interface provisioning — `setup_tap()` / `teardown_tap()` (host 172.16.0.1/24) |
| `src/orchestrator/contract.py` | State-diff contract — HTTP probe to guest `/health` endpoint |
| `src/orchestrator/snapshot.py` | Snapshot engine — `capture()` (pause/snapshot/resume), `restore()` (kill/spawn/load), `storage_footprint()` |
| `src/orchestrator/main.py` | CLI entrypoint — `setup`, `run --baseline [git\|firecracker\|all]`, `clean` |

---

## Phase 1: Firecracker Client & Lifecycle Management ✅
**Objective:** Establish programatic control over the Firecracker daemon via its UNIX socket.

*   **Task 1.1: Environment & Dependency Setup** ✅
    *   `requirements.txt` with `requests-unixsocket==0.4.1` and `psycopg2-binary==2.9.10`.
*   **Task 1.2: The Firecracker API Wrapper (`firecracker_client.py`)** ✅
    *   `FirecrackerClient` class with methods for `/machine-config`, `/boot-source`, `/drives`, `/network-interfaces`.
    *   Uses `requests-unixsocket` for HTTP-over-UNIX-socket communication.
*   **Task 1.3: Boot & Teardown Execution** ✅
    *   `start()` sends `PUT /actions` with `InstanceStart`.
    *   `kill()` sends SIGTERM, waits, falls back to SIGKILL, cleans up socket file.
    *   `spawn()` starts the firecracker process and waits for socket readiness.

## Phase 2: Host Networking & State-Diff Contract ✅
**Objective:** Enable the Python host to communicate with the PostgreSQL daemon running inside the guest microVM to verify state.

*   **Task 2.1: TAP Interface Provisioning (`network.py`)** ✅
    *   `setup_tap()`: recreates `vmtap0`, assigns 172.16.0.1/24, and brings the interface up.
    *   `teardown_tap()`: deletes vmtap0, ignores errors if absent.
*   **Task 2.2: MicroVM Network Attachment** ✅
    *   `set_network()` in `FirecrackerClient` binds guest eth0 to host vmtap0.
*   **Task 2.3: The State-Diff Contract (`contract.py`)** ✅
    *   **Design change:** Uses HTTP probe to `/health` endpoint instead of direct psycopg2 connection. This verifies both server liveness AND database schema integrity in a single call, matching the experiment's goal of testing full-stack state recovery.
    *   `verify_state()` returns `(passed: bool, detail: str)`.

## Phase 3: The Snapshot Engine (Core Innovation) ✅
**Objective:** Implement the state-freezing and CoW restoration mechanics.

*   **Task 3.1: Snapshot Capture** ✅
    *   `client.pause()` sends `PATCH /vm` with `state: Paused`.
    *   `client.create_snapshot()` sends `PUT /snapshot/create` with Full snapshot type.
    *   Files written to `images/snapshots/memory.bin` and `images/snapshots/vmstate`.
*   **Task 3.2: Snapshot Restoration (Copy-on-Write)** ✅
    *   `snapshot.restore()` kills current VM, spawns fresh daemon, calls `load_snapshot()` with `resume_vm: true`.
*   **Task 3.3: Snapshot Storage Telemetry** ✅
    *   `storage_footprint()` sums `os.stat().st_size` for memory.bin + vmstate.

## Phase 4: The Deterministic State Machine & CLI ✅
**Objective:** Wire the components together into a reproducible, CLI-driven experimental pipeline.

*   **Task 4.1: Command Line Interface (`main.py`)** ✅
    *   `argparse` with subcommands: `setup`, `run --baseline [git|firecracker|all]`, `clean`.
*   **Task 4.2: Mock Agent Actions** ✅
    *   `simulate_agent_success()`: `CREATE TABLE IF NOT EXISTS users (id serial PRIMARY KEY)`.
    *   `simulate_agent_failure()`: `DROP TABLE IF EXISTS users`.
*   **Task 4.3: Baseline A — Git** ✅
    *   Git milestone: init `workdir/`, write `migrations/001_create_users.sql`, `git add . && git commit`.
    *   Git rollback: `git reset --hard HEAD`.
    *   Penalty routine: re-runs `CREATE TABLE` via psycopg2, timed separately.
    *   Contract verification at each stage (pre-failure, post-failure, post-reset, post-penalty).
*   **Task 4.4: Baseline B — Firecracker** ✅
    *   Firecracker milestone: `snapshot.capture()` (pause → snapshot → resume).
    *   Firecracker rollback: `snapshot.restore()` (kill → spawn → load_snapshot).
    *   Contract passes immediately post-restore with zero penalty.
*   **Task 4.5: Telemetry & Reporting Engine** ✅
    *   All milestones/rollbacks wrapped in `time.perf_counter()`.
    *   JSON report saved to `results/run_<timestamp>.json`.
    *   Summary table printed to stdout.

---

## Usage

```bash
# 1. Build the guest rootfs
./setup.sh

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Provision host networking (requires sudo)
python -m src.orchestrator.main setup

# 4. Run the experiment
python -m src.orchestrator.main run --baseline all

# 5. Clean up
python -m src.orchestrator.main clean
```

| Phase 5: Live LLM Agent (V2) | ✅ Complete |
| Phase 6: Incremental Optimization (V3) | 🛠️ Planned |
| Phase 7: Agent Autonomy (V4) | 🛠️ Planned |

---

## Phase 6: Incremental State Optimization (V3) 🛠️
**Objective:** Reduce the storage and I/O overhead of snapshots using Firecracker's block-device deltas and dirty-page tracking.

*   **Task 6.1: Diff Snapshot Implementation**
    *   Update `snapshot.py` to support `enable_diff_snapshots=True`.
    *   Compare storage footprint (Full 268MB vs. Incremental ~5-10MB).
*   **Task 6.2: Capture Latency Benchmarking**
    *   Measure the speed increase of capturing only modified memory pages.

## Phase 7: Agentic Autonomy (V4) 🛠️
**Objective:** Shift control of the state lifecycle from the Orchestrator to the Agent.

*   **Task 7.1: Snapshot Tooling**
    *   Expose `capture_snapshot` and `restore_snapshot` as tools in the `AgentLoop`.
*   **Task 7.2: Automatic Health Injection (The "Perception Hook")**
    *   Modify the Orchestrator to automatically prepend the latest `/health` contract result to every message sent to the agent.
    *   Goal: Eliminate the need for the agent to explicitly "ask" if the system is healthy.
*   **Task 7.3: Complex Milestone Navigation**
    *   Test the agent's ability to create "save points" before risky operations and independently decide to rollback when the injected health status turns negative.
