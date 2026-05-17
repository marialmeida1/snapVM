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
- `experiments/`: isolated experiment code, methodology, setup notes, and result artifacts.

## Current experiment layout

- `experiments/src/`: orchestrator implementation and experiment entrypoints.
- `experiments/src/orchestrator/`: Firecracker client, snapshot engine, network setup, health contract, and V4-V6 experiment modules.
- `experiments/tests/`: automated tests for the orchestrator validation flow.
- `experiments/experiment-results/`: experiment write-ups and exported JSON results.
- `experiments/experiments-specs/`: formal experiment specifications.
- `experiments/environment/`: setup and replication guides for the host environment.
- `experiments/methodology/`: evaluation metrics and trial limitations.
- `experiments/2_orchestrator/`: legacy documentation folder kept for historical context.

## Quick start

Move into the orchestrator experiment directory:

```bash
cd Codigo/experiments
```

Install the Python dependencies declared for the experiments:

```bash
python3 -m pip install -r requirements.txt
```

The main orchestrator code lives under:

- `Codigo/experiments/src/orchestrator/`
