"""V5 token ledger — phase-level metric accounting and CSV serialization."""

import csv
import os
import time
from dataclasses import asdict, dataclass
from enum import Enum


class Phase(str, Enum):
    DIAGNOSIS = "diagnosis"
    PLANNING = "planning"
    MANUAL_REPAIR = "manual_repair"
    SNAPSHOT_RESTORE = "snapshot_restore"
    CHECKPOINT_SAVE = "checkpoint_save"
    CHECKPOINT_RESTORE = "checkpoint_restore"
    VALIDATION = "validation"
    FINAL_RESPONSE = "final_response"
    OTHER = "other"


CSV_COLUMNS = [
    "run_id", "trial_id", "experiment", "approach", "strategy",
    "success", "failure_reason",
    "tokens_total", "tokens_diagnosis", "tokens_planning",
    "tokens_manual_repair", "tokens_snapshot_restore",
    "tokens_checkpoint_save", "tokens_checkpoint_restore",
    "tokens_validation", "tokens_final_response", "tokens_other",
    "latency_total", "tool_calls", "context_pollution",
    "checkpoints_created", "checkpoints_restored",
    "start_time", "end_time", "trial_status", "seed", "scenario_id", "notes",
]


@dataclass
class TrialRow:
    run_id: str = ""
    trial_id: str = ""
    experiment: str = "v5"
    approach: str = ""
    strategy: str = ""
    success: bool = False
    failure_reason: str = ""
    tokens_total: int = 0
    tokens_diagnosis: int = 0
    tokens_planning: int = 0
    tokens_manual_repair: int = 0
    tokens_snapshot_restore: int = 0
    tokens_checkpoint_save: int = 0
    tokens_checkpoint_restore: int = 0
    tokens_validation: int = 0
    tokens_final_response: int = 0
    tokens_other: int = 0
    latency_total: float = 0.0
    tool_calls: int = 0
    context_pollution: int = 0
    checkpoints_created: int = 0
    checkpoints_restored: int = 0
    start_time: str = ""
    end_time: str = ""
    trial_status: str = ""
    seed: str = ""
    scenario_id: str = "v5_long_task"
    notes: str = ""

    def phase_sum(self) -> int:
        return (
            self.tokens_diagnosis
            + self.tokens_planning
            + self.tokens_manual_repair
            + self.tokens_snapshot_restore
            + self.tokens_checkpoint_save
            + self.tokens_checkpoint_restore
            + self.tokens_validation
            + self.tokens_final_response
            + self.tokens_other
        )

    def validate(self) -> bool:
        """Return True if the phase totals match the recorded total."""
        return self.tokens_total == self.phase_sum()

    def to_dict(self) -> dict:
        data = asdict(self)
        data["success"] = str(data["success"])
        return data


class TokenLedger:
    """Accumulates token events by phase and serializes a trial row."""

    def __init__(self, run_id: str, approach: str, trial_number: int, seed: str = ""):
        self.run_id = run_id
        self.trial_id = f"{run_id}_{trial_number:03d}"
        self.approach = approach
        self.seed = seed
        self._phase_tokens = {phase: 0 for phase in Phase}
        self._tool_calls = 0
        self._context_pollution = 0
        self._checkpoints_created = 0
        self._checkpoints_restored = 0
        self._excluded_time = 0.0
        self._start = time.time()
        self._start_iso = time.strftime("%Y-%m-%dT%H:%M:%S")

    def record(self, phase: Phase, prompt_tokens: int, completion_tokens: int):
        self._phase_tokens[phase] += prompt_tokens + completion_tokens

    def record_tool_call(self):
        self._tool_calls += 1

    def record_checkpoint_save(self):
        self._checkpoints_created += 1

    def record_checkpoint_restore(self):
        self._checkpoints_restored += 1

    def set_context_pollution(self, tokens: int):
        self._context_pollution = tokens

    def exclude_time(self, seconds: float):
        """Exclude rate-limit backoff wait from the final latency."""
        self._excluded_time += seconds

    def finalize(self, success: bool, failure_reason: str = "", notes: str = "") -> TrialRow:
        end_iso = time.strftime("%Y-%m-%dT%H:%M:%S")
        latency = time.time() - self._start - self._excluded_time
        total = sum(self._phase_tokens.values())

        row = TrialRow(
            run_id=self.run_id,
            trial_id=self.trial_id,
            approach=self.approach,
            strategy=self.approach,
            success=success,
            failure_reason=failure_reason,
            tokens_total=total,
            tokens_diagnosis=self._phase_tokens[Phase.DIAGNOSIS],
            tokens_planning=self._phase_tokens[Phase.PLANNING],
            tokens_manual_repair=self._phase_tokens[Phase.MANUAL_REPAIR],
            tokens_snapshot_restore=self._phase_tokens[Phase.SNAPSHOT_RESTORE],
            tokens_checkpoint_save=self._phase_tokens[Phase.CHECKPOINT_SAVE],
            tokens_checkpoint_restore=self._phase_tokens[Phase.CHECKPOINT_RESTORE],
            tokens_validation=self._phase_tokens[Phase.VALIDATION],
            tokens_final_response=self._phase_tokens[Phase.FINAL_RESPONSE],
            tokens_other=self._phase_tokens[Phase.OTHER],
            latency_total=latency,
            tool_calls=self._tool_calls,
            context_pollution=self._context_pollution,
            checkpoints_created=self._checkpoints_created,
            checkpoints_restored=self._checkpoints_restored,
            start_time=self._start_iso,
            end_time=end_iso,
            trial_status="valid",
            seed=self.seed,
            notes=notes,
        )

        if not row.validate():
            row.trial_status = "instrumentation-invalid"

        return row


def write_csv_row(path: str, row: TrialRow):
    """Append a row to CSV, creating the file and header when needed."""
    file_exists = os.path.isfile(path)
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)

    with open(path, "a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row.to_dict())
