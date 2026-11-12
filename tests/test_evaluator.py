"""Seam A, the Evaluator: tiny hand-made documents with chosen P(yes) values.

Every expected figure below is worked out by hand in the comments, so the assertions do not
recompute what the implementation does.
"""

import pytest

from jev_cascade.domain import Clause, Highlight
from jev_cascade.evaluator import evaluate_rule


def make_clause(index: int, start: int, end: int, text: str) -> Clause:
    return Clause(doc_id="D", index=index, start=start, end=end, text=text)


def make_highlight(start: int, end: int) -> Highlight:
    return Highlight(doc_id="D", rule_id="R1", start=start, end=end)


# A hand-made document of four Clauses holding ten words between them.
#
#   C0 [0,20)  "one two three"        3 words   P(yes) 0.10
#   C1 [20,40) "four five"            2 words   P(yes) 0.50
#   C2 [40,60) "six seven eight nine" 4 words   P(yes) 0.90
#   C3 [60,80) "ten"                  1 word    P(yes) 0.50
#
# Two R1 Highlights: H1 [25,30) lies inside C1, H2 [45,50) lies inside C2.
FOUR_CLAUSES = [
    make_clause(0, 0, 20, "one two three"),
    make_clause(1, 20, 40, "four five"),
    make_clause(2, 40, 60, "six seven eight nine"),
    make_clause(3, 60, 80, "ten"),
]
TWO_HIGHLIGHTS = [make_highlight(25, 30), make_highlight(45, 50)]
FOUR_PYES = {
    ("D", "0-20"): 0.10,
    ("D", "20-40"): 0.50,
    ("D", "40-60"): 0.90,
    ("D", "60-80"): 0.50,
}


def evaluate_four(cutoff: float):
    return evaluate_rule("R1", FOUR_CLAUSES, TWO_HIGHLIGHTS, FOUR_PYES, cutoff)


def test_a_pair_at_the_cutoff_is_binned_not_escalated():
    # C1 and C3 both score exactly 0.50. Binned means "at or below", so only C2 (0.90) is
    # Escalated: 1 Escalated, 3 Binned.
    m = evaluate_four(0.50)
    assert m.escalated_clauses == 1
    assert m.binned_clauses == 3


def test_clause_recall_is_the_share_of_holding_clauses_escalated():
    # C1 and C2 hold a Highlight. Of those, only C2 is Escalated. 1/2.
    m = evaluate_four(0.50)
    assert m.holding_clauses == 2
    assert m.holding_escalated == 1
    assert m.clause_recall == pytest.approx(0.5)


def test_precision_counts_escalated_clauses_not_highlights():
    # One Clause is Escalated (C2) and it holds a Highlight, so Precision is 1/1 = 1.0 even
    # though only one of the two Highlights survived.
    m = evaluate_four(0.50)
    assert m.escalated_clauses == 1
    assert m.holding_escalated == 1
    assert m.precision == pytest.approx(1.0)


def test_a_highlight_whose_only_holding_clause_is_binned_is_a_lost_provision():
    # H1 is held only by C1, which is Binned at 0.50. H2's C2 is Escalated.
    m = evaluate_four(0.50)
    assert m.highlights == 2
    assert m.lost_provisions == 1
    assert m.provision_recall == pytest.approx(0.5)


def test_binned_share_counts_words_not_clauses():
    # Binned Clauses C0+C1+C3 hold 3+2+1 = 6 of the document's 10 words, so the Binned Share is
    # 0.60 even though 3 of 4 Clauses (0.75) were Binned.
    m = evaluate_four(0.50)
    assert m.total_words == 10
    assert m.binned_words == 6
    assert m.binned_share == pytest.approx(0.6)
    assert m.binned_share != pytest.approx(0.75)


def test_escalating_everything_loses_no_provision():
    # A Cutoff below every score Bins nothing.
    m = evaluate_four(0.0)
    assert m.escalated_clauses == 4
    assert m.lost_provisions == 0
    assert m.clause_recall == pytest.approx(1.0)
    assert m.binned_share == pytest.approx(0.0)
    # Of 4 Escalated Clauses, 2 hold a Highlight.
    assert m.precision == pytest.approx(0.5)


def test_binning_everything_loses_every_provision():
    m = evaluate_four(1.0)
    assert m.binned_clauses == 4
    assert m.lost_provisions == 2
    assert m.clause_recall == pytest.approx(0.0)
    assert m.binned_share == pytest.approx(1.0)
    # Precision is undefined with nothing Escalated, and must read as n/a rather than crash.
    assert m.precision is None


# A Highlight spanning three Clauses.
#
#   C0 [0,10) "a" P(yes) 0.10, C1 [10,20) "b" P(yes) 0.10, C2 [20,30) "c" P(yes) 0.90
#   H [5,25) overlaps all three.
THREE_CLAUSES = [
    make_clause(0, 0, 10, "a"),
    make_clause(1, 10, 20, "b"),
    make_clause(2, 20, 30, "c"),
]
SPANNING_HIGHLIGHT = [make_highlight(5, 25)]
THREE_PYES = {("D", "0-10"): 0.10, ("D", "10-20"): 0.10, ("D", "20-30"): 0.90}


def test_a_highlight_across_three_clauses_is_not_lost_when_one_is_escalated():
    m = evaluate_rule("R1", THREE_CLAUSES, SPANNING_HIGHLIGHT, THREE_PYES, 0.50)
    assert m.holding_clauses == 3
    assert m.holding_escalated == 1
    assert m.lost_provisions == 0


def test_provision_recall_exceeds_clause_recall_on_a_spanning_highlight():
    # Clause Recall is 1 of 3 holding Clauses; Provision Recall is the whole Highlight, 1 of 1.
    m = evaluate_rule("R1", THREE_CLAUSES, SPANNING_HIGHLIGHT, THREE_PYES, 0.50)
    assert m.clause_recall == pytest.approx(1 / 3)
    assert m.provision_recall == pytest.approx(1.0)
    assert m.provision_recall > m.clause_recall


def test_a_spanning_highlight_binned_everywhere_is_lost_once():
    # A Cutoff of 0.95 Bins all three holding Clauses. The Highlight is one Lost Provision, not
    # three.
    m = evaluate_rule("R1", THREE_CLAUSES, SPANNING_HIGHLIGHT, THREE_PYES, 0.95)
    assert m.holding_escalated == 0
    assert m.lost_provisions == 1
    assert m.provision_recall == pytest.approx(0.0)


def test_a_rule_with_no_highlights_reports_recall_as_undefined():
    m = evaluate_rule("R1", THREE_CLAUSES, [], THREE_PYES, 0.50)
    assert m.highlights == 0
    assert m.clause_recall is None
    assert m.provision_recall is None
    assert m.lost_provisions == 0
    # Binned Share is still defined: it does not depend on Highlights.
    assert m.binned_share == pytest.approx(2 / 3)


def test_a_highlight_held_by_no_clause_is_refused():
    # A partition makes this impossible (ADR-0004). If it ever happens the Highlight would read as
    # Lost no matter what Jev answered, so the Evaluator refuses rather than reporting a vacuous
    # loss.
    orphan = [make_highlight(100, 200)]
    with pytest.raises(ValueError, match="held by no Clause"):
        evaluate_rule("R1", THREE_CLAUSES, orphan, THREE_PYES, 0.50)


def test_a_clause_with_no_p_yes_is_refused():
    with pytest.raises(KeyError, match="no P\\(yes\\)"):
        evaluate_rule("R1", THREE_CLAUSES, SPANNING_HIGHLIGHT, {("D", "0-10"): 0.1}, 0.50)


def test_precision_and_clause_recall_share_their_numerator():
    # An Escalated Clause that holds a Highlight and a holding Clause that is Escalated are the
    # same set, so one count serves both figures.
    m = evaluate_four(0.50)
    assert m.holding_escalated == 1
    assert m.precision == pytest.approx(m.holding_escalated / m.escalated_clauses)


def test_clauses_and_highlights_are_not_pooled_across_documents():
    # Two documents whose offsets overlap: each Highlight is held only inside its own document.
    # Pooling them invented six holding relations against four real ones on the tracer run.
    a = Clause(doc_id="A", index=0, start=0, end=100, text="one two three")
    b = Clause(doc_id="B", index=0, start=0, end=100, text="four five six")
    only_in_a = [Highlight(doc_id="A", rule_id="R1", start=10, end=20)]
    pyes = {("A", "0-100"): 0.9, ("B", "0-100"): 0.9}

    m = evaluate_rule("R1", [a, b], only_in_a, pyes, 0.5)

    assert m.clauses == 2
    assert m.holding_clauses == 1
    assert m.precision == pytest.approx(0.5)
