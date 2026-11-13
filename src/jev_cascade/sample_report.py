"""Ticket 08's report: three question types, then heading on against off, by separation per Rule.

A pure function of its inputs, so it can be rebuilt from the cache with no network. Every separation
is printed beside the held and not-held counts it came from.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from .sample_study import (
    HELD_PER_RULE,
    MARGIN,
    NEAR_MISS_SHARE,
    NOT_HELD_PER_RULE,
    PER_DOCUMENT_CAP,
    SAMPLE_SEED,
    ArmResult,
    SampleSet,
)

Difference = tuple[float, float, float]


@dataclass(frozen=True)
class StudyInputs:
    sample: SampleSet
    #: The three question types asked with heading context on, in the order shown.
    type_results: Sequence[ArmResult]
    chosen_type: str
    #: The chosen type asked with the heading taken out.
    heading_off: ArmResult
    #: The heading setting chosen: True keeps the heading in Jev's context.
    heading_context: bool
    #: Mean separation minus `binary`'s, with a 95% interval, for each type but `binary`.
    type_differences: Mapping[str, Difference]
    #: Heading off minus heading on, for the chosen type.
    heading_difference: Difference
    model_version: str
    is_stub: bool
    #: Documents the sample was drawn from.
    documents: int
    #: Over the whole corpus: Clauses, how many have a Parent Line, and of those how many are a
    #: standalone heading, introduce a list (end in a colon), or are other longer lines.
    parent_lines: Mapping[str, int]
    #: Jev answers behind the report, read from the cache so a rebuild states the same figure.
    answers: int


def _cell(arm: ArmResult, rule_id: str) -> str:
    result = arm.by_rule.get(rule_id)
    if result is None:
        return "n/a"
    return f"{result.value:.3f} ({result.held}/{result.not_held})"


def _interval(difference: Difference) -> str:
    point, low, high = difference
    return f"{point:+.3f} (95% interval {low:+.3f} to {high:+.3f})"


def _verdict(difference: Difference) -> str:
    _, low, high = difference
    if low > 0:
        return "the interval is above zero"
    if high < 0:
        return "the interval is below zero"
    return "the interval spans zero, so the sample cannot tell the two apart"


def _table(results: Sequence[ArmResult], rule_ids: Sequence[str]) -> list[str]:
    lines = [
        "| Rule | " + " | ".join(r.arm.label for r in results) + " |",
        "| --- |" + " --- |" * len(results),
    ]
    for rule_id in rule_ids:
        lines.append(f"| {rule_id} | " + " | ".join(_cell(r, rule_id) for r in results) + " |")
    lines.append("| **Mean** | " + " | ".join(f"**{r.mean_separation:.3f}**" for r in results) + " |")
    return lines


#: Separation at or above this in every cell of every table counts as near the ceiling.
CEILING = 0.9


def _ceiling_note(inputs: StudyInputs) -> list[str]:
    """A bullet saying the sample cannot discriminate, when every arm scores near 1.0."""
    arms = [*inputs.type_results, inputs.heading_off]
    values = [s.value for arm in arms for s in arm.by_rule.values() if s is not None]
    if not values or min(values) < CEILING:
        return []
    near_misses = sum(inputs.sample.near_misses.values())
    return [
        f"- **Separation is near its ceiling here.** Every Rule scores at least {min(values):.3f} "
        "in every arm, so this sample has little room to tell the arms apart. Read 'no difference' "
        "as none detectable on this sample, not as none. In particular the harm a heading may do, "
        "stamping a section label on unrelated Clauses, would show over the corpus's many "
        f"unrelated Clauses, and this sample holds only {near_misses} near misses across all Rules.",
    ]


def _most_from_one_document(sample: SampleSet) -> int:
    most = 0
    for clauses in sample.by_rule.values():
        counts: dict[str, int] = {}
        for clause in clauses:
            counts[clause.doc_id] = counts.get(clause.doc_id, 0) + 1
        most = max(most, max(counts.values(), default=0))
    return most


def _not_held(inputs: StudyInputs) -> int:
    return sum(r.not_held for r in inputs.type_results[0].by_rule.values() if r is not None)


def _near_miss_share(inputs: StudyInputs) -> float:
    not_held = _not_held(inputs)
    return sum(inputs.sample.near_misses.values()) / not_held if not_held else 0.0


def _heading_scope(kinds: Mapping[str, int]) -> list[str]:
    """What 'the heading taken out' covers, measured over the corpus, so a reader is not misled."""
    with_parent = kinds["with_parent"]
    if not with_parent:
        return []
    return [
        f"Of the corpus's {kinds['clauses']} Clauses, {with_parent} have a Parent Line. "
        f"**{kinds['heading']}** of those are a standalone section heading, and that is all the "
        f"heading-off arm takes out. {kinds['list_intro']} introduce a list and {kinds['other']} are "
        "other longer lines, many a heading with its body text on the same line "
        "('14. REPRESENTATIONS AND WARRANTIES.  (a) Each party...'); those stay in both arms. So "
        "'heading off' removes the heading for "
        f"{kinds['heading'] / with_parent:.0%} of Parent Lines, and the comparison understates what "
        "removing every heading would do.",
        "",
    ]


def render_study(inputs: StudyInputs) -> str:
    """The comparison as Markdown."""
    sample = inputs.sample
    rule_ids = list(sample.by_rule)
    lines: list[str] = ["# Question wording, type and heading: the ticket 08 sample", ""]

    if inputs.is_stub:
        lines += [
            "> **Stub run.** These answers carry no signal: every figure below is noise and none "
            "of it says anything about Jev.",
            "",
        ]

    lines += [
        f"Model `{inputs.model_version}`. {inputs.answers} Jev answers behind this report, all in "
        "the cache, so a rerun asks nothing and the report can be rebuilt with no network.",
        "",
        "## Decision rules",
        "",
        "Fixed before any real call. Both choices are made on **separation per Rule only**: the "
        "chance that a Clause holding a Highlight scores above one that does not, ties counting "
        "half. 1.0 is a perfect ranking, 0.5 is a coin.",
        "",
        "- Compare the three types with the heading shown. Pick the highest mean separation across "
        f"Rules, unless it beats `binary` by less than {MARGIN:.2f}, in which case `binary` stands.",
        f"- Then ask the chosen type with the heading taken out. The heading comes out only if that "
        f"beats heading-on by at least {MARGIN:.2f}; otherwise it stays.",
        "- A 95% paired bootstrap interval, resampling documents, is printed beside each "
        "difference, so a reader can see whether it is inside the noise. It does not change the "
        "rule.",
        "- **Binned Share and Precision are not read from this sample.** It is enriched with held "
        "Clauses and near misses, so its base rate is wrong and those figures do not transfer.",
        "",
        "## The sample",
        "",
        f"Seed {SAMPLE_SEED}. Up to {HELD_PER_RULE} held Clauses and {NOT_HELD_PER_RULE} not-held "
        f"Clauses per Rule, drawn from all {inputs.documents} documents. A **held** Clause holds at "
        "least one Highlight of the Rule; a **not-held** Clause holds none, whether or not its "
        "document is a Certified Negative.",
        "",
        f"The cap is {PER_DOCUMENT_CAP} Clauses from any one document for each of the three draws "
        f"(held, near miss, other not-held), so up to three times that to one Rule; the most any "
        f"one Rule took from one document is {_most_from_one_document(sample)}.",
        "",
        f"The aim was {NEAR_MISS_SHARE:.0%} near misses among the not-held Clauses: ones under the "
        f"same section heading as a held Clause. **The sample got {_near_miss_share(inputs):.0%}** "
        f"({sum(sample.near_misses.values())} of {_not_held(inputs)}), because few not-held Clauses "
        "share a heading with a held one; the rest are drawn at random. Each Clause is asked only "
        f"its own Rule's question, so one arm is {sample.pairs} Pairs.",
        "",
        "| Rule | Held | Not held | Near misses | Heading-affected Clauses |",
        "| --- | --- | --- | --- | --- |",
    ]
    for rule_id in rule_ids:
        first = inputs.type_results[0].by_rule.get(rule_id)
        held = first.held if first else 0
        not_held = first.not_held if first else 0
        affected = sum(1 for c in sample.by_rule[rule_id] if c.parent_is_heading)
        lines.append(
            f"| {rule_id} | {held} | {not_held} | {sample.near_misses[rule_id]} | {affected} |"
        )
    lines += [
        "",
        "A heading-affected Clause is one whose Parent Line is a section heading. It is the only "
        "kind the heading setting can change; the others are the same prompt in both arms. The "
        "column counts Clauses within a Rule, so a Clause drawn for two Rules is counted in both, "
        "and the column's sum is Pairs.",
        "",
        "## Question type, heading shown",
        "",
        "Separation, with held/not-held Clause counts in brackets.",
        "",
        *_table(inputs.type_results, rule_ids),
        "",
    ]
    for question_type, difference in inputs.type_differences.items():
        lines.append(
            f"- `{question_type}` minus `binary`, mean separation: {_interval(difference)}: "
            f"{_verdict(difference)}."
        )
    lines += [
        "",
        f"**Chosen question type: {inputs.chosen_type}**, for every Rule.",
        "",
        "## Heading context",
        "",
        f"The chosen type, `{inputs.chosen_type}`, with the section heading shown against taken out. "
        "A Parent Line that introduces a list, such as 'Licensee shall:', is shown in both.",
        "",
        *_heading_scope(inputs.parent_lines),
        "",
    ]
    on = next(r for r in inputs.type_results if r.arm.question_type == inputs.chosen_type)
    lines += [
        *_table([on, inputs.heading_off], rule_ids),
        "",
        f"- Heading off minus heading on, mean separation: {_interval(inputs.heading_difference)}: "
        f"{_verdict(inputs.heading_difference)}.",
        "",
        f"**Heading context: {'on' if inputs.heading_context else 'off'}**.",
        "",
        "## What this does not show",
        "",
        "- **Both choices were made on Pairs that the full run later scores.** That is a small "
        "selection leak: two settings, chosen on a sample of a few percent of the corpus. The final "
        "report says so.",
        f"- With {HELD_PER_RULE} held and {NOT_HELD_PER_RULE} not-held Clauses a Rule, one Rule's "
        "separation is uncertain by a few hundredths. The mean across Rules is steadier; the "
        "intervals above are the honest read.",
        *_ceiling_note(inputs),
        "- Held and not-held are CUAD's labels. A not-held Clause may hold a provision the lawyers "
        "did not mark, which depresses every arm's separation alike.",
        "",
    ]
    return "\n".join(lines)
