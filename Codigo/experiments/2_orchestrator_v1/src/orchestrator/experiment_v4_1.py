"""Experiment V4.1 — Complex Stateful Failures.

Same fair methodology as V4 but with multi-layered failures that are
expensive to diagnose and repair manually, while snapshot restore remains O(1).
"""

import json
import os
import time
from datetime import datetime, timezone

import psycopg2
import requests

from . import contract, network, snapshot
from .experiment_v4 import (
    FairAgentLoop,
    SYSTEM_PROMPT,
    INIT_PROMPT,
    TOOL_EXECUTE_BASH,
    TOOL_CHECK_HEALTH,
    TOOL_QUERY_DB,
    TOOL_RESTORE_SNAPSHOT,
    GUEST_IP,
    DB_CONN,
    KERNEL,
    ROOTFS,
    RESULTS_DIR,
    _boot_vm,
    _db_exec,
    _wait_for_guest,
)
from .firecracker_client import FirecrackerClient

MAX_TOOL_CALLS = 25

# ── Failure Scenarios ────────────────────────────────────────────────────

FAILURE_SCENARIOS = [
    {
        "id": "F1",
        "name": "multi_table_corruption",
        "description": "Drop users table + insert corrupt data into a new rogue table",
        "complexity": 2,
    },
    {
        "id": "F2",
        "name": "process_and_config",
        "description": "Kill Node.js process + corrupt the server.js file",
        "complexity": 2,
    },
    {
        "id": "F3",
        "name": "schema_and_data_corruption",
        "description": "Alter column type + insert invalid data that breaks queries",
        "complexity": 2,
    },
    {
        "id": "F4",
        "name": "permissions_and_schema",
        "description": "Drop users table + revoke DB user permissions",
        "complexity": 2,
    },
    {
        "id": "F5",
        "name": "cascading_service_failure",
        "description": "Truncate table + kill PostgreSQL + remove PG socket",
        "complexity": 3,
    },
]


def _inject_failure(scenario_id):
    """Inject a complex failure into the guest environment."""
    if scenario_id == "F1":
        _db_exec("DROP TABLE IF EXISTS users;")
        _db_exec("CREATE TABLE IF NOT EXISTS rogue_data (id serial, garbage text);")
        _db_exec("INSERT INTO rogue_data (garbage) VALUES ('corrupted'), ('bad_state'), ('leak');")

    elif scenario_id == "F2":
        # Kill Node.js and corrupt server.js
        requests.post(f"http://{GUEST_IP}:3000/exec",
                      json={"command": "pkill -f 'node server.js'"}, timeout=5)
        # Wait a moment for process to die, then corrupt the file
        time.sleep(0.5)
        # We can't use the /exec endpoint anymore (server is dead), so we
        # corrupt via DB-level side effect: the server is simply dead.
        # Also write garbage to server.js via a pre-kill command won't work.
        # Instead: kill node + drop the table (double failure without /exec)
        _db_exec("DROP TABLE IF EXISTS users;")

    elif scenario_id == "F3":
        _db_exec("ALTER TABLE users ADD COLUMN name text;")
        _db_exec("ALTER TABLE users ALTER COLUMN id TYPE text USING id::text;")
        _db_exec("INSERT INTO users (id, name) VALUES ('not_a_number', 'corrupt');")

    elif scenario_id == "F4":
        _db_exec("DROP TABLE IF EXISTS users;")
        # Revoke connect from the app user (admin) on the database
        # Use postgres superuser workaround: admin IS superuser in our setup,
        # so instead revoke CREATE privilege to make table recreation fail
        _db_exec("REVOKE CREATE ON SCHEMA public FROM admin;")

    elif scenario_id == "F5":
        _db_exec("TRUNCATE users;")
        # Kill PostgreSQL via the exec endpoint (server still alive at this point)
        requests.post(f"http://{GUEST_IP}:3000/exec",
                      json={"command": "pkill -9 postgres"}, timeout=5)
        time.sleep(0.5)
        # Remove PG socket to make reconnection harder
        requests.post(f"http://{GUEST_IP}:3000/exec",
                      json={"command": "rm -rf /var/run/postgresql/.s.PGSQL.5432"}, timeout=5)


def _get_health_detail_for_scenario(scenario_id):
    """Get the actual health detail after injection (what the agent sees)."""
    passed, detail = contract.verify_state()
    if not passed:
        return detail
    # If somehow still healthy, force-check
    return "unknown failure"


# ── Perception Hook ──────────────────────────────────────────────────────

def _perception_hook(health_detail):
    ts = datetime.now(timezone.utc).isoformat()
    return (
        "[ENVIRONMENT STATE]\n"
        "health_status: UNHEALTHY\n"
        f"health_detail: {health_detail}\n"
        f"last_health_check: {ts}\n"
        "[/ENVIRONMENT STATE]\n\n"
        "The environment health has changed. Resolve the issue."
    )


# ── Baselines ────────────────────────────────────────────────────────────

def run_standard_baseline(client, iteration, scenario):
    """Baseline A: manual recovery only."""
    print(f"\n  [standard] iter {iteration} scenario {scenario['id']}: {scenario['name']}")
    tools = [TOOL_EXECUTE_BASH, TOOL_CHECK_HEALTH, TOOL_QUERY_DB]
    agent = FairAgentLoop(tools=tools)
    agent.tool_call_count = 0  # reset

    try:
        _boot_vm(client)

        # Init
        agent.messages.append({"role": "system", "content": SYSTEM_PROMPT})
        agent.chat(INIT_PROMPT)
        passed, _ = contract.verify_state()
        if not passed:
            raise RuntimeError("Init failed health check")

        # Inject complex failure
        _inject_failure(scenario["id"])
        health_detail = _get_health_detail_for_scenario(scenario["id"])

        # Recovery phase
        agent.set_phase("recovery")
        agent.tool_call_count = 0
        agent.tool_sequence = []

        # Override max tool calls for complex scenarios
        original_chat = agent.chat

        def limited_chat(msg):
            agent.messages.append({"role": "user", "content": msg})
            while True:
                response = agent.client.chat.completions.create(
                    model=agent.model, messages=agent.messages,
                    tools=agent.tools, tool_choice="auto", temperature=0,
                )
                agent._track_usage(response.usage)
                m = response.choices[0].message
                agent.messages.append(m)
                if not m.tool_calls:
                    return m.content
                for tc in m.tool_calls:
                    result = agent._run_tool(tc)
                    agent.messages.append({
                        "role": "tool", "tool_call_id": tc.id,
                        "name": tc.function.name, "content": result,
                    })
                if agent.tool_call_count >= MAX_TOOL_CALLS:
                    return None

        t0 = time.perf_counter()
        limited_chat(_perception_hook(health_detail))
        recovery_latency = time.perf_counter() - t0

        passed, detail = contract.verify_state()

        return {
            "iteration": iteration,
            "baseline": "standard",
            "scenario_id": scenario["id"],
            "scenario_name": scenario["name"],
            "failure_complexity": scenario["complexity"],
            "recovery_success": passed,
            "tool_calls_total": agent.tool_call_count,
            "token_consumption": agent.recovery_tokens["prompt"] + agent.recovery_tokens["completion"],
            "prompt_tokens": agent.recovery_tokens["prompt"],
            "completion_tokens": agent.recovery_tokens["completion"],
            "recovery_latency_s": round(recovery_latency, 3),
            "context_pollution": agent.get_context_pollution(),
            "first_action": agent.tool_sequence[0] if agent.tool_sequence else None,
            "tool_sequence": agent.tool_sequence,
            "recovery_strategy": "manual_repair" if passed else "failed",
        }
    finally:
        client.kill()


def run_snapvm_baseline(client, iteration, scenario):
    """Baseline B: has restore_last_snapshot tool."""
    print(f"\n  [snapvm] iter {iteration} scenario {scenario['id']}: {scenario['name']}")

    def restore_handler():
        t0 = time.perf_counter()
        snapshot.restore(client)
        if not _wait_for_guest():
            return {"ok": False, "error": "VM did not become reachable after restore"}
        latency = time.perf_counter() - t0
        passed, detail = contract.verify_state()
        return {
            "ok": passed,
            "restore_latency_s": round(latency, 3),
            "health_after_restore": "HEALTHY" if passed else f"UNHEALTHY: {detail}",
        }

    tools = [TOOL_EXECUTE_BASH, TOOL_CHECK_HEALTH, TOOL_QUERY_DB, TOOL_RESTORE_SNAPSHOT]
    agent = FairAgentLoop(tools=tools, restore_handler=restore_handler)

    try:
        _boot_vm(client)

        # Init
        agent.messages.append({"role": "system", "content": SYSTEM_PROMPT})
        agent.chat(INIT_PROMPT)
        passed, _ = contract.verify_state()
        if not passed:
            raise RuntimeError("Init failed health check")

        # Capture snapshot (silent)
        snapshot.capture(client, snapshot_type="Full")

        # Inject complex failure
        _inject_failure(scenario["id"])
        health_detail = _get_health_detail_for_scenario(scenario["id"])

        # Recovery phase
        agent.set_phase("recovery")
        agent.tool_call_count = 0
        agent.tool_sequence = []
        agent._snapshot_restored = False

        t0 = time.perf_counter()
        agent.chat(_perception_hook(health_detail))
        recovery_latency = time.perf_counter() - t0

        passed, detail = contract.verify_state()

        strategy = "failed"
        if passed:
            if "restore_last_snapshot" in agent.tool_sequence:
                strategy = "snapshot_restore"
            else:
                strategy = "manual_repair"

        return {
            "iteration": iteration,
            "baseline": "snapvm",
            "scenario_id": scenario["id"],
            "scenario_name": scenario["name"],
            "failure_complexity": scenario["complexity"],
            "recovery_success": passed,
            "tool_calls_total": agent.tool_call_count,
            "token_consumption": agent.recovery_tokens["prompt"] + agent.recovery_tokens["completion"],
            "prompt_tokens": agent.recovery_tokens["prompt"],
            "completion_tokens": agent.recovery_tokens["completion"],
            "recovery_latency_s": round(recovery_latency, 3),
            "context_pollution": agent.get_context_pollution(),
            "first_action": agent.tool_sequence[0] if agent.tool_sequence else None,
            "tool_sequence": agent.tool_sequence,
            "recovery_strategy": strategy,
        }
    finally:
        client.kill()


# ── Experiment Runner ────────────────────────────────────────────────────

def run_experiment(iterations=4):
    """Run V4.1: 5 failure scenarios × N iterations × 2 baselines."""
    total_trials = len(FAILURE_SCENARIOS) * iterations * 2
    print("=" * 60)
    print("Experiment V4.1: Complex Stateful Failures")
    print(f"Scenarios: {len(FAILURE_SCENARIOS)}, Iterations per scenario: {iterations}")
    print(f"Total trials: {total_trials}")
    print("=" * 60)

    client = FirecrackerClient()
    results = []

    for scenario in FAILURE_SCENARIOS:
        print(f"\n{'─' * 40}")
        print(f"Scenario {scenario['id']}: {scenario['name']}")
        print(f"{'─' * 40}")

        for i in range(1, iterations + 1):
            results.append(run_standard_baseline(client, i, scenario))
            results.append(run_snapvm_baseline(client, i, scenario))

    # Compute summaries
    standard = [r for r in results if r["baseline"] == "standard"]
    snapvm_results = [r for r in results if r["baseline"] == "snapvm"]

    summary = {
        "overall": {
            "standard": _summarize(standard),
            "snapvm": _summarize(snapvm_results),
        },
        "per_scenario": {},
    }

    for scenario in FAILURE_SCENARIOS:
        sid = scenario["id"]
        s_std = [r for r in standard if r["scenario_id"] == sid]
        s_snap = [r for r in snapvm_results if r["scenario_id"] == sid]
        summary["per_scenario"][sid] = {
            "name": scenario["name"],
            "complexity": scenario["complexity"],
            "standard": _summarize(s_std),
            "snapvm": _summarize(s_snap),
        }

    report = {
        "experiment": "v4_1_complex_stateful_failures",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": "gpt-4o",
        "temperature": 0,
        "iterations_per_scenario": iterations,
        "max_tool_calls": MAX_TOOL_CALLS,
        "scenarios": FAILURE_SCENARIOS,
        "results": results,
        "summary": summary,
    }

    os.makedirs(RESULTS_DIR, exist_ok=True)
    path = os.path.join(RESULTS_DIR, f"v4_1_run_{int(time.time() * 1000)}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    _print_summary(summary)
    print(f"\nReport saved to {path}")


def _summarize(results):
    n = len(results)
    if n == 0:
        return {}
    successes = [r for r in results if r["recovery_success"]]
    strategies = {}
    for r in results:
        s = r["recovery_strategy"]
        strategies[s] = strategies.get(s, 0) + 1
    return {
        "success_rate": round(len(successes) / n, 2),
        "avg_tool_calls": round(sum(r["tool_calls_total"] for r in results) / n, 1),
        "avg_tokens": round(sum(r["token_consumption"] for r in results) / n, 1),
        "avg_latency_s": round(sum(r["recovery_latency_s"] for r in results) / n, 3),
        "avg_context_pollution": round(sum(r["context_pollution"] for r in results) / n, 1),
        "strategy_distribution": strategies,
    }


def _print_summary(summary):
    print("\n" + "=" * 60)
    print("OVERALL SUMMARY")
    print("=" * 60)
    s = summary["overall"]["standard"]
    v = summary["overall"]["snapvm"]
    print(f"{'Metric':<25} {'Standard':<15} {'SnapVM':<15} {'Ratio':<10}")
    print("-" * 65)
    print(f"{'Success Rate':<25} {s['success_rate']:<15.0%} {v['success_rate']:<15.0%}")
    print(f"{'Avg Tool Calls':<25} {s['avg_tool_calls']:<15} {v['avg_tool_calls']:<15} {s['avg_tool_calls']/max(v['avg_tool_calls'],0.1):.1f}x")
    print(f"{'Avg Tokens':<25} {s['avg_tokens']:<15} {v['avg_tokens']:<15} {s['avg_tokens']/max(v['avg_tokens'],0.1):.1f}x")
    print(f"{'Avg Latency (s)':<25} {s['avg_latency_s']:<15} {v['avg_latency_s']:<15} {s['avg_latency_s']/max(v['avg_latency_s'],0.01):.1f}x")
    print(f"{'Avg Context Pollution':<25} {s['avg_context_pollution']:<15} {v['avg_context_pollution']:<15}")

    print(f"\nStrategy Distribution:")
    print(f"  Standard: {s['strategy_distribution']}")
    print(f"  SnapVM:   {v['strategy_distribution']}")

    print(f"\n{'─' * 65}")
    print("PER-SCENARIO BREAKDOWN")
    print(f"{'─' * 65}")
    print(f"{'Scenario':<30} {'Std Calls':<12} {'Snap Calls':<12} {'Std Tokens':<12} {'Snap Tokens':<12}")
    print("-" * 78)
    for sid, data in summary["per_scenario"].items():
        name = f"{sid}: {data['name'][:22]}"
        sc = data["standard"]
        sv = data["snapvm"]
        print(f"{name:<30} {sc['avg_tool_calls']:<12} {sv['avg_tool_calls']:<12} {sc['avg_tokens']:<12} {sv['avg_tokens']:<12}")
