# snapVM

`snapVM` is a research project exploring how Firecracker snapshots can improve agentic code execution workflows.

## Project status

**This is a research project under active development.**  
Expect frequent changes to structure, docs, and experiments.

## What this repository contains

- `firecracker-docs/`: documentation about Firecracker and snapshotting internals.
- `docs/`: project-specific notes and supporting documentation.
- `examples/`: runnable experiments and proof-of-concept demos.

## Quick start

Clone Firecracker into the project root:

```bash
make clone-firecracker
```

This will clone:

- `https://github.com/firecracker-microvm/firecracker`

into:

- `./firecracker`

## Example: snapshot rollback after code failure

See:

- `examples/firecracker-snapshot-rollback/README.md`

This example boots a microVM, snapshots a working Python API, injects a broken change, detects failure, and rolls back by loading the previous snapshot.
