# Firecracker Snapshot Implementation Walkthrough

> Last documented update: 2026-03-19  
> Author: Arthur Carvalho

This guide explains **how snapshotting is implemented inside Firecracker**, starting from API requests and ending with serialization/restoration internals.

If you are new to Firecracker, read this as: **HTTP request -> API parsing -> VMM action -> snapshot engine**.

## Source map (deep links)

- API contract:
  - [`/snapshot/create`, `/snapshot/load`, `/vm` endpoints](../../src/firecracker/swagger/firecracker.yaml#L736-L820)
- API routing and request parsing:
  - [URI routing to snapshot parser](../../src/firecracker/src/api_server/parsed_request.rs#L102-L128)
  - [Snapshot request parsing](../../src/firecracker/src/api_server/request/snapshot.rs#L26-L125)
- VMM action layer:
  - [`VmmAction::{CreateSnapshot,LoadSnapshot}`](../../src/vmm/src/rpc_interface.rs#L47-L94)
  - [Pre-boot load handler](../../src/vmm/src/rpc_interface.rs#L623-L666)
  - [Runtime create handler](../../src/vmm/src/rpc_interface.rs#L874-L911)
- Snapshot core:
  - [Snapshot format and validation](../../src/vmm/src/snapshot/mod.rs#L4-L220)
  - [Create/restore orchestration](../../src/vmm/src/persist.rs#L86-L209)
  - [Restore pipeline + backend choice](../../src/vmm/src/persist.rs#L358-L470)
  - [Memory dump logic (full vs diff)](../../src/vmm/src/vstate/vm.rs#L328-L390)
  - [Snapshot request structures](../../src/vmm/src/vmm_config/snapshot.rs#L12-L143)

## 1) API contract and semantics

Firecracker exposes:

- `PUT /snapshot/create` (post-boot, VM should be paused)
- `PUT /snapshot/load` (pre-boot, fresh process)
- `PATCH /vm` (`Paused` / `Resumed`)

From the OpenAPI spec:

```yaml
/snapshot/create:
  put:
    summary: Creates a full or diff snapshot. Post-boot only.

/snapshot/load:
  put:
    summary: Loads a snapshot. Pre-boot only.
```

Reference: [`firecracker.yaml`](../../src/firecracker/swagger/firecracker.yaml#L736-L787).

## 2) How HTTP requests become VMM actions

### Router dispatch

```rust
(Method::Put, "snapshot", Some(body)) => parse_put_snapshot(body, path_tokens.next()),
(Method::Patch, "vm", Some(body)) => parse_patch_vm_state(body),
```

Reference: [`parsed_request.rs`](../../src/firecracker/src/api_server/parsed_request.rs#L109-L124).

### Snapshot parser

```rust
match request_type {
    "create" => parse_put_snapshot_create(body),
    "load" => parse_put_snapshot_load(body),
    _ => Err(RequestError::InvalidPathMethod(...)),
}
```

For load, Firecracker validates exactly one memory source (`mem_backend` xor deprecated `mem_file_path`) and constructs:

```rust
ParsedRequest::new_sync(VmmAction::LoadSnapshot(snapshot_params))
```

Reference: [`request/snapshot.rs`](../../src/firecracker/src/api_server/request/snapshot.rs#L26-L125).

## 3) Action layer: pre-boot vs runtime

`VmmAction` is the internal command enum:

```rust
CreateSnapshot(CreateSnapshotParams),
LoadSnapshot(LoadSnapshotParams),
Pause,
Resume,
```

Reference: [`rpc_interface.rs`](../../src/vmm/src/rpc_interface.rs#L50-L104).

Important split:

- `LoadSnapshot` is handled by the **pre-boot** controller (`BootStrapApiController`).
- `CreateSnapshot` is handled by the **runtime** controller (`RuntimeApiController`).

## 4) Create path internals

### 4.1 Runtime API handler

```rust
fn create_snapshot(&mut self, create_params: &CreateSnapshotParams) -> Result<VmmData, VmmActionError> {
    let mut locked_vmm = self.vmm.lock().unwrap();
    let vm_info = VmInfo::from(&*locked_vmm);
    create_snapshot(&mut locked_vmm, &vm_info, create_params)?;
    Ok(VmmData::Empty)
}
```

Reference: [`rpc_interface.rs`](../../src/vmm/src/rpc_interface.rs#L874-L911).

### 4.2 Persist layer orchestration

```rust
pub fn create_snapshot(vmm: &mut Vmm, vm_info: &VmInfo, params: &CreateSnapshotParams)
-> Result<(), CreateSnapshotError> {
    let microvm_state = vmm.save_state(vm_info)?;
    snapshot_state_to_file(&microvm_state, &params.snapshot_path)?;
    vmm.vm.snapshot_memory_to_file(&params.mem_file_path, params.snapshot_type)?;
    vmm.device_manager.mark_virtio_queue_memory_dirty(vmm.vm.guest_memory());
    Ok(())
}
```

Reference: [`persist.rs`](../../src/vmm/src/persist.rs#L166-L187).

### 4.3 What `save_state()` captures

`save_state()` collects device state, vCPU state, KVM state, and VM state:

```rust
let device_states = self.device_manager.save();
let vcpu_states = self.save_vcpu_states()?;
let kvm_state = self.kvm.save_state();
let vm_state = self.vm.save_state()?;
```

Reference: [`lib.rs`](../../src/vmm/src/lib.rs#L561-L592).

### 4.4 Full vs diff memory snapshots

```rust
match snapshot_type {
    SnapshotType::Diff => {
        let dirty_bitmap = self.get_dirty_bitmap()?;
        self.guest_memory().dump_dirty(&mut file, &dirty_bitmap)?;
    }
    SnapshotType::Full => {
        self.guest_memory().dump(&mut file)?;
        self.reset_dirty_bitmap();
        self.guest_memory().reset_dirty();
    }
}
```

Reference: [`vstate/vm.rs`](../../src/vmm/src/vstate/vm.rs#L378-L388).

## 5) Snapshot state file format

Firecracker wraps VM state in `Snapshot<Data>`:

- Header: `magic` + `version`
- Payload: serialized state (`bitcode`)
- Tail: CRC64

```rust
pub struct Snapshot<Data> {
    header: SnapshotHdr,
    pub data: Data,
}
```

And validation checks include:

- architecture magic ID
- version compatibility
- CRC integrity

Reference: [`snapshot/mod.rs`](../../src/vmm/src/snapshot/mod.rs#L11-L220).

## 6) Load path internals

### 6.1 Pre-boot API handler

```rust
let vmm = restore_from_snapshot(..., load_params, ...)?;
if load_params.resume_vm {
    vmm.lock().expect("Poisoned lock").resume_vm()?;
}
self.built_vmm = Some(vmm);
```

Reference: [`rpc_interface.rs`](../../src/vmm/src/rpc_interface.rs#L623-L666).

### 6.2 Restore orchestration

`restore_from_snapshot()`:

1. reads snapshot state from `snapshot_path`;
2. applies optional network/vsock overrides;
3. performs sanity checks;
4. selects memory backend (`File` or `Uffd`);
5. rebuilds a runnable VMM from persisted state.

Key branch:

```rust
let (guest_memory, uffd) = match params.mem_backend.backend_type {
    MemBackendType::File => (...),
    MemBackendType::Uffd => guest_memory_from_uffd(...)?,
};
builder::build_microvm_from_snapshot(..., microvm_state, guest_memory, uffd, ...)
```

Reference: [`persist.rs`](../../src/vmm/src/persist.rs#L358-L470).

### 6.3 Rebuild process

`build_microvm_from_snapshot()` restores memory regions, vCPUs, VM/KVM state, and devices, then returns a live `Vmm`.

Reference: [`builder.rs`](../../src/vmm/src/builder.rs#L435-L520).

## 7) Types that define the API payloads

The snapshot configuration types live in one place:

- `SnapshotType` (`Full` / `Diff`)
- `CreateSnapshotParams`
- `LoadSnapshotParams`
- `MemBackendType` (`File` / `Uffd`)

Reference: [`vmm_config/snapshot.rs`](../../src/vmm/src/vmm_config/snapshot.rs#L12-L143).

## 8) Mental model summary

Snapshotting in Firecracker is intentionally split into two artifacts:

- **State file** (serialized virtual hardware + VMM state)
- **Memory file/backend** (guest RAM content)

Creation and restore are wired through a strict API/action pipeline and guarded by validation (input checks, snapshot sanity checks, version/magic/CRC checks). This makes the feature composable while keeping the fast-restore design.
