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

#: The **Word Ceiling**: no Clause may exceed this many words, counted by `str.split` as
#: `Clause.word_count` does. 600 is the figure ADR-0004 and `docs/cuad-ground-truth.md` measure the
#: oversized Clauses against. It is a ceiling, so a Clause of exactly 600 words stands.
WORD_CEILING = 600


def _is_lettered(marker: str) -> bool:
    """Whether a marker is `(a)` or `(iv)` rather than numbered.

    `ITEM_MARKER` carries its indentation, so the marker text of an indented item is `"  (a)"`. The
    strip lives here, once, because a check made on the raw text silently treats every indented
    lettered item as a numbered one.
    """
    return marker.strip().startswith("(")


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


def _first_line(region_text: str) -> str:
    """The region's own opening line, which is what it offers its children as a Parent Line."""
    for line in region_text.splitlines():
        if line.strip():
            return line.strip()
    return ""


def _is_heading_shape(region_text: str, marker: str | None) -> bool:
    """Whether the region reads as a section heading rather than a provision.

    A heading is a single line carrying a marker and a short label. Two things are deliberately
    **not** headings:

    - a line ending in a colon, which is a Parent Line. ADR-0004 grades a Highlight lying only in a
      Parent Line on the Clause that holds it, so a line introducing a list has to keep a Clause of
      its own.
    - anything longer than `HEADING_MAX_WORDS`, which is what keeps one-line definitions whole.
    """
    if marker is None:
        return False
    lines = [line for line in region_text.splitlines() if line.strip()]
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
    if _is_lettered(marker):
        return numeric_depth + 1
    return marker.strip().rstrip(".").count(".") + 1


def _regions(text: str) -> list[_Region]:
    """Cut the text at markers and classify each piece."""
    cuts = _cut_points(text)
    bounds = list(zip(cuts, cuts[1:] + [len(text)]))

    regions: list[_Region] = []
    numeric_depth = 0
    for start, end in bounds:
        region_text = text[start:end]
        match = ITEM_MARKER.match(region_text)
        marker = match.group(0) if match else None
        depth = _depth_of(marker, numeric_depth)
        if marker is not None and not _is_lettered(marker):
            numeric_depth = depth
        regions.append(
            _Region(
                start=start,
                end=end,
                marker=marker,
                depth=depth,
                first_line=_first_line(region_text),
                is_heading_shape=_is_heading_shape(region_text, marker),
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
    #: Whether the Parent Line is a standalone section heading. See `Clause`.
    parent_is_heading: bool = False


def _leading_number(marker: str) -> str:
    """The first integer of a numbered marker: `7` for `7.2`, `7.2.` and `7.`."""
    match = re.match(r"\d+", marker.strip())
    return match.group(0) if match else ""


def _parent_text(marker: str, candidate: _Region | None) -> str:
    """The line an item with `marker` sits under, given the nearest shallower marked region above.

    A lettered item sits under whatever shallower item holds it. A **numbered** item only does when
    the numbering agrees: `6.2` sits under `6.`, but `7.2` after a missing `7.` does not, because
    the nearest shallower item is then `6. Term and Termination.` and naming it would stamp the
    wrong section onto the Clause. Measured over the corpus, the depth rule alone picked a parent
    with a different leading number for 362 of 750 numbered items under a numbered ancestor. A wrong
    section label is worse than none, so those get an empty Parent Line.
    """
    if candidate is None:
        return ""
    if not _is_lettered(marker):
        if candidate.marker is None or _is_lettered(candidate.marker):
            return ""
        if _leading_number(marker) != _leading_number(candidate.marker):
            return ""
    return candidate.first_line


def _parent_lines(regions: list[_Region]) -> list[tuple[str, bool]]:
    """The Parent Line of every region, and whether it is a heading: the line it sits one level
    under, never a sibling.

    A Parent Line is a heading when the region it came from has the shape of one (a single short
    label after its marker, no colon), the same test `_is_heading_shape` makes for merging. A line
    ending in a colon introduces a list, and a longer one carries body text, so neither is one.

    Walks the regions with a stack of the open items. Entering a region closes every open item at
    its depth or deeper, so what is left on top is the nearest shallower item, which is the line
    this one sits under. The unmarked opening has depth 0 and is never anyone's parent.
    """
    parents: list[tuple[str, bool]] = []
    stack: list[_Region] = []
    for region in regions:
        if region.marker is None:
            parents.append(("", False))
            continue
        while stack and stack[-1].depth >= region.depth:
            stack.pop()
        text = _parent_text(region.marker, stack[-1] if stack else None)
        parents.append((text, bool(text) and stack[-1].is_heading_shape))
        stack.append(region)
    return parents


def _merge_headings(regions: list[_Region]) -> list[_Piece]:
    """Give each heading's words to the first Clause beneath it, and assign Parent Lines.

    A merged Clause takes the Parent Line of its **heading**, not the heading itself: the heading's
    words are already in the Clause, so naming it again would only repeat them.
    """
    parents = _parent_lines(regions)
    pieces: list[_Piece] = []
    pending_heading: int | None = None

    for index, region in enumerate(regions):
        if _is_heading(regions, index):
            pending_heading = index
            continue
        first = pending_heading if pending_heading is not None else index
        pending_heading = None
        line, is_heading = parents[first]
        pieces.append(
            _Piece(
                start=regions[first].start,
                end=region.end,
                parent_line=line,
                parent_is_heading=is_heading,
            )
        )

    if pending_heading is not None:
        # A heading with nothing below it: the document ends on it. It keeps its own Clause.
        heading = regions[pending_heading]
        line, is_heading = parents[pending_heading]
        pieces.append(
            _Piece(
                start=heading.start,
                end=heading.end,
                parent_line=line,
                parent_is_heading=is_heading,
            )
        )
    return pieces


#: Where an oversized Clause may be cut, tried in this order and recursing a lone oversized
#: segment to the next. Each pattern's match end is the cut, so a separator stays with the text
#: before it and the pieces still concatenate to the original.
#:
#: The first two are the paragraph breaks ADR-0004 asks for. The last two exist because a paragraph
#: break is not always there: newlines in the CUAD `context` sit at page boundaries, and in some
#: documents a whole page is one line with nothing to cut at. Sentence ends and then any
#: whitespace guarantee the ceiling is reached, since the last level cuts after every word.
_CUT_LEVELS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\n[ \t]*\n\s*"),  # a blank line: a paragraph break
    re.compile(r"\n\s*"),  # any line break
    re.compile(r"(?<=[.;:!?])\s+"),  # the end of a sentence or a semicolon clause
    re.compile(r"\s+"),  # between any two words
)


def _word_count(text: str, start: int, end: int) -> int:
    """Words by `str.split`, the same count `Clause.word_count` uses."""
    return len(text[start:end].split())


def _segments(text: str, start: int, end: int, pattern: re.Pattern[str]) -> list[tuple[int, int]]:
    """Cut `[start, end)` after every match of `pattern`, never leaving a blank segment.

    A segment with no words is joined to the one after it, or to the one before it when it is last,
    so no piece of a split is empty or whitespace-only. The span must contain at least one word,
    which the caller guarantees by only cutting text that is over the ceiling.
    """
    cuts = [m.end() for m in pattern.finditer(text, start, end) if start < m.end() < end]
    bounds = [start, *cuts, end]
    segments: list[tuple[int, int]] = []
    carried: int | None = None
    for left, right in zip(bounds, bounds[1:]):
        if carried is not None:
            left, carried = carried, None
        if not text[left:right].strip():
            carried = left
            continue
        segments.append((left, right))
    if carried is not None:
        segments[-1] = (segments[-1][0], end)
    return segments


def _split_oversized(
    text: str, start: int, end: int, ceiling: int, level: int = 0
) -> list[tuple[int, int]]:
    """Cut `[start, end)` into spans of at most `ceiling` words, as few and as large as possible.

    Segments are packed greedily at the current cut level. A single segment that is itself over
    the ceiling is recursed to the next level, so a block with no paragraph break falls through to
    sentences and then to words.

    The recursion ends by itself: the last cut level leaves one word in every segment, and a word is
    never over a ceiling of at least 1, so `level` cannot run past `_CUT_LEVELS`. If it ever did,
    the `IndexError` is wanted over a silently oversized Clause.
    """
    if _word_count(text, start, end) <= ceiling:
        return [(start, end)]

    segments = _segments(text, start, end, _CUT_LEVELS[level])
    if len(segments) == 1:
        return _split_oversized(text, start, end, ceiling, level + 1)

    spans: list[tuple[int, int]] = []
    run_start: int | None = None
    run_words = 0
    for left, right in segments:
        words = _word_count(text, left, right)
        if words > ceiling:
            if run_start is not None:
                spans.append((run_start, left))
                run_start, run_words = None, 0
            spans.extend(_split_oversized(text, left, right, ceiling, level + 1))
            continue
        if run_start is not None and run_words + words > ceiling:
            spans.append((run_start, left))
            run_start, run_words = None, 0
        if run_start is None:
            run_start = left
        run_words += words
    if run_start is not None:
        spans.append((run_start, end))
    return spans


def _split_pieces(text: str, pieces: list[_Piece], ceiling: int) -> list[_Piece]:
    """Split every piece over the word ceiling. A continuation keeps the whole Clause's Parent Line.

    A continuation is not a new item, so it sits under the same line the whole Clause did. It does
    not take its own first line as one: that would be a mid-sentence fragment.
    """
    result: list[_Piece] = []
    for piece in pieces:
        for start, end in _split_oversized(text, piece.start, piece.end, ceiling):
            result.append(
                _Piece(
                    start=start,
                    end=end,
                    parent_line=piece.parent_line,
                    parent_is_heading=piece.parent_is_heading,
                )
            )
    return result


def split_document(
    doc_id: str, text: str, word_ceiling: int = WORD_CEILING
) -> tuple[Clause, ...]:
    """Partition one document into Clauses in reading order, none over `word_ceiling` words."""
    if word_ceiling < 1:
        raise ValueError(f"word_ceiling must be at least 1, got {word_ceiling}")
    if not text:
        return ()

    pieces = _split_pieces(text, _merge_headings(_regions(text)), word_ceiling)

    return tuple(
        Clause(
            doc_id=doc_id,
            index=index,
            start=piece.start,
            end=piece.end,
            text=text[piece.start : piece.end],
            parent_line=piece.parent_line,
            parent_is_heading=piece.parent_is_heading,
        )
        for index, piece in enumerate(pieces)
    )
