"""V5 analysis and plotting pipeline."""

import argparse
import csv
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Union

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

BASE_DIR = Path(__file__).resolve().parents[1]
CSV_PATH = BASE_DIR / "results" / "v5_trials.csv"
PLOT_DIR = BASE_DIR / "results" / "plots"

PHASE_COLUMNS = [
    "tokens_diagnosis",
    "tokens_planning",
    "tokens_manual_repair",
    "tokens_snapshot_restore",
    "tokens_checkpoint_save",
    "tokens_checkpoint_restore",
    "tokens_validation",
    "tokens_final_response",
    "tokens_other",
]

PHASE_LABELS = [column.replace("tokens_", "").replace("_", " ").title() for column in PHASE_COLUMNS]


def load_csv(path: Union[str, Path]) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def group_by_approach(rows: list[dict]) -> dict[str, list[dict]]:
    groups = defaultdict(list)
    for row in rows:
        groups[row["approach"]].append(row)
    return dict(groups)


def _stats(values: list[float]) -> dict:
    if not values:
        return {"mean": 0, "median": 0, "stdev": 0, "n": 0}
    return {
        "mean": statistics.mean(values),
        "median": statistics.median(values),
        "stdev": statistics.stdev(values) if len(values) > 1 else 0,
        "n": len(values),
    }


def compute_summary(groups: dict[str, list[dict]]) -> dict:
    summary = {}
    for approach, rows in groups.items():
        n = len(rows)
        successes = sum(1 for row in rows if row["success"] == "True")
        phase_totals = {column: sum(int(row[column]) for row in rows) for column in PHASE_COLUMNS}
        total_phase_tokens = sum(phase_totals.values())
        summary[approach] = {
            "n": n,
            "success_count": successes,
            "success_pct": (successes / n * 100) if n else 0,
            "tokens_total": _stats([float(row["tokens_total"]) for row in rows]),
            "latency_total": _stats([float(row["latency_total"]) for row in rows]),
            "context_pollution": _stats([float(row["context_pollution"]) for row in rows]),
            "tool_calls": _stats([float(row["tool_calls"]) for row in rows]),
            "checkpoints_created": _stats([float(row["checkpoints_created"]) for row in rows]),
            "checkpoints_restored": _stats([float(row["checkpoints_restored"]) for row in rows]),
            "phase_totals": phase_totals,
            "phase_share": {
                column: (phase_totals[column] / total_phase_tokens * 100) if total_phase_tokens else 0
                for column in PHASE_COLUMNS
            },
        }
    return summary


def print_summary(summary: dict):
    print("\n" + "=" * 70)
    print("V5 ENHANCED EXPERIMENT — SUMMARY")
    print("=" * 70)
    for approach, stats in summary.items():
        print(f"\n── {approach} (n={stats['n']}) ──")
        print(f"  Success: {stats['success_count']}/{stats['n']} ({stats['success_pct']:.1f}%)")
        for metric in [
            "tokens_total",
            "latency_total",
            "context_pollution",
            "tool_calls",
            "checkpoints_created",
            "checkpoints_restored",
        ]:
            values = stats[metric]
            print(
                f"  {metric}: mean={values['mean']:.1f} "
                f"median={values['median']:.1f} stdev={values['stdev']:.1f}"
            )
        print("  Phase token share:")
        for column in PHASE_COLUMNS:
            pct = stats["phase_share"][column]
            if pct > 0.1:
                print(f"    {column}: {pct:.1f}%")


def _ensure_plot_dir(plot_dir: Union[str, Path]):
    Path(plot_dir).mkdir(parents=True, exist_ok=True)


def plot_success_rate(groups: dict, summary: dict, plot_dir: Union[str, Path]):
    approaches = list(groups.keys())
    rates = [summary[approach]["success_pct"] for approach in approaches]
    counts = [f"{summary[approach]['success_count']}/{summary[approach]['n']}" for approach in approaches]

    fig, ax = plt.subplots(figsize=(6, 4))
    bars = ax.bar(approaches, rates, color=["#4C72B0", "#55A868"], width=0.5)
    for bar, count, rate in zip(bars, counts, rates):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 1,
            f"{rate:.1f}%\n({count})",
            ha="center",
            va="bottom",
            fontsize=10,
        )
    ax.set_ylabel("Success Rate (%)")
    ax.set_title("V5: Success Rate by Approach")
    ax.set_ylim(0, 110)
    plt.tight_layout()
    plt.savefig(Path(plot_dir) / "v5_success_rate.png", dpi=150)
    plt.close()


def plot_success_strip(groups: dict, plot_dir: Union[str, Path]):
    fig, ax = plt.subplots(figsize=(8, 3))
    for index, (approach, rows) in enumerate(groups.items()):
        outcomes = [1 if row["success"] == "True" else 0 for row in rows]
        jitter = np.random.default_rng(42).uniform(-0.1, 0.1, len(outcomes))
        colors = ["#55A868" if outcome else "#C44E52" for outcome in outcomes]
        ax.scatter([index + delta for delta in jitter], outcomes, c=colors, alpha=0.7, s=30)
        ax.text(index, -0.15, approach, ha="center", fontsize=9)
    ax.set_yticks([0, 1])
    ax.set_yticklabels(["Fail", "Pass"])
    ax.set_xlim(-0.5, len(groups) - 0.5)
    ax.set_title("V5: Per-Trial Outcomes")
    ax.set_xticks([])
    plt.tight_layout()
    plt.savefig(Path(plot_dir) / "v5_success_strip.png", dpi=150)
    plt.close()


def plot_context_pollution(groups: dict, plot_dir: Union[str, Path]):
    fig, ax = plt.subplots(figsize=(6, 4))
    data = [[float(row["context_pollution"]) for row in rows] for rows in groups.values()]
    ax.violinplot(data, positions=range(len(groups)), showmeans=True, showmedians=True)
    ax.set_xticks(range(len(groups)))
    ax.set_xticklabels(list(groups.keys()))
    ax.set_ylabel("Context Pollution (tokens)")
    ax.set_title("V5: Context Pollution")
    plt.tight_layout()
    plt.savefig(Path(plot_dir) / "v5_context_pollution.png", dpi=150)
    plt.close()


def plot_tokens_violin(groups: dict, plot_dir: Union[str, Path]):
    fig, ax = plt.subplots(figsize=(6, 4))
    data = [[float(row["tokens_total"]) for row in rows] for rows in groups.values()]
    ax.violinplot(data, positions=range(len(groups)), showmeans=True, showmedians=True)
    for index, values in enumerate(data):
        jitter = np.random.default_rng(42).uniform(-0.05, 0.05, len(values))
        ax.scatter([index + delta for delta in jitter], values, alpha=0.4, s=15, color="black")
    ax.set_xticks(range(len(groups)))
    ax.set_xticklabels(list(groups.keys()))
    ax.set_ylabel("Total Tokens")
    ax.set_title("V5: Total Token Usage")
    plt.tight_layout()
    plt.savefig(Path(plot_dir) / "v5_tokens_violin.png", dpi=150)
    plt.close()


def plot_phase_tokens_stacked(groups: dict, summary: dict, plot_dir: Union[str, Path]):
    approaches = list(groups.keys())
    fig, ax = plt.subplots(figsize=(8, 5))
    bottoms = np.zeros(len(approaches))
    colors = plt.cm.Set3(np.linspace(0, 1, len(PHASE_COLUMNS)))

    for index, column in enumerate(PHASE_COLUMNS):
        values = [summary[approach]["phase_totals"][column] for approach in approaches]
        ax.bar(approaches, values, bottom=bottoms, color=colors[index], label=PHASE_LABELS[index])
        bottoms += np.array(values, dtype=float)

    ax.set_ylabel("Total Tokens (sum across trials)")
    ax.set_title("V5: Phase Token Distribution (Stacked)")
    ax.legend(bbox_to_anchor=(1.05, 1), loc="upper left", fontsize=8)
    plt.tight_layout()
    plt.savefig(Path(plot_dir) / "v5_phase_tokens_stacked.png", dpi=150, bbox_inches="tight")
    plt.close()


def plot_phase_tokens_share(groups: dict, summary: dict, plot_dir: Union[str, Path]):
    approaches = list(groups.keys())
    fig, axes = plt.subplots(1, len(approaches), figsize=(5 * len(approaches), 5))
    if len(approaches) == 1:
        axes = [axes]
    colors = plt.cm.Set3(np.linspace(0, 1, len(PHASE_COLUMNS)))

    for axis, approach in zip(axes, approaches):
        shares = [summary[approach]["phase_share"][column] for column in PHASE_COLUMNS]
        nonzero = [(share, label, color) for share, label, color in zip(shares, PHASE_LABELS, colors) if share > 0.5]
        if nonzero:
            values, labels, palette = zip(*nonzero)
            axis.pie(values, labels=labels, colors=palette, autopct="%1.0f%%", textprops={"fontsize": 8})
        axis.set_title(approach)

    plt.suptitle("V5: Phase Token Share", fontsize=12)
    plt.tight_layout()
    plt.savefig(Path(plot_dir) / "v5_phase_tokens_share.png", dpi=150, bbox_inches="tight")
    plt.close()


def run_analysis(csv_path: Union[str, Path] = CSV_PATH, plot_dir: Union[str, Path] = PLOT_DIR):
    rows = load_csv(csv_path)
    groups = group_by_approach(rows)
    summary = compute_summary(groups)

    print_summary(summary)

    _ensure_plot_dir(plot_dir)
    plot_success_rate(groups, summary, plot_dir)
    plot_success_strip(groups, plot_dir)
    plot_context_pollution(groups, plot_dir)
    plot_tokens_violin(groups, plot_dir)
    plot_phase_tokens_stacked(groups, summary, plot_dir)
    plot_phase_tokens_share(groups, summary, plot_dir)

    print(f"\nPlots saved to {plot_dir}/")


def main():
    parser = argparse.ArgumentParser(description="V5 analysis and plotting")
    parser.add_argument("--csv", default=str(CSV_PATH), help="Input CSV path")
    parser.add_argument("--plots", default=str(PLOT_DIR), help="Output plot directory")
    args = parser.parse_args()
    run_analysis(csv_path=args.csv, plot_dir=args.plots)


if __name__ == "__main__":
    main()
