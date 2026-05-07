"""Experiment V6 — Exploration Branching (Speculative Execution).

An ambiguous debugging task with multiple root causes and red herrings.
Baseline A explores sequentially (failed attempts pollute context).
Baseline B can branch/restore (failed attempts are cleanly reverted).
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
    TOOL_EXECUTE_BASH,
    TOOL_CHECK_HEALTH,
    TOOL_QUERY_DB,
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

MAX_TOOL_CALLS = 30

SYSTEM_PROMPT = (
    "You are an AI engineer debugging a stateful microVM environment running a "
    "Node.js API backed by PostgreSQL. The health check is failing. Your goal is "
    "to diagnose the root cause(s) and fix the environment so the health check passes. "
    "There may be multiple issues. Be methodical in your investigation."
)

TASK_PROMPT = (
    "[ENVIRONMENT STATE]\n"
    "health_status: UNHEALTHY\n"
    "health_detail: health probe timed out\n"
    "last_known_healthy: 30 minutes ago\n"
    "recent_changes: multiple modifications were made since last healthy state\n"
    "[/ENVIRONMENT STATE]\n\n"
    "The API health check is failing with a timeout. The last known working state "
    "was 30 minutes ago. Multiple changes were made since then. Diagnose and fix the issue."
)

# ── Branching Tools ──────────────────────────────────────────────────────

TOOL_SAVE_BRANCH = {
    "type": "function",
    "function": {
        "name": "save_branch_point",
        "description": (
            "Save the current environment state as a branch point. Use this before "
            "attempting a fix you're not sure about. If the fix doesn't work, you can "
            "restore to this point and try a different approach with a clean slate."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "hypothesis": {
                    "type": "string",
                    "description": "What you think the problem is and what fix you're about to try."
                }
            },
            "required": ["hypothesis"],
        },
    },
}

TOOL_RESTORE_BRANCH = {
    "type": "function",
    "function": {
        "name": "restore_branch_point",
        "description": (
            "Abandon the current fix attempt and restore the environment to the last "
            "branch point. The environment will be exactly as it was before your attempted "
            "fix. Use this when your current approach isn't working."
        ),
        "parameters": {"type": "object", "properties": {}},
    },
}

# ── Ambiguous Failure Setup ──────────────────────────────────────────────

def _setup_broken_environment():
    """Inject multi-cause failure with red herrings.

    Root causes (both must be fixed):
      1. Index on users dropped + statement_timeout set to 50ms
         (makes SELECT 1 FROM users timeout on unindexed scan)
      2. Users table has 10000 rows of junk (makes unindexed query slow)

    Red herrings:
      1. A recently-modified config comment in server.js (irrelevant)
      2. A suspicious _migrations_log table with recent timestamps
      3. PostgreSQL log warnings about checkpoint segments (unrelated)
    """
    # Root cause 1: drop index and set aggressive timeout
    _db_exec("DROP INDEX IF EXISTS users_pkey CASCADE;")
    # Recreate table without primary key to remove implicit index
    _db_exec("DROP TABLE IF EXISTS users;")
    _db_exec("CREATE TABLE users (id integer, name text);")
    # Root cause 2: flood with rows to make unindexed scan slow
    _db_exec("INSERT INTO users SELECT g, 'user_' || g FROM generate_series(1, 10000) g;")
    # Set statement timeout so the health query times out
    _db_exec("ALTER DATABASE app_db SET statement_timeout = '50ms';")

    # Red herring 1: modify server.js comment via exec endpoint
    try:
        requests.post(f"http://{GUEST_IP}:3000/exec", json={
            "command": "sed -i '1i // Modified: config update 2026-05-07 — pool tuning' /opt/app/server.js"
        }, timeout=5)
    except Exception:
        pass

    # Red herring 2: suspicious table
    _db_exec("""
        CREATE TABLE IF NOT EXISTS _migrations_log (
            id serial, migration text, applied_at timestamp default now()
        );
        INSERT INTO _migrations_log (migration) VALUES
            ('20260507_alter_pool_size'), ('20260507_update_indexes');
    """)

    # Red herring 3: generate PG log noise
    _db_exec("SET log_min_messages = 'warning';")
    try:
        _db_exec("CHECKPOINT;")
    except Exception:
        pass


def _verify_health_fixed():
    """Check if health endpoint responds successfully (not timeout)."""
    try:
        r = requests.get(f"http://{GUEST_IP}:3000/health", timeout=5)
        if r.status_code == 200:
            body = r.json()
            return body.get("status") == "healthy", f"status={body.get('status')}"
        return False, f"http {r.status_code}"
    except requests.Timeout:
        return False, "timeout"
    except requests.ConnectionError:
        return False, "connection refused"
    except Exception as e:
        return False, str(e)


# ── Branching Agent Loop ─────────────────────────────────────────────────

class BranchingAgentLoop(FairAgentLoop):
    """Extends FairAgentLoop with branch point save/restore."""

    def __init__(self, tools, client=None, enable_branching=False):
        super().__init__(tools=tools, restore_handler=None)
        self._client = client
        self._enable_branching = enable_branching
        self.branches_created = 0
        self.branches_restored = 0
        self.hypotheses = []

    def _run_tool(self, tool_call):
        name = tool_call.function.name
        args = json.loads(tool_call.function.arguments) if tool_call.function.arguments else {}

        if self._phase == "recovery":
            self.tool_sequence.append(name)
            self.tool_call_count += 1

        if name == "save_branch_point":
            return self._tool_save_branch(args.get("hypothesis", ""))
        elif name == "restore_branch_point":
            return self._tool_restore_branch()
        elif name == "execute_bash":
            return self._tool_execute_bash(args.get("command", ""))
        elif name == "check_health":
            return self._tool_check_health()
        elif name == "query_db":
            return self._tool_query_db(args.get("sql", ""))
        return json.dumps({"error": "unknown tool"})

    def _tool_check_health(self):
        """Override to use the timeout-aware check."""
        passed, detail = _verify_health_fixed()
        return json.dumps({
            "status": "HEALTHY" if passed else "UNHEALTHY",
            "detail": detail,
            "checked_at": datetime.now(timezone.utc).isoformat()
        })

    def _tool_save_branch(self, hypothesis):
        if not self._enable_branching or not self._client:
            return json.dumps({"error": "branching not available"})
        try:
            latency, _ = snapshot.capture(self._client, snapshot_type="Full")
            self.branches_created += 1
            self.hypotheses.append(hypothesis)
            return json.dumps({
                "ok": True,
                "hypothesis": hypothesis,
                "branch_number": self.branches_created,
                "capture_latency_s": round(latency, 3),
            })
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)})

    def _tool_restore_branch(self):
        if not self._enable_branching or not self._client:
            return json.dumps({"error": "branching not available"})
        if self.branches_created == 0:
            return json.dumps({"ok": False, "error": "no branch point saved"})
        try:
            t0 = time.perf_counter()
            snapshot.restore(self._client)
            if not _wait_for_guest():
                return json.dumps({"ok": False, "error": "VM not reachable after restore"})
            latency = time.perf_counter() - t0
            self.branches_restored += 1
            return json.dumps({
                "ok": True,
                "restore_latency_s": round(latency, 3),
                "message": "Environment restored. Previous fix attempt reverted.",
            })
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)})

    def chat(self, user_input):
        self.messages.append({"role": "user", "content": user_input})
        while True:
            response = self.client.chat.completions.create(
                model=self.model, messages=self.messages,
                tools=self.tools, tool_choice="auto", temperature=0.3,
            )
            self._track_usage(response.usage)
            msg = response.choices[0].message
            self.messages.append(msg)

            if not msg.tool_calls:
                return msg.content

            for tc in msg.tool_calls:
                result = self._run_tool(tc)
                self.messages.append({
                    "role": "tool", "tool_call_id": tc.id,
                    "name": tc.function.name, "content": result,
                })

            if self._phase == "recovery" and self.tool_call_count >= MAX_TOOL_CALLS:
                return None


# ── Baselines ────────────────────────────────────────────────────────────

def run_standard_baseline(client, iteration):
    """Baseline A: Sequential exploration, no branching."""
    print(f"\n  [standard] iteration {iteration}")
    tools = [TOOL_EXECUTE_BASH, TOOL_CHECK_HEALTH, TOOL_QUERY_DB]
    agent = BranchingAgentLoop(tools=tools, client=client, enable_branching=False)

    try:
        _boot_vm(client)

        # Create healthy state first
        _db_exec("CREATE TABLE IF NOT EXISTS users (id serial PRIMARY KEY);")
        passed, _ = _verify_health_fixed()
        if not passed:
            raise RuntimeError("Could not establish healthy baseline")

        # Now break it
        _setup_broken_environment()
        passed, _ = _verify_health_fixed()
        if passed:
            raise RuntimeError("Failure injection did not break health")

        # Agent debugs
        agent.messages.append({"role": "system", "content": SYSTEM_PROMPT})
        agent.set_phase("recovery")

        t0 = time.perf_counter()
        agent.chat(TASK_PROMPT)
        recovery_latency = time.perf_counter() - t0

        passed, detail = _verify_health_fixed()

        return _build_result(agent, iteration, "standard", passed, detail, recovery_latency)
    finally:
        client.kill()


def run_branching_baseline(client, iteration):
    """Baseline B: Can save/restore branch points."""
    print(f"\n  [branching] iteration {iteration}")
    tools = [TOOL_EXECUTE_BASH, TOOL_CHECK_HEALTH, TOOL_QUERY_DB,
             TOOL_SAVE_BRANCH, TOOL_RESTORE_BRANCH]
    agent = BranchingAgentLoop(tools=tools, client=client, enable_branching=True)

    try:
        _boot_vm(client)

        # Create healthy state
        _db_exec("CREATE TABLE IF NOT EXISTS users (id serial PRIMARY KEY);")
        passed, _ = _verify_health_fixed()
        if not passed:
            raise RuntimeError("Could not establish healthy baseline")

        # Now break it
        _setup_broken_environment()
        passed, _ = _verify_health_fixed()
        if passed:
            raise RuntimeError("Failure injection did not break health")

        # Agent debugs
        agent.messages.append({"role": "system", "content": SYSTEM_PROMPT})
        agent.set_phase("recovery")

        t0 = time.perf_counter()
        agent.chat(TASK_PROMPT)
        recovery_latency = time.perf_counter() - t0

        passed, detail = _verify_health_fixed()

        return _build_result(agent, iteration, "branching", passed, detail, recovery_latency)
    finally:
        client.kill()


def _build_result(agent, iteration, baseline, passed, detail, recovery_latency):
    # Classify which root causes were addressed
    seq_str = " ".join(agent.tool_sequence)
    found_timeout = any("statement_timeout" in str(m.get("content", ""))
                        for m in agent.messages if isinstance(m, dict))
    found_index = any("CREATE INDEX" in str(m.get("content", "")).upper() or
                      "PRIMARY KEY" in str(m.get("content", "")).upper()
                      for m in agent.messages if isinstance(m, dict))

    return {
        "iteration": iteration,
        "baseline": baseline,
        "recovery_success": passed,
        "health_detail": detail,
        "tool_calls_total": agent.tool_call_count,
        "token_consumption": agent.recovery_tokens["prompt"] + agent.recovery_tokens["completion"],
        "prompt_tokens": agent.recovery_tokens["prompt"],
        "completion_tokens": agent.recovery_tokens["completion"],
        "recovery_latency_s": round(recovery_latency, 3),
        "context_pollution": agent.get_context_pollution(),
        "first_action": agent.tool_sequence[0] if agent.tool_sequence else None,
        "tool_sequence": agent.tool_sequence,
        "branches_created": getattr(agent, "branches_created", 0),
        "branches_restored": getattr(agent, "branches_restored", 0),
        "hypotheses": getattr(agent, "hypotheses", []),
        "found_timeout_issue": found_timeout,
        "found_index_issue": found_index,
        "recovery_strategy": _classify(agent, passed),
    }


def _classify(agent, passed):
    if not passed:
        return "failed"
    if agent.branches_restored > 0:
        return "branching_exploration"
    if agent.branches_created > 0:
        return "branching_unused"
    return "sequential"


# ── Experiment Runner ────────────────────────────────────────────────────

def run_experiment(iterations=15):
    """Run V6: ambiguous debugging with branching."""
    total = iterations * 2
    print("=" * 60)
    print("Experiment V6: Exploration Branching (Speculative Execution)")
    print(f"Iterations per baseline: {iterations} ({total} total trials)")
    print("=" * 60)

    client = FirecrackerClient()
    results = []

    for i in range(1, iterations + 1):
        print(f"\n--- Iteration {i}/{iterations} ---")
        results.append(run_standard_baseline(client, i))
        results.append(run_branching_baseline(client, i))

    standard = [r for r in results if r["baseline"] == "standard"]
    branching = [r for r in results if r["baseline"] == "branching"]

    summary = {
        "standard": _summarize(standard),
        "branching": _summarize(branching),
    }

    report = {
        "experiment": "v6_exploration_branching",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": "gpt-4o",
        "temperature": 0.3,
        "iterations_per_baseline": iterations,
        "max_tool_calls": MAX_TOOL_CALLS,
        "root_causes": ["dropped index + 10k rows (slow scan)", "statement_timeout = 50ms"],
        "red_herrings": ["modified server.js comment", "_migrations_log table", "PG checkpoint warnings"],
        "results": results,
        "summary": summary,
    }

    os.makedirs(RESULTS_DIR, exist_ok=True)
    path = os.path.join(RESULTS_DIR, f"v6_run_{int(time.time() * 1000)}.json")
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
    found_both = sum(1 for r in results if r["found_timeout_issue"] and r["found_index_issue"])
    return {
        "success_rate": round(len(successes) / n, 2),
        "avg_tool_calls": round(sum(r["tool_calls_total"] for r in results) / n, 1),
        "avg_tokens": round(sum(r["token_consumption"] for r in results) / n, 1),
        "avg_latency_s": round(sum(r["recovery_latency_s"] for r in results) / n, 3),
        "avg_context_pollution": round(sum(r["context_pollution"] for r in results) / n, 1),
        "avg_branches_created": round(sum(r["branches_created"] for r in results) / n, 1),
        "avg_branches_restored": round(sum(r["branches_restored"] for r in results) / n, 1),
        "found_both_causes_rate": round(found_both / n, 2),
        "strategy_distribution": strategies,
    }


def _print_summary(summary):
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    s, b = summary["standard"], summary["branching"]
    print(f"{'Metric':<30} {'Standard':<15} {'Branching':<15}")
    print("-" * 60)
    print(f"{'Success Rate':<30} {s['success_rate']:<15.0%} {b['success_rate']:<15.0%}")
    print(f"{'Avg Tool Calls':<30} {s['avg_tool_calls']:<15} {b['avg_tool_calls']:<15}")
    print(f"{'Avg Tokens':<30} {s['avg_tokens']:<15} {b['avg_tokens']:<15}")
    print(f"{'Avg Latency (s)':<30} {s['avg_latency_s']:<15} {b['avg_latency_s']:<15}")
    print(f"{'Avg Context Pollution':<30} {s['avg_context_pollution']:<15} {b['avg_context_pollution']:<15}")
    print(f"{'Found Both Root Causes':<30} {s['found_both_causes_rate']:<15.0%} {b['found_both_causes_rate']:<15.0%}")
    print(f"{'Avg Branches Created':<30} {'-':<15} {b['avg_branches_created']:<15}")
    print(f"{'Avg Branches Restored':<30} {'-':<15} {b['avg_branches_restored']:<15}")
    print(f"\nStrategy Distribution:")
    print(f"  Standard:  {s['strategy_distribution']}")
    print(f"  Branching: {b['strategy_distribution']}")
