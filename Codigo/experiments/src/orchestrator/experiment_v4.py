"""Experiment V4 — Autonomous Agent Recovery (Fair Comparison).

Measures agent recovery cost when the only variable is the availability
of the restore_last_snapshot tool.
"""

import json
import os
import time
from datetime import datetime, timezone

import psycopg2
import requests
import tiktoken
from dotenv import load_dotenv
from openai import OpenAI

from . import contract, snapshot
from .config import (
    DB_CONN,
    EXEC_URL,
    HEALTH_URL,
    KERNEL_PATH,
    RESULTS_DIR,
    ROOTFS_PATH,
    RUN_ROOTFS_PATH,
)
from .firecracker_client import FirecrackerClient

load_dotenv()

KERNEL = KERNEL_PATH
ROOTFS = ROOTFS_PATH
RUN_ROOTFS = RUN_ROOTFS_PATH
MAX_TOOL_CALLS = 15

SYSTEM_PROMPT = (
    "You are an AI engineer managing a stateful microVM environment running a "
    "Node.js API backed by PostgreSQL. Your goal is to keep the environment healthy. "
    "When the environment becomes unhealthy, use the tools available to you to restore "
    "it to a healthy state as efficiently as possible."
)

INIT_PROMPT = (
    "Initialize the environment by creating a 'users' table in the database "
    "with columns: id (serial primary key)."
)

# ── Tool Definitions ─────────────────────────────────────────────────────

TOOL_EXECUTE_BASH = {
    "type": "function",
    "function": {
        "name": "execute_bash",
        "description": "Execute a bash command inside the guest microVM via the API.",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "The bash command to run."}
            },
            "required": ["command"],
        },
    },
}

TOOL_CHECK_HEALTH = {
    "type": "function",
    "function": {
        "name": "check_health",
        "description": "Check the health status of the environment.",
        "parameters": {"type": "object", "properties": {}},
    },
}

TOOL_QUERY_DB = {
    "type": "function",
    "function": {
        "name": "query_db",
        "description": "Execute a SQL query against the PostgreSQL database.",
        "parameters": {
            "type": "object",
            "properties": {
                "sql": {"type": "string", "description": "The SQL query to execute."}
            },
            "required": ["sql"],
        },
    },
}

TOOL_RESTORE_SNAPSHOT = {
    "type": "function",
    "function": {
        "name": "restore_last_snapshot",
        "description": (
            "Restore the environment to the last known healthy snapshot. "
            "This will revert all state (code, database, running processes) "
            "to the point when the snapshot was captured."
        ),
        "parameters": {"type": "object", "properties": {}},
    },
}


# ── FairAgentLoop ────────────────────────────────────────────────────────

class FairAgentLoop:
    """Agent loop with configurable tools and per-phase token tracking."""

    def __init__(self, tools, restore_handler=None):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY must be set.")
        self.client = OpenAI(api_key=api_key)
        self.model = "gpt-4o"
        self.tools = tools
        self.restore_handler = restore_handler
        self.messages = []
        self.encoding = tiktoken.encoding_for_model(self.model)
        # Per-phase tracking
        self.init_tokens = {"prompt": 0, "completion": 0}
        self.recovery_tokens = {"prompt": 0, "completion": 0}
        self._phase = "init"
        self.tool_sequence = []
        self.tool_call_count = 0
        self._snapshot_restored = False

    def set_phase(self, phase):
        self._phase = phase

    def _track_usage(self, usage):
        bucket = self.recovery_tokens if self._phase == "recovery" else self.init_tokens
        bucket["prompt"] += usage.prompt_tokens
        bucket["completion"] += usage.completion_tokens

    def _run_tool(self, tool_call):
        name = tool_call.function.name
        args = json.loads(tool_call.function.arguments) if tool_call.function.arguments else {}

        if self._phase == "recovery":
            self.tool_sequence.append(name)
            self.tool_call_count += 1

        if name == "execute_bash":
            return self._tool_execute_bash(args.get("command", ""))
        elif name == "check_health":
            return self._tool_check_health()
        elif name == "query_db":
            return self._tool_query_db(args.get("sql", ""))
        elif name == "restore_last_snapshot":
            return self._tool_restore_snapshot()
        return json.dumps({"error": "unknown tool"})

    def _tool_execute_bash(self, command):
        try:
            resp = requests.post(
                EXEC_URL,
                json={"command": command}, timeout=10
            )
            data = resp.json()
            return json.dumps({
                "stdout": data.get("stdout", ""),
                "stderr": data.get("stderr", ""),
                "exit_code": 0 if not data.get("error") else 1
            })
        except Exception as e:
            return json.dumps({"stdout": "", "stderr": str(e), "exit_code": 1})

    def _tool_check_health(self):
        passed, detail = contract.verify_state()
        return json.dumps({
            "status": "HEALTHY" if passed else "UNHEALTHY",
            "detail": detail,
            "checked_at": datetime.now(timezone.utc).isoformat()
        })

    def _tool_query_db(self, sql):
        try:
            conn = psycopg2.connect(**DB_CONN)
            conn.autocommit = True
            with conn.cursor() as cur:
                cur.execute(sql)
                if cur.description:
                    result = cur.fetchall()
                else:
                    result = "OK"
            conn.close()
            return json.dumps({"result": result, "error": None})
        except Exception as e:
            return json.dumps({"result": None, "error": str(e)})

    def _tool_restore_snapshot(self):
        if self.restore_handler:
            result = self.restore_handler()
            if result.get("ok"):
                self._snapshot_restored = True
            return json.dumps(result)
        return json.dumps({"ok": False, "error": "no healthy snapshot available"})

    def chat(self, user_input):
        """Send a message and let the agent act until it stops or hits limits."""
        self.messages.append({"role": "user", "content": user_input})

        while True:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.messages,
                tools=self.tools,
                tool_choice="auto",
                temperature=0,
            )
            self._track_usage(response.usage)
            msg = response.choices[0].message
            self.messages.append(msg)

            if not msg.tool_calls:
                return msg.content

            for tool_call in msg.tool_calls:
                result = self._run_tool(tool_call)
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_call.function.name,
                    "content": result,
                })

                # End immediately on successful snapshot restore
                if self._snapshot_restored:
                    return result

            # Check max tool calls in recovery phase
            if self._phase == "recovery" and self.tool_call_count >= MAX_TOOL_CALLS:
                return None

    def get_context_pollution(self):
        text = ""
        for m in self.messages:
            if hasattr(m, "content") and m.content:
                text += m.content
            elif isinstance(m, dict) and m.get("content"):
                text += m["content"]
        return len(self.encoding.encode(text))


# ── Helpers ──────────────────────────────────────────────────────────────

def _db_exec(sql, retries=30, delay=2):
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
    raise RuntimeError(f"DB operation failed after retries: {last_error}")


def _wait_for_guest(retries=30, delay=2):
    for _ in range(retries):
        try:
            requests.get(HEALTH_URL, timeout=2)
            return True
        except requests.RequestException:
            time.sleep(delay)
    return False

def _boot_vm(client, track_dirty_pages=False):
    # Copy fresh rootfs for this trial to ensure isolation
    import shutil
    shutil.copy2(ROOTFS, RUN_ROOTFS)
    
    client.spawn()
    client.set_machine_config(vcpu_count=1, mem_size_mib=256, track_dirty_pages=track_dirty_pages)
    client.set_boot_source(KERNEL)
    client.set_rootfs(RUN_ROOTFS)
    client.set_network()
    client.start()
    if not _wait_for_guest():
        raise RuntimeError("Guest did not become reachable")


def _perception_hook():
    ts = datetime.now(timezone.utc).isoformat()
    return (
        "[ENVIRONMENT STATE]\n"
        "health_status: UNHEALTHY\n"
        "health_detail: relation \"users\" does not exist\n"
        f"last_health_check: {ts}\n"
        "[/ENVIRONMENT STATE]\n\n"
        "The environment health has changed. Resolve the issue."
    )


# ── Baselines ────────────────────────────────────────────────────────────

def run_standard_baseline(client, iteration):
    """Baseline A: Agent recovers with execute_bash, check_health, query_db only."""
    print(f"\n  [standard] iteration {iteration}")
    tools = [TOOL_EXECUTE_BASH, TOOL_CHECK_HEALTH, TOOL_QUERY_DB]
    agent = FairAgentLoop(tools=tools)

    try:
        _boot_vm(client)

        # Init phase
        agent.messages.append({"role": "system", "content": SYSTEM_PROMPT})
        agent.chat(INIT_PROMPT)

        passed, detail = contract.verify_state()
        if not passed:
            raise RuntimeError(f"Init failed health check: {detail}")

        # Inject failure
        _db_exec("DROP TABLE IF EXISTS users;")
        passed, detail = contract.verify_state()
        if passed:
            raise RuntimeError("Failure injection did not break health")

        # Recovery phase
        agent.set_phase("recovery")
        t0 = time.perf_counter()
        agent.chat(_perception_hook())
        recovery_latency = time.perf_counter() - t0

        # Final health check
        passed, detail = contract.verify_state()

        return {
            "iteration": iteration,
            "baseline": "standard",
            "recovery_success": passed,
            "tool_calls_total": agent.tool_call_count,
            "token_consumption": agent.recovery_tokens["prompt"] + agent.recovery_tokens["completion"],
            "prompt_tokens": agent.recovery_tokens["prompt"],
            "completion_tokens": agent.recovery_tokens["completion"],
            "recovery_latency_s": round(recovery_latency, 3),
            "context_pollution": agent.get_context_pollution(),
            "first_action": agent.tool_sequence[0] if agent.tool_sequence else None,
            "tool_sequence": agent.tool_sequence,
            "recovery_strategy": _classify_strategy(agent.tool_sequence, passed),
            "diagnosis_calls": _count_diagnosis_calls(agent.tool_sequence),
        }
    finally:
        client.kill()


def run_snapvm_baseline(client, iteration):
    """Baseline B: Agent has restore_last_snapshot tool available."""
    print(f"\n  [snapvm] iteration {iteration}")

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

        # Init phase
        agent.messages.append({"role": "system", "content": SYSTEM_PROMPT})
        agent.chat(INIT_PROMPT)

        passed, detail = contract.verify_state()
        if not passed:
            raise RuntimeError(f"Init failed health check: {detail}")

        # Capture snapshot (silent)
        snapshot.capture(client, snapshot_type="Full")

        # Inject failure
        _db_exec("DROP TABLE IF EXISTS users;")
        passed, detail = contract.verify_state()
        if passed:
            raise RuntimeError("Failure injection did not break health")

        # Recovery phase
        agent.set_phase("recovery")
        t0 = time.perf_counter()
        agent.chat(_perception_hook())
        recovery_latency = time.perf_counter() - t0

        # Final health check
        passed, detail = contract.verify_state()

        return {
            "iteration": iteration,
            "baseline": "snapvm",
            "recovery_success": passed,
            "tool_calls_total": agent.tool_call_count,
            "token_consumption": agent.recovery_tokens["prompt"] + agent.recovery_tokens["completion"],
            "prompt_tokens": agent.recovery_tokens["prompt"],
            "completion_tokens": agent.recovery_tokens["completion"],
            "recovery_latency_s": round(recovery_latency, 3),
            "context_pollution": agent.get_context_pollution(),
            "first_action": agent.tool_sequence[0] if agent.tool_sequence else None,
            "tool_sequence": agent.tool_sequence,
            "recovery_strategy": _classify_strategy(agent.tool_sequence, passed),
            "diagnosis_calls": _count_diagnosis_calls(agent.tool_sequence),
        }
    finally:
        client.kill()


# ── Strategy Classification ──────────────────────────────────────────────

def _classify_strategy(tool_sequence, success):
    if not success:
        return "failed"
    if "restore_last_snapshot" in tool_sequence:
        has_repair = any(t in ("execute_bash", "query_db") for t in tool_sequence
                        if tool_sequence.index(t) > tool_sequence.index("restore_last_snapshot"))
        return "mixed" if has_repair else "snapshot_restore"
    return "manual_repair"


def _count_diagnosis_calls(tool_sequence):
    """Count tool calls before the first 'fix' action (query_db with write or execute_bash)."""
    for i, name in enumerate(tool_sequence):
        if name in ("query_db", "execute_bash", "restore_last_snapshot"):
            return i
    return len(tool_sequence)


# ── Experiment Runner ────────────────────────────────────────────────────

def run_experiment(iterations=20):
    """Run the full V4 experiment and save report."""
    print("=" * 60)
    print("Experiment V4: Autonomous Agent Recovery (Fair Comparison)")
    print(f"Iterations per baseline: {iterations}")
    print("=" * 60)

    client = FirecrackerClient()
    results = []

    for i in range(1, iterations + 1):
        print(f"\n--- Iteration {i}/{iterations} ---")
        results.append(run_standard_baseline(client, i))
        results.append(run_snapvm_baseline(client, i))

    # Compute summary
    standard = [r for r in results if r["baseline"] == "standard"]
    snapvm = [r for r in results if r["baseline"] == "snapvm"]

    summary = {
        "standard": _summarize(standard),
        "snapvm": _summarize(snapvm),
    }

    report = {
        "experiment": "v4_autonomous_recovery",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": "gpt-4o",
        "temperature": 0,
        "iterations_per_baseline": iterations,
        "max_tool_calls": MAX_TOOL_CALLS,
        "results": results,
        "summary": summary,
    }

    # Save
    os.makedirs(RESULTS_DIR, exist_ok=True)
    path = os.path.join(RESULTS_DIR, f"v4_run_{int(time.time() * 1000)}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    # Print summary
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
        "success_rate": len(successes) / n,
        "avg_tool_calls": round(sum(r["tool_calls_total"] for r in results) / n, 1),
        "avg_tokens": round(sum(r["token_consumption"] for r in results) / n, 1),
        "avg_latency_s": round(sum(r["recovery_latency_s"] for r in results) / n, 3),
        "avg_context_pollution": round(sum(r["context_pollution"] for r in results) / n, 1),
        "strategy_distribution": strategies,
    }


def _print_summary(summary):
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"{'Metric':<25} {'Standard':<15} {'SnapVM':<15}")
    print("-" * 55)
    s, v = summary["standard"], summary["snapvm"]
    print(f"{'Success Rate':<25} {s['success_rate']:<15.0%} {v['success_rate']:<15.0%}")
    print(f"{'Avg Tool Calls':<25} {s['avg_tool_calls']:<15} {v['avg_tool_calls']:<15}")
    print(f"{'Avg Tokens':<25} {s['avg_tokens']:<15} {v['avg_tokens']:<15}")
    print(f"{'Avg Latency (s)':<25} {s['avg_latency_s']:<15} {v['avg_latency_s']:<15}")
    print(f"{'Avg Context Pollution':<25} {s['avg_context_pollution']:<15} {v['avg_context_pollution']:<15}")
    print(f"\nStrategy Distribution:")
    print(f"  Standard: {s['strategy_distribution']}")
    print(f"  SnapVM:   {v['strategy_distribution']}")
