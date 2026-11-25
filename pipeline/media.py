"""Small ffprobe helpers shared by the stages."""
from __future__ import annotations

import subprocess
from pathlib import Path


def duration(path: Path) -> float:
    """Length in seconds of an audio or video file, read with ffprobe."""
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    return float(out)
