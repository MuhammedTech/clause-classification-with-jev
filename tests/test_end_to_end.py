"""Seam C, end to end: the command runs on real documents with the stub and writes the report."""

import pytest

from jev_cascade import config
from jev_cascade.cli import main
from jev_cascade.corpus import load_corpus
from jev_cascade.domain import holds
from jev_cascade.jev import CountingJevClient, StubJevClient
from jev_cascade.pipeline import TRACER_DOC_IDS, run
from jev_cascade.rulebook import rule
from jev_cascade.splitter import split_document

pytestmark = pytest.mark.skipif(
    not config.cuad_is_available(),
    reason=f"CUAD v1 not present at {config.cuad_dir()}; the dataset is not in this repo",
)


def test_the_run_writes_a_report_with_an_r1_table(tmp_path):
    result = run(client=StubJevClient(), out_dir=tmp_path)

    assert result.report_path.exists()
    markdown = result.report_path.read_text(encoding="utf-8")

    assert "## R1 — Cap On Liability" in markdown
    for figure in ("Clause Recall", "Precision", "Lost Provisions", "Binned Share"):
        assert figure in markdown, figure
    # Counts come before shares in each row.
    assert "holding Clauses Escalated" in markdown
    assert "words Binned" in markdown


def test_every_figure_is_labelled_as_stub(tmp_path):
    result = run(client=StubJevClient(), out_dir=tmp_path)
    assert "stub-derived" in result.markdown
    assert "carry no signal" in result.markdown


def test_a_second_run_makes_zero_client_calls(tmp_path):
    first = CountingJevClient(StubJevClient())
    run(client=first, out_dir=tmp_path)
    assert first.calls > 0

    second = CountingJevClient(StubJevClient())
    rerun = run(client=second, out_dir=tmp_path)

    assert second.calls == 0
    assert rerun.stats.cache_hits == rerun.stats.pairs


def test_the_report_rebuilds_from_the_cache_with_identical_figures(tmp_path):
    first = run(client=StubJevClient(), out_dir=tmp_path)
    rerun = run(client=StubJevClient(), out_dir=tmp_path)

    assert [m.binned_words for m in rerun.metrics] == [m.binned_words for m in first.metrics]
    assert [m.lost_provisions for m in rerun.metrics] == [
        m.lost_provisions for m in first.metrics
    ]


def test_the_clauses_partition_each_tracer_document():
    for document in load_corpus(rules=[rule("R1")], doc_ids=TRACER_DOC_IDS):
        clauses = split_document(document.doc_id, document.text)
        assert "".join(c.text for c in clauses) == document.text
        assert clauses[0].start == 0
        assert clauses[-1].end == len(document.text)


def test_no_highlight_in_the_tracer_documents_is_held_by_zero_clauses():
    # A Highlight held by nothing would read as Lost whatever Jev answered (ADR-0004).
    for document in load_corpus(rules=[rule("R1")], doc_ids=TRACER_DOC_IDS):
        clauses = split_document(document.doc_id, document.text)
        for highlight in document.highlights_for("R1"):
            assert any(holds(c, highlight) for c in clauses)


def test_no_clause_holds_a_highlight_from_another_document(tmp_path):
    # Offsets are per document. Pooling the tracer documents into one evaluation invented six
    # holding relations against four real ones, two of them inside the Certified Negative
    # document, and inflated the base rate from 1.2% to 3.5%.
    result = run(client=StubJevClient(), out_dir=tmp_path)

    for clause in result.clauses:
        for highlight in result.highlights:
            if holds(clause, highlight):
                assert clause.doc_id == highlight.doc_id


def test_the_certified_negative_document_holds_nothing(tmp_path):
    # CUAD flags this document as having no Cap On Liability clause anywhere, so no Clause of it
    # may hold an R1 Highlight. This is the spec's bulletproof negative.
    result = run(client=StubJevClient(), out_dir=tmp_path)
    certified = [
        d for d in load_corpus(rules=[rule("R1")], doc_ids=TRACER_DOC_IDS)
        if d.is_certified_negative("R1")
    ]
    assert len(certified) == 1
    certified_id = certified[0].doc_id

    for clause in (c for c in result.clauses if c.doc_id == certified_id):
        assert not any(holds(clause, h) for h in result.highlights)


def test_the_reported_base_rate_matches_the_measured_corpus_order(tmp_path):
    # docs/cuad-ground-truth.md measures a 1.57% base rate for Cap On Liability corpus-wide. A
    # tracer base rate several times that means Clauses are being credited with Highlights they
    # do not hold.
    result = run(client=StubJevClient(), out_dir=tmp_path)
    (r1,) = result.metrics
    assert r1.base_rate is not None
    assert r1.base_rate < 0.03


def test_the_command_runs_and_reports_where_it_wrote(tmp_path, capsys):
    exit_code = main(["--out", str(tmp_path), "--cutoff", "0.5"])
    captured = capsys.readouterr().out

    assert exit_code == 0
    assert "Wrote" in captured
    assert (tmp_path / "report.md").exists()
    assert (tmp_path / "pyes.jsonl").exists()
