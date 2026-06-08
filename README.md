![SnapVM screenshot](Divulgacao/Apresentacao/img/snapvm-logo.png)

# SnapVM

SnapVM is an experimental project that explores the use of **Firecracker microVM snapshots** to build fast, recoverable execution environments.

The project investigates how snapshot-based virtual machines can be used to create environments that can be saved, restored, and cloned quickly, enabling safer experimentation and faster recovery from failures.

At its core, SnapVM studies **stateful AI agent recovery**: how to restore not only source files, but the full execution state of a system, including memory, background processes, sockets, and database state. This is especially relevant for AI coding agents, automated testing pipelines, and other long-running agentic workflows where traditional file-only rollback mechanisms are insufficient.

SnapVM is being developed as a **command-line tool (CLI)** and research platform for orchestrating Firecracker microVMs, validating rollback strategies, and comparing infrastructure-level recovery against conventional Git-based baselines.

---

# Motivation

Modern systems that execute code automatically, such as AI coding agents, testing pipelines, or experimental runtime environments, require isolated environments where code can run safely.

Current approaches often rely on container-based environments or stateless version control. While effective in many situations, these approaches typically require rebuilding or reconfiguring the system when failures occur, and they do not fully restore corrupted execution state.

SnapVM explores a different approach by using **virtual machine snapshots as the primary mechanism for environment management**.

With this approach it becomes possible to:

- restore environments almost instantly
- recover from failures without rebuilding the system
- safely experiment with destructive operations
- clone environments for parallel execution
- avoid expensive recovery loops caused by partially broken runtime state

---

# Project Goals

The main objective of SnapVM is to validate the feasibility of snapshot-based execution environments.

The project aims to demonstrate that microVM snapshots can support workflows where environments can be:

- created
- saved
- restored
- reused
- recovered quickly after failure

The current implementation focuses on building minimal but realistic validations around these operations, including experiments that compare **Git rollback** with **Firecracker snapshot restoration** in stateful environments.

---

# System Architecture

The current research directions include a bare-metal host orchestrating isolated Firecracker guests and validating recovery through reproducible experiments.

1. **Host Orchestration Layer**
   Manages experiment control flow, recovery strategy selection, contract validation, and experiment telemetry.

2. **Firecracker MicroVM Guest**
   Runs the isolated workload being evaluated, including stateful services and benchmark applications.

3. **State-Diff Validation Contract**
   Confirms whether the environment is truly healthy after rollback, not only whether files were reverted.

4. **Experiment-Specific Workloads**
   Includes both deterministic benchmarks and orchestrated rollback scenarios for stateful services.

---

# Repository Organization

- **Codigo/**: source workspace for the SnapVM project, split between the future `snapvm` module, general documentation, and validated experiments.
- **Codigo/snapvm/**: reserved module for the future main SnapVM implementation.
- **Codigo/docs/**: general project documentation, concepts, and roadmap.
- **Codigo/experiments/**: formal experiment implementations and their supporting materials.
- **Artefatos/**: project artifacts and deliverables.
- **Documentacao/**: complementary project documentation.
- **Divulgacao/**: presentation and communication materials.
- Root files include project metadata such as **README**, **LICENSE**, and **CITATION.cff**.

---

# Experiment Structure

The repository currently separates validations into self-contained experiment areas:

- **`Codigo/experiments/src/`**: Python orchestrator implementation, including the Firecracker client, snapshot engine, contract validation, and experiment entrypoints.
- **`Codigo/experiments/tests/`**: automated tests for the orchestrator and snapshot lifecycle.
- **`Codigo/experiments/experiments-specs/`**: specifications for experiment phases such as autonomous recovery, forced snapshots, checkpoints, and exploration branching.
- **`Codigo/experiments/experiment-results/`**: experiment reports and exported JSON result files.
- **`Codigo/experiments/environment/`**: environment setup and replication guides for the Firecracker-based experiments.
- **`Codigo/experiments/methodology/`**: evaluation metrics, trial design, and limitations documentation.
- **`Codigo/experiments/2_orchestrator/`**: legacy documentation folder preserved for the orchestrator experiment narrative.

This structure keeps experiment-specific assets isolated from the future `snapvm` product module.

---

# Implementation Status

| Phase | Status |
|-------|--------|
| Phase 1: Firecracker Client | Complete |
| Phase 2: Networking & Contract | Complete |
| Phase 3: Snapshot Engine | Complete |
| Phase 4: CLI & Baselines (V1 Mock) | Complete |
| Phase 5: Live LLM Agent (V2) | In research / merge |

Current validated directions include:

- deterministic rollback baselines comparing Git and Firecracker
- benchmark execution inside Firecracker microVMs
- stateful recovery validation through contract checks
- experiment scaffolding for future AI-agent-driven recovery workflows

---

# Project Roadmap

The development of SnapVM is organized into three main phases:

### Sprint 1 - Research and Documentation

Define the conceptual foundation of the project and validate core ideas through small experiments.

### Sprint 2 - SnapVM CLI Implementation

Develop the first functional version of SnapVM capable of managing microVM environments and snapshots.

### Sprint 3 - System Consolidation

Refine the prototype, complete missing functionality, and finalize the project documentation.

---

# Where To Look

- General concepts and roadmap: `Codigo/docs/`
- Orchestrator implementation and CLI experiments: `Codigo/experiments/src/`
- Experiment reports and exported results: `Codigo/experiments/experiment-results/`
- Replication, setup, and methodology: `Codigo/experiments/environment/` and `Codigo/experiments/methodology/`

---

# Contributors

[![Arthur](https://img.shields.io/badge/GitHub-Arthur-0e8a16?style=for-the-badge&logo=github)](https://github.com/ArthurCRodrigues)

[![Debora](https://img.shields.io/badge/GitHub-Debora-f9a825?style=for-the-badge&logo=github)](https://github.com/DebLuiza)

[![Gustavo](https://img.shields.io/badge/GitHub-Gustavo-d73a49?style=for-the-badge&logo=github)](https://github.com/GhrCastro)

[![Mariana](https://img.shields.io/badge/GitHub-Mariana-6f42c1?style=for-the-badge&logo=github)](https://github.com/marialmeida1)

---

# Advisors

- Matheus Alcântara — Professor, PUC Minas
- Felipe Domingos — Professor, PUC Minas

---

# Citation

If you use SnapVM in academic work or derivative research, cite the project using the metadata in `CITATION.cff`.
