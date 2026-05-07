# Experiment 4.2: Forced Snapshot Recovery — Spec

> Status: Awaiting Execution
> Author: Gemini CLI
> Date: 2026-05-07

## 1. Goal

Measure the **theoretical maximum efficiency** of SnapVM by ensuring 100% snapshot usage in the SnapVM baseline. This removes the "Agent Psychology" variable from Experiment 4.1 and provides a clear comparison of O(1) restoration vs. O(N) manual repair.

## 2. Hypothesis

1. With 100% snapshot usage, the SnapVM baseline will consistently achieve ~1-2 tool calls and ~400-600 tokens.
2. The "Scissors Chart" will be fully realized: Standard cost will scale with scenario complexity while SnapVM cost remains flat.
3. The token gap will reach its maximum potential (likely 5x-10x for complex scenarios).

## 3. Methodology

### 3.1 Forcing Mechanism

For **Baseline B (SnapVM)**, the agent's instructions will be modified to ensure immediate restoration:

- **System Prompt Update:** "You are an AI engineer... When the environment becomes unhealthy, your **absolute priority** is to use `restore_last_snapshot` immediately. Only attempt manual repair if restoration fails."
- **Perception Hook Update:** Append "Restore the environment to its last healthy state using the available snapshot tool."

### 3.2 Failure Scenarios

Reuses the 5 scenarios from V4.1:
- F1: multi_table_corruption
- F2: process_and_config
- F3: schema_and_data_corruption
- F4: permissions_and_schema
- F5: cascading_service_failure

## 4. Parameters

| Parameter | Value |
|-----------|-------|
| Model | GPT-4o |
| Temperature | 0 |
| Scenarios | 5 |
| Iterations per scenario | 4 |
| Total trials | 40 (5 × 4 × 2 baselines) |
| Max tool calls | 25 |

## 5. Metrics

Identical to V4.1.

## 6. Expected Outcome

A "pure" infrastructure benchmark. We expect to see the SnapVM lines on the graphs stay perfectly horizontal (constant cost) while the Standard lines climb significantly as we move from F1 to F5.
