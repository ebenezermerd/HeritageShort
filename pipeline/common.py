"""Shared helpers: run logging, input hashing, per-stage manifests, retries."""
from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, TypeVar

from dotenv import load_dotenv

T = TypeVar("T")

ROOT = Path(__file__).resolve().parent.parent


def log_run(
    stage: str,
    shot_id: str | None,
    provider: str,
    model: str,
    params: dict,
    seed: int | None,
    input_hash: str,
    latency_s: float,
    status: str,
    cost_usd: float = 0.0,
    error: str | None = None,
) -> None:
    """Append one line to runs.jsonl. Called for every attempt, failures included."""
    row = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "stage": stage,
        "shot_id": shot_id,
        "provider": provider,
        "model": model,
        "params": params,
        "seed": seed,
        "input_hash": input_hash,
        "latency_s": round(latency_s, 3),
        "status": status,
        "cost_usd": cost_usd,
        "error": error,
    }
    with open(ROOT / "runs.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def input_hash(*parts: Any) -> str:
    """SHA-256 over the inputs that decide an output. A Path contributes its bytes."""
    h = hashlib.sha256()
    for part in parts:
        if isinstance(part, Path):
            h.update(b"F" + part.read_bytes())
        else:
            h.update(b"J" + json.dumps(part, sort_keys=True, separators=(",", ":"), default=str).encode())
        h.update(b"\0")
    return h.hexdigest()


class Manifest:
    """Per-stage record of which input hash produced which output file."""

    def __init__(self, stage: str):
        self.stage = stage

    @property
    def _path(self) -> Path:
        return ROOT / "outputs" / self.stage / "manifest.json"

    def _read(self) -> dict:
        if self._path.exists():
            return json.loads(self._path.read_text())
        return {}

    def get(self, shot_id: str) -> dict | None:
        return self._read().get(shot_id)

    def is_fresh(self, shot_id: str, h: str) -> bool:
        entry = self.get(shot_id)
        return entry is not None and entry["hash"] == h and (ROOT / entry["path"]).exists()

    def put(self, shot_id: str, h: str, path: str) -> None:
        data = self._read()
        data[shot_id] = {"hash": h, "path": path}
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(data, indent=2))


def with_retries(
    fn: Callable[[], T],
    attempts: int = 3,
    base_delay: float = 2.0,
    sleep: Callable[[float], None] = time.sleep,
) -> T:
    """Call fn up to `attempts` times, backing off 2s, 4s, ... Re-raises the last error."""
    for i in range(attempts):
        try:
            return fn()
        except Exception:
            if i == attempts - 1:
                raise
            sleep(base_delay * 2**i)
    raise RuntimeError("unreachable")


def require_env(name: str) -> str:
    load_dotenv(ROOT / ".env")
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"Missing {name}. Put it in .env (see .env.example).")
    return value
