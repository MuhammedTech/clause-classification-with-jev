"""Seam A, the cost model: what the expensive model would be asked, and what that costs.

Three Clauses, three Rules, Cutoff 0.50. The counter is one token per word, so every expected
figure below is added up by hand from the words, not recomputed by the code under test.

Questions: R1 "q q q" (3 words), R2 "q q q q" (4), R3 "q q q q q" (5). Overhead 10 tokens a call,
7 output tokens per question.

    clause  Parent Line  text    R1    R2    R3    Escalated for
    C0      (none)       6 words 0.90  0.90  0.10  R1, R2          -> one call, 2 questions
    C1      2 words      4 words 0.10  0.10  0.10  nothing         -> Fully Binned, no call
    C2      2 words      2 words 0.10  0.10  0.90  R3              -> one call, 1 question

Cascade expensive input: C0 10+6+(3+4)=23, C2 10+2+2+5=19, total 42; output (2+1)*7=21.
Expensive alone, every Clause with all 3 questions (12 words): C0 10+6+12=28, C1 10+2+4+12=28,
C2 10+2+2+12=26, total 82; output 3 Clauses * 3 questions * 7 = 63.
Jev, every Pair, no overhead: Parent Line + text + that question. C0 6+3, 6+4, 6+5 = 30;
C1 (2+4)=6 each, 6*3+12 = 30; C2 (2+2)=4 each, 4*3+12 = 24. Total 84.
"""

import pytest

from jev_cascade.config import ExpensiveModel, Sourced
from jev_cascade.cost import cost_usage, jev_time, price_usage
from jev_cascade.domain import Clause
from jev_cascade.runner import AnswerTiming, RunStats

CLAUSES = [
    Clause(doc_id="D", index=0, start=0, end=10, text="a b c d e f"),
    Clause(doc_id="D", index=1, start=10, end=20, text="g h i j", parent_line="x y"),
    Clause(doc_id="D", index=2, start=20, end=30, text="k l", parent_line="x y"),
]
QUESTIONS = {"R1": "q q q", "R2": "q q q q", "R3": "q q q q q"}
P_YES = {
    "R1": {("D", "0-10"): 0.9, ("D", "10-20"): 0.1, ("D", "20-30"): 0.1},
    "R2": {("D", "0-10"): 0.9, ("D", "10-20"): 0.1, ("D", "20-30"): 0.1},
    "R3": {("D", "0-10"): 0.1, ("D", "10-20"): 0.1, ("D", "20-30"): 0.9},
}


def words(text: str) -> int:
    return len(text.split())


def usage(p_yes=P_YES, cutoff=0.5):
    return cost_usage(
        CLAUSES, p_yes, QUESTIONS, cutoff,
        count_tokens=words, overhead_tokens=10, output_tokens_per_question=7,
    )


def test_one_call_per_clause_escalated_for_any_rule_and_none_for_a_fully_binned_clause():
    result = usage()
    # C0 and C2 are Escalated for something, C1 for nothing.
    assert result.fully_binned_clauses == 1
    assert result.cascade.calls == 2


def test_the_cascade_call_is_sized_to_only_the_escalated_questions():
    result = usage()
    # C0 asks R1 and R2 (3+4 words), not R3's 5; C2 asks R3 alone. The Parent Line is counted.
    assert result.cascade.input_tokens == 42


def test_output_tokens_are_counted_for_the_expensive_model():
    result = usage()
    assert result.cascade.output_tokens == 21
    assert result.alone.output_tokens == 63


def test_the_expensive_model_alone_reads_every_clause_with_every_question():
    result = usage()
    assert result.alone.calls == 3
    assert result.alone.input_tokens == 82


def test_jev_is_charged_every_pair_with_its_own_question_and_no_overhead():
    result = usage()
    assert result.jev.calls == 9
    assert result.jev.input_tokens == 84
    assert result.jev.output_tokens == 0


def test_a_cutoff_that_bins_everything_costs_the_expensive_model_nothing():
    result = usage(cutoff=0.95)
    assert result.fully_binned_clauses == 3
    assert result.cascade.calls == 0
    assert result.cascade.input_tokens == 0
    assert result.cascade.output_tokens == 0
    # Jev still read everything, and the baseline is unchanged.
    assert result.jev.calls == 9
    assert result.alone.calls == 3


def test_a_clause_missing_from_a_rules_table_is_refused():
    incomplete = {**P_YES, "R3": {("D", "0-10"): 0.1}}
    with pytest.raises(KeyError, match="no P\\(yes\\)"):
        usage(p_yes=incomplete)


def test_a_rule_without_a_question_is_refused():
    with pytest.raises(KeyError, match="R3"):
        cost_usage(
            CLAUSES, P_YES, {"R1": "q", "R2": "q"}, 0.5,
            count_tokens=words, overhead_tokens=0, output_tokens_per_question=0,
        )


def _model(input_per_mtok: float, output_per_mtok: float) -> ExpensiveModel:
    def sourced(value: float) -> Sourced:
        return Sourced(value, "USD per million tokens", "test", "2026-01-01")

    return ExpensiveModel("test model", sourced(input_per_mtok), sourced(output_per_mtok))


# $1,000 per million input tokens is $0.001 a token; $2,000 per million output is $0.002.
MODEL = _model(1000, 2000)
JEV_PER_MTOK = 500  # $0.0005 a token


def _figures(batch: bool, cutoff: float = 0.5, jev_per_mtok: float = JEV_PER_MTOK):
    return price_usage(
        usage(cutoff=cutoff), MODEL, batch=batch, jev_input_per_mtok=jev_per_mtok,
        batch_discount=0.5,
    )


def test_prices_turn_tokens_into_dollars():
    figures = _figures(batch=False)
    # alone 82*0.001 + 63*0.002 = 0.082 + 0.126
    assert figures.alone_usd == pytest.approx(0.208)
    # cascade 42*0.001 + 21*0.002 = 0.042 + 0.042
    assert figures.cascade_usd == pytest.approx(0.084)
    # Jev 84 * 0.0005
    assert figures.jev_usd == pytest.approx(0.042)
    assert figures.net_usd == pytest.approx(0.208 - 0.084 - 0.042)


def test_batch_halves_the_expensive_model_but_not_jev():
    figures = _figures(batch=True)
    assert figures.alone_usd == pytest.approx(0.104)
    assert figures.cascade_usd == pytest.approx(0.042)
    assert figures.jev_usd == pytest.approx(0.042)
    assert figures.net_usd == pytest.approx(0.104 - 0.042 - 0.042)


def test_figures_scale_to_a_thousand_clauses():
    figures = _figures(batch=False)
    # Three Clauses were priced; a thousand is 1000/3 times as many.
    assert figures.per_1000(figures.alone_usd) == pytest.approx(0.208 * 1000 / 3)


def test_savings_are_negative_when_jev_costs_more_than_it_saves():
    # Cutoff 0.0 Escalates every Clause for every Rule, so the cascade's expensive part is the
    # baseline and Jev is pure extra cost.
    figures = _figures(batch=False, cutoff=0.0)
    assert figures.net_usd < 0


def test_with_no_clauses_nothing_scales():
    empty = cost_usage([], {"R1": {}}, {"R1": "q"}, 0.5, count_tokens=words,
                       overhead_tokens=0, output_tokens_per_question=0)
    figures = price_usage(empty, MODEL, batch=False, jev_input_per_mtok=1, batch_discount=0.5)
    assert figures.per_1000(figures.alone_usd) is None


def test_jev_time_per_thousand_clauses_scales_from_seconds_per_call():
    # 6 calls in 3 seconds is half a second a call; 2 Rules means 2,000 calls per 1,000 Clauses.
    stats = RunStats(pairs=6, calls_made=6, cache_hits=0, seconds=3.0)
    timing = jev_time(stats, rules_asked=2, rate_limit_per_minute=1200)
    assert timing.seconds_per_1000_clauses == pytest.approx(1000.0)
    assert timing.calls_per_1000_clauses == 2000
    # 2,000 calls at 1,200 a minute.
    assert timing.minutes_per_1000_clauses_at_rate_limit == pytest.approx(2000 / 1200)


def test_jev_time_is_undefined_when_every_answer_came_from_the_cache():
    # A run with no calls took no Jev time, so a rate read off it would say zero.
    stats = RunStats(pairs=6, calls_made=0, cache_hits=6, seconds=0.01)
    timing = jev_time(stats, rules_asked=2, rate_limit_per_minute=1200)
    assert timing.seconds_per_1000_clauses is None
    assert timing.minutes_per_1000_clauses_at_rate_limit == pytest.approx(2000 / 1200)


def test_jev_time_of_a_rebuild_is_the_original_runs_not_the_rebuilds():
    # A rebuild made no calls and took 0.01s, but the cache says 101 answers arrived over 50 active
    # seconds: half a second a call, so 2 Rules means 1,000 seconds per 1,000 Clauses.
    original = AnswerTiming(
        answers=101, first_at=0.0, last_at=50.0, active_seconds=50.0, longest_pause_seconds=0.5
    )
    stats = RunStats(pairs=101, calls_made=0, cache_hits=101, seconds=0.01, timing=original)
    timing = jev_time(stats, rules_asked=2, rate_limit_per_minute=1200)
    assert timing.seconds_per_1000_clauses == pytest.approx(1000.0)
