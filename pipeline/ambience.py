"""Ambience layer: the sound of the place (water, a few birds) and splash effects, all from FFmpeg.

It is a stand-in for nothing: the brief calls ambience and small effects optional but says they make
AI pictures feel real. Splashes come from the storyboard (`sfx` on a shot), not from code."""
from __future__ import annotations

import subprocess
from pathlib import Path

from pipeline import timeline

SR = 44100
# Birds: short rising chirps on a slow rhythm, at different periods so they never line up.
BIRD = ("aevalsrc='0.10*sin(2*PI*(2600+900*sin(2*PI*9*t))*t)*lt(mod(t+{off},{period}),0.30)"
        "*sin(PI*mod(t+{off},{period})/0.30)':s=44100:d={total}")
GAIN = {"water": 0.55, "birds": 0.5, "splash": 1.0}


def splash_times(storyboard: dict, durations: dict[str, float]) -> list[float]:
    """Absolute film time of every splash cue."""
    starts = timeline.shot_starts(storyboard, durations)
    return sorted(starts[s["id"]] + c["at_s"] for s in storyboard["shots"]
                  for c in s.get("sfx", []) if c["type"] == "splash")


def build(total: float, splashes: list[float], out: Path) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    T = f"{total:.3f}"
    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "lavfi", "-i", f"anoisesrc=color=pink:amplitude=0.5:r={SR}:d={T}:seed=1",
           "-f", "lavfi", "-i", BIRD.format(off=0.0, period=6.7, total=T),
           "-f", "lavfi", "-i", BIRD.format(off=2.9, period=9.1, total=T)]
    parts = [f"[0:a]highpass=f=250,lowpass=f=3200,tremolo=f=0.4:d=0.35,volume={GAIN['water']}[water]",
             f"[1:a][2:a]amix=inputs=2:normalize=0,volume={GAIN['birds']}[birds]"]
    mix = ["[water]", "[birds]"]
    for i, t in enumerate(splashes):
        cmd += ["-f", "lavfi", "-i", f"anoisesrc=color=white:amplitude=0.9:r={SR}:d=1.2:seed={i + 5}"]
        n = 3 + i
        parts.append(f"[{n}:a]highpass=f=700,lowpass=f=6500,afade=t=in:d=0.02,afade=t=out:st=0.05:d=1.1,"
                     f"volume={GAIN['splash']},adelay={int(t * 1000)}:all=1[sp{i}]")
        mix.append(f"[sp{i}]")
    parts.append(f"{''.join(mix)}amix=inputs={len(mix)}:normalize=0:duration=longest,"
                 f"apad,atrim=0:{T},aformat=channel_layouts=stereo[out]")
    subprocess.run(cmd + ["-filter_complex", ";".join(parts), "-map", "[out]", str(out)], check=True)
    return out
