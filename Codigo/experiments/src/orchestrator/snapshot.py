"""Snapshot engine: capture, restore, and measure Firecracker microVM state."""

import os
import time

from .config import SNAPSHOT_DIR

MEM_FILE = os.path.join(SNAPSHOT_DIR, "memory.bin")
SNAPSHOT_FILE = os.path.join(SNAPSHOT_DIR, "vmstate")


def ensure_dir():
    os.makedirs(SNAPSHOT_DIR, exist_ok=True)


def _get_actual_size(path):
    """Return actual disk usage in bytes (handling sparse files)."""
    st = os.stat(path)
    # st_blocks is in 512-byte units
    return st.st_blocks * 512


def capture(client, snapshot_type="Full", suffix=""):
    """Pause VM, create snapshot, resume. Returns (latency_s, storage_bytes)."""
    ensure_dir()
    
    # Use suffixes for incremental snapshots (e.g., vmstate.diff.1)
    tag = f".{suffix}" if suffix else ""
    mem_path = f"{MEM_FILE}{tag}"
    snap_path = f"{SNAPSHOT_FILE}{tag}"
    
    t0 = time.perf_counter()
    client.pause()
    try:
        client.create_snapshot(
            mem_path=mem_path,
            snapshot_path=snap_path,
            snapshot_type=snapshot_type
        )
    finally:
        client.resume()
    
    latency = time.perf_counter() - t0
    
    # Calculate actual disk usage
    storage = _get_actual_size(mem_path) + _get_actual_size(snap_path)
    return latency, storage


def restore(client, enable_diff=False, suffix=""):
    """Kill current VM, spawn fresh daemon, load snapshot. Returns latency_s."""
    tag = f".{suffix}" if suffix else ""
    mem_path = f"{MEM_FILE}{tag}"
    snap_path = f"{SNAPSHOT_FILE}{tag}"
    
    for path in (mem_path, snap_path):
        if not os.path.exists(path):
            raise FileNotFoundError(f"Missing snapshot artifact: {path}")
    
    t0 = time.perf_counter()
    client.kill()
    client.spawn()
    client.load_snapshot(mem_path=mem_path, snapshot_path=snap_path, enable_diff=enable_diff)
    latency = time.perf_counter() - t0
    return latency


def storage_footprint():
    """Return combined byte size of all files in snapshot directory."""
    total = 0
    if not os.path.exists(SNAPSHOT_DIR):
        return 0
    for entry in os.scandir(SNAPSHOT_DIR):
        if entry.is_file():
            total += _get_actual_size(entry.path)
    return total
