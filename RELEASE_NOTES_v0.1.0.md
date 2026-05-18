# SnapVM v0.1.0

## First Research Prototype

SnapVM v0.1.0 is the first public release of the project and marks the transition from concept documentation into a functional research prototype.

This release packages the current state of SnapVM as an experimental platform for evaluating whether Firecracker microVM snapshots can serve as a practical rollback and recovery primitive for stateful execution environments. The focus is not yet a production-ready end-user CLI, but a validated experimental stack composed of orchestrator code, experiment scenarios, replication guides, and documented results.

## What this release includes

This version includes a Python-based orchestration layer that manages Firecracker microVM execution, lifecycle control, networking, snapshot capture and restore operations, and contract-based health validation. It also includes the guest workload used in the experiments, based on a Node.js API and PostgreSQL stateful service model.

The repository now contains a complete experimental track with:

- baseline comparisons between Git rollback and Firecracker snapshot restoration
- stateful recovery validations using contract checks
- autonomous recovery scenarios for agent-managed environments
- forced snapshot restore comparisons
- agent-driven checkpoint experiments
- speculative branching and recovery experiments
- setup, replication, and methodology documentation
- experiment reports and exported JSON result files
- unit tests for core orchestrator and snapshot behaviors

## Why this release matters

Traditional rollback methods such as Git reset can restore files, but they do not restore the full runtime state of an environment. SnapVM investigates a different model: restoring the machine itself, including memory-adjacent execution state, running services, and database state, through Firecracker snapshots.

This release establishes the first integrated prototype showing that this approach is viable as a research direction and can be measured across multiple experimental conditions.

## Main technical highlights

### Firecracker orchestration foundation

The project now includes the core building blocks needed to boot microVMs, configure guest execution, capture snapshots, restore previous machine states, and compare this flow against conventional Git-based rollback.

### Stateful recovery validation

Recovery is evaluated using explicit contract checks instead of file diffs alone. This allows the experiments to measure whether an environment is truly healthy after rollback, not merely whether the repository contents were reverted.

### Agent-oriented experiment design

The prototype extends beyond infrastructure-only measurements and explores how physical state restoration affects autonomous or semi-autonomous agents, including impacts on recovery latency, token usage, tool calls, and context pollution.

### Reproducibility support

This release includes replication guidance, environment setup notes, methodology documentation, and experiment result summaries so that the research path can be inspected and reproduced more easily.

## Included experiment scope

- Experiment 1: baseline benchmarks
- Experiment 2: live LLM agent recovery
- Experiment 3: incremental snapshot optimization
- Experiment 4: autonomous agent recovery
- Experiment 4.1: complex stateful failures
- Experiment 4.2: forced snapshot recovery
- Experiment 5: agent-driven checkpoints
- Experiment 6: exploration branching

## Selected results summary

Across the documented experiments, the current prototype shows strong recovery-speed and agent-efficiency advantages for snapshot-based restoration in scenarios where runtime state matters, while also exposing the expected storage overhead of full-machine snapshots. The current results indicate that the tradeoff is meaningful and worthy of continued development, particularly for agentic workflows that suffer from expensive recovery loops and context pollution after partial failures.

## Limitations of v0.1.0

- This is an experimental research prototype, not a stable production release.
- The `Codigo/snapvm/` module is still reserved for future product-facing implementation work.
- Running the full stack requires a suitable Linux environment with KVM, Firecracker, kernel assets, and root filesystem preparation.
- Some live experiments require external API credentials.
- Packaging, distribution ergonomics, and end-user CLI polish are not yet complete.

## Recommended use of this release

This release is best suited for:

- academic demonstration
- research replication
- architecture review
- experimentation with stateful rollback concepts
- groundwork for future SnapVM CLI/product development

It is not intended for production deployment or general-purpose operational use.

## Acknowledgments

This release reflects the first consolidated milestone of the SnapVM research effort, bringing together documentation, infrastructure experiments, and agent-oriented recovery validation into a single repository state.
