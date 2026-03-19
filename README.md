
![SnapVM screenshot](Divulgacao/Apresentacao/img/snapvm-logo.png)

# SnapVM

SnapVM is an experimental project that explores the use of **Firecracker microVM snapshots** to build fast, recoverable execution environments.

The project investigates how snapshot-based virtual machines can be used to create environments that can be saved, restored, and cloned quickly, enabling safer experimentation and faster recovery from failures.

SnapVM is being developed as a **command-line tool (CLI)** that orchestrates Firecracker microVMs and manages their execution state through snapshots.

---

# Motivation

Modern systems that execute code automatically, such as AI coding agents, testing pipelines, or experimental runtime environments, require isolated environments where code can run safely.

Current approaches often rely on container-based environments. While effective, these environments typically require rebuilding or reconfiguring the system when failures occur.

SnapVM explores a different approach by using **virtual machine snapshots as the primary mechanism for environment management**.

With this approach it becomes possible to:

- restore environments almost instantly
- recover from failures without rebuilding the system
- safely experiment with destructive operations
- clone environments for parallel execution

---

# Project Goals

The main objective of SnapVM is to validate the feasibility of snapshot-based execution environments.

The project aims to demonstrate that microVM snapshots can support workflows where environments can be:

- created
- saved
- restored
- reused
- recovered quickly after failure

The current implementation focuses on building a minimal system capable of managing these operations.

---

# Repository Organization

- **Codigo/**: main implementation, benchmarks, scripts, and technical docs.
- **Artefatos/**: project artifacts and deliverables.
- **Documentacao/**: complementary project documentation.
- **Divulgacao/**: presentation and communication materials.
- Root files include project metadata such as **README**, **LICENSE**, and **CITATION.cff**.

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

# Contributors

[![Alice](https://img.shields.io/badge/GitHub-Alice-1f6feb?style=for-the-badge&logo=github)](https://github.com/alicesalim)

[![Arthur](https://img.shields.io/badge/GitHub-Arthur-0e8a16?style=for-the-badge&logo=github)](https://github.com/ArthurCRodrigues)

[![Debora](https://img.shields.io/badge/GitHub-Debora-f9a825?style=for-the-badge&logo=github)](https://github.com/DebLuiza)

[![Gustavo](https://img.shields.io/badge/GitHub-Gustavo-d73a49?style=for-the-badge&logo=github)](https://github.com/GhrCastro)

[![Mariana](https://img.shields.io/badge/GitHub-Mariana-6f42c1?style=for-the-badge&logo=github)](https://github.com/marialmeid)
