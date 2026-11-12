"""The Report: renders the Evaluator's output to Markdown, counts first.

Ticket 01's report is one table for R1 at one fixed Cutoff. The Cutoff Curve, the charts and the
full "How this is measured" sections arrive in ticket 05.

Every figure here is stub-derived and labelled as such: the stub's P(yes) values are a hash of its
inputs and carry no signal, so nothing in this report says anything about how Jev would behave.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .evaluator import RuleMetrics
from .rulebook import QUESTION_TYPE, Rule
from .runner import RunStats


@dataclass(frozen=True)
class DocumentSummary:
    """One row of the report's document table."""

    doc_id: str
    clauses: int
    words: int


@dataclass(frozen=True)
class ReportInputs:
    """Everything the report prints, so rendering stays a pure function of its inputs."""

    rules: Sequence[Rule]
    metrics: Sequence[RuleMetrics]
    stats: RunStats
    cutoff: float
    model_version: str
    documents: Sequence[DocumentSummary]
    is_stub: bool


def _format_share(value: float | None) -> str:
    """Render a share, or "n/a" where the denominator was empty."""
    return "n/a" if value is None else f"{value * 100:.1f}%"


def _count_pair(numerator: int, denominator: int) -> str:
    return f"{numerator}/{denominator}"


def render(inputs: ReportInputs) -> str:
    """Render the tracer-bullet report."""
    label = "stub" if inputs.is_stub else inputs.model_version
    lines: list[str] = []

    lines.append("# Jev cascade: tracer bullet")
    lines.append("")
    rule_names = ", ".join(r.id for r in inputs.rules)
    lines.append(
        f"{rule_names} over {len(inputs.documents)} documents, end to end on the **{label}** Jev "
        f"client at a single fixed Cutoff of **{inputs.cutoff:g}**."
    )
    lines.append("")

    if inputs.is_stub:
        lines.append(
            "> **Every figure in this report is stub-derived.** The stub's P(yes) values are a "
            "hash of its inputs spread uniformly over [0, 1]; they carry no signal. Nothing here "
            "says anything about how Jev would behave. The real client arrives in ticket 07."
        )
        lines.append("")

    lines.append("## Run")
    lines.append("")
    lines.append("| | |")
    lines.append("| --- | --- |")
    lines.append(f"| Documents | {len(inputs.documents)} |")
    lines.append(f"| Clauses | {sum(d.clauses for d in inputs.documents)} |")
    lines.append(f"| Words | {sum(d.words for d in inputs.documents)} |")
    lines.append(f"| Rules asked | {len(inputs.rules)} |")
    lines.append(f"| Pairs | {inputs.stats.pairs} |")
    lines.append(f"| Jev calls made | {inputs.stats.calls_made} |")
    lines.append(f"| Answers served from cache | {inputs.stats.cache_hits} |")
    lines.append(f"| Wall clock | {inputs.stats.seconds:.2f}s |")
    lines.append(f"| Question type | {QUESTION_TYPE} |")
    lines.append(f"| Model version | {inputs.model_version} |")
    lines.append("")

    lines.append("## Documents")
    lines.append("")
    lines.append("| Document | Clauses | Words |")
    lines.append("| --- | --- | --- |")
    for document in inputs.documents:
        lines.append(f"| {document.doc_id} | {document.clauses} | {document.words} |")
    lines.append("")

    for rule, metric in zip(inputs.rules, inputs.metrics):
        lines.append(f"## {rule.id} — {rule.cuad_category}")
        lines.append("")
        lines.append(f'Detection Question: _"{rule.detection_question}"_')
        lines.append("")
        lines.append(f"At Cutoff {metric.cutoff:g}, counts first:")
        lines.append("")
        lines.append("| Figure | Counts | Share |")
        lines.append("| --- | --- | --- |")
        lines.append(
            f"| Clause Recall | {_count_pair(metric.holding_escalated, metric.holding_clauses)} "
            f"holding Clauses Escalated | {_format_share(metric.clause_recall)} |"
        )
        lines.append(
            f"| Precision | {_count_pair(metric.holding_escalated, metric.escalated_clauses)} "
            f"Escalated Clauses hold a Highlight | {_format_share(metric.precision)} |"
        )
        lines.append(
            f"| Provision Recall | "
            f"{_count_pair(metric.highlights - metric.lost_provisions, metric.highlights)} "
            f"Highlights still reachable | {_format_share(metric.provision_recall)} |"
        )
        lines.append(
            f"| Lost Provisions | {metric.lost_provisions} of {metric.highlights} Highlights had "
            f"every holding Clause Binned | — |"
        )
        lines.append(
            f"| Binned Share | {_count_pair(metric.binned_words, metric.total_words)} words "
            f"Binned | {_format_share(metric.binned_share)} |"
        )
        lines.append("")
        lines.append(
            f"Supporting counts: {metric.clauses} Clauses, {metric.binned_clauses} Binned and "
            f"{metric.escalated_clauses} Escalated; {metric.holding_clauses} hold a Highlight, a "
            f"base rate of {_format_share(metric.base_rate)}."
        )
        lines.append("")
        lines.append(
            "Precision reads low by arithmetic at this base rate, not because Jev is performing "
            "badly. Always read it beside its counts."
        )
        lines.append("")

    lines.append("## What this does not measure")
    lines.append("")
    lines.append(
        "- Whether Jev's confident yes answers are trustworthy. The cascade never acts on a yes."
    )
    lines.append(
        "- Whether the expensive model would actually find a provision once its Clause is Escalated."
    )
    lines.append("- Whether the lawyers highlighted everything.")
    lines.append("")
    lines.append(
        "Accuracy and ROC AUC are deliberately absent: at a ~1% base rate, answering no to "
        "everything would score 99% accuracy (ADR-0003)."
    )
    lines.append("")

    return "\n".join(lines)
