"""Keyframe stage: one painted still per shot per ratio, cached by prompt, seed, ratio and model."""
from __future__ import annotations

import io
import time
from functools import partial
from pathlib import Path
from typing import Callable

from PIL import Image

from pipeline import common, providers
from pipeline.common import Manifest, input_hash, log_run, with_retries

STAGE = "keyframes"
SIZES = {"9:16": (768, 1344), "16:9": (1344, 768)}
MODEL = providers.FLUX_KLEIN_4B

klein = partial(providers.cloudflare_flux, model=MODEL)


def to_png(data: bytes) -> bytes:
    """Cloudflare's klein returns JPEG bytes; store a real PNG so every tool can read the file."""
    buf = io.BytesIO()
    Image.open(io.BytesIO(data)).convert("RGB").save(buf, "PNG")
    return buf.getvalue()


def ratio_dir(ratio: str) -> str:
    return ratio.replace(":", "x")


def build_prompt(storyboard: dict, shot: dict) -> str:
    """Style block + the looks of the characters in this shot + the shot's own prompt."""
    by_id = {c["id"]: c for c in storyboard["characters"]}
    looks = "; ".join(
        f"{by_id[c]['name'].split('(')[0].strip().split()[0]} is {by_id[c]['look']}"
        for c in shot.get("characters", [])
    )
    parts = [storyboard["style_block"], shot["image_prompt"]]
    if looks:
        parts.append("Characters: " + looks)
    return ". ".join(p.rstrip(".") for p in parts) + "."


def run(storyboard: dict, gen: Callable[[str, int, tuple[int, int]], bytes] = klein,
        sleep: Callable[[float], None] = time.sleep) -> dict[str, dict[str, Path]]:
    manifest = Manifest(STAGE)
    result: dict[str, dict[str, Path]] = {}
    failed: list[str] = []
    for shot in storyboard["shots"]:
        sid, seed = shot["id"], shot["seed"]
        prompt = build_prompt(storyboard, shot)
        for ratio in storyboard["ratios"]:
            size = SIZES[ratio]
            path = common.ROOT / "outputs" / STAGE / ratio_dir(ratio) / f"{sid}.png"
            h = input_hash(prompt, seed, ratio, MODEL)
            key = f"{sid}@{ratio}"
            if not manifest.is_fresh(key, h):
                params = {"width": size[0], "height": size[1], "ratio": ratio}

                def attempt(prompt=prompt, seed=seed, size=size, params=params, h=h, sid=sid) -> bytes:
                    start = time.time()
                    try:
                        img = gen(prompt, seed, size)
                    except Exception as e:  # noqa: BLE001 - logged, then re-raised for the retry
                        log_run(STAGE, sid, "cloudflare", MODEL, params, seed, h, time.time() - start,
                                "failed", error=str(e)[:300])
                        raise
                    log_run(STAGE, sid, "cloudflare", MODEL, params, seed, h, time.time() - start, "ok")
                    return img

                try:
                    img = with_retries(attempt, base_delay=5.0, sleep=sleep)
                except Exception:  # noqa: BLE001 - reported together after the other shots finish
                    failed.append(sid)
                    continue
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(to_png(img))
                manifest.put(key, h, str(path.relative_to(common.ROOT)))
            result.setdefault(sid, {})[ratio] = path
    if failed:
        raise RuntimeError(f"keyframes failed for: {', '.join(sorted(set(failed)))}")
    return result


if __name__ == "__main__":
    from pipeline.validate import load_storyboard

    out = run(load_storyboard())
    print(f"{sum(len(v) for v in out.values())} keyframes ready")
