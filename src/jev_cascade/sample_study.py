"""Ticket 08's sample study: how Jev should be asked, settled on a small sample before the real run.

Two questions, both answered on **separation per Rule only** (see `evaluator.separation`):

1. Which question type, one for all Rules: Jev's yes/no type, a two-level score, or a yes/no choice?
2. Is the section heading shown to Jev as Parent Line, or not?

The sample is deliberately enriched with held Clauses and with near-miss not-held ones, so its base
rate is wrong. That is why Binned Share and Precision are never read from it: they do not transfer.
Separation is a ranking of held above not-held and does not depend on the base rate.

**The decision rules are fixed here, before any real call**, so the result cannot choose its own
rule. Both pick on the point estimate of the mean separation across Rules, with a margin so that a
difference inside the noise does not change the setting; a paired bootstrap interval is printed
beside every difference so the reader can see whether it is inside the noise.

Both settings are chosen on Pairs that the full run later scores. That is a small selection leak
and the final report says so.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from .domain import Clause, Highlight, holds, without_heading
from .evaluator import ClauseKey, Separation, separation
from .jev import JevClient
from .rulebook import Rule, rule
from .runner import run_pairs

#: Held Clauses drawn per Rule, not-held Clauses drawn per Rule, and the most Clauses one document
#: may supply to **each** of the three draws (held, near-miss, other not-held), so one contract
#: cannot be the sample. The cap applies to each draw separately, so a document can supply up to
#: three times this to one Rule; the report prints the realised maximum.
HELD_PER_RULE = 20
NOT_HELD_PER_RULE = 40
PER_DOCUMENT_CAP = 4

#: Half the not-held Clauses are near misses: they sit under the same section heading as a held
#: Clause. Plain random not-held Clauses are mostly boilerplate that every question type scores
#: near zero, which would make the types look alike. Near misses are also the only Clauses where
#: showing the heading can change the answer for the worse, which is what the heading check probes.
NEAR_MISS_SHARE = 0.5

#: Fixed, so the same sample is drawn every time and the cache serves a re-run.
SAMPLE_SEED = 20261113

#: A setting must beat the one it replaces by this much mean separation to be chosen over it. Below
#: it the difference is inside the noise of a sample this size, and the simpler setting stands.
MARGIN = 0.02

#: The type chosen when nothing wins by the margin: Jev's native yes/no type, the cheapest to read.
DEFAULT_TYPE = "binary"

QUESTION_TYPES = ("binary", "score2", "choice2")


@dataclass(frozen=True)
class Arm:
    """One way of asking: a question type and whether the heading is shown."""

    question_type: str
    heading_context: bool

    @property
    def label(self) -> str:
        return f"{self.question_type}, heading {'on' if self.heading_context else 'off'}"


@dataclass(frozen=True)
class SampleSet:
    """The Clauses drawn for each Rule. A Clause may be drawn for more than one Rule."""

    by_rule: Mapping[str, tuple[Clause, ...]]
    #: Of the not-held Clauses drawn for each Rule, how many are near misses.
    near_misses: Mapping[str, int]

    @property
    def pairs(self) -> int:
        """Pairs one arm asks: each Clause is asked only the Rule it was drawn for."""
        return sum(len(clauses) for clauses in self.by_rule.values())


def _spread(candidates: list[Clause], count: int, per_document: int, rng: random.Random) -> list[Clause]:
    """Up to `count` of `candidates`, at most `per_document` from any one document.

    Shuffled first, then taken in order, so which Clauses are drawn depends only on the seed.
    """
    shuffled = list(candidates)
    rng.shuffle(shuffled)
    taken: list[Clause] = []
    per_doc: dict[str, int] = {}
    for clause in shuffled:
        if len(taken) == count:
            break
        if per_doc.get(clause.doc_id, 0) >= per_document:
            continue
        per_doc[clause.doc_id] = per_doc.get(clause.doc_id, 0) + 1
        taken.append(clause)
    return taken


def draw_sample(
    clauses: Sequence[Clause],
    highlights_by_rule: Mapping[str, Sequence[Highlight]],
    rules: Sequence[Rule],
    held: int = HELD_PER_RULE,
    not_held: int = NOT_HELD_PER_RULE,
    per_document: int = PER_DOCUMENT_CAP,
    seed: int = SAMPLE_SEED,
) -> SampleSet:
    """Draw, for each Rule, held Clauses and not-held Clauses, half the latter near misses.

    A Rule with fewer held Clauses than asked gets all it has. Near misses are drawn first from the
    not-held Clauses that share a section heading (and a document) with a drawn held Clause, then the
    rest at random from the other not-held Clauses.
    """
    by_rule: dict[str, tuple[Clause, ...]] = {}
    near_counts: dict[str, int] = {}
    for rule in rules:
        rng = random.Random(f"{seed}/{rule.id}")
        marked = list(highlights_by_rule.get(rule.id, ()))
        holding = [c for c in clauses if any(holds(c, h) for h in marked)]
        holding_keys = {c.key for c in holding}
        others = [c for c in clauses if c.key not in holding_keys]

        drawn_held = _spread(holding, held, per_document, rng)
        headings = {(c.doc_id, c.parent_line) for c in drawn_held if c.parent_is_heading}
        near_pool = [c for c in others if c.parent_is_heading and (c.doc_id, c.parent_line) in headings]
        near = _spread(near_pool, round(not_held * NEAR_MISS_SHARE), per_document, rng)
        near_keys = {c.key for c in near}
        rest_pool = [c for c in others if c.key not in near_keys]
        rest = _spread(rest_pool, not_held - len(near), per_document, rng)

        by_rule[rule.id] = tuple(sorted(drawn_held + near + rest, key=lambda c: (c.doc_id, c.start)))
        near_counts[rule.id] = len(near)
    return SampleSet(by_rule=by_rule, near_misses=near_counts)


@dataclass(frozen=True)
class ArmResult:
    """One arm's P(yes) for its sample, and the separation each Rule's P(yes) achieved."""

    arm: Arm
    by_rule: Mapping[str, Separation | None]
    p_yes: Mapping[str, Mapping[ClauseKey, float]]

    @property
    def mean_separation(self) -> float:
        """The mean over the Rules that have both held and not-held Clauses."""
        values = [s.value for s in self.by_rule.values() if s is not None]
        return sum(values) / len(values) if values else float("nan")


def run_arm(
    arm: Arm,
    sample: SampleSet,
    highlights_by_rule: Mapping[str, Sequence[Highlight]],
    client: JevClient,
    cache_path: Path,
    workers: int = 1,
) -> ArmResult:
    """Ask every drawn Clause its own Rule's question under `arm`, and score the separation.

    Answers come from the shared cache where the prompt is identical, so an arm that differs only
    in the heading asks only the Clauses that had one.
    """
    rules_by_id = {r.id: r for r in _rules_for(sample)}
    tables: dict[str, Mapping[ClauseKey, float]] = {}
    separations: dict[str, Separation | None] = {}
    for rule_id, clauses in sample.by_rule.items():
        shown = clauses if arm.heading_context else tuple(without_heading(clauses))
        table, _ = run_pairs(
            shown,
            [rules_by_id[rule_id]],
            client,
            cache_path,
            workers=workers,
            question_type=arm.question_type,
        )
        tables[rule_id] = table[rule_id]
        separations[rule_id] = separation(shown, highlights_by_rule.get(rule_id, ()), table[rule_id])
    return ArmResult(arm=arm, by_rule=separations, p_yes=tables)


def _rules_for(sample: SampleSet) -> list[Rule]:
    return [rule(rule_id) for rule_id in sample.by_rule]


def choose_type(results: Sequence[ArmResult]) -> Arm:
    """The question type with the highest mean separation, unless none beats `binary` by `MARGIN`.

    Decided on the point estimate, fixed before any real call. A type that wins by less than the
    margin is inside the noise of a sample this size, so `binary` stands.
    """
    by_type = {r.arm.question_type: r for r in results}
    base = by_type[DEFAULT_TYPE]
    best = max(results, key=lambda r: r.mean_separation)
    if best.arm.question_type != DEFAULT_TYPE and best.mean_separation - base.mean_separation >= MARGIN:
        return best.arm
    return base.arm


def choose_heading(on: ArmResult, off: ArmResult) -> bool:
    """Whether heading context stays on. It is turned off only if off wins by `MARGIN`.

    The rule is deliberately lopsided: turning the heading off is the change, so it has to show a
    clear gain. Within the margin the setting the study started from stands.
    """
    return not (off.mean_separation - on.mean_separation >= MARGIN)


def bootstrap_difference(
    a: ArmResult,
    b: ArmResult,
    sample: SampleSet,
    highlights_by_rule: Mapping[str, Sequence[Highlight]],
    draws: int = 1000,
    seed: int = SAMPLE_SEED,
) -> tuple[float, float, float]:
    """Mean separation of `b` minus `a`, and a 95% paired bootstrap interval around it.

    Each draw resamples a Rule's **documents** with replacement and takes all the Clauses the
    sample holds from each, the same resample for both arms. Clauses from one contract are alike,
    so resampling Clauses singly would make the interval too narrow. A draw in which a Rule loses
    all its held or all its not-held Clauses leaves that Rule out for both arms.

    The interval is the 2.5th and 97.5th percentile of the draws and is not adjusted to contain the
    point estimate.
    """
    rng = random.Random(seed)
    by_document: dict[str, dict[str, list[Clause]]] = {}
    for rule_id, clauses in sample.by_rule.items():
        groups: dict[str, list[Clause]] = {}
        for clause in clauses:
            groups.setdefault(clause.doc_id, []).append(clause)
        by_document[rule_id] = groups

    differences: list[float] = []
    for _ in range(draws):
        gaps: list[float] = []
        for rule_id, groups in by_document.items():
            doc_ids = list(groups)
            resampled = [
                clause
                for doc_id in (doc_ids[rng.randrange(len(doc_ids))] for _ in doc_ids)
                for clause in groups[doc_id]
            ]
            marked = highlights_by_rule.get(rule_id, ())
            left = separation(resampled, marked, a.p_yes[rule_id])
            right = separation(resampled, marked, b.p_yes[rule_id])
            if left is not None and right is not None:
                gaps.append(right.value - left.value)
        if gaps:
            differences.append(sum(gaps) / len(gaps))
    differences.sort()
    point = b.mean_separation - a.mean_separation
    if not differences:
        return point, math.nan, math.nan
    low = differences[int(0.025 * (len(differences) - 1))]
    high = differences[math.ceil(0.975 * (len(differences) - 1))]
    return point, low, high
