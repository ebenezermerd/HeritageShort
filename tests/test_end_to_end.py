import io
import json

import pytest
from PIL import Image

from pipeline import common, providers, run_all

SB = {
    "title": "t",
    "ratios": ["9:16", "16:9"],
    "style_block": "painted look for testing",
    "characters": [{"id": "a", "name": "A (A)", "age": 16, "look": "short dark hair"}],
    "music": {"caption": "gentle acoustic", "bpm": 80, "key": "D major", "duration_s": 30},
    "end_card": {"text": "Made with AI. Painted from memory.", "duration_s": 2},
    "shots": [
        {"id": "s01", "reason": "r", "narration": "First line.", "image_prompt": "one", "characters": ["a"],
         "seed": 1, "duration_s": 3, "motion": {"mode": "kenburns", "camera": "push_in", "prompt": "p"}},
        {"id": "s02", "reason": "r", "narration": "Second line.", "image_prompt": "two", "characters": [],
         "seed": 2, "duration_s": 3, "motion": {"mode": "wan", "camera": "pull_out", "prompt": "p"}},
        {"id": "s03", "reason": "r", "narration": None, "image_prompt": "three", "characters": [],
         "seed": 3, "duration_s": 3, "motion": {"mode": "kenburns", "camera": "pan_left", "prompt": "p"}},
    ],
}


class Fakes:
    def __init__(self):
        self.tts_calls, self.gen_calls = [], []

    def tts(self, text, style):
        self.tts_calls.append(text)
        return providers.pcm_to_wav(b"\x00\x10" * 24000)  # one second of a faint tone

    def gen(self, prompt, seed, size):
        self.gen_calls.append(prompt)
        buf = io.BytesIO()
        Image.new("RGB", (64, 112), (seed * 40, 90, 60)).save(buf, "JPEG")
        return buf.getvalue()


@pytest.fixture
def project(tmp_path, monkeypatch):
    monkeypatch.setattr(common, "ROOT", tmp_path)
    return tmp_path


def lines(root):
    return [json.loads(x) for x in (root / "runs.jsonl").read_text().splitlines()]


def go(fakes, sb=SB):
    return run_all.pipeline(sb, tts=fakes.tts, gen=fakes.gen, sleep=lambda s: None)


def test_both_ratios_are_produced(project):
    outputs = go(Fakes())
    assert outputs["9:16"].name == "final_9x16.mp4" and outputs["9:16"].exists()
    assert outputs["16:9"].name == "final_16x9.mp4" and outputs["16:9"].exists()


def test_second_run_makes_no_model_calls_and_logs_nothing_new(project):
    fakes = Fakes()
    go(fakes)
    calls = (len(fakes.tts_calls), len(fakes.gen_calls))
    n = len(lines(project))
    go(fakes)
    assert (len(fakes.tts_calls), len(fakes.gen_calls)) == calls
    assert len(lines(project)) == n


def test_one_narration_edit_regenerates_only_that_line_and_reassembles(project):
    fakes = Fakes()
    go(fakes)
    n = len(lines(project))
    edited = json.loads(json.dumps(SB))
    edited["shots"][0]["narration"] = "A different first line."
    go(fakes, edited)
    assert fakes.tts_calls[-1] == "A different first line." and len(fakes.tts_calls) == 3
    assert len(fakes.gen_calls) == 6  # 3 shots x 2 ratios, none repeated
    new = lines(project)[n:]
    assert [r["stage"] for r in new if r["stage"] in ("narration", "keyframes")] == ["narration"]
    assert sum(1 for r in new if r["stage"] == "assemble") == 2


def test_restore_assets_copies_only_missing_files(project):
    (project / "assets/shots").mkdir(parents=True)
    (project / "assets/shots/s02.mp4").write_bytes(b"clip")
    run_all.restore_assets()
    assert (project / "outputs/shots/raw/s02.mp4").read_bytes() == b"clip"
    (project / "outputs/shots/raw/s02.mp4").write_bytes(b"newer download")
    run_all.restore_assets()
    assert (project / "outputs/shots/raw/s02.mp4").read_bytes() == b"newer download"
