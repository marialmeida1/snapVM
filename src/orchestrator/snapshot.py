"""Snapshot engine: capture, restore, and measure Firecracker microVM state."""

import os
import time

SNAPSHOT_DIR = "images/snapshots"
MEM_FILE = os.path.join(SNAPSHOT_DIR, "memory.bin")
SNAPSHOT_FILE = os.path.join(SNAPSHOT_DIR, "vmstate")


def ensure_dir():
    os.makedirs(SNAPSHOT_DIR, exist_ok=True)


def capture(client, snapshot_type="Full"):
    """Pause VM, create snapshot, resume. Returns (latency_s, storage_bytes)."""
    ensure_dir()
    t0 = time.perf_counter()
    client.pause()
    try:
        client.create_snapshot(
            mem_path=MEM_FILE,
            snapshot_path=SNAPSHOT_FILE,
            snapshot_type=snapshot_type
        )
    finally:
        client.resume()
    latency = time.perf_counter() - t0
    storage = storage_footprint()
    return latency, storage


def restore(client, enable_diff=False):
    """Kill current VM, spawn fresh daemon, load snapshot. Returns latency_s."""
    for path in (MEM_FILE, SNAPSHOT_FILE):
        if not os.path.exists(path):
            raise FileNotFoundError(f"Missing snapshot artifact: {path}")
    t0 = time.perf_counter()
    client.kill()
    client.spawn()
    client.load_snapshot(mem_path=MEM_FILE, snapshot_path=SNAPSHOT_FILE, enable_diff=enable_diff)
    latency = time.perf_counter() - t0
    return latency


def storage_footprint():
    """Return combined byte size of all files in snapshot directory."""
    total = 0
    if not os.path.exists(SNAPSHOT_DIR):
        return 0
    for entry in os.scandir(SNAPSHOT_DIR):
        if entry.is_file():
            total += entry.stat().st_size
    return total
