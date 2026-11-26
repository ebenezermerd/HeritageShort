"""One command for the whole film: validate, narrate, keyframes, shots, music, assemble both ratios."""
from __future__ import annotations

import argparse
import shutil
import time
from pathlib import Path
from typing import Callable

from pipeline import assemble, common, keyframes, music, narrate, providers, references, shots


KEPT = ("keyframes", "references", "narration/gemini")


def restore_assets() -> None:
    """Copy committed files from assets/ into outputs/ when not already there: Wan clips, the score,
    and the chosen keyframes, references and narration."""
    for sub in ("shots", "music"):
        src, dst = common.ROOT / "assets" / sub, common.ROOT / "outputs" / sub / "raw"
        if not src.exists():
            continue
        dst.mkdir(parents=True, exist_ok=True)
        for f in src.iterdir():
            if not f.is_file():
                continue
            # the chosen score goes where assembly reads it; everything else is a raw download
            target = common.ROOT / "outputs" / "music" / "score.wav" if (sub, f.name) == ("music", "score.wav") \
                else dst / f.name
            if not target.exists():
                shutil.copyfile(f, target)
    # The chosen pictures and the Gemini voice cannot be made again exactly (klein on Cloudflare does
    # not repeat a seed, E14; Gemini allows 10 requests a day), so they are restored with their
    # manifests and every stage sees them as cached.
    for sub in KEPT:
        src = common.ROOT / "assets" / sub
        if not src.exists():
            continue
        for f in sorted(src.rglob("*")):
            target = common.ROOT / "outputs" / sub / f.relative_to(src)
            if f.is_file() and not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(f, target)


def pipeline(storyboard: dict, *, tts: Callable | None = None, gen: Callable | None = None,
             voice: str = "gemini", sleep: Callable[[float], None] = time.sleep) -> dict[str, Path]:
    timings: dict[str, float] = {}

    def timed(name: str, fn: Callable):
        t = time.time()
        result = fn()
        timings[name] = time.time() - t
        return result

    restore_assets()
    durations = timed("narration", lambda: narrate.run(storyboard, tts, sleep, voice))
    timed("references", lambda: references.run(storyboard, gen or keyframes.klein, sleep))
    timed("keyframes", lambda: keyframes.run(storyboard, gen or keyframes.klein, sleep))
    timed("shots", lambda: (shots.export_wan_jobs(storyboard), shots.run(storyboard, durations)))
    candidates = music.import_candidates()
    print(f"music: {len(candidates)} ACE-Step candidates found"
          + ("" if (common.ROOT / 'outputs/music/score.wav').exists() else "; no score chosen, assembly uses a pad"))
    outputs = {r: timed(f"assemble {r}", lambda r=r: assemble.run(storyboard, durations, r, voice))
               for r in storyboard["ratios"]}
    for name, secs in timings.items():
        print(f"  {name:<14} {secs:6.1f}s")
    return outputs


if __name__ == "__main__":
    from pipeline.validate import load_storyboard

    ap = argparse.ArgumentParser()
    ap.add_argument("--voice", choices=sorted(providers.VOICES), default="gemini")
    for ratio, path in pipeline(load_storyboard(), voice=ap.parse_args().voice).items():
        print(f"{ratio}: {path}")
