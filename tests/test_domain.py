"""Seam A, the Holds relation: a Clause holds a Highlight on one character of overlap."""

from jev_cascade.domain import Clause, Highlight, holds


def clause(start: int, end: int, text: str = "x") -> Clause:
    return Clause(doc_id="D", index=0, start=start, end=end, text=text)


def highlight(start: int, end: int) -> Highlight:
    return Highlight(doc_id="D", rule_id="R1", start=start, end=end)


def test_one_character_of_overlap_counts_as_holding():
    # The Clause covers [0, 10); the Highlight starts on the Clause's last character.
    assert holds(clause(0, 10), highlight(9, 40)) is True


def test_a_clause_overlapping_nothing_does_not_hold_it():
    assert holds(clause(0, 10), highlight(40, 50)) is False


def test_a_clause_ending_exactly_where_the_highlight_starts_does_not_hold_it():
    # Spans are half-open, so [0, 10) and [10, 20) share no character.
    assert holds(clause(0, 10), highlight(10, 20)) is False


def test_a_highlight_ending_exactly_where_the_clause_starts_does_not_hold_it():
    assert holds(clause(10, 20), highlight(0, 10)) is False


def test_a_highlight_wholly_inside_one_clause_is_held():
    assert holds(clause(0, 100), highlight(40, 50)) is True


def test_a_clause_wholly_inside_one_highlight_is_held():
    assert holds(clause(40, 50), highlight(0, 100)) is True


def test_word_count_counts_words_of_the_clause_text():
    assert clause(0, 20, "one two  three\nfour").word_count == 4


def test_an_empty_clause_holds_nothing():
    # A zero-width Clause cannot overlap by a character.
    assert holds(clause(10, 10), highlight(0, 100)) is False


def test_a_clause_and_highlight_in_different_documents_never_hold():
    # Offsets are only comparable within one document. Pooling documents into one evaluation
    # without this check invents overlaps: on the tracer documents it produced six false holding
    # relations against four real ones.
    other_document = Highlight(doc_id="OTHER", rule_id="R1", start=0, end=100)
    assert holds(clause(0, 100), other_document) is False


def test_identical_offsets_in_different_documents_do_not_hold():
    assert holds(clause(10, 20), Highlight("OTHER", "R1", 10, 20)) is False


def test_the_clause_key_is_its_document_and_span():
    assert clause(5, 9).key == ("D", "5-9")
