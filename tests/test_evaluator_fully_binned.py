"""Seam A, the Evaluator: the Fully Binned Clause share, the only figure that becomes money.

Three Clauses, two Rules, Cutoff 0.50:

    clause   words   R1 P(yes)   R2 P(yes)
    C0       6       0.10        0.20      Binned for both      -> Fully Binned
    C1       3       0.10        0.90      Binned for R1 only   -> not Fully Binned
    C2       1       0.90        0.10      Binned for R2 only   -> not Fully Binned
"""

import pytest

from jev_cascade.domain import Clause
from jev_cascade.evaluator import fully_binned

CLAUSES = [
    Clause(doc_id="D", index=0, start=0, end=10, text="one two three four five six"),
    Clause(doc_id="D", index=1, start=10, end=20, text="seven eight nine"),
    Clause(doc_id="D", index=2, start=20, end=30, text="ten"),
]
P_YES = {
    "R1": {("D", "0-10"): 0.10, ("D", "10-20"): 0.10, ("D", "20-30"): 0.90},
    "R2": {("D", "0-10"): 0.20, ("D", "10-20"): 0.90, ("D", "20-30"): 0.10},
}


def test_a_fully_binned_clause_needs_every_rule_binned():
    result = fully_binned(CLAUSES, P_YES, 0.50)
    # Each Rule Bins two of three Clauses, but only C0 is Binned by both.
    assert result.clauses == 3
    assert result.fully_binned_clauses == 1
    assert result.clause_share == pytest.approx(1 / 3)


def test_fully_binned_share_is_also_counted_in_words():
    result = fully_binned(CLAUSES, P_YES, 0.50)
    # C0's 6 of the document's 10 words, not 1 of 3 Clauses.
    assert result.total_words == 10
    assert result.fully_binned_words == 6
    assert result.word_share == pytest.approx(0.6)


def test_a_clause_at_the_cutoff_in_every_rule_is_fully_binned():
    result = fully_binned(CLAUSES, P_YES, 0.90)
    # 0.90 is "at or below": everything is Binned in both Rules.
    assert result.fully_binned_clauses == 3


def test_a_clause_missing_from_one_rules_table_is_refused():
    incomplete = {"R1": P_YES["R1"], "R2": {("D", "0-10"): 0.2}}
    with pytest.raises(KeyError, match="no P\\(yes\\)"):
        fully_binned(CLAUSES, incomplete, 0.50)


def test_with_no_clauses_the_shares_are_undefined():
    result = fully_binned([], P_YES, 0.50)
    assert result.clause_share is None
    assert result.word_share is None
