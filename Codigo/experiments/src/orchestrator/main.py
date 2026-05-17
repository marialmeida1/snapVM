"""Orchestrator V2 CLI — Firecracker vs Git baselines with Incremental Snapshot support."""

import argparse
import json
import os
import shutil
import subprocess
import time

import psycopg2
import requests

from . import contract, network, snapshot
from .agent import AgentLoop
from .config import DB_CONN, GUEST_IP, HEALTH_URL, KERNEL_PATH, RESULTS_DIR, ROOTFS_PATH, WORKDIR
from .firecracker_client import FirecrackerClient

SYSTEM_PROMPT = """You are an AI engineer tasked with managing a stateful microVM environment.
Your goal is to ensure the database and Node.js server are healthy.
You have tools to query the DB, execute bash commands, and check health.
When asked to perform a migration, ensure you verify the state before and after.
"""


# ── helpers ──────────────────────────────────────────────────────────────

def _db_exec(sql, retries=30, delay=2):
    """Execute a SQL statement against the guest PostgreSQL."""
    last_error = None
    for _ in range(retries):
        try:
            conn = psycopg2.connect(**DB_CONN)
            conn.autocommit = True
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.close()
            return
        except psycopg2.OperationalError as e:
            last_error = e
            time.sleep(delay)
    raise RuntimeError(f"Database operation failed after retries: {last_error}")


def _wait_for_guest(retries=30, delay=2):
    """Block until the guest /health endpoint is reachable (even if unhealthy)."""
    for _ in range(retries):
        try:
            requests.get(HEALTH_URL, timeout=2)
            return True
        except requests.RequestException:
            time.sleep(delay)
    return False


def _assert_contract(stage, expected, passed, detail):
    expectation = "pass" if expected else "fail"
    if passed != expected:
        raise RuntimeError(
            f"Contract drift at stage '{stage}': expected {expectation}, got {passed} ({detail})"
        )


# ── mock agent actions ───────────────────────────────────────────────────

def simulate_agent_success():
    _db_exec("CREATE TABLE IF NOT EXISTS users (id serial PRIMARY KEY);")


def simulate_agent_failure():
    _db_exec("DROP TABLE IF EXISTS users;")


# ── git baseline helpers ─────────────────────────────────────────────────

def _git_init_workdir():
    if os.path.isdir(WORKDIR):
        shutil.rmtree(WORKDIR)
    os.makedirs(WORKDIR, exist_ok=True)
    subprocess.run(["git", "init"], cwd=WORKDIR, capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "orchestrator@example.local"],
        cwd=WORKDIR,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Orchestrator V1"],
        cwd=WORKDIR,
        capture_output=True,
        check=True,
    )


def _git_commit_milestone():
    migration = os.path.join(WORKDIR, "migrations")
    os.makedirs(migration, exist_ok=True)
    with open(os.path.join(migration, "001_create_users.sql"), "w", encoding="utf-8") as f:
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

def _boot_vm(client, track_dirty_pages=False):
    client.spawn()
    client.set_machine_config(vcpu_count=1, mem_size_mib=256, track_dirty_pages=track_dirty_pages)
    client.set_boot_source(KERNEL_PATH)
    client.set_rootfs(ROOTFS_PATH)
    client.set_network()
    client.start()
    if not _wait_for_guest():
        raise RuntimeError("Guest did not become reachable")


# ── baselines ────────────────────────────────────────────────────────────

def run_git_baseline(client, agent=None):
    """Baseline A: Git rollback with penalty/re-thinking."""
    print("\n=== Baseline A: Git ===")
    report = {"baseline": "git"}

    try:
        # Boot VM and wait for guest
        _boot_vm(client)

        # Milestone: agent creates table + git commit
        if agent:
            print("  Agent: initializing environment...")
            agent.chat("Initialize the environment by creating a 'users' table in the database.", SYSTEM_PROMPT)
        else:
            simulate_agent_success()

        t0 = time.perf_counter()
        _git_init_workdir()
        _git_commit_milestone()
        report["capture_latency_s"] = time.perf_counter() - t0
        report["storage_bytes"] = _dir_size(WORKDIR)

        passed, detail = contract.verify_state()
        print(f"  Pre-failure contract: {passed} — {detail}")
        _assert_contract("git/pre-failure", expected=True, passed=passed, detail=detail)

        # Failure injection
        print("  Injecting failure...")
        simulate_agent_failure()
        passed, detail = contract.verify_state()
        print(f"  Post-failure contract: {passed} — {detail}")
        _assert_contract("git/post-failure", expected=False, passed=passed, detail=detail)

        # Git rollback
        t0 = time.perf_counter()
        _git_reset()
        git_reset_time = time.perf_counter() - t0

        # Contract should FAIL — DB is still broken
        passed, detail = contract.verify_state()
        print(f"  Post-git-reset contract: {passed} — {detail}")
        _assert_contract("git/post-reset", expected=False, passed=passed, detail=detail)

        # Penalty routine / LLM recovery
        t0 = time.perf_counter()
        if agent:
            print("  Agent: recovering from failure...")
            agent.chat("The environment state was just reset via Git. However, the database might still be corrupted. Please ensure the 'users' table exists and the server is healthy.")
        else:
            _penalty_routine()
        penalty_time = time.perf_counter() - t0

        report["restore_latency_s"] = git_reset_time + penalty_time
        report["penalty_time_s"] = penalty_time

        passed, detail = contract.verify_state()
        _assert_contract("git/post-penalty", expected=True, passed=passed, detail=detail)
        report["contract_passed"] = passed

        if agent:
            report.update(agent.get_telemetry())
        else:
            report.update({"token_consumption": 0, "context_pollution": 0})

        print(f"  Post-penalty contract: {passed} — {detail}")
        return report
    finally:
        client.kill()


def run_firecracker_baseline(client, agent=None, use_diff=False):
    """Baseline B: Firecracker snapshot rollback."""
    print("\n=== Baseline B: Firecracker Snapshot ===")
    report = {"baseline": "firecracker"}

    try:
        # Boot VM and wait for guest
        _boot_vm(client, track_dirty_pages=use_diff)

        # Milestone: agent creates table + snapshot
        if agent:
            print("  Agent: initializing environment...")
            agent.chat("Initialize the environment by creating a 'users' table in the database.", SYSTEM_PROMPT)
        else:
            simulate_agent_success()
        
        cap_latency, storage = snapshot.capture(client, snapshot_type="Full")
        report["capture_latency_s"] = cap_latency
        report["storage_bytes"] = storage

        passed, detail = contract.verify_state()
        print(f"  Pre-failure contract: {passed} — {detail}")
        _assert_contract("firecracker/pre-failure", expected=True, passed=passed, detail=detail)

        # Failure injection
        print("  Injecting failure...")
        simulate_agent_failure()
        passed, detail = contract.verify_state()
        print(f"  Post-failure contract: {passed} — {detail}")
        _assert_contract("firecracker/post-failure", expected=False, passed=passed, detail=detail)

        # Snapshot restore
        restore_start = time.perf_counter()
        snapshot.restore(client)

        # Wait for restored VM to be reachable
        if not _wait_for_guest():
            raise RuntimeError("Restored VM did not become reachable")
        report["restore_latency_s"] = time.perf_counter() - restore_start

        passed, detail = contract.verify_state()
        _assert_contract("firecracker/post-restore", expected=True, passed=passed, detail=detail)
        report["contract_passed"] = passed
        report["penalty_time_s"] = 0.0

        if agent:
            report.update(agent.get_telemetry())
        else:
            report.update({"token_consumption": 0, "context_pollution": 0})

        print(f"  Post-restore contract: {passed} — {detail}")
        return report
    finally:
        client.kill()


def run_diff_test():
    """Experiment 3: Compare Full vs Diff snapshot performance."""
    print("\n=== Experiment 3: Full vs Diff Snapshots ===")
    client = FirecrackerClient()
    results = []

    try:
        # 1. Boot and Full Snapshot (Base)
        _boot_vm(client, track_dirty_pages=True)
        
        # Ensure table exists before snapshotting base
        _db_exec("CREATE TABLE IF NOT EXISTS users (id serial PRIMARY KEY);")
        
        print("  Capturing BASE Full Snapshot...")
        cap_lat_full, size_full = snapshot.capture(client, snapshot_type="Full", suffix="base")
        print(f"    Full: {cap_lat_full:.4f}s, {size_full} bytes")
        
        # 2. Perform some work (Simulate state change)
        print("  Simulating work (creating 10,000 users)...")
        for i in range(100): # Batched for speed
            users = ", ".join(["(nextval('users_id_seq'))" for _ in range(100)])
            _db_exec(f"INSERT INTO users (id) VALUES {users};")
        
        # 3. Capture Diff Snapshot
        print("  Capturing DIFF Snapshot...")
        cap_lat_diff, size_diff = snapshot.capture(client, snapshot_type="Diff", suffix="diff")
        print(f"    Diff: {cap_lat_diff:.4f}s, {size_diff} bytes")
        
        results = [
            {"type": "Full (Base)", "latency": cap_lat_full, "size": size_full},
            {"type": "Diff (Incremental)", "latency": cap_lat_diff, "size": size_diff}
        ]
        
        # 4. Verification: Restore from Diff
        print("  Verifying Restoration from Diff...")
        res_lat = snapshot.restore(client, suffix="diff")
        _wait_for_guest()
        passed, detail = contract.verify_state()
        print(f"    Restore Result: {passed} — {detail}")
        
        return results
    except Exception as e:
        print(f"  Error in diff-test: {e}")
        return []
    finally:
        client.kill()


# ── telemetry ────────────────────────────────────────────────────────────

def _dir_size(path):
    total = 0
    if not os.path.exists(path):
        return 0
    for dirpath, _, filenames in os.walk(path):
        for f in filenames:
            total += os.path.getsize(os.path.join(dirpath, f))
    return total


def save_report(results):
    os.makedirs(RESULTS_DIR, exist_ok=True)
    path = os.path.join(RESULTS_DIR, f"run_{int(time.time() * 1000)}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nReport saved to {path}")


# ── CLI commands ─────────────────────────────────────────────────────────

def cmd_setup():
    """Provision TAP network interface."""
    network.setup_tap()
    print("TAP interface configured.")


def cmd_run(baseline, mode, iterations):
    """Run one or both baselines across N iterations."""
    client = FirecrackerClient()
    all_results = []

    for i in range(iterations):
        if iterations > 1:
            print(f"\n--- Iteration {i+1}/{iterations} ---")
        
        results = []
        
        if baseline in ("git", "all"):
            agent = AgentLoop() if mode == "live" else None
            results.append(run_git_baseline(client, agent))
        
        if baseline in ("firecracker", "all"):
            agent = AgentLoop() if mode == "live" else None
            results.append(run_firecracker_baseline(client, agent, use_diff=(mode == "live")))
        
        all_results.extend(results)

    save_report(all_results)

    # Print summary table
    print("\n── Summary ──")
    print(f"{'Baseline':<12} {'Capture':<8} {'Restore':<8} {'Storage':<10} {'Tokens':<8} {'Pollution':<10} {'Result':<8}")
    print("-" * 75)
    for r in all_results:
        print(f"{r['baseline']:<12} "
              f"{r['capture_latency_s']:>7.3f}s "
              f"{r['restore_latency_s']:>7.3f}s "
              f"{r['storage_bytes']:>9}B "
              f"{r['token_consumption']:>8} "
              f"{r['context_pollution']:>10} "
              f"{'PASS' if r['contract_passed'] else 'FAIL':<8}")


def cmd_diff_test():
    """Execute Experiment 3 and print results."""
    results = run_diff_test()
    if not results:
        return

    print("\n── Experiment 3 Results ──")
    print(f"{'Type':<20} {'Latency':<12} {'Storage':<15}")
    print("-" * 50)
    for r in results:
        print(f"{r['type']:<20} {r['latency']:>10.4f}s {r['size']:>13}B")
    
    improvement_size = (1 - results[1]['size'] / results[0]['size']) * 100
    print(f"\nStorage Improvement: {improvement_size:.1f}%")


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
    parser = argparse.ArgumentParser(description="Orchestrator V2 — Firecracker vs Git baselines")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("setup", help="Provision host TAP network interface")

    run_p = sub.add_parser("run", help="Execute baseline experiment(s)")
    run_p.add_argument("--baseline", choices=["git", "firecracker", "all"], default="all")
    run_p.add_argument("--mode", choices=["mock", "live"], default="mock", help="Use deterministic mock or live LLM agent")
    run_p.add_argument("--iterations", type=int, default=1, help="Number of experimental iterations")

    sub.add_parser("diff-test", help="Execute Experiment 3 (Full vs Diff Optimization)")

    sub.add_parser("clean", help="Tear down network, kill VMs, remove workdir")

    run_v4_p = sub.add_parser("run-v4", help="Execute Experiment 4 (Fair Autonomous Recovery)")
    run_v4_p.add_argument("--iterations", type=int, default=20, help="Iterations per baseline")

    run_v4_1_p = sub.add_parser("run-v4.1", help="Execute Experiment 4.1 (Complex Failures)")
    run_v4_1_p.add_argument("--iterations", type=int, default=4, help="Iterations per scenario")

    run_v4_2_p = sub.add_parser("run-v4.2", help="Execute Experiment 4.2 (Forced Snapshot Recovery)")
    run_v4_2_p.add_argument("--iterations", type=int, default=4, help="Iterations per scenario")

    run_v5_p = sub.add_parser("run-v5", help="Execute Experiment 5 (Agent-Driven Checkpoints)")
    run_v5_p.add_argument("--iterations", type=int, default=10, help="Iterations per baseline")

    run_v6_p = sub.add_parser("run-v6", help="Execute Experiment 6 (Exploration Branching)")
    run_v6_p.add_argument("--iterations", type=int, default=15, help="Iterations per baseline")

    args = parser.parse_args()

    if args.command == "setup":
        cmd_setup()
    elif args.command == "run":
        cmd_run(args.baseline, args.mode, args.iterations)
    elif args.command == "diff-test":
        cmd_diff_test()
    elif args.command == "run-v4":
        from .experiment_v4 import run_experiment
        run_experiment(iterations=args.iterations)
    elif args.command == "run-v4.1":
        from .experiment_v4_1 import run_experiment
        run_experiment(iterations=args.iterations)
    elif args.command == "run-v4.2":
        from .experiment_v4_2 import run_experiment
        run_experiment(iterations=args.iterations)
    elif args.command == "run-v5":
        from .experiment_v5 import run_experiment
        run_experiment(iterations=args.iterations)
    elif args.command == "run-v6":
        from .experiment_v6 import run_experiment
        run_experiment(iterations=args.iterations)
    elif args.command == "clean":
        cmd_clean()


if __name__ == "__main__":
    main()
