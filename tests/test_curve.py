"""Seam A, the Cutoff Curve and the free-saving headline, on the hand-made four-Clause document.

Hand-worked figures (see `tests/test_evaluator.py` for the document):

  C0 [0,20)  3 words  P(yes) 0.10   holds nothing
  C1 [20,40) 2 words  P(yes) 0.50   holds H1
  C2 [40,60) 4 words  P(yes) 0.90   holds H2
  C3 [60,80) 1 word   P(yes) 0.50   holds nothing

Distinct observed P(yes): 0.10, 0.50, 0.90, so the curve has three rows.
"""

from jev_cascade.domain import Clause, Highlight
from jev_cascade.evaluator import cutoff_curve, free_saving

from test_evaluator import FOUR_CLAUSES, FOUR_PYES, TWO_HIGHLIGHTS


def curve():
    return cutoff_curve("R1", FOUR_CLAUSES, TWO_HIGHLIGHTS, FOUR_PYES)


def test_the_curve_has_exactly_one_row_per_distinct_observed_p_yes():
    # Four Pairs, but C1 and C3 share 0.50: three rows, not four.
    assert [row.cutoff for row in curve()] == [0.10, 0.50, 0.90]


def test_each_row_is_the_ordinary_evaluation_at_that_cutoff():
    low, mid, high = curve()
    # At 0.10 only C0 is Binned (3 of 10 words); both highlights are still reachable.
    assert (low.binned_clauses, low.binned_words, low.lost_provisions) == (1, 3, 0)
    # At 0.50 C0, C1, C3 are Binned (6 words); C1's Highlight is Lost.
    assert (mid.binned_clauses, mid.binned_words, mid.lost_provisions) == (3, 6, 1)
    # At the highest P(yes) everything is Binned.
    assert (high.binned_clauses, high.binned_words, high.lost_provisions) == (4, 10, 2)


def test_a_curve_over_no_clauses_has_no_rows():
    assert cutoff_curve("R1", [], [], {}) == ()


def test_the_free_saving_is_what_can_be_binned_strictly_below_the_lowest_held_p_yes():
    # The lowest P(yes) of a holding Clause is C1's 0.50. Strictly below it only C0 (3 words) is
    # Binned: 3/10 words, 1 Clause, and no Highlight is lost by construction.
    saving = free_saving("R1", FOUR_CLAUSES, TWO_HIGHLIGHTS, FOUR_PYES)
    assert saving.lowest_held_p_yes == 0.50
    assert saving.lowest_held_clause == ("D", "20-40")
    assert (saving.binned_clauses, saving.binned_words, saving.total_words) == (1, 3, 10)
    assert saving.binned_share == 0.3
    assert saving.lost_provisions == 0


def test_a_clause_scoring_exactly_the_lowest_held_p_yes_is_not_free():
    # C3 ties C1 at 0.50 and holds nothing, but binning at 0.50 would bin C1 too. So C3 stays
    # Escalated: it is not in the 3 words.
    saving = free_saving("R1", FOUR_CLAUSES, TWO_HIGHLIGHTS, FOUR_PYES)
    assert saving.binned_clauses == 1


def test_when_the_lowest_held_clause_is_the_lowest_of_all_nothing_is_free():
    pyes = dict(FOUR_PYES)
    pyes[("D", "20-40")] = 0.05  # C1 now scores below everything
    saving = free_saving("R1", FOUR_CLAUSES, TWO_HIGHLIGHTS, pyes)
    assert saving.lowest_held_p_yes == 0.05
    assert (saving.binned_clauses, saving.binned_words) == (0, 0)
    assert saving.binned_share == 0.0


def test_a_rule_with_no_holding_clause_has_no_free_saving():
    assert free_saving("R1", FOUR_CLAUSES, [], FOUR_PYES) is None
