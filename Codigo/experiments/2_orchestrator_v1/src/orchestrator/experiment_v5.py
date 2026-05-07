"""Experiment V5 — Multi-Step Task with Agent-Driven Checkpoints.

The agent performs a 6-step database migration. The orchestrator silently
injects failures between steps. Baseline A has no checkpoint tools;
Baseline B has save_checkpoint/restore_checkpoint. The agent decides
its own recovery strategy.
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

MAX_TOOL_CALLS = 40

SYSTEM_PROMPT = (
    "You are an AI engineer managing a stateful microVM environment running a "
    "Node.js API backed by PostgreSQL. You will be given a multi-step database "
    "migration task. Complete all steps in order. If the environment becomes "
    "unhealthy or a step fails unexpectedly, use the tools available to you to "
    "recover and continue. Your goal is to complete the entire migration successfully."
)

TASK_PROMPT = """Complete the following database migration steps in order:

1. Create a "products" table (id serial primary key, name text not null, price numeric not null)
2. Seed 100 rows of sample product data
3. Create a "categories" table (id serial primary key, name text not null) and add a category_id column to products as a foreign key
4. Populate the categories table with 5 categories and assign each product a category_id
5. Create an index on products(category_id)
6. Verify the final state: products table has 100 rows with valid category_id references

Execute each step and verify it works before moving to the next."""

# ── Checkpoint Tools ─────────────────────────────────────────────────────

TOOL_SAVE_CHECKPOINT = {
    "type": "function",
    "function": {
        "name": "save_checkpoint",
        "description": (
            "Save the current environment state as a checkpoint. Use this before "
            "performing risky operations (migrations, schema changes, bulk updates). "
            "You can restore to this point if something goes wrong."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "label": {"type": "string", "description": "A short label describing what state this checkpoint captures."}
            },
            "required": ["label"],
        },
    },
}

TOOL_RESTORE_CHECKPOINT = {
    "type": "function",
    "function": {
        "name": "restore_checkpoint",
        "description": (
            "Restore the environment to the last saved checkpoint. All changes "
            "made after the checkpoint will be reverted. Use this when something "
            "went wrong and you want to start fresh from a known-good state."
        ),
        "parameters": {"type": "object", "properties": {}},
    },
}

# ── Failure Injection ────────────────────────────────────────────────────

INJECTION_POINTS = {
    "after_seed": {
        "description": "Corrupt 20% of seeded product data",
        "trigger_after_tool_calls": 8,  # approximate: after seeding is done
    },
    "after_categories": {
        "description": "Drop the categories table",
        "trigger_after_tool_calls": 20,  # approximate: after category assignment
    },
}


def _inject_after_seed():
    """Corrupt product data — set some prices to NULL and names to empty."""
    try:
        conn = psycopg2.connect(**DB_CONN)
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("UPDATE products SET price = NULL WHERE id % 5 = 0;")
            cur.execute("UPDATE products SET name = '' WHERE id % 7 = 0;")
        conn.close()
        return True
    except Exception:
        return False


def _inject_after_categories():
    """Drop the categories table, breaking FK references."""
    try:
        conn = psycopg2.connect(**DB_CONN)
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("ALTER TABLE products DROP CONSTRAINT IF EXISTS products_category_id_fkey;")
            cur.execute("DROP TABLE IF EXISTS categories CASCADE;")
        conn.close()
        return True
    except Exception:
        return False


# ── Validation Contract ──────────────────────────────────────────────────

def _validate_final_state():
    """Check if the migration is fully complete."""
    checks = []
    try:
        conn = psycopg2.connect(**DB_CONN)
        conn.autocommit = True
        with conn.cursor() as cur:
            # Products table with correct columns
            cur.execute("SELECT id, name, price, category_id FROM products LIMIT 1;")
            checks.append(("products_schema", True))

            # At least 80 valid rows
            cur.execute("SELECT COUNT(*) FROM products WHERE name != '' AND price IS NOT NULL AND category_id IS NOT NULL;")
            count = cur.fetchone()[0]
            checks.append(("valid_rows", count >= 80))

            # Categories table exists
            cur.execute("SELECT COUNT(*) FROM categories;")
            cat_count = cur.fetchone()[0]
            checks.append(("categories_exist", cat_count >= 3))

            # Index exists
            cur.execute("SELECT 1 FROM pg_indexes WHERE tablename='products' AND indexdef LIKE '%category_id%';")
            has_index = cur.fetchone() is not None
            checks.append(("index_exists", has_index))

        conn.close()
    except Exception as e:
        checks.append(("connection", False))
        return False, f"validation error: {e}", checks

    all_passed = all(v for _, v in checks)
    detail = "; ".join(f"{k}={'OK' if v else 'FAIL'}" for k, v in checks)
    return all_passed, detail, checks


# ── Checkpoint-Aware Agent Loop ──────────────────────────────────────────

class CheckpointAgentLoop(FairAgentLoop):
    """Extends FairAgentLoop with checkpoint and injection logic."""

    def __init__(self, tools, client=None, enable_checkpoints=False):
        super().__init__(tools=tools, restore_handler=None)
        self._client = client
        self._enable_checkpoints = enable_checkpoints
        self.checkpoints_created = 0
        self.checkpoints_restored = 0
        self.checkpoint_labels = []
        self._injection_1_done = False
        self._injection_2_done = False
        self._injections_applied = []

    def _run_tool(self, tool_call):
        name = tool_call.function.name
        args = json.loads(tool_call.function.arguments) if tool_call.function.arguments else {}

        if self._phase == "task":
            self.tool_sequence.append(name)
            self.tool_call_count += 1
            self._maybe_inject()

        if name == "save_checkpoint":
            return self._tool_save_checkpoint(args.get("label", "unnamed"))
        elif name == "restore_checkpoint":
            return self._tool_restore_checkpoint()
        elif name == "execute_bash":
            return self._tool_execute_bash(args.get("command", ""))
        elif name == "check_health":
            return self._tool_check_health()
        elif name == "query_db":
            return self._tool_query_db(args.get("sql", ""))
        return json.dumps({"error": "unknown tool"})

    def _maybe_inject(self):
        """Inject failures at specific points in the agent's work."""
        if not self._injection_1_done and self.tool_call_count >= 8:
            if _inject_after_seed():
                self._injection_1_done = True
                self._injections_applied.append({
                    "type": "after_seed",
                    "at_tool_call": self.tool_call_count,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

        if not self._injection_2_done and self.tool_call_count >= 20:
            if _inject_after_categories():
                self._injection_2_done = True
                self._injections_applied.append({
                    "type": "after_categories",
                    "at_tool_call": self.tool_call_count,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

    def _tool_save_checkpoint(self, label):
        if not self._enable_checkpoints or not self._client:
            return json.dumps({"error": "checkpoint not available"})
        try:
            latency, storage = snapshot.capture(self._client, snapshot_type="Full")
            self.checkpoints_created += 1
            self.checkpoint_labels.append(label)
            return json.dumps({
                "ok": True,
                "label": label,
                "checkpoint_number": self.checkpoints_created,
                "capture_latency_s": round(latency, 3),
            })
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)})

    def _tool_restore_checkpoint(self):
        if not self._enable_checkpoints or not self._client:
            return json.dumps({"error": "checkpoint not available"})
        if self.checkpoints_created == 0:
            return json.dumps({"ok": False, "error": "no checkpoint saved"})
        try:
            t0 = time.perf_counter()
            snapshot.restore(self._client)
            if not _wait_for_guest():
                return json.dumps({"ok": False, "error": "VM not reachable after restore"})
            latency = time.perf_counter() - t0
            self.checkpoints_restored += 1
            # Reset injection flags — environment is back to checkpoint state
            self._injection_1_done = False
            self._injection_2_done = False
            return json.dumps({
                "ok": True,
                "restore_latency_s": round(latency, 3),
                "restored_to": self.checkpoint_labels[-1] if self.checkpoint_labels else "unknown",
            })
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)})

    def chat(self, user_input):
        """Chat with max tool call enforcement."""
        self.messages.append({"role": "user", "content": user_input})

        while True:
            response = self.client.chat.completions.create(
                model=self.model, messages=self.messages,
                tools=self.tools, tool_choice="auto", temperature=0,
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

            if self._phase == "task" and self.tool_call_count >= MAX_TOOL_CALLS:
                return None


# ── Baselines ────────────────────────────────────────────────────────────

def run_standard_baseline(client, iteration):
    """Baseline A: No checkpoint tools."""
    print(f"\n  [standard] iteration {iteration}")
    tools = [TOOL_EXECUTE_BASH, TOOL_CHECK_HEALTH, TOOL_QUERY_DB]
    agent = CheckpointAgentLoop(tools=tools, client=client, enable_checkpoints=False)

    try:
        _boot_vm(client)
        agent.messages.append({"role": "system", "content": SYSTEM_PROMPT})
        agent.set_phase("task")

        t0 = time.perf_counter()
        agent.chat(TASK_PROMPT)
        task_latency = time.perf_counter() - t0

        passed, detail, checks = _validate_final_state()

        return _build_result(agent, iteration, "standard", passed, detail, checks, task_latency)
    finally:
        client.kill()


def run_checkpoint_baseline(client, iteration):
    """Baseline B: Has save_checkpoint and restore_checkpoint."""
    print(f"\n  [checkpoint] iteration {iteration}")
    tools = [TOOL_EXECUTE_BASH, TOOL_CHECK_HEALTH, TOOL_QUERY_DB,
             TOOL_SAVE_CHECKPOINT, TOOL_RESTORE_CHECKPOINT]
    agent = CheckpointAgentLoop(tools=tools, client=client, enable_checkpoints=True)

    try:
        _boot_vm(client)
        agent.messages.append({"role": "system", "content": SYSTEM_PROMPT})
        agent.set_phase("task")

        t0 = time.perf_counter()
        agent.chat(TASK_PROMPT)
        task_latency = time.perf_counter() - t0

        passed, detail, checks = _validate_final_state()

        return _build_result(agent, iteration, "checkpoint", passed, detail, checks, task_latency)
    finally:
        client.kill()


def _build_result(agent, iteration, baseline, passed, detail, checks, task_latency):
    return {
        "iteration": iteration,
        "baseline": baseline,
        "task_completed": passed,
        "validation_detail": detail,
        "validation_checks": {k: v for k, v in checks},
        "tool_calls_total": agent.tool_call_count,
        "token_consumption": agent.recovery_tokens["prompt"] + agent.recovery_tokens["completion"],
        "prompt_tokens": agent.recovery_tokens["prompt"],
        "completion_tokens": agent.recovery_tokens["completion"],
        "task_latency_s": round(task_latency, 3),
        "context_pollution": agent.get_context_pollution(),
        "tool_sequence": agent.tool_sequence,
        "checkpoints_created": agent.checkpoints_created,
        "checkpoints_restored": agent.checkpoints_restored,
        "checkpoint_labels": agent.checkpoint_labels,
        "injections_applied": agent._injections_applied,
        "recovery_strategy": _classify(agent, passed),
    }


def _classify(agent, passed):
    if not passed:
        return "failed"
    if agent.checkpoints_restored > 0:
        return "checkpoint_restore"
    if agent.checkpoints_created > 0:
        return "checkpoint_unused"
    return "manual_only"


# ── Experiment Runner ────────────────────────────────────────────────────

def run_experiment(iterations=10):
    """Run V5: multi-step task with injected failures."""
    total = iterations * 2
    print("=" * 60)
    print("Experiment V5: Multi-Step Task with Agent-Driven Checkpoints")
    print(f"Iterations per baseline: {iterations} ({total} total trials)")
    print("=" * 60)

    client = FirecrackerClient()
    results = []

    for i in range(1, iterations + 1):
        print(f"\n--- Iteration {i}/{iterations} ---")
        results.append(run_standard_baseline(client, i))
        results.append(run_checkpoint_baseline(client, i))

    standard = [r for r in results if r["baseline"] == "standard"]
    checkpoint = [r for r in results if r["baseline"] == "checkpoint"]

    summary = {
        "standard": _summarize(standard),
        "checkpoint": _summarize(checkpoint),
    }

    report = {
        "experiment": "v5_agent_driven_checkpoints",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": "gpt-4o",
        "temperature": 0,
        "iterations_per_baseline": iterations,
        "max_tool_calls": MAX_TOOL_CALLS,
        "injection_points": ["after_seed (tool_call ~8)", "after_categories (tool_call ~20)"],
        "results": results,
        "summary": summary,
    }

    os.makedirs(RESULTS_DIR, exist_ok=True)
    path = os.path.join(RESULTS_DIR, f"v5_run_{int(time.time() * 1000)}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    _print_summary(summary)
    print(f"\nReport saved to {path}")


def _summarize(results):
    n = len(results)
    if n == 0:
        return {}
    completed = [r for r in results if r["task_completed"]]
    strategies = {}
    for r in results:
        s = r["recovery_strategy"]
        strategies[s] = strategies.get(s, 0) + 1
    return {
        "completion_rate": round(len(completed) / n, 2),
        "avg_tool_calls": round(sum(r["tool_calls_total"] for r in results) / n, 1),
        "avg_tokens": round(sum(r["token_consumption"] for r in results) / n, 1),
        "avg_latency_s": round(sum(r["task_latency_s"] for r in results) / n, 3),
        "avg_context_pollution": round(sum(r["context_pollution"] for r in results) / n, 1),
        "avg_checkpoints_created": round(sum(r["checkpoints_created"] for r in results) / n, 1),
        "avg_checkpoints_restored": round(sum(r["checkpoints_restored"] for r in results) / n, 1),
        "strategy_distribution": strategies,
    }


def _print_summary(summary):
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    s, c = summary["standard"], summary["checkpoint"]
    print(f"{'Metric':<25} {'Standard':<15} {'Checkpoint':<15}")
    print("-" * 55)
    print(f"{'Completion Rate':<25} {s['completion_rate']:<15.0%} {c['completion_rate']:<15.0%}")
    print(f"{'Avg Tool Calls':<25} {s['avg_tool_calls']:<15} {c['avg_tool_calls']:<15}")
    print(f"{'Avg Tokens':<25} {s['avg_tokens']:<15} {c['avg_tokens']:<15}")
    print(f"{'Avg Latency (s)':<25} {s['avg_latency_s']:<15} {c['avg_latency_s']:<15}")
    print(f"{'Avg Context Pollution':<25} {s['avg_context_pollution']:<15} {c['avg_context_pollution']:<15}")
    print(f"{'Avg Checkpoints Created':<25} {'-':<15} {c['avg_checkpoints_created']:<15}")
    print(f"{'Avg Checkpoints Restored':<25} {'-':<15} {c['avg_checkpoints_restored']:<15}")
    print(f"\nStrategy Distribution:")
    print(f"  Standard:   {s['strategy_distribution']}")
    print(f"  Checkpoint: {c['strategy_distribution']}")
