# SnapVM — Business Rules Summary

> Condensed from `context-and-rules.md` (55 rules: RN-001 to RN-055). Refer to the full document for details.

## Git Rollback Definition

"Git rollback" means the agent performs **standard manual recovery** using whatever tools it has — git commands, SQL queries, bash, rollback migrations. It is NOT just `git reset --hard`. It's the full agent-driven repair loop that represents how agents work today without SnapVM. This is the baseline we always compare against. It also serves as the production fallback when snapshots are unavailable or inapplicable (e.g., simple code-only changes).

## Scope Boundaries (RN-001 to RN-005)

- SnapVM is an **experimental** orchestration tool, not a production product.
- MVP focus: workflows with AI agents (not human end-users).
- SnapVM is an **additional layer** to Git, not a replacement.
- MVP scenario: Express API + PostgreSQL + `/health` + `DROP TABLE users` failure.
- Design must be **generalizable** to other stateful environments.

## Health Rules (RN-006 to RN-013)

- Every workflow requires an explicit **health contract**.
- MVP contract: `/health` endpoint validates API + PostgreSQL + `users` table.
- Only **HEALTHY** states can replace the last healthy snapshot.
- Partial states are logged but never promoted.
- Health check runs after every relevant action (migration, code change, rollback, restart).
- Agent cannot contest the health check result.

## Snapshot Rules (RN-014 to RN-022)

- Only the **orchestrator** creates snapshots (never the agent).
- Flow: `relevant action → health check → if HEALTHY → capture snapshot`.
- System keeps only **one** healthy snapshot (`last_known_good`).
- Old snapshot removed only **after** new one is validated.
- If capture fails, previous snapshot remains valid.
- Snapshot type configurable: `Full` (default) or `Diff`.
- Metadata logged: `snapshot_id`, `created_at`, `health_status`, `trigger`, `snapshot_type`, `storage_bytes`.
- Storage path: `images/snapshots/last_known_good/` (memory.bin + vmstate + metadata.json).

## Rollback Rules (RN-023 to RN-031)

- Rollback triggered when health returns UNHEALTHY/UNKNOWN/error/timeout.
- Always restores `last_known_good` (no multi-snapshot selection in MVP).
- Orchestrator executes rollback (even if agent requests it).
- Post-rollback health check required — states: `ROLLBACK_SUCCESS_HEALTHY`, `ROLLBACK_FAILED_UNHEALTHY`.
- Agent informed via Perception Hook after rollback.
- Failed attempt can be summarized (basic Context Surgeon).
- **Fallback chain**: snapshot → Git (if no snapshot or restore fails).

## Agent Rules (RN-032 to RN-039)

- Agent **cannot** create or delete snapshots.
- Agent **can** be informed rollback is available (not ordered to use it).
- Agent has **no** direct access to: Firecracker process, snapshot files, host commands.
- Agent tools (MVP): `execute_bash(command)`, `check_health()`, `restore_last_snapshot()`.
- `query_db(sql)` exists but is NOT a main tool (too DB-specific).

## Perception Hook Rules (RN-040 to RN-045)

- Emitted on state transitions (HEALTHY→UNHEALTHY, rollback executed, etc.).
- Contains: `health_status`, `health_detail`, `last_known_good_snapshot`, `rollback_available`, `checked_at`.
- Must be **short** — avoid context pollution.
- Informs but does NOT decide for the agent.
- Only most recent hook kept (old hooks don't accumulate).

## Tool Output Rules (RN-046 to RN-050)

- All tools return **structured JSON**.
- Every tool call is **logged** (tool name, input, output, timestamp, duration, success/failure).

## Security Rules (RN-051 to RN-055)

- Experiment runs in **isolated** microVM only.
- Destructive commands are logged.
- Orchestrator interrupts unproductive agent loops.
- Recovery failures are logged with full context.
- Agent cannot execute commands outside the microVM.

## System States

```
Health:    HEALTHY | UNHEALTHY | UNKNOWN
Snapshot:  NO_SNAPSHOT | SNAPSHOT_AVAILABLE | CAPTURE_IN_PROGRESS | CAPTURE_FAILED | INVALID | RESTORED
Rollback:  NOT_REQUESTED | REQUESTED | IN_PROGRESS | SUCCESS | FAILED | GIT_FALLBACK_*
```

## Nominal Flow

```
1. Boot microVM → 2. Create valid state → 3. Health check (HEALTHY)
→ 4. Capture snapshot → 5. Inject failure → 6. Health check (UNHEALTHY)
→ 7. Perception Hook → 8. Agent requests restore → 9. Orchestrator rollback
→ 10. Health check (HEALTHY) → 11. Log success
```

## MVP Success Criteria

The MVP succeeds if it demonstrates:
- Orchestrator controls environment lifecycle end-to-end
- Health contract correctly identifies healthy vs broken states
- Snapshot captured only after healthy check; never replaced by broken state
- Agent can request rollback via tool; orchestrator executes it
- Health passes after rollback
- Git acts as fallback when snapshot unavailable
- All tool calls and destructive commands logged
- Flow reduces reliance on manual agent repair
