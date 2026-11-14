"""The Operating Point: one Cutoff chosen on half the documents and reported on the other half.

ADR-0007. A lawyer will not accept "10% of marked provisions lost", so the question becomes: if we
state a loss we can live with, how much does Jev still skip, **on documents it was not tuned on**?

The procedure is fixed here and does not depend on the answer:

1. Split the documents into two halves, by a hash of the document id (no random generator, so the
   same corpus always splits the same way).
2. On the **Selection Half**, take the highest Cutoff, one shared by every Rule, at which the
   Provisions Lost stay within the Loss Budget (a share of that half's Provisions).
3. Apply that Cutoff to the **Report Half** and read the skip, the loss and the cost there.
4. Do it both ways round, so every document is reported on exactly once, and pool the two readings.

Pure, like the Evaluator: nothing here asks Jev or reads a file. Nothing that grades a run imports
this module (`tests/test_no_tuning.py` checks), so the 0.5 reading in the report is untouched.
"""

from __future__ import annotations

import bisect
import hashlib
import math
from collections import Counter
from dataclasses import dataclass
from typing import Collection, Mapping, Sequence

from . import config
from .cost import CostFigures, TokenUsage, cost_usage, price_usage
from .domain import Clause, Highlight
from .evaluator import ClauseKey, cutoff_curve, evaluate_rule, fully_binned

#: The Loss Budgets read in the report: Pedro's "1-2% of marked provisions".
BUDGETS = (0.01, 0.02)

#: Changing this changes which documents land in which half. Written down so the split is a fact of
#: the repo and not of a run.
HALF_SALT = "halves-1"


def split_halves(
    doc_ids: Collection[str], salt: str = HALF_SALT
) -> tuple[frozenset[str], frozenset[str]]:
    """Two disjoint halves of the documents, decided by the parity of a hash of each id."""
    first: set[str] = set()
    second: set[str] = set()
    for doc_id in sorted(set(doc_ids)):
        digest = hashlib.sha256(f"{salt}:{doc_id}".encode("utf-8")).digest()
        (first if digest[0] % 2 == 0 else second).add(doc_id)
    return frozenset(first), frozenset(second)


def choose_cutoff(
    clauses: Sequence[Clause],
    highlights: Sequence[Highlight],
    p_yes_by_rule: Mapping[str, Mapping[ClauseKey, float]],
    budget_share: float,
) -> float:
    """The highest Cutoff, shared by every Rule, whose Provisions Lost stay within the budget.

    The budget is `budget_share` of all the Provisions (Highlights) given, rounded down to a whole
    provision. Provisions Lost never fall as the Cutoff rises, so this is the last Cutoff before the
    budget is first exceeded. It lies on a P(yes) Jev actually gave, since nothing changes between
    two of them. Returns 0.0 when even the lowest observed Cutoff exceeds the budget.
    """
    allowed = math.floor(budget_share * len(highlights) + 1e-9)
    steps: dict[str, tuple[list[float], list[int]]] = {}
    for rule_id, table in p_yes_by_rule.items():
        rows = cutoff_curve(
            rule_id, clauses, [h for h in highlights if h.rule_id == rule_id], table
        )
        steps[rule_id] = ([row.cutoff for row in rows], [row.lost_provisions for row in rows])

    candidates = sorted({cutoff for cutoffs, _ in steps.values() for cutoff in cutoffs})
    chosen = 0.0
    for candidate in candidates:
        lost = 0
        for cutoffs, losses in steps.values():
            index = bisect.bisect_right(cutoffs, candidate)
            lost += losses[index - 1] if index else 0
        if lost > allowed:
            break
        chosen = candidate
    return chosen


@dataclass(frozen=True)
class Reading:
    """One set of documents read at one Cutoff, shared by every Rule."""

    cutoff: float
    clauses: int
    skipped_clauses: int
    total_words: int
    skipped_words: int
    provisions: int
    lost: int
    #: The Provisions Lost, by document, most first. Shows whether a few documents decide the loss.
    lost_by_document: tuple[tuple[str, int], ...]
    usage: TokenUsage
    #: The same Clauses with the expensive model's answer length set to zero: the cost of reading
    #: only, which does not rest on the assumed output per question.
    usage_input_only: TokenUsage

    @property
    def skipped_share(self) -> float:
        return self.skipped_clauses / self.clauses if self.clauses else 0.0

    @property
    def lost_share(self) -> float:
        return self.lost / self.provisions if self.provisions else 0.0


def read_at(
    clauses: Sequence[Clause],
    highlights: Sequence[Highlight],
    p_yes_by_rule: Mapping[str, Mapping[ClauseKey, float]],
    questions: Mapping[str, str],
    cutoff: float,
) -> Reading:
    """Skip, loss and token usage for these Clauses at one Cutoff."""
    fully = fully_binned(clauses, p_yes_by_rule, cutoff)

    lost_by_document: Counter[str] = Counter()
    for doc_id in sorted({clause.doc_id for clause in clauses}):
        doc_clauses = [c for c in clauses if c.doc_id == doc_id]
        for rule_id, table in p_yes_by_rule.items():
            held = [h for h in highlights if h.doc_id == doc_id and h.rule_id == rule_id]
            if held:
                lost_by_document[doc_id] += evaluate_rule(
                    rule_id, doc_clauses, held, table, cutoff
                ).lost_provisions

    return Reading(
        cutoff=cutoff,
        clauses=fully.clauses,
        skipped_clauses=fully.fully_binned_clauses,
        total_words=fully.total_words,
        skipped_words=fully.fully_binned_words,
        provisions=len(highlights),
        lost=sum(lost_by_document.values()),
        lost_by_document=tuple(
            (doc_id, count) for doc_id, count in lost_by_document.most_common() if count
        ),
        usage=cost_usage(clauses, p_yes_by_rule, questions, cutoff),
        usage_input_only=cost_usage(
            clauses, p_yes_by_rule, questions, cutoff, output_tokens_per_question=0
        ),
    )


@dataclass(frozen=True)
class Direction:
    """Chosen on one half, reported on the other."""

    selection_documents: int
    report_documents: int
    cutoff: float
    #: The Selection Half at its own chosen Cutoff: where the budget was met by construction.
    on_selection: Reading
    #: The Report Half at the same Cutoff: the number that counts.
    on_report: Reading


@dataclass(frozen=True)
class Study:
    """Both directions at one Loss Budget. Every document is reported on exactly once."""

    budget_share: float
    directions: tuple[Direction, Direction]

    @property
    def readings(self) -> tuple[Reading, Reading]:
        return self.directions[0].on_report, self.directions[1].on_report

    @property
    def clauses(self) -> int:
        return sum(r.clauses for r in self.readings)

    @property
    def skipped_clauses(self) -> int:
        return sum(r.skipped_clauses for r in self.readings)

    @property
    def provisions(self) -> int:
        return sum(r.provisions for r in self.readings)

    @property
    def lost(self) -> int:
        return sum(r.lost for r in self.readings)

    @property
    def skipped_share(self) -> float:
        return self.skipped_clauses / self.clauses if self.clauses else 0.0

    @property
    def lost_share(self) -> float:
        return self.lost / self.provisions if self.provisions else 0.0

    def lost_by_document(self) -> tuple[tuple[str, int], ...]:
        counts: Counter[str] = Counter()
        for reading in self.readings:
            counts.update(dict(reading.lost_by_document))
        return tuple(counts.most_common())


def study(
    clauses: Sequence[Clause],
    highlights: Sequence[Highlight],
    p_yes_by_rule: Mapping[str, Mapping[ClauseKey, float]],
    questions: Mapping[str, str],
    budget_share: float,
    halves: tuple[Collection[str], Collection[str]] | None = None,
) -> Study:
    """Choose on each half, report on the other, at one Loss Budget."""
    if halves is None:
        halves = split_halves({clause.doc_id for clause in clauses})
    first, second = halves

    def part(documents: Collection[str]):
        return (
            [c for c in clauses if c.doc_id in documents],
            [h for h in highlights if h.doc_id in documents],
        )

    def one_way(selection: Collection[str], report: Collection[str]) -> Direction:
        sel_clauses, sel_highlights = part(selection)
        rep_clauses, rep_highlights = part(report)
        cutoff = choose_cutoff(sel_clauses, sel_highlights, p_yes_by_rule, budget_share)
        return Direction(
            selection_documents=len(selection),
            report_documents=len(report),
            cutoff=cutoff,
            on_selection=read_at(sel_clauses, sel_highlights, p_yes_by_rule, questions, cutoff),
            on_report=read_at(rep_clauses, rep_highlights, p_yes_by_rule, questions, cutoff),
        )

    return Study(budget_share, (one_way(first, second), one_way(second, first)))


def dollars(
    readings: Sequence[Reading], model: config.ExpensiveModel, input_only: bool = False
) -> CostFigures:
    """The cost of the expensive model alone, the cascade and Jev, summed over several readings."""
    figures = [
        price_usage(
            r.usage_input_only if input_only else r.usage,
            model,
            batch=False,
            jev_input_per_mtok=config.JEV_INPUT_PRICE.value,
            batch_discount=config.BATCH_DISCOUNT.value,
        )
        for r in readings
    ]
    return CostFigures(
        clauses=sum(f.clauses for f in figures),
        alone_usd=sum(f.alone_usd for f in figures),
        cascade_usd=sum(f.cascade_usd for f in figures),
        jev_usd=sum(f.jev_usd for f in figures),
    )


def calls_saved(readings: Sequence[Reading]) -> tuple[int, int]:
    """Expensive-model calls (model alone, cascade) summed over several readings."""
    alone = sum(r.usage.alone.calls for r in readings)
    cascade = sum(r.usage.cascade.calls for r in readings)
    return alone, cascade


__all__ = [
    "BUDGETS",
    "Direction",
    "Reading",
    "Study",
    "calls_saved",
    "choose_cutoff",
    "dollars",
    "read_at",
    "split_halves",
    "study",
]
