"""SnapVM MCP Server — exposes microVM lifecycle, checkpoint/restore, and execution tools."""

import json
import os
import signal
import subprocess
import time

import psycopg2
import requests
import requests_unixsocket
from mcp.server.fastmcp import FastMCP

# ── Configuration (overridable via environment) ──────────────────────────

GUEST_IP = os.environ.get("SNAPVM_GUEST_IP", "172.16.0.2")
API_PORT = int(os.environ.get("SNAPVM_API_PORT", "3000"))
DB_PORT = int(os.environ.get("SNAPVM_DB_PORT", "5432"))
DB_USER = os.environ.get("SNAPVM_DB_USER", "admin")
DB_PASS = os.environ.get("SNAPVM_DB_PASS", "admin")
DB_NAME = os.environ.get("SNAPVM_DB_NAME", "app_db")
TAP_NAME = os.environ.get("SNAPVM_TAP", "vmtap0")
HOST_IP = os.environ.get("SNAPVM_HOST_IP", "172.16.0.1/24")
FIRECRACKER_BIN = os.environ.get("SNAPVM_FIRECRACKER_BIN", "bin/firecracker")
KERNEL_PATH = os.environ.get("SNAPVM_KERNEL_PATH", "images/vmlinux")
ROOTFS_PATH = os.environ.get("SNAPVM_ROOTFS_PATH", "images/rootfs_run.ext4")
SOCKET_PATH = os.environ.get("SNAPVM_SOCKET_PATH", "/tmp/firecracker.socket")
PID_FILE = os.environ.get("SNAPVM_PID_FILE", "/tmp/firecracker.pid")
SNAPSHOT_DIR = os.environ.get("SNAPVM_SNAPSHOT_DIR", "images/snapshots")

HEALTH_URL = f"http://{GUEST_IP}:{API_PORT}/health"
EXEC_URL = f"http://{GUEST_IP}:{API_PORT}/exec"
DB_CONN = {"host": GUEST_IP, "port": DB_PORT, "user": DB_USER, "password": DB_PASS, "dbname": DB_NAME}

# ── Firecracker Client ───────────────────────────────────────────────────

_process = None
_session = requests_unixsocket.Session()


def _base_url():
    encoded = SOCKET_PATH.replace("/", "%2F")
    return f"http+unix://{encoded}"


def _put(path, body):
    r = _session.put(f"{_base_url()}{path}", json=body)
    r.raise_for_status()
    return r


def _patch(path, body):
    r = _session.patch(f"{_base_url()}{path}", json=body)
    r.raise_for_status()
    return r


def _spawn():
    global _process
    if _process and _process.poll() is None:
        raise RuntimeError("Firecracker already running")
    for p in (SOCKET_PATH, PID_FILE):
        if os.path.exists(p):
            os.remove(p)
    _process = subprocess.Popen(
        [FIRECRACKER_BIN, "--api-sock", SOCKET_PATH],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    for _ in range(50):
        if _process.poll() is not None:
            raise RuntimeError(f"Firecracker exited early (rc={_process.returncode})")
        if os.path.exists(SOCKET_PATH):
            with open(PID_FILE, "w") as f:
                f.write(str(_process.pid))
            return
        time.sleep(0.1)
    raise TimeoutError("Firecracker socket did not appear")


def _kill():
    global _process
    if _process and _process.poll() is None:
        _process.send_signal(signal.SIGTERM)
        try:
            _process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _process.kill()
            _process.wait(timeout=5)
        _process = None
    elif os.path.exists(PID_FILE):
        with open(PID_FILE) as f:
            pid = int(f.read().strip())
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    for p in (SOCKET_PATH, PID_FILE):
        if os.path.exists(p):
            os.remove(p)


# ── MCP Server ───────────────────────────────────────────────────────────

mcp = FastMCP(
    "snapvm",
    instructions=(
        "SnapVM MCP server for managing Firecracker microVM environments. "
        "Provides tools for VM lifecycle (start/stop), health checking, "
        "bash execution inside the guest, SQL queries against guest PostgreSQL, "
        "and snapshot-based checkpoint/restore."
    ),
)


@mcp.tool()
def vm_start(
    vcpu_count: int = 1,
    mem_size_mib: int = 256,
    track_dirty_pages: bool = False,
    boot_args: str = "console=ttyS0 reboot=k panic=1 pci=off selinux=0 init=/sbin/init.sh",
) -> str:
    """Boot a Firecracker microVM with the configured kernel and rootfs.

    Call this before any other tool. Spawns the Firecracker process, configures
    machine resources, attaches kernel/rootfs/network, and starts the instance.
    """
    try:
        _spawn()
        _put("/machine-config", {
            "vcpu_count": vcpu_count,
            "mem_size_mib": mem_size_mib,
            "track_dirty_pages": track_dirty_pages,
        })
        _put("/boot-source", {"kernel_image_path": KERNEL_PATH, "boot_args": boot_args})
        _put("/drives/rootfs", {
            "drive_id": "rootfs",
            "path_on_host": ROOTFS_PATH,
            "is_root_device": True,
            "is_read_only": False,
        })
        _put(f"/network-interfaces/eth0", {
            "iface_id": "eth0",
            "host_dev_name": TAP_NAME,
        })
        _put("/actions", {"action_type": "InstanceStart"})
        return json.dumps({"ok": True, "message": "VM started"})
    except Exception as e:
        return json.dumps({"ok": False, "error": str(e)})


@mcp.tool()
def vm_stop() -> str:
    """Stop and kill the running Firecracker microVM, cleaning up the socket and PID file."""
    try:
        _kill()
        return json.dumps({"ok": True, "message": "VM stopped"})
    except Exception as e:
        return json.dumps({"ok": False, "error": str(e)})


@mcp.tool()
def check_health() -> str:
    """Probe the guest /health endpoint to verify API + DB are healthy.

    Returns the health status JSON from the guest. A healthy response indicates
    both the Express API and PostgreSQL are running with the expected schema.
    """
    try:
        r = requests.get(HEALTH_URL, timeout=5)
        return r.text
    except requests.ConnectionError:
        return json.dumps({"status": "unhealthy", "error": "connection refused — server down"})
    except requests.Timeout:
        return json.dumps({"status": "unhealthy", "error": "probe timed out"})
    except Exception as e:
        return json.dumps({"status": "unhealthy", "error": str(e)})


@mcp.tool()
def execute_bash(command: str) -> str:
    """Execute a bash command inside the guest microVM via its /exec HTTP endpoint.

    The command runs as root inside the VM. Returns stdout/stderr and exit code.
    """
    try:
        r = requests.post(EXEC_URL, json={"command": command}, timeout=30)
        return r.text
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def query_db(sql: str) -> str:
    """Execute a SQL query against the guest PostgreSQL database.

    Supports SELECT, INSERT, UPDATE, DELETE, DDL, etc. Returns rows for SELECT
    queries or a success/error message for others.
    """
    try:
        conn = psycopg2.connect(**DB_CONN)
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(sql)
            if cur.description:
                cols = [d[0] for d in cur.description]
                rows = cur.fetchall()
                result = {"columns": cols, "rows": rows, "row_count": len(rows)}
            else:
                result = {"ok": True, "status": cur.statusmessage}
        conn.close()
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def save_checkpoint(label: str) -> str:
    """Capture a full VM snapshot (memory + CPU + disk state) as a checkpoint.

    Use before risky operations. The VM is briefly paused during capture then
    automatically resumed. Only one checkpoint is kept at a time (last wins).
    """
    os.makedirs(SNAPSHOT_DIR, exist_ok=True)
    mem_path = os.path.join(SNAPSHOT_DIR, "memory.bin")
    snap_path = os.path.join(SNAPSHOT_DIR, "vmstate")
    try:
        t0 = time.perf_counter()
        _patch("/vm", {"state": "Paused"})
        try:
            _put("/snapshot/create", {
                "snapshot_type": "Full",
                "snapshot_path": snap_path,
                "mem_file_path": mem_path,
            })
        finally:
            _patch("/vm", {"state": "Resumed"})
        latency = time.perf_counter() - t0
        return json.dumps({"ok": True, "label": label, "latency_s": round(latency, 3)})
    except Exception as e:
        return json.dumps({"ok": False, "error": str(e)})


@mcp.tool()
def restore_checkpoint() -> str:
    """Restore the VM to the last saved checkpoint.

    Kills the current VM, spawns a fresh Firecracker process, and loads the
    snapshot. All changes since the checkpoint are reverted (memory, disk, DB).
    """
    mem_path = os.path.join(SNAPSHOT_DIR, "memory.bin")
    snap_path = os.path.join(SNAPSHOT_DIR, "vmstate")
    for p in (mem_path, snap_path):
        if not os.path.exists(p):
            return json.dumps({"ok": False, "error": f"Missing snapshot artifact: {p}"})
    try:
        t0 = time.perf_counter()
        _kill()
        _spawn()
        _put("/snapshot/load", {
            "snapshot_path": snap_path,
            "mem_file_path": mem_path,
            "enable_diff_snapshots": False,
            "resume_vm": True,
        })
        latency = time.perf_counter() - t0
        return json.dumps({"ok": True, "latency_s": round(latency, 3)})
    except Exception as e:
        return json.dumps({"ok": False, "error": str(e)})


def main():
    mcp.run()


if __name__ == "__main__":
    main()
