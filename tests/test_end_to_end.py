"""Seam C, end to end: the command runs on real documents with the stub and writes the report."""

import pytest

from jev_cascade import config
from jev_cascade.cli import main
from jev_cascade.corpus import load_corpus
from jev_cascade.domain import holds
from jev_cascade.jev import CountingJevClient, StubJevClient
from jev_cascade.pipeline import TRACER_DOC_IDS, run
from jev_cascade.rulebook import RULEBOOK, rule
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


def test_the_report_states_the_corpus_filter_and_the_pacira_normalisation(tmp_path):
    markdown = run(client=StubJevClient(), out_dir=tmp_path).markdown

    assert "## Corpus" in markdown
    # The filter that gives the set, and the two that do not.
    assert "Document Name" in markdown
    assert "licen" in markdown
    assert "| CSV `Filename` contains \"licen\" | 44 |" in markdown
    assert "| JSON `title` contains \"licen\" | 44 |" in markdown
    # The join and the one document that needs it.
    assert "alphanumerics" in markdown
    assert "PACIRA" in markdown.upper()


def _gate_rows(markdown: str) -> dict[str, str]:
    """The gate table's rows, keyed by Rule id, so assertions do not count table pipes."""
    rows = {}
    for line in markdown.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) == 6 and cells[0] in {rule_.id for rule_ in RULEBOOK} | {"R4"}:
            rows[cells[0]] = line
    return rows


def test_the_report_shows_all_seven_rules_with_their_counts_and_a_passing_gate(tmp_path):
    markdown = run(client=StubJevClient(), out_dir=tmp_path).markdown

    assert "## Rulebook" in markdown
    for rule_ in RULEBOOK:
        assert rule_.cuad_category in markdown, rule_.id
        assert rule_.detection_question in markdown, rule_.id

    rows = _gate_rows(markdown)
    assert sorted(rows) == ["R1", "R2", "R3", "R5", "R6", "R7", "R8"]
    for rule_id, row in rows.items():
        assert row.rstrip().endswith("| pass |"), row
    # Full-corpus counts, not the tracer subset: R8 at 41 documents and 85 Highlights.
    assert "| 41 | 85 | 12 | pass |" in rows["R8"]
    # The gate is settled from CUAD's annotations, so it never depends on the Splitter.
    assert "not from the Splitter" in markdown


def test_the_gate_is_corpus_wide_even_when_the_run_scores_one_document(tmp_path):
    markdown = run(
        client=StubJevClient(), doc_ids=TRACER_DOC_IDS[:1], out_dir=tmp_path
    ).markdown

    assert "| 41 | 85 | 12 | pass |" in _gate_rows(markdown)["R8"]
    assert "53 documents" in markdown


def test_the_report_gives_the_corrected_reason_uncapped_liability_was_dropped(tmp_path):
    markdown = run(client=StubJevClient(), out_dir=tmp_path).markdown

    assert "Uncapped Liability" in markdown
    # Dropped, so never asked as a Rule: no scored section, and no row in the gate table.
    assert "## R4" not in markdown
    assert "R4" not in _gate_rows(markdown)
    # Measured on all 53 documents, where it passes the gate by one Highlight.
    assert "17 documents and 26 Highlights" in markdown
    assert "passes the gate by one Highlight" in markdown
    assert "not independent of R1" in markdown
    # The reason ADR-0005 gave before Pacira joined may appear only as a superseded measurement,
    # never as the standing reason.
    assert "only Rule failing" not in markdown
    assert "the gate is not a reason to drop this Rule" in markdown
    assert "superseded" in markdown
    # Being compound does not distinguish R4 from R2 and R6, which survive, so it is not given.
    assert "compound" not in markdown


def test_the_report_warns_that_r5_and_r8_changed_meaning(tmp_path):
    markdown = run(client=StubJevClient(), out_dir=tmp_path).markdown

    assert "Non-Compete" in markdown
    assert "Volume Restriction" in markdown


def test_the_report_marks_the_detection_questions_as_drafts(tmp_path):
    # Ticket 08 is a human checkpoint: the user approves the wording before the real run.
    markdown = run(client=StubJevClient(), out_dir=tmp_path).markdown
    assert "draft" in markdown.lower()
    assert "ticket 08" in markdown.lower()


def test_the_command_runs_and_reports_where_it_wrote(tmp_path, capsys):
    exit_code = main(["--out", str(tmp_path), "--cutoff", "0.5"])
    captured = capsys.readouterr().out

    assert exit_code == 0
    assert "Wrote" in captured
    assert (tmp_path / "report.md").exists()
    assert (tmp_path / "pyes.jsonl").exists()


def test_running_the_command_twice_reports_zero_jev_calls(tmp_path, capsys):
    # The ticket's "a second run makes zero client calls", asked of the command itself rather
    # than of run().
    assert main(["--out", str(tmp_path)]) == 0
    assert "0 Jev calls" not in capsys.readouterr().out

    assert main(["--out", str(tmp_path)]) == 0
    assert "0 Jev calls" in capsys.readouterr().out
