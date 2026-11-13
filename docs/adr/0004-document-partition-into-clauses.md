# Partition the document so every character belongs to exactly one clause

## The decision

The splitter **partitions** the contract: every character of the text lands in exactly one Clause,
with no gaps and no overlaps.

- Cut at item markers at the start of a line: `1.`, `1.1`, `(a)`, `(iv)`.
- Text before the first marker becomes its own Clause (the title, the parties, the recitals).
- Text trailing after a numbered item, with no marker of its own, belongs to that item.
- A heading's words belong to the **first Clause beneath it**, and the heading is also passed to the
  rest of its section as context.
- **A Clause over the word ceiling is split again at paragraph breaks** until every Clause is under it.
  This is mandatory, not a safety net.

A Clause carries its span, its word count, and its **immediate** parent line as context. Jev is shown
the parent plus the Clause; grading uses only the Clause's own span.

## Why partition

Cutting only at markers leaves text in no Clause at all. A highlight landing there is held by zero
Clauses, and "lost when every holding Clause was Binned" is vacuously true of an empty set, so the
provision reads as lost no matter what Jev answered. Partitioning makes that impossible by
construction instead of something a test has to catch. It also makes the Binned Share denominator
well defined, since every word is in exactly one Clause.

## Why the oversized split is mandatory

A naive partition of the 53-document corpus produces 3,244 Clauses with a median of 59 words, but a
mean of 138, a 90th percentile of 295, **91 Clauses over 600 words and one of 16,176**. Under the
one-character overlap rule a huge Clause holding a single highlighted sentence counts entirely as
holding a provision, so Jev gets full credit for escalating all of it. One measured case: a 450-word
Clause of indemnification text containing one 248-character limitation-of-liability sentence. Without
the oversized split, recall is flattered and precision is meaningless on those Clauses.

## Why headings go to the Clause below, not their own Clause

Both section headings in a typical fragment contain a number, so a strict reading of "cut at the
numbers" would make each its own Clause. A Clause holding only "Section 9 · Limitation of Liability"
carries every keyword for the liability rule and no provision at all, so Jev would very likely
escalate it and be wrong by construction. The alternative, giving headings their own Clause and never
asking about them, breaks differently: a provision marked inside a heading would be held only by a
Clause nobody asks, so it would read as lost automatically.

Two headings in a row, such as "ARTICLE IX" followed by "Section 9.1", still produce a heading-only
Clause under this rule. Accepted; it is rare.

Whether a heading helps or hurts is an open empirical question. It gives Jev real context on a genuine
liability cap, and it also stamps the section label onto every unrelated Clause in that section. Test
it both ways on a sample before the full run rather than deciding now.

## Consequences

- **The clever splitter is no longer needed.** The old requirements for mid-line numbering (Eton),
  spaced dotted numbering (Telkom) and table rows that are not markers (Glu Mobile) existed to avoid
  giant and fake Clauses. Partition plus the oversized split degrades gracefully instead: those
  documents yield coarser Clauses, which is visible in the reported statistics rather than silently
  wrong.
- **All 53 documents stay.** An earlier proposal dropped Eton, Telkom and Glu Mobile to avoid the hard
  splitter work. That is no longer worth the corpus bias it introduces, since the partition handles
  them. Report the per-document share of highlights sitting inside one Clause so a bad split shows up.
- **The 97% single-Clause target is a reported number, not a build gate.** Measured, 418 of 429 spans
  contain no item marker, so 97% is what the data naturally gives. Gating on it would pressure the
  splitter to stop separating sub-items, which would undo the parent-context design. The word ceiling
  stays the build-breaker.
- **The lead-in touch rule is dropped.** The old rule passed a highlight down from a lead-in that was
  itself the whole highlight, which rested on exact string equality and raised a trimmed-equality
  versus containment question. With one cutoff its main job is gone, and only 12 of 455 highlights were
  lead-in-only. Those are now graded on the lead-in Clause alone.
- The plain-chunk sensitivity rerun is dropped. It doubled the Jev run, and because a chunk normally
  carries no parent line while sometimes swallowing one, it varied the cut and the context together.

## Considered and rejected

- **Cut only at markers, leave gaps.** Rejected: silent vacuous losses, as above.
- **Headings as their own unasked Clause.** Rejected: a highlight inside a heading becomes an
  automatic loss.
- **Word-count chunks as the primary unit.** Rejected: a dry run moved Anti-Assignment by 11
  highlights, and Clauses are the unit a lawyer recognises.

## Amendment, 2026-11-12: what ticket 03 settled

These extend the decision above without reversing it. The text above is left as written, including
its use of "lead-in", which the glossary has since renamed Parent Line.

- **The oversized split cuts at more than paragraph breaks.** The order is paragraph break, line
  break, sentence end, then word break. A paragraph break is not always there: newlines in the CUAD
  `context` sit at page boundaries, and 4 of the 92 oversized Clauses have none to cut at. The last
  level cuts after every word, so the Word Ceiling is always reached.
- **A Parent Line can be empty.** A numbered item takes one only when its leading number matches
  the item above it, so `7.2` with no `7.` above it gets none instead of the wrong section. Measured,
  the depth rule alone named a different section for 362 of 750 numbered items. A merged heading
  Clause takes the heading's own Parent Line, and the pieces of a split Clause keep the whole
  Clause's.
- **Only numbered headings merge forward.** `ARTICLE IX` and `Section 9 · Limitation of Liability`,
  this ADR's own examples, carry no item marker and are not treated as headings. That line stays at
  the tail of the Clause above it. This was not built, because the ticket asks for no cleverer marker
  detection, and the per-document table in the report's Partition section is where it would show.

## Amendment, 2026-11-13: what ticket 08 settled about the heading

The open question above, whether a heading helps or hurts Jev, was tested on a sample
(`docs/question-type-and-heading-sample.md`): 20 held and 40 not-held Clauses per Rule, half the
not-held ones under the same heading as a held Clause, asked with the heading shown and taken out.
Mean separation was 0.980 both ways (difference +0.000, 95% interval -0.002 to +0.002), so the
heading **stays on**.

- **"Heading" means a section heading, not every Parent Line.** The Splitter now records whether a
  Parent Line is a heading (a single short label after its marker, no colon), and taking the heading
  out leaves a lead-in such as `10.1 Licensee shall:` in place. Blanking every Parent Line would have
  tested something else, and a list item read without its lead-in is a different question.
- **The sample could not discriminate.** Every Rule scored at least 0.938 in every arm, and the sample
  holds only 40 near misses in all. "No difference" means none was detectable here. The harm the ADR
  worried about, a section label stamped on unrelated Clauses, would show over the corpus's many
  unrelated Clauses, which separation on a held-enriched sample does not measure.
- The choice was made on Pairs the full run later scores, a small selection leak the final report
  discloses.
