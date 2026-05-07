# snapVM

> Last documented update: 2026-03-16  
> Author: Arthur Carvalho

`snapVM` is a research project exploring how Firecracker snapshots can improve agentic code execution workflows.

## Project status

**This is a research project under active development.**  
Expect frequent changes to structure, docs, and experiments.

## What this repository contains

- `snapvm/`: reserved module for the future main SnapVM implementation.
- `docs/`: general project documentation shared across the repository.
- `experiments/`: isolated experiments, each with its own docs, scripts, and support files.

## Current experiment layout

- `experiments/1_benchmark/`: Firecracker benchmark experiment.
- `experiments/1_benchmark/benchmark/`: Java benchmark project used in the experiment.
- `experiments/1_benchmark/docs/`: experiment report and Firecracker-specific notes.
- `experiments/1_benchmark/scripts/`: experiment automation scripts.
- `experiments/2_orchestrator_v1/`: validation of the Python orchestrator workflow and rollback baselines.
- `experiments/2_orchestrator_v1/docs/`: experiment documentation, methodology, and setup guides.
- `experiments/2_orchestrator_v1/src/`: implementation code for the orchestrator validation.
- `experiments/2_orchestrator_v1/tests/`: tests for the orchestrator validation.

## Quick start

Move into the benchmark experiment directory:

```bash
cd Codigo/experiments/1_benchmark
make clone-firecracker
```

This will clone:

- `https://github.com/firecracker-microvm/firecracker`

into:

- `./firecracker`
