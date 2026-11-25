import json

import pytest

from pipeline import common, narrate, providers


@pytest.fixture(autouse=True)
def isolated_root(tmp_path, monkeypatch):
    monkeypatch.setattr(common, "ROOT", tmp_path)
    return tmp_path


class FakeTTS:
    """Returns a real WAV whose length depends on the text, and counts calls."""

    def __init__(self, fail_on=None):
        self.calls = []
        self.fail_on = fail_on

    def __call__(self, text, style):
        self.calls.append(text)
        if self.fail_on and self.fail_on in text:
            raise RuntimeError("503 overloaded")
        return providers.pcm_to_wav(b"\x00\x00" * 2400 * len(text), rate=24000)


def sb(*lines):
    return {"shots": [{"id": f"s{i + 1:02d}", "narration": t} for i, t in enumerate(lines)]}


def runs(root):
    p = root / "runs.jsonl"
    return [json.loads(x) for x in p.read_text().splitlines()] if p.exists() else []


def test_one_file_per_narrated_shot(isolated_root):
    tts = FakeTTS()
    durations = narrate.run(sb("one", "two words"), tts, sleep=lambda s: None)
    assert (isolated_root / "outputs/narration/s01.wav").exists()
    assert (isolated_root / "outputs/narration/s02.wav").exists()
    assert durations["s01"] == pytest.approx(0.1 * 3, abs=0.01)
    assert durations["s02"] == pytest.approx(0.1 * 9, abs=0.01)


def test_second_run_makes_zero_tts_calls():
    tts = FakeTTS()
    story = sb("one", "two")
    narrate.run(story, tts, sleep=lambda s: None)
    before = len(tts.calls)
    narrate.run(story, tts, sleep=lambda s: None)
    assert len(tts.calls) == before


def test_changing_one_line_regenerates_only_that_shot(isolated_root):
    tts = FakeTTS()
    narrate.run(sb("one", "two", "three"), tts, sleep=lambda s: None)
    calls_before, log_before = len(tts.calls), len(runs(isolated_root))
    narrate.run(sb("one", "TWO changed", "three"), tts, sleep=lambda s: None)
    assert tts.calls[calls_before:] == ["TWO changed"]
    new = runs(isolated_root)[log_before:]
    assert len(new) == 1
    assert new[0]["shot_id"] == "s02" and new[0]["status"] == "ok"


def test_silent_shot_gets_no_file_and_no_call(isolated_root):
    tts = FakeTTS()
    durations = narrate.run(sb("one", None), tts, sleep=lambda s: None)
    assert not (isolated_root / "outputs/narration/s02.wav").exists()
    assert "s02" not in durations
    assert tts.calls == ["one"]


def test_rate_limit_backoff_waits_at_least_fifteen_seconds():
    # Gemini's free TTS answered 429 within seconds; 2s/4s backoff was not enough.
    sleeps = []
    with pytest.raises(RuntimeError):
        narrate.run(sb("bad line"), FakeTTS(fail_on="bad"), sleep=sleeps.append)
    assert sleeps == [15.0, 30.0]


def test_failed_shot_is_logged_each_attempt_and_reported(isolated_root):
    tts = FakeTTS(fail_on="bad")
    with pytest.raises(RuntimeError, match="s02"):
        narrate.run(sb("good", "bad line"), tts, sleep=lambda s: None)
    failed = [r for r in runs(isolated_root) if r["status"] == "failed"]
    assert len(failed) == 3
    assert all(r["shot_id"] == "s02" and "503" in r["error"] for r in failed)
    assert (isolated_root / "outputs/narration/s01.wav").exists()
