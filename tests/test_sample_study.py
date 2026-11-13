"""Ticket 08's sample study: draw a sample, ask it under each setting, compare by separation.

Seams: `draw_sample` (pure and seeded), `run_arm` (through the runner, on the stub), the two
decision rules, and `bootstrap_difference`. Hand-made Clauses and Highlights throughout.
"""

import pytest

from jev_cascade.domain import Clause, Highlight
from jev_cascade.jev import CountingJevClient, StubJevClient
from jev_cascade.rulebook import rule
from jev_cascade.sample_study import (
    Arm,
    ArmResult,
    bootstrap_difference,
    choose_heading,
    choose_type,
    draw_sample,
    run_arm,
)

R1 = rule("R1")


def make_corpus():
    """Two documents of 30 Clauses each, 10 characters a Clause.

    Document A: Clauses 0-4 are held by an R1 Highlight, all under the heading "9. Liability".
    Clauses 5-9 are under the same heading and not held (near misses). The rest sit under no heading.
    Document B: Clauses 0-1 are held, the rest not, no heading anywhere.
    """
    clauses, highlights = [], []
    for doc in ("A", "B"):
        for i in range(30):
            heading = doc == "A" and i < 10
            clauses.append(
                Clause(
                    doc,
                    i,
                    i * 10,
                    i * 10 + 10,
                    f"text {doc}{i}",
                    "9. Liability" if heading else "",
                    parent_is_heading=heading,
                )
            )
    for i in range(5):
        highlights.append(Highlight("A", "R1", i * 10 + 2, i * 10 + 5))
    for i in range(2):
        highlights.append(Highlight("B", "R1", i * 10 + 2, i * 10 + 5))
    return clauses, {"R1": highlights}


def held_keys(sample_clauses, highlights):
    from jev_cascade.domain import holds

    return {c.key for c in sample_clauses if any(holds(c, h) for h in highlights)}


def test_the_sample_is_enriched_with_held_clauses_and_capped_per_document():
    clauses, highlights = make_corpus()

    sample = draw_sample(clauses, highlights, [R1], held=4, not_held=6, per_document=3, seed=1)

    drawn = sample.by_rule["R1"]
    held = held_keys(drawn, highlights["R1"])
    assert len(held) == 4
    assert len(drawn) == 10
    # Document A has five held Clauses but the cap is three, so B must supply at least one.
    assert sum(1 for k in held if k[0] == "A") <= 3
    assert sum(1 for k in held if k[0] == "B") >= 1


def test_half_the_not_held_clauses_are_near_misses_under_a_held_clauses_heading():
    clauses, highlights = make_corpus()

    sample = draw_sample(clauses, highlights, [R1], held=4, not_held=6, per_document=4, seed=1)

    drawn = sample.by_rule["R1"]
    held = held_keys(drawn, highlights["R1"])
    not_held = [c for c in drawn if c.key not in held]
    near_misses = [c for c in not_held if c.parent_is_heading and c.parent_line == "9. Liability"]
    # Not-held Clauses 5-9 of A share the held Clauses' heading: 3 of the 6 are drawn from them.
    assert len(near_misses) == 3
    assert sample.near_misses["R1"] == 3


def test_the_same_seed_gives_the_same_sample_and_another_seed_a_different_one():
    clauses, highlights = make_corpus()
    args = dict(held=3, not_held=6, per_document=3)

    one = draw_sample(clauses, highlights, [R1], seed=1, **args).by_rule["R1"]
    again = draw_sample(clauses, highlights, [R1], seed=1, **args).by_rule["R1"]
    other = draw_sample(clauses, highlights, [R1], seed=2, **args).by_rule["R1"]

    assert one == again
    assert one != other


def test_a_rule_with_fewer_held_clauses_than_asked_gets_all_it_has():
    clauses, highlights = make_corpus()
    highlights = {"R1": highlights["R1"][:1]}  # one held Clause in the whole corpus

    sample = draw_sample(clauses, highlights, [R1], held=4, not_held=6, per_document=3, seed=1)

    assert len(held_keys(sample.by_rule["R1"], highlights["R1"])) == 1


def test_each_sampled_clause_is_asked_only_its_own_rule_and_a_rerun_asks_nothing(tmp_path):
    clauses, highlights = make_corpus()
    sample = draw_sample(clauses, highlights, [R1], held=4, not_held=6, per_document=3, seed=1)
    arm = Arm("binary", True)
    cache = tmp_path / "pyes.jsonl"

    first = CountingJevClient(StubJevClient())
    result = run_arm(arm, sample, highlights, first, cache)
    assert first.calls == 10
    assert result.by_rule["R1"].held == 4

    again = CountingJevClient(StubJevClient())
    run_arm(arm, sample, highlights, again, cache)
    assert again.calls == 0


def test_taking_the_heading_out_re_asks_only_the_clauses_that_had_one(tmp_path):
    clauses, highlights = make_corpus()
    sample = draw_sample(clauses, highlights, [R1], held=4, not_held=6, per_document=4, seed=1)
    cache = tmp_path / "pyes.jsonl"
    run_arm(Arm("binary", True), sample, highlights, StubJevClient(), cache)

    off = CountingJevClient(StubJevClient())
    run_arm(Arm("binary", False), sample, highlights, off, cache)

    with_heading = [c for c in sample.by_rule["R1"] if c.parent_is_heading]
    assert 0 < len(with_heading) < 10
    assert off.calls == len(with_heading)


def result(question_type, heading, *separations):
    from jev_cascade.evaluator import Separation

    return ArmResult(
        arm=Arm(question_type, heading),
        by_rule={f"R{i}": Separation(10, 10, v) for i, v in enumerate(separations, 1)},
        p_yes={},
    )


def test_the_type_with_the_highest_mean_separation_wins():
    results = [
        result("binary", True, 0.70, 0.80),
        result("score2", True, 0.80, 0.90),
        result("choice2", True, 0.60, 0.70),
    ]
    assert choose_type(results).question_type == "score2"


def test_a_type_that_wins_by_less_than_the_margin_loses_to_binary():
    results = [
        result("binary", True, 0.80, 0.80),
        result("score2", True, 0.81, 0.81),  # +0.01, inside the 0.02 margin
        result("choice2", True, 0.70, 0.70),
    ]
    assert choose_type(results).question_type == "binary"


def test_heading_context_is_turned_off_only_if_off_wins_by_the_margin_else_it_stays_as_was():
    on = result("binary", True, 0.80, 0.80)
    assert choose_heading(on, result("binary", False, 0.90, 0.90)) is False
    # Off is no better: keep the setting the study started from.
    assert choose_heading(on, result("binary", False, 0.80, 0.80)) is True
    assert choose_heading(on, result("binary", False, 0.70, 0.70)) is True


def test_the_bootstrap_difference_is_seeded_and_its_interval_spans_the_point_estimate(tmp_path):
    clauses, highlights = make_corpus()
    sample = draw_sample(clauses, highlights, [R1], held=4, not_held=12, per_document=4, seed=1)
    cache = tmp_path / "pyes.jsonl"
    a = run_arm(Arm("binary", True), sample, highlights, StubJevClient(seed=1), cache)
    b = run_arm(Arm("score2", True), sample, highlights, StubJevClient(seed=2), cache)

    one = bootstrap_difference(a, b, sample, highlights, draws=200, seed=3)
    two = bootstrap_difference(a, b, sample, highlights, draws=200, seed=3)

    assert one == two
    point, low, high = one
    assert low <= point <= high
    assert point == pytest.approx(b.mean_separation - a.mean_separation)
