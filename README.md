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
  - [Experiment 1: Rollback Mechanisms in Stateful Workflows](./docs/experiments/01-baseline-benchmarks.md)
- [**Methodology**](./docs/methodology/): How we measure success, failure, and efficiency.
  - [Evaluation Metrics](./docs/methodology/evaluation-metrics.md)
- [**Environment Setup**](./docs/environment/): Instructions for provisioning the host and guest systems.
  - [Bare-Metal Architecture & Setup Guide](./docs/environment/setup-guide.md)

## Next Steps

Our immediate focus is developing the Minimum Viable Prototype (MVP):
1. Acquiring/compiling the `vmlinux` kernel.
2. Constructing the `rootfs.ext4` containing Node.js and PostgreSQL.
3. Writing the Python orchestrator to manage the Firecracker API and TAP network interfaces.
