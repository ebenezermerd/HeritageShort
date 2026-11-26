import io
import json

import pytest
from PIL import Image

from pipeline import candidates, common

SB = {
    "style_block": "warm hand-painted look",
    "characters": [{"id": "beki", "name": "Bereket (Beki)", "age": 19, "look": "tall"}],
    "ratios": ["9:16", "16:9"],
    "shots": [
        {"id": "s01", "image_prompt": "the spring", "seed": 10, "characters": []},
        {"id": "s02", "image_prompt": "a boy jumps", "seed": 20, "characters": ["beki"]},
    ],
}


@pytest.fixture(autouse=True)
def isolated_root(tmp_path, monkeypatch):
    monkeypatch.setattr(common, "ROOT", tmp_path)
    return tmp_path


class FakeGen:
    def __init__(self):
        self.calls = []

    def __call__(self, prompt, seed, size, refs=None):
        self.calls.append((seed, size))
        buf = io.BytesIO()
        Image.new("RGB", (8, 8), (seed, 0, 0)).save(buf, "JPEG")
        return buf.getvalue()


def test_n_candidates_per_shot_use_consecutive_seeds_in_9x16(isolated_root):
    gen = FakeGen()
    out = candidates.run(SB, n=3, gen=gen, sleep=lambda s: None)
    assert [p.name for p in out["s02"]] == ["20.png", "21.png", "22.png"]
    assert {c[1] for c in gen.calls} == {(768, 1344)}
    assert (isolated_root / "outputs/candidates/s01/12.png").exists()


def test_rerun_makes_no_new_calls_and_each_call_is_logged(isolated_root):
    gen = FakeGen()
    candidates.run(SB, n=2, gen=gen, sleep=lambda s: None)
    n = len(gen.calls)
    candidates.run(SB, n=2, gen=gen, sleep=lambda s: None)
    assert len(gen.calls) == n == 4
    rows = [json.loads(x) for x in (isolated_root / "runs.jsonl").read_text().splitlines()]
    assert len(rows) == 4 and {r["stage"] for r in rows} == {"candidates"}


def test_only_selected_shots_when_asked(isolated_root):
    gen = FakeGen()
    candidates.run(SB, n=2, shots=["s02"], gen=gen, sleep=lambda s: None)
    assert [c[0] for c in gen.calls] == [20, 21]


def test_picked_candidate_becomes_the_9x16_keyframe_without_a_new_call(isolated_root):
    # Cloudflare's klein does not reproduce an image from the same seed (E14), so a pick must keep
    # the exact file that was chosen, not just remember the seed.
    from pipeline import keyframes

    gen = FakeGen()
    out = candidates.run(SB, n=3, gen=gen, sleep=lambda s: None)
    chosen = out["s02"][1]
    sb = json.loads(json.dumps(SB))
    sb["shots"][1]["pick"] = {"9:16": 21}
    candidates.pick(sb, "s02", "9:16")
    kf_gen = FakeGen()
    keyframes.run(sb, kf_gen, sleep=lambda s: None)
    nine = (isolated_root / "outputs/keyframes/9x16/s02.png").read_bytes()
    assert nine == chosen.read_bytes()
    assert (768, 1344) not in {c[1] for c in kf_gen.calls if c[0] == 21}


def test_a_9x16_keyframe_can_be_cut_from_the_picked_16x9_candidate(isolated_root):
    # s08: every 9:16 candidate drew a fourth boy; the 16:9 pick had exactly three. A logged crop
    # of the 16:9 file becomes the 9:16 keyframe, and the keyframe stage then makes no call for it.
    from pipeline import keyframes

    wide = candidates.candidate_path("s02", 20, "16:9")
    wide.parent.mkdir(parents=True)
    img = Image.new("RGB", (1344, 768), (0, 0, 0))
    img.paste((255, 0, 0), (500, 0, 939, 768))  # the red band (768 x 4:7 = 439 wide) is the part to keep
    img.save(wide)
    sb = json.loads(json.dumps(SB))
    sb["shots"][1]["pick"] = {"16:9": 20}
    sb["shots"][1]["crop_from_wide"] = {"9:16": {"x": 500}}
    candidates.pick(sb, "s02", "16:9")
    dest = candidates.pick(sb, "s02", "9:16")
    out = Image.open(dest).convert("RGB")
    assert out.size == (768, 1344)
    assert out.getpixel((10, 10)) == (255, 0, 0) and out.getpixel((758, 1334)) == (255, 0, 0)
    row = [json.loads(x) for x in (isolated_root / "runs.jsonl").read_text().splitlines()][-1]
    assert row["shot_id"] == "s02" and row["params"]["crop_from"].endswith("16x9/20.png")
    kf_gen = FakeGen()
    keyframes.run(sb, kf_gen, sleep=lambda s: None)
    assert not [c for c in kf_gen.calls if c[0] == 20]
