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
    highlights = list(highlights)

    escalated: dict[ClauseKey, bool] = {}
    for clause in clauses:
        if clause.key not in p_yes:
            raise KeyError(f"Clause {clause.key} has no P(yes) for rule {rule_id}")
        escalated[clause.key] = p_yes[clause.key] > cutoff

    def is_escalated(clause: Clause) -> bool:
        return escalated[clause.key]

    total_words = sum(c.word_count for c in clauses)
    binned_words = sum(c.word_count for c in clauses if not is_escalated(c))
    binned_clauses = sum(1 for c in clauses if not is_escalated(c))

    holding_clauses = 0
    holding_escalated = 0
    certified_clauses = certified_escalated = 0
    inferred_clauses = inferred_escalated = 0
    for clause in clauses:
        if any(holds(clause, h) for h in highlights):
            holding_clauses += 1
            if is_escalated(clause):
                holding_escalated += 1
        elif clause.doc_id in certified_negative_docs:
            certified_clauses += 1
            if is_escalated(clause):
                certified_escalated += 1
        else:
            inferred_clauses += 1
            if is_escalated(clause):
                inferred_escalated += 1

    lost_provisions = 0
    for highlight in highlights:
        holders = [c for c in clauses if holds(c, highlight)]
        if not holders:
            raise ValueError(
                f"Highlight {highlight.doc_id} [{highlight.start},{highlight.end}) for rule "
                f"{rule_id} is held by no Clause; the Clauses do not partition the document "
                f"(ADR-0004)"
            )
        if not any(is_escalated(c) for c in holders):
            lost_provisions += 1

    return RuleMetrics(
        rule_id=rule_id,
        cutoff=cutoff,
        clauses=len(clauses),
        binned_clauses=binned_clauses,
        escalated_clauses=len(clauses) - binned_clauses,
        holding_clauses=holding_clauses,
        holding_escalated=holding_escalated,
        highlights=len(highlights),
        lost_provisions=lost_provisions,
        total_words=total_words,
        binned_words=binned_words,
        certified_negative_clauses=certified_clauses,
        certified_negative_escalated=certified_escalated,
        inferred_negative_clauses=inferred_clauses,
        inferred_negative_escalated=inferred_escalated,
    )


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
    highlights = list(highlights)
    observed = sorted({p_yes[clause.key] for clause in clauses if clause.key in p_yes})
    return tuple(
        evaluate_rule(rule_id, clauses, highlights, p_yes, observed_p_yes, certified_negative_docs)
        for observed_p_yes in observed
    )


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
    transfer. It is the area under the ROC curve.
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
