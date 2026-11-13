"""Seam A, the Evaluator: separation, how well P(yes) ranks held Clauses above not-held ones.

Worked by hand. Four Clauses in one document, one Highlight, chosen P(yes) values.
"""

import pytest

from jev_cascade.domain import Clause, Highlight
from jev_cascade.evaluator import separation


def clause(index: int, start: int, end: int, doc_id: str = "D") -> Clause:
    return Clause(doc_id=doc_id, index=index, start=start, end=end, text="x")


def highlight(start: int, end: int, doc_id: str = "D") -> Highlight:
    return Highlight(doc_id=doc_id, rule_id="R1", start=start, end=end)


CLAUSES = [clause(0, 0, 10), clause(1, 10, 20), clause(2, 20, 30), clause(3, 30, 40)]


def table(*values: float) -> dict:
    return {c.key: v for c, v in zip(CLAUSES, values)}


def test_perfect_ranking_is_one():
    # C1 is held, 0.9; the three not-held score 0.1, 0.2, 0.3. Held beats all 3 pairs.
    result = separation(CLAUSES, [highlight(12, 15)], table(0.1, 0.9, 0.2, 0.3))
    assert (result.held, result.not_held) == (1, 3)
    assert result.value == 1.0


def test_inverted_ranking_is_zero():
    result = separation(CLAUSES, [highlight(12, 15)], table(0.5, 0.1, 0.6, 0.7))
    assert result.value == 0.0


def test_ties_count_half():
    # Two held (C1 0.5, C2 0.9), two not held (C0 0.5, C3 0.1).
    # Pairs (held, not held): 0.5v0.5 tie, 0.5v0.1 win, 0.9v0.5 win, 0.9v0.1 win.
    # (0.5 + 1 + 1 + 1) / 4 = 0.875
    result = separation(CLAUSES, [highlight(12, 15), highlight(22, 25)], table(0.5, 0.5, 0.9, 0.1))
    assert (result.held, result.not_held) == (2, 2)
    assert result.value == pytest.approx(0.875)


def test_all_equal_is_one_half():
    result = separation(CLAUSES, [highlight(12, 15)], table(0.99, 0.99, 0.99, 0.99))
    assert result.value == 0.5


def test_a_clause_is_held_by_one_overlapping_character_only_within_its_document():
    # The Highlight is in another document, so no Clause here is held.
    assert separation(CLAUSES, [highlight(12, 15, doc_id="OTHER")], table(0.1, 0.9, 0.2, 0.3)) is None


def test_none_when_nothing_is_not_held():
    assert separation(CLAUSES, [highlight(0, 40)], table(0.1, 0.9, 0.2, 0.3)) is None
