# snapVM

> Last documented update: 2026-03-16  
> Author: Arthur Carvalho

`snapVM` is a research project exploring how Firecracker snapshots can improve agentic code execution workflows.

## Project status

**This is a research project under active development.**  
Expect frequent changes to structure, docs, and experiments.

## What this repository contains

- `docs/firecracker-docs/`: documentation about Firecracker and snapshotting internals.
- `docs/`: project-specific notes and supporting documentation.

## Firecracker helper scripts

- `scripts/setup_firecracker_assets.sh`: builds a reproducible rootfs (via Docker) that embeds the csv benchmark and downloads Firecracker binaries/kernels into `firecracker-assets/`.
- `scripts/run_firecracker_benchmark.sh`: launches Firecracker with the prepared assets and captures console/log output plus run durations into `firecracker-run/`.

## Quick start

Clone Firecracker into the project root:

```bash
make clone-firecracker
```

This will clone:

- `https://github.com/firecracker-microvm/firecracker`

into:

- `./firecracker`
