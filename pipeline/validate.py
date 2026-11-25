"""Validate storyboard.json against schema/storyboard.schema.json."""
from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from pipeline import common


def load_storyboard(path: Path | None = None) -> dict:
    """Return the storyboard dict, or exit with every failing JSON path."""
    path = path or common.ROOT / "storyboard.json"
    schema = json.loads((common.ROOT / "schema" / "storyboard.schema.json").read_text())
    data = json.loads(Path(path).read_text())
    errors = sorted(Draft202012Validator(schema).iter_errors(data), key=lambda e: list(map(str, e.path)))
    if errors:
        lines = ["storyboard invalid:"]
        for e in errors:
            where = "/".join(str(p) for p in e.absolute_path) or "(root)"
            lines.append(f"  {where}: {e.message}")
        raise SystemExit("\n".join(lines))
    return data


def shot_ids(sb: dict) -> list[str]:
    return [s["id"] for s in sb["shots"]]


if __name__ == "__main__":
    load_storyboard()
    print("storyboard ok")
