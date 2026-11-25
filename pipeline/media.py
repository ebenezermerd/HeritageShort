"""Small ffprobe helpers shared by the stages."""
from __future__ import annotations

import subprocess
from pathlib import Path


def decodes_fully(path: Path, tolerance: float = 0.95) -> bool:
    """True only if FFmpeg decodes the whole file without errors and reaches (almost) its declared length.

    A file cut short after an intact header still reports its full duration, so reading the header
    is not enough; this actually decodes it."""
    try:
        declared = duration(path)
    except Exception:  # noqa: BLE001 - unreadable means not valid
        return False
    proc = subprocess.run(["ffmpeg", "-v", "error", "-nostats", "-progress", "pipe:1", "-i", str(path),
                           "-f", "null", "-"], capture_output=True, text=True)
    if proc.returncode != 0 or proc.stderr.strip():
        return False
    reached = None
    for line in proc.stdout.splitlines():
        if line.startswith("out_time_us=") and line.split("=", 1)[1].isdigit():
            reached = int(line.split("=", 1)[1]) / 1e6
    return reached is not None and reached >= tolerance * declared


def size(path: Path) -> tuple[int, int]:
    """(width, height) of the first video stream."""
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
         "-of", "csv=s=x:p=0", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    w, h = out.split("x")
    return int(w), int(h)


def duration(path: Path) -> float:
    """Length in seconds of an audio or video file, read with ffprobe."""
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    return float(out)
