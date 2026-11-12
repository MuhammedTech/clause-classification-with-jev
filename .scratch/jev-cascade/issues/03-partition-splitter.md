# 03: Partition splitter

**What to build:** the splitter from ADR-0004. Every character of a contract lands in exactly one
Clause.

- Cut at item markers at the start of a line: `1.`, `1.1`, `(a)`, `(iv)`.
- Text before the first marker becomes its own Clause.
- Text trailing after a numbered item belongs to that item.
- A heading's words belong to the first Clause beneath it, and the heading is also the Parent Line for
  the rest of its section.
- **A Clause over the word ceiling is split again at paragraph breaks** until none exceed it. This is
  mandatory: a naive partition leaves 91 Clauses over 600 words and one of 16,176.

Each Clause records its span, word count and immediate Parent Line. Jev sees the Parent Line plus the
Clause. Grading uses only the Clause's own span.

No clever marker detection is needed. Mid-line numbering, spaced dotted numbering and pricing-table
rows produce coarser Clauses, which the oversized split then breaks up. That is visible in the
reported statistics rather than silently wrong, which is why all 53 documents stay.

**Blocked by:** 02.

**Status:** ready-for-agent

- [ ] A corpus-wide test asserts the Clauses of each document partition it: concatenating them in
      order reproduces the source text exactly, with no gaps or overlaps.
- [ ] A corpus-wide test asserts no Clause exceeds the word ceiling.
- [ ] A test asserts no Highlight is held by zero Clauses, for any Rule, anywhere in the corpus.
- [ ] Splitter tests use short real excerpts: opening text before the first marker, a heading with
      numbered items under it, a lettered list under a parent line, and an oversized block that must
      be split at a paragraph break.
- [ ] Jev receives Parent Line plus Clause text; an Evaluator test shows a Highlight lying only in the
      Parent Line does not make the sub-item hold it.
- [ ] The report shows Clause count, the word-length distribution, the share of Highlights inside one
      Clause (expect about 97%), that share per document so a bad split is visible, and the token
      growth from Parent Line context.

## Comments

**2026-11-12, from ticket 01.** The word ceiling needs a fallback that does not depend on finding a
paragraph break. Newlines in the JSON `context` sit at page boundaries, not item boundaries, and in
some documents a whole page is a single line: `HertzGroupRealtyTrustInc_..._Trademark License
Agreement` is 14,313 characters and partitions into **4 clauses**, with no paragraph break inside
them to split at. Splitting oversized clauses at paragraph breaks therefore cannot bring those
documents under the ceiling. Measured detail is in `docs/cuad-ground-truth.md` under "The text to
split is the JSON `context`".

Also settled in ticket 01, so ticket 03 need not rediscover it: split the JSON `context`, which is
the string the span offsets are measured against. `full_contract_txt/` is not usable as a substitute
because it is incomplete — 19 files for 510 documents, only 3 of our 53 — and its files sit in
`Part_I/`-style subdirectories. Where a file does exist it is byte-identical to the `context`, so the
two sources do not disagree; there is just not enough of one.

**2026-11-12, part way through 03.** Two of the four splitter passes are in, on branch
`worktree-jev-cascade-01-tracer-bullet` at commit `904d0bf`. Suite green at 93 tests and the one
strict xfail below.

- **The marker is settled.** A plain integer needs its dot: `1.` cuts, a bare `1` does not, because
  at a line start it is normally a page number, a year or a table quantity. Ticket 01's pattern cut
  on 170 of them. The corpus moves from 3,669 Clauses to **3,130**, and Clauses over 600 words from
  65 to **92** — the oversized split, still owed, is what brings that to zero.
- **Headings merge forward.** A heading is a single short labelled line whose next marker is
  **deeper**. That test is what the corpus actually supports: it separates 137 real headings
  ("1. Definitions.") from 145 one-line definitions that read exactly like one
  ('1.49 "Field" means the treatment of HIV in humans.') and must stay whole. A single-line test
  alone is useless here, because a whole Clause normally sits on one line in this corpus — median 43
  words — so it catches 2,174 of 3,130 regions. A line ending in a colon is a lead-in, not a
  heading, and keeps its own Clause as ADR-0004 requires.

Still owed: the Parent Line depth stack (which flips the strict xfail
`test_a_sibling_item_is_not_a_parent_line`), the oversized split, the three corpus-wide tests, the
Evaluator test for a Highlight lying only in the Parent Line, and the report's partition statistics.
`Word Ceiling` is used by the spec, this ticket and ADR-0004 but defined in no glossary entry; it
needs one, and the value needs pinning at 600 words, which is the only figure the ADR and
`docs/cuad-ground-truth.md` measure against.

**Ticket 10 blocks this one's correctness.** The P(yes) cache key has no Parent Line in it, so this
ticket's Parent Line work makes an existing cache serve answers computed from a different prompt.
See `10-cache-key-ignores-the-parent-line.md`.

Two measured corrections to make while here. `docs/cuad-ground-truth.md` says a line averages about
a page; measured, 21,225 lines over 2,990,822 characters is a **mean of 140 characters**, and the
page-long lines are confined to a few documents rather than typical. The oversized split needs its
newline-free fallback for **4** of the 92 oversized Clauses; the other 88 do contain a newline.
