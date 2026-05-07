# Experiment 2: Orchestrator V1

This experiment validates a Python orchestrator that compares Git-based rollback against Firecracker snapshot restoration.

## Structure

- `docs/`: experiment reports, setup guides, environment notes, and methodology.
- `src/`: orchestrator implementation plus guest application assets.
- `tests/`: automated tests for the orchestrator flow.
- `Dockerfile`: guest image build for the experiment.
- `init.sh`: guest init routine used by the Firecracker VM.
- `setup.sh`: experiment setup script for Firecracker assets and rootfs creation.
- `requirements.txt`: Python dependencies required to run the orchestrator.

This directory should contain everything needed for the Orchestrator V1 validation without mixing it into the future `snapvm/` module or the general project documentation.
