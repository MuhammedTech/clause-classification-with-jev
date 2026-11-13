"""The Evaluator: given Clauses, Highlights and the P(yes) table, what one Cutoff costs and saves.

Pure, as ADR-0003 requires: no folds, no tuning, no randomness, no overlap threshold. Called once
per Rule. Every figure carries its counts, and a figure with an empty denominator is `None` so the
report can print "n/a" rather than inventing a zero.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Collection, Iterable, Mapping, Sequence

from .domain import Clause, Highlight, holds

#: A Clause's identity across the corpus: its document plus its span. See `Clause.key`.
ClauseKey = tuple[str, str]


def _share(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


@dataclass(frozen=True)
class RuleMetrics:
    """What one Cutoff does to one Rule. Shares are `None` where the denominator is empty."""

    rule_id: str
    cutoff: float

    clauses: int
    binned_clauses: int
    escalated_clauses: int

    holding_clauses: int
    holding_escalated: int

    highlights: int
    lost_provisions: int

    total_words: int
    binned_words: int

    #: Clauses holding nothing, split by whether CUAD certified their document as having no such
    #: clause. `*_escalated` is how many of each Jev did not rule out.
    certified_negative_clauses: int = 0
    certified_negative_escalated: int = 0
    inferred_negative_clauses: int = 0
    inferred_negative_escalated: int = 0

    @property
    def false_alarm_rate(self) -> float | None:
        """Of Clauses in Certified Negative documents, the share Escalated.

        Reported apart from Precision because it rests on nothing but CUAD's explicit negatives:
        no Inferred Negative is in it. `None` when no scored document is certified for the Rule.
        """
        return _share(self.certified_negative_escalated, self.certified_negative_clauses)

    @property
    def clause_recall(self) -> float | None:
        """Of Clauses holding a Highlight, the share Escalated."""
        return _share(self.holding_escalated, self.holding_clauses)

    @property
    def provision_recall(self) -> float | None:
        """Of Highlights, the share with at least one holding Clause Escalated."""
        return _share(self.highlights - self.lost_provisions, self.highlights)

    @property
    def precision(self) -> float | None:
        """Of Escalated Clauses, the share holding a Highlight.

        The numerator is `holding_escalated`: an Escalated Clause that holds a Highlight and a
        holding Clause that is Escalated are the same set.
        """
        return _share(self.holding_escalated, self.escalated_clauses)

    @property
    def binned_share(self) -> float | None:
        """The share of contract words Binned. The saving, measured in text not unit count."""
        return _share(self.binned_words, self.total_words)

    @property
    def base_rate(self) -> float | None:
        """The share of Clauses holding a Highlight.

        This is what Precision reads when every Clause is Escalated, which is why Precision reads
        in single digits at any useful Cutoff (ADR-0003).
        """
        return _share(self.holding_clauses, self.clauses)


@dataclass(frozen=True)
class _Ground:
    """What does not change with the Cutoff: who holds what, and the words each Clause carries.

    Worked out once per Rule. `cutoff_curve` evaluates one row per distinct P(yes), thousands of
    them on a real run, and re-deriving which Clause holds which Highlight for every row made a full
    run's report take longer than the run itself.
    """

    clauses: tuple[Clause, ...]
    highlights: int
    #: Per Clause, in order: "holding", "certified" (holds nothing, in a Certified Negative
    #: document) or "inferred" (holds nothing, anywhere else).
    kinds: tuple[str, ...]
    #: Per Highlight, the indexes of the Clauses that hold it. Never empty.
    holders: tuple[tuple[int, ...], ...]
    total_words: int


def _ground(
    rule_id: str,
    clauses: Sequence[Clause],
    highlights: Iterable[Highlight],
    certified_negative_docs: Collection[str],
) -> _Ground:
    clauses = tuple(clauses)
    highlights = list(highlights)

    holders: list[tuple[int, ...]] = []
    for highlight in highlights:
        held_by = tuple(i for i, c in enumerate(clauses) if holds(c, highlight))
        if not held_by:
            raise ValueError(
                f"Highlight {highlight.doc_id} [{highlight.start},{highlight.end}) for rule "
                f"{rule_id} is held by no Clause; the Clauses do not partition the document "
                f"(ADR-0004)"
            )
        holders.append(held_by)

    holding = {i for held_by in holders for i in held_by}
    kinds = tuple(
        "holding"
        if i in holding
        else "certified"
        if clause.doc_id in certified_negative_docs
        else "inferred"
        for i, clause in enumerate(clauses)
    )
    return _Ground(
        clauses=clauses,
        highlights=len(highlights),
        kinds=kinds,
        holders=tuple(holders),
        total_words=sum(c.word_count for c in clauses),
    )


def _at_cutoff(
    rule_id: str, ground: _Ground, p_yes: Mapping[ClauseKey, float], cutoff: float
) -> RuleMetrics:
    escalated: list[bool] = []
    for clause in ground.clauses:
        if clause.key not in p_yes:
            raise KeyError(f"Clause {clause.key} has no P(yes) for rule {rule_id}")
        escalated.append(p_yes[clause.key] > cutoff)

    binned_words = binned_clauses = 0
    counts = {"holding": [0, 0], "certified": [0, 0], "inferred": [0, 0]}
    for clause, kind, is_escalated in zip(ground.clauses, ground.kinds, escalated):
        counts[kind][0] += 1
        if is_escalated:
            counts[kind][1] += 1
        else:
            binned_clauses += 1
            binned_words += clause.word_count

    lost_provisions = sum(
        1 for held_by in ground.holders if not any(escalated[i] for i in held_by)
    )

    return RuleMetrics(
        rule_id=rule_id,
        cutoff=cutoff,
        clauses=len(ground.clauses),
        binned_clauses=binned_clauses,
        escalated_clauses=len(ground.clauses) - binned_clauses,
        holding_clauses=counts["holding"][0],
        holding_escalated=counts["holding"][1],
        highlights=ground.highlights,
        lost_provisions=lost_provisions,
        total_words=ground.total_words,
        binned_words=binned_words,
        certified_negative_clauses=counts["certified"][0],
        certified_negative_escalated=counts["certified"][1],
        inferred_negative_clauses=counts["inferred"][0],
        inferred_negative_escalated=counts["inferred"][1],
    )


def evaluate_rule(
    rule_id: str,
    clauses: Sequence[Clause],
    highlights: Iterable[Highlight],
    p_yes: Mapping[ClauseKey, float],
    cutoff: float,
    certified_negative_docs: Collection[str] = frozenset(),
) -> RuleMetrics:
    """Evaluate one Rule at one Cutoff.

    A Pair whose P(yes) is at or below `cutoff` is Binned; above it, Escalated.
    `certified_negative_docs` names the documents CUAD flags `is_impossible` for this Rule.
    """
    ground = _ground(rule_id, clauses, highlights, certified_negative_docs)
    return _at_cutoff(rule_id, ground, p_yes, cutoff)


def cutoff_curve(
    rule_id: str,
    clauses: Sequence[Clause],
    highlights: Iterable[Highlight],
    p_yes: Mapping[ClauseKey, float],
    certified_negative_docs: Collection[str] = frozenset(),
) -> tuple[RuleMetrics, ...]:
    """The Cutoff Curve: one row at every distinct P(yes) Jev gave this Rule, lowest first.

    The piles only change when the Cutoff crosses a P(yes) Jev actually gave, so these rows are the
    complete curve. Nothing is fitted and nothing is chosen: the caller reads it whole.
    """
    ground = _ground(rule_id, clauses, highlights, certified_negative_docs)
    observed = sorted({p_yes[clause.key] for clause in clauses if clause.key in p_yes})
    return tuple(_at_cutoff(rule_id, ground, p_yes, cutoff) for cutoff in observed)


@dataclass(frozen=True)
class FreeSaving:
    """What can be Binned for nothing: strictly below the lowest P(yes) of any holding Clause.

    Below that P(yes) no Clause holding a Highlight is Binned, so no Highlight is Lost. It is the one
    figure on the curve that costs nothing, and the most useful number in the report. `metrics` is
    the Rule evaluated at the Cutoff just under that P(yes), so Precision there is on hand too.
    """

    rule_id: str
    lowest_held_p_yes: float
    #: The Clause that was given it. On a tie, the first by (document, span), so it is stable.
    lowest_held_clause: ClauseKey
    metrics: RuleMetrics

    @property
    def binned_clauses(self) -> int:
        return self.metrics.binned_clauses

    @property
    def binned_words(self) -> int:
        return self.metrics.binned_words

    @property
    def total_words(self) -> int:
        return self.metrics.total_words

    @property
    def clauses(self) -> int:
        return self.metrics.clauses

    @property
    def lost_provisions(self) -> int:
        return self.metrics.lost_provisions

    @property
    def binned_share(self) -> float | None:
        return self.metrics.binned_share


def free_saving(
    rule_id: str,
    clauses: Sequence[Clause],
    highlights: Iterable[Highlight],
    p_yes: Mapping[ClauseKey, float],
) -> FreeSaving | None:
    """The lowest P(yes) Jev gave a Clause holding a Highlight, and the Binned Share below it.

    `None` when no Clause holds a Highlight, since there is then no P(yes) to stay below.
    """
    highlights = list(highlights)
    held = [
        (p_yes[clause.key], clause.key)
        for clause in clauses
        if any(holds(clause, highlight) for highlight in highlights)
    ]
    if not held:
        return None
    lowest, lowest_clause = min(held)
    # Binned means "at or below" the Cutoff, so the float just under `lowest` Bins exactly the
    # Clauses scoring strictly less than it.
    metrics = evaluate_rule(rule_id, clauses, highlights, p_yes, math.nextafter(lowest, -math.inf))
    return FreeSaving(
        rule_id=rule_id,
        lowest_held_p_yes=lowest,
        lowest_held_clause=lowest_clause,
        metrics=metrics,
    )


@dataclass(frozen=True)
class FullyBinned:
    """Clauses Binned for every Rule asked, so the expensive model is never called on them.

    The only figure that becomes money: per-Rule Binned Share does not combine into it. Counted in
    Clauses as the ticket asks, and in words as well, since words are what a reader is paid for.
    """

    clauses: int
    fully_binned_clauses: int
    total_words: int
    fully_binned_words: int

    @property
    def clause_share(self) -> float | None:
        return _share(self.fully_binned_clauses, self.clauses)

    @property
    def word_share(self) -> float | None:
        return _share(self.fully_binned_words, self.total_words)


def fully_binned(
    clauses: Sequence[Clause],
    p_yes_by_rule: Mapping[str, Mapping[ClauseKey, float]],
    cutoff: float,
) -> FullyBinned:
    """Count the Clauses whose P(yes) is at or below `cutoff` for every Rule in the table."""
    count = 0
    words = 0
    for clause in clauses:
        for rule_id, table in p_yes_by_rule.items():
            if clause.key not in table:
                raise KeyError(f"Clause {clause.key} has no P(yes) for rule {rule_id}")
        if all(table[clause.key] <= cutoff for table in p_yes_by_rule.values()):
            count += 1
            words += clause.word_count
    return FullyBinned(
        clauses=len(clauses),
        fully_binned_clauses=count,
        total_words=sum(c.word_count for c in clauses),
        fully_binned_words=words,
    )


@dataclass(frozen=True)
class Separation:
    """How well one Rule's P(yes) ranks Clauses that hold a Highlight above those that do not.

    `value` is the chance that a held Clause scores higher than a not-held one, drawn at random,
    with a tie counting half: 1.0 ranks every held Clause above every not-held one, 0.5 is no better
    than a coin. It needs no Cutoff, and it does not depend on the base rate, which is why ticket 08
    can use it on a sample enriched with held Clauses where Binned Share and Precision would not
    transfer.
    """

    held: int
    not_held: int
    value: float


def separation(
    clauses: Sequence[Clause],
    highlights: Iterable[Highlight],
    p_yes: Mapping[ClauseKey, float],
) -> Separation | None:
    """Separation of one Rule over `clauses`, or `None` when either group is empty.

    A Clause is held when it holds at least one of `highlights`, as everywhere else.
    """
    highlights = list(highlights)
    held: list[float] = []
    not_held: list[float] = []
    for clause in clauses:
        group = held if any(holds(clause, h) for h in highlights) else not_held
        group.append(p_yes[clause.key])
    if not held or not not_held:
        return None
    # Counted in integers (a win is 2, a tie 1) so ties never cost a float rounding error.
    points = sum(2 if h > n else 1 if h == n else 0 for h in held for n in not_held)
    return Separation(
        held=len(held),
        not_held=len(not_held),
        value=points / (2 * len(held) * len(not_held)),
    )
