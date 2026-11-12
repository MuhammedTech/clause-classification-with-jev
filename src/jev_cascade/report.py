"""The Report: renders the Evaluator's output to Markdown, counts first.

The report opens with a per-Rule summary, then says how it is measured, describes the corpus, the
Rulebook and the partition, and gives each Rule its fixed-Cutoff figures, its free saving and its
Cutoff Curve with a chart. It closes with how to read the curve, what is not measured and the vendor
caveats.

While Jev is the stub, every figure is labelled as stub-derived: the stub's P(yes) values are a
hash of its inputs and carry no signal, so nothing in the report says anything about how Jev would
behave.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from . import config
from .corpus import GATE_MIN_DOCUMENTS, GATE_MIN_HIGHLIGHTS, CorpusFacts, RuleCounts
from .cost import CostReport
from .evaluator import FreeSaving, FullyBinned, RuleMetrics
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
class RuleCurve:
    """One Rule's Cutoff Curve and where its files were written, relative to the report."""

    rule_id: str
    #: One row per distinct observed P(yes), lowest first. The complete curve.
    rows: tuple[RuleMetrics, ...]
    saving: FreeSaving | None
    chart: str
    csv: str


@dataclass(frozen=True)
class ReportInputs:
    """Everything the report prints, so rendering stays a pure function of its inputs."""

    rules: Sequence[Rule]
    metrics: Sequence[RuleMetrics]
    fully_binned: FullyBinned
    curves: Sequence[RuleCurve]
    cost: CostReport
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
        "different set and are not the one used, which is why earlier notes disagree on the size. "
        f"The {filters.csv_filename} comes from the `Filename` column and the "
        f"{filters.json_title} from the JSON `title`, so neither is the "
        f"{filters.csv_document_name}:",
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


#: How many rows of a curve the Markdown prints before it excerpts. The CSV always holds them all.
CURVE_EXCERPT_ROWS = 25


def _stub_label(inputs: ReportInputs) -> list[str]:
    """The line that sits before every table of scored figures while Jev is the stub."""
    if not inputs.is_stub:
        return []
    return [
        "_Stub-derived: the stub's P(yes) values carry no signal, so these figures say nothing "
        "about Jev._",
        "",
    ]


def _summary_section(inputs: ReportInputs) -> list[str]:
    """The opening: per Rule, counts first, then the free saving, then the one saving that is money."""
    cutoff = inputs.cutoff
    lines = [
        "## Summary",
        "",
        "Per Rule, counts first. The headline is the lowest P(yes) Jev gave to any Clause holding a "
        "Highlight, and the share of contract words that can be Binned strictly below it: the free "
        "saving, because no Highlight is Lost there. It is read off the curve after seeing it, so it "
        "is a headline and not a tuned Cutoff.",
        "",
    ]
    lines.extend(_stub_label(inputs))
    lines.extend(
        [
            "| Rule | Clauses holding a Highlight | Highlights | Lowest P(yes) of a holding Clause | "
            "Words Binned below it | Binned Share below it |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for rule, curve in zip(inputs.rules, inputs.curves):
        saving = curve.saving
        if saving is None:
            lines.append(f"| {rule.id} — {rule.cuad_category} | 0 | 0 | n/a | n/a | n/a |")
            continue
        metrics = saving.metrics
        lines.append(
            f"| {rule.id} — {rule.cuad_category} | "
            f"{_count_pair(metrics.holding_clauses, saving.clauses)} Clauses | "
            f"{metrics.highlights} | {saving.lowest_held_p_yes:g} | "
            f"{_count_pair(saving.binned_words, saving.total_words)} words | "
            f"{_format_share(saving.binned_share)} |"
        )
    lines.append("")

    fully = inputs.fully_binned
    asked = len(inputs.rules)
    lines.append(
        f"**Fully Binned Clauses** at the fixed Cutoff of {cutoff:g}: "
        f"{_count_pair(fully.fully_binned_clauses, fully.clauses)} Clauses "
        f"({_format_share(fully.clause_share)}) are Binned for every Rule asked in this run "
        f"({asked} Rule{'s' if asked != 1 else ''}). It is the only saving that turns into money, "
        "and the per-Rule Binned Share above does not combine into it."
    )
    lines.append("")
    return lines


def _usd(value: float | None) -> str:
    """Dollars to three places, because Jev's part is a few cents per 1,000 Clauses."""
    if value is None:
        return "n/a"
    sign = "-" if value < 0 else ""
    return f"{sign}${abs(value):,.3f}"


def _sourced_row(label: str, item: config.Sourced, shown: str) -> str:
    return f"| {label} | {shown} | {item.unit} | {item.source} | {item.as_of} |"


def _cost_section(inputs: ReportInputs) -> list[str]:
    """What the cascade would save and how long Jev takes, estimated from token counts."""
    cost = inputs.cost
    usage = cost.usage
    asked = usage.rules
    rules = f"{asked} Rule{'s' if asked != 1 else ''}"
    lines = [
        "## Cost and time",
        "",
        "How much the cascade could save, and how fast Jev is, per 1,000 Clauses. No expensive "
        "model is run, so every dollar figure is an **estimate** from token counts at list "
        "prices, and the token counts are themselves estimated from character length (there is "
        "no tokenizer in the code). Treat the figures as an order of magnitude, not a quote.",
        "",
        f"Priced over this run's {usage.clauses:,} Clauses and {rules}, then scaled to 1,000. "
        "The baseline is the expensive model alone: one call per Clause carrying every Rule "
        "asked. The cascade's expensive part is one call per Clause Escalated for at least one "
        "Rule, sized to only its Escalated questions; a Fully Binned Clause gets no call. Jev is "
        "charged for every Pair at input price, and is not batched.",
        "",
    ]
    lines.extend(_stub_label(inputs))

    header = ["Per 1,000 Clauses"]
    for model, batch, _ in cost.figures:
        header.append(f"{model.name} batch" if batch else model.name)
    lines.append("| " + " | ".join(header) + " |")
    lines.append("| " + " | ".join(["---"] * len(header)) + " |")

    def figure_row(label: str, pick) -> None:
        cells = [_usd(f.per_1000(pick(f))) for _, _, f in cost.figures]
        lines.append(f"| {label} | " + " | ".join(cells) + " |")

    figure_row("Expensive model alone", lambda f: f.alone_usd)
    figure_row("Cascade: expensive part", lambda f: f.cascade_usd)
    figure_row("Cascade: Jev part", lambda f: f.jev_usd)
    figure_row("Net savings", lambda f: f.net_usd)
    shares = [
        _format_share(f.net_usd / f.alone_usd) if f.alone_usd else "n/a"
        for _, _, f in cost.figures
    ]
    lines.append("| Saved, share of the baseline | " + " | ".join(shares) + " |")
    lines.append("")

    lines.append(
        "Net savings are the baseline less the cascade's expensive part less Jev, so they can be "
        "negative. **Savings track the Fully Binned Clause share, not per-Rule Binned Share**: "
        f"{_count_pair(usage.fully_binned_clauses, usage.clauses)} Clauses "
        f"({_format_share(inputs.fully_binned.clause_share)}) are Fully Binned here, and a Clause "
        "Binned for all but one Rule still costs a call."
    )
    lines.append("")

    lines.append("| Calls and tokens | Calls | Input tokens | Output tokens |")
    lines.append("| --- | --- | --- | --- |")
    for label, totals in (
        ("Expensive calls, model alone", usage.alone),
        ("Cascade expensive calls", usage.cascade),
        ("Jev calls", usage.jev),
    ):
        lines.append(
            f"| {label} | {totals.calls:,} | {totals.input_tokens:,} | {totals.output_tokens:,} |"
        )
    lines.append("")
    lines.append(
        "The expensive model's output tokens are counted, at the assumed output per question "
        "asked below. Jev's answer is one probability, so its output is taken as free."
    )
    lines.append("")

    time = cost.time
    if time.seconds_per_1000_clauses is None:
        measured = "n/a (every answer came from the cache, so no Jev call was timed)"
    else:
        stub = " (stub timing)" if inputs.is_stub else ""
        measured = f"{time.seconds_per_1000_clauses:,.1f}s{stub}"
    lines.append("### Jev time")
    lines.append("")
    if inputs.is_stub:
        lines.append(
            "_Stub timing: the stub answers instantly, so the measured figure says nothing about "
            "Jev's latency._"
        )
        lines.append("")
    lines.append("| Per 1,000 Clauses | |")
    lines.append("| --- | --- |")
    lines.append(f"| Jev calls | {time.calls_per_1000_clauses:,} |")
    lines.append(f"| Jev wall clock, measured | {measured} |")
    lines.append(
        f"| Jev time at the published rate limit | "
        f"{time.minutes_per_1000_clauses_at_rate_limit:,.2f} minutes "
        f"({time.calls_per_1000_clauses:,} calls at "
        f"{config.JEV_RATE_LIMIT_PER_MINUTE.value:,.0f} a minute) |"
    )
    lines.append("")

    full = cost.full_run
    lines.append("### The full run")
    lines.append("")
    lines.append(
        "Asking Jev every Pair of the whole corpus, no expensive model, counted from the "
        "documents with their Parent Lines. Not stub-derived: it needs no P(yes). It replaces "
        "the roughly $0.20 the spec carried, which was never recomputed after Parent Lines added "
        "about 16% more words per call."
    )
    lines.append("")
    lines.append("| | |")
    lines.append("| --- | --- |")
    lines.append(f"| Clauses, all 53 documents | {full.clauses:,} |")
    lines.append(f"| Rules in the Rulebook | {full.rules} |")
    lines.append(f"| Jev calls for the full run | {full.calls:,} |")
    lines.append(f"| Jev input tokens, estimated | {full.jev_input_tokens:,} |")
    lines.append(f"| Jev cost, estimated | {_usd(full.jev_usd)} |")
    lines.append(
        f"| Full run time at the published rate limit | {full.minutes_at_rate_limit:,.1f} minutes |"
    )
    lines.append("")

    lines.append("### Prices and assumptions")
    lines.append("")
    lines.append(
        "Every number the cost model uses, from `config.py`. The last three are assumptions, not "
        "prices; the output per question is the softest number in the table."
    )
    lines.append("")
    lines.append("| Item | Value | Unit | Source | As of |")
    lines.append("| --- | --- | --- | --- | --- |")
    for model in config.EXPENSIVE_MODELS:
        lines.append(_sourced_row(f"{model.name} input", model.input, f"${model.input.value:g}"))
        lines.append(_sourced_row(f"{model.name} output", model.output, f"${model.output.value:g}"))
    priced = (
        ("Batch discount", config.BATCH_DISCOUNT, "{:g}"),
        ("Jev input price", config.JEV_INPUT_PRICE, "${:g}"),
        ("Jev rate limit", config.JEV_RATE_LIMIT_PER_MINUTE, "{:,.0f}"),
        ("Characters per token", config.CHARS_PER_TOKEN, "{:g}"),
        ("Expensive call overhead", config.EXPENSIVE_OVERHEAD_TOKENS, "{:,.0f}"),
        (
            "Expensive output per question",
            config.EXPENSIVE_OUTPUT_TOKENS_PER_QUESTION,
            "{:,.0f}",
        ),
    )
    for label, item, template in priced:
        lines.append(_sourced_row(label, item, template.format(item.value)))
    lines.append("")
    lines.append(
        "Jev's tokenizer and Claude's differ, so one characters-per-token figure covers both only "
        "roughly. The baseline and the cascade share every assumption, so the share saved is "
        "steadier than the dollars."
    )
    lines.append("")
    return lines


def _how_measured_section() -> list[str]:
    return [
        "## How this is measured",
        "",
        "- **Highlights are the only ground truth.** A Highlight is a span of text a CUAD lawyer "
        "marked as an instance of a category. No other model's opinion is used to grade anything.",
        "- **A Clause holds a Highlight when their character ranges overlap by one character or "
        "more.** No overlap threshold, no word minimum: the offsets are exact (ADR-0004).",
        "- **Clause Recall against Provision Recall.** Clause Recall asks of the Clauses that hold a "
        "Highlight how many are Escalated. Provision Recall asks of the Highlights how many have at "
        "least one holding Clause Escalated. A Highlight that spans several Clauses is lost only "
        "when all of them are Binned, so Provision Recall is never below Clause Recall.",
        "- **Certified against Inferred Negatives.** A Clause holding nothing is a Certified "
        "Negative when CUAD flags its document as having no such clause anywhere, and an Inferred "
        "Negative when the document has Highlights for the Rule elsewhere. The false-alarm rate is "
        "counted on Certified Negatives alone, since those are verified.",
        "- **Binned Share is measured in words**, so it does not depend on where the Splitter cuts.",
        "- **The Cutoff is swept, never chosen.** A Pair at or below it is Binned and above it "
        "Escalated. The curve has one row at every P(yes) Jev actually gave, because the piles only "
        "change when the Cutoff crosses one. Nothing is fitted, so nothing can overfit. Any single "
        "figure quoted from the curve was picked after seeing it, and the report says so where it "
        "quotes one.",
        "",
    ]


def _curve_excerpt(rows: Sequence[RuleMetrics]) -> list[RuleMetrics]:
    """Every row if the curve is short, else evenly spaced by position, first and last included.

    Chosen by position and never by outcome, so the excerpt cannot flatter the curve.
    """
    if len(rows) <= CURVE_EXCERPT_ROWS:
        return list(rows)
    last = len(rows) - 1
    positions = sorted({round(i * last / (CURVE_EXCERPT_ROWS - 1)) for i in range(CURVE_EXCERPT_ROWS)})
    return [rows[i] for i in positions]


def _curve_block(inputs: ReportInputs, curve: RuleCurve) -> list[str]:
    """One Rule's free saving, the curve excerpt and the chart."""
    lines: list[str] = []
    saving = curve.saving
    if saving is None:
        lines.append(
            "**Free saving.** No Clause holds a Highlight for this Rule in the documents scored, so "
            "there is no score to stay below."
        )
    else:
        doc_id, span = saving.lowest_held_clause
        stub = "_Stub-derived._ " if inputs.is_stub else ""
        lines.append(
            f"**Free saving.** {stub}The lowest P(yes) Jev gave a Clause holding a Highlight is "
            f"**{saving.lowest_held_p_yes:g}**, given to the Clause at characters {span} of "
            f"{doc_id}. Strictly below it "
            f"{saving.binned_clauses} of {saving.clauses} Clauses are Binned, which is "
            f"{_count_pair(saving.binned_words, saving.total_words)} words "
            f"(**{_format_share(saving.binned_share)}**), and {saving.lost_provisions} Highlights "
            "are Lost. This was read off the curve after seeing it."
        )
    lines.append("")
    lines.append(f"### {curve.rule_id} Cutoff Curve")
    lines.append("")
    excerpt = _curve_excerpt(curve.rows)
    lines.append(
        f"The complete curve has {len(curve.rows)} rows, one per distinct P(yes), in "
        f"[`{curve.csv}`]({curve.csv}). This table shows {len(excerpt)} of them"
        f"{', chosen by position' if len(excerpt) < len(curve.rows) else ''}."
    )
    lines.append("")
    lines.extend(_stub_label(inputs))
    lines.append(
        "| Cutoff | Binned Clauses | Escalated Clauses | Clause Recall | Provision Recall | "
        "Precision | Lost Provisions | Binned Share |"
    )
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
    for row in excerpt:
        lines.append(
            f"| {row.cutoff:g} | {row.binned_clauses} | {row.escalated_clauses} | "
            f"{_count_pair(row.holding_escalated, row.holding_clauses)} "
            f"({_format_share(row.clause_recall)}) | "
            f"{_count_pair(row.highlights - row.lost_provisions, row.highlights)} "
            f"({_format_share(row.provision_recall)}) | "
            f"{_count_pair(row.holding_escalated, row.escalated_clauses)} "
            f"({_format_share(row.precision)}) | "
            f"{row.lost_provisions}/{row.highlights} | "
            f"{_count_pair(row.binned_words, row.total_words)} words "
            f"({_format_share(row.binned_share)}) |"
        )
    lines.append("")
    lines.append(f"![{curve.rule_id} Cutoff Curve]({curve.chart})")
    lines.append("")
    return lines


def _reading_section(inputs: ReportInputs) -> list[str]:
    """The two ways to read the curve, each named, with Precision never passed off as accuracy."""
    lines = [
        "## Reading the curve",
        "",
        "The same curve is read two ways, and mixing them up is the commonest mistake.",
        "",
        "- **The classifier reading, at a Cutoff around 0.5.** Jev's P(yes) is treated as a yes/no "
        f"answer. Recall and Precision mean what they usually mean. This run's fixed Cutoff is "
        f"{inputs.cutoff:g}, and the classifier rows below are read there.",
        "- **The cascade reading, at the low end.** The Cutoff sits just under the lowest P(yes) of "
        "any holding Clause, so almost everything is Escalated and Precision is low by design. "
        "Escalated here means Jev could not rule the Clause out, not that it detected anything. The "
        "figure to read is Binned Share, the saving.",
        "",
        "**Quoting Precision at a low Cutoff as Jev's accuracy would be wrong.** At a base rate near "
        "1%, Escalating every Clause already scores exactly the base rate, so a Precision in single "
        "digits is what the arithmetic gives, not Jev failing.",
        "",
    ]
    lines.extend(_stub_label(inputs))
    lines.append(
        "| Rule | Reading | Cutoff | Clause Recall | Provision Recall | Precision | Binned Share |"
    )
    lines.append("| --- | --- | --- | --- | --- | --- | --- |")

    def cells(m: RuleMetrics) -> str:
        return (
            f"{_count_pair(m.holding_escalated, m.holding_clauses)} "
            f"({_format_share(m.clause_recall)}) | "
            f"{_count_pair(m.highlights - m.lost_provisions, m.highlights)} "
            f"({_format_share(m.provision_recall)}) | "
            f"{_count_pair(m.holding_escalated, m.escalated_clauses)} "
            f"({_format_share(m.precision)}) | "
            f"{_count_pair(m.binned_words, m.total_words)} words ({_format_share(m.binned_share)})"
        )

    for metric, curve in zip(inputs.metrics, inputs.curves):
        lines.append(f"| {metric.rule_id} | classifier reading | {metric.cutoff:g} | {cells(metric)} |")
        saving = curve.saving
        if saving is not None:
            lines.append(
                f"| {metric.rule_id} | cascade reading | just under {saving.lowest_held_p_yes:g} | "
                f"{cells(saving.metrics)} |"
            )
    lines.append("")
    lines.append(
        "The classifier row is at the fixed Cutoff this run was given, which is not tuned. The "
        "cascade row is at the point the curve itself marks, read after seeing it."
    )
    lines.append("")
    return lines


def _vendor_caveats_section() -> list[str]:
    return [
        "## Vendor caveats",
        "",
        "- TypeSafe's calibration evaluations of Jev were self-run: published by the vendor, not "
        "reproduced by anyone else, and not checked here.",
        "- TypeSafe documents a prompt-injection limitation. Jev reads the Clause inside its "
        "question, so text in a Clause that reads like an instruction could in principle steer the "
        "answer. This report does not test for it.",
        "- Jev's probabilities depend on how the question is asked: the same question put as a "
        "different question type has given very different probabilities elsewhere. The question "
        "type and wording are settled in ticket 08, before the real run.",
        "",
    ]


def render(inputs: ReportInputs) -> str:
    """Render the tracer-bullet report."""
    label = "stub" if inputs.is_stub else inputs.model_version
    lines: list[str] = []

    lines.append("# Jev cascade report")
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

    lines.extend(_summary_section(inputs))

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

    lines.extend(_how_measured_section())
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

    for rule, metric, curve in zip(inputs.rules, inputs.metrics, inputs.curves):
        lines.append(f"## {rule.id} — {rule.cuad_category}")
        lines.append("")
        lines.append(f'Detection Question: _"{rule.detection_question}"_')
        lines.append("")
        lines.append(f"At the fixed Cutoff of {metric.cutoff:g}, counts first:")
        lines.append("")
        lines.extend(_stub_label(inputs))
        lines.append("| Figure | Counts | Share |")
        lines.append("| --- | --- | --- |")
        lines.append(
            f"| Clause Recall | {_count_pair(metric.holding_escalated, metric.holding_clauses)} "
            f"holding Clauses Escalated | {_format_share(metric.clause_recall)} |"
        )
        lines.append(
            f"| Precision | {_count_pair(metric.holding_escalated, metric.escalated_clauses)} "
            f"Escalated Clauses hold a Highlight; base rate "
            f"{_count_pair(metric.holding_clauses, metric.clauses)} Clauses "
            f"({_format_share(metric.base_rate)}) | {_format_share(metric.precision)} |"
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
        lines.append(
            f"| False-alarm rate on Certified Negative documents | "
            f"{_count_pair(metric.certified_negative_escalated, metric.certified_negative_clauses)} "
            f"Clauses Escalated, in documents CUAD certifies hold no such clause | "
            f"{_format_share(metric.false_alarm_rate)} |"
        )
        lines.append("")
        lines.append(
            f"Supporting counts: {metric.clauses} Clauses, {metric.binned_clauses} Binned and "
            f"{metric.escalated_clauses} Escalated; {metric.holding_clauses} hold a Highlight; "
            f"{metric.certified_negative_clauses} Certified Negative and "
            f"{metric.inferred_negative_clauses} Inferred Negative Clauses hold none."
        )
        lines.append("")
        lines.append(
            "Precision reads in single digits by arithmetic at a base rate near 1%: Escalating "
            "every Clause would score exactly the base rate printed beside it, so a low "
            "Precision is not by itself Jev performing badly. Always read it beside its counts. "
            "The false-alarm rate is a separate figure on a separate denominator, resting on "
            "CUAD's explicit negatives alone with no Inferred Negative in it."
        )
        lines.append("")
        lines.extend(_curve_block(inputs, curve))

    fully = inputs.fully_binned
    asked = len(inputs.rules)
    lines.append("## Fully Binned Clauses")
    lines.append("")
    lines.append(
        f"A Fully Binned Clause is Binned for every Rule asked in this run ({asked} "
        f"Rule{'s' if asked != 1 else ''}), so the expensive model is never called on it. It is "
        "the only saving that turns into money: per-Rule Binned Share does not combine into it."
    )
    lines.append("")
    lines.extend(_stub_label(inputs))
    lines.append("| Figure | Counts | Share |")
    lines.append("| --- | --- | --- |")
    lines.append(
        f"| Fully Binned Clauses | {_count_pair(fully.fully_binned_clauses, fully.clauses)} "
        f"Clauses | {_format_share(fully.clause_share)} |"
    )
    lines.append(
        f"| Fully Binned words | {_count_pair(fully.fully_binned_words, fully.total_words)} "
        f"words | {_format_share(fully.word_share)} |"
    )
    lines.append("")

    lines.extend(_cost_section(inputs))

    lines.extend(_reading_section(inputs))

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
        "everything would score 99% accuracy, and ROC AUC flatters a rare problem the same way "
        "(ADR-0003). Recall and Precision, with their counts, are reported instead."
    )
    lines.append("")

    lines.extend(_vendor_caveats_section())

    return "\n".join(lines)
