"""The Evaluator: given Clauses, Highlights and the P(yes) table, what one Cutoff costs and saves.

Pure, as ADR-0003 requires: no folds, no tuning, no randomness, no overlap threshold. Called once
per Rule. Every figure carries its counts, and a figure with an empty denominator is `None` so the
report can print "n/a" rather than inventing a zero.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

from .domain import Clause, Highlight, holds

ClauseKey = tuple[str, str]


def clause_key(clause: Clause) -> ClauseKey:
    """Identifies a Clause across the corpus: its document plus its span."""
    return (clause.doc_id, clause.span_key)


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

    escalated_holding: int

    total_words: int
    binned_words: int

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
        """Of Escalated Clauses, the share holding a Highlight."""
        return _share(self.escalated_holding, self.escalated_clauses)

    @property
    def binned_share(self) -> float | None:
        """The share of contract words Binned. The saving, measured in text not unit count."""
        return _share(self.binned_words, self.total_words)

    @property
    def base_rate(self) -> float | None:
        """The share of Clauses holding a Highlight. Precision is bounded by this."""
        return _share(self.holding_clauses, self.clauses)


def evaluate_rule(
    rule_id: str,
    clauses: Sequence[Clause],
    highlights: Iterable[Highlight],
    p_yes: Mapping[ClauseKey, float],
    cutoff: float,
) -> RuleMetrics:
    """Score one Rule at one Cutoff.

    A Pair whose P(yes) is at or below `cutoff` is Binned; above it, Escalated.
    """
    highlights = list(highlights)

    escalated: dict[ClauseKey, bool] = {}
    for clause in clauses:
        key = clause_key(clause)
        if key not in p_yes:
            raise KeyError(f"Clause {key} has no P(yes) for rule {rule_id}")
        escalated[key] = p_yes[key] > cutoff

    def is_escalated(clause: Clause) -> bool:
        return escalated[clause_key(clause)]

    total_words = sum(c.word_count for c in clauses)
    binned_words = sum(c.word_count for c in clauses if not is_escalated(c))
    binned_clauses = sum(1 for c in clauses if not is_escalated(c))

    holding_clauses = 0
    holding_escalated = 0
    escalated_holding = 0
    for clause in clauses:
        clause_holds = any(holds(clause, h) for h in highlights)
        if clause_holds:
            holding_clauses += 1
            if is_escalated(clause):
                holding_escalated += 1
                escalated_holding += 1

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
        escalated_holding=escalated_holding,
        total_words=total_words,
        binned_words=binned_words,
    )
