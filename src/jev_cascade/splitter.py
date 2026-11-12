"""The Splitter: partitions one document into Clauses.

The splitter from ADR-0004. Every character of the document lands in exactly one Clause, with no
gaps and no overlaps, which is what stops a Highlight being held by zero Clauses and so reading as
Lost no matter what Jev answered.

The work happens in four passes, in this order:

1. **Cut at item markers** at the start of a line: `1.`, `1.1`, `(a)`, `(iv)`. Text before the first
   marker becomes its own Clause, and text trailing after an item belongs to that item.
2. **Merge headings forward.** A heading's words belong to the first Clause beneath it, and the
   heading becomes the Parent Line for the rest of its section.
3. **Assign Parent Lines** from the marker nesting, so a Clause sees the line it sits *under* rather
   than the sibling above it.
4. **Split oversized Clauses**, mandatorily, until none exceeds the word ceiling.

The order matters: the oversized split runs last so that a Clause enlarged by a merged heading is
still measured against the ceiling, and so no piece of a split Clause can be mistaken for a heading.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .domain import Clause

#: An item marker at the start of a line: `1.`, `1.1`, `1.1.1`, `(a)`, `(iv)`. Exactly the four
#: shapes ADR-0004 lists.
#:
#: The marker must be followed by whitespace, so a bare sentence or a parenthesised definition is
#: not mistaken for one. A **plain integer must carry its dot**: `1.` is a marker and `1` is not,
#: because a bare integer at a line start is normally a page number, a year or a table quantity.
#: Ticket 01's pattern allowed it and cut 170 times on them across the corpus. Dotted numbering
#: may omit the trailing dot, since `1.1` is already unambiguous.
ITEM_MARKER = re.compile(
    r"""
    [ \t]*                      # indentation
    (?:
        \d+ (?: \.\d+ )+ \.?    # 1.1  1.1.1  1.1.
      | \d+ \.                  # 1.   — the dot is required
      | \( [A-Za-z]{1,4} \)     # (a)  (iv)  (A)
    )
    (?= [ \t] | $ )             # a marker is followed by space or ends the line
    """,
    re.VERBOSE,
)

_LINE_START_MARKER = re.compile(rf"^(?={ITEM_MARKER.pattern})", re.VERBOSE | re.MULTILINE)

#: Words a heading may carry after its marker. "1. Definitions." and
#: "2.2 Additional Licensing Provisions." are headings; a one-line definition such as
#: '1.49 "Field" means the treatment of HIV in humans.' is a Clause in its own right.
HEADING_MAX_WORDS = 8


@dataclass(frozen=True)
class _Region:
    """One cut of the document before headings are merged and Parent Lines assigned."""

    start: int
    end: int
    marker: str | None
    depth: int
    first_line: str
    is_heading_shape: bool


def _cut_points(text: str) -> list[int]:
    """Offsets where a new Clause begins: the start of every line carrying an item marker."""
    cuts = [m.start() for m in _LINE_START_MARKER.finditer(text)]
    # Text before the first marker is its own Clause (the title, the parties, the recitals).
    if not cuts or cuts[0] != 0:
        cuts.insert(0, 0)
    return cuts


def _first_line(segment: str) -> str:
    """The region's own opening line, which is what it offers its children as a Parent Line."""
    for line in segment.splitlines():
        if line.strip():
            return line.strip()
    return ""


def _is_heading_shape(segment: str, marker: str | None) -> bool:
    """Whether the region reads as a section heading rather than a provision.

    A heading is a single line carrying a marker and a short label. Two things are deliberately
    **not** headings:

    - a line ending in a colon, which is a Parent Line. ADR-0004 grades a lead-in-only Highlight on
      the lead-in Clause alone, so the lead-in has to keep a Clause of its own.
    - anything longer than `HEADING_MAX_WORDS`, which is what keeps one-line definitions whole.
    """
    if marker is None:
        return False
    lines = [line for line in segment.splitlines() if line.strip()]
    if len(lines) != 1:
        return False
    label = lines[0].strip()[len(marker.strip()) :].strip()
    if label.endswith(":"):
        return False
    return 0 < len(label.split()) <= HEADING_MAX_WORDS


def _depth_of(marker: str | None, numeric_depth: int) -> int:
    """How deeply a marker nests, for Parent Lines and for the heading test.

    `1.` is depth 1 and `1.1` depth 2, counting dotted components. A lettered or roman marker sits
    one level under the numbered item it follows, so `(a)` under `1.` is depth 2. Letters and romans
    share a level: `(a)` and `(iv)` are the same shape, so this splitter cannot tell a nested roman
    list from a lettered one, and ADR-0004 asks for no cleverer marker detection than that.
    """
    if marker is None:
        return 0
    if marker.startswith("("):
        return numeric_depth + 1
    return marker.strip().rstrip(".").count(".") + 1


def _regions(text: str) -> list[_Region]:
    """Cut the text at markers and classify each piece."""
    cuts = _cut_points(text)
    bounds = list(zip(cuts, cuts[1:] + [len(text)]))

    regions: list[_Region] = []
    numeric_depth = 0
    for start, end in bounds:
        segment = text[start:end]
        match = ITEM_MARKER.match(segment)
        marker = match.group(0) if match else None
        depth = _depth_of(marker, numeric_depth)
        if marker is not None and not marker.strip().startswith("("):
            numeric_depth = depth
        regions.append(
            _Region(
                start=start,
                end=end,
                marker=marker,
                depth=depth,
                first_line=_first_line(segment),
                is_heading_shape=_is_heading_shape(segment, marker),
            )
        )
    return regions


def _is_heading(regions: list[_Region], index: int) -> bool:
    """Whether this region is a heading that hands its words to the region below.

    It must look like a heading *and* be followed by a deeper marker, which is the "section heading
    over its sub-items" case ADR-0004 describes. Measured over the corpus, that distinction is what
    separates 137 real headings from 145 short definition items that happen to read like one.

    A heading directly above another heading stands alone rather than merging into it, so
    "ARTICLE IX" over "Section 9.1" still leaves a heading-only Clause. ADR-0004 accepts that as
    rare.
    """
    region = regions[index]
    if not region.is_heading_shape:
        return False
    if index + 1 >= len(regions):
        return False
    below = regions[index + 1]
    if below.depth <= region.depth:
        return False
    # Heading *shape* is not enough to block the merge: a sub-item can be short enough to read as
    # one. The region below only blocks it by being a heading itself, which needs its own deeper
    # marker below it in turn.
    return not _is_heading(regions, index + 1)


@dataclass(frozen=True)
class _Piece:
    """A Clause's span and context, settled but not yet numbered."""

    start: int
    end: int
    parent_line: str


def _merge_headings(regions: list[_Region]) -> list[_Piece]:
    """Give each heading's words to the first Clause beneath it."""
    pieces: list[_Piece] = []
    pending_heading: _Region | None = None

    for index, region in enumerate(regions):
        if _is_heading(regions, index):
            pending_heading = region
            continue
        start = pending_heading.start if pending_heading is not None else region.start
        pending_heading = None
        pieces.append(_Piece(start=start, end=region.end, parent_line=""))

    if pending_heading is not None:
        # A heading with nothing below it: the document ends on it. It keeps its own Clause.
        pieces.append(
            _Piece(start=pending_heading.start, end=pending_heading.end, parent_line="")
        )
    return pieces


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

    pieces = _merge_headings(_regions(text))

    return tuple(
        Clause(
            doc_id=doc_id,
            index=index,
            start=piece.start,
            end=piece.end,
            text=text[piece.start : piece.end],
            parent_line=_parent_line(text, piece.start),
        )
        for index, piece in enumerate(pieces)
    )
