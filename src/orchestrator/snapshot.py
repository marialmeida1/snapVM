"""Snapshot engine: capture, restore, and measure Firecracker microVM state."""

import os
import time

SNAPSHOT_DIR = "images/snapshots"
MEM_FILE = os.path.join(SNAPSHOT_DIR, "memory.bin")
SNAPSHOT_FILE = os.path.join(SNAPSHOT_DIR, "vmstate")


def ensure_dir():
    os.makedirs(SNAPSHOT_DIR, exist_ok=True)


def capture(client):
    """Pause VM, create snapshot, resume. Returns (latency_s, storage_bytes)."""
    ensure_dir()
    t0 = time.perf_counter()
    client.pause()
    client.create_snapshot(mem_path=MEM_FILE, snapshot_path=SNAPSHOT_FILE)
    client.resume()
    latency = time.perf_counter() - t0
    storage = storage_footprint()
    return latency, storage


def restore(client):
    """Kill current VM, spawn fresh daemon, load snapshot. Returns latency_s."""
    client.kill()
    client.spawn()
    t0 = time.perf_counter()
    client.load_snapshot(mem_path=MEM_FILE, snapshot_path=SNAPSHOT_FILE)
    latency = time.perf_counter() - t0
    return latency


def storage_footprint():
    """Return combined byte size of snapshot files."""
    total = 0
    for name in (MEM_FILE, SNAPSHOT_FILE):
        if os.path.exists(name):
            total += os.stat(name).st_size
    return total
