import json
import subprocess

import pytest

from pipeline import common, providers, radio_cut, timeline

SB = {
    "shots": [
        {"id": "s01", "duration_s": 5, "narration": "line one"},
        {"id": "s02", "duration_s": 3, "narration": "a longer second line"},
        {"id": "s03", "duration_s": 4, "narration": None},
    ]
}
DUR = {"s01": 2.0, "s02": 4.0}


def test_shot_lengths_use_set_duration_unless_narration_needs_more():
    assert timeline.shot_lengths(SB, DUR) == {"s01": 5.0, "s02": 4.5, "s03": 4.0}


def test_shot_starts_are_cumulative():
    assert timeline.shot_starts(SB, DUR) == {"s01": 0.0, "s02": 5.0, "s03": 9.5}


def test_total_adds_up():
    assert timeline.total(SB, DUR) == pytest.approx(13.5)


@pytest.fixture
def narration_files(tmp_path, monkeypatch):
    monkeypatch.setattr(common, "ROOT", tmp_path)
    d = tmp_path / "outputs" / "narration" / "gemini"
    d.mkdir(parents=True)
    for sid, secs in DUR.items():
        (d / f"{sid}.wav").write_bytes(providers.pcm_to_wav(b"\x00\x00" * int(24000 * secs)))
    return tmp_path


def _streams(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type", "-of", "json", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout
    return [s["codec_type"] for s in json.loads(out)["streams"]]


def test_radio_cut_length_matches_timeline(narration_files):
    from pipeline import media

    out = radio_cut.build(SB, DUR)
    assert media.duration(out) == pytest.approx(13.5, abs=0.3)


def test_radio_cut_has_black_video_and_audio(narration_files):
    out = radio_cut.build(SB, DUR)
    assert sorted(_streams(out)) == ["audio", "video"]
