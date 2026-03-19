# Managing Snapshots for One microVM

This guide is operational: how to **create, store, rotate, and restore snapshots** for a specific microVM.

Use it as a runbook when you already understand Firecracker basics and need repeatable snapshot workflows.

## Quick references

- API contract:
  - [`/snapshot/create` and `/snapshot/load`](../../src/firecracker/swagger/firecracker.yaml#L736-L787)
  - [`PATCH /vm` for pause/resume](../../src/firecracker/swagger/firecracker.yaml#L803-L820)
- Request parsing and input validation:
  - [Snapshot request parser](../../src/firecracker/src/api_server/request/snapshot.rs#L26-L125)
- Runtime behavior:
  - [Create snapshot handler](../../src/vmm/src/rpc_interface.rs#L874-L911)
  - [Load snapshot handler](../../src/vmm/src/rpc_interface.rs#L623-L666)
  - [Core create/restore functions](../../src/vmm/src/persist.rs#L166-L470)

## 1) Understand the artifacts you must manage

For one snapshot point-in-time, you will handle:

- **VM state file** (`snapshot_path`)
- **Guest memory file** (`mem_file_path` / `mem_backend.backend_path`)
- **Guest disk image files** (owned by you; Firecracker does not package them)

The request types are defined in [`CreateSnapshotParams` / `LoadSnapshotParams`](../../src/vmm/src/vmm_config/snapshot.rs#L39-L84).

## 2) Suggested directory layout for one microVM

```text
/srv/firecracker/vm-123/
  disks/
    rootfs.ext4
  snapshots/
    full-0001/
      vmstate.fc
      memory.fc
    diff-0002/
      vmstate.fc
      memory.fc
```

Use immutable, versioned snapshot directories. Avoid in-place edits.

## 3) Create a snapshot safely

### Step A: pause the microVM

```bash
curl --unix-socket /path/to/firecracker.socket \
  -i -X PATCH 'http://localhost/vm' \
  -H 'Accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{"state":"Paused"}'
```

### Step B: create snapshot (`Full` or `Diff`)

```bash
curl --unix-socket /path/to/firecracker.socket \
  -i -X PUT 'http://localhost/snapshot/create' \
  -H 'Accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
    "snapshot_type": "Full",
    "snapshot_path": "/srv/firecracker/vm-123/snapshots/full-0001/vmstate.fc",
    "mem_file_path": "/srv/firecracker/vm-123/snapshots/full-0001/memory.fc"
  }'
```

### Step C: resume the microVM

```bash
curl --unix-socket /path/to/firecracker.socket \
  -i -X PATCH 'http://localhost/vm' \
  -H 'Accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{"state":"Resumed"}'
```

Why this order matters: runtime snapshot creation is exposed via `VmmAction::CreateSnapshot` and assumes a paused VM for consistency ([handler](../../src/vmm/src/rpc_interface.rs#L874-L911), [spec text](../../src/firecracker/swagger/firecracker.yaml#L738-L742)).

## 4) Full vs diff strategy

- Use **Full** for portable checkpoints and long-term retention.
- Use **Diff** for short-interval incrementals between full snapshots.

Implementation detail: diff writes only dirty pages, full writes all pages and resets dirty tracking ([memory dump logic](../../src/vmm/src/vstate/vm.rs#L378-L388)).

## 5) Restore a snapshot into a fresh Firecracker process

`/snapshot/load` is pre-boot only. Do this before normal boot/config flow.

```bash
curl --unix-socket /path/to/new-firecracker.socket \
  -i -X PUT 'http://localhost/snapshot/load' \
  -H 'Accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
    "snapshot_path": "/srv/firecracker/vm-123/snapshots/full-0001/vmstate.fc",
    "mem_backend": {
      "backend_type": "File",
      "backend_path": "/srv/firecracker/vm-123/snapshots/full-0001/memory.fc"
    },
    "resume_vm": true
  }'
```

Under the hood this maps to `VmmAction::LoadSnapshot` and then `restore_from_snapshot(...)` ([action path](../../src/vmm/src/rpc_interface.rs#L623-L666), [restore path](../../src/vmm/src/persist.rs#L358-L470)).

## 6) Network and vsock overrides (common for clones)

When restoring into a different environment, use:

- `network_overrides` to swap tap names by interface ID
- `vsock_override` to set a new host UDS path

These are applied during restore before VM reconstruction ([restore code](../../src/vmm/src/persist.rs#L365-L409)).

## 7) Operational checks you should automate

- Check API response code (`204` expected on success).
- Confirm snapshot files exist and are non-empty.
- Track snapshot metadata in your control plane:
  - VM ID
  - snapshot type (`Full`/`Diff`)
  - paths
  - parent lineage (for diff chains)
  - creation timestamp

## 8) Retention and cleanup recommendations

- Keep at least one recent **full** snapshot per microVM.
- Bound diff-chain length (periodically roll up to a new full snapshot).
- Delete old snapshots only after replacement snapshots are validated by test restore.
- Keep snapshot files and disk images under access controls; treat them as sensitive VM state.

## 9) Failure patterns and first responses

- `400` on `/snapshot/load`:
  - verify `mem_backend` xor deprecated `mem_file_path` rule ([validation](../../src/firecracker/src/api_server/request/snapshot.rs#L65-L77)).
- Restore fails during build:
  - confirm snapshot/memory/disk files belong to the same capture set.
- Networking broken after clone:
  - use `network_overrides` and review clone networking guidance in [`network-for-clones.md`](./network-for-clones.md).

## 10) Minimal lifecycle template

1. Pause VM.  
2. Create snapshot (`Full` or `Diff`).  
3. Resume VM.  
4. Persist metadata + artifacts.  
5. Periodically test restore in a fresh Firecracker process.  
6. Rotate old artifacts only after successful restore validation.
