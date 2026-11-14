"""Builds one multi-step Valkyrie task per conversation in data/*.json, with one step per teen message."""

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
TASKS_DIR = ROOT / "tasks"
JUDGE_SOURCE = ROOT / "judge" / "judge.py"
BENCHMARK = "teen-mania"

DOCKERFILE = """\
FROM python:3.12-slim

# The chat agent calls Anthropic or OpenAI models; the judge calls Anthropic.
RUN pip install --no-cache-dir anthropic==2.8.0 openai==3.51.0

WORKDIR /app
"""

STEP_TEST = """\
#!/bin/bash
# Grades the chatbot's reply for this round.
python3 /tests/judge.py --round {round}
"""


def toml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def task_toml(task: dict, rounds: list[int]) -> str:
    lines = [
        'schema_version = "1.4"',
        'multi_step_reward_strategy = "mean"',
        "",
        "[task]",
        f"name = {toml_string(BENCHMARK + '/' + task['task_id'])}",
        "",
        "[metadata]",
        f"case_id = {toml_string(task['case_id'])}",
        f"version = {toml_string(task['version'])}",
        f"measures = {toml_string(task['measures'])}",
        "",
        "[agent]",
        "timeout_sec = 300.0",
        "",
        "[verifier]",
        "timeout_sec = 300.0",
        "",
        "# The judge uses the ANTHROPIC_API_KEY the run sets in the sandbox for the agent.",
        "[verifier.env]",
        'JUDGE_MODEL = "claude-opus-5-5"',
        "",
        "[environment]",
        "build_timeout_sec = 600.0",
        "cpus = 1",
        "memory_mb = 1024",
        "storage_mb = 4096",
    ]
    for number in rounds:
        lines += ["", "[[steps]]", f'name = "round-{number}"']
    return "\n".join(lines) + "\n"


def case_file(task: dict) -> dict:
    """The hidden grading context: background, round guidance, and answer key."""
    return {
        "task_id": task["task_id"],
        "version": task["version"],
        "version_name": task["version_name"],
        "background": {
            "measures": task["measures"],
            "setting": task["setting"],
            "age": task["age"],
            "profile": task["profile"],
            "background": task["background"],
            "case_details": [item["detail"] for item in task["case_details"]],
            "what_the_teen_wants": task["what_the_teen_wants"],
            "severity_1_to_5": task["severity_1_to_5"],
            "overall": task["overall"],
            "unsafe_request": task["unsafe_request"],
        },
        "guidance_by_round": {str(m["round"]): m["guidance"] for m in task["teen_messages"]},
        "answer_key": task["answer_key"],
    }


def build_task(task: dict) -> Path:
    folder = TASKS_DIR / task["task_id"]
    if folder.exists():
        shutil.rmtree(folder)
    rounds = [m["round"] for m in task["teen_messages"]]

    (folder / "environment").mkdir(parents=True)
    (folder / "environment" / "Dockerfile").write_text(DOCKERFILE)
    (folder / "task.toml").write_text(task_toml(task, rounds))

    tests = folder / "tests"
    tests.mkdir()
    shutil.copy(JUDGE_SOURCE, tests / "judge.py")
    (tests / "case.json").write_text(json.dumps(case_file(task), indent=2, ensure_ascii=False) + "\n")

    for message in task["teen_messages"]:
        step = folder / "steps" / f"round-{message['round']}"
        (step / "tests").mkdir(parents=True)
        (step / "instruction.md").write_text(message["teen"].strip() + "\n")
        test_script = step / "tests" / "test.sh"
        test_script.write_text(STEP_TEST.format(round=message["round"]))
        test_script.chmod(0o755)
    return folder


def main() -> None:
    sources = [Path(arg) for arg in sys.argv[1:]] or sorted(DATA_DIR.glob("*.json"))
    for source in sources:
        for task in json.loads(source.read_text())["tasks"]:
            folder = build_task(task)
            print(f"{source.name}: wrote {folder.relative_to(ROOT)} ({len(task['teen_messages'])} rounds)")


if __name__ == "__main__":
    main()
