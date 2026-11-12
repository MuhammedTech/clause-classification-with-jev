"""Partition statistics: how well the Splitter cut the corpus, measured so a bad split is visible.

ADR-0004 keeps all 53 documents, including the ones a line-start splitter handles badly, on the
condition that the damage shows up in the reported statistics instead of silently skewing results.
This module is where it shows up. It is **corpus-wide by design**: the tracer documents were chosen
because they split cleanly, so statistics over them alone would hide exactly the documents worth
seeing.

Everything is a pure function of the Documents. Context growth is counted in **words**: this project
has no tokenizer, and token counts belong to ticket 06.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

from .corpus import Document
from .domain import Clause, holds
from .splitter import WORD_CEILING, split_document


def _share(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _nearest_rank(sorted_values: Sequence[int], fraction: float) -> int:
    """The smallest value with at least `fraction` of the values at or below it."""
    if not sorted_values:
        return 0
    rank = max(1, math.ceil(fraction * len(sorted_values)))
    return sorted_values[rank - 1]


@dataclass(frozen=True)
class DocumentPartition:
    """How one document was cut, and how many of its Highlights sit inside one Clause."""

    doc_id: str
    clauses: int
    words: int
    largest_clause_words: int
    highlights: int
    single_clause_highlights: int

    @property
    def single_clause_share(self) -> float | None:
        """Of this document's Highlights, the share held by exactly one Clause.

        `None` where the document has no Highlights, so it prints "n/a" and not a misleading 0%.
        """
        return _share(self.single_clause_highlights, self.highlights)


@dataclass(frozen=True)
class PartitionFacts:
    """The Splitter's output over a set of documents, in totals and per document."""

    word_ceiling: int
    documents: tuple[DocumentPartition, ...]
    clause_word_counts: tuple[int, ...]
    clauses_with_parent_line: int
    parent_line_words: int
    largest_parent_line_words: int

    @property
    def clauses(self) -> int:
        return len(self.clause_word_counts)

    @property
    def words(self) -> int:
        return sum(self.clause_word_counts)

    @property
    def over_ceiling(self) -> int:
        """Clauses above the Word Ceiling. Zero by construction; reported because it is the
        build-breaker (ADR-0004)."""
        return sum(1 for words in self.clause_word_counts if words > self.word_ceiling)

    @property
    def largest_clause_words(self) -> int:
        return max(self.clause_word_counts, default=0)

    @property
    def median_clause_words(self) -> float:
        counts = sorted(self.clause_word_counts)
        if not counts:
            return 0
        middle = len(counts) // 2
        return counts[middle] if len(counts) % 2 else (counts[middle - 1] + counts[middle]) / 2

    @property
    def mean_clause_words(self) -> float:
        return self.words / self.clauses if self.clauses else 0

    @property
    def p90_clause_words(self) -> int:
        return _nearest_rank(sorted(self.clause_word_counts), 0.9)

    @property
    def highlights(self) -> int:
        return sum(d.highlights for d in self.documents)

    @property
    def single_clause_highlights(self) -> int:
        return sum(d.single_clause_highlights for d in self.documents)

    @property
    def single_clause_share(self) -> float | None:
        """Of all Highlights, the share held by exactly one Clause. Reported, never a build gate."""
        return _share(self.single_clause_highlights, self.highlights)

    @property
    def parent_line_growth(self) -> float | None:
        """Words the Parent Lines add, as a share of the Clause words, if every Clause is asked once.

        Jev is shown Parent Line plus Clause for every Rule, so this is also the growth in the
        words Jev reads per Rule.
        """
        return _share(self.parent_line_words, self.words)


def partition_facts(
    documents: Sequence[Document], word_ceiling: int = WORD_CEILING
) -> PartitionFacts:
    """Split every document and measure the partition against all of its Highlights."""
    rows: list[DocumentPartition] = []
    word_counts: list[int] = []
    parent_words: list[int] = []

    for document in documents:
        clauses: tuple[Clause, ...] = split_document(
            document.doc_id, document.text, word_ceiling=word_ceiling
        )
        counts = [c.word_count for c in clauses]
        word_counts.extend(counts)
        parent_words.extend(len(c.parent_line.split()) for c in clauses)
        single = sum(
            1
            for highlight in document.highlights
            if sum(1 for clause in clauses if holds(clause, highlight)) == 1
        )
        rows.append(
            DocumentPartition(
                doc_id=document.doc_id,
                clauses=len(clauses),
                words=sum(counts),
                largest_clause_words=max(counts, default=0),
                highlights=len(document.highlights),
                single_clause_highlights=single,
            )
        )

    return PartitionFacts(
        word_ceiling=word_ceiling,
        documents=tuple(rows),
        clause_word_counts=tuple(word_counts),
        clauses_with_parent_line=sum(1 for words in parent_words if words),
        parent_line_words=sum(parent_words),
        largest_parent_line_words=max(parent_words, default=0),
    )
