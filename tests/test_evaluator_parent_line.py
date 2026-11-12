"""Seam A, the Evaluator: a Parent Line is context for Jev and never part of grading (ticket 03).

Jev is shown Parent Line plus Clause text, but a Clause holds a Highlight only when the Highlight
overlaps the Clause's **own span** (ADR-0004). So a Highlight lying only in the Parent Line must not
make the sub-item beneath it hold anything.

The hand-made document, with the figures worked out by hand:

    C0 [0,20)   "liability is capped:"   the parent Clause, 3 words
    C1 [20,40)  "(a) pay the fees"       its sub-item, 4 words, Parent Line "liability is capped:"

One Highlight, [5,15), lies inside C0 only. C1 repeats that text in its Parent Line and nowhere else.
"""

from jev_cascade.domain import Clause, Highlight, holds
from jev_cascade.evaluator import evaluate_rule

PARENT_CLAUSE = Clause("D", 0, 0, 20, "liability is capped:")
SUB_ITEM = Clause("D", 1, 20, 40, "(a) pay the fees", parent_line="liability is capped:")
CLAUSES = [PARENT_CLAUSE, SUB_ITEM]
HIGHLIGHT = Highlight("D", "R1", 5, 15)


def test_a_highlight_lying_only_in_the_parent_line_is_not_held_by_the_sub_item():
    assert holds(PARENT_CLAUSE, HIGHLIGHT)
    assert not holds(SUB_ITEM, HIGHLIGHT)


def test_only_the_parent_clause_counts_as_holding_the_highlight():
    # C0 holds it, C1 does not: 1 holding Clause out of 2, whatever C1's Parent Line says.
    p_yes = {("D", "0-20"): 0.9, ("D", "20-40"): 0.9}
    m = evaluate_rule("R1", CLAUSES, [HIGHLIGHT], p_yes, cutoff=0.5)
    assert m.holding_clauses == 1
    assert m.holding_escalated == 1


def test_the_highlight_is_lost_when_the_parent_clause_is_binned_though_the_sub_item_was_escalated():
    # Jev saw the Highlight in C1's Parent Line and answered 0.9, but the Highlight belongs to C0,
    # which scored 0.1 and was Binned. Every holding Clause (just C0) is Binned, so it is Lost. If
    # the Parent Line counted toward grading, C1's 0.9 would have rescued it.
    p_yes = {("D", "0-20"): 0.1, ("D", "20-40"): 0.9}
    m = evaluate_rule("R1", CLAUSES, [HIGHLIGHT], p_yes, cutoff=0.5)
    assert m.lost_provisions == 1
    assert m.provision_recall == 0.0
    assert m.holding_escalated == 0
    # C1 is still Escalated: 1 Escalated of 2, so Precision is 0 of 1.
    assert m.escalated_clauses == 1
    assert m.precision == 0.0
