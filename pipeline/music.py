"""Music stage: import ACE-Step candidates made on Kaggle, record the choice, or fall back to a pad."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

from pipeline import common, media
from pipeline.radio_cut import PAD

MIN_CANDIDATE_SECONDS = 5.0
AUDIO_SUFFIXES = {".flac", ".wav", ".mp3", ".ogg"}


def _raw_dir() -> Path:
    return common.ROOT / "outputs" / "music" / "raw"


def import_candidates(raw_dir: Path | None = None) -> list[Path]:
    """Readable audio files of a sensible length, in name order. Empty or corrupt files are skipped."""
    raw_dir = raw_dir or _raw_dir()
    good = []
    for p in sorted(raw_dir.glob("*")):
        if p.suffix.lower() not in AUDIO_SUFFIXES:
            continue
        try:
            if media.duration(p) >= MIN_CANDIDATE_SECONDS and media.decodes_fully(p):
                good.append(p)
        except Exception:  # noqa: BLE001 - a truncated download is just not a candidate
            continue
    return good


def _next_experiment_number(text: str) -> int:
    return max([int(n) for n in re.findall(r"^## E(\d+)\.", text, flags=re.M)] or [0]) + 1


def choose(index: int, reason: str) -> Path:
    """Copy candidate `index` to outputs/music/score.wav and write the reason into EXPERIMENTS.md."""
    candidates = import_candidates()
    if not candidates:
        raise SystemExit("no valid music candidates in outputs/music/raw")
    pick = candidates[index]
    score = common.ROOT / "outputs" / "music" / "score.wav"
    score.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(pick), "-ar", "44100", "-ac", "2",
                    str(score)], check=True)
    exp = common.ROOT / "EXPERIMENTS.md"
    text = exp.read_text() if exp.exists() else "# Experiments\n"
    n = _next_experiment_number(text)
    names = ", ".join(p.name for p in candidates)
    entry = (f"\n## E{n:02d}. Which score candidate? \n\n"
             f"**Hypothesis.** One of the ACE-Step candidates sits under the narration without competing with it.\n\n"
             f"**Change.** Listened to {len(candidates)} candidates ({names}) quietly under the narration.\n\n"
             f"**Result.** Chose {pick.name}. {reason}\n")
    exp.write_text(text.rstrip("\n") + "\n" + entry)
    return score


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 3:
        raise SystemExit('usage: python -m pipeline.music <candidate number from 1> "why this one"')
    cands = import_candidates()
    for i, p in enumerate(cands, start=1):
        print(f"{i}  {p.name}")
    print(choose(int(sys.argv[1]) - 1, sys.argv[2]))


def fallback_score(seconds: float, out: Path) -> Path:
    """A quiet synthesised pad, used when no ACE-Step candidate has been downloaded yet."""
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
                    "-i", PAD.format(total=f"{seconds:.3f}"), "-ac", "2", str(out)], check=True)
    return out
