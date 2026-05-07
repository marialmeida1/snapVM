# SnapVM — Project Overview

## Identity

SnapVM is a **research project** (academic/experimental) exploring Firecracker microVM snapshots as a recovery mechanism for stateful environments in AI agent workflows. Author: Arthur Carvalho Rodrigues.

Repository: `ArthurCRodrigues/snapVM` on GitHub.

## Core Thesis

Traditional Git-based rollback cannot restore **stateful environments** (running databases, active processes, memory). SnapVM uses Firecracker's full-state snapshots (memory + CPU + disk) to provide instant, complete environment recovery — eliminating the "hallucination retry loop" where AI agents waste tokens trying to manually repair corrupted state.

## Architecture (ReSnapAct)

The system follows a layered architecture:

```
┌─────────────────────────────────────────┐
│  AI Agent (GPT-4o via OpenAI SDK)       │  ← Reasons + Acts via tools
├─────────────────────────────────────────┤
│  Orchestrator (Python)                  │  ← Controls lifecycle, health, snapshots
├─────────────────────────────────────────┤
│  Firecracker microVM                    │  ← Isolated execution environment
│  ┌─────────────┐  ┌──────────────────┐  │
│  │ Express API │  │ PostgreSQL 15    │  │
│  │ (Node.js)   │  │ (stateful DB)    │  │
│  └─────────────┘  └──────────────────┘  │
└─────────────────────────────────────────┘
```

## Key Roles

- **Orchestrator**: Deterministic controller. Manages VM lifecycle, health checks, snapshot capture/restore, Git fallback, logging. The agent NEVER directly controls snapshots.
- **Agent**: AI that reasons about failures and calls tools (`execute_bash`, `check_health`, `restore_last_snapshot`). Cannot access host or infrastructure directly.
- **Health Contract**: `/health` endpoint that queries `SELECT 1 FROM users LIMIT 1` — validates both API liveness and DB schema integrity.
- **Perception Hook**: Short structured message informing the agent of state changes (health status, rollback availability).

## Current Stage

- Sprint 1 (Research & Validation): ✅ Complete
- Experiment 1 (Firecracker Benchmark): ✅ Complete — validated VM boot + workload execution
- Experiment 2 (Orchestrator V1-V3): ✅ Complete — proved snapshot superiority over Git for stateful recovery
  - V1: Deterministic mock baselines
  - V2: Live LLM agent integration (80.8% token reduction with snapshots)
  - V3: Incremental/Diff snapshots (36.5% storage reduction)
- Experiment 4 (Agent Autonomy / V4): 🛠️ Planned — agent controls its own snapshots
- Sprint 2 (SnapVM CLI): Planned
- Sprint 3 (Consolidation): Planned

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Orchestrator | Python 3.x (requests-unixsocket, psycopg2, openai, tiktoken) |
| Guest App | Node.js 20 + Express 4.21 + pg 8.13 |
| Database | PostgreSQL 15 |
| VM | Firecracker v1.7.0 microVM |
| Guest OS | Debian bookworm-slim |
| Host | Bare-metal Linux with KVM |
| Networking | TAP interface (host 172.16.0.1/24, guest 172.16.0.2) |

## "Git Rollback" — What It Actually Means

"Git rollback" in this project does NOT mean just running `git reset`. It refers to the **full agent-driven manual recovery loop**: the agent notices the environment is broken, reasons about the failure, and uses standard tools (git commands, SQL queries, bash, migrations) to diagnose and fix the problem itself. It represents how AI agents recover today without snapshot infrastructure.

- It's the **control group** in experiments — measuring the cost (tokens, time, context pollution) of manual agent recovery.
- In production workflows, it remains the **fallback** when snapshots aren't available or don't apply (e.g., pure code changes with no stateful corruption).
- In experiments, the "penalty routine" captures this: after `git reset` fails the health check (because Git can't restore DB state), the agent must spend additional tokens to re-create the table manually.

## Key Results (Experiment 2 — 20 iterations)

| Metric | Git Baseline | Firecracker | Winner |
|--------|-------------|-------------|--------|
| Restore Latency | 6.572s | 0.184s | Firecracker (35x faster) |
| Token Consumption | 2860 | 549 | Firecracker (5.2x lower) |
| Context Pollution | 456 tokens | 166 tokens | Firecracker (2.7x lower) |
| Storage | 27 KB | 268 MB | Git (trade-off) |

## Language

Project documentation is in **English**. The root `context-and-rules.md` is the authoritative business rules document.
