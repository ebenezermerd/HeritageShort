"""Reference stage: the spring plate and the brothers sheet that every keyframe is conditioned on.

The brief: make a character and style reference first, then generate each keyframe against it.
klein takes up to four reference images per call (`input_image_0..3`), so a shot lists the
references it needs in `refs` and keyframes.py sends them."""
from __future__ import annotations

import time
from pathlib import Path
from typing import Callable

from pipeline import common
from pipeline.common import Manifest, input_hash, log_run, with_retries
from pipeline.keyframes import MODEL, klein, to_png

STAGE = "references"


def run(storyboard: dict, gen: Callable[..., bytes] = klein,
        sleep: Callable[[float], None] = time.sleep) -> dict[str, Path]:
    manifest = Manifest(STAGE)
    out: dict[str, Path] = {}
    for ref in storyboard.get("references", []):
        rid, seed, size = ref["id"], ref["seed"], tuple(ref["size"])
        prompt = f"{storyboard['style_block'].rstrip('.')}. {ref['prompt']}"
        path = common.ROOT / "outputs" / STAGE / f"{rid}.png"
        h = input_hash(prompt, seed, size, MODEL)
        if not manifest.is_fresh(rid, h):
            def attempt() -> bytes:
                start = time.time()
                try:
                    img = gen(prompt, seed, size)
                except Exception as e:  # noqa: BLE001 - logged, then re-raised for the retry
                    log_run(STAGE, rid, "cloudflare", MODEL, {"size": size}, seed, h, time.time() - start,
                            "failed", error=str(e)[:300])
                    raise
                log_run(STAGE, rid, "cloudflare", MODEL, {"size": size}, seed, h, time.time() - start, "ok")
                return img

            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(to_png(with_retries(attempt, base_delay=5.0, sleep=sleep)))
            manifest.put(rid, h, str(path.relative_to(common.ROOT)))
        out[rid] = path
    return out


if __name__ == "__main__":
    from pipeline.validate import load_storyboard

    for rid, p in run(load_storyboard()).items():
        print(rid, p)
