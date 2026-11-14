"""ADR-0007: choose a Cutoff on one half of the documents, report it on the other.

Two documents, one Rule, four Clauses each. Clause i of a document spans [10i, 10i+10).

    doc A                                   doc B
    clause  holds   P(yes)                  clause  holds   P(yes)
    A0      yes     0.05                    B0      yes     0.40
    A1      yes     0.30                    B1      -       0.02
    A2      -       0.02                    B2      -       0.02
    A3      -       0.90                    B3      yes     0.80
"""

import pytest

from jev_cascade.domain import Clause, Highlight
from jev_cascade.operating_point import choose_cutoff, dollars, read_at, split_halves, study

QUESTIONS = {"R1": "Does this clause cap liability?"}


def _doc(doc_id, p_values, holding):
    clauses = [
        Clause(doc_id=doc_id, index=i, start=10 * i, end=10 * i + 10, text="one two three")
        for i in range(len(p_values))
    ]
    highlights = [Highlight(doc_id, "R1", 10 * i + 2, 10 * i + 5) for i in holding]
    table = {c.key: p for c, p in zip(clauses, p_values)}
    return clauses, highlights, table


A_CLAUSES, A_HIGHLIGHTS, A_P = _doc("A", [0.05, 0.30, 0.02, 0.90], holding=[0, 1])
B_CLAUSES, B_HIGHLIGHTS, B_P = _doc("B", [0.40, 0.02, 0.02, 0.80], holding=[0, 3])
CLAUSES = A_CLAUSES + B_CLAUSES
HIGHLIGHTS = A_HIGHLIGHTS + B_HIGHLIGHTS
P_YES = {"R1": {**A_P, **B_P}}


def test_the_split_is_disjoint_complete_and_the_same_every_time():
    ids = [f"doc-{n}" for n in range(60)]
    first, second = split_halves(ids)
    assert first.isdisjoint(second)
    assert first | second == set(ids)
    assert split_halves(ids) == (first, second)
    assert split_halves(reversed(ids)) == (first, second)


def test_the_split_puts_a_reasonable_share_in_each_half():
    first, second = split_halves([f"doc-{n}" for n in range(200)])
    assert 70 <= len(first) <= 130
    assert len(first) + len(second) == 200


def test_the_cutoff_is_the_highest_one_before_the_loss_budget_is_exceeded():
    # Doc A alone: 2 Provisions. Allowing 1 lost (50%): Cutoff 0.05 Bins A0, so 1 lost; 0.30 Bins
    # A1 as well, so 2 lost, over budget.
    assert choose_cutoff(A_CLAUSES, A_HIGHLIGHTS, {"R1": A_P}, 0.50) == pytest.approx(0.05)


def test_a_zero_budget_stops_at_the_last_cutoff_that_loses_nothing():
    # Below 0.05 only A2 (0.02) is Binned, and it holds nothing.
    assert choose_cutoff(A_CLAUSES, A_HIGHLIGHTS, {"R1": A_P}, 0.0) == pytest.approx(0.02)


def test_a_budget_that_allows_everything_picks_the_top_observed_score():
    assert choose_cutoff(A_CLAUSES, A_HIGHLIGHTS, {"R1": A_P}, 1.0) == pytest.approx(0.90)


def test_the_budget_rounds_down_to_whole_provisions():
    # 49% of 2 Provisions is 0.98, so no whole provision may be lost.
    assert choose_cutoff(A_CLAUSES, A_HIGHLIGHTS, {"R1": A_P}, 0.49) == pytest.approx(0.02)


def test_reading_a_cutoff_counts_skip_and_loss_and_names_the_document():
    reading = read_at(B_CLAUSES, B_HIGHLIGHTS, {"R1": B_P}, QUESTIONS, 0.05)
    # B1 and B2 are Binned (0.02); neither holds anything.
    assert reading.skipped_clauses == 2 and reading.clauses == 4
    assert reading.lost == 0 and reading.provisions == 2
    assert reading.lost_by_document == ()

    reading = read_at(B_CLAUSES, B_HIGHLIGHTS, {"R1": B_P}, QUESTIONS, 0.40)
    # B0 (0.40) is now Binned and holds a Provision, so it is lost, in document B.
    assert reading.skipped_clauses == 3
    assert reading.lost == 1
    assert reading.lost_by_document == (("B", 1),)


def test_the_choice_is_made_on_one_half_and_read_on_the_other():
    result = study(
        CLAUSES, HIGHLIGHTS, P_YES, QUESTIONS, budget_share=0.50,
        halves=({"A"}, {"B"}),
    )
    a_to_b, b_to_a = result.directions
    # A -> B: chosen on A at 0.05, then read on B at 0.05: two Clauses skipped, nothing lost.
    assert a_to_b.cutoff == pytest.approx(0.05)
    assert a_to_b.on_selection.lost == 1
    assert a_to_b.on_report.skipped_clauses == 2 and a_to_b.on_report.lost == 0
    # B -> A: B's 2 Provisions allow 1 lost, which is reached at 0.40; read on A at 0.40.
    assert b_to_a.cutoff == pytest.approx(0.40)
    assert b_to_a.on_report.skipped_clauses == 3 and b_to_a.on_report.lost == 2


def test_each_document_is_reported_on_exactly_once():
    result = study(CLAUSES, HIGHLIGHTS, P_YES, QUESTIONS, 0.50, halves=({"A"}, {"B"}))
    assert result.clauses == len(CLAUSES)
    assert result.provisions == len(HIGHLIGHTS)
    assert result.skipped_clauses == 2 + 3
    assert result.lost == 0 + 2
    assert result.lost_share == pytest.approx(2 / 4)
    assert result.lost_by_document() == (("A", 2),)


def test_dollars_sum_across_readings_and_skipping_something_saves_something():
    result = study(CLAUSES, HIGHLIGHTS, P_YES, QUESTIONS, 0.50, halves=({"A"}, {"B"}))
    from jev_cascade import config

    figures = dollars(result.readings, config.EXPENSIVE_MODELS[0])
    assert figures.clauses == len(CLAUSES)
    assert figures.alone_usd > figures.cascade_usd > 0
    assert figures.net_usd == pytest.approx(
        figures.alone_usd - figures.cascade_usd - figures.jev_usd
    )
