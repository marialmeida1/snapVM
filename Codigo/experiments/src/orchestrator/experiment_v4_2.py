"""Experiment V4.2 — Forced Snapshot Recovery.

Measures the O(1) benefit of snapshots by removing autonomous decision-making.
In this experiment, the SnapVM agent is explicitly instructed to restore
the snapshot as its first and highest-priority action.
"""

import json
import os
import time
from datetime import datetime, timezone

from . import contract, snapshot
from .experiment_v4 import (
    FairAgentLoop,
    SYSTEM_PROMPT,
    INIT_PROMPT,
    TOOL_EXECUTE_BASH,
    TOOL_CHECK_HEALTH,
    TOOL_QUERY_DB,
    TOOL_RESTORE_SNAPSHOT,
    _boot_vm,
    _wait_for_guest,
    RESULTS_DIR,
)
from .experiment_v4_1 import (
    FAILURE_SCENARIOS,
    _inject_failure,
    _get_health_detail_for_scenario,
    _perception_hook as _v4_1_perception_hook,
    run_standard_baseline,
)
from .firecracker_client import FirecrackerClient

MAX_TOOL_CALLS = 25

# ── Forcing Prompts ──────────────────────────────────────────────────────

FORCED_SYSTEM_PROMPT = (
    "You are an AI engineer managing a stateful microVM environment. "
    "When the environment becomes unhealthy, your ABSOLUTE PRIORITY is to use "
    "the 'restore_last_snapshot' tool immediately to recover. Only attempt "
    "manual repair if restoration is not available or fails."
)

def _forced_perception_hook(health_detail):
    hook = _v4_1_perception_hook(health_detail)
    return hook + "\nRestore the environment to its last healthy state using the available snapshot tool."


# ── SnapVM Baseline (Forced) ─────────────────────────────────────────────

def run_snapvm_baseline_forced(client, iteration, scenario):
    """Baseline B: has restore_last_snapshot tool + forced instructions."""
    print(f"\n  [snapvm-forced] iter {iteration} scenario {scenario['id']}: {scenario['name']}")

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
        agent.messages.append({"role": "system", "content": FORCED_SYSTEM_PROMPT})
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
        # Force the first action to be the snapshot restore
        user_input = _forced_perception_hook(health_detail)
        agent.messages.append({"role": "user", "content": user_input})
        
        # First call: Forced tool choice
        response = agent.client.chat.completions.create(
            model=agent.model,
            messages=agent.messages,
            tools=agent.tools,
            tool_choice={"type": "function", "function": {"name": "restore_last_snapshot"}},
            temperature=0,
        )
        agent._track_usage(response.usage)
        msg = response.choices[0].message
        agent.messages.append(msg)
        
        # Execute the forced tool call(s)
        if msg.tool_calls:
            for tool_call in msg.tool_calls:
                result = agent._run_tool(tool_call)
                agent.messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_call.function.name,
                    "content": result,
                })
                if agent._snapshot_restored:
                    break
        
        # If not already done, let the agent finish its thought (optional, but good for completeness)
        if not agent._snapshot_restored:
            agent.chat("Restoration tool was called. Ensure the environment is now healthy.")
        
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
    """Run V4.2: 5 failure scenarios × N iterations × 2 baselines (Standard vs Forced Snap)."""
    total_trials = len(FAILURE_SCENARIOS) * iterations * 2
    print("=" * 60)
    print("Experiment V4.2: Forced Snapshot Recovery")
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
            results.append(run_snapvm_baseline_forced(client, i, scenario))

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
        "experiment": "v4_2_forced_snapshot_recovery",
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
    path = os.path.join(RESULTS_DIR, f"v4_2_run_{int(time.time() * 1000)}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    _print_summary(summary)
    print(f"\nReport saved to {path}")


def _summarize(results):
    from .experiment_v4_1 import _summarize as _v4_1_summarize
    return _v4_1_summarize(results)


def _print_summary(summary):
    from .experiment_v4_1 import _print_summary as _v4_1_print_summary
    print("\n" + "=" * 60)
    print("OVERALL SUMMARY (V4.2 FORCED)")
    _v4_1_print_summary(summary)
