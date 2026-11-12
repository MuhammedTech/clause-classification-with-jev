"""The tracer bullet: one command's worth of work, from the corpus to the written report.

Every stage of the spec runs here — Corpus, Splitter, Rulebook, Jev client, Jev runner, Evaluator,
Report — so later tickets deepen a pipeline that already runs end to end.

The Jev client is injected rather than constructed here, which is what lets the tests count its
calls and interrupt it.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from . import config
from .corpus import corpus_facts, load_corpus
from .domain import Clause, Highlight
from .evaluator import FullyBinned, RuleMetrics, evaluate_rule, fully_binned
from .jev import JevClient, StubJevClient
from .partition import partition_facts
from .report import DocumentSummary, ReportInputs, render
from .rulebook import Rule, rule
from .runner import RunStats, run_pairs
from .splitter import split_document

#: The tracer documents: two with R1 Highlights, so the recall denominators are not empty, and one
#: CUAD certifies as having no such clause anywhere. All three are documents the ticket 01 splitter
#: partitions sensibly (median 31 to 72 words a Clause, none over 600), so the tracer exercises the
#: pipeline rather than the splitter's weak spot. See `docs/cuad-ground-truth.md` on the documents
#: whose pages collapse to one line.
TRACER_DOC_IDS = (
    "WebmdHealthCorp_20050908_S-1A_EX-10.7_1027007_EX-10.7_Content License Agreement",
    "SPARKLINGSPRINGWATERHOLDINGSLTD_07_03_2002-EX-10.13-SOFTWARE LICENSE AND MAINTENANCE AGREEMENT",
    "DataCallTechnologies_20060918_SB-2A_EX-10.9_944510_EX-10.9_Content License Agreement",
)

DEFAULT_CUTOFF = 0.5

#: Ticket 01 scores one Rule. The other six arrive with the full run.
DEFAULT_RULE_IDS = ("R1",)


@dataclass(frozen=True)
class RunResult:
    """What one run produced, so a caller can assert on it without re-reading the Markdown."""

    report_path: Path
    cache_path: Path
    markdown: str
    metrics: tuple[RuleMetrics, ...]
    fully_binned: FullyBinned
    stats: RunStats
    clauses: tuple[Clause, ...]
    highlights: tuple[Highlight, ...]


def run(
    client: JevClient | None = None,
    doc_ids: Sequence[str] = TRACER_DOC_IDS,
    rule_ids: Sequence[str] = DEFAULT_RULE_IDS,
    cutoff: float = DEFAULT_CUTOFF,
    out_dir: Path | None = None,
    cuad_directory: Path | None = None,
) -> RunResult:
    """Take the documents through every stage and write the report."""
    client = client if client is not None else StubJevClient()
    out_dir = Path(out_dir or config.DEFAULT_OUT_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)

    rules: list[Rule] = [rule(rule_id) for rule_id in rule_ids]

    documents = load_corpus(rules=rules, doc_ids=doc_ids, directory=cuad_directory)

    clauses: list[Clause] = []
    highlights: list[Highlight] = []
    certified_by_rule: dict[str, set[str]] = {r.id: set() for r in rules}
    doc_rows: list[DocumentSummary] = []
    for document in documents:
        document_clauses = split_document(document.doc_id, document.text)
        clauses.extend(document_clauses)
        highlights.extend(document.highlights)
        for r in rules:
            if document.is_certified_negative(r.id):
                certified_by_rule[r.id].add(document.doc_id)
        doc_rows.append(
            DocumentSummary(
                doc_id=document.doc_id,
                clauses=len(document_clauses),
                words=sum(c.word_count for c in document_clauses),
            )
        )

    cache_path = out_dir / "pyes.jsonl"
    table, stats = run_pairs(clauses, rules, client, cache_path)

    metrics = tuple(
        evaluate_rule(
            rule_id=r.id,
            clauses=clauses,
            highlights=[h for h in highlights if h.rule_id == r.id],
            p_yes=table[r.id],
            cutoff=cutoff,
            certified_negative_docs=certified_by_rule[r.id],
        )
        for r in rules
    )
    fully = fully_binned(clauses, table, cutoff)

    markdown = render(
        ReportInputs(
            rules=rules,
            metrics=metrics,
            fully_binned=fully,
            stats=stats,
            cutoff=cutoff,
            model_version=client.model_version,
            documents=doc_rows,
            is_stub=client.is_stub,
            # Corpus-wide and counted from CUAD, so it does not depend on which documents or
            # Rules this run scored: the gate is a statement about the available ground truth.
            corpus=corpus_facts(directory=cuad_directory),
            # Also corpus-wide: every document is split, with all seven Rules' Highlights, so a
            # document this run did not score still shows how well it partitions. No Jev calls.
            partition=partition_facts(load_corpus(directory=cuad_directory)),
        )
    )

    report_path = out_dir / "report.md"
    report_path.write_text(markdown, encoding="utf-8")

    return RunResult(
        report_path=report_path,
        cache_path=cache_path,
        markdown=markdown,
        metrics=metrics,
        fully_binned=fully,
        stats=stats,
        clauses=tuple(clauses),
        highlights=tuple(highlights),
    )
