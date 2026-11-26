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
from pipeline.keyframes import MODEL, SIZES, build_prompt, klein, ref_paths, ref_payload, seed_for, to_png

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
        prompt = build_prompt(storyboard, shot, RATIO)
        refs = ref_paths(storyboard, shot, RATIO)
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


def candidate_path(shot_id: str, seed: int, ratio: str = RATIO) -> Path:
    base = common.ROOT / "outputs" / STAGE / shot_id
    return base / f"{seed}.png" if ratio == RATIO else base / ratio.replace(":", "x") / f"{seed}.png"


def pick(storyboard: dict, shot_id: str, ratio: str = RATIO, provider: str = "cloudflare") -> Path:
    """Make the candidate named by the shot's `pick` (or `seed`) the keyframe for `ratio`.
    The file itself is kept: Cloudflare's klein does not reproduce an image from a seed (E14)."""
    shot = next(s for s in storyboard["shots"] if s["id"] == shot_id)
    seed = seed_for(shot, ratio)
    src = candidate_path(shot_id, seed, ratio)
    if not src.exists():
        raise FileNotFoundError(src)
    dest = common.ROOT / "outputs" / "keyframes" / ratio.replace(":", "x") / f"{shot_id}.png"
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dest)
    h = input_hash(build_prompt(storyboard, shot, ratio), seed, ratio, MODEL, *ref_paths(storyboard, shot, ratio))
    Manifest("keyframes").put(f"{shot_id}@{ratio}", h, str(dest.relative_to(common.ROOT)))
    log_run("keyframes", shot_id, provider, MODEL, {"ratio": ratio, "picked_from": str(src.relative_to(common.ROOT))},
            seed, h, 0.0, "picked", error="chosen candidate kept as the keyframe")
    return dest


if __name__ == "__main__":
    from pipeline.validate import load_storyboard

    ap = argparse.ArgumentParser()
    ap.add_argument("-n", type=int, default=3)
    ap.add_argument("shots", nargs="*")
    ap.add_argument("--pick", action="store_true", help="make each shot's `pick` seeds its keyframes")
    ap.add_argument("--provider", default="cloudflare", help="who made the candidates (kaggle or cloudflare)")
    a = ap.parse_args()
    if a.pick:
        sb = load_storyboard()
        for shot in sb["shots"]:
            for ratio in shot.get("pick") or {RATIO: shot["seed"]}:
                print("picked", pick(sb, shot["id"], ratio, provider=a.provider))
        raise SystemExit
    res = run(load_storyboard(), n=a.n, shots=a.shots or None)
    print(sum(len(v) for v in res.values()), "candidates ready")
