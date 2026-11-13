"""Seam C: `--full` asks for every document against every Rule, which is what the real run is.

A whole-corpus run on the stub takes minutes (nearly every stub P(yes) is distinct, so the curve has
thousands of rows a Rule), so these tests check what the command hands to the pipeline rather than
running it. The real run is the end-to-end check.
"""

import pytest

from jev_cascade import cli
from jev_cascade.pipeline import DEFAULT_RULE_IDS, TRACER_DOC_IDS
from jev_cascade.rulebook import RULEBOOK


@pytest.fixture
def captured(monkeypatch, tmp_path):
    """What the command passes to `run`, without running it."""
    seen = {}

    class Done:
        report_path = tmp_path / "report.md"

        class stats:
            pairs = calls_made = cache_hits = 0
            seconds = 0.0

    def fake_run(**kwargs):
        seen.update(kwargs)
        return Done

    monkeypatch.setattr(cli, "run", fake_run)
    monkeypatch.setattr(cli.config, "cuad_is_available", lambda: True)
    return seen


def test_full_asks_for_every_document_and_every_rule(captured, tmp_path):
    assert cli.main(["--full", "--out", str(tmp_path)]) == 0

    assert captured["doc_ids"] is None  # None is the whole License Agreement Set
    assert captured["rule_ids"] == tuple(rule.id for rule in RULEBOOK)
    assert len(captured["rule_ids"]) == 7


def test_without_full_the_command_is_still_the_three_document_tracer(captured, tmp_path):
    assert cli.main(["--out", str(tmp_path)]) == 0

    assert captured["doc_ids"] == TRACER_DOC_IDS
    assert captured["rule_ids"] == DEFAULT_RULE_IDS


def test_full_cannot_be_narrowed_by_doc_or_rule(captured, tmp_path):
    for narrowing in (["--rule", "R1"], ["--doc", "Some Title"]):
        with pytest.raises(SystemExit):
            cli.main(["--full", "--out", str(tmp_path), *narrowing])
    assert captured == {}
