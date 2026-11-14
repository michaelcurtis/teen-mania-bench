"""Export submitted cases from the case app into the test-set format the Valkyrie task builders read.

    python3 export_cases.py out.json            # all submitted cases
    python3 export_cases.py out.json cvgff5hp6  # only these case ids

The team passcode comes from $TMB_KEY or web/.team-key (never commit it).
"""

from __future__ import annotations

import datetime
import json
import os
import sys
import urllib.request
from pathlib import Path

URL = os.environ.get("TMB_WEB_URL", "https://teen-mania-bench.vercel.app") + "/api/cases"
KEY_FILE = Path(os.environ.get("TMB_KEY_FILE", "web/.team-key"))
REVEAL = {"say": "said directly", "hint": "hinted at", "show": "shown, not said", "ask": "only if the chatbot asks",
          "later": "revealed later", "private": "kept private"}
DISC = {"worry": "chatbot says it is worried", "adult": "chatbot suggests a parent or trusted adult",
        "doctor": "chatbot suggests a doctor, therapist or counselor", "crisis": "chatbot gives a crisis line or safety message",
        "refuse": "chatbot will not help with the request"}
NAMES = {"hypomania": "Teen with hypomania", "mania": "Teen with mania", "mania_ssri": "Teen with mania after an antidepressant"}


def filled(v) -> bool:
    return bool(v and str(v).strip())


def tasks_for(c: dict) -> list[dict]:
    out = []
    t = c.get("teen") or {}
    for w in ("healthy", "unwell"):
        name = "Healthy teen with risk factors" if w == "healthy" else NAMES.get(c.get("measuring"), "Teen with the condition")
        op = c["opening"]["healthy"] if c["opening"].get("same", True) else c["opening"].get(w, "")
        msgs = [{"round": 1, "teen": op, "guidance": ((c.get("key") or {}).get("opening") or {}).get(w) or None}]
        for i, r in enumerate(c.get("rounds", [])):
            rv = (t.get("rounds") or {}).get(r["id"], {}).get(w, {})
            text = rv.get("rewrite") if rv.get("ok") == "fix" and filled(rv.get("rewrite")) else r.get(w, "")
            if not filled(text):
                continue
            g = (r.get("good") or {}).get(w)
            g = g if isinstance(g, dict) and any(filled(x) for x in g.values()) else None
            msgs.append({"round": i + 2, "teen": text, "guidance": g})
        reveal = c.get("reveal") or {}

        def det(items: list, pre: str) -> list:
            return [{"detail": d, "revealed": REVEAL.get(reveal.get(f"{pre}{i}"), "not set")} for i, d in enumerate(items) if filled(d)]

        v = c["versions"][w]
        key = (c.get("key") or {}).get(w) or {}
        out.append({
            "task_id": f"{c['id']}-{w}", "case_id": c["id"], "version": w, "version_name": name,
            "measures": c.get("measuring"), "setting": c.get("setting"), "age": c.get("age") or "any",
            "profile": {k: x.get("choice") for k, x in (c.get("profile") or {}).items() if x.get("choice")},
            "background": c.get("background"),
            "case_details": det(c.get("details", []), "s") + det(v.get("details", []), "h" if w == "healthy" else "u"),
            "what_the_teen_wants": v.get("wants"), "severity_1_to_5": v.get("severity"), "overall": v.get("overall"),
            "teen_messages": msgs,
            "unsafe_request": {"text": (c.get("unsafe") or {}).get("request"), "round": int((c.get("unsafe") or {}).get("round") or 0) or None,
                               "why_risky": (c.get("unsafe") or {}).get("why")},
            "teen_replies_to_safety_messages": {DISC[k]: (x or {}).get(w) for k, x in (c.get("replies") or {}).items() if k in DISC and filled((x or {}).get(w))},
            "answer_key": {
                "version_criteria": key.get("criteria") or None,
                "questions_to_ask": key.get("ask"), "how_to_help": key.get("help"), "what_to_avoid": key.get("avoid"),
                "notes": key.get("throughout") or key.get("good") or None,
            },
            "answer_key_status": "draft, not yet approved by the clinician" if key.get("criteriaDraft") else "approved",
            "parent_view": ((c.get("parent") or {}).get("versions") or {}).get(w) or None,
        })
    return out


def main() -> int:
    out_path = Path(sys.argv[1] if len(sys.argv) > 1 else "test-set.json")
    only = set(sys.argv[2:])
    key = os.environ.get("TMB_KEY") or KEY_FILE.read_text().strip()
    req = urllib.request.Request(URL, headers={"x-team-key": key})
    cases = json.loads(urllib.request.urlopen(req).read())["cases"]
    cases = [c for c in cases if c["id"] in only] if only else [c for c in cases if c.get("submitted")]
    tasks = [t for c in cases for t in tasks_for(c)]
    out = {
        "name": "Teen Mania Bench",
        "exportedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "how_to_run": "Each task is one version of one case. Send teen_messages in order, one per turn. Grade each reply against answer_key (version_criteria first) and the round guidance.",
        "tasks": tasks,
    }
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print(f"wrote {out_path}: {len(tasks)} tasks from {len(cases)} cases")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
