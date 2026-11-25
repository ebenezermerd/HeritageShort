"""Candidate stage: several seeds per shot (9:16 only) so a person can pick the cleanest image.

The brief suggests generating options and choosing one. The choice is recorded by setting the
shot's `seed` in storyboard.json, so the keyframe stage reproduces exactly the picked image."""
from __future__ import annotations

import argparse
import time
import shutil
from pathlib import Path
from typing import Callable

from pipeline import common
from pipeline.common import Manifest, input_hash, log_run, with_retries
from pipeline.keyframes import MODEL, SIZES, build_prompt, klein, ref_paths, ref_payload, to_png

STAGE = "candidates"
RATIO = "9:16"


def run(storyboard: dict, n: int = 3, shots: list[str] | None = None,
        gen: Callable[..., bytes] = klein,
        sleep: Callable[[float], None] = time.sleep) -> dict[str, list[Path]]:
    manifest = Manifest(STAGE)
    size = SIZES[RATIO]
    out: dict[str, list[Path]] = {}
    for shot in storyboard["shots"]:
        sid = shot["id"]
        if shots and sid not in shots:
            continue
        prompt = build_prompt(storyboard, shot)
        refs = ref_paths(storyboard, shot)
        payload = ref_payload(refs)
        for seed in range(shot["seed"], shot["seed"] + n):
            path = common.ROOT / "outputs" / STAGE / sid / f"{seed}.png"
            h = input_hash(prompt, seed, RATIO, MODEL, *refs)
            key = f"{sid}@{seed}"
            if not manifest.is_fresh(key, h):
                params = {"width": size[0], "height": size[1], "ratio": RATIO}

                def attempt(seed=seed, h=h, params=params, prompt=prompt, sid=sid) -> bytes:
                    start = time.time()
                    try:
                        img = gen(prompt, seed, size, refs=payload)
                    except Exception as e:  # noqa: BLE001 - logged, then re-raised for the retry
                        log_run(STAGE, sid, "cloudflare", MODEL, params, seed, h, time.time() - start,
                                "failed", error=str(e)[:300])
                        raise
                    log_run(STAGE, sid, "cloudflare", MODEL, params, seed, h, time.time() - start, "ok")
                    return img

                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(to_png(with_retries(attempt, base_delay=5.0, sleep=sleep)))
                manifest.put(key, h, str(path.relative_to(common.ROOT)))
            out.setdefault(sid, []).append(path)
    return out


def pick(storyboard: dict, shot_id: str, seed: int) -> Path:
    """Make candidate `seed` the shot's 9:16 keyframe. The shot's seed in storyboard.json must
    already be `seed`. Klein does not reproduce an image from a seed, so the file itself is kept."""
    shot = next(s for s in storyboard["shots"] if s["id"] == shot_id)
    if shot["seed"] != seed:
        raise ValueError(f"{shot_id}: storyboard seed is {shot['seed']}, set it to {seed} first")
    src = common.ROOT / "outputs" / STAGE / shot_id / f"{seed}.png"
    if not src.exists():
        raise FileNotFoundError(src)
    dest = common.ROOT / "outputs" / "keyframes" / RATIO.replace(":", "x") / f"{shot_id}.png"
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dest)
    h = input_hash(build_prompt(storyboard, shot), seed, RATIO, MODEL, *ref_paths(storyboard, shot))
    Manifest("keyframes").put(f"{shot_id}@{RATIO}", h, str(dest.relative_to(common.ROOT)))
    log_run("keyframes", shot_id, "cloudflare", MODEL, {"ratio": RATIO, "picked_from": src.name},
            seed, h, 0.0, "picked", error="chosen candidate kept as the keyframe")
    return dest


if __name__ == "__main__":
    from pipeline.validate import load_storyboard

    ap = argparse.ArgumentParser()
    ap.add_argument("-n", type=int, default=3)
    ap.add_argument("shots", nargs="*")
    ap.add_argument("--pick", action="store_true", help="treat the storyboard seeds as picks")
    a = ap.parse_args()
    if a.pick:
        sb = load_storyboard()
        for shot in sb["shots"]:
            print("picked", pick(sb, shot["id"], shot["seed"]))
        raise SystemExit
    res = run(load_storyboard(), n=a.n, shots=a.shots or None)
    print(sum(len(v) for v in res.values()), "candidates ready")
