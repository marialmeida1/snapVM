
# ⚙️ cow-snapshot-indexer

> **Orchestrating sub-second Time-Travel Debugging for AI coding agents via Firecracker microVM differential snapshots and Copy-on-Write memory mapping.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Firecracker](https://img.shields.io/badge/Powered%20By-Firecracker-orange)](https://firecracker-microvm.github.io/)
[![Status: Active Research](https://img.shields.io/badge/Status-Active%20Research-success)](#)

Traditional AI coding agents rely on software-layer version control (Git) and container restarts (Docker) to recover from destructive execution errors. This approach is slow, prone to permanent state corruption, and scales linearly in memory, bottlenecking parallel swarm execution.

**`cow-snapshot-indexer`** replaces software-layer version control with continuous, hardware-enforced microVM state capture. By linking an LLM's cognitive logic (Thought/Action) directly to KVM-backed memory diffs, this orchestrator enables instantaneous, deterministic execution replay and sub-linear memory scaling for Monte Carlo Tree Search (MCTS) agent architectures.

---

## 📖 Table of Contents
- [The Paradigm Shift](#-the-paradigm-shift)
- [Architecture & Mechanics](#-architecture--mechanics)
- [Key Features](#-key-features)
- [Getting Started](#-getting-started)
- [The State-Thought Index (API)](#-the-state-thought-index-api)
- [Research Roadmap](#-research-roadmap)
- [Citation](#-citation)

---

## 🚀 The Paradigm Shift

### The Problem: Ephemeral Sandboxing
When an autonomous agent executes a destructive command (e.g., `rm -rf /usr/lib` or installing a corrupted kernel module), `git reset` cannot restore the operating system or the background runtime processes. The agent becomes trapped in an infinite error loop within a corrupted environment.

### The Solution: Hypervisor-Level Rollbacks
This project introduces **Unified State-Thought Indexing**. Every time the agent makes a decision, the orchestrator pauses the Firecracker microVM, captures the dirtied memory pages (differential snapshot), and indexes the physical file path to the LLM's context window. 

If the agent fails, it doesn't write un-do commands. The orchestrator physically "time-travels" the machine back to the exact millisecond before the mistake, restoring the full OS, filesystem, and physical RAM state in **<150ms**.

---

## 🧠 Architecture & Mechanics

```mermaid
graph TD
    A[LLM Agent / Brain] -->|Thought & Command| B(State-Thought Indexer)
    B -->|1. Pause VM| C{Firecracker API}
    B -->|2. Diff Snapshot| C
    C -->|Extract Dirty Pages| D[(memory_diff_X.snap)]
    C -->|Extract vCPU State| E[(state_X.snap)]
    B -->|3. Map to Token ID| F[(Vector/JSON Index)]
    B -->|4. Execute Command| G[Guest MicroVM]
    G -->|If Fatal Error| B
    B -->|5. Instant Rollback| C

---

# Contributors

[![Alice](https://img.shields.io/badge/GitHub-Alice-1f6feb?style=for-the-badge&logo=github)](https://github.com/alicesalim)

[![Arthur](https://img.shields.io/badge/GitHub-Arthur-0e8a16?style=for-the-badge&logo=github)](https://github.com/ArthurCRodrigues)

[![Débora](https://img.shields.io/badge/GitHub-Débora-f9a825?style=for-the-badge&logo=github)](https://github.com/DebLuiza)

[![Gustavo](https://img.shields.io/badge/GitHub-Gustavo-d73a49?style=for-the-badge&logo=github)](https://github.com/GhrCastro)

[![Mariana](https://img.shields.io/badge/GitHub-Mariana-6f42c1?style=for-the-badge&logo=github)](https://github.com/marialmeida1)

