# SnapVM — Codebase Map

## Repository Root Structure

```
snapVM/
├── context-and-rules.md          # Authoritative business rules (55 rules, RN-001 to RN-055)
├── README.md                     # Project overview (academic context)
├── CITATION.cff                  # Citation metadata
├── LICENSE                       # Open source license
├── Artefatos/                    # Academic artifacts (presentations, deliverables)
├── Divulgacao/                   # Dissemination materials (presentations, video)
├── Documentacao/                 # Academic documentation
├── Codigo/                       # ALL source code and experiments live here
│   ├── docs/                     # Shared project documentation
│   ├── experiments/              # Isolated experiments (each self-contained)
│   └── snapvm/                   # Reserved for future SnapVM CLI module
└── .kiro/                        # Agentic context (steerings, skills)
```

## Codigo/docs/ — Shared Documentation

| File | Purpose |
|------|---------|
| `overview.md` | What SnapVM is, the problem, the core idea |
| `concepts.md` | Background concepts (ReAct, microVMs, Firecracker, CoW, snapshots) |
| `roadmap.md` | Sprint plan (Sprint 1: Research, Sprint 2: CLI, Sprint 3: Consolidation) |
| `firecracker-docs/snapshot-implementation.md` | Deep dive into Firecracker snapshot internals (API → VMM → persist) |
| `firecracker-docs/snapshot-management.md` | Operational runbook for snapshot create/restore/rotate |

## Codigo/experiments/1_benchmark/ — Experiment 1: Firecracker Benchmark

Validates that workloads can run inside Firecracker. Uses a Java CSV analytics benchmark.

| Path | Purpose |
|------|---------|
| `benchmark/` | Java Maven project (csv-analytics-benchmark) |
| `scripts/setup_firecracker_assets.sh` | Builds rootfs + downloads kernel/binaries |
| `scripts/run_firecracker_benchmark.sh` | Boots Firecracker, runs benchmark, captures output |
| `docs/1.firecracker-benchmark.md` | Results: host ~1s vs Firecracker ~8.5s lifecycle |
| `Makefile` | `make clone-firecracker` helper |

## Codigo/experiments/2_orchestrator_v1/ — Experiment 2: Orchestrator (MAIN EXPERIMENT)

The core implementation. Python orchestrator comparing Git vs Firecracker rollback.

### Source Code (`src/orchestrator/`)

| File | Purpose |
|------|---------|
| `main.py` | CLI entrypoint + experiment logic. Commands: `setup`, `run`, `diff-test`, `clean`. Contains `run_git_baseline()`, `run_firecracker_baseline()`, `run_diff_test()` |
| `firecracker_client.py` | `FirecrackerClient` class — UNIX socket API wrapper. Methods: `spawn()`, `kill()`, `set_machine_config()`, `set_boot_source()`, `set_rootfs()`, `set_network()`, `start()`, `pause()`, `resume()`, `create_snapshot()`, `load_snapshot()` |
| `snapshot.py` | Snapshot engine — `capture()` (pause→snapshot→resume), `restore()` (kill→spawn→load), `storage_footprint()` |
| `contract.py` | Health contract — HTTP probe to `/health` endpoint, returns `(passed, detail)` |
| `network.py` | TAP interface provisioning — `setup_tap()`, `teardown_tap()`. Host: 172.16.0.1/24, Guest: 172.16.0.2 |
| `agent.py` | `AgentLoop` class — OpenAI SDK integration with tools (`query_db`, `execute_bash`, `check_health`). Tracks token usage and context pollution |

### Guest Application (`src/`)

| File | Purpose |
|------|---------|
| `server.js` | Express API: `/health` (SELECT 1 FROM users), `/exec` (run bash commands) |
| `package.json` | Dependencies: express 4.21.2, pg 8.13.3 |

### Infrastructure

| File | Purpose |
|------|---------|
| `Dockerfile` | Guest rootfs: Debian + PostgreSQL 15 + Node.js 20 |
| `init.sh` | MicroVM init: mounts, networking (172.16.0.2), starts PostgreSQL + Node.js |
| `setup.sh` | Downloads Firecracker v1.7.0, kernel, builds rootfs.ext4 |
| `requirements.txt` | Python deps: requests, requests-unixsocket, psycopg2-binary, openai, tiktoken, python-dotenv |

### Tests

| File | Purpose |
|------|---------|
| `tests/test_orchestrator_v1.py` | Unit tests: snapshot resume-on-failure, artifact validation, PID safety, git workdir, VM cleanup |

### Documentation (`docs/`)

| File | Purpose |
|------|---------|
| `experiments/orchestrator-v1-roadmap.md` | Implementation phases (1-7), status, usage instructions |
| `experiments/01-baseline-benchmarks.md` | V1 mock results: Git stateful flaw proven |
| `experiments/02-llm-agent-recovery.md` | V2 live results: 5.2x token reduction, 35x faster restore |
| `experiments/03-incremental-optimization.md` | V3 diff results: 36.5% storage reduction |
| `methodology/evaluation-metrics.md` | Metrics definitions (capture latency, restore latency, token consumption, context pollution) |
| `methodology/trial-setup-and-limitations.md` | Trial methodology, fairness analysis, known limitations |
| `environment/setup-guide.md` | Infrastructure requirements (KVM, TAP, kernel, rootfs) |
| `environment/replication-guide.md` | Step-by-step replication: install Firecracker, build rootfs, configure networking |

## Running the Orchestrator

```bash
cd Codigo/experiments/2_orchestrator_v1

# 1. Build guest rootfs
./setup.sh

# 2. Install Python deps
pip install -r requirements.txt

# 3. Provision networking (requires sudo, Linux only)
python -m src.orchestrator.main setup

# 4. Run experiment
python -m src.orchestrator.main run --baseline all --mode mock    # deterministic
python -m src.orchestrator.main run --baseline all --mode live    # with LLM agent

# 5. Run diff snapshot test
python -m src.orchestrator.main diff-test

# 6. Cleanup
python -m src.orchestrator.main clean
```

## Key Design Decisions

- Health contract uses HTTP probe (not direct DB) to test full-stack state
- Snapshot restore kills VM + spawns fresh process + loads snapshot (CoW)
- Git baseline always fails post-reset health check (proves stateful flaw)
- Agent tools are generic (`execute_bash`, `check_health`, `restore_last_snapshot`) — not DB-specific
- Only one healthy snapshot maintained at a time (`last_known_good`)
