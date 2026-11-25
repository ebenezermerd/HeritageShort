import json
import subprocess

import pytest
from PIL import Image

from pipeline import common, media, shots

SB = {
    "ratios": ["9:16", "16:9"],
    "shots": [
        {"id": "s01", "duration_s": 4, "narration": None, "seed": 1,
         "motion": {"mode": "wan", "camera": "push_in", "prompt": "slow push in"}},
        {"id": "s02", "duration_s": 3, "narration": None, "seed": 2,
         "motion": {"mode": "kenburns", "camera": "pull_out", "prompt": "pull out"}},
        {"id": "s03", "duration_s": 4, "narration": None, "seed": 3,
         "motion": {"mode": "wan", "camera": "pan_right", "prompt": "pan"}},
    ],
}


@pytest.fixture(autouse=True)
def isolated_root(tmp_path, monkeypatch):
    monkeypatch.setattr(common, "ROOT", tmp_path)
    for ratio, size in (("9x16", (768, 1344)), ("16x9", (1344, 768))):
        d = tmp_path / "outputs" / "keyframes" / ratio
        d.mkdir(parents=True)
        for sid in ("s01", "s02", "s03"):
            Image.new("RGB", size, (30, 120, 90)).save(d / f"{sid}.png")
    return tmp_path


def make_clip(path, seconds=3.5, job_hash=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
                    "-i", f"testsrc2=s=320x568:r=24:d={seconds}", "-pix_fmt", "yuv420p",
                    "-movflags", "+faststart", str(path)], check=True)
    if job_hash:
        path.with_suffix(".json").write_text(json.dumps({"hash": job_hash}))


def good_hash(i=0):
    return shots.wan_job_hash(SB["shots"][i])


def runs(root):
    p = root / "runs.jsonl"
    return [json.loads(x) for x in p.read_text().splitlines()] if p.exists() else []


def test_kenburns_output_has_requested_duration_and_size(isolated_root, tmp_path):
    out = shots.kenburns(isolated_root / "outputs/keyframes/9x16/s01.png", "push_in", 2.0,
                         tmp_path / "kb.mp4", (360, 640))
    assert media.duration(out) == pytest.approx(2.0, abs=0.15)
    assert media.size(out) == (360, 640)


def test_wan_job_file_lists_only_wan_shots_and_copies_keyframes(isolated_root):
    path = shots.export_wan_jobs(SB)
    jobs = json.loads(path.read_text())
    assert [j["id"] for j in jobs] == ["s01", "s03"]
    assert jobs[0]["prompt"] == "slow push in"
    assert (isolated_root / "outputs/jobs/keyframes/s01.png").exists()


def test_truncated_wan_clip_is_rejected(isolated_root):
    raw = isolated_root / "outputs/shots/raw"
    raw.mkdir(parents=True)
    (raw / "s01.mp4").write_bytes(b"not a video")
    make_clip(raw / "s03.mp4")
    assert shots.import_wan() == ["s03"]


def test_clip_cut_short_after_an_intact_header_is_rejected(isolated_root):
    # Review finding: a faststart MP4 cut to a third still reported its full duration.
    raw = isolated_root / "outputs/shots/raw"
    make_clip(raw / "s01.mp4", seconds=4.0, job_hash=good_hash(0))
    data = (raw / "s01.mp4").read_bytes()
    (raw / "s01.mp4").write_bytes(data[: len(data) // 3])
    assert shots.import_wan() == []
    shots.run(SB, {})
    fallbacks = [r for r in runs(isolated_root) if r["status"] == "fallback"]
    assert "s01" in {r["shot_id"] for r in fallbacks}


def test_missing_wan_clip_falls_back_to_kenburns_and_logs_it(isolated_root):
    out = shots.run(SB, {})
    assert out["s01"]["9:16"].exists()
    fallbacks = [r for r in runs(isolated_root) if r["status"] == "fallback"]
    assert {r["shot_id"] for r in fallbacks} == {"s01", "s03"}


def test_valid_wan_clip_is_used_for_9x16_and_fitted_to_the_shot_length(isolated_root):
    make_clip(isolated_root / "outputs/shots/raw/s01.mp4", seconds=3.5, job_hash=good_hash(0))
    out = shots.run(SB, {})
    assert media.duration(out["s01"]["9:16"]) == pytest.approx(4.0, abs=0.2)
    used = [r for r in runs(isolated_root) if r["shot_id"] == "s01" and r["params"].get("ratio") == "9:16"]
    assert used[-1]["provider"] == "wan"


def test_stale_wan_clip_falls_back_and_says_why(isolated_root):
    # Review finding: a clip made from an older keyframe or prompt was still used.
    make_clip(isolated_root / "outputs/shots/raw/s01.mp4", job_hash="0ld")
    shots.run(SB, {})
    rows = [r for r in runs(isolated_root) if r["shot_id"] == "s01" and r["status"] == "fallback"]
    assert rows and "stale" in rows[0]["error"]


def test_wan_clip_with_no_job_hash_is_not_trusted(isolated_root):
    make_clip(isolated_root / "outputs/shots/raw/s01.mp4")
    shots.run(SB, {})
    rows = [r for r in runs(isolated_root) if r["shot_id"] == "s01" and r["status"] == "fallback"]
    assert rows


def test_editing_the_prompt_makes_an_existing_clip_stale(isolated_root):
    make_clip(isolated_root / "outputs/shots/raw/s01.mp4", job_hash=good_hash(0))
    edited = json.loads(json.dumps(SB))
    edited["shots"][0]["motion"]["prompt"] = "a completely different motion"
    shots.run(edited, {})
    rows = [r for r in runs(isolated_root) if r["shot_id"] == "s01" and r["status"] == "fallback"]
    assert rows and "stale" in rows[0]["error"]


def test_16x9_never_uses_wan(isolated_root):
    make_clip(isolated_root / "outputs/shots/raw/s01.mp4", job_hash=good_hash(0))
    shots.run(SB, {})
    wide = [r for r in runs(isolated_root) if r["shot_id"] == "s01" and r["params"].get("ratio") == "16:9"]
    assert wide and all(r["provider"] == "ffmpeg" for r in wide)


def test_second_run_makes_no_new_work(isolated_root):
    shots.run(SB, {})
    n = len(runs(isolated_root))
    shots.run(SB, {})
    assert len(runs(isolated_root)) == n
