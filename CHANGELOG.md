# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, adapted to the current research-oriented stage of the project.

## [0.1.0] - 2026-05-17

### Added

- Initial public research prototype of SnapVM focused on Firecracker microVM snapshot orchestration.
- Python-based experiment orchestrator covering Firecracker lifecycle management, snapshot capture and restore flows, guest networking, and contract-based state validation.
- Comparative baseline experiments for Git rollback versus Firecracker snapshot restoration in stateful environments.
- Advanced experiment suites for autonomous agent recovery, complex failures, forced restore flows, agent-driven checkpoints, and speculative branching workflows.
- Guest workload components for a Node.js API backed by PostgreSQL to validate stateful rollback behavior.
- Environment setup and replication guides for rebuilding the Firecracker-based experiment infrastructure.
- Consolidated experiment reports, methodology documentation, and exported JSON results for reproducibility and analysis.
- Initial unit test coverage for snapshot handling, orchestrator cleanup behavior, and Firecracker client process management.
- Project metadata and academic support files including `LICENSE`, `CITATION.cff`, and top-level research documentation.

### Highlights

- Establishes SnapVM as an experimental platform for evaluating infrastructure-level rollback instead of file-only recovery.
- Validates recovery scenarios where full machine state matters, including database state, processes, sockets, and execution context.
- Demonstrates measurable tradeoffs between Git-based recovery and snapshot-based recovery, including latency, storage overhead, and agent context impact.

### Known Limitations

- The repository currently exposes a research orchestrator and experiment framework, not a stabilized end-user `snapvm` product CLI.
- Full experiment execution depends on a Linux host with KVM access, Firecracker, guest kernel assets, and root filesystem preparation.
- Some experiment paths depend on external credentials and services, including an OpenAI API key for live agent-driven runs.
- Repository contents currently include generated Python bytecode under `__pycache__/`, which is not part of a polished distribution package.

### Status

- Release maturity: experimental
- Intended audience: research, academic validation, and prototype evaluation
- Production readiness: not intended for production use
