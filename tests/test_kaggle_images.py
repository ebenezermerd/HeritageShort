import json

import pytest
from PIL import Image

from pipeline import candidates, common, kaggle_images, keyframes, references

SB = {
    "style_block": "painted",
    "characters": [{"id": "beki", "name": "Bereket (Beki)", "age": 19, "look": "tall"}],
    "ratios": ["9:16", "16:9"],
    "references": [{"id": "spring", "prompt": "the spring", "seed": 7, "size": [1024, 768], "use": "the spring"}],
    "shots": [
        {"id": "s01", "image_prompt": "the pool", "seed": 10, "characters": [], "refs": ["spring"]},
        {"id": "s02", "image_prompt": "a boy jumps", "seed": 20, "characters": ["beki"]},
    ],
}


@pytest.fixture(autouse=True)
def isolated_root(tmp_path, monkeypatch):
    monkeypatch.setattr(common, "ROOT", tmp_path)
    return tmp_path


def test_jobs_list_references_first_then_n_candidates_per_shot_and_ratio_with_exact_prompts():
    jobs = json.loads(kaggle_images.export_jobs(SB, n=2).read_text())
    assert jobs[0] == {"kind": "ref", "id": "spring", "seed": 7, "width": 1024, "height": 768,
                       "prompt": "painted. the spring", "refs": [], "out": "refs/spring.png"}
    shots = [j for j in jobs if j["kind"] == "shot"]
    assert len(shots) == 2 * 2 * 2
    s01 = [j for j in shots if j["id"] == "s01" and j["ratio"] == "9:16"]
    assert [j["seed"] for j in s01] == [10, 11]
    assert s01[0]["prompt"] == keyframes.build_prompt(SB, SB["shots"][0])
    assert s01[0]["refs"] == ["refs/spring.png"] and s01[0]["out"] == "shots/9x16/s01/10.png"
    assert (s01[0]["width"], s01[0]["height"]) == (768, 1344)


def _results(root):
    res = root / "kaggle_results"
    for rel, size in [("refs/spring.png", (1024, 768)), ("shots/9x16/s01/11.png", (768, 1344)),
                      ("shots/16x9/s01/10.png", (1344, 768))]:
        (res / rel).parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", size, (1, 2, 3)).save(res / rel)
    return res


def test_imported_reference_counts_as_cached_so_the_pipeline_makes_no_call(isolated_root):
    kaggle_images.import_results(SB, _results(isolated_root))
    calls = []
    references.run(SB, gen=lambda *a, **k: calls.append(a), sleep=lambda s: None)
    assert calls == []


def test_picking_imported_candidates_per_ratio_makes_keyframes_cached(isolated_root):
    kaggle_images.import_results(SB, _results(isolated_root))
    sb = json.loads(json.dumps(SB))
    sb["shots"] = sb["shots"][:1]
    sb["shots"][0]["pick"] = {"9:16": 11, "16:9": 10}
    candidates.pick(sb, "s01", "9:16", provider="kaggle")
    candidates.pick(sb, "s01", "16:9", provider="kaggle")
    calls = []
    keyframes.run(sb, lambda *a, **k: calls.append(a), sleep=lambda s: None)
    assert calls == []
    rows = [json.loads(x) for x in (isolated_root / "runs.jsonl").read_text().splitlines()]
    assert any(r["status"] == "imported" and r["provider"] == "kaggle" for r in rows)
    assert [r["seed"] for r in rows if r["status"] == "picked"] == [11, 10]
