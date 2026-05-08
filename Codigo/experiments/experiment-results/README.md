# Experiment Benchmarks Summary

This document consolidates the quantitative data from all SnapVM experiments.

## Experiment 1: Baseline Benchmarks (Mock V1)
Establishment of core infrastructure metrics using a deterministic state machine to mock agent actions and failures.

| Baseline | Capture | Restore | Storage | Contract | Penalty |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Git** | 0.008s | 0.006s | 27,420B | PASS | 0.004s |
| **Firecracker** | 0.413s | 0.158s | 268,449,211B | PASS | 0.000s |

## Experiment 2: LLM Agent Recovery (Live V2)
Measurement of how physical state restoration impacts cognitive load, token cost, and recovery speed of a live AI agent.

| Metric | Baseline A (Git) | Baseline B (Firecracker) | Improvement |
|--------|------------------|--------------------------|-------------|
| **Capture Latency** | 0.030s | 0.484s | -1513% |
| **Restore Latency (Total)** | 6.572s | 0.184s | **3471%** |
| **Penalty Time (LLM Repair)** | 6.570s | 0.000s | **100%** |
| **Token Consumption** | 2860.3 | 549.2 | **5.2x Lower** |
| **Context Pollution** | 456.1 | 165.6 | **2.7x Lower** |
| **Storage Overhead** | 27.4 KB | 268.4 MB | -979,000% |

## Experiment 3: Incremental State Optimization
Comparison of "Full" vs. "Diff" snapshots to optimize storage footprint and capture latency.

| Snapshot Type | Capture Latency | Physical Storage (Disk) | Improvement |
|---------------|-----------------|-------------------------|-------------|
| **Full (Base)** | 0.432s | 268.4 MB | - |
| **Diff (Incremental)** | 0.350s | 170.5 MB | **36.5% Lower** |

## Experiment 4.1: Complex Stateful Failures
Recovery efficiency against multi-layered, complex failures with autonomous agent behavior.

| Metric | Standard (Manual) | SnapVM (Autonomous) | Delta |
| :--- | :--- | :--- | :--- |
| **Success Rate** | 100% | 100% | - |
| **Avg Tool Calls** | 2.2 | 1.9 | **-14%** |
| **Avg Token Consumption** | 1,349.5 | 1,174.1 | **-13%** |
| **Avg Recovery Latency** | 2.85s | 2.14s | **-25%** |
| **Avg Context Pollution** | 276.1 tokens | 263.3 tokens | **-5%** |

| Scenario | Std Calls | Snap Calls | Std Tokens | Snap Tokens | Snap Strategy |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **F1: Multi-table** | 3.0 | 3.0 | 1751 | 1688 | 50% Restore / 50% Manual |
| **F2: Process & Config** | 3.0 | 2.0 | 1758 | 1036 | 75% Restore / 25% Manual |
| **F3: Schema & Data** | 1.0 | 1.0 | 740 | 818 | 100% Manual |
| **F4: Permissions** | 3.0 | 2.5 | 1757 | 1514 | 50% Restore / 50% Manual |
| **F5: Cascade** | 1.0 | 1.0 | 742 | 816 | 100% Manual |

## Experiment 4.2: Forced Snapshot Recovery
Theoretical maximum benchmark by forcing snapshot restoration for every failure.

| Metric | Standard (Manual) | SnapVM (Forced Restore) | Delta |
| :--- | :--- | :--- | :--- |
| **Success Rate** | 100% | 100% | - |
| **Avg Tool Calls** | 2.2 | 1.0 | **-55%** |
| **Avg Token Consumption** | 1,350.2 | 441.8 | **-67%** |
| **Avg Recovery Latency** | 3.25s | 0.92s | **-72%** |
| **Avg Context Pollution** | 275.1 tokens | 266.8 tokens | **-3%** |

| Scenario | Std Calls | Snap Calls | Std Tokens | Snap Tokens | Improvement (Tokens) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **F1: Multi-table** | 3.0 | 1.0 | 1758.5 | 449.0 | **3.9x** |
| **F2: Process & Config** | 3.0 | 1.0 | 1758.5 | 449.0 | **3.9x** |
| **F3: Schema & Data** | 1.0 | 1.0 | 740.5 | 431.0 | **1.7x** |
| **F4: Permissions** | 3.0 | 1.0 | 1757.0 | 449.0 | **3.9x** |
| **F5: Cascade** | 1.0 | 1.0 | 736.8 | 431.0 | **1.7x** |

## Experiment 4: Autonomous Agent Recovery (Fair Comparison)
Validation of SnapVM as a superior recovery mechanism for uncoached autonomous agents.

| Metric | Baseline A: Standard (Manual) | Baseline B: SnapVM (Restore) | Delta |
| :--- | :--- | :--- | :--- |
| **Success Rate** | 100% | 100% | - |
| **Avg Tool Calls** | 2.2 | 1.6 | **-27%** |
| **Avg Token Consumption** | 1,298.8 | 776.6 | **-40%** |
| **Avg Recovery Latency** | 2.61s | 1.72s | **-34%** |
| **Avg Context Pollution** | 259.6 tokens | 248.9 tokens | **-4%** |

## Experiment 5: Agent-Driven Checkpointing
Evaluation of snapshots as a development acceleration primitive managed by the agent.

| Metric | Baseline A: Standard | Baseline B: Checkpoint | Delta |
| :--- | :--- | :--- | :--- |
| **Task Completion Rate** | 67% | 100% | **+33%** |
| **Avg Tool Calls** | 24.3 | 26.7 | +10% |
| **Avg Token Consumption** | 47,553 | 42,060 | **-12%** |
| **Avg Task Latency** | 92.0s | 64.6s | **-30%** |
| **Avg Context Pollution** | 3,124 tokens | 1,590 tokens | **-49%** |
