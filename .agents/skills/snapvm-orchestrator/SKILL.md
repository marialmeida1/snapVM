---
name: snapvm-orchestrator
description: >
  Workflow for developing, testing, and extending the SnapVM orchestrator experiment.
  Use when the user asks to modify the orchestrator code, add new experiments,
  implement new phases (V4 agent autonomy), or debug the Firecracker integration.
---

# SnapVM Orchestrator Development Skill

## When to Activate

Use this skill when the user asks to:
- Modify or extend the Python orchestrator (`Codigo/experiments/2_orchestrator_v1/src/orchestrator/`)
- Add new experiment phases (e.g., V4 Agent Autonomy)
- Change the health contract, snapshot logic, or agent tools
- Debug Firecracker API interactions
- Update the guest application (server.js, init.sh, Dockerfile)
- Write or run tests for the orchestrator

## Project Context

Read the steering files first:
- `.kiro/steering/project-overview.md` — architecture and current stage
- `.kiro/steering/codebase-map.md` — file locations and module purposes
- `.kiro/steering/business-rules-summary.md` — rules that constrain implementation

The authoritative business rules are in `context-and-rules.md` at the repo root. Consult it for any rule numbered RN-001 through RN-055.

## Development Workflow

### 1. Understand the Change

Before modifying code:
1. Read the relevant source files in `Codigo/experiments/2_orchestrator_v1/src/orchestrator/`
2. Check if the change aligns with business rules (especially agent boundaries RN-032–039)
3. Identify which experiment phase the change belongs to (see roadmap in `docs/experiments/orchestrator-v1-roadmap.md`)

### 2. Implementation Conventions

- **Python style**: Follow existing patterns in the codebase (no type hints used, docstrings on public functions)
- **CLI commands**: Added via `argparse` subparsers in `main.py`
- **New modules**: Add to `src/orchestrator/` package, import in `main.py`
- **Firecracker API calls**: Go through `FirecrackerClient` methods (never raw HTTP)
- **Health checks**: Always use `contract.verify_state()` — returns `(passed: bool, detail: str)`
- **Snapshot operations**: Use `snapshot.capture()` and `snapshot.restore()` — they handle pause/resume
- **Agent tools**: Defined in `AgentLoop.__init__` as OpenAI function-calling schema
- **Telemetry**: Wrap timing with `time.perf_counter()`, save reports to `results/`

### 3. Key Constraints

- The agent must NEVER directly create/delete snapshots (RN-032, RN-037)
- The orchestrator must NEVER promote an unhealthy state to `last_known_good` (RN-009)
- All tool calls must be logged with structured JSON (RN-050)
- The experiment runs ONLY inside the microVM — no host-side destructive operations (RN-051, RN-055)
- Guest networking: host=172.16.0.1/24, guest=172.16.0.2, TAP=vmtap0

### 4. Testing

Run tests from the experiment directory:
```bash
cd Codigo/experiments/2_orchestrator_v1
python -m pytest tests/ -v
```

Tests use `unittest` with `mock.patch` for Firecracker interactions. When adding new functionality:
- Mock the `FirecrackerClient` (don't require a running VM)
- Test error paths (snapshot failure, restore failure, network timeout)
- Verify cleanup (VM always killed in `finally` blocks)

### 5. Next Planned Phase: V4 Agent Autonomy

Per the roadmap, the next implementation phase includes:
- **Task 7.1**: Expose `capture_snapshot` and `restore_snapshot` as agent tools
- **Task 7.2**: Automatic health injection (Perception Hook prepended to every agent message)
- **Task 7.3**: Complex milestone navigation (agent creates save points before risky operations)

This phase shifts snapshot control partially to the agent — a deliberate evolution from the MVP rules. Document any rule deviations in the experiment docs.

## File Quick Reference

| What | Where |
|------|-------|
| Main orchestrator logic | `Codigo/experiments/2_orchestrator_v1/src/orchestrator/main.py` |
| Firecracker API client | `Codigo/experiments/2_orchestrator_v1/src/orchestrator/firecracker_client.py` |
| Snapshot engine | `Codigo/experiments/2_orchestrator_v1/src/orchestrator/snapshot.py` |
| Health contract | `Codigo/experiments/2_orchestrator_v1/src/orchestrator/contract.py` |
| Network setup | `Codigo/experiments/2_orchestrator_v1/src/orchestrator/network.py` |
| Agent loop (OpenAI) | `Codigo/experiments/2_orchestrator_v1/src/orchestrator/agent.py` |
| Guest Express server | `Codigo/experiments/2_orchestrator_v1/src/server.js` |
| Guest init script | `Codigo/experiments/2_orchestrator_v1/init.sh` |
| Guest Dockerfile | `Codigo/experiments/2_orchestrator_v1/Dockerfile` |
| Tests | `Codigo/experiments/2_orchestrator_v1/tests/test_orchestrator_v1.py` |
| Business rules | `context-and-rules.md` |
| Experiment results docs | `Codigo/experiments/2_orchestrator_v1/docs/experiments/` |
