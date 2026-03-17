# Firecracker Snapshot Rollback Demo

This example demonstrates a full loop:

1. Boot a Firecracker microVM.
2. Run a working Python "Hello, world!" web API in the guest.
3. Create a VM snapshot.
4. Replace the app with intentionally broken code.
5. Detect the failure.
6. Load the previous snapshot in a fresh Firecracker process.
7. Verify the app works again.

## Why this works

The demo app is written to `/dev/shm/app.py` (memory-backed tmpfs).  
Firecracker snapshots capture guest memory, so loading the snapshot restores the pre-failure code and process state.

## Files

- `guest/api_working.py` – healthy API implementation.
- `guest/api_broken.py` – intentionally broken version (syntax error).
- `scripts/setup_tap.sh` – creates tap networking.
- `scripts/teardown_tap.sh` – removes tap networking.
- `scripts/demo_snapshot_rollback.sh` – end-to-end orchestration.

## Prerequisites

- Linux host with KVM and Firecracker.
- Firecracker guest kernel image.
- Rootfs image with:
  - Python 3
  - OpenSSH server enabled
  - root login via SSH key
  - `curl`
- `curl`, `ssh`, `scp`, and `sudo` available on host.

## Run

From repository root:

```bash
cd examples/firecracker-snapshot-rollback
chmod +x scripts/*.sh
```

Set required variables:

```bash
export FIRECRACKER_BIN=/absolute/path/to/firecracker
export KERNEL_IMAGE=/absolute/path/to/vmlinux
export ROOTFS_IMAGE=/absolute/path/to/rootfs.ext4
export SSH_KEY=/absolute/path/to/id_rsa
```

Optional networking variables:

```bash
export TAP_DEV=fctap0
export HOST_TAP_IP=172.16.0.1
export GUEST_IP=172.16.0.2
```

Create tap device:

```bash
./scripts/setup_tap.sh
```

Run the demo:

```bash
./scripts/demo_snapshot_rollback.sh
```

Cleanup:

```bash
./scripts/teardown_tap.sh
```

## Expected output (high-level)

- API healthy before snapshot.
- Failure detected after broken code deployment.
- Snapshot load succeeds.
- API healthy again after rollback.
