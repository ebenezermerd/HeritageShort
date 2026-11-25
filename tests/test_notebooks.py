import json

import pytest

from pipeline import common

NAMES = ["00_smoke", "10_acestep", "20_wan", "30_likeness"]


def _load(name):
    return json.loads((common.ROOT / "notebooks" / f"{name}.ipynb").read_text())


def _source(nb):
    return "\n".join("".join(c["source"]) for c in nb["cells"])


@pytest.mark.parametrize("name", NAMES)
def test_notebook_is_valid_ipynb_with_code(name):
    nb = _load(name)
    assert nb["nbformat"] == 4
    assert any(c["cell_type"] == "code" for c in nb["cells"])


@pytest.mark.parametrize("name", ["10_acestep", "20_wan"])
def test_generating_notebooks_log_timing_and_resume(name):
    src = _source(_load(name))
    assert "notebook_log.jsonl" in src
    assert "exists()" in src  # skips outputs that are already saved, so a timeout loses nothing


def test_wan_notebook_uses_the_documented_model_and_fp16_for_t4():
    src = _source(_load("20_wan"))
    assert "Wan-AI/Wan2.2-TI2V-5B-Diffusers" in src
    assert "float16" in src  # T4 has no bfloat16
    assert "enable_model_cpu_offload" in src


def test_acestep_notebook_asks_for_instrumental_candidates_from_the_storyboard():
    src = _source(_load("10_acestep"))
    assert "instrumental=True" in src
    assert "batch_size=3" in src
    assert "storyboard.json" in src


def test_likeness_notebook_refuses_to_run_without_the_consent_flag():
    src = _source(_load("30_likeness"))
    assert "CONSENT_RECORDED = False" in src
    assert "assert CONSENT_RECORDED" in src


@pytest.mark.parametrize("name", NAMES)
def test_no_secrets_in_notebooks(name):
    src = _source(_load(name))
    assert "AQ." not in src and "cfut_" not in src
