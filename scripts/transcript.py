"""Writes a run's conversations as readable Markdown, with the healthy and unwell teen side by side each round.

    python3 scripts/transcript.py RUN_ID

Writes one file per case to results/transcripts/, with every message, every reply, and the judge's verdict.
"""

import json
import re
import subprocess
import sys
import tempfile
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "results" / "transcripts"
VERSIONS = ("healthy", "unwell")


@dataclass(frozen=True)
class Verdict:
    good: bool
    raised_concern: bool
    harmful: bool
    red_flags: tuple[str, ...]
    explanation: str


def valkyrie(*args: str) -> str:
    return subprocess.run(["valkyrie", *args], check=True, capture_output=True, text=True).stdout


def parse_verdict(verifier_output: str) -> Verdict | None:
    """Reads the judge's printed JSON; handles both the current judge and the earlier one."""
    start = verifier_output.find("{")
    if start < 0:
        return None
    printed = json.loads(verifier_output[start:])
    if "round_result" in printed:
        result = printed["round_result"]
        return Verdict(
            good=bool(result["round_good"]),
            raised_concern=bool(result["round_raised_concern"]),
            harmful=bool(result["round_harmful"]),
            red_flags=tuple(printed.get("red_flags", [])),
            explanation=printed["explanation"],
        )
    result = printed["rewards"]
    return Verdict(
        good=bool(result["reward"]),
        raised_concern=bool(result["raised_concern"]),
        harmful=bool(result["harmful"]),
        red_flags=(),
        explanation=printed["explanation"],
    )


def verdicts_for(run_id: str, task_id: str) -> list[Verdict | None]:
    task = json.loads(valkyrie("run", "task", run_id, task_id, "--format", "json"))
    steps = ((task.get("evaluation_result") or {}).get("metadata") or {}).get("steps", [])
    return [parse_verdict((step.get("metadata") or {}).get("verifier_output", "")) for step in steps]


def last_conversation(task_dir: Path) -> list[dict]:
    """The conversation saved after the last round has every turn."""
    files = list(task_dir.glob("steps/round-*/agent_output/logs/teen-chat/conversation.json"))
    if not files:
        return []
    latest = max(files, key=lambda f: int(re.search(r"round-(\d+)", str(f)).group(1)))
    return json.loads(latest.read_text())["turns"]


def verdict_line(verdict: Verdict | None) -> str:
    if verdict is None:
        return "_Not graded._"
    parts = ["✅ good reply" if verdict.good else "❌ not a good reply"]
    if verdict.raised_concern:
        parts.append("raised concern about the teen")
    if verdict.harmful:
        parts.append("harmful")
    if verdict.red_flags:
        parts.append("red flags: " + ", ".join(flag.replace("_", " ") for flag in verdict.red_flags))
    return (
        f"**Judge:** {' · '.join(parts)}\n\n"
        f"<details><summary>Judge's explanation</summary>\n\n{verdict.explanation}\n\n</details>"
    )


def quote(text: str) -> str:
    return "\n".join(f"> {line}" if line else ">" for line in text.strip().splitlines())


def write_case(case_id: str, model: str, run_id: str, dataset: str, sides: dict[str, tuple[list, list]]) -> Path:
    lines = [
        f"# {model}: case {case_id}",
        "",
        f"Run `{run_id}` on `{dataset}`. Each round shows the healthy teen, then the unwell teen.",
        "",
    ]
    rounds = max(len(turns) for turns, _ in sides.values())
    for number in range(1, rounds + 1):
        lines += [f"## Round {number}", ""]
        for version in VERSIONS:
            turns, verdicts = sides.get(version, ([], []))
            if number > len(turns):
                lines += [f"### {version.capitalize()} teen", "", "_This conversation stopped before this round._", ""]
                continue
            turn = turns[number - 1]
            verdict = verdicts[number - 1] if number <= len(verdicts) else None
            lines += [
                f"### {version.capitalize()} teen",
                "",
                quote(turn["teen"]),
                "",
                f"**{model}:**",
                "",
                quote(turn["reply"] or "(no reply)"),
                "",
                verdict_line(verdict),
                "",
            ]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", model.lower()).strip("-")
    path = OUT_DIR / f"{slug}-{case_id}-{run_id[:8]}.md"
    path.write_text("\n".join(lines))
    return path


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    run_id = sys.argv[1]
    with tempfile.TemporaryDirectory() as scratch:
        valkyrie("run", "outputs", run_id, "--output-dir", scratch)
        summary = json.loads(next(Path(scratch).glob("*.json")).read_text())
        arguments = summary["benchmark_arguments"]
        model = arguments["contract"]["model"].split("/", 1)[-1]
        dataset = (arguments.get("dataset_version") or {}).get("id", "unknown dataset")

        cases: dict[str, dict[str, tuple[list, list]]] = defaultdict(dict)
        for task_dir in sorted(p for p in Path(scratch).iterdir() if p.is_dir()):
            case_id, _, version = task_dir.name.rpartition("-")
            if version not in VERSIONS:
                continue
            cases[case_id][version] = (last_conversation(task_dir), verdicts_for(run_id, task_dir.name))

    for case_id, sides in cases.items():
        print(f"Wrote {write_case(case_id, model, run_id, dataset, sides).relative_to(ROOT)}")


if __name__ == "__main__":
    main()
