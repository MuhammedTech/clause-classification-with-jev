"""Renders the Operating Point study as Markdown. Pure: takes the studies, returns text."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from . import config
from .operating_point import Study, calls_saved, dollars
from .rulebook import DROPPED_RULES, RULEBOOK

_NUMBER_WORDS = {3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight"}


@dataclass(frozen=True)
class OperatingPointInputs:
    studies: Sequence[Study]
    documents: int
    clauses: int
    provisions: int
    model_version: str
    #: The 0.5 reading the main report leads with, for the comparison: skipped share, lost, provisions.
    fixed_skipped_share: float
    fixed_lost: int
    fixed_provisions: int


def _rules_in_words() -> str:
    return _NUMBER_WORDS.get(len(RULEBOOK), str(len(RULEBOOK)))


def _rule_set_bullet() -> str:
    """The admission that the Rule set was changed after results were seen, one line per dropped
    Rule that was dropped for performance rather than independence. Generated from the Rulebook so
    it cannot name a Rule that is back in, or miss one that has gone."""
    after_run = [r for r in DROPPED_RULES if r.detection_question]
    if not after_run:
        return ""
    names = ", ".join(f"{r.cuad_category} ({r.id})" for r in after_run)
    return (
        f"- **The Rule set was changed after the results were seen.** {names} was removed after the "
        "real run, because Jev separated it worst and its marked Provisions could not be checked: "
        "there is no lawyer and there is no more data. This departs from the Rules agreed beforehand "
        "and makes every figure on this page more favourable than a Rule set fixed in advance. The "
        "Cutoff is still chosen on one half and read on the other, but the Rule set is not held out. "
        "See ADR-0008 for the same run over all seven Rules."
    )


def _pct(share: float) -> str:
    return f"{share * 100:.1f}%"


def _usd(value: float | None) -> str:
    return "n/a" if value is None else f"${value:,.2f}"


def _doc_label(doc_id: str) -> str:
    return doc_id if len(doc_id) <= 48 else doc_id[:45] + "..."


def _study_table(s: Study) -> list[str]:
    lines = [
        "| Chosen on | Cutoff | Skipped there | Lost there | Reported on | Skipped | Lost |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for label, d in zip(("half 1", "half 2"), s.directions):
        sel, rep = d.on_selection, d.on_report
        other = "half 2" if label == "half 1" else "half 1"
        lines.append(
            f"| {label} ({d.selection_documents} docs) | {d.cutoff:.2f} "
            f"| {_pct(sel.skipped_share)} | {sel.lost}/{sel.provisions} ({_pct(sel.lost_share)}) "
            f"| {other} ({d.report_documents} docs) "
            f"| {rep.skipped_clauses}/{rep.clauses} ({_pct(rep.skipped_share)}) "
            f"| {rep.lost}/{rep.provisions} ({_pct(rep.lost_share)}) |"
        )
    lines.append(
        f"| **Both, each document reported once** | | | | all {s.clauses:,} Clauses "
        f"| **{s.skipped_clauses:,}/{s.clauses:,} ({_pct(s.skipped_share)})** "
        f"| **{s.lost}/{s.provisions} ({_pct(s.lost_share)})** |"
    )
    return lines


def _cost_table(studies: Sequence[Study], model: config.ExpensiveModel) -> list[str]:
    lines = [
        "| Loss Budget | Skipped | Lost | Claude alone | Cascade (Claude + Jev) | Saved | Saved, share "
        "| Saved, reading only |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for s in studies:
        full = dollars(s.readings, model)
        inputs = dollars(s.readings, model, input_only=True)
        saved = full.per_1000(full.net_usd)
        lines.append(
            f"| {_pct(s.budget_share)} | {_pct(s.skipped_share)} | {_pct(s.lost_share)} "
            f"| {_usd(full.per_1000(full.alone_usd))} "
            f"| {_usd(full.per_1000(full.cascade_usd + full.jev_usd))} "
            f"| **{_usd(saved)}** | {_pct(full.net_usd / full.alone_usd)} "
            f"| {_usd(inputs.per_1000(inputs.net_usd))} ({_pct(inputs.net_usd / inputs.alone_usd)}) |"
        )
    return lines


def render_operating_point(inputs: OperatingPointInputs) -> str:
    model = config.EXPENSIVE_MODELS[0]
    studies = inputs.studies
    out: list[str] = []
    out.append("# Operating Point: the Cutoff a legal reader would accept")
    out.append("")
    out.append(
        f"{inputs.documents} documents, {inputs.clauses:,} Clauses, {inputs.provisions} lawyer-marked "
        f"Provisions, {_rules_in_words()} Rules, `{inputs.model_version}`. Read from the stored answers; nothing is asked of Jev."
    )
    out.append("")
    out.append("## Why this exists")
    out.append("")
    out.append(
        f"The main report reads the cascade at a fixed Cutoff of 0.5. There Jev skips "
        f"{_pct(inputs.fixed_skipped_share)} of Clauses and loses {inputs.fixed_lost} of "
        f"{inputs.fixed_provisions} marked Provisions ({_pct(inputs.fixed_lost / inputs.fixed_provisions)}). "
        "That is too many for a legal team. So: state a loss we can live with, choose the Cutoff for it, "
        "and say how much Jev still skips. Choosing a Cutoff is tuning, so it is done on one half of the "
        "documents and reported on the other (ADR-0007)."
    )
    out.append("")
    out.append("## Procedure")
    out.append("")
    out.append(
        "1. Split the documents in two by a hash of the document id. No random generator, so the split is the same every time."
    )
    out.append(
        f"2. On the **Selection Half**, take the highest Cutoff, **one shared by all {_rules_in_words()} Rules**, at which "
        "the Provisions Lost stay within the **Loss Budget**, a share of that half's Provisions."
    )
    out.append("3. Apply that Cutoff to the **Report Half** and read the skip, the loss and the cost there.")
    out.append(
        "4. Do it both ways round, so every document is reported on exactly once, and pool the two readings."
    )
    out.append("")
    for s in studies:
        out.append(f"## Loss Budget {_pct(s.budget_share)} of marked Provisions")
        out.append("")
        out.extend(_study_table(s))
        out.append("")
        alone, cascade = calls_saved(s.readings)
        verdict = (
            f"The pooled loss of {_pct(s.lost_share)} is within the {_pct(s.budget_share)} budget."
            if s.lost_share <= s.budget_share
            else f"The pooled loss of {_pct(s.lost_share)} is **above** the {_pct(s.budget_share)} budget."
        )
        worst = max(d.on_report.lost_share for d in s.directions)
        out.append(
            f"{verdict} The worse half lost {_pct(worst)}. Claude calls: {alone:,} if everything is sent, "
            f"{cascade:,} in the cascade ({_pct(1 - cascade / alone)} fewer). The two halves disagree, and "
            "the gap is the point: read the pooled row as the answer and the two rows above it as how far it can move."
        )
        out.append("")
    out.append("## What it saves, per 1,000 Clauses")
    out.append("")
    out.append(
        f"Against sending every Clause to {model.name}, at list price, priced over the Report Halves "
        "and scaled to 1,000 Clauses. The Claude run was never made, so this is an estimate from token counts."
    )
    out.append("")
    out.extend(_cost_table(inputs.studies, model))
    out.append("")
    out.append(
        f"The saving is larger than the skipped share because a Clause that is sent on carries only the "
        f"questions Jev said yes to, and the expensive model's answer length "
        f"({int(config.EXPENSIVE_OUTPUT_TOKENS_PER_QUESTION.value)} tokens per question) is an assumption. "
        "The last column sets that answer length to zero, which is the saving from reading alone and does not depend on the guess."
    )
    out.append("")
    for s in studies:
        top = s.lost_by_document()[:3]
        if not top:
            continue
        out.append(f"## Where the {_pct(s.budget_share)}-budget losses sit")
        out.append("")
        top_doc, top_count = s.lost_by_document()[0]
        out.append(
            f"{top_count} of the {s.lost} Provisions Lost on the Report Halves are in one document, "
            f"`{_doc_label(top_doc)}`. By document:"
        )
        out.append("")
        out.append("| Document | Provisions Lost |")
        out.append("| --- | --- |")
        for doc_id, count in top:
            out.append(f"| {_doc_label(doc_id)} | {count} |")
        out.append("")
    out.append("## Read this before quoting a number")
    out.append("")
    out.append(
        "- **The budget is met on average, not on every half.** A Cutoff chosen to fit one half's budget "
        "exactly sits at the edge of that half's data, so on the other half it can lose more or less. The two "
        "directions above show by how much."
    )
    out.append(_rule_set_bullet())
    out.append(
        "- **A few documents decide it.** Read the tables above: the losses sit in a handful of "
        "contracts, so another sample of contracts could move the figure a long way."
    )
    out.append(
        "- **One shared Cutoff.** Per-Rule Cutoffs were tried while designing this and are not used: see ADR-0007."
    )
    out.append(
        "- **The procedure was chosen after the full-data curve was seen.** The 1% and 2% budgets and the "
        "shared Cutoff were picked knowing roughly where the curve sits, and a prototype on a different "
        "split was looked at while designing this. The split used here (`halves-1`) was the first one "
        "written into the code and was not picked for its result, but the pooled figure is not a perfectly "
        "blind test. The choice of the Cutoff itself is held out."
    )
    out.append(
        "- **Cost is an estimate.** The expensive model was never run. Tokens are characters divided by 4 "
        "and its answer length is assumed. See `report.md`, Cost and time."
    )
    out.append("- **53 license agreements only.** Nothing here says how it does on other contract types.")
    out.append("")
    return "\n".join(out)
