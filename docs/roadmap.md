# SnapVM Roadmap

> Last documented update: 2026-03-19  
> Author: Mariana Almeida

This document outlines the development roadmap for the SnapVM project.

SnapVM is an experimental project that explores the use of Firecracker microVM snapshots to build fast, recoverable execution environments.

The development of the project is organized into three main sprints, each focusing on a specific stage of the system.

---

# Sprint 1 — Research and Concept Validation

## Goal

Establish the conceptual foundation of SnapVM and validate the main ideas through small experiments and documentation.

This stage focuses on understanding the problem space and confirming that the underlying technologies support the intended workflow.

## Main Activities

- Define the project scope and objectives
- Document the core ideas behind SnapVM
- Study Firecracker microVM architecture
- Identify the key system concepts
- Run small experiments to validate assumptions

## Deliverables

Documentation:

- `docs/overview.md`
- `docs/concepts.md`

Experiments:

- `docs/experiments/first-snapshot.md`
- `docs/experiments/environment-rollback.md`
- `docs/experiments/parallel-vm.md`

## Expected Outcome

A clear conceptual understanding of the system and confirmation that Firecracker snapshots can support the core ideas of SnapVM.

---

# Sprint 2 — SnapVM CLI Implementation

## Goal

Develop the first functional implementation of SnapVM as a command-line tool capable of managing Firecracker microVM environments and snapshots.

This stage transforms the experimental ideas into a working prototype.

## Main Activities

- Design the SnapVM CLI interface
- Implement integration with the Firecracker API
- Implement VM lifecycle management
- Implement snapshot creation and restoration
- Provide a simple command interface for interacting with microVM environments

## Example CLI Commands

`snapvm start`
`snapvm stop`
`snapvm snapshot`
`snapvm restore`
`snapvm status`


## Expected Outcome

A working SnapVM prototype capable of:

- starting microVM environments
- creating VM snapshots
- restoring environments from snapshots
- demonstrating fast rollback capabilities

---

# Sprint 3 — System Consolidation

## Goal

Refine the SnapVM prototype, complete missing functionality, and finalize the project documentation.

This stage focuses on stabilizing the system and demonstrating the results of the project.

## Main Activities

- Improve CLI usability
- Refine snapshot workflows
- Complete missing functionality
- Run additional validation experiments
- Finalize project documentation

## Deliverables

- Stable SnapVM CLI prototype
- Completed documentation
- Documented experiment results

## Expected Outcome

A functional experimental system that demonstrates the feasibility of snapshot-based execution environments.

---

# Future Directions

Possible future extensions of SnapVM may include:

- automated snapshot orchestration
- integration with AI coding agents
- support for parallel VM execution
- distributed execution environments

These directions depend on the results and stability of the initial prototype.
