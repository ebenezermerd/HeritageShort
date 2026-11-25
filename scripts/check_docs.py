"""Fail loudly if the evidence a reviewer reads is missing. Run: uv run python scripts/check_docs.py"""
from __future__ import annotations

import json
import re
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))

from pipeline import common  # noqa: E402

REQUIRED = ["README.md", "ARCHITECTURE.md", "DESIGN.md", "EXPERIMENTS.md", "FAILURES.md", "COSTS.md",
            "ETHICS.md", "REPORT.md"]
RUN_FIELDS = ["ts", "stage", "shot_id", "provider", "model", "params", "seed", "input_hash", "latency_s",
              "status", "cost_usd", "error"]
MIN_EXPERIMENTS = 10


def _problems() -> list[str]:
    root = common.ROOT
    problems = [f"missing {name}" for name in REQUIRED if not (root / name).exists()]

    exp = root / "EXPERIMENTS.md"
    if exp.exists():
        sections = re.split(r"^## E\d+\.", exp.read_text(), flags=re.M)[1:]
        complete = [s for s in sections if all(k in s for k in ("**Hypothesis.**", "**Change.**", "**Result.**"))]
        if len(complete) < MIN_EXPERIMENTS:
            problems.append(f"EXPERIMENTS.md has {len(complete)} complete entries, needs {MIN_EXPERIMENTS}")

    eth = root / "ETHICS.md"
    if eth.exists():
        text = eth.read_text()
        for name in ("Tesfa", "Beki"):
            if not re.search(rf"\*\*{name}:\*\*\s+\".+\"", text):
                problems.append(f"ETHICS.md has no quoted consent from {name}")

    runs = root / "runs.jsonl"
    if not runs.exists():
        problems.append("missing runs.jsonl")
    else:
        for i, line in enumerate(runs.read_text().splitlines(), start=1):
            missing = [k for k in RUN_FIELDS if k not in json.loads(line)]
            if missing:
                problems.append(f"runs.jsonl line {i} lacks {', '.join(missing)}")
                break
    return problems


def main() -> int:
    problems = _problems()
    for p in problems:
        print("PROBLEM:", p)
    if not problems:
        print("docs ok")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
