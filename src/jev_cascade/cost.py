"""The cost model: what the expensive model would be asked, what that costs, and how long Jev takes.

Pure, like the Evaluator. No expensive model is ever called: every figure here is a token count at a
list price, and the report says so. Prices and assumptions come from `config`, each with a source
and a date.

Three things are priced, all over the same Clauses:

- **Expensive model alone.** One call per Clause carrying every Rule asked in the run. This is the
  baseline the saving is measured against.
- **The cascade's expensive part.** One call per Clause Escalated for **at least one** Rule, sized to
  only the Escalated questions. A Fully Binned Clause gets no call at all. This is why the saving
  tracks the Fully Binned Clause share and not any per-Rule Binned Share.
- **Jev.** One call per Clause carrying every Rule's question, input tokens only, whatever the
  Cutoff. Tokens are counted per Pair, the cautious figure (see `jev_pair_usage`).

Net saving is the baseline minus the cascade's expensive part minus Jev's cost, and it can be
negative: a Cutoff that Bins little saves little and still pays Jev for every Pair.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Mapping, Sequence

from . import config
from .domain import Clause
from .evaluator import ClauseKey
from .runner import RunStats

TokenCounter = Callable[[str], int]

TOKENS_PER_MILLION = 1_000_000
CLAUSES_PER_THOUSAND = 1000


def estimate_tokens(text: str) -> int:
    """Tokens in `text`, estimated from its length at `config.CHARS_PER_TOKEN`.

    There is no tokenizer in the code and the report must rebuild with no network, so this is a
    heuristic and every figure built on it is an estimate. Rounded up, so a non-empty text is never
    free.
    """
    if not text:
        return 0
    return math.ceil(len(text) / config.CHARS_PER_TOKEN.value)


@dataclass(frozen=True)
class CallTotals:
    """How many calls one party makes and the tokens they carry."""

    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass(frozen=True)
class TokenUsage:
    """The calls and tokens of each of the three things priced, over one set of Clauses."""

    clauses: int
    rules: int
    #: Clauses Binned for every Rule asked: the expensive model is never called on them.
    fully_binned_clauses: int
    alone: CallTotals
    cascade: CallTotals
    jev: CallTotals


def _check_inputs(
    clauses: Sequence[Clause],
    p_yes_by_rule: Mapping[str, Mapping[ClauseKey, float]],
    questions: Mapping[str, str],
) -> None:
    for rule_id, table in p_yes_by_rule.items():
        if rule_id not in questions:
            raise KeyError(f"Rule {rule_id} has no Detection Question to count")
        for clause in clauses:
            if clause.key not in table:
                raise KeyError(f"Clause {clause.key} has no P(yes) for rule {rule_id}")


def jev_pair_usage(
    clauses: Sequence[Clause],
    questions: Mapping[str, str],
    count_tokens: TokenCounter = estimate_tokens,
) -> CallTotals:
    """Jev's calls: one per Clause, carrying every Rule's question (the fan-out).

    Input tokens are counted **per Pair**, the Parent Line and Clause once for each question, as if
    Jev billed the Clause again for every question it answers. Whether it does is not known until a
    run's replies report their `usage`, so this is the cautious figure: the bill can only be lower.
    Independent of any P(yes): Jev reads everything whatever the Cutoff. Input tokens only.
    """
    question_tokens = {rule_id: count_tokens(text) for rule_id, text in questions.items()}
    calls = 0
    input_tokens = 0
    for clause in clauses:
        context = count_tokens(clause.parent_line) + count_tokens(clause.text)
        calls += 1
        for tokens in question_tokens.values():
            input_tokens += context + tokens
    return CallTotals(calls=calls, input_tokens=input_tokens, output_tokens=0)


def cost_usage(
    clauses: Sequence[Clause],
    p_yes_by_rule: Mapping[str, Mapping[ClauseKey, float]],
    questions: Mapping[str, str],
    cutoff: float,
    count_tokens: TokenCounter = estimate_tokens,
    overhead_tokens: int | None = None,
    output_tokens_per_question: int | None = None,
) -> TokenUsage:
    """Count the calls and tokens of the baseline, the cascade's expensive part and Jev.

    `p_yes_by_rule` names the Rules asked; each needs a Detection Question in `questions`. A Pair
    whose P(yes) is above `cutoff` is Escalated, as in the Evaluator. Every expensive call carries
    `overhead_tokens` of fixed instruction, and the model writes `output_tokens_per_question` back
    for each question it is asked.
    """
    if overhead_tokens is None:
        overhead_tokens = int(config.EXPENSIVE_OVERHEAD_TOKENS.value)
    if output_tokens_per_question is None:
        output_tokens_per_question = int(config.EXPENSIVE_OUTPUT_TOKENS_PER_QUESTION.value)
    _check_inputs(clauses, p_yes_by_rule, questions)

    rule_ids = list(p_yes_by_rule)
    question_tokens = {rule_id: count_tokens(questions[rule_id]) for rule_id in rule_ids}
    all_questions_tokens = sum(question_tokens.values())

    alone_calls = alone_in = alone_out = 0
    cascade_calls = cascade_in = cascade_out = 0
    fully_binned = 0
    for clause in clauses:
        context = count_tokens(clause.parent_line) + count_tokens(clause.text)

        alone_calls += 1
        alone_in += overhead_tokens + context + all_questions_tokens
        alone_out += len(rule_ids) * output_tokens_per_question

        escalated = [r for r in rule_ids if p_yes_by_rule[r][clause.key] > cutoff]
        if not escalated:
            fully_binned += 1
            continue
        cascade_calls += 1
        cascade_in += overhead_tokens + context + sum(question_tokens[r] for r in escalated)
        cascade_out += len(escalated) * output_tokens_per_question

    return TokenUsage(
        clauses=len(clauses),
        rules=len(rule_ids),
        fully_binned_clauses=fully_binned,
        alone=CallTotals(alone_calls, alone_in, alone_out),
        cascade=CallTotals(cascade_calls, cascade_in, cascade_out),
        jev=jev_pair_usage(clauses, {r: questions[r] for r in rule_ids}, count_tokens),
    )


@dataclass(frozen=True)
class CostFigures:
    """The dollars for one expensive model, in batch or not, over `clauses` Clauses."""

    clauses: int
    alone_usd: float
    cascade_usd: float
    jev_usd: float

    @property
    def net_usd(self) -> float:
        """What the cascade saves: the baseline less the cascade's expensive part and Jev."""
        return self.alone_usd - self.cascade_usd - self.jev_usd

    def per_1000(self, usd: float) -> float | None:
        """A figure scaled to 1,000 Clauses, or `None` when no Clauses were priced."""
        if not self.clauses:
            return None
        return usd * CLAUSES_PER_THOUSAND / self.clauses


def _dollars(tokens: int, usd_per_million: float) -> float:
    return tokens * usd_per_million / TOKENS_PER_MILLION


def _expensive_usd(totals: CallTotals, model: config.ExpensiveModel, factor: float) -> float:
    dollars = _dollars(totals.input_tokens, model.input.value) + _dollars(
        totals.output_tokens, model.output.value
    )
    return dollars * factor


def price_usage(
    usage: TokenUsage,
    model: config.ExpensiveModel,
    batch: bool,
    jev_input_per_mtok: float,
    batch_discount: float,
) -> CostFigures:
    """Turn tokens into dollars for one expensive model.

    Batch scales the expensive model's two lines by `batch_discount`. Jev is not batched, so its
    cost is the same in both.
    """
    factor = batch_discount if batch else 1.0
    return CostFigures(
        clauses=usage.clauses,
        alone_usd=_expensive_usd(usage.alone, model, factor),
        cascade_usd=_expensive_usd(usage.cascade, model, factor),
        jev_usd=_dollars(usage.jev.input_tokens, jev_input_per_mtok),
    )


@dataclass(frozen=True)
class JevTime:
    """How long Jev takes per 1,000 Clauses, measured and at the published rate limit."""

    calls_per_1000_clauses: int
    #: From the runner's wall clock over the calls it made. `None` when it made none (a run
    #: answered wholly from the cache), since the clock then timed a file read and not Jev.
    seconds_per_1000_clauses: float | None
    minutes_per_1000_clauses_at_rate_limit: float


def jev_time(stats: RunStats, rate_limit_per_minute: float) -> JevTime:
    """Scale the runner's timing to 1,000 Clauses.

    Seconds a call, times 1,000: a call is one Clause with every Rule's question in it, so 1,000
    Clauses are 1,000 calls however many Rules are asked. When the cache carries timestamps the
    seconds come from them (first to last answer, pauses left out), so a report rebuilt from the
    cache shows the real run's timing. A cache with none falls back to the runner's own clock over
    the calls it made, which also covers the cache write after each call; that is `None` when it
    made none, since the clock then timed a file read and not Jev.
    """
    calls = CLAUSES_PER_THOUSAND
    seconds = None
    timing = stats.timing
    if timing is not None and timing.answers > 1:
        # The original run's own clock, read back from the cache's timestamps, so a rebuild reports
        # the run's timing and not the file read's. N answers span N-1 gaps, and pauses between
        # sessions are already left out.
        seconds = timing.active_seconds / (timing.answers - 1) * calls
    elif stats.calls_made:
        seconds = stats.seconds / stats.calls_made * calls
    return JevTime(
        calls_per_1000_clauses=calls,
        seconds_per_1000_clauses=seconds,
        minutes_per_1000_clauses_at_rate_limit=calls / rate_limit_per_minute,
    )


@dataclass(frozen=True)
class FullRunEstimate:
    """What asking Jev every Pair of the whole corpus costs and takes. No expensive model, no P(yes)."""

    clauses: int
    rules: int
    calls: int
    jev_input_tokens: int
    jev_usd: float
    minutes_at_rate_limit: float


def full_run_estimate(
    clauses: Sequence[Clause],
    questions: Mapping[str, str],
    count_tokens: TokenCounter = estimate_tokens,
    jev_input_per_mtok: float | None = None,
    rate_limit_per_minute: float | None = None,
) -> FullRunEstimate:
    """The size of the whole run: every Clause against every Rule, Jev only, one call a Clause.

    Replaces the spec's "roughly $0.20", which predates the Parent Lines and was never recomputed.
    """
    if jev_input_per_mtok is None:
        jev_input_per_mtok = config.JEV_INPUT_PRICE.value
    if rate_limit_per_minute is None:
        rate_limit_per_minute = config.JEV_RATE_LIMIT_PER_MINUTE.value
    totals = jev_pair_usage(clauses, questions, count_tokens)
    return FullRunEstimate(
        clauses=len(clauses),
        rules=len(questions),
        calls=totals.calls,
        jev_input_tokens=totals.input_tokens,
        jev_usd=_dollars(totals.input_tokens, jev_input_per_mtok),
        minutes_at_rate_limit=totals.calls / rate_limit_per_minute,
    )


@dataclass(frozen=True)
class CostReport:
    """Everything the report's cost section prints, so rendering stays a pure function of it."""

    usage: TokenUsage
    #: One entry per (expensive model, batch?) in `config.EXPENSIVE_MODELS` order, non-batch first.
    figures: tuple[tuple[config.ExpensiveModel, bool, CostFigures], ...]
    time: JevTime
    full_run: FullRunEstimate


def build_cost_report(
    clauses: Sequence[Clause],
    p_yes_by_rule: Mapping[str, Mapping[ClauseKey, float]],
    questions: Mapping[str, str],
    cutoff: float,
    stats: RunStats,
    corpus_clauses: Sequence[Clause],
    all_questions: Mapping[str, str],
) -> CostReport:
    """Price this run's Clauses against every configured expensive model, and size the full run."""
    usage = cost_usage(clauses, p_yes_by_rule, questions, cutoff)
    figures = tuple(
        (
            model,
            batch,
            price_usage(
                usage,
                model,
                batch,
                jev_input_per_mtok=config.JEV_INPUT_PRICE.value,
                batch_discount=config.BATCH_DISCOUNT.value,
            ),
        )
        for model in config.EXPENSIVE_MODELS
        for batch in (False, True)
    )
    return CostReport(
        usage=usage,
        figures=figures,
        time=jev_time(stats, config.JEV_RATE_LIMIT_PER_MINUTE.value),
        full_run=full_run_estimate(corpus_clauses, all_questions),
    )
