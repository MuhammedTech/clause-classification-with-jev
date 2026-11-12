"""Seam B, the Splitter: the Clauses must partition the document.

Ticket 01 only needs line-start markers. The word ceiling and the heading rules land in ticket 03,
so the cases here are the partition guarantee and the marker basics.
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
    assert lettered[1].parent_line == "(a) pay the fees."


def test_dotted_subsection_numbering_is_a_marker():
    text = "1. Fees\n1.1 Licensee shall pay.\n1.2 Interest accrues.\n"
    clauses = split_document("D", text)
    assert len(clauses) == 3
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
