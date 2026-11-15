"""Runs the final benchmark on every model in MODELS.

    python3 scripts/big_run.py smoke teen-mania/main@v2   # one short run per model, to check each model ID works
    python3 scripts/big_run.py full  teen-mania/main@v2   # the real runs (RUNS each, Luna gets LUNA_RUNS)

Each `full` run covers every task, so the run-level scores are correct. Run IDs are appended to
results/run_ids.txt (model, label, run ID); pass them to `uv run scripts/report.py`.
Edit MODELS before running: drop any model whose smoke run failed.
"""

import re
import subprocess
import time
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

MODELS = [
    # Anthropic: current and previous frontier generations.
    "anthropic/claude-fable-5-2",
    "anthropic/claude-fable-5-1",
    "anthropic/claude-opus-5-5",
    # "anthropic/claude-opus-5",  # left out: refused every message in the check run (stop_reason "refusal", 0 output tokens)
    "anthropic/claude-sonnet-5-5",
    "anthropic/claude-sonnet-5",
    "anthropic/claude-haiku-5-5",
    # OpenAI. gpt-6-sol and gpt-6-luna are confirmed IDs; the others come from secondary sources, so smoke-test them.
    "openai/gpt-6-astra",
    "openai/gpt-6.1-sol",
    "openai/gpt-6-sol",
    "openai/gpt-6.1-terra",
    "openai/gpt-6-luna",
    "openai/gpt-5.6",
]
RUNS = 2
LUNA_RUNS = 5  # GPT-6 Luna is the ChatGPT free-tier model: extra runs for its spotlight.
SMOKE_TASK = "cq91ggr91-healthy"  # the shortest conversation (5 rounds)


def start(model: str, dataset: str, label: str, count: int, extra: list[str]) -> list[str]:
    command = [
        "valkyrie", "run", "start", "--agent", "teen-chat", "--dataset", dataset, "--model", model,
        "--provider", "modal", "-s", "ANTHROPIC_API_KEY", "anthropic-api-key", "-s", "OPENAI_API_KEY", "openai-api-key",
        "--concurrency", "2", "-l", label, "-n", str(count), *extra,
    ]
    while True:
        result = subprocess.run(command, capture_output=True, text=True)
        output = result.stdout + result.stderr
        ids = re.findall(r"Run ID:\s+([0-9a-f-]{36})", output)
        if ids:
            break
        # Valkyrie caps how many runs an org can have active at once; wait for some to finish, then try again.
        if "may run at most" in output:
            print(f"  {model}: the org is at its active-run limit, retrying in 60 seconds")
            time.sleep(60)
            continue
        print(f"  {model}: could not start: {output.strip()[-500:]}")
        return []
    if len(ids) != count:
        print(f"  warning: asked for {count} runs of {model}, saw {len(ids)} run IDs; check `valkyrie run list -l {label}`")
    return ids


def main() -> None:
    if len(sys.argv) != 3 or sys.argv[1] not in ("smoke", "full"):
        raise SystemExit(__doc__)
    mode, dataset = sys.argv[1], sys.argv[2]
    tag = dataset.split("@")[-1]
    label = f"{mode}-{tag}"
    log = ROOT / "results" / "run_ids.txt"
    for model in MODELS:
        if mode == "smoke":
            ids = start(model, dataset, label, 1, ["--task-ids", SMOKE_TASK])
        else:
            ids = start(model, dataset, label, LUNA_RUNS if model.endswith("gpt-6-luna") else RUNS, [])
        for run_id in ids:
            print(f"{model}  {run_id}")
            if mode == "full":
                with log.open("a") as f:
                    f.write(f"{model}\t{label}\t{run_id}\n")
    print(f"\nWatch: valkyrie run list -l {label}")
    if mode == "smoke":
        print("Then check each one with `valkyrie run errors <run ID>` and remove failing models from MODELS.")


if __name__ == "__main__":
    main()
