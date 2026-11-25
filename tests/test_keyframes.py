import io
import json

import pytest
from PIL import Image

from pipeline import common, keyframes

SB = {
    "style_block": "warm hand-painted look",
    "characters": [
        {"id": "beki", "name": "Bereket (Beki)", "age": 19, "look": "tall, short curly hair"},
        {"id": "tesfa", "name": "Tesahun (Tesfa)", "age": 17, "look": "slim, short dark hair"},
    ],
    "ratios": ["9:16", "16:9"],
    "shots": [
        {"id": "s01", "image_prompt": "the spring at dawn", "seed": 1, "characters": []},
        {"id": "s02", "image_prompt": "a boy jumps", "seed": 2, "characters": ["beki"]},
    ],
}


@pytest.fixture(autouse=True)
def isolated_root(tmp_path, monkeypatch):
    monkeypatch.setattr(common, "ROOT", tmp_path)
    return tmp_path


class FakeGen:
    def __init__(self, fail_on=None):
        self.calls = []
        self.fail_on = fail_on

    def __call__(self, prompt, seed, size, refs=None):
        self.calls.append((prompt, seed, size))
        if self.fail_on and self.fail_on in prompt:
            raise RuntimeError("429 quota")
        # Cloudflare's klein actually returns JPEG bytes, so the fake does too.
        buf = io.BytesIO()
        Image.new("RGB", (8, 8), (seed, 0, 0)).save(buf, "JPEG")
        return buf.getvalue()


def runs(root):
    p = root / "runs.jsonl"
    return [json.loads(x) for x in p.read_text().splitlines()] if p.exists() else []


def test_two_ratios_per_shot(isolated_root):
    gen = FakeGen()
    out = keyframes.run(SB, gen, sleep=lambda s: None)
    assert (isolated_root / "outputs/keyframes/9x16/s01.png").exists()
    assert (isolated_root / "outputs/keyframes/16x9/s02.png").exists()
    assert set(out["s01"]) == {"9:16", "16:9"}
    sizes = {c[2] for c in gen.calls}
    assert sizes == {(768, 1344), (1344, 768)}


def test_saved_keyframes_are_real_png_files(isolated_root):
    keyframes.run(SB, FakeGen(), sleep=lambda s: None)
    head = (isolated_root / "outputs/keyframes/9x16/s01.png").read_bytes()[:8]
    assert head == b"\x89PNG\r\n\x1a\n"


def test_prompt_contains_style_block_and_only_the_characters_in_the_shot():
    gen = FakeGen()
    keyframes.run(SB, gen, sleep=lambda s: None)
    by_seed = {c[1]: c[0] for c in gen.calls}
    assert "warm hand-painted look" in by_seed[2]
    assert "tall, short curly hair" in by_seed[2]
    assert "slim, short dark hair" not in by_seed[2]
    assert "tall, short curly hair" not in by_seed[1]


def test_cache_hit_makes_no_calls():
    gen = FakeGen()
    keyframes.run(SB, gen, sleep=lambda s: None)
    n = len(gen.calls)
    keyframes.run(SB, gen, sleep=lambda s: None)
    assert len(gen.calls) == n


def test_changing_one_prompt_regenerates_only_that_shot_in_both_ratios():
    gen = FakeGen()
    keyframes.run(SB, gen, sleep=lambda s: None)
    n = len(gen.calls)
    changed = json.loads(json.dumps(SB))
    changed["shots"][1]["image_prompt"] = "a boy jumps higher"
    keyframes.run(changed, gen, sleep=lambda s: None)
    assert len(gen.calls) - n == 2


def test_third_failure_is_logged_failed_and_other_shots_continue(isolated_root):
    gen = FakeGen(fail_on="a boy jumps")
    with pytest.raises(RuntimeError, match="s02"):
        keyframes.run(SB, gen, sleep=lambda s: None)
    assert (isolated_root / "outputs/keyframes/9x16/s01.png").exists()
    failed = [r for r in runs(isolated_root) if r["status"] == "failed"]
    assert len(failed) == 6  # 3 attempts x 2 ratios


def _with_refs(root):
    sb = json.loads(json.dumps(SB))
    sb["references"] = [{"id": "spring", "prompt": "the empty spring", "seed": 5,
                         "size": [1024, 768], "use": "the same spring, pool and trees"}]
    sb["shots"][1]["refs"] = ["spring"]
    ref = root / "outputs/references/spring.png"
    ref.parent.mkdir(parents=True)
    Image.new("RGB", (1024, 768), (0, 120, 140)).save(ref)
    return sb, ref


class RefGen(FakeGen):
    def __call__(self, prompt, seed, size, refs=None):
        self.refs = getattr(self, "refs", {})
        self.refs[(seed, size)] = refs or []
        return super().__call__(prompt, seed, size, refs)


def test_shot_with_refs_sends_each_reference_under_512_and_names_it_in_the_prompt(isolated_root):
    sb, _ = _with_refs(isolated_root)
    gen = RefGen()
    keyframes.run(sb, gen, sleep=lambda s: None)
    sent = gen.refs[(2, (768, 1344))]
    assert len(sent) == 1
    w, h = Image.open(io.BytesIO(sent[0])).size
    assert max(w, h) < 512
    assert gen.refs[(1, (768, 1344))] == []
    prompt = [c[0] for c in gen.calls if c[1] == 2][0]
    assert "image 0" in prompt.lower() and "the same spring, pool and trees" in prompt


def test_changing_a_reference_image_regenerates_the_shots_that_use_it(isolated_root):
    sb, ref = _with_refs(isolated_root)
    gen = RefGen()
    keyframes.run(sb, gen, sleep=lambda s: None)
    n = len(gen.calls)
    Image.new("RGB", (1024, 768), (200, 10, 10)).save(ref)
    keyframes.run(sb, gen, sleep=lambda s: None)
    assert [c[1] for c in gen.calls[n:]] == [2, 2]
