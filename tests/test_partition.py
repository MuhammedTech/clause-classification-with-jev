"""Seam B across the whole corpus: the Splitter's guarantees on all 53 real documents.

Three guarantees are asserted here (ticket 03):

- the Clauses of every document partition it, with no gap and no overlap;
- no Clause exceeds the word ceiling;
- no Highlight, for any Rule in the Rulebook, is held by zero Clauses.

The share of Highlights inside one Clause (about 97% of 378) is **reported, not asserted**: ADR-0004
says it is what the data naturally gives and not a build gate, since gating on it would pressure the
Splitter to stop separating sub-items.
"""

import pytest

from jev_cascade import config
from jev_cascade.corpus import load_corpus
from jev_cascade.domain import holds
from jev_cascade.splitter import WORD_CEILING, split_document

pytestmark = pytest.mark.skipif(
    not config.cuad_is_available(),
    reason=f"CUAD v1 not present at {config.cuad_dir()}; the dataset is not in this repo",
)


@pytest.fixture(scope="module")
def partitioned():
    """Every document of the License Agreement Set, split once, with all six Rules' Highlights."""
    documents = load_corpus()
    return [(document, split_document(document.doc_id, document.text)) for document in documents]


def test_the_corpus_is_the_53_documents(partitioned):
    assert len(partitioned) == 53


def test_the_clauses_of_every_document_reproduce_it_exactly(partitioned):
    for document, clauses in partitioned:
        assert "".join(c.text for c in clauses) == document.text, document.doc_id


def test_the_clauses_of_every_document_meet_end_to_end_with_no_gap_or_overlap(partitioned):
    for document, clauses in partitioned:
        assert clauses[0].start == 0, document.doc_id
        assert clauses[-1].end == len(document.text), document.doc_id
        for earlier, later in zip(clauses, clauses[1:]):
            assert earlier.end == later.start, (document.doc_id, earlier.end, later.start)


def test_every_clause_span_matches_its_text(partitioned):
    for document, clauses in partitioned:
        for clause in clauses:
            assert document.text[clause.start : clause.end] == clause.text


def test_no_clause_exceeds_the_word_ceiling_in_any_document(partitioned):
    for document, clauses in partitioned:
        worst = max(c.word_count for c in clauses)
        assert worst <= WORD_CEILING, (document.doc_id, worst)


def test_no_clause_is_blank_in_any_document_except_possibly_the_opening(partitioned):
    for document, clauses in partitioned:
        blank = [c for c in clauses[1:] if not c.text.strip()]
        assert not blank, (document.doc_id, [(c.start, c.end) for c in blank[:3]])


def test_no_highlight_is_held_by_zero_clauses_for_any_rule(partitioned):
    # "Lost when every holding Clause was Binned" is vacuously true of an empty set, so a Highlight
    # in no Clause would read as lost whatever Jev answered. The partition makes that impossible.
    checked = 0
    for document, clauses in partitioned:
        for highlight in document.highlights:
            holders = [c for c in clauses if holds(c, highlight)]
            assert holders, (document.doc_id, highlight.rule_id, highlight.start, highlight.end)
            checked += 1
    assert checked == 378  # 429 over seven Rules, less R6's 51 (ADR-0008)


def test_clauses_are_numbered_in_reading_order_in_every_document(partitioned):
    for document, clauses in partitioned:
        assert [c.index for c in clauses] == list(range(len(clauses))), document.doc_id
