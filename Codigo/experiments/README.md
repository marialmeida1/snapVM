# Experiments

This directory groups validated experiment implementations and their supporting material.

Each experiment should be self-contained and may include its own:

- `docs/`
- `scripts/`
- source code or benchmark code
- datasets or generated assets when appropriate

General SnapVM documentation should stay in `Codigo/docs/`.

## Current experiments

- `1_benchmark/`: Firecracker benchmark validation with Java workload, scripts, and experiment-specific notes.
- `2_orchestrator_v1/`: Orchestrator validation covering Git vs. Firecracker rollback baselines, setup assets, implementation code, and tests.
