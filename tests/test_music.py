import subprocess

import pytest

from pipeline import common, media, music


@pytest.fixture(autouse=True)
def isolated_root(tmp_path, monkeypatch):
    monkeypatch.setattr(common, "ROOT", tmp_path)
    (tmp_path / "EXPERIMENTS.md").write_text("# Experiments\n\n## E01. First thing\n\nbody\n")
    return tmp_path


def tone(path, seconds):
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
                    "-i", f"sine=frequency=220:duration={seconds}", str(path)], check=True)


def test_zero_length_and_garbage_candidates_are_rejected(isolated_root):
    raw = isolated_root / "outputs/music/raw"
    tone(raw / "a.flac", 20)
    (raw / "b.flac").write_bytes(b"")
    (raw / "c.flac").write_bytes(b"not audio")
    assert [p.name for p in music.import_candidates()] == ["a.flac"]


def test_choose_copies_the_pick_and_records_the_reason_in_experiments(isolated_root):
    raw = isolated_root / "outputs/music/raw"
    tone(raw / "a.flac", 20)
    tone(raw / "b.flac", 25)
    score = music.choose(1, "softest texture, leaves room for the voice")
    assert score.name == "score.wav"
    assert media.duration(score) == pytest.approx(25, abs=0.3)
    text = (isolated_root / "EXPERIMENTS.md").read_text()
    assert "## E02." in text
    assert "softest texture, leaves room for the voice" in text
    assert "b.flac" in text


def test_second_choice_gets_the_next_experiment_number(isolated_root):
    raw = isolated_root / "outputs/music/raw"
    tone(raw / "a.flac", 20)
    music.choose(0, "first reason")
    music.choose(0, "second reason")
    assert "## E03." in (isolated_root / "EXPERIMENTS.md").read_text()


def test_choose_with_no_candidates_says_so(isolated_root):
    with pytest.raises(SystemExit, match="no valid music candidates"):
        music.choose(0, "anything")


def test_fallback_score_has_requested_duration(isolated_root):
    out = music.fallback_score(12.0, isolated_root / "outputs/music/fallback.wav")
    assert media.duration(out) == pytest.approx(12.0, abs=0.2)


def test_flac_cut_short_after_an_intact_header_is_rejected(isolated_root):
    raw = isolated_root / "outputs/music/raw"
    tone(raw / "a.flac", 20)
    data = (raw / "a.flac").read_bytes()
    (raw / "a.flac").write_bytes(data[: len(data) // 4])
    assert music.import_candidates() == []
