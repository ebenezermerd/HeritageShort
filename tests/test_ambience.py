import subprocess

import pytest

from pipeline import ambience, media, validate


def rms_db(path, start, dur):
    r = subprocess.run(["ffmpeg", "-v", "info", "-ss", str(start), "-t", str(dur), "-i", str(path),
                        "-af", "astats=metadata=0", "-f", "null", "-"], capture_output=True, text=True)
    line = [x for x in r.stderr.splitlines() if "RMS level dB" in x][-1]
    return float(line.split(":")[-1])


def test_bed_has_the_requested_length_and_is_not_silent(tmp_path):
    out = ambience.build(6.0, [], tmp_path / "a.wav")
    assert media.duration(out) == pytest.approx(6.0, abs=0.1)
    assert rms_db(out, 0, 6) > -50


def test_a_splash_cue_makes_that_moment_louder(tmp_path):
    out = ambience.build(8.0, [4.0], tmp_path / "a.wav")
    assert rms_db(out, 4.0, 0.5) > rms_db(out, 1.0, 0.5) + 3


def test_storyboard_cues_are_in_the_schema_and_turn_into_absolute_times():
    sb = validate.load_storyboard()
    durations = {s["id"]: 2.0 for s in sb["shots"] if s["narration"]}
    times = ambience.splash_times(sb, durations)
    assert times == sorted(times) and len(times) >= 4
