import subprocess

from pipeline import media


def _make(path, args):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args, str(path)], check=True)


def _truncate(path, fraction):
    data = path.read_bytes()
    path.write_bytes(data[: int(len(data) * fraction)])


def test_a_good_file_decodes_fully(tmp_path):
    mp4 = tmp_path / "a.mp4"
    _make(mp4, ["-f", "lavfi", "-i", "testsrc2=s=160x284:r=24:d=4", "-pix_fmt", "yuv420p",
                "-movflags", "+faststart"])
    assert media.decodes_fully(mp4)


def test_mp4_cut_short_after_an_intact_header_does_not(tmp_path):
    # Review finding: a faststart MP4 cut to a third still reported its full duration.
    mp4 = tmp_path / "a.mp4"
    _make(mp4, ["-f", "lavfi", "-i", "testsrc2=s=160x284:r=24:d=4", "-pix_fmt", "yuv420p",
                "-movflags", "+faststart"])
    _truncate(mp4, 0.33)
    assert not media.decodes_fully(mp4)


def test_flac_cut_short_does_not(tmp_path):
    flac = tmp_path / "a.flac"
    _make(flac, ["-f", "lavfi", "-i", "sine=frequency=220:duration=20"])
    _truncate(flac, 0.25)
    assert not media.decodes_fully(flac)


def test_garbage_does_not(tmp_path):
    bad = tmp_path / "a.mp4"
    bad.write_bytes(b"not media")
    assert not media.decodes_fully(bad)
