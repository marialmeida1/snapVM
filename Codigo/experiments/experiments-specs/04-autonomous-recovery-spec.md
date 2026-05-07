# Experiment 4: Autonomous Agent Recovery — Fair Comparison

> Status: Spec Complete — Awaiting Implementation
> Author: Arthur Carvalho
> Date: 2026-05-07

## 1. Goal

Measure how an AI agent recovers from stateful failures when given **equal information** and **no coaching** in both baselines. The only variable is the **availability of the snapshot restore tool**.

This experiment addresses a limitation of V2: the Git baseline agent received a coaching prompt that told it what was wrong and what to fix. V4 removes that bias entirely.

---

## 2. Hypothesis

1. When `restore_last_snapshot` is available, the agent will use it as its primary recovery strategy (1–2 tool calls).
2. Without the snapshot tool, the agent will spend significantly more tokens diagnosing and repairing the failure manually.
3. The token/time gap will be **larger** than V2's 5.2x because the agent now bears the full uncoached diagnostic cost.

---

## 3. Baselines

| | Baseline A: Standard Agent | Baseline B: SnapVM Agent |
|---|---|---|
| Tools | `execute_bash`, `check_health`, `query_db` | `execute_bash`, `check_health`, `query_db`, `restore_last_snapshot` |
| Snapshot captured at milestone? | No | Yes |
| Recovery information | Perception Hook (user message) | Perception Hook (user message) |
| Coaching/hints | None | None |

The **only independent variable** is the presence of `restore_last_snapshot` in the tool list.

---

## 4. Methodology

### 4.1 System Prompt (identical for both baselines)

```
You are an AI engineer managing a stateful microVM environment running a Node.js API backed by PostgreSQL. Your goal is to keep the environment healthy. When the environment becomes unhealthy, use the tools available to you to restore it to a healthy state as efficiently as possible.
```

No mention of Git, snapshots, or recovery strategies.

### 4.2 Initialization Phase (identical for both baselines)

```
1. Orchestrator boots microVM
2. Orchestrator waits for guest to be reachable
3. Orchestrator sends agent initialization prompt:
   "Initialize the environment by creating a 'users' table in the database with columns: id (serial primary key)."
4. Agent acts (uses tools to create table)
5. Orchestrator verifies health contract → must be HEALTHY
6. [Baseline B only] Orchestrator captures snapshot (silent — agent is not informed)
```

### 4.3 Failure Injection (identical for both baselines)

```
7. Orchestrator executes: DROP TABLE users (bypassing agent)
8. Orchestrator verifies health contract → must be UNHEALTHY
```

### 4.4 Recovery Phase (identical for both baselines)

```
9. Orchestrator injects Perception Hook as a user message:

   "[ENVIRONMENT STATE]
   health_status: UNHEALTHY
   health_detail: relation "users" does not exist
   last_health_check: <timestamp>
   [/ENVIRONMENT STATE]

   The environment health has changed. Resolve the issue."

10. Agent acts autonomously using available tools
11. After each agent response (with or without tool calls):
    - If agent called no tools and declared done → orchestrator runs health check
    - If agent called tools → let it continue until it stops calling tools
12. Trial ends when:
    - Health check passes → SUCCESS
    - Max tool calls reached (15) → FAILED_MAX_CALLS
    - Agent explicitly says it cannot fix → FAILED_GAVE_UP
```

### 4.5 Post-Trial

```
13. Orchestrator runs final health check
14. Orchestrator records all metrics
15. Orchestrator kills VM
16. Fresh VM booted for next trial (no state carried over)
```

---

## 5. Metrics

### 5.1 Primary Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `recovery_success` | bool | Did health pass at end of trial? |
| `tool_calls_total` | int | Number of tool invocations during recovery phase |
| `token_consumption` | int | prompt_tokens + completion_tokens during recovery phase only |
| `recovery_latency_s` | float | Wall-clock from Perception Hook to HEALTHY |
| `context_pollution` | int | Token length of agent memory at trial end |

### 5.2 Secondary Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `first_action` | string | Name of the first tool the agent called after Perception Hook |
| `tool_sequence` | list[str] | Ordered list of tool names called during recovery |
| `recovery_strategy` | enum | `snapshot_restore`, `manual_repair`, `mixed`, `failed` |
| `diagnosis_calls` | int | Tool calls before the agent's first "fix" action |

### 5.3 Strategy Classification

- `snapshot_restore`: Agent called `restore_last_snapshot` and it succeeded
- `manual_repair`: Agent used `execute_bash`/`query_db` to fix the issue
- `mixed`: Agent tried restore (failed or not available), then fell back to manual
- `failed`: Agent did not achieve HEALTHY within limits

---

## 6. Controls

| Parameter | Value |
|-----------|-------|
| Model | GPT-4o |
| Temperature | 0 |
| Iterations per baseline | 20 (40 total) |
| Max tool calls per trial | 15 |
| Fresh agent context per trial | Yes (no memory between trials) |
| Failure type | `DROP TABLE users` |
| Health contract | `GET /health` → `SELECT 1 FROM users LIMIT 1` |
| VM config | 1 vCPU, 256 MiB RAM |

---

## 7. Tool Definitions

### 7.1 `execute_bash` (both baselines)

```json
{
  "name": "execute_bash",
  "description": "Execute a bash command inside the guest microVM via the API.",
  "parameters": {
    "type": "object",
    "properties": {
      "command": {"type": "string", "description": "The bash command to run."}
    },
    "required": ["command"]
  }
}
```

Response format:
```json
{"stdout": "...", "stderr": "...", "exit_code": 0}
```

### 7.2 `check_health` (both baselines)

```json
{
  "name": "check_health",
  "description": "Check the health status of the environment.",
  "parameters": {"type": "object", "properties": {}}
}
```

Response format:
```json
{"status": "HEALTHY|UNHEALTHY", "detail": "...", "checked_at": "..."}
```

### 7.3 `query_db` (both baselines)

```json
{
  "name": "query_db",
  "description": "Execute a SQL query against the PostgreSQL database.",
  "parameters": {
    "type": "object",
    "properties": {
      "sql": {"type": "string", "description": "The SQL query to execute."}
    },
    "required": ["sql"]
  }
}
```

Response format:
```json
{"result": [...], "error": null}
```
or
```json
{"result": null, "error": "relation \"users\" does not exist"}
```

### 7.4 `restore_last_snapshot` (Baseline B only)

```json
{
  "name": "restore_last_snapshot",
  "description": "Restore the environment to the last known healthy snapshot. This will revert all state (code, database, running processes) to the point when the snapshot was captured.",
  "parameters": {"type": "object", "properties": {}}
}
```

Response format (success):
```json
{"ok": true, "restore_latency_s": 0.184, "health_after_restore": "HEALTHY"}
```

---

## 8. Report Structure

Each run produces a JSON report:

```json
{
  "experiment": "v4_autonomous_recovery",
  "timestamp": "2026-05-07T...",
  "model": "gpt-4o",
  "temperature": 0,
  "iterations_per_baseline": 20,
  "results": [
    {
      "iteration": 1,
      "baseline": "standard",
      "recovery_success": true,
      "tool_calls_total": 5,
      "token_consumption": 2340,
      "prompt_tokens": 1800,
      "completion_tokens": 540,
      "recovery_latency_s": 8.42,
      "context_pollution": 890,
      "first_action": "check_health",
      "tool_sequence": ["check_health", "query_db", "query_db", "check_health", "check_health"],
      "recovery_strategy": "manual_repair",
      "diagnosis_calls": 2
    },
    {
      "iteration": 1,
      "baseline": "snapvm",
      "recovery_success": true,
      "tool_calls_total": 2,
      "token_consumption": 380,
      "prompt_tokens": 290,
      "completion_tokens": 90,
      "recovery_latency_s": 0.95,
      "context_pollution": 210,
      "first_action": "restore_last_snapshot",
      "tool_sequence": ["restore_last_snapshot", "check_health"],
      "recovery_strategy": "snapshot_restore",
      "diagnosis_calls": 0
    }
  ],
  "summary": {
    "standard": {
      "success_rate": 1.0,
      "avg_tool_calls": 5.2,
      "avg_tokens": 2680,
      "avg_latency_s": 7.8,
      "avg_context_pollution": 850,
      "strategy_distribution": {"manual_repair": 20}
    },
    "snapvm": {
      "success_rate": 1.0,
      "avg_tool_calls": 1.8,
      "avg_tokens": 360,
      "avg_latency_s": 0.9,
      "avg_context_pollution": 195,
      "strategy_distribution": {"snapshot_restore": 20}
    }
  }
}
```

---

## 9. Code Changes

### 9.1 New File: `src/orchestrator/experiment_v4.py`

The main experiment module. Contains:

- `FairAgentLoop` class (extends or replaces `AgentLoop`):
  - Configurable tool list (accepts list of tool names to register)
  - Tracks `tool_sequence` and `first_action`
  - Separates initialization phase tokens from recovery phase tokens
  - Max tool call limit with early termination

- `run_standard_baseline(client, iteration)`:
  - Boots VM
  - Runs initialization phase (agent creates table)
  - Verifies health
  - Injects failure
  - Injects Perception Hook as user message
  - Lets agent recover with `execute_bash`, `check_health`, `query_db`
  - Collects metrics
  - Kills VM

- `run_snapvm_baseline(client, iteration)`:
  - Same as above, but:
  - Captures snapshot after healthy milestone
  - Agent also has `restore_last_snapshot` tool
  - Tool implementation calls `snapshot.restore()` + `_wait_for_guest()` + `contract.verify_state()`

- `run_experiment(iterations=20)`:
  - Runs all iterations for both baselines
  - Computes summary statistics
  - Saves report

- CLI integration: adds `run-v4` subcommand to `main.py`

### 9.2 Modified File: `src/orchestrator/main.py`

Minimal change — add subcommand:

```python
run_v4_p = sub.add_parser("run-v4", help="Execute Experiment 4 (Fair Autonomous Recovery)")
run_v4_p.add_argument("--iterations", type=int, default=20)
```

Handler imports and calls `experiment_v4.run_experiment()`.

### 9.3 No Changes To

- `firecracker_client.py` — API wrapper unchanged
- `snapshot.py` — capture/restore logic unchanged
- `contract.py` — health probe unchanged
- `network.py` — TAP setup unchanged
- `server.js` — guest app unchanged
- `init.sh` / `Dockerfile` — guest image unchanged

### 9.4 New File: `docs/experiments/04-autonomous-recovery.md`

Experiment report (written after results are collected).

---

## 10. Implementation Order

1. Create `src/orchestrator/experiment_v4.py` with `FairAgentLoop` class
2. Implement `run_standard_baseline()` 
3. Implement `run_snapvm_baseline()`
4. Implement `run_experiment()` with reporting
5. Wire CLI subcommand in `main.py`
6. Test with 1 iteration per baseline (verify flow works)
7. Run full 20-iteration experiment
8. Write results doc

---

## 11. Differences from V2

| Aspect | V2 | V4 |
|--------|----|----|
| Recovery prompt | Coaching ("DB might be corrupted, fix it") | Neutral Perception Hook only |
| Tool availability | Different flows, not different tools | Same tools minus one (`restore_last_snapshot`) |
| Agent decision | None — orchestrator decides recovery path | Agent decides everything |
| `query_db` tool | Available but not central | Available in both baselines |
| What's measured | Cost of coached recovery | Cost of autonomous recovery under uncertainty |
| Independent variable | Entire recovery mechanism | Presence of one tool |
