"""Tests for V5 metrics schema validation and token aggregation."""

import csv
import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout

from analysis import v5_plots
from src.orchestrator.dashboard import Dashboard
from src.orchestrator.metrics import CSV_COLUMNS, Phase, TokenLedger, TrialRow, write_csv_row


class TestTrialRow(unittest.TestCase):
    def test_phase_sum_matches_total(self):
        row = TrialRow(tokens_total=100, tokens_diagnosis=40, tokens_planning=30, tokens_validation=30)
        self.assertTrue(row.validate())

    def test_phase_sum_mismatch_fails_validation(self):
        row = TrialRow(tokens_total=999, tokens_diagnosis=10)
        self.assertFalse(row.validate())

    def test_to_dict_has_all_csv_columns(self):
        row = TrialRow()
        data = row.to_dict()
        for column in CSV_COLUMNS:
            self.assertIn(column, data)

    def test_success_serialized_as_string(self):
        row = TrialRow(success=True)
        self.assertEqual(row.to_dict()["success"], "True")


class TestTokenLedger(unittest.TestCase):
    def test_record_accumulates_by_phase(self):
        ledger = TokenLedger(run_id="r1", approach="Checkpoint", trial_number=1)
        ledger.record(Phase.DIAGNOSIS, prompt_tokens=50, completion_tokens=20)
        ledger.record(Phase.DIAGNOSIS, prompt_tokens=10, completion_tokens=5)
        ledger.record(Phase.VALIDATION, prompt_tokens=30, completion_tokens=10)
        row = ledger.finalize(success=True)
        self.assertEqual(row.tokens_diagnosis, 85)
        self.assertEqual(row.tokens_validation, 40)
        self.assertEqual(row.tokens_total, 125)
        self.assertTrue(row.validate())

    def test_finalize_sets_instrumentation_invalid_on_mismatch(self):
        ledger = TokenLedger(run_id="r1", approach="Standard/Manual", trial_number=1)
        ledger.record(Phase.DIAGNOSIS, 10, 10)
        row = ledger.finalize(success=True)
        row.tokens_total = 999
        self.assertFalse(row.validate())

    def test_checkpoint_counters(self):
        ledger = TokenLedger(run_id="r1", approach="Checkpoint", trial_number=1)
        ledger.record_checkpoint_save()
        ledger.record_checkpoint_save()
        ledger.record_checkpoint_restore()
        ledger.record(Phase.CHECKPOINT_SAVE, 10, 5)
        row = ledger.finalize(success=True)
        self.assertEqual(row.checkpoints_created, 2)
        self.assertEqual(row.checkpoints_restored, 1)

    def test_standard_approach_zero_checkpoints(self):
        ledger = TokenLedger(run_id="r1", approach="Standard/Manual", trial_number=1)
        ledger.record(Phase.MANUAL_REPAIR, 50, 50)
        row = ledger.finalize(success=False, failure_reason="table missing")
        self.assertEqual(row.checkpoints_created, 0)
        self.assertEqual(row.checkpoints_restored, 0)

    def test_tool_call_counter(self):
        ledger = TokenLedger(run_id="r1", approach="Standard/Manual", trial_number=1)
        ledger.record_tool_call()
        ledger.record_tool_call()
        ledger.record_tool_call()
        ledger.record(Phase.DIAGNOSIS, 10, 10)
        row = ledger.finalize(success=True)
        self.assertEqual(row.tool_calls, 3)


class TestWriteCsv(unittest.TestCase):
    def test_csv_has_correct_header_and_row(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "test.csv")
            row = TrialRow(
                run_id="abc",
                trial_id="abc_001",
                approach="Checkpoint",
                success=True,
                tokens_total=100,
                tokens_diagnosis=100,
            )
            write_csv_row(path, row)
            write_csv_row(path, row)

            with open(path, newline="", encoding="utf-8") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, CSV_COLUMNS)
                rows = list(reader)
                self.assertEqual(len(rows), 2)
                self.assertEqual(rows[0]["run_id"], "abc")
                self.assertEqual(rows[0]["success"], "True")


class TestV5Analysis(unittest.TestCase):
    def test_analysis_writes_expected_plots(self):
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = os.path.join(tmp, "v5_trials.csv")
            plot_dir = os.path.join(tmp, "plots")

            rows = [
                TrialRow(
                    run_id="run1",
                    trial_id="run1_001",
                    approach="Standard/Manual",
                    strategy="Standard/Manual",
                    success=True,
                    tokens_total=120,
                    tokens_diagnosis=40,
                    tokens_planning=20,
                    tokens_manual_repair=40,
                    tokens_validation=20,
                ),
                TrialRow(
                    run_id="run1",
                    trial_id="run1_002",
                    approach="Checkpoint",
                    strategy="Checkpoint",
                    success=True,
                    tokens_total=140,
                    tokens_diagnosis=30,
                    tokens_planning=20,
                    tokens_checkpoint_save=10,
                    tokens_checkpoint_restore=10,
                    tokens_validation=70,
                ),
            ]
            for row in rows:
                write_csv_row(csv_path, row)

            with redirect_stdout(io.StringIO()):
                v5_plots.run_analysis(csv_path=csv_path, plot_dir=plot_dir)

            expected = {
                "v5_success_rate.png",
                "v5_success_strip.png",
                "v5_context_pollution.png",
                "v5_tokens_violin.png",
                "v5_phase_tokens_stacked.png",
                "v5_phase_tokens_share.png",
            }
            produced = set(os.listdir(plot_dir))
            self.assertTrue(expected.issubset(produced))


class TestDashboard(unittest.TestCase):
    def test_on_trial_end_updates_counters(self):
        with redirect_stdout(io.StringIO()):
            dash = Dashboard(run_id="run1", total_trials=2)
            dash.on_trial_end(TrialRow(success=True, tokens_total=10, latency_total=1.2))

        self.assertEqual(dash.completed, 1)
        self.assertEqual(dash.successes, 1)


if __name__ == "__main__":
    unittest.main()
