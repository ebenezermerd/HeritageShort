import copy
import json

import pytest

from pipeline import common, validate


def _write(tmp_path, data):
    p = tmp_path / "storyboard.json"
    p.write_text(json.dumps(data))
    return p


def _good():
    return json.loads((common.ROOT / "storyboard.json").read_text())


def test_example_storyboard_is_valid():
    sb = validate.load_storyboard()
    assert sb["shots"]


def test_shot_without_reason_is_rejected(tmp_path):
    sb = copy.deepcopy(_good())
    del sb["shots"][0]["reason"]
    with pytest.raises(SystemExit) as exc:
        validate.load_storyboard(_write(tmp_path, sb))
    assert "reason" in str(exc.value)


def test_unknown_motion_mode_is_rejected(tmp_path):
    sb = copy.deepcopy(_good())
    sb["shots"][2]["motion"]["mode"] = "sora"
    with pytest.raises(SystemExit) as exc:
        validate.load_storyboard(_write(tmp_path, sb))
    assert "motion" in str(exc.value)


def test_blank_narration_is_rejected(tmp_path):
    sb = copy.deepcopy(_good())
    sb["shots"][0]["narration"] = "   "
    with pytest.raises(SystemExit) as exc:
        validate.load_storyboard(_write(tmp_path, sb))
    assert "narration" in str(exc.value)


def test_silent_shot_may_have_null_narration():
    sb = validate.load_storyboard()
    assert sb["shots"][-1]["narration"] is None


def test_ten_shots_with_unique_ids():
    ids = validate.shot_ids(validate.load_storyboard())
    assert len(ids) == 10
    assert len(set(ids)) == 10
