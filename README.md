# Stateful AI Agent Recovery Research: Firecracker vs. Git Baselines

## Overview

As autonomous artificial intelligence (AI) agents are increasingly deployed in stateful, continuous software engineering workflows, the necessity for robust failure recovery has become a critical bottleneck. Traditional error handling relies on stateless version control (like Git), which can revert code files but fails to repair corrupted background processes, active network sockets, or destroyed database schemas.

This project evaluates a paradigm shift in multi-agent orchestration: **infrastructure-level state recovery**. We propose that utilizing Amazon Firecracker's microVM snapshots paired with a state-diff evaluation contract is theoretically superior to standard version control methods. 

By capturing the complete execution reality—including active memory, background processes, and database locks—and utilizing Copy-on-Write (CoW) anonymous memory mapping, a Firecracker microVM can be restored to a precise snapshot point in as little as 5 milliseconds. This bypasses OS cold-start latency, prevents LLM context exhaustion, and avoids expensive "hallucinated retry loops."

## System Architecture

The project is built on a bare-metal Linux host with hardware virtualization (KVM) enabled. The architecture consists of:

1. **Python Orchestration Control Plane (Host):**
   - Manages the AI agent's prompt history and LLM interactions.
   - Triggers Firecracker API calls for snapshotting and restoring microVMs.
   - Executes deterministic Failure Injection.
   - Runs State-Diff Contracts (HTTP/Network probes) against the microVM to verify state integrity post-rollback.

2. **Firecracker MicroVM (Guest Environment):**
   - **Kernel:** Uncompressed Linux kernel (`vmlinux`) optimized for rapid boot.
   - **Rootfs:** Minimal `ext4` filesystem.
   - **Stack:** Node.js API server connected to a persistent **PostgreSQL** database daemon. This guarantees a highly stateful environment (active TCP connection pools, shared memory buffers, background writers) that standard Git rollbacks cannot properly restore.

## Documentation Structure

Detailed documentation regarding the project's methodologies, experiments, and environment setup can be found in the `docs/` directory:

- [**Experiments**](./docs/experiments/): Definitions of our deterministic workflows and baseline comparisons.
  - [Experiment 1: Rollback Mechanisms (Mock)](./docs/experiments/01-baseline-benchmarks.md)
  - [Experiment 2: LLM Agent Recovery & Token Efficiency (Live)](./docs/experiments/02-llm-agent-recovery.md)
  - [Experiment 3: Incremental State Optimization (V3)](./docs/experiments/01-baseline-benchmarks.md) — *Planned*
  - [Experiment 4: Agent Autonomy & State Control (V4)](./docs/experiments/01-baseline-benchmarks.md) — *Planned*
- [**Methodology**](./docs/methodology/): How we measure success, failure, and efficiency.
  - [Evaluation Metrics](./docs/methodology/evaluation-metrics.md)
- [**Environment Setup**](./docs/environment/): Instructions for provisioning the host and guest systems.
  - [Bare-Metal Architecture & Setup Guide](./docs/environment/setup-guide.md)

## Implementation Status

| Phase | Status |
|-------|--------|
| Phase 1: Firecracker Client | ✅ Complete |
| Phase 2: Networking & Contract | ✅ Complete |
| Phase 3: Snapshot Engine | ✅ Complete |
| Phase 4: CLI & Baselines (V1 Mock) | ✅ Complete |
| Phase 5: Live LLM Agent (V2) | ✅ Complete |

### V2 Features
*   **Live LLM Integration:** Uses OpenAI SDK with custom ReAct loop.
*   **AI-Specific Metrics:** Tracks Token Consumption and Context Window Pollution.
*   **Infrastructure Optimization:** Firecracker Native Diffs (block device deltas).
*   **Statistical Runs:** Support for `--iterations N`.

## Usage

```bash
# 1. Build the guest rootfs
./setup.sh

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Provision host networking (requires sudo)
python -m src.orchestrator.main setup

# 4. Run the experiment (Mock Mode)
python -m src.orchestrator.main run --baseline all --mode mock

# 5. Run the experiment (Live LLM Mode)
export OPENAI_API_KEY="your-key-here"
python -m src.orchestrator.main run --baseline all --mode live --iterations 3
```
