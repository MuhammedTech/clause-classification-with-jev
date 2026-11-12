"""Seam B, the Splitter: the Clauses must partition the document.

The partition guarantee, the marker basics and the heading rule. Parent Lines on real excerpts and
the word ceiling are in `test_splitter_excerpts.py`, and the corpus-wide guarantees in
`test_partition.py`.
"""

from jev_cascade.splitter import ITEM_MARKER, split_document

OPENING_AND_ITEMS = """SOFTWARE LICENCE AGREEMENT

This Agreement is made between Acme and Beta.

1. Grant of Licence
Licensor grants Licensee a licence to use the Software.

2. Limitation of Liability
In no event shall Licensor's liability exceed the fees paid.
"""


def test_the_clauses_reproduce_the_document_exactly():
    clauses = split_document("D", OPENING_AND_ITEMS)
    assert "".join(c.text for c in clauses) == OPENING_AND_ITEMS


def test_every_character_lands_in_exactly_one_clause():
    clauses = split_document("D", OPENING_AND_ITEMS)
    assert clauses[0].start == 0
    assert clauses[-1].end == len(OPENING_AND_ITEMS)
    for earlier, later in zip(clauses, clauses[1:]):
        assert earlier.end == later.start


def test_each_clause_span_matches_its_text():
    clauses = split_document("D", OPENING_AND_ITEMS)
    for clause in clauses:
        assert OPENING_AND_ITEMS[clause.start : clause.end] == clause.text


def test_opening_text_before_the_first_marker_becomes_its_own_clause():
    clauses = split_document("D", OPENING_AND_ITEMS)
    assert clauses[0].start == 0
    assert "SOFTWARE LICENCE AGREEMENT" in clauses[0].text
    assert "Grant of Licence" not in clauses[0].text


def test_each_numbered_item_starts_a_clause():
    clauses = split_document("D", OPENING_AND_ITEMS)
    starts = [c.text.lstrip()[:2] for c in clauses[1:]]
    assert starts == ["1.", "2."]


def test_trailing_text_with_no_marker_joins_the_item_above():
    text = "1. Term\nThis Agreement runs for five years.\nSigned by both parties.\n"
    clauses = split_document("D", text)
    assert len(clauses) == 1
    assert "Signed by both parties." in clauses[0].text


def test_a_lettered_list_takes_the_line_above_as_its_parent_line():
    text = "2. Licensee commits to:\n(a) pay the fees.\n(b) report quarterly.\n"
    clauses = split_document("D", text)
    lettered = [c for c in clauses if c.text.lstrip().startswith(("(a)", "(b)"))]
    assert len(lettered) == 2
    assert lettered[0].parent_line == "2. Licensee commits to:"


def test_a_sibling_item_is_not_a_parent_line():
    # A Parent Line is the line a Clause sits under, one level only (GLOSSARY, ADR-0004), so a
    # sibling is never one. `(b)` sits under the numbered item, not under `(a)`.
    text = "2. Licensee commits to:\n(a) pay the fees.\n(b) report quarterly.\n"
    clauses = split_document("D", text)
    second = [c for c in clauses if c.text.lstrip().startswith("(b)")][0]
    assert second.parent_line == "2. Licensee commits to:"


def test_dotted_subsection_numbering_is_a_marker():
    # "1. Fees" is a heading, so its words join 1.1 beneath it and the two subsections stay
    # separate Clauses. Ticket 01 asserted three Clauses here, before the heading rule existed.
    text = "1. Fees\n1.1 Licensee shall pay.\n1.2 Interest accrues.\n"
    clauses = split_document("D", text)
    assert len(clauses) == 2
    assert clauses[0].text == "1. Fees\n1.1 Licensee shall pay.\n"
    assert clauses[1].text == "1.2 Interest accrues.\n"
    assert "".join(c.text for c in clauses) == text


def test_a_document_with_no_markers_is_one_clause():
    text = "This letter confirms our understanding.\nNothing further is agreed.\n"
    clauses = split_document("D", text)
    assert len(clauses) == 1
    assert clauses[0].text == text


def test_an_empty_document_yields_no_clauses():
    assert split_document("D", "") == ()


def test_clauses_are_numbered_in_reading_order():
    clauses = split_document("D", OPENING_AND_ITEMS)
    assert [c.index for c in clauses] == list(range(len(clauses)))


def test_roman_and_letter_markers_are_recognised():
    for marker in ["1.", "1.1", "1.1.1", "(a)", "(iv)", "(A)"]:
        assert ITEM_MARKER.match(f"{marker} text"), marker


def test_a_bare_sentence_is_not_a_marker():
    for line in ["Licensee shall pay.", "In no event shall liability exceed", "(the Software)"]:
        assert not ITEM_MARKER.match(line), line


def test_a_bare_integer_at_a_line_start_is_not_a_marker():
    # A page number, a year or a table quantity sits at a line start without a dot. Cutting there
    # invents a Clause boundary inside a real one. 170 of these fire across the corpus; requiring
    # the dot drops them (docs/cuad-ground-truth.md).
    text = "1. Fees\nLicensee shall pay the sums below.\n12\nThe table above is indicative.\n"
    clauses = split_document("D", text)
    assert len(clauses) == 1
    assert "".join(c.text for c in clauses) == text


HEADING_AND_SUBITEMS = """1. Definitions.
(a) "Software" means the licensed program.
(b) "Term" means the period of this Agreement.
"""


def test_a_headings_words_belong_to_the_first_clause_beneath_it():
    # A Clause holding only "1. Definitions." carries the section's keywords and no provision, so
    # Jev would escalate it and be wrong by construction (ADR-0004).
    clauses = split_document("D", HEADING_AND_SUBITEMS)
    assert len(clauses) == 2
    assert clauses[0].text.startswith("1. Definitions.")
    assert '(a) "Software"' in clauses[0].text
    assert "".join(c.text for c in clauses) == HEADING_AND_SUBITEMS


def test_a_short_item_followed_by_a_sibling_is_not_a_heading():
    # A one-line definition reads like a heading but is a Clause in its own right. Across the
    # corpus 145 short labelled items are followed by a sibling and 137 by a deeper marker; only
    # the second kind is a heading.
    text = '1.49 "Field" means the treatment of HIV.\n1.50 "Net Sales" means gross amounts.\n'
    clauses = split_document("D", text)
    assert len(clauses) == 2
    assert clauses[0].text.startswith('1.49 "Field"')


def test_a_lead_in_is_not_a_heading():
    # "Licensee commits to:" is a Parent Line, and ADR-0004 grades a lead-in-only Highlight on the
    # lead-in Clause alone, so the lead-in must keep a Clause of its own.
    text = "2. Licensee commits to:\n(a) pay the fees.\n(b) report quarterly.\n"
    clauses = split_document("D", text)
    assert len(clauses) == 3
    assert clauses[0].text.strip() == "2. Licensee commits to:"
