# Experiment 4.1: Complex Stateful Failures — Spec

> Status: Awaiting Execution
> Author: Arthur Carvalho
> Date: 2026-05-07

## 1. Goal

Demonstrate that snapshot restore cost is **constant** regardless of failure complexity, while manual agent recovery cost **scales linearly** with the number of issues to diagnose and fix.

## 2. Hypothesis

1. SnapVM recovery remains ~1-2 tool calls and ~400-800 tokens across all failure types.
2. Standard agent recovery scales to 8-15+ tool calls and 4000-8000+ tokens for multi-layered failures.
3. The token gap widens from V4's 1.7x to **5-10x** with complex failures.
4. Standard agent success rate drops below 100% for the hardest scenarios (F4, F5).

## 3. Failure Scenarios

| ID | Name | Injection | Why it's hard |
|----|------|-----------|---------------|
| F1 | multi_table_corruption | `DROP TABLE users` + create rogue table with corrupt data | Agent must discover multiple problems, fix in correct order |
| F2 | process_and_config | Kill Node.js process + drop users table | Agent must diagnose dead server (no /exec available) AND fix DB |
| F3 | schema_and_data_corruption | Alter column types + insert invalid data | Agent must figure out original schema, fix types, clean bad rows |
| F4 | permissions_and_schema | `DROP TABLE users` + revoke CREATE on public schema | Agent hits permission errors when trying to fix, must diagnose auth first |
| F5 | cascading_service_failure | Truncate table + kill PostgreSQL + remove PG socket | Multi-service cascade — must restart PG, then fix data |

### Health Check Behavior

The `/health` endpoint only reports the **first error it encounters** (e.g., "connection refused" for F5, "relation users does not exist" for F1). The agent must discover additional problems through investigation.

## 4. Methodology

Same fair design as V4:
- Identical system prompt (no coaching)
- Perception Hook as user message (only shows first error)
- Baseline A: `execute_bash`, `check_health`, `query_db`
- Baseline B: same + `restore_last_snapshot`
- Fresh agent context per trial

### Parameters

| Parameter | Value |
|-----------|-------|
| Model | GPT-4o |
| Temperature | 0 |
| Scenarios | 5 |
| Iterations per scenario | 4 |
| Total trials | 40 (5 × 4 × 2 baselines) |
| Max tool calls | 25 |

## 5. Metrics

Same as V4 plus:
- `scenario_id` / `scenario_name` — which failure was injected
- `failure_complexity` — number of distinct issues (2 or 3)
- Per-scenario breakdown in summary

## 6. Report Structure

```json
{
  "experiment": "v4_1_complex_stateful_failures",
  "summary": {
    "overall": { "standard": {...}, "snapvm": {...} },
    "per_scenario": {
      "F1": { "standard": {...}, "snapvm": {...} },
      ...
    }
  }
}
```

## 7. Code

- **New file**: `src/orchestrator/experiment_v4_1.py`
- **Modified**: `src/orchestrator/main.py` (adds `run-v4.1` subcommand)
- **Reuses**: `FairAgentLoop` and tool definitions from `experiment_v4.py`

## 8. Usage

```bash
python3 -m src.orchestrator.main run-v4.1 --iterations 4
```

## 9. Expected Outcome

The per-scenario breakdown should show SnapVM cost flat (~1-2 calls, ~500 tokens) while Standard cost increases with complexity, producing the "scissors chart" that proves snapshot value scales with failure severity.
