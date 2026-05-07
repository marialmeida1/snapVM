# Experiment 6: Exploration Branching (Speculative Execution) — Spec

> Status: Planned
> Author: Arthur Carvalho
> Date: 2026-05-07

## 1. Goal

Prove that snapshots enable a fundamentally different **reasoning pattern** — speculative execution. Agents with snapshot branching can explore multiple solution strategies without accumulating context pollution from failed attempts, leading to faster and cheaper problem resolution.

## 2. Hypothesis

1. Snapshot-enabled agents will explore more strategies per problem (higher exploration breadth).
2. Failed exploration branches don't pollute context — the agent "forgets" bad paths via restore.
3. Standard agents get progressively worse at finding solutions as failed attempts fill their context window.
4. Snapshot-enabled agents find correct solutions in fewer total tokens despite trying more approaches.

## 3. The Problem

An **ambiguous debugging task** where the correct fix is non-obvious and multiple approaches seem plausible:

**Scenario:** The `/health` endpoint returns 500. The agent is told only:

```
"The API health check is failing. The last known working state was 30 minutes ago.
Multiple changes were made since then. Diagnose and fix the issue."
```

**Actual root cause (unknown to agent):** A combination of:
1. A missing environment variable (`DB_POOL_SIZE`) that causes connection exhaustion under the new schema
2. A corrupted index that makes the health query timeout

**Red herrings planted:**
- A recently modified config file (irrelevant change)
- A new table that looks suspicious but is fine
- PostgreSQL logs showing warnings (unrelated to the actual issue)

The agent must investigate, form hypotheses, try fixes, and verify.

## 4. Baselines

| | Baseline A: Standard Agent | Baseline B: Branching Agent |
|---|---|---|
| Tools | `execute_bash`, `check_health`, `query_db` | Same + `save_branch_point`, `restore_branch_point` |
| Failed fix behavior | Stays in context, agent must reason around it | Restored away — context is clean for next attempt |
| Exploration strategy | Sequential (try A, if fail try B with A's noise in context) | Branching (try A, restore, try B with clean context) |

### New Tools (Baseline B only)

**`save_branch_point`**
```json
{
  "name": "save_branch_point",
  "description": "Save the current environment state as a branch point. Use this before attempting a fix you're not sure about. If the fix doesn't work, you can restore to this point and try a different approach with a clean slate.",
  "parameters": {
    "type": "object",
    "properties": {
      "hypothesis": {"type": "string", "description": "What you think the problem is and what fix you're about to try."}
    },
    "required": ["hypothesis"]
  }
}
```

**`restore_branch_point`**
```json
{
  "name": "restore_branch_point",
  "description": "Abandon the current fix attempt and restore the environment to the last branch point. The environment will be exactly as it was before your attempted fix. Use this when your current approach isn't working.",
  "parameters": {"type": "object", "properties": {}}
}
```

## 5. Methodology

### Failure Setup (before agent starts)

The orchestrator prepares the broken environment:
1. Boot VM, create healthy state (users table, working API)
2. Inject the multi-cause failure:
   - Drop the index on users table
   - Set `statement_timeout = '50ms'` in PostgreSQL (makes unindexed queries fail)
   - Create a red-herring table (`_migrations_log`) with recent timestamps
   - Add a modified (but irrelevant) comment to server.js
3. Verify health fails
4. Capture snapshot of this broken state (so both baselines start from identical broken state)

### Agent Flow

```
1. System prompt (identical for both baselines)
2. Perception Hook: "UNHEALTHY — health probe timed out"
3. Agent investigates and attempts fixes
4. Trial ends when:
   - Health passes → SUCCESS
   - Max tool calls (30) → FAILED
   - Agent gives up → FAILED
```

### Key Difference

- **Baseline A**: Every failed fix attempt stays in the environment AND in the agent's context. The agent must mentally track "I already tried X and it didn't work."
- **Baseline B**: After a failed fix, the agent restores to branch point. The environment is clean AND the agent's context only contains the hypothesis that failed (not the messy execution details).

### Parameters

| Parameter | Value |
|-----------|-------|
| Model | GPT-4o |
| Temperature | 0.3 (slightly higher to encourage exploration diversity) |
| Iterations | 15 per baseline (30 total) |
| Max tool calls | 30 |
| Root causes | 2 (missing index + statement timeout) |
| Red herrings | 3 (config file, rogue table, PG warnings) |

## 6. Metrics

All V4 metrics plus:

| Metric | Description |
|--------|-------------|
| `branches_created` | Number of branch points saved (Baseline B) |
| `branches_abandoned` | Number of times agent restored (failed approaches) |
| `hypotheses_tested` | Distinct fix strategies attempted |
| `red_herrings_investigated` | Time/tokens spent on irrelevant leads |
| `fix_order` | Which root cause was found first |
| `context_at_solution` | Context window size when correct fix was found |
| `exploration_efficiency` | Correct fix tokens / total tokens (signal-to-noise ratio) |

## 7. Expected Outcomes

**Baseline A (Standard):**
- Agent investigates red herrings, tries fixes that don't work
- Each failed fix leaves residue in the environment (altered configs, partial changes)
- Context fills with debugging output, making later reasoning harder
- May find one root cause but miss the second (partial fix)
- Higher token cost, lower success rate on full fix

**Baseline B (Branching):**
- Agent saves branch point, tries a hypothesis
- If it doesn't work → restore, try next hypothesis with clean environment
- No residue from failed attempts
- Context contains only "I tried X (hypothesis), it didn't work" — not the full execution log
- Finds both root causes more reliably
- Lower total tokens despite more exploration

## 8. What This Proves Beyond V5

| V5 proves | V6 proves |
|-----------|-----------|
| Checkpoints help with known-risky operations | Branching helps with unknown/ambiguous problems |
| Agent saves state before planned actions | Agent saves state before speculative exploration |
| Linear workflow with recovery | Non-linear exploration with backtracking |
| Snapshot as safety net | Snapshot as reasoning primitive |
| Reduces recovery cost | Reduces exploration cost AND improves solution quality |

## 9. Connection to ReSnapAct Vision

This experiment directly validates the **ReSnapAct** thesis: the agent's execution cycle incorporates snapshots as part of the action-observation-recovery loop. Instead of the traditional ReAct pattern:

```
Reason → Act → Observe → (if bad) Reason about failure → Act to fix
```

ReSnapAct becomes:

```
Reason → Save → Act → Observe → (if bad) Restore → Reason fresh → Act differently
```

The "Restore" step eliminates the compounding cost of failed actions and enables true speculative execution — the agent can safely try risky approaches knowing it can always return to a known-good state.
