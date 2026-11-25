"""Narration stage: one WAV per narrated shot, cached by the exact prompt, voice and model."""
from __future__ import annotations

import argparse
import shutil
import time
from pathlib import Path
from typing import Callable

from pipeline import common, media, providers
from pipeline.common import Manifest, input_hash, log_run, with_retries

STAGE = "narration"


def audio_dir(voice: str):
    """Each voice has its own folder, so a placeholder run can never overwrite real Gemini audio."""
    return common.ROOT / "outputs" / STAGE / voice


def audio_path(voice: str, shot_id: str):
    return audio_dir(voice) / f"{shot_id}.wav"


def _hash(text: str, voice: str) -> str:
    provider, model, voice_name = providers.VOICES[voice]
    return input_hash(providers.tts_prompt(text, providers.DEFAULT_STYLE), voice_name, model)


def import_audio(shot_id: str, text: str, src, voice: str = "gemini", note: str = "") -> Path:
    """Register an existing clip as this shot's narration, as if it had just been generated.

    Only for audio made from exactly this prompt, voice and model (it is stored under that hash).
    Logged as status "imported" so the record shows it was not a new request."""
    src = Path(src)
    if not media.decodes_fully(src):
        raise ValueError(f"{src} does not decode")
    provider, model, voice_name = providers.VOICES[voice]
    h = _hash(text, voice)
    dest = audio_path(voice, shot_id)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dest)
    Manifest(f"{STAGE}/{voice}").put(shot_id, h, str(dest.relative_to(common.ROOT)))
    log_run(STAGE, shot_id, provider, model, {"voice": voice_name, "source": src.name}, None, h, 0.0,
            "imported", error=note or "imported existing audio")
    return dest


def repair(voice: str = "gemini") -> list[str]:
    """Fix clips saved by the old bug: Gemini's own WAV wrapped in a second WAV header, so its
    provenance block played as noise at the end of each line (FAILURES #11). No new requests."""
    provider, model, _ = providers.VOICES[voice]
    fixed = []
    for path in sorted(audio_dir(voice).glob("*.wav")):
        inner = providers.unwrap_double_wav(path.read_bytes())
        if inner is None:
            continue
        path.write_bytes(inner)
        fixed.append(path.stem)
        log_run(STAGE, path.stem, provider, model, {"fix": "unwrap double WAV header"}, None, "", 0.0,
                "repaired", error="removed the outer WAV header; Gemini's own WAV and its C2PA chunk kept")
    return fixed


def _generate(shot_id: str, text: str, h: str, tts: Callable[[str, str], bytes], sleep,
              provider: str, model: str, voice: str) -> bytes:
    params = {"voice": voice, "style": providers.DEFAULT_STYLE}

    def attempt() -> bytes:
        start = time.time()
        try:
            audio = tts(text, providers.DEFAULT_STYLE)
        except Exception as e:  # noqa: BLE001 - every failure is logged then re-raised for the retry
            log_run(STAGE, shot_id, provider, model, params, None, h, time.time() - start,
                    "failed", error=str(e)[:300])
            raise
        log_run(STAGE, shot_id, provider, model, params, None, h, time.time() - start, "ok")
        return audio

    return with_retries(attempt, base_delay=15.0, sleep=sleep)


def run(storyboard: dict, tts: Callable[[str, str], bytes] | None = None,
        sleep: Callable[[float], None] = time.sleep, voice: str = "gemini") -> dict[str, float]:
    """Make narration for every shot with a line. Returns {shot_id: seconds}.

    voice="gemini" is the real narrator; voice="say" is a local placeholder for when the
    Gemini free quota is spent."""
    provider, model, voice_name = providers.VOICES[voice]
    if tts is None:
        tts = providers.gemini_tts if voice == "gemini" else providers.say_tts
    manifest = Manifest(f"{STAGE}/{voice}")
    out_dir = audio_dir(voice)
    out_dir.mkdir(parents=True, exist_ok=True)
    durations: dict[str, float] = {}
    failed: list[str] = []
    for shot in storyboard["shots"]:
        text = shot["narration"]
        if not text:
            continue
        sid = shot["id"]
        h = _hash(text, voice)
        path = out_dir / f"{sid}.wav"
        if not manifest.is_fresh(sid, h):
            try:
                path.write_bytes(_generate(sid, text, h, tts, sleep, provider, model, voice_name))
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

    ap = argparse.ArgumentParser()
    ap.add_argument("--voice", choices=sorted(providers.VOICES), default="gemini")
    ap.add_argument("--repair", action="store_true", help="unwrap clips saved with a double WAV header")
    a = ap.parse_args()
    if a.repair:
        print("repaired:", narrate_fixed := repair(a.voice))
        raise SystemExit
    d = run(load_storyboard(), voice=a.voice)
    for k, v in d.items():
        print(f"{k}  {v:5.1f}s")
    print(f"total narration {sum(d.values()):.1f}s")
