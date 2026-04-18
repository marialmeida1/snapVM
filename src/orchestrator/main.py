"""Orchestrator V1 CLI — deterministic mock baselines for Firecracker vs Git."""

import argparse
import json
import os
import shutil
import subprocess
import time

import psycopg2

from . import contract, network, snapshot
from .firecracker_client import FirecrackerClient

GUEST_IP = network.GUEST_IP
DB_CONN = dict(host=GUEST_IP, port=5432, user="admin", password="admin", dbname="app_db")
WORKDIR = "workdir"
KERNEL = "images/vmlinux"
ROOTFS = "images/rootfs.ext4"
RESULTS_DIR = "results"


# ── helpers ──────────────────────────────────────────────────────────────

def _db_exec(sql):
    """Execute a SQL statement against the guest PostgreSQL."""
    conn = psycopg2.connect(**DB_CONN)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.close()


def _wait_for_guest(retries=30, delay=2):
    """Block until the guest /health endpoint is reachable (even if unhealthy)."""
    import requests
    for _ in range(retries):
        try:
            requests.get(f"http://{GUEST_IP}:3000/health", timeout=2)
            return True
        except Exception:
            time.sleep(delay)
    return False


# ── mock agent actions ───────────────────────────────────────────────────

def simulate_agent_success():
    _db_exec("CREATE TABLE IF NOT EXISTS users (id serial PRIMARY KEY);")


def simulate_agent_failure():
    _db_exec("DROP TABLE IF EXISTS users;")
    # Kill the Node.js server inside the guest (simulates process crash)
    # We can't SSH in, but dropping the table is enough — /health will 500.


# ── git baseline helpers ─────────────────────────────────────────────────

def _git_init_workdir():
    os.makedirs(WORKDIR, exist_ok=True)
    subprocess.run(["git", "init"], cwd=WORKDIR, capture_output=True, check=True)


def _git_commit_milestone():
    migration = os.path.join(WORKDIR, "migrations")
    os.makedirs(migration, exist_ok=True)
    with open(os.path.join(migration, "001_create_users.sql"), "w") as f:
        f.write("CREATE TABLE IF NOT EXISTS users (id serial PRIMARY KEY);\n")
    subprocess.run(["git", "add", "."], cwd=WORKDIR, capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "milestone: create users table"],
        cwd=WORKDIR, capture_output=True, check=True,
    )


def _git_reset():
    subprocess.run(["git", "reset", "--hard", "HEAD"], cwd=WORKDIR, capture_output=True, check=True)


def _penalty_routine():
    """Re-create the table to simulate an agent manually fixing state."""
    _db_exec("CREATE TABLE IF NOT EXISTS users (id serial PRIMARY KEY);")


# ── VM boot helper ───────────────────────────────────────────────────────

def _boot_vm(client):
    client.spawn()
    client.set_machine_config(vcpu_count=1, mem_size_mib=256)
    client.set_boot_source(KERNEL)
    client.set_rootfs(ROOTFS)
    client.set_network()
    client.start()
    if not _wait_for_guest():
        raise RuntimeError("Guest did not become reachable")


# ── baselines ────────────────────────────────────────────────────────────

def run_git_baseline(client):
    """Baseline A: Git rollback with penalty routine."""
    print("\n=== Baseline A: Git ===")
    report = {"baseline": "git"}

    # Boot VM and wait for guest
    _boot_vm(client)

    # Milestone: agent creates table + git commit
    simulate_agent_success()
    t0 = time.perf_counter()
    _git_init_workdir()
    _git_commit_milestone()
    report["capture_latency_s"] = time.perf_counter() - t0
    report["storage_bytes"] = _dir_size(WORKDIR)

    passed, detail = contract.verify_state()
    print(f"  Pre-failure contract: {passed} — {detail}")

    # Failure injection
    print("  Injecting failure...")
    simulate_agent_failure()
    passed, detail = contract.verify_state()
    print(f"  Post-failure contract: {passed} — {detail}")

    # Git rollback
    t0 = time.perf_counter()
    _git_reset()
    git_reset_time = time.perf_counter() - t0

    # Contract should FAIL — DB is still broken
    passed, detail = contract.verify_state()
    print(f"  Post-git-reset contract: {passed} — {detail}")

    # Penalty routine
    t0 = time.perf_counter()
    _penalty_routine()
    penalty_time = time.perf_counter() - t0

    report["restore_latency_s"] = git_reset_time + penalty_time
    report["git_reset_time_s"] = git_reset_time
    report["penalty_time_s"] = penalty_time

    passed, detail = contract.verify_state()
    report["contract_passed"] = passed
    print(f"  Post-penalty contract: {passed} — {detail}")

    client.kill()
    return report


def run_firecracker_baseline(client):
    """Baseline B: Firecracker snapshot rollback."""
    print("\n=== Baseline B: Firecracker Snapshot ===")
    report = {"baseline": "firecracker"}

    # Boot VM and wait for guest
    _boot_vm(client)

    # Milestone: agent creates table + snapshot
    simulate_agent_success()
    cap_latency, storage = snapshot.capture(client)
    report["capture_latency_s"] = cap_latency
    report["storage_bytes"] = storage

    passed, detail = contract.verify_state()
    print(f"  Pre-failure contract: {passed} — {detail}")

    # Failure injection
    print("  Injecting failure...")
    simulate_agent_failure()
    passed, detail = contract.verify_state()
    print(f"  Post-failure contract: {passed} — {detail}")

    # Snapshot restore
    restore_latency = snapshot.restore(client)
    report["restore_latency_s"] = restore_latency

    # Wait for restored VM to be reachable
    _wait_for_guest()

    passed, detail = contract.verify_state()
    report["contract_passed"] = passed
    report["penalty_time_s"] = 0.0
    print(f"  Post-restore contract: {passed} — {detail}")

    client.kill()
    return report


# ── telemetry ────────────────────────────────────────────────────────────

def _dir_size(path):
    total = 0
    for dirpath, _, filenames in os.walk(path):
        for f in filenames:
            total += os.path.getsize(os.path.join(dirpath, f))
    return total


def save_report(results):
    os.makedirs(RESULTS_DIR, exist_ok=True)
    path = os.path.join(RESULTS_DIR, f"run_{int(time.time())}.json")
    with open(path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nReport saved to {path}")


# ── CLI commands ─────────────────────────────────────────────────────────

def cmd_setup():
    """Provision TAP network interface."""
    network.setup_tap()
    print("TAP interface configured.")


def cmd_run(baseline):
    """Run one or both baselines."""
    client = FirecrackerClient()
    results = []

    if baseline in ("git", "all"):
        results.append(run_git_baseline(client))
    if baseline in ("firecracker", "all"):
        results.append(run_firecracker_baseline(client))

    save_report(results)

    # Print summary table
    print("\n── Summary ──")
    for r in results:
        print(f"  [{r['baseline']}]  capture={r['capture_latency_s']:.4f}s  "
              f"restore={r['restore_latency_s']:.4f}s  "
              f"storage={r['storage_bytes']}B  "
              f"contract={'PASS' if r['contract_passed'] else 'FAIL'}  "
              f"penalty={r['penalty_time_s']:.4f}s")


def cmd_clean():
    """Tear down TAP, kill any running VM, remove workdir."""
    network.teardown_tap()
    client = FirecrackerClient()
    client.kill()
    if os.path.isdir(WORKDIR):
        shutil.rmtree(WORKDIR)
    print("Cleaned up.")


# ── entrypoint ───────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Orchestrator V1 — Firecracker vs Git baselines")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("setup", help="Provision host TAP network interface")

    run_p = sub.add_parser("run", help="Execute baseline experiment(s)")
    run_p.add_argument("--baseline", choices=["git", "firecracker", "all"], default="all")

    sub.add_parser("clean", help="Tear down network, kill VMs, remove workdir")

    args = parser.parse_args()

    if args.command == "setup":
        cmd_setup()
    elif args.command == "run":
        cmd_run(args.baseline)
    elif args.command == "clean":
        cmd_clean()


if __name__ == "__main__":
    main()
