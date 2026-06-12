# SnapVM MCP Server

MCP (Model Context Protocol) server that exposes Firecracker microVM lifecycle, checkpoint/restore, and execution tools — enabling any MCP-compatible AI agent to manage stateful VM environments.

## Tools

| Tool | Description |
|------|-------------|
| `vm_start` | Boot a Firecracker microVM (configure vCPUs, memory, kernel, rootfs, network) |
| `vm_stop` | Kill the running VM and clean up |
| `check_health` | Probe guest `/health` endpoint (validates API + DB) |
| `execute_bash` | Run a bash command inside the guest VM |
| `query_db` | Execute SQL against the guest PostgreSQL |
| `save_checkpoint` | Capture full VM snapshot (pause → snapshot → resume) |
| `restore_checkpoint` | Restore VM to last checkpoint (kill → spawn → load snapshot) |

## Prerequisites

- Linux host with KVM enabled
- Firecracker binary, kernel image, and rootfs built (see `../experiments/setup.sh`)
- TAP networking configured (`sudo ip tuntap add dev vmtap0 mode tap && sudo ip addr add 172.16.0.1/24 dev vmtap0 && sudo ip link set vmtap0 up`)

## Installation

```bash
cd Codigo/snapvm
pip install -e .
```

## Running

```bash
# stdio transport (default for MCP clients)
snapvm-mcp

# Or directly:
python -m snapvm_mcp.server
```

## Configuration

All settings are environment-variable overridable:

| Variable | Default | Description |
|----------|---------|-------------|
| `SNAPVM_GUEST_IP` | `172.16.0.2` | Guest VM IP |
| `SNAPVM_API_PORT` | `3000` | Guest API port |
| `SNAPVM_DB_PORT` | `5432` | Guest PostgreSQL port |
| `SNAPVM_DB_USER` | `admin` | DB username |
| `SNAPVM_DB_PASS` | `admin` | DB password |
| `SNAPVM_DB_NAME` | `app_db` | DB name |
| `SNAPVM_TAP` | `vmtap0` | TAP interface name |
| `SNAPVM_HOST_IP` | `172.16.0.1/24` | Host TAP IP |
| `SNAPVM_FIRECRACKER_BIN` | `bin/firecracker` | Firecracker binary path |
| `SNAPVM_KERNEL_PATH` | `images/vmlinux` | Kernel image path |
| `SNAPVM_ROOTFS_PATH` | `images/rootfs_run.ext4` | Root filesystem path |
| `SNAPVM_SOCKET_PATH` | `/tmp/firecracker.socket` | Firecracker API socket |
| `SNAPVM_PID_FILE` | `/tmp/firecracker.pid` | PID file path |
| `SNAPVM_SNAPSHOT_DIR` | `images/snapshots` | Snapshot storage directory |

## MCP Client Configuration

### Claude Desktop / Kiro

Add to your MCP config (`~/.config/claude/claude_desktop_config.json` or equivalent):

```json
{
  "mcpServers": {
    "snapvm": {
      "command": "snapvm-mcp",
      "env": {
        "SNAPVM_FIRECRACKER_BIN": "/path/to/firecracker",
        "SNAPVM_KERNEL_PATH": "/path/to/vmlinux",
        "SNAPVM_ROOTFS_PATH": "/path/to/rootfs_run.ext4"
      }
    }
  }
}
```

### Using `uv` (without pre-installing)

```json
{
  "mcpServers": {
    "snapvm": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/Codigo/snapvm", "snapvm-mcp"]
    }
  }
}
```

## Typical Workflow

```
1. vm_start()           → Boot the microVM
2. check_health()       → Verify guest is ready
3. save_checkpoint()    → Capture known-good state
4. execute_bash(...)    → Do work inside the VM
5. query_db(...)        → Interact with PostgreSQL
6. check_health()       → Verify still healthy
7. restore_checkpoint() → Revert if something broke
8. vm_stop()            → Clean shutdown
```
