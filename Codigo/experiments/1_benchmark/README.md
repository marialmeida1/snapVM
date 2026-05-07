# Experiment 1: Firecracker Benchmark

This experiment validates the execution of `csv-analytics-benchmark` inside a Firecracker microVM.

## Structure

- `benchmark/`: Java benchmark project and its own benchmark-specific documentation.
- `docs/`: experiment report and Firecracker research notes used in this experiment.
- `scripts/`: experiment automation scripts for building assets and running Firecracker.
- `Makefile`: helper target for cloning the Firecracker repository locally for this experiment.

Generated directories such as `.firecracker-build/`, `firecracker-assets/`, `firecracker-bin/`, and `firecracker-run/` are created during execution and are ignored by git.
