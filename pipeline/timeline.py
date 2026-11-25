"""One timing rule shared by the radio cut and the final assembly."""
from __future__ import annotations

NARRATION_TAIL_S = 0.5  # breathing room after a spoken line


def shot_lengths(storyboard: dict, durations: dict[str, float]) -> dict[str, float]:
    """A shot lasts its set duration, or its narration plus a tail if that is longer."""
    lengths: dict[str, float] = {}
    for shot in storyboard["shots"]:
        sid = shot["id"]
        length = float(shot["duration_s"])
        if sid in durations:
            length = max(length, durations[sid] + NARRATION_TAIL_S)
        lengths[sid] = length
    return lengths


def shot_starts(storyboard: dict, durations: dict[str, float]) -> dict[str, float]:
    starts: dict[str, float] = {}
    t = 0.0
    for sid, length in shot_lengths(storyboard, durations).items():
        starts[sid] = t
        t += length
    return starts


def total(storyboard: dict, durations: dict[str, float]) -> float:
    return sum(shot_lengths(storyboard, durations).values())
