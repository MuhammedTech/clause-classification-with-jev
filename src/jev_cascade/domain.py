"""The units every judgement is made on: Clause, Highlight and the Pair key.

Spans are half-open character ranges `[start, end)` into the document text, so a Clause ending
exactly where a Highlight starts does not overlap it.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Highlight:
    """A span of contract text a CUAD lawyer marked as an instance of a CUAD category.

    The only ground truth there is.
    """

    doc_id: str
    rule_id: str
    start: int
    end: int
    text: str = ""

    def __post_init__(self) -> None:
        if self.end < self.start:
            raise ValueError(f"Highlight end {self.end} precedes start {self.start}")


@dataclass(frozen=True)
class Clause:
    """A numbered or lettered item of a contract, the unit every judgement is made on.

    Clauses partition their document: every character belongs to exactly one.
    """

    doc_id: str
    index: int
    start: int
    end: int
    text: str
    parent_line: str = ""

    def __post_init__(self) -> None:
        if self.end < self.start:
            raise ValueError(f"Clause end {self.end} precedes start {self.start}")

    @property
    def word_count(self) -> int:
        """Words in the Clause's own text. The Binned Share is measured in these."""
        return len(self.text.split())

    @property
    def span_key(self) -> str:
        """Identifies the Clause inside its document, for the P(yes) cache key."""
        return f"{self.start}-{self.end}"

    @property
    def key(self) -> tuple[str, str]:
        """Identifies the Clause across the corpus: its document plus its span."""
        return (self.doc_id, self.span_key)


def holds(clause: Clause, highlight: Highlight) -> bool:
    """A Clause holds a Highlight when their character ranges overlap by one character or more.

    Pure arithmetic, no threshold.

    Offsets are only comparable **within one document**, so a Clause and a Highlight from
    different documents never hold, however their ranges line up. Pooling several documents into
    one evaluation without this check silently invents overlaps: on the three tracer documents it
    produced six false holding relations against four real ones, two of them inside a Certified
    Negative document, which by definition holds nothing.

    Spans are half-open, so ranges that merely abut share no character and do not overlap.
    """
    if clause.doc_id != highlight.doc_id:
        return False
    return max(clause.start, highlight.start) < min(clause.end, highlight.end)
