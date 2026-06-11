"""V5 dashboard — simple terminal progress output."""

import time

from .metrics import TrialRow


class Dashboard:
    """Small print-based progress display for v5 trials."""

    def __init__(self, run_id: str, total_trials: int, model: str = "gpt-4o-mini"):
        self.run_id = run_id
        self.total_trials = total_trials
        self.model = model
        self.completed = 0
        self.successes = 0
        self._start = time.time()
        print(f"\n{'═' * 60}")
        print(f"  V5 Experiment | run={run_id} | model={model} | trials={total_trials}")
        print(f"{'═' * 60}")

    def start(self):
        pass

    def stop(self):
        pass

    def log(self, msg: str, style: str = ""):
        print(f"  {msg}")

    def set_approach(self, approach: str):
        print(f"\n── {approach} ──")

    def on_trial_start(self, trial_num: int):
        print(f"  [{trial_num}/{self.total_trials}] running...", end="", flush=True)

    def on_model_call(self, phase: str, prompt_tok: int, comp_tok: int):
        pass

    def on_tool_call(self, name: str, duration_ms: float = 0):
        pass

    def on_checkpoint_save(self, label: str, latency: float):
        pass

    def on_checkpoint_restore(self, latency: float):
        pass

    def on_trial_end(self, row: TrialRow):
        self.completed += 1
        if row.success:
            self.successes += 1
        rate = self.successes / self.completed * 100
        elapsed = time.time() - self._start
        eta = (elapsed / self.completed) * (self.total_trials - self.completed)
        status = "✓" if row.success else "✗"
        print(
            f" {status} tok={row.tokens_total} lat={row.latency_total:.1f}s | "
            f"rate={self.successes}/{self.completed} ({rate:.0f}%) | ETA {eta:.0f}s"
        )

    def on_infra_error(self, error: str):
        print(f"  ⚠ INFRA: {error[:80]}")

    def on_experiment_done(self):
        elapsed = time.time() - self._start
        print(f"\n{'═' * 60}")
        print(f"  DONE | {self.completed} trials | {self.successes} passed | {elapsed:.0f}s")
        print(f"{'═' * 60}")
