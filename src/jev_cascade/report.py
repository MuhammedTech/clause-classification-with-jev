"""The Report: renders the Evaluator's output to Markdown, counts first.

Ticket 01's report is one table for R1 at one fixed Cutoff. The Cutoff Curve, the charts and the
full "How this is measured" sections arrive in ticket 05.

Every figure here is stub-derived and labelled as such: the stub's P(yes) values are a hash of its
inputs and carry no signal, so nothing in this report says anything about how Jev would behave.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .corpus import CORPUS_DOCUMENTS, GATE_MIN_DOCUMENTS, GATE_MIN_SPANS, CorpusFacts
from .evaluator import RuleMetrics
from .rulebook import (
    DROPPED_REASONS,
    QUESTION_TYPE,
    REPLACED_RULES,
    RULEBOOK,
    Rule,
)
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
    corpus: CorpusFacts


def _format_share(value: float | None) -> str:
    """Render a share, or "n/a" where the denominator was empty."""
    return "n/a" if value is None else f"{value * 100:.1f}%"


def _count_pair(numerator: int, denominator: int) -> str:
    return f"{numerator}/{denominator}"


def _corpus_section(corpus: CorpusFacts) -> list[str]:
    """How the 53 documents were chosen, and the join one of them needs."""
    counts = corpus.filter_counts
    return [
        "## Corpus",
        "",
        f"The **License Agreement Set** is the {counts['csv_document_name']} rows of "
        '`master_clauses.csv` whose `Document Name` contains "licen". Two other filters give a '
        "different set and are not the one used, which is why earlier notes disagree on the size:",
        "",
        "| Filter | Documents |",
        "| --- | --- |",
        f'| CSV `Document Name` contains "licen" | {counts["csv_document_name"]} |',
        f'| CSV `Filename` contains "licen" | {counts["csv_filename"]} |',
        f'| JSON `title` contains "licen" | {counts["json_title"]} |',
        "",
        "The JSON carries no `Document Name` field, so each CSV row is joined to `CUAD_v1.json` by "
        "comparing `Filename` against the JSON `title`: the `.pdf` / `.txt` extension stripped, "
        "then compared on **alphanumerics only, lowercased**. With that normalisation all "
        f"{counts['csv_document_name']} resolve. Without it exactly one fails — PACIRA "
        "PHARMACEUTICALS, whose filename says `A&R` where the title says `A_R`.",
        "",
        f"Graded text is the JSON `context`, the same string the Highlight offsets are measured "
        f"against: **{corpus.documents} documents**, {corpus.characters:,} characters, "
        f"{corpus.spans} Highlights across the seven Rules. Every one of those offsets lands "
        "exactly on its answer text, so character-range overlap is a sound label (ADR-0004).",
        "",
    ]


def _rulebook_section(corpus: CorpusFacts) -> list[str]:
    """The seven Rules, their ground-truth counts, the gate, and what was dropped and renamed."""
    lines = [
        "## Rulebook and the gate",
        "",
        "Seven Rules, each mapped to one CUAD category and asked as one positively phrased "
        "Detection Question (ADR-0005). The **gate** asks for at least "
        f"{GATE_MIN_DOCUMENTS} documents carrying a span and at least {GATE_MIN_SPANS} spans; "
        "below either, the denominators are too thin to read a curve off.",
        "",
        "These counts come from **CUAD** annotations rather than from the Splitter, so they do not "
        f"move when the partition changes. The gate is therefore settled once, over all "
        f"{CORPUS_DOCUMENTS} documents at corpus-loading time, and is never re-checked after a "
        "run.",
        "",
        "| Rule | CUAD category | Documents with a span | Spans | Certified Negative documents | "
        "Gate |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for count in corpus.gate:
        lines.append(
            f"| {count.rule_id} | {count.cuad_category} | {count.documents_with_spans} | "
            f"{count.spans} | {count.certified_negative_documents} | "
            f"{'pass' if count.passes_gate else 'FAIL'} |"
        )
    lines.append("")
    lines.append(
        f"{'All seven Rules pass' if corpus.gate_passes else 'Not every Rule passes'} the gate. "
        "A Certified Negative document is one CUAD flags as having no such clause anywhere, so "
        "every Clause in it is a verified negative for that Rule."
    )
    lines.append("")
    lines.append(
        "The Detection Questions below are **drafted and awaiting the user's review in ticket "
        "08**, which is a human checkpoint before any real run:"
    )
    lines.append("")
    for rule in RULEBOOK:
        lines.append(f'- **{rule.id}** — _"{rule.detection_question}"_')
    lines.append("")

    for count in corpus.dropped:
        reason = DROPPED_REASONS.get(count.rule_id, "")
        lines.append(
            f"**Dropped: {count.cuad_category} ({count.rule_id}).** It is absent from the Rulebook "
            f"and never asked. ADR-0005 dropped it as the Rule failing the gate, at 16 documents "
            f"and 23 spans — but that was measured before Pacira joined the corpus. Over all "
            f"{CORPUS_DOCUMENTS} documents it measures **{count.documents_with_spans} documents "
            f"and {count.spans} spans**, which "
            f"{'passes' if count.passes_gate else 'still fails'} the gate"
            f"{' by one span' if count.passes_gate and count.spans == GATE_MIN_SPANS + 1 else ''}. "
            f"It stays dropped on the other ground ADR-0005 gives. {reason}"
        )
        lines.append("")

    category = {rule.id: rule.cuad_category for rule in RULEBOOK}
    replaced = ", ".join(
        f"{rule_id} ({category[rule_id]}) replaced {former}"
        for rule_id, former in REPLACED_RULES.items()
    )
    lines.append(
        f"**Two Rules changed meaning** from the earlier notes: {replaced}, both because the "
        "originals had too few documents. Their results must not be compared to the old rules."
    )
    lines.append("")
    lines.append(
        "The surviving Rules were chosen partly for having clean definitions, which will make "
        "these results read optimistically (ADR-0005)."
    )
    lines.append("")
    return lines


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
    lines.append(
        f"The Corpus and Rulebook sections below describe the whole License Agreement Set and are "
        f"counted from CUAD over all {inputs.corpus.documents} documents. Everything from "
        f'"Documents scored in this run" onwards covers only the '
        f"{len(inputs.documents)} document(s) and {len(inputs.rules)} Rule(s) this run scored."
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

    lines.extend(_corpus_section(inputs.corpus))
    lines.extend(_rulebook_section(inputs.corpus))

    lines.append("## Documents scored in this run")
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
