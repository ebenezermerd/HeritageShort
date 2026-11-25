"""Assembly: cut the shots to the timeline, caption them, duck the score under the voice, set the
loudness, add the end card, and export one aspect ratio. Everything here is deterministic FFmpeg."""
from __future__ import annotations

import json
import re
import subprocess
import time
from pathlib import Path

from pipeline import captions, common, media, music, timeline
from pipeline.common import Manifest, input_hash, log_run
from pipeline.keyframes import ratio_dir
from pipeline.radio_cut import LEAD_S
from pipeline.shots import FINAL_SIZES, FPS

STAGE = "assemble"
TARGET_LUFS = -14
TRUE_PEAK = -1.5  # a little under the -1 dB ceiling so AAC encoding cannot push it over
SCORE_GAIN = 0.6
DUCK = "threshold=0.02:ratio=6:attack=300:release=1500"


def _ff(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args], check=True, capture_output=True, text=True)


def _loudnorm_two_pass(src: Path, dst: Path) -> None:
    base = f"loudnorm=I={TARGET_LUFS}:TP={TRUE_PEAK}:LRA=11"
    probe = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(src), "-af", f"{base}:print_format=json",
                            "-f", "null", "-"], capture_output=True, text=True, check=True).stderr
    m = json.loads(re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", probe, flags=re.S).group(0))
    measured = (f"measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:"
                f"measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    _ff("-i", str(src), "-af", f"{base}:{measured}", "-ar", "44100", "-ac", "2", str(dst))


def run(storyboard: dict, durations: dict[str, float], ratio: str) -> Path:
    rd, size = ratio_dir(ratio), FINAL_SIZES[ratio]
    root = common.ROOT
    out = root / "outputs" / f"final_{rd}.mp4"
    work = root / "outputs" / STAGE / rd
    work.mkdir(parents=True, exist_ok=True)

    shots_list = storyboard["shots"]
    clips = [root / "outputs" / "shots" / rd / f"{s['id']}.mp4" for s in shots_list]
    narr = {s["id"]: root / "outputs" / "narration" / f"{s['id']}.wav" for s in shots_list if s["id"] in durations}
    starts = timeline.shot_starts(storyboard, durations)
    card = storyboard["end_card"]
    total = timeline.total(storyboard, durations) + card["duration_s"]

    score = root / "outputs" / "music" / "score.wav"
    score_fallback = not score.exists()
    h = input_hash(ratio, {k: round(v, 3) for k, v in durations.items()}, card,
                   [s["narration"] for s in shots_list], *clips, *narr.values(),
                   "fallback" if score_fallback else score)
    manifest = Manifest(STAGE)
    if manifest.is_fresh(ratio, h):
        return out

    start_time = time.time()
    # 1. captions and end card
    cap_pngs = {s["id"]: captions.render(s["narration"], size, work / f"cap_{s['id']}.png")
                for s in shots_list if s["narration"]}
    card_png = captions.end_card(card["text"], size, work / "end_card.png")
    card_mp4 = work / "end_card.mp4"
    _ff("-loop", "1", "-i", str(card_png), "-t", f"{card['duration_s']}", "-r", str(FPS),
        "-vf", "format=yuv420p", "-c:v", "libx264", str(card_mp4))

    # 2. picture: concatenate shots + end card, overlay captions at their shot's time
    listing = work / "concat.txt"
    listing.write_text("".join(f"file '{p}'\n" for p in [*clips, card_mp4]))
    inputs = ["-f", "concat", "-safe", "0", "-i", str(listing)]
    chain, last = [], "0:v"
    for i, (sid, png) in enumerate(cap_pngs.items(), start=1):
        inputs += ["-loop", "1", "-t", f"{total:.3f}", "-i", str(png)]
        t0 = starts[sid] + LEAD_S
        t1 = t0 + durations[sid] + 0.3
        chain.append(f"[{last}][{i}:v]overlay=enable='between(t,{t0:.3f},{t1:.3f})'[v{i}]")
        last = f"v{i}"
    silent = work / "picture.mp4"
    _ff(*inputs, "-filter_complex", ";".join(chain) if chain else "null", "-map", f"[{last}]" if chain else "0:v",
        "-t", f"{total:.3f}", "-r", str(FPS), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-an", str(silent))

    # 3. sound: voice at each shot's start, score ducked under it
    if score_fallback:
        score = music.fallback_score(total, work / "score_fallback.wav")
        log_run("music", None, "ffmpeg", "synth-pad", {}, None, "", 0.0, "fallback",
                error="no ACE-Step score in outputs/music/score.wav, used a synthesised pad")
    audio_in = ["-i", str(score)]
    parts = [f"[0:a]aresample=44100,apad,atrim=0:{total:.3f},afade=t=out:st={total - 2.5:.3f}:d=2.5,"
             f"volume={SCORE_GAIN}[score]"]
    voices = []
    for i, (sid, wav) in enumerate(narr.items(), start=1):
        audio_in += ["-i", str(wav)]
        parts.append(f"[{i}:a]aresample=44100,adelay={int((starts[sid] + LEAD_S) * 1000)}:all=1[n{i}]")
        voices.append(f"[n{i}]")
    if voices:
        parts.append(f"{''.join(voices)}amix=inputs={len(voices)}:normalize=0:duration=longest,"
                     f"apad,atrim=0:{total:.3f},asplit=2[v1][v2]")
        parts.append(f"[score][v1]sidechaincompress={DUCK}[duck]")
        parts.append("[duck][v2]amix=inputs=2:normalize=0:duration=longest[mix]")
    else:
        parts.append("[score]anull[mix]")
    mix = work / "mix.wav"
    _ff(*audio_in, "-filter_complex", ";".join(parts), "-map", "[mix]", "-t", f"{total:.3f}", "-ac", "2", str(mix))
    normed = work / "mix_norm.wav"
    _loudnorm_two_pass(mix, normed)

    # 4. mux
    _ff("-i", str(silent), "-i", str(normed), "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-t", f"{total:.3f}", "-movflags", "+faststart", str(out))
    log_run(STAGE, None, "ffmpeg", "ffmpeg", {"ratio": ratio, "lufs": TARGET_LUFS, "true_peak": TRUE_PEAK,
                                              "duck": DUCK}, None, h, time.time() - start_time, "ok")
    manifest.put(ratio, h, str(out.relative_to(root)))
    return out


if __name__ == "__main__":
    from pipeline import narrate
    from pipeline.validate import load_storyboard

    sb = load_storyboard()
    dur = narrate.run(sb, voice="say")
    for r in sb["ratios"]:
        print(run(sb, dur, r))
