"""Radio cut: the narration on the film's real timing, over a quiet pad, on a black screen."""
from __future__ import annotations

import subprocess
from pathlib import Path

from pipeline import common, narrate, timeline

LEAD_S = 0.3  # a line starts a moment after its shot begins

PAD = (
    "aevalsrc=0.05*(0.7+0.3*sin(2*PI*0.2*t))"
    "*(sin(2*PI*110*t)+0.7*sin(2*PI*164.81*t)+0.5*sin(2*PI*220*t)):s=44100:d={total}"
)


def build(storyboard: dict, durations: dict[str, float], out: Path | None = None,
          voice: str = "gemini") -> Path:
    out = out or common.ROOT / "outputs" / "radio_cut.mp4"
    out.parent.mkdir(parents=True, exist_ok=True)
    starts = timeline.shot_starts(storyboard, durations)
    total = timeline.total(storyboard, durations)
    lines = [sid for sid in starts if sid in durations]

    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "lavfi", "-i", f"color=c=black:s=1280x720:r=24:d={total:.3f}",
           "-f", "lavfi", "-i", PAD.format(total=f"{total:.3f}")]
    for sid in lines:
        cmd += ["-i", str(narrate.audio_path(voice, sid))]

    parts = ["[1:a]volume=0.5[pad]"]
    mix_inputs = ["[pad]"]
    for i, sid in enumerate(lines):
        delay_ms = int((starts[sid] + LEAD_S) * 1000)
        parts.append(f"[{i + 2}:a]aresample=44100,adelay={delay_ms}:all=1[n{i}]")
        mix_inputs.append(f"[n{i}]")
    parts.append(f"{''.join(mix_inputs)}amix=inputs={len(mix_inputs)}:normalize=0:duration=longest[a]")

    cmd += ["-filter_complex", ";".join(parts), "-map", "0:v", "-map", "[a]",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-t", f"{total:.3f}", str(out)]
    subprocess.run(cmd, check=True)
    return out


if __name__ == "__main__":
    import argparse

    from pipeline import providers
    from pipeline.validate import load_storyboard

    ap = argparse.ArgumentParser()
    ap.add_argument("--voice", choices=sorted(providers.VOICES), default="gemini")
    voice = ap.parse_args().voice
    sb = load_storyboard()
    print(build(sb, narrate.run(sb, voice=voice), voice=voice))
