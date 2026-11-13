"""The units every judgement is made on: Clause, Highlight and the Pair key.

Spans are half-open character ranges `[start, end)` into the document text, so a Clause ending
exactly where a Highlight starts does not overlap it.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable


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
    #: Whether `parent_line` is a section heading ("9. Limitation of Liability") rather than a
    #: lead-in ("10.1 Licensee shall:"). Never shown to Jev; ticket 08 reads it to take the heading
    #: out of Jev's context and leave a lead-in in.
    parent_is_heading: bool = False

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


def without_heading(clauses: Iterable[Clause]) -> list[Clause]:
    """The Clauses as Jev is shown them when heading context is off.

    A Parent Line that is a section heading is blanked; a lead-in ("Licensee shall:") stays,
    because a list item read without its lead-in is a different and unfair question. The span and
    text are untouched, so grading is identical in both arms, and the Parent Line is part of the
    cache fingerprint, so the two arms never share an answer where they differ.
    """
    return [replace(c, parent_line="") if c.parent_is_heading else c for c in clauses]
