Business Rules — SnapVM / ReSnapAct Experimental MVP
1. Document purpose
This document defines the business rules for the SnapVM/ReSnapAct experimental MVP, focusing on the use of Firecracker microVM snapshots as a recovery mechanism for stateful environments used in workflows with AI agents.

The objective is not to describe a final product ready for production, but rather to establish clear rules for the implementation, validation, and evolution of the current experiment.

This document should serve as a reference for:

orchestrator implementation;

definition of the tools exposed to the agent;

snapshot control;

rollback execution;

health check usage;

log registration;

experiment standardization;

communication among team members.

2. Experimental MVP context
SnapVM, in its current stage, should be understood as an experimental orchestration tool for workflows with AI agents.

The project's proposal is to investigate whether Firecracker microVM snapshots can offer a more faithful and efficient way of recovering environments than traditional mechanisms based solely on Git.

Git remains important, but it primarily acts on versioned files. In stateful environments, such as applications with databases, active processes, memory, running services, and persistent state, restoring only files may not be enough.

SnapVM acts as an additional or complementary layer, operating on the complete state of the environment, not just the source code.

3. MVP Scope
3.1 Current scope
The experimental MVP is focused on a controlled scenario:

simple application in Express;

PostgreSQL database;

execution inside a Firecracker microVM;

health contract via the /health endpoint;

controlled failure based on the removal of the users table;

AI agent operating in a recovery workflow;

orchestrator responsible for health check, snapshot, and rollback.

Although the current scenario uses an API + database, the project should not be defined as a specific tool for PostgreSQL. The database is merely the first representative case of a stateful environment.

3.2 Conceptual scope
SnapVM should be designed for agentic workflows where an AI can:

alter code;

execute commands;

apply migrations;

break the environment;

generate inconsistent states;

consume tokens trying to repair failures;

pollute its context window with bad attempts.

SnapVM's goal is to reduce this cost by offering a recovery primitive based on the complete state of the environment.

3.3 Out of current scope
In this MVP, the following will not be addressed:

production environments;

multiple simultaneous users;

multiple historical checkpoints;

choosing between multiple milestones;

rollback of external services;

AWS, Kafka, remote databases, or third-party APIs;

advanced Context Surgeon;

full tombstoning;

sophisticated security policies per command;

generic support for any stack in the first version;

broad comparison with Docker or other virtualization systems.

These points may be considered in future phases.

4. Business rules objectives
The rules in this document seek to answer:

What is the orchestrator's role?

What is the agent's role?

When should a snapshot be created?

When can a snapshot be considered healthy?

When should rollback be allowed?

What happens if there is no snapshot?

How is the agent informed about the environment's state?

Which tools can the agent use?

How should the system handle failures?

What should be logged for further analysis?

5. Main definitions
5.1 SnapVM
SnapVM is the experimental orchestration layer that controls the execution environment, manages snapshots, and coordinates rollback in workflows with AI agents.

In the MVP, SnapVM should not be treated as a final product, but as an experimental implementation to validate the stateful recovery thesis.

5.2 ReSnapAct
ReSnapAct is the future architectural vision of the project, in which the agent's execution cycle incorporates snapshots as part of the action, observation, and recovery loop.

While traditional ReAct relies on the agent to reason and correct errors, ReSnapAct seeks to shift part of the recovery responsibility to the infrastructure.

5.3 Orchestrator
The orchestrator is the layer responsible for controlling the environment.

It is responsible for:

starting the microVM;

stopping the microVM;

configuring the environment;

executing health checks;

capturing snapshots;

restoring snapshots;

maintaining the last healthy snapshot;

applying fallback to Git;

logging events;

exposing tools to the agent;

preventing the agent from directly controlling critical infrastructure.

The orchestrator is the most deterministic part of the system.

5.4 Agent
The agent is the AI responsible for interpreting the workflow state and requesting actions through tools.

The agent can:

analyze a failure;

call tools;

execute commands via the orchestrator;

check the environment's health;

request rollback;

continue the workflow after recovery.

The agent must not directly control snapshots, microVMs, or internal infrastructure files.

5.5 MicroVM
The microVM is the isolated environment where the application and its services run.

In the MVP, the microVM contains:

Linux system;

Express API;

PostgreSQL;

necessary dependencies;

/health endpoint.

5.6 Snapshot
A snapshot is a capture of the microVM's state.

This state can include:

memory;

CPU state;

active processes;

database state;

running application;

associated filesystem.

In the MVP, the snapshot is used as the environment's restore point.

5.7 Last healthy snapshot
The last healthy snapshot is the most recent snapshot captured after the environment passes the health contract.

In the MVP, the system should maintain only one active healthy snapshot.

5.8 Health check
A health check is the verification used to determine if the environment is functional.

In the MVP, the health check is done through the /health endpoint.

5.9 Health contract
A health contract is the rule that defines if the environment can be considered healthy.

In the MVP, the contract verifies:

if the API responds;

if PostgreSQL is functional;

if the users table exists;

if the validation query executes successfully.

In future versions, this contract could be configurable per project.

5.10 Perception Hook
A Perception Hook is the state message generated by the orchestrator to inform the agent about relevant changes in the environment.

It can inform:

the environment's current state;

the reason for the failure;

snapshot availability;

rollback availability;

the result of the last health check.

The Perception Hook informs, but must not make decisions for the agent.

6. Scope rules
RN-001 — SnapVM should be treated as an experimental orchestration tool
In this MVP, SnapVM should be described as an experimental orchestration tool, not as a final, ready product.

Justification:

The project is still in the phase of validating hypotheses, experiments, and architecture.

Practical implication:

Documentation and code should prioritize experimental clarity, reproducibility, and thesis validation.

RN-002 — The MVP focus is workflows with AI agents
The system must be designed for scenarios where an agent performs actions in a development or testing environment.

Includes:

agent executing commands;

agent applying changes;

agent breaking the environment;

agent trying to recover the environment;

agent using tools exposed by the orchestrator.

Not included in this MVP:

use by an end human user;

production;

multi-user environments.

RN-003 — SnapVM should act as an additional layer to Git
SnapVM does not replace Git in the MVP.

It acts as an additional layer aimed at recovering the complete state of the environment.

Practical rule:

Git continues to be used as a traditional fallback mechanism.

SnapVM is used when there is a healthy snapshot available.

Git can be triggered when a snapshot does not exist or fails.

RN-004 — The MVP must use API + PostgreSQL as the initial scenario
The official scenario of the MVP will be:

Express API;

PostgreSQL;

users table;

/health endpoint;

failure based on DROP TABLE users.

Note:

This scenario does not limit the project's vision. It serves as the first controlled experimental case.

RN-005 — The project must be documented as expandable to other systems
Even though the MVP uses API + PostgreSQL, SnapVM should be described as an approach for stateful environments in general.

Future examples:

APIs with caching;

workers;

queues;

different databases;

Java applications;

Python applications;

services with automated tests;

environments with multiple processes.

7. Environment health rules
RN-006 — Every workflow must have a health contract
The orchestrator can only decide if an environment is healthy based on an explicit contract.

In the MVP, this contract will be the /health endpoint.

Objective:

Prevent the system from capturing snapshots of invalid states.

RN-007 — In the MVP, the health contract will be the /health endpoint
The /health endpoint must validate the minimum state necessary to consider the environment functional.

In the current scenario, it must confirm:

Express API running;

PostgreSQL accessible;

users table existing;

validation query executed successfully.

RN-008 — The concept of health must be generalizable
Although the MVP uses /health, the business rule must be described in a generic way.

General definition:

A healthy state is any state that satisfies the health contract configured for that workflow.

Examples of future contracts:

/health endpoint;

execution of npm test;

execution of pytest;

successful build;

database verification;

active process validation;

customized verification script.

RN-009 — Only healthy states can replace the last healthy snapshot
The orchestrator can only promote a new snapshot as the last healthy snapshot if the health contract returns HEALTHY.

Partial, uncertain, or broken states cannot replace the last healthy snapshot.

RN-010 — Partially healthy states can be logged, but not promoted
If the environment is partially functional, the event can be logged, but it must not replace the main snapshot.

Examples of partial states:

API responds, but database fails;

database responds, but endpoint fails;

service starts, but main test fails;

health check returns intermittent error.

RN-011 — The health check must be executed after relevant actions
The orchestrator must execute a health check after actions that may alter the state of the environment.

In the MVP, relevant actions include:

initial creation of the users table;

migration execution;

code alteration that affects API or database;

recovery attempt;

rollback;

service restart;

relevant configuration change.

RN-012 — The agent must not contest the health check in the MVP
In the MVP, the result of the health contract is sovereign.

The agent can observe the result, but must not override the contract's decision.

RN-013 — Multiple health contracts are out of the current scope
In the MVP, there will be only one main health contract.

The possibility of multiple contracts per project should be treated as a future evolution.

8. Snapshot rules
RN-014 — The snapshot must be created by the orchestrator
The agent must not create snapshots manually in the MVP.

Justification:

Snapshot creation is part of infrastructure control and must follow deterministic health rules.

RN-015 — The snapshot must be created after a relevant action with a healthy health check
The standard flow must be:

Plaintext
relevant action → health check → if HEALTHY → capture snapshot
The snapshot must not be created before confirming the environment's health.

RN-016 — The orchestrator decides which actions are relevant
In the MVP, the relevance of actions will be defined by the experimental flow.

The agent does not decide on its own when an action deserves a snapshot.

Example in the MVP:

Orchestrator creates the users table;

Executes health check;

If the health check passes, it captures a snapshot.

RN-017 — The system must keep only the last healthy snapshot
Due to memory and storage limitations, the MVP must maintain only one main snapshot.

When a new healthy snapshot is created, the previous snapshot can be removed.

RN-018 — The previous snapshot can only be removed after the new snapshot is validated
To avoid losing the recovery point, the system must follow this order:

capture new snapshot in a temporary directory;

confirm that the artifacts were created correctly;

log metadata;

promote new snapshot to last_known_good;

remove previous snapshot.

Never remove the old snapshot before ensuring the new one is valid.

RN-019 — If snapshot capture fails, the previous snapshot remains valid
A capture failure cannot erase or invalidate the last existing healthy snapshot.

The system must:

log error;

maintain previous snapshot;

inform that the new snapshot was not created;

continue operating with the last valid snapshot.

RN-020 — The snapshot type must be configurable
The MVP must allow configuring the snapshot type.

Recommended configuration:

default: Full;

optional: Diff.

Rule:

The Full mode should be considered the safest default. The Diff mode can be activated when the experiment wishes to evaluate storage and latency reduction.

RN-021 — The system must log snapshot metadata
Every healthy snapshot must have associated metadata.

Minimum fields:

JSON
{
  "snapshot_id": "lkg_001",
  "created_at": "2026-05-07T14:22:10Z",
  "health_status": "HEALTHY",
  "health_detail": "state-diff contract passed",
  "trigger": "post_action_health_passed",
  "snapshot_type": "Full",
  "storage_bytes": 268449211
}
RN-022 — The healthy snapshot must be stored in a standardized location
Suggestion:

Plaintext
images/snapshots/last_known_good/
  memory.bin
  vmstate
  metadata.json
9. Rollback rules
RN-023 — Rollback must be allowed when the environment is not healthy
The main rollback trigger is the health check returning:

UNHEALTHY;

UNKNOWN;

error;

timeout.

In the MVP, rollback is associated with the failure of the health contract.

RN-024 — Rollback must always attempt to restore the last healthy snapshot
In the MVP, there will be no selection among multiple snapshots.

The rollback destination will always be:

Plaintext
last_known_good
RN-025 — Rollback must be executed by the orchestrator
Even if the agent requests a rollback, the actual execution belongs to the orchestrator.

Example:

The agent calls:

Plaintext
restore_last_snapshot()
The orchestrator:

verifies if there is a healthy snapshot;

stops the current microVM;

restores the snapshot;

resumes execution;

executes health check;

informs the agent of the result.

RN-026 — The system must ask for confirmation before rollback in the MVP
As an initial rule, rollback must be an explicit action mediated by the orchestrator.

The confirmation can be:

orchestrator's decision in the experimental flow;

explicit call by the agent to the restore_last_snapshot tool;

execution flag in automatic mode.

RN-027 — After rollback, the system must execute a new health check
Rollback will only be considered successful if the health contract passes after restoration.

Possible post-rollback states:

Plaintext
ROLLBACK_SUCCESS_HEALTHY
ROLLBACK_FAILED_UNHEALTHY
ROLLBACK_FAILED_UNKNOWN
RN-028 — The agent must be informed that the rollback has occurred
After rollback, the orchestrator must inform the agent with a short message.

Example:

Plaintext
[ENVIRONMENT STATE]
rollback_executed: true
health_status: HEALTHY
health_detail: state-diff contract passed
[/ENVIRONMENT STATE]
RN-029 — The history of the failed attempt can be summarized
The MVP will not implement the full Context Surgeon.

However, the system can summarize the failed attempt to prevent context pollution.

Example:

Plaintext
Previous attempt failed because the environment became unhealthy after the users table was removed. The environment has been restored to the last known healthy snapshot.
RN-030 — If there is no healthy snapshot, the system must use Git as fallback
When last_known_good does not exist, the system must resort to the traditional Git-based behavior.

Important:

Git is a fallback, not the main stateful recovery mechanism.

RN-031 — If snapshot restoration fails, the system must use Git as fallback
If the snapshot exists, but restoration fails, the orchestrator must log the failure and trigger the Git fallback.

Possible states:

Plaintext
SNAPSHOT_RESTORE_FAILED
GIT_FALLBACK_STARTED
GIT_FALLBACK_COMPLETED
GIT_FALLBACK_FAILED
10. Agent rules
RN-032 — The agent must not decide when to create a snapshot
Snapshot creation is the orchestrator's responsibility.

The agent must not call snapshot capture tools in the MVP.

RN-033 — The agent can be encouraged to use rollback
The system can inform that rollback is available.

However, the agent should not receive a biased order such as:

Plaintext
Use rollback now.
The ideal is to inform:

Plaintext
rollback_available: true
RN-034 — The agent must not access critical infrastructure directly
The agent must not have direct access to:

snapshot creation;

snapshot deletion;

direct control of the Firecracker process;

direct manipulation of internal microVM files;

host commands that affect the environment outside the microVM.

RN-035 — The agent must operate with generic tools
Main MVP tools:

Plaintext
execute_bash(command)
check_health()
restore_last_snapshot()
These tools keep the experiment less dependent on PostgreSQL.

RN-036 — The query_db(sql) tool must not be a main tool
query_db(sql) makes the experiment too specialized in the database.

It can exist in future implementations or specific variants, but it should not be the agent's main path in the MVP.

RN-037 — The agent must not manually create a snapshot
The agent will not have a capture_snapshot tool in the MVP.

This possibility remains for future versions.

RN-038 — The agent must not directly restore a snapshot
The agent can request restoration via a tool.

The entity that executes the restoration is the orchestrator.

RN-039 — The agent does not need to formally justify the choice of rollback
In the MVP, formal justification from the agent to use rollback will not be required.

The focus is to measure behavior and recovery, not detailed explainability.

11. Perception Hook rules
RN-040 — The system must inform the agent when the environment's state changes
The Perception Hook must be triggered when there is a relevant transition.

Examples:

HEALTHY → UNHEALTHY;

UNHEALTHY → HEALTHY;

UNKNOWN → HEALTHY;

healthy snapshot available;

rollback executed;

rollback failed;

Git fallback started.

RN-041 — The Perception Hook must inform state and reason
The hook must contain:

current state;

health check detail;

snapshot availability;

rollback availability;

timestamp of the last check.

Example:

Plaintext
[ENVIRONMENT STATE]
health_status: UNHEALTHY
health_detail: relation "users" does not exist
last_known_good_snapshot: AVAILABLE
rollback_available: true
checked_at: 2026-05-07T14:24:05Z
[/ENVIRONMENT STATE]
RN-042 — The Perception Hook must inform that rollback is available, not that it should be used
The hook must not make a decision for the agent.

Allowed:

Plaintext
rollback_available: true
Avoid:

Plaintext
You should rollback now.
RN-043 — The Perception Hook must be short
The hook must avoid context pollution.

It should contain only the operational information necessary for the agent to decide.

RN-044 — The hook must be generated when the state changes
In the MVP, it is not necessary to inject the hook into all messages.

It should appear primarily when there is a state change.

RN-045 — Old hooks must not accumulate indefinitely
The system must avoid maintaining a long sequence of old hooks.

Recommended rule:

keep only the most recent hook;

or replace the previous hook when the state changes;

or summarize old hooks in logs, not in the agent's context.

12. Tools rules
RN-046 — The agent will have access to execute_bash(command)
This tool allows executing commands in the controlled environment.

It must return:

exit code;

summarized stdout;

summarized stderr;

duration;

success/failure status.

Example response:

JSON
{
  "exit_code": 0,
  "stdout": "ok",
  "stderr": "",
  "duration_seconds": 0.42
}
RN-047 — The agent will have access to check_health()
This tool executes the health contract.

Example response:

JSON
{
  "status": "UNHEALTHY",
  "detail": "relation users does not exist",
  "duration_seconds": 0.05
}
RN-048 — The agent will have access to restore_last_snapshot()
This tool requests rollback to the last healthy snapshot.

Example response:

JSON
{
  "ok": true,
  "restore_latency_seconds": 0.184,
  "health_after_restore": "HEALTHY"
}
RN-049 — Tools must have structured outputs
All tools exposed to the agent must return structured responses, preferably in JSON.

This reduces ambiguity and facilitates metrics collection.

RN-050 — Every tool call must be logged
The orchestrator must log:

tool name;

summarized input;

summarized output;

start time;

duration;

success/failure;

error, if any.

Log example:

JSON
{
  "tool": "check_health",
  "input_summary": "{}",
  "output_summary": "UNHEALTHY: relation users does not exist",
  "started_at": "2026-05-07T14:24:05Z",
  "duration_seconds": 0.05,
  "success": true
}
13. Security and control rules
RN-051 — The experimental environment must always run in isolation
The experiment must be executed inside a controlled microVM.

Destructive commands are only acceptable within this isolated environment.

RN-052 — Destructive commands must be logged
The system must log commands that:

remove data;

alter database;

delete files;

restart services;

modify critical configurations;

alter persistent state.

It is not necessary to list all commands in the MVP.

RN-053 — The orchestrator must interrupt unproductive loops
The system must foresee interruption when the agent repeats actions without progress.

In the MVP, the limit can be configurable or implemented in a simple way.

Examples of loop signs:

same tool called repeatedly with same input;

health check failing after several attempts;

agent executing commands without changing state;

excessive time without progress.

RN-054 — The system must log recovery failures
Any failure of rollback, snapshot, or Git fallback must be logged.

Recommended fields:

type of failure;

stage in which it occurred;

error message;

health state before;

health state after;

fallback triggered or not.

RN-055 — The agent must not execute commands outside the microVM
The agent must not have unrestricted access to the host.

The orchestrator must mediate actions to maintain the isolation of the experiment.

14. Main business flow
14.1 Nominal flow
Plaintext
1. Orchestrator starts the microVM
2. Environment boots up API + PostgreSQL
3. Orchestrator creates valid initial state
4. Orchestrator executes health check
5. Health check returns HEALTHY
6. Orchestrator captures last healthy snapshot
7. Orchestrator injects controlled failure
8. Health check returns UNHEALTHY
9. Perception Hook informs the agent
10. Agent can request restore_last_snapshot()
11. Orchestrator executes rollback
12. Orchestrator executes new health check
13. Health check returns HEALTHY
14. Orchestrator logs success
14.2 Flow without available snapshot
Plaintext
1. Environment becomes UNHEALTHY
2. Agent or orchestrator requests rollback
3. Orchestrator verifies last_known_good
4. Snapshot does not exist
5. Orchestrator logs absence of snapshot
6. Orchestrator triggers Git fallback
7. Health check is executed after fallback
8. Result is logged
14.3 Flow with failure in snapshot capture
Plaintext
1. Relevant action is completed
2. Health check returns HEALTHY
3. Orchestrator tries to capture new snapshot
4. Capture fails
5. Orchestrator maintains previous snapshot
6. Failure event is logged
7. System continues operating with last valid snapshot
14.4 Flow with rollback failure
Plaintext
1. Environment is UNHEALTHY
2. Rollback via snapshot is requested
3. Orchestrator tries to restore last_known_good
4. Restoration fails
5. Orchestrator logs error
6. Orchestrator triggers Git fallback
7. Health check is executed
8. Result is logged
15. System states
15.1 Health states
Plaintext
HEALTHY
UNHEALTHY
UNKNOWN
HEALTHY
The health contract passed.

UNHEALTHY
The health contract failed with a known reason.

UNKNOWN
The system could not determine the environment's health.

Examples:

timeout;

microVM does not respond;

endpoint inaccessible;

unexpected error in probe.

15.2 Snapshot states
Plaintext
NO_SNAPSHOT
SNAPSHOT_AVAILABLE
SNAPSHOT_CAPTURE_IN_PROGRESS
SNAPSHOT_CAPTURE_FAILED
SNAPSHOT_INVALID
SNAPSHOT_RESTORED
15.3 Rollback states
Plaintext
ROLLBACK_NOT_REQUESTED
ROLLBACK_REQUESTED
ROLLBACK_IN_PROGRESS
ROLLBACK_SUCCESS
ROLLBACK_FAILED
GIT_FALLBACK_IN_PROGRESS
GIT_FALLBACK_SUCCESS
GIT_FALLBACK_FAILED
16. Suggested JSON report structure
Every execution of the experiment must generate a structured report.

Example:

JSON
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
17. MVP success criteria
The MVP will be considered successful if it demonstrates that:

The orchestrator can start and control the environment.

The health contract correctly identifies healthy and broken states.

The system captures a snapshot only after a healthy health check.

The system maintains only the last healthy snapshot.

The system does not replace a valid snapshot with a broken snapshot.

The Perception Hook informs the agent when the state changes.

The agent can request rollback via a tool.

The orchestrator successfully executes rollback.

The health check passes after rollback.

Git acts as a fallback when the snapshot does not exist or fails.

All relevant tool calls are logged.

Destructive commands are logged.

The flow reduces reliance on manual repair by the agent.

18. Decision points for implementation
18.1 Decision 1 — Full or Diff Snapshot
Current rule:

Full as default;

Diff by configuration.

Suggested implementation:

Plaintext
SNAPSHOT_TYPE=Full
or

Plaintext
SNAPSHOT_TYPE=Diff
18.2 Decision 2 — Where to store the last healthy snapshot
Suggestion:

Plaintext
images/snapshots/last_known_good/
18.3 Decision 3 — When to emit Perception Hook
Current rule:

emit when state changes.

Do not emit on every message to avoid context pollution.

18.4 Decision 4 — Which tools to enable
Default tools:

Plaintext
execute_bash
check_health
restore_last_snapshot
Non-default tool:

Plaintext
query_db
18.5 Decision 5 — Git Fallback
Git Fallback should be triggered when:

there is no snapshot;

snapshot is invalid;

restoration fails;

post-rollback health check does not pass.

19. Future evolutions
The following functionalities should be considered for the future:

19.1 Multiple milestones
Allow several semantic restore points.

Out of the current MVP scope.

19.2 Automatic snapshot via advanced heuristics
Automatically detect risky actions.

Example:

migrations;

package installation;

alteration to critical files;

destructive commands.

19.3 Context Surgeon
Remove bad history from the agent's context and replace it with a compact summary.

19.4 Tombstoning
Log failed attempts as compacted lessons to avoid error repetition.

19.5 Support for multiple health contracts
Allow each project to define its own contract.

19.6 Support for other experimental scenarios
Examples:

API + Redis;

API + queue;

Java application;

environment with tests;

environment with cache;

asynchronous worker.

19.7 Security policies by command
Classify and block destructive commands outside of a safe context.

20. Executive summary of rules
The experimental MVP of SnapVM must follow these central ideas:

SnapVM is an experimental orchestration tool for workflows with AI agents.

The initial scenario is Express API + PostgreSQL.

The system must be designed in a generalizable way for other stateful environments.

The orchestrator controls snapshots, rollback, and health checks.

The agent requests actions via tools, but does not control critical infrastructure.

The system maintains only the last healthy snapshot.

Snapshot is only updated after a healthy health check.

Rollback always attempts to restore the last healthy snapshot.

If snapshot does not exist or fails, Git acts as fallback.

The Perception Hook informs state changes to the agent.

Tools must be generic to avoid excessive specialization in the database.

All tool calls and destructive commands must be logged.

The MVP does not work with multiple milestones, external state, or advanced Context Surgeon.

The goal is to validate the feasibility of stateful rollback as an additional layer to Git.