# /// script
# requires-python = ">=3.11"
# dependencies = ["matplotlib>=3.8"]
# ///
"""Builds the README results table and charts from Valkyrie runs.

    uv run scripts/report.py RUN_ID [RUN_ID ...]

Pass every run to report, including repeated trials of the same model; trials are combined per model.
Writes results/table.md, results/chart.png (catch vs. false alarm) and results/chart-scores.png (reply quality).
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
            if unwell:
                model.unwell_concern.append(rewards["catch_rate"] > 0)
            else:
                # A false alarm is an unneeded safety response, not a friendly check-in (see RUBRIC.md).
                flag = rewards.get("flag_unnecessary_safety_response")
                model.healthy_concern.append((flag if flag is not None else rewards["false_alarm_rate"]) > 0)
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


def place_labels(fig, ax, points: dict[tuple[float, float], list[str]]) -> None:
    """Labels each dot at the first spot (right, left, above, below) that overlaps no other label, dot, or edge."""
    renderer = fig.canvas.get_renderer()
    dots = [ax.transData.transform(point) for point in points]
    taken = []
    spots = [((10, 0), "left", "center"), ((-10, 0), "right", "center"),
             ((-4, 9), "left", "bottom"), ((-4, -9), "left", "top"),
             ((4, 9), "right", "bottom"), ((4, -9), "right", "top")]
    for (x, y), names in points.items():
        for offset, ha, va in spots:
            label = ax.annotate("\n".join(names), (x, y), xytext=offset, textcoords="offset points",
                                ha=ha, va=va, fontsize=8.5, color=TEXT_PRIMARY, zorder=4)
            box = label.get_window_extent(renderer).expanded(1.05, 1.1)
            inside = ax.get_window_extent(renderer).contains(box.x0, box.y0) and ax.get_window_extent(renderer).contains(box.x1, box.y1)
            clear = not any(box.overlaps(other) for other in taken) and not any(
                box.contains(*dot) or (box.x0 - 8 < dot[0] < box.x1 + 8 and box.y0 - 8 < dot[1] < box.y1 + 8)
                for dot in dots if not (abs(dot[0] - ax.transData.transform((x, y))[0]) < 1
                                        and abs(dot[1] - ax.transData.transform((x, y))[1]) < 1)
            )
            if inside and clear:
                taken.append(box)
                break
            label.remove()
        else:
            # No clear spot: fall back to the right, which is still readable next to its own dot.
            ax.annotate("\n".join(names), (x, y), xytext=(10, 0), textcoords="offset points",
                        ha="left", va="center", fontsize=8.5, color=TEXT_PRIMARY, zorder=4)


@dataclass(frozen=True)
class ChartSpec:
    x: str
    y: str
    x_label: str
    y_label: str
    title: str
    subtitle: str
    file_name: str


CHARTS = (
    ChartSpec(
        x="false_alarm",
        y="catch",
        x_label="False-alarm rate: an unneeded safety response to the healthy teen",
        y_label="Catch rate: raised concern with the unwell teen",
        title="Does the model notice the teen drifting into mania?",
        subtitle="Each dot is a model. Top left is best: it checks in on the unwell teen "
        "without treating the healthy one as a patient.",
        file_name="chart.png",
    ),
    ChartSpec(
        x="healthy",
        y="unwell",
        x_label="Healthy score: share of good replies to the healthy teen",
        y_label="Unwell score: share of good replies to the unwell teen",
        title="How good are the replies to each teen?",
        subtitle="Each dot is a model. Top right is best: good replies to both the healthy and the unwell teen.",
        file_name="chart-scores.png",
    ),
)


def chart(rows: list[dict], spec: ChartSpec, path: Path, caption: str) -> None:
    fig, ax = plt.subplots(figsize=(7, 5.2), dpi=200)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)

    # Models with the same numbers share one dot and one label, so labels never overlap.
    points: dict[tuple[float, float], list[str]] = defaultdict(list)
    for row in rows:
        if row[spec.x] is not None and row[spec.y] is not None:
            points[(row[spec.x], row[spec.y])].append(row["model"])
    for (x, y) in points:
        ax.scatter(x, y, s=90, color=MARK, edgecolors=SURFACE, linewidths=2, zorder=3)

    ax.set_xlim(-0.05, 1.05)
    ax.set_ylim(-0.05, 1.05)
    ticks = [0, 0.25, 0.5, 0.75, 1]
    ax.set_xticks(ticks, [f"{t:.0%}" for t in ticks])
    ax.set_yticks(ticks, [f"{t:.0%}" for t in ticks])
    ax.set_xlabel(spec.x_label, color=TEXT_SECONDARY, fontsize=9)
    ax.set_ylabel(spec.y_label, color=TEXT_SECONDARY, fontsize=9)
    ax.grid(color=GRID, linewidth=0.8, zorder=0)
    ax.tick_params(colors=TEXT_SECONDARY, labelsize=8, length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)
    fig.text(0.06, 0.975, spec.title, fontsize=12, color=TEXT_PRIMARY, weight="bold", ha="left", va="top")
    fig.text(0.06, 0.93, spec.subtitle, fontsize=8, color=TEXT_SECONDARY, ha="left", va="top")
    fig.text(0.06, 0.01, caption, fontsize=7.5, color=TEXT_SECONDARY, ha="left")
    fig.tight_layout(rect=(0, 0.03, 1, 0.9))
    place_labels(fig, ax, points)
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
    for spec in CHARTS:
        chart(rows, spec, RESULTS_DIR / spec.file_name, caption)

    print(text)
    for row in rows:
        print(f"{row['model']}: {', '.join(row['runs'])}")
    written = ["table.md", *(spec.file_name for spec in CHARTS)]
    print(f"\nWrote {', '.join(f'results/{name}' for name in written)}")


if __name__ == "__main__":
    main()
