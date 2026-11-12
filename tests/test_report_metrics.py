"""Seam C: the report shows every Evaluator figure per Rule, each beside its counts."""

import pytest

from jev_cascade import config
from jev_cascade.corpus import load_corpus
from jev_cascade.jev import StubJevClient
from jev_cascade.pipeline import TRACER_DOC_IDS, run
from jev_cascade.rulebook import rule

pytestmark = pytest.mark.skipif(
    not config.cuad_is_available(),
    reason=f"CUAD v1 not present at {config.cuad_dir()}; the dataset is not in this repo",
)


def _section(markdown: str, heading: str) -> str:
    start = markdown.index(heading)
    end = markdown.find("\n## ", start + len(heading))
    return markdown[start : end if end != -1 else len(markdown)]


@pytest.fixture(scope="module")
def result(tmp_path_factory):
    return run(client=StubJevClient(), out_dir=tmp_path_factory.mktemp("report"))


def test_the_rule_section_reports_the_false_alarm_rate_apart_from_precision(result):
    section = _section(result.markdown, "## R1 — ")
    metric = result.metrics[0]
    # The tracer set holds one document CUAD certifies as having no R1 clause, so the rate is
    # defined, and it is printed as counts first.
    assert metric.certified_negative_clauses > 0
    assert (
        f"| False-alarm rate on Certified Negative documents | "
        f"{metric.certified_negative_escalated}/{metric.certified_negative_clauses} Clauses"
    ) in section
    assert "Certified Negative" in section and "Inferred Negative" in section
    assert (
        f"{metric.certified_negative_clauses} Certified Negative and "
        f"{metric.inferred_negative_clauses} Inferred Negative"
    ) in section


def test_the_pipeline_tells_the_evaluator_which_documents_are_certified(result):
    certified = {
        d.doc_id
        for d in load_corpus(rules=[rule("R1")], doc_ids=TRACER_DOC_IDS)
        if d.is_certified_negative("R1")
    }
    in_certified = sum(1 for c in result.clauses if c.doc_id in certified)
    assert certified  # the tracer set includes one
    assert result.metrics[0].certified_negative_clauses == in_certified


def test_the_base_rate_sits_beside_precision(result):
    section = _section(result.markdown, "## R1 — ")
    metric = result.metrics[0]
    precision_row = next(line for line in section.splitlines() if line.startswith("| Precision"))
    assert f"base rate {metric.holding_clauses}/{metric.clauses}" in precision_row


def test_the_report_states_precision_reads_in_single_digits_by_arithmetic(result):
    section = _section(result.markdown, "## R1 — ")
    assert "single digits" in section
    assert "by arithmetic" in section


def test_the_report_has_a_fully_binned_section_counting_clauses_and_words(result):
    section = _section(result.markdown, "## Fully Binned Clauses")
    fully = result.fully_binned
    assert f"{fully.fully_binned_clauses}/{fully.clauses} Clauses" in section
    assert f"{fully.fully_binned_words}/{fully.total_words} words" in section
    # One Rule was asked in this run, and the report says so rather than claiming seven.
    assert "every Rule asked" in section
    assert "1 Rule" in section
