import json
import re
import subprocess

import pytest

from pipeline import assemble, common, media, providers, timeline

SB = {
    "ratios": ["9:16", "16:9"],
    "end_card": {"text": "Made with AI. Painted from memory.", "duration_s": 2},
    "shots": [
        {"id": "s01", "duration_s": 4, "narration": "Arba Minch means forty springs."},
        {"id": "s02", "duration_s": 4, "narration": "Then Tesfa."},
        {"id": "s03", "duration_s": 3, "narration": None},
    ],
}
DUR = {"s01": 2.0, "s02": 1.0}
SIZES = {"9:16": (720, 1280), "16:9": (1280, 720)}


@pytest.fixture
def project(tmp_path, monkeypatch):
    monkeypatch.setattr(common, "ROOT", tmp_path)
    lengths = timeline.shot_lengths(SB, DUR)
    for ratio, (w, h) in SIZES.items():
        d = tmp_path / "outputs" / "shots" / ratio.replace(":", "x")
        d.mkdir(parents=True)
        for sid, secs in lengths.items():
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
                            "-i", f"testsrc2=s={w}x{h}:r=24:d={secs}", "-pix_fmt", "yuv420p",
                            str(d / f"{sid}.mp4")], check=True)
    nd = tmp_path / "outputs" / "narration"
    nd.mkdir(parents=True)
    for sid, secs in DUR.items():
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
                        "-i", f"sine=frequency=300:duration={secs}", "-ar", "24000", "-ac", "1",
                        str(nd / f"{sid}.wav")], check=True)
    return tmp_path


def _probe(path, entries):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          f"stream={entries}", "-of", "json", str(path)],
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out)["streams"][0]


def _loudness(path):
    res = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(path), "-af", "ebur128=peak=true",
                          "-f", "null", "-"], capture_output=True, text=True).stderr
    summary = res[res.rfind("Summary:"):]
    integrated = float(re.search(r"I:\s+(-?[\d.]+) LUFS", summary).group(1))
    peak = float(re.search(r"Peak:\s+(-?[\d.]+) dBFS", summary).group(1))
    return integrated, peak


def test_real_storyboard_total_is_between_60_and_90_seconds():
    sb = json.loads((common.ROOT / "storyboard.json").read_text())
    typical = {s["id"]: 3.0 for s in sb["shots"] if s["narration"]}
    total = timeline.total(sb, typical) + sb["end_card"]["duration_s"]
    assert 60 <= total <= 90


def test_vertical_output_has_expected_length_size_and_codecs(project):
    out = assemble.run(SB, DUR, "9:16")
    expected = timeline.total(SB, DUR) + 2
    assert media.duration(out) == pytest.approx(expected, abs=0.4)
    info = _probe(out, "codec_name,width,height,r_frame_rate,avg_frame_rate")
    assert info["codec_name"] == "h264"
    assert (info["width"], info["height"]) == (720, 1280)
    assert info["r_frame_rate"] == info["avg_frame_rate"] == "24/1"
    audio = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries",
                            "stream=codec_name", "-of", "csv=p=0", str(out)],
                           capture_output=True, text=True, check=True).stdout.strip()
    assert audio == "aac"


def test_horizontal_output_is_16_9(project):
    out = assemble.run(SB, DUR, "16:9")
    assert out.name == "final_16x9.mp4"
    assert (_probe(out, "width,height")["width"], _probe(out, "width,height")["height"]) == (1280, 720)


def test_loudness_is_near_minus_14_lufs_with_true_peak_below_minus_1(project):
    out = assemble.run(SB, DUR, "9:16")
    integrated, peak = _loudness(out)
    assert integrated == pytest.approx(-14.0, abs=1.5)
    assert peak <= -0.9


def test_sparse_speech_mix_still_reaches_the_target_loudness(tmp_path):
    # Real narration is short bursts over a quiet bed, so its peaks are high for its loudness.
    # Without a limiter, loudnorm stalled at about -15.5 LUFS on the real film (experiment E06).
    src, dst = tmp_path / "sparse.wav", tmp_path / "normed.wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    "aevalsrc=0.02*sin(2*PI*150*t)+0.1*sin(2*PI*300*t)*lt(mod(t\\,4)\\,0.6)"
                    "+0.8*sin(2*PI*1000*t)*lt(mod(t\\,4)\\,0.003):s=44100:d=20",
                    "-ac", "2", str(src)], check=True)
    assemble._loudnorm_two_pass(src, dst)
    integrated, peak = _loudness(dst)
    assert integrated == pytest.approx(-14.0, abs=0.7)
    assert peak <= -1.4


def test_missing_score_falls_back_and_is_logged_not_fatal(project):
    assemble.run(SB, DUR, "9:16")
    rows = [json.loads(x) for x in (project / "runs.jsonl").read_text().splitlines()]
    assert any(r["stage"] == "assemble" and r["status"] == "ok" for r in rows)
    assert any(r["stage"] == "music" and r["status"] == "fallback" for r in rows)


def test_second_run_with_same_inputs_does_not_rebuild(project):
    out = assemble.run(SB, DUR, "9:16")
    stamp = out.stat().st_mtime_ns
    assemble.run(SB, DUR, "9:16")
    assert out.stat().st_mtime_ns == stamp
