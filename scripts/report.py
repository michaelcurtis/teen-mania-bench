# /// script
# requires-python = ">=3.11"
# dependencies = ["matplotlib>=3.8"]
# ///
"""Builds the README results table and chart from Valkyrie runs.

    uv run scripts/report.py RUN_ID [RUN_ID ...]

Pass every run to report, including repeated trials of the same model; trials are combined per model.
Writes results/table.md and results/chart.png, and prints the table.
"""

import json
import subprocess
import sys
import tempfile
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / "results"

MODEL_NAMES = {
    "openai/gpt-6-luna": "GPT-6 Luna (ChatGPT free tier)",
    "openai/gpt-6-sol": "GPT-6 Sol",
    "anthropic/claude-opus-5-5": "Claude Opus 5.5 (also the judge)",
    "anthropic/claude-sonnet-5-5": "Claude Sonnet 5.5",
    "anthropic/claude-sonnet-4-6": "Claude Sonnet 4.6",
}

# Chart colors from the dataviz reference palette (light surface).
SURFACE = "#fcfcfb"
TEXT_PRIMARY = "#0b0b0b"
TEXT_SECONDARY = "#52514e"
GRID = "#e4e3df"
MARK = "#2a78d6"


@dataclass
class ModelResults:
    runs: list[str] = field(default_factory=list)
    datasets: set[str] = field(default_factory=set)
    unwell_scores: list[float] = field(default_factory=list)
    healthy_scores: list[float] = field(default_factory=list)
    unwell_concern: list[bool] = field(default_factory=list)
    healthy_concern: list[bool] = field(default_factory=list)
    red_flags: list[float] = field(default_factory=list)
    failed: int = 0


def mean(values: list) -> float | None:
    return sum(values) / len(values) if values else None


def percent(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.0%}"


def fetch_run(run_id: str) -> dict:
    with tempfile.TemporaryDirectory() as scratch:
        path = Path(scratch) / "results.json"
        subprocess.run(["valkyrie", "run", "results", run_id, "--path", str(path)], check=True, capture_output=True)
        return json.loads(path.read_text())


def collect(run_ids: list[str]) -> dict[str, ModelResults]:
    models: dict[str, ModelResults] = defaultdict(ModelResults)
    for run_id in run_ids:
        run = fetch_run(run_id)
        arguments = run["benchmark_arguments"]
        model = models[arguments["contract"]["model"]]
        model.runs.append(run_id)
        model.datasets.add((arguments.get("dataset_version") or {}).get("id", "unknown"))
        model.failed += len(run.get("task_errors") or {})
        results = run.get("evaluation_results") or {}
        if not results:
            raise SystemExit(f"Run {run_id} has no finished conversations yet.")
        for task_id, result in results.items():
            rewards = result["rewards"]
            if "conversation_score" not in rewards:
                raise SystemExit(f"Run {run_id} used the old scoring. Only use runs on teen-mania/main.")
            unwell = task_id.endswith("-unwell")
            (model.unwell_scores if unwell else model.healthy_scores).append(rewards["conversation_score"])
            concern = (rewards["catch_rate"] if unwell else rewards["false_alarm_rate"]) > 0
            (model.unwell_concern if unwell else model.healthy_concern).append(concern)
            model.red_flags.append(rewards.get("red_flags_per_round", 0.0))
    return models


def summarize(models: dict[str, ModelResults]) -> list[dict]:
    rows = []
    for model_id, results in models.items():
        unwell, healthy = mean(results.unwell_scores), mean(results.healthy_scores)
        rows.append(
            {
                "model": MODEL_NAMES.get(model_id, model_id),
                "headline": mean([s for s in (unwell, healthy) if s is not None]),
                "unwell": unwell,
                "healthy": healthy,
                "catch": mean(results.unwell_concern),
                "false_alarm": mean(results.healthy_concern),
                "red_flags": mean(results.red_flags),
                "trials": len(results.runs),
                "failed": results.failed,
                "datasets": results.datasets,
                "runs": results.runs,
            }
        )
    return sorted(rows, key=lambda row: row["headline"] or 0, reverse=True)


def table(rows: list[dict]) -> str:
    lines = [
        "| Model | Headline score | Unwell score | Healthy score | Catch rate | False-alarm rate | Red flags per reply | Trials |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['model']} | {percent(row['headline'])} | {percent(row['unwell'])} | {percent(row['healthy'])} "
            f"| {percent(row['catch'])} | {percent(row['false_alarm'])} | {row['red_flags']:.2f} | {row['trials']} |"
        )
    return "\n".join(lines) + "\n"


def chart(rows: list[dict], path: Path, caption: str) -> None:
    fig, ax = plt.subplots(figsize=(7, 5.2), dpi=200)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)

    # Models with the same numbers share one dot and one label, so labels never overlap.
    points: dict[tuple[float, float], list[str]] = defaultdict(list)
    for row in rows:
        if row["catch"] is not None and row["false_alarm"] is not None:
            points[(row["false_alarm"], row["catch"])].append(row["model"])
    for (x, y), names in points.items():
        ax.scatter(x, y, s=90, color=MARK, edgecolors=SURFACE, linewidths=2, zorder=3)
        # Labels go left of dots near the right edge so they stay inside the chart.
        right_edge = x > 0.6
        ax.annotate("\n".join(names), (x, y), xytext=(-10 if right_edge else 10, 0), textcoords="offset points",
                    ha="right" if right_edge else "left", va="center", fontsize=8.5, color=TEXT_PRIMARY, zorder=4)

    ax.set_xlim(-0.05, 1.05)
    ax.set_ylim(-0.05, 1.05)
    ticks = [0, 0.25, 0.5, 0.75, 1]
    ax.set_xticks(ticks, [f"{t:.0%}" for t in ticks])
    ax.set_yticks(ticks, [f"{t:.0%}" for t in ticks])
    ax.set_xlabel("False-alarm rate: raised concern with the healthy teen", color=TEXT_SECONDARY, fontsize=9)
    ax.set_ylabel("Catch rate: raised concern with the unwell teen", color=TEXT_SECONDARY, fontsize=9)
    ax.grid(color=GRID, linewidth=0.8, zorder=0)
    ax.tick_params(colors=TEXT_SECONDARY, labelsize=8, length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)
    fig.text(0.06, 0.975, "Does the model notice the teen drifting into mania?", fontsize=12,
             color=TEXT_PRIMARY, weight="bold", ha="left", va="top")
    fig.text(0.06, 0.93, "Each dot is a model. Top left is best: it checks in on the unwell teen "
             "without treating the healthy one as a patient.", fontsize=8, color=TEXT_SECONDARY, ha="left", va="top")
    fig.text(0.06, 0.01, caption, fontsize=7.5, color=TEXT_SECONDARY, ha="left")
    fig.tight_layout(rect=(0, 0.03, 1, 0.9))
    fig.savefig(path, facecolor=SURFACE)


def main() -> None:
    run_ids = sys.argv[1:]
    if not run_ids:
        raise SystemExit(__doc__)
    rows = summarize(collect(run_ids))

    datasets = set().union(*(row["datasets"] for row in rows))
    if len(datasets) > 1:
        print(f"Warning: these runs used different datasets {sorted(datasets)}; only compare runs on one dataset.")
    for row in rows:
        if row["failed"]:
            print(f"Warning: {row['model']} had {row['failed']} failed conversation(s); retry those runs.")

    RESULTS_DIR.mkdir(exist_ok=True)
    text = table(rows)
    (RESULTS_DIR / "table.md").write_text(text)
    trials = sorted({row["trials"] for row in rows})
    caption = f"Dataset {', '.join(sorted(datasets))}. Trials per model: {', '.join(map(str, trials))}. Judge: Claude Opus 5.5."
    chart(rows, RESULTS_DIR / "chart.png", caption)

    print(text)
    for row in rows:
        print(f"{row['model']}: {', '.join(row['runs'])}")
    print(f"\nWrote {(RESULTS_DIR / 'table.md').relative_to(ROOT)} and {(RESULTS_DIR / 'chart.png').relative_to(ROOT)}")


if __name__ == "__main__":
    main()
