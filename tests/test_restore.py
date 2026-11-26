import json

import pytest

from pipeline import common, run_all


@pytest.fixture(autouse=True)
def isolated_root(tmp_path, monkeypatch):
    monkeypatch.setattr(common, "ROOT", tmp_path)
    return tmp_path


def _put(root, rel, data=b"x"):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)
    return p


def test_committed_keyframes_references_and_narration_are_restored_with_their_manifests(isolated_root):
    # A fresh clone has no outputs/. The chosen pictures and the Gemini voice cannot be made again
    # (klein on Cloudflare does not repeat a seed, E14; Gemini allows 10 requests a day), so they are
    # committed under assets/ and restored, manifests included, so every stage sees them as cached.
    for rel in ["keyframes/9x16/s01.png", "keyframes/16x9/s01.png", "keyframes/manifest.json",
                "references/spring.png", "references/manifest.json",
                "narration/gemini/s01.wav", "narration/gemini/manifest.json"]:
        _put(isolated_root, f"assets/{rel}", rel.encode())
    run_all.restore_assets()
    for rel in ["keyframes/9x16/s01.png", "keyframes/16x9/s01.png", "keyframes/manifest.json",
                "references/spring.png", "references/manifest.json",
                "narration/gemini/s01.wav", "narration/gemini/manifest.json"]:
        assert (isolated_root / "outputs" / rel).read_bytes() == rel.encode()


def test_restore_never_overwrites_work_already_in_outputs(isolated_root):
    _put(isolated_root, "assets/keyframes/9x16/s01.png", b"committed")
    _put(isolated_root, "outputs/keyframes/9x16/s01.png", b"newer local pick")
    run_all.restore_assets()
    assert (isolated_root / "outputs/keyframes/9x16/s01.png").read_bytes() == b"newer local pick"
