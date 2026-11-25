"""Narration stage: one WAV per narrated shot, cached by the exact line and voice settings."""
from __future__ import annotations

import time
from typing import Callable

from pipeline import common, media, providers
from pipeline.common import Manifest, input_hash, log_run, with_retries

STAGE = "narration"


def _generate(shot_id: str, text: str, h: str, tts: Callable[[str, str], bytes], sleep) -> bytes:
    params = {"voice": providers.DEFAULT_VOICE, "style": providers.DEFAULT_STYLE}

    def attempt() -> bytes:
        start = time.time()
        try:
            audio = tts(text, providers.DEFAULT_STYLE)
        except Exception as e:  # noqa: BLE001 - every failure is logged then re-raised for the retry
            log_run(STAGE, shot_id, "gemini", providers.GEMINI_TTS_MODEL, params, None, h,
                    time.time() - start, "failed", error=str(e)[:300])
            raise
        log_run(STAGE, shot_id, "gemini", providers.GEMINI_TTS_MODEL, params, None, h,
                time.time() - start, "ok")
        return audio

    return with_retries(attempt, base_delay=15.0, sleep=sleep)


def run(storyboard: dict, tts: Callable[[str, str], bytes] = providers.gemini_tts,
        sleep: Callable[[float], None] = time.sleep) -> dict[str, float]:
    """Make narration for every shot with a line. Returns {shot_id: seconds}."""
    manifest = Manifest(STAGE)
    out_dir = common.ROOT / "outputs" / STAGE
    out_dir.mkdir(parents=True, exist_ok=True)
    durations: dict[str, float] = {}
    failed: list[str] = []
    for shot in storyboard["shots"]:
        text = shot["narration"]
        if not text:
            continue
        sid = shot["id"]
        h = input_hash(text, providers.DEFAULT_STYLE, providers.DEFAULT_VOICE, providers.GEMINI_TTS_MODEL)
        path = out_dir / f"{sid}.wav"
        if not manifest.is_fresh(sid, h):
            try:
                path.write_bytes(_generate(sid, text, h, tts, sleep))
            except Exception:  # noqa: BLE001 - reported together after the other shots finish
                failed.append(sid)
                continue
            manifest.put(sid, h, str(path.relative_to(common.ROOT)))
        durations[sid] = media.duration(path)
    if failed:
        raise RuntimeError(f"narration failed for: {', '.join(failed)}")
    return durations


if __name__ == "__main__":
    from pipeline.validate import load_storyboard

    d = run(load_storyboard())
    for k, v in d.items():
        print(f"{k}  {v:5.1f}s")
    print(f"total narration {sum(d.values()):.1f}s")
