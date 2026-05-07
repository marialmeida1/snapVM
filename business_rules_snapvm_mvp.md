# Business Rules — SnapVM Experimental MVP

## 1. Purpose of the document

This document defines the business rules for the **experimental SnapVM MVP**, focusing on the use of Firecracker microVM snapshots as a recovery mechanism for stateful environments used in workflows with AI agents.

The goal is not to describe a production-ready final product, but rather to establish clear rules for the implementation, validation, and evolution of the current experiment.

This document should serve as a reference for:

- orchestrator implementation;
- definition of the tools exposed to the agent;
- snapshot control;
- rollback execution;
- health check usage;
- log recording;
- experiment standardization;
- communication among team members.

---

## 2. Context of the experimental MVP

At the current stage, SnapVM should be understood as an **experimental orchestration tool for workflows with AI agents**.

The project proposal is to investigate whether Firecracker microVM snapshots can offer a more faithful and efficient way to recover environments than traditional mechanisms based only on Git.

Git remains important, but it mainly acts on versioned files. In stateful environments, such as applications with databases, active processes, memory, running services, and persistent state, restoring only files may not be enough.

SnapVM acts as an additional or complementary layer, operating on the **complete state of the environment**, not only on the source code.

---

## 3. MVP scope

### 3.1 Current scope

The experimental MVP focuses on a controlled scenario:

- simple Express application;
- PostgreSQL database;
- execution inside a Firecracker microVM;
- health contract through the `/health` endpoint;
- controlled failure based on removing the `users` table;
- AI agent operating in a recovery workflow;
- orchestrator responsible for health check, snapshot, and rollback.

Although the current scenario uses API + database, the project should not be defined as a PostgreSQL-specific tool. The database is only the first representative case of a stateful environment.

### 3.2 Conceptual scope

SnapVM should be designed for agentic workflows in which an AI may:

- change code;
- execute commands;
- apply migrations;
- break the environment;
- generate inconsistent states;
- consume tokens trying to repair failures;
- pollute its context window with poor attempts.

The goal of SnapVM is to reduce this cost by offering a recovery primitive based on the complete state of the environment.

### 3.3 Out of current scope

This MVP will not address:

- production environments;
- multiple simultaneous users;
- multiple historical checkpoints;
- choosing between several milestones;
- rollback of external services;
- AWS, Kafka, remote databases, or third-party APIs;
- advanced Context Surgeon;
- complete tombstoning;
- sophisticated security policies per command;
- generic support for any stack in the first version;
- broad comparison with Docker or other virtualization systems.

These points may be considered in future phases.

---

## 4. Objectives of the business rules

The rules in this document seek to answer:

1. What is the role of the orchestrator?
2. What is the role of the agent?
3. When should a snapshot be created?
4. When can a snapshot be considered healthy?
5. When should rollback be allowed?
6. What happens if there is no snapshot?
7. How is the agent informed about the environment state?
8. Which tools can the agent use?
9. How should the system handle failures?
10. What should be recorded for later analysis?

---

## 5. Main definitions

### 5.1 SnapVM

SnapVM is the experimental orchestration layer that controls the execution environment, manages snapshots, and coordinates rollback in workflows with AI agents.

In the MVP, SnapVM should not be treated as a final product, but as an experimental implementation to validate the stateful recovery thesis.

### 5.2 ReSnapAct

ReSnapAct is the future architectural vision of the project, in which the agent execution cycle incorporates snapshots as part of the action, observation, and recovery loop.

While traditional ReAct depends on the agent to reason and correct errors, ReSnapAct aims to shift part of the recovery responsibility to the infrastructure.

### 5.3 Orchestrator

The orchestrator is the layer responsible for controlling the environment.

It is responsible for:

- starting the microVM;
- shutting down the microVM;
- configuring the environment;
- executing health checks;
- capturing snapshots;
- restoring snapshots;
- maintaining the last healthy snapshot;
- applying Git fallback;
- recording events;
- exposing tools to the agent;
- preventing the agent from directly controlling critical infrastructure.

The orchestrator is the most deterministic part of the system.

### 5.4 Agent

The agent is the AI responsible for interpreting the workflow state and requesting actions through tools.

The agent may:

- analyze a failure;
- call tools;
- execute commands through the orchestrator;
- verify the environment health;
- request rollback;
- continue the workflow after recovery.

The agent must not directly control snapshots, microVMs, or internal infrastructure files.

### 5.5 MicroVM

The microVM is the isolated environment where the application and its services are executed.

In the MVP, the microVM contains:

- Linux system;
- Express API;
- PostgreSQL;
- required dependencies;
- `/health` endpoint.

### 5.6 Snapshot

A snapshot is a capture of the microVM state.

This state may include:

- memory;
- CPU state;
- active processes;
- database state;
- running application;
- associated filesystem.

In the MVP, the snapshot is used as the environment restoration point.

### 5.7 Last healthy snapshot

The last healthy snapshot is the most recent snapshot captured after the environment passes the health contract.

In the MVP, the system must maintain only one active healthy snapshot.

### 5.8 Health check

A health check is the verification used to determine whether the environment is functional.

In the MVP, the health check is performed through the `/health` endpoint.

### 5.9 Health contract

A health contract is the rule that defines whether the environment can be considered healthy.

In the MVP, the contract verifies:

- whether the API responds;
- whether PostgreSQL is functional;
- whether the `users` table exists;
- whether the validation query executes successfully.

In future versions, this contract may be configurable per project.

### 5.10 Perception Hook

A Perception Hook is the state message generated by the orchestrator to inform the agent about relevant changes in the environment.

It may inform:

- current environment state;
- reason for the failure;
- snapshot availability;
- rollback availability;
- result of the last health check.

The Perception Hook informs, but must not decide for the agent.

---

# 6. Scope rules

## RN-001 — SnapVM must be treated as an experimental orchestration tool

In this MVP, SnapVM must be described as an experimental orchestration tool, not as a finished ready-to-use product.

**Rationale:**  
The project is still in a phase of hypothesis validation, experiments, and architecture definition.

**Practical implication:**  
Documentation and code should prioritize experimental clarity, reproducibility, and validation of the thesis.

---

## RN-002 — The MVP focuses on workflows with AI agents

The system must be designed for scenarios in which an agent executes actions in a development or test environment.

**Includes:**

- agent executing commands;
- agent applying changes;
- agent breaking the environment;
- agent trying to recover the environment;
- agent using tools exposed by the orchestrator.

**Does not include in this MVP:**

- use by an end human user;
- production;
- multi-user environments.

---

## RN-003 — SnapVM must act as an additional layer to Git

SnapVM does not replace Git in the MVP.

It acts as an additional layer aimed at recovering the complete state of the environment.

**Practical rule:**

- Git continues to be used as the traditional fallback mechanism.
- SnapVM is used when a healthy snapshot is available.
- Git may be triggered when a snapshot does not exist or fails.

---

## RN-004 — The MVP must use API + PostgreSQL as the initial scenario

The official MVP scenario will be:

- Express API;
- PostgreSQL;
- `users` table;
- `/health` endpoint;
- failure based on `DROP TABLE users`.

**Note:**  
This scenario does not limit the project vision. It serves as the first controlled experimental case.

---

## RN-005 — The project must be documented as expandable to other systems

Even though the MVP uses API + PostgreSQL, SnapVM must be described as an approach for stateful environments in general.

**Future examples:**

- APIs with cache;
- workers;
- queues;
- different databases;
- Java applications;
- Python applications;
- services with automated tests;
- environments with multiple processes.

---

# 7. Environment health rules

## RN-006 — Every workflow must have a health contract

The orchestrator can only decide whether an environment is healthy based on an explicit contract.

In the MVP, this contract will be the `/health` endpoint.

**Objective:**  
Prevent the system from capturing snapshots of invalid states.

---

## RN-007 — In the MVP, the health contract will be the `/health` endpoint

The `/health` endpoint must validate the minimum state required to consider the environment functional.

In the current scenario, it must confirm:

1. Express API running;
2. PostgreSQL accessible;
3. `users` table existing;
4. validation query executed successfully.

---

## RN-008 — The concept of health must be generalizable

Although the MVP uses `/health`, the business rule must be described in a generic way.

General definition:

> A healthy state is any state that satisfies the health contract configured for that workflow.

Examples of future contracts:

- `/health` endpoint;
- execution of `npm test`;
- execution of `pytest`;
- successful build;
- database verification;
- active process validation;
- custom verification script.

---

## RN-009 — Only healthy states may replace the last healthy snapshot

The orchestrator may only promote a new snapshot as the last healthy snapshot if the health contract returns `HEALTHY`.

Partial, uncertain, or broken states cannot replace the last healthy snapshot.

---

## RN-010 — Partially healthy states may be logged, but not promoted

If the environment is partially functional, the event may be recorded in a log, but it must not replace the main snapshot.

**Examples of partial states:**

- API responds, but database fails;
- database responds, but endpoint fails;
- service starts, but the main test fails;
- health check returns an intermittent error.

---

## RN-011 — The health check must run after relevant actions

The orchestrator must run a health check after actions that may change the environment state.

In the MVP, relevant actions include:

- initial creation of the `users` table;
- migration execution;
- code changes that affect the API or database;
- recovery attempt;
- rollback;
- service restart;
- relevant configuration change.

---

## RN-012 — The agent must not challenge the health check in the MVP

In the MVP, the result of the health contract is authoritative.

The agent may observe the result, but must not override the contract decision.

---

## RN-013 — Multiple health contracts are out of current scope

In the MVP, there will be only one main health contract.

The possibility of multiple contracts per project should be treated as a future evolution.

---

# 8. Snapshot rules

## RN-014 — The snapshot must be created by the orchestrator

The agent must not create snapshots manually in the MVP.

**Rationale:**  
Snapshot creation is part of infrastructure control and must follow deterministic health rules.

---

## RN-015 — The snapshot must be created after a relevant action with a healthy health check

The standard flow must be:

```text
relevant action → health check → if HEALTHY → capture snapshot
```

The snapshot must not be created before confirming the environment health.

---

## RN-016 — The orchestrator decides which actions are relevant

In the MVP, the relevance of actions will be defined by the experimental flow.

The agent does not decide by itself when an action deserves a snapshot.

**Example in the MVP:**

1. Orchestrator creates the `users` table;
2. Runs the health check;
3. If the health check passes, captures a snapshot.

---

## RN-017 — The system must keep only the last healthy snapshot

Due to memory and storage limitations, the MVP must keep only one main snapshot.

When a new healthy snapshot is created, the previous snapshot may be removed.

---

## RN-018 — The previous snapshot may only be removed after the new snapshot is validated

To avoid losing the recovery point, the system must follow this order:

1. capture new snapshot in a temporary directory;
2. confirm that the artifacts were created correctly;
3. record metadata;
4. promote the new snapshot to `last_known_good`;
5. remove the previous snapshot.

Never remove the old snapshot before ensuring that the new one is valid.

---

## RN-019 — If snapshot capture fails, the previous snapshot remains valid

A capture failure cannot erase or invalidate the existing last healthy snapshot.

The system must:

- record the error;
- keep the previous snapshot;
- report that the new snapshot was not created;
- continue operating with the last valid snapshot.

---

## RN-020 — The snapshot type must be configurable

The MVP must allow configuring the snapshot type.

Recommended configuration:

- default: `Full`;
- optional: `Diff`.

**Rule:**  
`Full` mode must be considered the safest default. `Diff` mode may be enabled when the experiment aims to evaluate storage and latency reduction.

---

## RN-021 — The system must record snapshot metadata

Every healthy snapshot must have associated metadata.

Minimum fields:

```json
{
  "snapshot_id": "lkg_001",
  "created_at": "2026-05-07T14:22:10Z",
  "health_status": "HEALTHY",
  "health_detail": "state-diff contract passed",
  "trigger": "post_action_health_passed",
  "snapshot_type": "Full",
  "storage_bytes": 268449211
}
```

---

## RN-022 — The healthy snapshot must be stored in a standardized location

Suggestion:

```text
images/snapshots/last_known_good/
  memory.bin
  vmstate
  metadata.json
```

---

# 9. Rollback rules

## RN-023 — Rollback must be allowed when the environment is not healthy

The main rollback trigger is the health check returning:

- `UNHEALTHY`;
- `UNKNOWN`;
- error;
- timeout.

In the MVP, rollback is associated with health contract failure.

---

## RN-024 — Rollback must always try to restore the last healthy snapshot

In the MVP, there will be no selection among multiple snapshots.

The rollback target will always be:

```text
last_known_good
```

---

## RN-025 — Rollback must be executed by the orchestrator

Even if the agent requests rollback, the actual execution belongs to the orchestrator.

**Example:**

The agent calls:

```text
restore_last_snapshot()
```

The orchestrator:

1. checks whether there is a healthy snapshot;
2. stops the current microVM;
3. restores the snapshot;
4. resumes execution;
5. runs a health check;
6. informs the agent of the result.

---

## RN-026 — The system must request confirmation before rollback in the MVP

As an initial rule, rollback must be an explicit action mediated by the orchestrator.

Confirmation may be:

- orchestrator decision in the experimental flow;
- explicit call by the agent to the `restore_last_snapshot` tool;
- execution flag in automatic mode.

---

## RN-027 — After rollback, the system must run a new health check

Rollback will only be considered successful if the health contract passes after restoration.

Possible post-rollback states:

```text
ROLLBACK_SUCCESS_HEALTHY
ROLLBACK_FAILED_UNHEALTHY
ROLLBACK_FAILED_UNKNOWN
```

---

## RN-028 — The agent must be informed that rollback happened

After rollback, the orchestrator must inform the agent with a short message.

Example:

```text
[ENVIRONMENT STATE]
rollback_executed: true
health_status: HEALTHY
health_detail: state-diff contract passed
[/ENVIRONMENT STATE]
```

---

## RN-029 — The history of the failed attempt may be summarized

The MVP will not implement complete Context Surgeon.

However, the system may summarize the failed attempt to avoid context pollution.

Example:

```text
Previous attempt failed because the environment became unhealthy after the users table was removed. The environment has been restored to the last known healthy snapshot.
```

---

## RN-030 — If there is no healthy snapshot, the system must use Git as fallback

When `last_known_good` does not exist, the system must fall back to traditional Git-based behavior.

**Important:**  
Git is a fallback, not the main mechanism for stateful recovery.

---

## RN-031 — If snapshot restoration fails, the system must use Git as fallback

If the snapshot exists but restoration fails, the orchestrator must record the failure and trigger Git fallback.

Possible states:

```text
SNAPSHOT_RESTORE_FAILED
GIT_FALLBACK_STARTED
GIT_FALLBACK_COMPLETED
GIT_FALLBACK_FAILED
```

---

# 10. Agent rules

## RN-032 — The agent must not decide when to create a snapshot

Snapshot creation is the orchestrator's responsibility.

The agent must not call snapshot capture tools in the MVP.

---

## RN-033 — The agent may be encouraged to use rollback

The system may inform that rollback is available.

However, the agent must not receive a biased order such as:

```text
Use rollback now.
```

The ideal approach is to inform:

```text
rollback_available: true
```

---

## RN-034 — The agent must not directly access critical infrastructure

The agent must not have direct access to:

- snapshot creation;
- snapshot deletion;
- direct control of the Firecracker process;
- direct manipulation of internal microVM files;
- host commands that affect the environment outside the microVM.

---

## RN-035 — The agent must operate with generic tools

Main MVP tools:

```text
execute_bash(command)
check_health()
restore_last_snapshot()
```

These tools make the experiment less dependent on PostgreSQL.

---

## RN-036 — The `query_db(sql)` tool must not be the main tool

`query_db(sql)` makes the experiment too database-specific.

It may exist in future implementations or specific variants, but it must not be the agent's main path in the MVP.

---

## RN-037 — The agent must not manually create snapshots

The agent will not have a `capture_snapshot` tool in the MVP.

This possibility is left for future versions.

---

## RN-038 — The agent must not directly restore snapshots

The agent may request restoration through a tool.

The orchestrator is the component that executes restoration.

---

## RN-039 — The agent does not need to formally justify choosing rollback

In the MVP, the agent will not be required to formally justify the use of rollback.

The focus is to measure behavior and recovery, not detailed explainability.

---

# 11. Perception Hook rules

## RN-040 — The system must inform the agent when the environment state changes

The Perception Hook must be triggered when there is a relevant transition.

Examples:

- `HEALTHY` → `UNHEALTHY`;
- `UNHEALTHY` → `HEALTHY`;
- `UNKNOWN` → `HEALTHY`;
- healthy snapshot available;
- rollback executed;
- rollback failed;
- Git fallback started.

---

## RN-041 — The Perception Hook must inform state and reason

The hook must contain:

- current state;
- health check detail;
- snapshot availability;
- rollback availability;
- timestamp of the last verification.

Example:

```text
[ENVIRONMENT STATE]
health_status: UNHEALTHY
health_detail: relation "users" does not exist
last_known_good_snapshot: AVAILABLE
rollback_available: true
checked_at: 2026-05-07T14:24:05Z
[/ENVIRONMENT STATE]
```

---

## RN-042 — The Perception Hook must inform that rollback is available, not that it must be used

The hook must not make the decision for the agent.

Allowed:

```text
rollback_available: true
```

Avoid:

```text
You should rollback now.
```

---

## RN-043 — The Perception Hook must be short

The hook must avoid context pollution.

It should contain only the operational information required for the agent to decide.

---

## RN-044 — The hook must be generated when the state changes

In the MVP, it is not necessary to inject the hook into every message.

It should appear mainly when there is a state change.

---

## RN-045 — Old hooks must not accumulate indefinitely

The system must avoid keeping a long sequence of old hooks.

Recommended rule:

- keep only the most recent hook;
- or replace the previous hook when the state changes;
- or summarize old hooks in logs, not in the agent context.

---

# 12. Tool rules

## RN-046 — The agent will have access to `execute_bash(command)`

This tool allows commands to be executed in the controlled environment.

It must return:

- exit code;
- summarized stdout;
- summarized stderr;
- duration;
- success/failure status.

Example response:

```json
{
  "exit_code": 0,
  "stdout": "ok",
  "stderr": "",
  "duration_seconds": 0.42
}
```

---

## RN-047 — The agent will have access to `check_health()`

This tool executes the health contract.

Example response:

```json
{
  "status": "UNHEALTHY",
  "detail": "relation users does not exist",
  "duration_seconds": 0.05
}
```

---

## RN-048 — The agent will have access to `restore_last_snapshot()`

This tool requests rollback to the last healthy snapshot.

Example response:

```json
{
  "ok": true,
  "restore_latency_seconds": 0.184,
  "health_after_restore": "HEALTHY"
}
```

---

## RN-049 — Tools must have structured outputs

All tools exposed to the agent must return structured responses, preferably in JSON.

This reduces ambiguity and facilitates metrics collection.

---

## RN-050 — Every tool call must be logged

The orchestrator must record:

- tool name;
- summarized input;
- summarized output;
- start time;
- duration;
- success/failure;
- error, if any.

Example log:

```json
{
  "tool": "check_health",
  "input_summary": "{}",
  "output_summary": "UNHEALTHY: relation users does not exist",
  "started_at": "2026-05-07T14:24:05Z",
  "duration_seconds": 0.05,
  "success": true
}
```

---

# 13. Security and control rules

## RN-051 — The experimental environment must always run in isolation

The experiment must be executed inside a controlled microVM.

Destructive commands are only acceptable inside this isolated environment.

---

## RN-052 — Destructive commands must be logged

The system must record commands that:

- remove data;
- alter the database;
- delete files;
- restart services;
- modify critical configurations;
- change persistent state.

It is not necessary to list every command in the MVP.

---

## RN-053 — The orchestrator must interrupt unproductive loops

The system must provide interruption when the agent repeats actions without progress.

In the MVP, the limit may be configurable or implemented in a simple way.

Examples of loop signals:

- same tool repeatedly called with the same input;
- health check failing after several attempts;
- agent executing commands without changing state;
- excessive time without progress.

---

## RN-054 — The system must log recovery failures

Any rollback, snapshot, or Git fallback failure must be logged.

Recommended fields:

- failure type;
- stage where it occurred;
- error message;
- health state before;
- health state after;
- whether fallback was triggered.

---

## RN-055 — The agent must not execute commands outside the microVM

The agent must not have unrestricted access to the host.

The orchestrator must mediate actions to maintain the isolation of the experiment.

---

# 14. Main business flow

## 14.1 Nominal flow

```text
1. Orchestrator starts the microVM
2. Environment starts API + PostgreSQL
3. Orchestrator creates the initial valid state
4. Orchestrator runs health check
5. Health check returns HEALTHY
6. Orchestrator captures the last healthy snapshot
7. Orchestrator injects controlled failure
8. Health check returns UNHEALTHY
9. Perception Hook informs the agent
10. Agent may request restore_last_snapshot()
11. Orchestrator executes rollback
12. Orchestrator runs a new health check
13. Health check returns HEALTHY
14. Orchestrator records success
```

---

## 14.2 Flow with no available snapshot

```text
1. Environment becomes UNHEALTHY
2. Agent or orchestrator requests rollback
3. Orchestrator checks last_known_good
4. Snapshot does not exist
5. Orchestrator records absence of snapshot
6. Orchestrator triggers Git fallback
7. Health check is executed after fallback
8. Result is recorded
```

---

## 14.3 Flow with snapshot capture failure

```text
1. Relevant action is completed
2. Health check returns HEALTHY
3. Orchestrator tries to capture new snapshot
4. Capture fails
5. Orchestrator keeps the previous snapshot
6. Failure event is logged
7. System continues operating with the last valid snapshot
```

---

## 14.4 Flow with rollback failure

```text
1. Environment is UNHEALTHY
2. Snapshot rollback is requested
3. Orchestrator tries to restore last_known_good
4. Restoration fails
5. Orchestrator records error
6. Orchestrator triggers Git fallback
7. Health check is executed
8. Result is recorded
```

---

# 15. System states

## 15.1 Health states

```text
HEALTHY
UNHEALTHY
UNKNOWN
```

### HEALTHY

The health contract passed.

### UNHEALTHY

The health contract failed with a known reason.

### UNKNOWN

The system could not determine the environment health.

Examples:

- timeout;
- microVM does not respond;
- endpoint inaccessible;
- unexpected error in the probe.

---

## 15.2 Snapshot states

```text
NO_SNAPSHOT
SNAPSHOT_AVAILABLE
SNAPSHOT_CAPTURE_IN_PROGRESS
SNAPSHOT_CAPTURE_FAILED
SNAPSHOT_INVALID
SNAPSHOT_RESTORED
```

---

## 15.3 Rollback states

```text
ROLLBACK_NOT_REQUESTED
ROLLBACK_REQUESTED
ROLLBACK_IN_PROGRESS
ROLLBACK_SUCCESS
ROLLBACK_FAILED
GIT_FALLBACK_IN_PROGRESS
GIT_FALLBACK_SUCCESS
GIT_FALLBACK_FAILED
```

---

# 16. Suggested JSON report structure

Each experiment execution must generate a structured report.

Example:

```json
{
  "experiment": "health_aware_agentic_rollback",
  "iteration": 1,
  "environment": {
    "application": "express-api",
    "database": "postgresql",
    "health_contract": "/health"
  },
  "snapshot": {
    "last_known_good_available": true,
    "snapshot_type": "Full",
    "created_at": "2026-05-07T14:22:10Z",
    "storage_bytes": 268449211
  },
  "failure": {
    "type": "drop_users_table",
    "injected_by": "orchestrator",
    "agent_knows_failure_type": true
  },
  "health": {
    "before_failure": "HEALTHY",
    "after_failure": "UNHEALTHY",
    "after_rollback": "HEALTHY"
  },
  "perception_hook": {
    "emitted": true,
    "content_summary": "UNHEALTHY; rollback available"
  },
  "agent": {
    "tools_available": [
      "execute_bash",
      "check_health",
      "restore_last_snapshot"
    ],
    "tools_called": [
      "restore_last_snapshot"
    ]
  },
  "rollback": {
    "requested": true,
    "executed_by": "orchestrator",
    "success": true,
    "fallback_git_used": false
  },
  "logs": {
    "tool_calls_logged": true,
    "destructive_commands_logged": true
  }
}
```

---

# 17. MVP success criteria

The MVP will be considered successful if it demonstrates that:

1. The orchestrator can start and control the environment.
2. The health contract correctly identifies healthy and broken states.
3. The system captures a snapshot only after a healthy health check.
4. The system keeps only the last healthy snapshot.
5. The system does not replace a valid snapshot with a broken snapshot.
6. The Perception Hook informs the agent when the state changes.
7. The agent can request rollback through a tool.
8. The orchestrator executes rollback successfully.
9. The health check passes after rollback.
10. Git acts as fallback when a snapshot does not exist or fails.
11. All relevant tool calls are logged.
12. Destructive commands are logged.
13. The flow reduces dependence on manual repair by the agent.

---

# 18. Implementation decision points

## 18.1 Decision 1 — Full or Diff snapshot

Current rule:

- Full as default;
- Diff by configuration.

Suggested implementation:

```text
SNAPSHOT_TYPE=Full
```

or

```text
SNAPSHOT_TYPE=Diff
```

---

## 18.2 Decision 2 — Where to store the last healthy snapshot

Suggestion:

```text
images/snapshots/last_known_good/
```

---

## 18.3 Decision 3 — When to emit Perception Hook

Current rule:

- emit when state changes.

Do not emit in every message to avoid context pollution.

---

## 18.4 Decision 4 — Which tools to enable

Default tools:

```text
execute_bash
check_health
restore_last_snapshot
```

Non-default tool:

```text
query_db
```

---

## 18.5 Decision 5 — Git fallback

Git fallback must be triggered when:

- there is no snapshot;
- the snapshot is invalid;
- restoration fails;
- post-rollback health check does not pass.

---

# 19. Future evolutions

The following features should be considered future work:

## 19.1 Multiple milestones

Allow multiple semantic restoration points.

Out of the current MVP.

## 19.2 Automatic snapshot by advanced heuristic

Automatically detect risky actions.

Example:

- migrations;
- package installation;
- changes to critical files;
- destructive commands.

## 19.3 Context Surgeon

Remove poor history from the agent context and replace it with a compact summary.

## 19.4 Tombstoning

Record failed attempts as compact lessons to avoid repeating errors.

## 19.5 Support for multiple health contracts

Allow each project to define its own contract.

## 19.6 Support for other experimental scenarios

Examples:

- API + Redis;
- API + queue;
- Java application;
- environment with tests;
- environment with cache;
- asynchronous worker.

## 19.7 Security policies per command

Classify and block destructive commands outside a safe context.

---

# 20. Executive summary of the rules

The experimental SnapVM MVP must follow these core ideas:

1. SnapVM is an experimental orchestration tool for workflows with AI agents.
2. The initial scenario is Express API + PostgreSQL.
3. The system must be designed in a generalizable way for other stateful environments.
4. The orchestrator controls snapshots, rollback, and health checks.
5. The agent requests actions through tools, but does not control critical infrastructure.
6. The system keeps only the last healthy snapshot.
7. A snapshot is only updated after a healthy health check.
8. Rollback always tries to restore the last healthy snapshot.
9. If the snapshot does not exist or fails, Git acts as fallback.
10. The Perception Hook informs the agent of state changes.
11. Tools must be generic to avoid excessive database specialization.
12. All tool calls and destructive commands must be logged.
13. The MVP does not work with multiple milestones, external state, or advanced Context Surgeon.
14. The goal is to validate the feasibility of stateful rollback as an additional layer to Git.
