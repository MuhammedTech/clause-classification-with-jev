"""The partition statistics ticket 03 asks the report to show, on hand-made documents.

Document A is "1. Fees / 1.1 / 1.2". The heading merges into 1.1, so it partitions into two Clauses:

    C0 [0,21)  "1. Fees\\n1.1 pay now.\\n"   5 words, no Parent Line
    C1 [21,36) "1.2 late fees.\\n"           3 words, Parent Line "1. Fees" (2 words)

Two Highlights: H1 [10,15) lies inside C0 only; H2 [18,25) crosses the boundary into C1, so it is
held by two Clauses. So 1 of 2 Highlights sits inside one Clause.

Document B has one three-word Clause and no Highlights, so its share is undefined, not zero.
"""

from jev_cascade.corpus import Document
from jev_cascade.domain import Highlight
from jev_cascade.partition import partition_facts

A_TEXT = "1. Fees\n1.1 pay now.\n1.2 late fees.\n"
B_TEXT = "Just words here.\n"


def _document(doc_id, text, highlights=()):
    return Document(
        doc_id=doc_id,
        document_name=doc_id,
        filename=doc_id,
        text=text,
        highlights=tuple(highlights),
        certified_negative_rules=frozenset(),
    )


def _facts():
    a = _document(
        "A",
        A_TEXT,
        [Highlight("A", "R1", 10, 15), Highlight("A", "R1", 18, 25)],
    )
    b = _document("B", B_TEXT)
    return partition_facts([a, b])


def test_it_counts_clauses_words_and_the_ones_over_the_ceiling():
    facts = _facts()
    assert facts.clauses == 3
    assert facts.words == 11  # 5 + 3 + 3
    assert facts.over_ceiling == 0
    assert facts.largest_clause_words == 5


def test_a_lower_ceiling_gives_more_clauses_and_still_none_over_it():
    # C0 is 5 words, so a ceiling of 4 forces a split: the count rises above 2 and the splitter,
    # not the report, is what keeps `over_ceiling` at zero.
    a = _document("A", A_TEXT)
    facts = partition_facts([a], word_ceiling=4)
    assert facts.clauses > 2
    assert facts.over_ceiling == 0
    assert facts.word_ceiling == 4


def test_it_reports_the_share_of_highlights_inside_one_clause():
    facts = _facts()
    assert facts.highlights == 2
    assert facts.single_clause_highlights == 1
    assert facts.single_clause_share == 0.5


def test_it_reports_the_share_per_document_so_a_bad_split_shows():
    by_id = {d.doc_id: d for d in _facts().documents}
    assert by_id["A"].clauses == 2
    assert by_id["A"].highlights == 2
    assert by_id["A"].single_clause_highlights == 1
    assert by_id["A"].single_clause_share == 0.5
    # No Highlights, so there is nothing to take a share of.
    assert by_id["B"].highlights == 0
    assert by_id["B"].single_clause_share is None


def test_it_measures_the_context_the_parent_lines_add_in_words():
    facts = _facts()
    assert facts.clauses_with_parent_line == 1
    assert facts.parent_line_words == 2  # "1. Fees"
    assert facts.largest_parent_line_words == 2
    # 2 words of Parent Line on top of 11 words of Clause text.
    assert facts.parent_line_growth == 2 / 11


def test_the_word_distribution_is_nearest_rank():
    facts = _facts()
    # Clause word counts sorted: 3, 3, 5.
    assert facts.median_clause_words == 3
    assert facts.mean_clause_words == 11 / 3
    assert facts.p90_clause_words == 5


def test_an_empty_corpus_has_no_shares():
    facts = partition_facts([])
    assert facts.clauses == 0
    assert facts.single_clause_share is None
    assert facts.parent_line_growth is None
