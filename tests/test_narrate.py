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
    assert (isolated_root / "outputs/narration/gemini/s01.wav").exists()
    assert (isolated_root / "outputs/narration/gemini/s02.wav").exists()
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


def test_changing_the_prompt_format_invalidates_cached_audio(monkeypatch):
    tts = FakeTTS()
    narrate.run(sb("one", "two"), tts, sleep=lambda s: None)
    n = len(tts.calls)
    monkeypatch.setattr(providers, "tts_prompt", lambda text, style: f"Say softly: {text}")
    narrate.run(sb("one", "two"), tts, sleep=lambda s: None)
    assert len(tts.calls) - n == 2


def test_switching_voice_regenerates_and_logs_the_real_provider(isolated_root):
    tts = FakeTTS()
    narrate.run(sb("one"), tts, sleep=lambda s: None, voice="say")
    n = len(tts.calls)
    narrate.run(sb("one"), tts, sleep=lambda s: None, voice="gemini")
    assert len(tts.calls) - n == 1
    rows = runs(isolated_root)
    assert [r["provider"] for r in rows] == ["macos", "gemini"]


def test_each_voice_keeps_its_own_audio_and_never_overwrites_the_other(isolated_root):
    # Review finding: a placeholder run used to overwrite the real Gemini narration on disk.
    tts_gemini, tts_say = FakeTTS(), FakeTTS()
    narrate.run(sb("one"), tts_gemini, sleep=lambda s: None, voice="gemini")
    gemini_bytes = (isolated_root / "outputs/narration/gemini/s01.wav").read_bytes()
    narrate.run(sb("one"), tts_say, sleep=lambda s: None, voice="say")
    assert (isolated_root / "outputs/narration/say/s01.wav").exists()
    assert (isolated_root / "outputs/narration/gemini/s01.wav").read_bytes() == gemini_bytes
    narrate.run(sb("one"), tts_gemini, sleep=lambda s: None, voice="gemini")
    assert len(tts_gemini.calls) == 1  # still cached, no new Gemini request


def test_imported_audio_counts_as_cached_and_is_logged_as_imported(isolated_root, tmp_path):
    # A real Gemini clip made earlier for the same line, voice and prompt must not cost another request.
    src = tmp_path / "sample.wav"
    src.write_bytes(providers.pcm_to_wav(b"\x00\x00" * 24000))
    narrate.import_audio("s01", "one", src, note="Gemini output from experiment E01")
    tts = FakeTTS()
    durations = narrate.run(sb("one", "two"), tts, sleep=lambda s: None, voice="gemini")
    assert tts.calls == ["two"]
    assert durations["s01"] == pytest.approx(1.0, abs=0.05)
    row = [r for r in runs(isolated_root) if r["status"] == "imported"][0]
    assert row["shot_id"] == "s01" and row["provider"] == "gemini"
    assert "experiment E01" in row["error"]


def test_import_rejects_a_file_that_does_not_decode(isolated_root, tmp_path):
    bad = tmp_path / "bad.wav"
    bad.write_bytes(b"not audio")
    with pytest.raises(ValueError, match="does not decode"):
        narrate.import_audio("s01", "one", bad)


def test_silent_shot_gets_no_file_and_no_call(isolated_root):
    tts = FakeTTS()
    durations = narrate.run(sb("one", None), tts, sleep=lambda s: None)
    assert not (isolated_root / "outputs/narration/gemini/s02.wav").exists()
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
    assert (isolated_root / "outputs/narration/gemini/s01.wav").exists()


def test_repair_unwraps_double_wrapped_clips_and_logs_it(isolated_root):
    inner = providers.pcm_to_wav(b"\x03\x00" * 2400) + b""
    d = isolated_root / "outputs/narration/gemini"
    d.mkdir(parents=True)
    (d / "s01.wav").write_bytes(providers.pcm_to_wav(inner))
    (d / "s02.wav").write_bytes(inner)
    fixed = narrate.repair("gemini")
    assert fixed == ["s01"]
    assert (d / "s01.wav").read_bytes() == inner
    rows = [r for r in runs(isolated_root) if r["status"] == "repaired"]
    assert [r["shot_id"] for r in rows] == ["s01"]
