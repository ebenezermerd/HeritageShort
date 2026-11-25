import io

import pytest
from PIL import Image

from pipeline import common, references

SB = {"style_block": "painted", "references": [
    {"id": "spring", "prompt": "the empty spring", "seed": 3, "size": [1024, 768], "use": "the spring"}]}


@pytest.fixture(autouse=True)
def isolated_root(tmp_path, monkeypatch):
    monkeypatch.setattr(common, "ROOT", tmp_path)
    return tmp_path


def fake(calls):
    def gen(prompt, seed, size, refs=None):
        calls.append((prompt, size))
        buf = io.BytesIO()
        Image.new("RGB", size, (0, 0, 0)).save(buf, "JPEG")
        return buf.getvalue()
    return gen


def test_reference_is_made_once_at_its_size_with_the_style_block(isolated_root):
    calls = []
    references.run(SB, gen=fake(calls), sleep=lambda s: None)
    references.run(SB, gen=fake(calls), sleep=lambda s: None)
    assert len(calls) == 1 and calls[0][1] == (1024, 768) and calls[0][0].startswith("painted")
    assert Image.open(isolated_root / "outputs/references/spring.png").size == (1024, 768)
