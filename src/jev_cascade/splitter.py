"""The Splitter: partitions one document into Clauses.

Ticket 01's simple splitter, cutting at item markers at the start of a line. Every character of the
document lands in exactly one Clause, with no gaps and no overlaps, which is what stops a Highlight
being held by zero Clauses and so reading as Lost no matter what Jev answered (ADR-0004).

Still to come in ticket 03: the mandatory re-split of Clauses over the word ceiling, and the rule
that a heading's words belong to the first Clause beneath it while the heading becomes the Parent
Line for the rest of its section. Until then the Parent Line is simply the last non-empty line
above the Clause.
"""

from __future__ import annotations

import re

from .domain import Clause

#: An item marker at the start of a line: `1.`, `1.1`, `1.1.1`, `(a)`, `(iv)`.
#: The marker must be followed by whitespace, so a bare sentence or a parenthesised definition is
#: not mistaken for one.
ITEM_MARKER = re.compile(
    r"""
    [ \t]*                      # indentation
    (?:
        \d+ (?: \.\d+ )* \.?    # 1.  1.1  1.1.1
      | \( [A-Za-z]{1,4} \)     # (a)  (iv)  (A)
    )
    (?= [ \t] | $ )             # a marker is followed by space or ends the line
    """,
    re.VERBOSE,
)

_LINE_START_MARKER = re.compile(
    rf"^(?={ITEM_MARKER.pattern})", re.VERBOSE | re.MULTILINE
)


def _cut_points(text: str) -> list[int]:
    """Offsets where a new Clause begins: the start of every line carrying an item marker."""
    cuts = [m.start() for m in _LINE_START_MARKER.finditer(text)]
    # Text before the first marker is its own Clause (the title, the parties, the recitals).
    if not cuts or cuts[0] != 0:
        cuts.insert(0, 0)
    return cuts


def _parent_line(text: str, start: int) -> str:
    """The line a Clause sits under, as context for Jev. Never used in grading."""
    for line in reversed(text[:start].splitlines()):
        if line.strip():
            return line.strip()
    return ""


def split_document(doc_id: str, text: str) -> tuple[Clause, ...]:
    """Partition one document into Clauses in reading order."""
    if not text:
        return ()

    cuts = _cut_points(text)
    bounds = list(zip(cuts, cuts[1:] + [len(text)]))

    return tuple(
        Clause(
            doc_id=doc_id,
            index=index,
            start=start,
            end=end,
            text=text[start:end],
            parent_line=_parent_line(text, start),
        )
        for index, (start, end) in enumerate(bounds)
    )
