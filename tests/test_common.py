import json

import pytest

from pipeline import common


@pytest.fixture(autouse=True)
def isolated_root(tmp_path, monkeypatch):
    monkeypatch.setattr(common, "ROOT", tmp_path)
    return tmp_path


def test_log_run_appends_valid_json_line(isolated_root):
    common.log_run("narrate", "s1", "gemini", "tts-model", {"voice": "x"}, 7, "abc", 1.5, "ok")
    lines = (isolated_root / "runs.jsonl").read_text().strip().splitlines()
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row["stage"] == "narrate"
    assert row["shot_id"] == "s1"
    assert row["seed"] == 7
    assert row["latency_s"] == 1.5
    assert row["cost_usd"] == 0.0
    assert row["error"] is None
    assert "ts" in row


def test_input_hash_changes_when_any_part_changes():
    base = common.input_hash("a line", {"seed": 1})
    assert base == common.input_hash("a line", {"seed": 1})
    assert base != common.input_hash("a line.", {"seed": 1})
    assert base != common.input_hash("a line", {"seed": 2})


def test_input_hash_uses_file_bytes(tmp_path):
    f = tmp_path / "ref.png"
    f.write_bytes(b"one")
    first = common.input_hash(f)
    f.write_bytes(b"two")
    assert common.input_hash(f) != first


def test_manifest_is_fresh_only_for_same_hash_and_existing_file(isolated_root):
    out = isolated_root / "outputs" / "narration" / "s1.wav"
    out.parent.mkdir(parents=True)
    out.write_bytes(b"audio")
    m = common.Manifest("narration")
    assert not m.is_fresh("s1", "h1")
    m.put("s1", "h1", str(out))
    assert common.Manifest("narration").is_fresh("s1", "h1")
    assert not common.Manifest("narration").is_fresh("s1", "h2")
    out.unlink()
    assert not common.Manifest("narration").is_fresh("s1", "h1")


def test_with_retries_succeeds_on_third_try():
    calls, sleeps = [], []

    def flaky():
        calls.append(1)
        if len(calls) < 3:
            raise RuntimeError("rate limited")
        return "ok"

    assert common.with_retries(flaky, sleep=sleeps.append) == "ok"
    assert sleeps == [2.0, 4.0]


def test_with_retries_raises_after_three():
    sleeps = []

    def always_fails():
        raise ValueError("nope")

    with pytest.raises(ValueError):
        common.with_retries(always_fails, sleep=sleeps.append)
    assert sleeps == [2.0, 4.0]


def test_require_env_exits_with_name(monkeypatch):
    monkeypatch.delenv("HS_MISSING_KEY", raising=False)
    with pytest.raises(SystemExit) as exc:
        common.require_env("HS_MISSING_KEY")
    assert "HS_MISSING_KEY" in str(exc.value)
