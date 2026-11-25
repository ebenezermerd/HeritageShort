import json

import pytest

from pipeline import common
from scripts import check_docs

REQUIRED = ["README.md", "ARCHITECTURE.md", "DESIGN.md", "EXPERIMENTS.md", "FAILURES.md", "COSTS.md",
            "ETHICS.md", "REPORT.md"]
RUN_FIELDS = ["ts", "stage", "shot_id", "provider", "model", "params", "seed", "input_hash", "latency_s",
              "status", "cost_usd", "error"]


def experiments(n):
    return "# Experiments\n\n" + "".join(
        f"## E{i:02d}. Thing\n\n**Hypothesis.** h\n\n**Change.** c\n\n**Result.** r\n\n" for i in range(1, n + 1))


ETHICS = '- **Tesfa:** "ofcourse you can use it"\n- **Beki:** "Okay you may use mine"\n'


@pytest.fixture
def project(tmp_path, monkeypatch):
    monkeypatch.setattr(common, "ROOT", tmp_path)
    for name in REQUIRED:
        (tmp_path / name).write_text("# x\n")
    (tmp_path / "EXPERIMENTS.md").write_text(experiments(10))
    (tmp_path / "ETHICS.md").write_text(ETHICS)
    (tmp_path / "runs.jsonl").write_text(json.dumps({k: None for k in RUN_FIELDS}) + "\n")
    return tmp_path


def test_a_complete_project_passes(project):
    assert check_docs.main() == 0


def test_missing_file_fails(project):
    (project / "COSTS.md").unlink()
    assert check_docs.main() != 0


def test_nine_experiments_fails_ten_passes(project):
    (project / "EXPERIMENTS.md").write_text(experiments(9))
    assert check_docs.main() != 0
    (project / "EXPERIMENTS.md").write_text(experiments(10))
    assert check_docs.main() == 0


def test_experiment_without_a_result_does_not_count(project):
    text = experiments(10).replace("**Result.** r", "", 1)
    (project / "EXPERIMENTS.md").write_text(text)
    assert check_docs.main() != 0


def test_runs_line_missing_a_field_fails(project):
    row = {k: None for k in RUN_FIELDS}
    del row["latency_s"]
    (project / "runs.jsonl").write_text(json.dumps(row) + "\n")
    assert check_docs.main() != 0


def test_ethics_without_both_consent_quotes_fails(project):
    (project / "ETHICS.md").write_text('- **Tesfa:** "ofcourse you can use it"\n')
    assert check_docs.main() != 0
