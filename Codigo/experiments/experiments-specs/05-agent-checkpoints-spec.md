# Experiment 5: Multi-Step Task with Agent-Driven Checkpoints — Spec

> Status: Planned
> Author: Arthur Carvalho
> Date: 2026-05-07

## 1. Goal

Prove that snapshots aren't just a recovery tool — they're a **development acceleration primitive**. Measure whether agents that can create their own checkpoints before risky steps recover faster and cheaper across a multi-step task than agents without checkpoints.

## 2. Hypothesis

1. Agents with `save_checkpoint` will use it before risky operations (migrations, schema changes).
2. When failures occur mid-task, checkpoint-enabled agents recover in O(1) to the last safe state, while standard agents must manually undo their own mistakes.
3. Total task completion cost (tokens + time) will be significantly lower with checkpoints.
4. The advantage **compounds** — each subsequent failure is cheaper to recover from with checkpoints, while standard agents accumulate context pollution.

## 3. The Task

A realistic multi-step database migration workflow:

```
Step 1: Create a "products" table (id, name, price)
Step 2: Seed 100 rows of sample data
Step 3: Add a "category" column with a foreign key to a new "categories" table
Step 4: Migrate existing products to assign categories (UPDATE with logic)
Step 5: Create an index on products(category_id)
Step 6: Update the /health endpoint to validate the new schema
```

Each step builds on the previous. A failure at step 4 means steps 1-3 must be preserved.

## 4. Failure Injection Strategy

Failures are injected **after** the agent completes certain steps, simulating real-world issues:

- **After Step 2**: Orchestrator corrupts 20% of seeded data (simulates bad seed script)
- **After Step 4**: Orchestrator drops the categories table (simulates a conflicting migration)

The agent must recover and continue from where it left off.

## 5. Baselines

| | Baseline A: Standard Agent | Baseline B: Checkpoint Agent |
|---|---|---|
| Tools | `execute_bash`, `check_health`, `query_db` | Same + `save_checkpoint`, `restore_checkpoint` |
| Recovery method | Agent must manually diagnose and fix, then continue | Agent restores to last checkpoint, re-executes from there |
| Context after recovery | Polluted with debugging | Clean — only contains work up to checkpoint |

### New Tools (Baseline B only)

**`save_checkpoint`**
```json
{
  "name": "save_checkpoint",
  "description": "Save the current environment state as a checkpoint. Use this before performing risky operations (migrations, schema changes, bulk updates). You can restore to this point if something goes wrong.",
  "parameters": {
    "type": "object",
    "properties": {
      "label": {"type": "string", "description": "A short label describing what state this checkpoint captures."}
    },
    "required": ["label"]
  }
}
```

**`restore_checkpoint`**
```json
{
  "name": "restore_checkpoint",
  "description": "Restore the environment to the last saved checkpoint. All changes made after the checkpoint will be reverted.",
  "parameters": {"type": "object", "properties": {}}
}
```

## 6. Methodology

### Flow

```
1. System prompt (identical, no coaching on when to checkpoint)
2. Task prompt: "Complete the following database migration in order: [steps 1-6]"
3. Agent works through steps autonomously
4. Failure injected after steps 2 and 4
5. Perception Hook emitted after each failure (health_status: UNHEALTHY)
6. Agent recovers and continues
7. Task complete when all 6 steps pass validation
```

### Validation Contract

Extended health check that validates the final schema:
- products table exists with correct columns (id, name, price, category_id)
- categories table exists
- Foreign key constraint exists
- Index on category_id exists
- At least 80 valid product rows

### Parameters

| Parameter | Value |
|-----------|-------|
| Model | GPT-4o |
| Temperature | 0 |
| Iterations | 10 per baseline (20 total) |
| Max tool calls | 40 (longer task) |
| Failure injection points | After step 2, after step 4 |

## 7. Metrics

All V4 metrics plus:

| Metric | Description |
|--------|-------------|
| `checkpoints_created` | How many checkpoints the agent saved (Baseline B) |
| `checkpoints_restored` | How many times the agent restored (Baseline B) |
| `task_completion_rate` | Did the agent finish all 6 steps? |
| `steps_completed` | How far the agent got (0-6) |
| `tokens_per_recovery` | Token cost of each individual recovery event |
| `cumulative_context_at_recovery` | Context size at each failure point |
| `rework_steps` | Steps the agent had to redo after recovery |

## 8. Expected Outcomes

**Baseline A (Standard):**
- After failure at step 2: Agent spends tokens diagnosing corrupt data, fixing rows (~1000-2000 tokens)
- After failure at step 4: Agent must figure out categories table is gone, recreate it, re-run migration (~2000-4000 tokens)
- Context heavily polluted by end of task
- Some trials may fail to complete all 6 steps within tool call limit

**Baseline B (Checkpoint):**
- Agent saves checkpoints at steps 1, 3 (before risky operations)
- After failure at step 2: Restores to post-step-1 checkpoint, re-seeds (~400 tokens)
- After failure at step 4: Restores to post-step-3 checkpoint, re-runs step 4 (~400 tokens)
- Context stays clean throughout
- Near 100% task completion rate

## 9. What This Proves Beyond V4

| V4 proved | V5 proves |
|-----------|-----------|
| Recovery from single injected failure | Recovery across multiple failures in a real workflow |
| Orchestrator creates checkpoints | Agent creates its own checkpoints |
| One-shot recovery | Iterative recovery (fail → restore → retry → continue) |
| Token cost of one recovery | Cumulative token cost over an entire task |
| Snapshot as recovery tool | Snapshot as development acceleration primitive |
