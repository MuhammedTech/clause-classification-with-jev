"""The Report: renders the Evaluator's output to Markdown, counts first.

Ticket 01's report is one table for R1 at one fixed Cutoff. The Cutoff Curve, the charts and the
full "How this is measured" sections arrive in ticket 05.

Every figure here is stub-derived and labelled as such: the stub's P(yes) values are a hash of its
inputs and carry no signal, so nothing in this report says anything about how Jev would behave.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .corpus import GATE_MIN_DOCUMENTS, GATE_MIN_HIGHLIGHTS, CorpusFacts, RuleCounts
from .evaluator import RuleMetrics
from .partition import PartitionFacts
from .rulebook import (
    DROPPED_REASONS,
    QUESTION_TYPE,
    REPLACED_RULES,
    RULEBOOK,
    SUPERSEDED_GATE_COUNTS,
    Rule,
    rule as lookup_rule,
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
    partition: PartitionFacts


def _format_share(value: float | None) -> str:
    """Render a share, or "n/a" where the denominator was empty."""
    return "n/a" if value is None else f"{value * 100:.1f}%"


def _count_pair(numerator: int, denominator: int) -> str:
    return f"{numerator}/{denominator}"


def _corpus_section(corpus: CorpusFacts) -> list[str]:
    """How the corpus was chosen, and the join one of its documents needs."""
    filters = corpus.filters
    return [
        "## Corpus",
        "",
        f"The **License Agreement Set** is the {filters.csv_document_name} rows of "
        '`master_clauses.csv` whose `Document Name` contains "licen". Two other filters give a '
        "different set and are not the one used, which is why earlier notes disagree on the size:",
        "",
        "| Filter | Documents |",
        "| --- | --- |",
        f'| CSV `Document Name` contains "licen" | {filters.csv_document_name} |',
        f'| CSV `Filename` contains "licen" | {filters.csv_filename} |',
        f'| JSON `title` contains "licen" | {filters.json_title} |',
        "",
        "The JSON carries no `Document Name` field, so each CSV row is joined to `CUAD_v1.json` by "
        "comparing `Filename` against the JSON `title`: the `.pdf` / `.txt` extension stripped, "
        "then compared on **alphanumerics only, lowercased**. With that normalisation all "
        f"{filters.csv_document_name} resolve. Without it exactly one fails — PACIRA "
        "PHARMACEUTICALS, whose filename says `A&R` where the title says `A_R`.",
        "",
        f"Graded text is the JSON `context`, the same string the Highlight offsets are measured "
        f"against: **{corpus.documents} documents**, {corpus.characters:,} characters, "
        f"{corpus.highlights} Highlights across the seven Rules. Every one of those offsets lands "
        "exactly on the text it marks, so character-range overlap is a sound label (ADR-0004).",
        "",
    ]


def _margin_phrase(count: RuleCounts) -> str:
    """How far a Rule clears the gate's Highlight minimum, when that is worth saying."""
    margin = count.highlight_margin
    if not count.passes_gate or margin > 2:
        return ""
    return " by one Highlight" if margin == 1 else f" by {margin} Highlights"


def _dropped_rule_paragraph(count: RuleCounts, corpus_documents: int) -> list[str]:
    """One dropped Rule: what it measures now, what ADR-0005 recorded, and why it stays out.

    Both figures come from data — the live count from CUAD, the old one from
    `SUPERSEDED_GATE_COUNTS` — so this paragraph states no number of its own.
    """
    was = SUPERSEDED_GATE_COUNTS.get(count.rule_id)
    reason = DROPPED_REASONS.get(count.rule_id, "")

    lines = [
        f"**Dropped: {count.cuad_category} ({count.rule_id}).** It is absent from the Rulebook and "
        f"never asked, and it has no Detection Question: wording is drafted only for Rules that "
        f"are asked. Over all {corpus_documents} documents it measures "
        f"**{count.documents_with_highlights} documents and {count.highlights} Highlights**, "
        f"which {'passes' if count.passes_gate else 'fails'} the gate{_margin_phrase(count)}."
    ]
    if was is not None:
        lines.append("")
        lines.append(
            f"ADR-0005 recorded {was.documents} documents and {was.highlights} Highlights and "
            f"dropped it partly for failing the gate. That measurement is superseded — "
            f"{was.why_it_changed} — so **the gate is not a reason to drop this Rule**, and the "
            f"report does not give it as one."
        )
    if reason:
        lines.append("")
        lines.append(f"It stays dropped on the ground that survives the correction. {reason}")
    lines.append("")
    return lines


def _rulebook_section(corpus: CorpusFacts) -> list[str]:
    """The seven Rules, their ground-truth counts, the gate, and what was dropped and renamed."""
    lines = [
        "## Rulebook and the gate",
        "",
        "Seven Rules, each mapped to one CUAD category and asked as one positively phrased "
        "Detection Question (ADR-0005). The **gate** asks for at least "
        f"{GATE_MIN_DOCUMENTS} documents carrying a Highlight and at least "
        f"{GATE_MIN_HIGHLIGHTS} Highlights; below either, the denominators are too thin to read a "
        "curve off.",
        "",
        "These counts come from CUAD's own annotations and **not from the Splitter**, so they do "
        "not move when the partition changes. The gate is therefore settled once, over all "
        f"{corpus.documents} documents at corpus-loading time, and is never re-checked after a "
        "run.",
        "",
        "| Rule | CUAD category | Documents with a Highlight | Highlights | "
        "Certified Negative documents | Gate |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for count in corpus.gate:
        lines.append(
            f"| {count.rule_id} | {count.cuad_category} | {count.documents_with_highlights} | "
            f"{count.highlights} | {count.certified_negative_documents} | "
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
        lines.extend(_dropped_rule_paragraph(count, corpus.documents))

    replaced = ", ".join(
        f"{rule_id} ({lookup_rule(rule_id).cuad_category}) replaced {former}"
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


def _partition_section(partition: PartitionFacts) -> list[str]:
    """How the Splitter cut the whole corpus, with the per-document share so a bad split shows.

    Corpus-wide on purpose: the documents a run scores may be the ones that split cleanly.
    """
    ceiling = partition.word_ceiling
    lines = [
        "## Partition",
        "",
        f"The Splitter cut **all {len(partition.documents)} documents**, whichever of them this run "
        "scored, so the documents it handles badly are visible here (ADR-0004). Every character of "
        "each document lands in exactly one Clause, and a Clause over the Word Ceiling is split "
        f"again at paragraph breaks, then line breaks, sentence ends and word breaks, until none is "
        f"over **{ceiling} words**.",
        "",
        "| | |",
        "| --- | --- |",
        f"| Clauses | {partition.clauses} |",
        f"| Words in Clauses | {partition.words} |",
        f"| Median Clause | {partition.median_clause_words:g} words |",
        f"| Mean Clause | {partition.mean_clause_words:.1f} words |",
        f"| 90th percentile Clause | {partition.p90_clause_words} words |",
        f"| Largest Clause | {partition.largest_clause_words} words |",
        f"| Clauses over the Word Ceiling | {partition.over_ceiling} |",
        "",
        f"**Highlights inside exactly one Clause:** {partition.single_clause_highlights} of "
        f"{partition.highlights} ({_format_share(partition.single_clause_share)}). This is a "
        "reported number and not a build gate: it is what the data gives, and gating on it would "
        "pressure the Splitter to stop separating sub-items (ADR-0004). The rest are held by "
        "several Clauses, which is why Provision Recall can exceed Clause Recall.",
        "",
        f"**Parent Line context.** {partition.clauses_with_parent_line} of {partition.clauses} "
        f"Clauses carry a Parent Line, adding {partition.parent_line_words} words to the "
        f"{partition.words} words of Clause text: **{_format_share(partition.parent_line_growth)} "
        f"more words** for Jev to read per Rule. The largest Parent Line is "
        f"{partition.largest_parent_line_words} words, because in documents where a whole page is "
        "one line the first line of an item can be that long. Growth is counted in words: there is "
        "no tokenizer here, and token counts belong to the cost estimate (ticket 06).",
        "",
        "| Document | Clauses | Words | Largest Clause | Highlights | Inside one Clause | Share |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for document in partition.documents:
        lines.append(
            f"| {document.doc_id} | {document.clauses} | {document.words} | "
            f"{document.largest_clause_words} | {document.highlights} | "
            f"{document.single_clause_highlights} | "
            f"{_format_share(document.single_clause_share)} |"
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
    lines.extend(_partition_section(inputs.partition))

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
