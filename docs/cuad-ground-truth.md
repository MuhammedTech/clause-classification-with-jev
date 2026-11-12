# CUAD as ground truth: what was measured

Everything here was measured directly from the CUAD v1 files on 2026-11-11. Do not re-derive it;
correct it if a later run disagrees.

**A note on one word.** This file says "span" throughout, because that is what CUAD's own files and
README call an annotated range. In the project's vocabulary that thing is a **Highlight**, and
`GLOSSARY.md` lists "span" among the words to avoid for it. Code, tests and the report say Highlight;
this file keeps CUAD's word when describing CUAD's files. They are the same thing.

## Where the data is

The dataset is **not in this repo**. It lives at:

```
~/personal_coding/playground/cuad/CUAD_v1/
├── CUAD_v1.json          38 MB, 510 documents x 41 categories, SQuAD-style
├── master_clauses.csv    510 rows, one per document
├── full_contract_txt/
└── CUAD v1 ReadMe _ Datasheet/CUAD_v1_README.txt
```

## The License Agreement Set resolves to exactly 53 documents

Three different filters give three different counts, which is why the old notes disagreed:

| Filter | Count |
| --- | --- |
| CSV `Document Name` contains "licen" | **53** |
| CSV `Filename` contains "licen" | 44 |
| JSON `title` contains "licen" | 44 |

The 53 is the set we use. The JSON has no `Document Name` field, so the corpus loader must filter the
CSV on `Document Name` and then join to the JSON on `Filename` against `title`.

**The join needs one normalisation.** Strip the `.pdf` / `.txt` extension, then compare on
alphanumerics only, lowercased. With that, **all 53 resolve and none are missing**. Without it exactly
one fails: Pacira, whose filename says `A&R` where the JSON title says `A_R`.

Corpus size, re-measured on 2026-11-12 over all 53 documents with Pacira counted: **2,990,822
characters**, 447,653 words. Median contract 35,902 characters, largest 272,018, smallest 1,707.
Pacira alone is 145,168 characters, so the 2,845,654 and "roughly 474,000 words" recorded here
earlier were the 52 documents without it; the character figure is asserted in
`tests/test_corpus.py`.

## Span offsets are exact

Across the 429 spans covering the seven rules in these 53 documents:

- **429 of 429** have `answer_start` landing exactly on `answer["text"]` in the context. Zero drift.
- **Zero** contain the `<omitted>` marker the README warns about.

So character-range overlap is a sound basis for labelling. See ADR-0004.

## The annotation is exhaustive by protocol, including a machine-assisted sweep

From `CUAD_v1_README.txt`, the labelling ran seven steps. Two matter for recall:

- Step 3, **keyword search** to catch categories missed during manual labelling.
- Step 6, **"eBrevia extras" review**: the tool proposed clauses responsive to a category that humans
  had not labelled; attorneys and students reviewed **all** of them and added the correct ones,
  *"repeated until all or substantially all of the extras are incorrect labels."*

That is a completeness audit run to convergence, so **recall against these spans is trustworthy** and
we do not need to build our own audit. Also from the README: spans for yes/no categories are full
sentences ("from period to period"), table formatting is lost in the text conversion, and spacing is
inconsistent between words and paragraphs.

The dataset's own disclaimer that it is "not comprehensive or representative" is about which
categories and contracts were chosen, not about labelling completeness within a contract.

## Explicit negatives exist, and are what make precision measurable

A document with no clause of a category carries `is_impossible: true` with zero answers. This holds
cleanly: of 20,910 document-category pairs, 14,208 are `is_impossible` and **none of those has an
answer**. Every clause in such a document is a verified negative for that rule.

## Per-rule counts on the 53 documents

Gate from the old spec: at least 15 documents with a span and at least 25 spans.

Re-measured on 2026-11-12 over **all 53 documents, Pacira included**, by the corpus loader's gate
(ticket 02). The earlier version of this table excluded Pacira, which was added after it was
computed; its numbers are kept in the right-hand column so the correction is visible.

| Rule | CUAD category | Docs with spans | Spans | Docs certified as having none | Gate | Was, without Pacira |
| --- | --- | --- | --- | --- | --- | --- |
| R8 | Anti-Assignment | 41 | 85 | 12 | pass | 40 / 83 / 12 |
| R1 | Cap On Liability | 34 | 82 | 19 | pass | 33 / 78 / 19 |
| R2 | Post-Termination Services | 26 | 76 | 27 | pass | 25 / 58 / 27 |
| R5 | Exclusivity | 24 | 58 | 29 | pass | 23 / 55 / 29 |
| R3 | Termination For Convenience | 22 | 33 | 31 | pass | 21 / 30 / 31 |
| R7 | Change Of Control | 20 | 44 | 33 | pass | 19 / 39 / 33 |
| R6 | Minimum Commitment | 17 | 51 | 36 | pass | 17 / 51 / 35 |
| — | Uncapped Liability (dropped) | 17 | 26 | 36 | **pass** | 16 / 23 / 36 |
| — | Audit Rights (backup) | 29 | 92 | 24 | pass | 28 / 86 / 24 |
| — | IP Ownership Assignment (backup) | 17 | 52 | 36 | pass | 16 / 45 / 36 |

For every rule, docs with spans plus docs certified as having none is exactly 53: no document is
silently missing a category. The seven Rulebook rules hold **429 spans** between them, which is the
same 429 whose offsets are checked above.

**Uncapped Liability now passes the gate**, at 17 documents and 26 spans — one span over it. The
earlier 16 / 23 was measured before Pacira joined. So the reason ADR-0005 gives first, that it is
the only rule to fail the gate, no longer holds; its independence argument does, and that is now the
standing reason. See the correction note in ADR-0005. Neither backup is needed either way.

These counts are asserted in `tests/test_corpus.py` rather than kept in a script.

## The base rate is about 1%, and it caps what precision can look like

From a naive partition of the 53 documents at line-start item markers: **3,244 clauses**, median 59
words, mean 138, 90th percentile 295, largest 16,176 words, and **91 clauses over 600 words**. The
oversized-clause split in ADR-0004 is therefore mandatory, not optional.

A re-measurement on 2026-11-12 with a more permissive marker pattern gives 3,669 clauses, 65 clauses
over 600 words across 31 documents, and the same 16,176-word largest clause. The counts are not
interchangeable; see "Clause counts move with the marker pattern" above, which also records that some
documents have no line structure for the oversized split to use.

| Rule | Positive clauses | Base rate | Precision if 20% of clauses are escalated and 90% of positives caught |
| --- | --- | --- | --- |
| Minimum Commitment | 59 | 1.82% | ~8% |
| Anti-Assignment | 57 | 1.76% | ~8% |
| Post-Termination Services | 55 | 1.70% | ~8% |
| Cap On Liability | 51 | 1.57% | ~7% |
| Exclusivity | 48 | 1.48% | ~7% |
| Change Of Control | 30 | 0.92% | ~4% |
| Termination For Convenience | 27 | 0.83% | ~4% |

**Precision will read in single digits at any useful operating point.** That is arithmetic from a 1%
base rate, not Jev performing badly. With 27 to 59 positives per rule the numerator is small, so the
figure also moves a lot on resampling. Always print counts beside it.

## How much of the negative evidence is certified

A clause labelled as holding nothing is either a **certified negative** (its whole document is
`is_impossible` for that rule) or an **inferred negative** (the document has spans, just not here).
Reliability runs inversely to how common the clause type is.

| Rule | Certified | Inferred | Share certified |
| --- | --- | --- | --- |
| Minimum Commitment | 1,724 | 1,461 | 54% |
| Change Of Control | 1,700 | 1,514 | 53% |
| Exclusivity | 1,280 | 1,916 | 40% |
| Termination For Convenience | 1,094 | 2,123 | 34% |
| Post-Termination Services | 535 | 2,654 | 17% |
| Cap On Liability | 282 | 2,911 | 9% |
| Anti-Assignment | 156 | 3,031 | 5% |

This is why ADR-0003 reports a separate false-alarm rate on certified-negative documents.

## The text to split is the JSON `context`, and some documents have no line structure

Measured on 2026-11-12, while building the tracer bullet.

The text every span offset is measured against is `paragraphs[0].context` in `CUAD_v1.json`. **Split
that.** `full_contract_txt/` is not an alternative, for a simpler reason than whitespace drift: it is
**incomplete**. It ships 19 `.txt` files in `Part_I/`-style subdirectories, against 510 documents, and
only 3 of the 53 License Agreement Set documents have one at all. Of those 3, all 3 are
**byte-identical** to their JSON `context`, so there is no evidence the two sources disagree — there
is simply not enough of one to use. Grade and split the same string.

Corpus size reconciles with the figure above once Pacira is counted: the 53 contexts hold
**2,990,822 characters**, and **2,845,654 excluding Pacira**, which is exactly the number recorded
earlier. Pacira alone is 145,168 characters.

**The line structure is a page artefact, and in some documents it is absent.** Newlines sit at page
boundaries, not item boundaries. Corrected on 2026-11-12 during ticket 03: an earlier version of this
file said a "line" averages about a page, which is wrong. Measured, 21,225 lines over 2,990,822
characters is a **mean of 141 characters**, so a line is a sentence or two for most of the corpus and
the page-long lines are confined to a few documents. Most documents carry their item markers at the
start of a line, which is why the naive partition works at all. But some do not. In
`HertzGroupRealtyTrustInc_..._Trademark License Agreement` an entire page is one line —
`ARTICLE 1. BACKGROUND AND DEFINITIONS 1.1 Licensor has adopted ... 1.2 Licensee is ...` — and the
whole 14,313-character contract yields **4 clauses**.

This matters for the oversized split in ADR-0004: **a document like that has no paragraph breaks to
split at either**, so cutting oversized clauses at paragraph breaks cannot bring it under the word
ceiling. Ticket 03 needs a fallback that does not depend on finding a newline. The ticket 01 tracer
documents were therefore chosen from documents the line-start splitter does partition sensibly, so
the tracer exercises the pipeline rather than this weak spot.

**Measured when ticket 03 built that fallback** (2026-11-12): of the 92 Clauses over 600 words after
the marker cut and heading merge, **88 contain a newline and 4 do not**, so the fallback is needed for
4, not for every page-line document. All 4 are in one document, Ehave (`EX-4.44 ... Reseller
Agreement`). Hertz itself no longer produces an oversized Clause once the marker is settled. The
splitter's cut levels are paragraph break, line break, sentence end and word break, in that order, so
the ceiling is always reached.

### Clause counts move with the marker pattern, so quote the pattern

The ticket 01 splitter cuts on `\d+(\.\d+)*\.?` or `\([A-Za-z]{1,4}\)` at a line start, followed by
whitespace. Under it the 53 documents give **3,669 clauses**, against the 3,244 recorded earlier
under a stricter pattern. The largest clause is identical at **16,176 words**, so the two agree on the
shape of the problem and differ on where sub-items stop being cut.

Of the cuts this pattern fires, 2,055 line starts are dotted or numbered, 996 are lettered, and
**170 are a bare integer** with no dot — a page number, a year or a table quantity sitting at a line
start. That is a measured contribution to the gap, not a complete account of it; the exact cause of
the remaining difference was not chased, and ticket 03 settles the marker definition.

Oversized clauses also move with the pattern, so the two counts are **not** interchangeable:

| Marker pattern | Clauses | Clauses over 600 words |
| --- | --- | --- |
| Stricter, 2026-11-11 | 3,244 | 91 |
| Ticket 01 splitter, 2026-11-12 | 3,669 | 65 |

Under the ticket 01 splitter those 65 oversized clauses sit in **31 of the 53 documents**. Either way
the oversized split stays mandatory.

### The final partition (ticket 03, 2026-11-12)

With the marker settled (a plain integer needs its dot), headings merged forward, Parent Lines from
the marker nesting and the oversized split at **600 words**, all 53 documents give:

| | Before the oversized split | After it |
| --- | --- | --- |
| Clauses | 2,993 | **3,246** |
| Median words | 66 | 73 |
| Mean words | 149.6 | 137.9 |
| 90th percentile words | 315 | 430 |
| Largest, in words | 16,176 | **600** |
| Clauses over 600 words | 92 | **0** |

The three marker-pattern counts above (3,244, 3,669, 3,130 regions) all precede the heading merge,
which is why 2,993 is lower than any of them. The oversized split adds 253 Clauses and moves the
median and the 90th percentile up; the splitter packs greedily up to the ceiling, so many of the
new pieces sit close to it (the per-document table shows documents whose largest Clause is 598 or
600 words). The cause of the median's rise was not isolated. `tests/test_partition.py` asserts the
partition, the ceiling and that no Highlight is held by zero Clauses, over all 53 documents.

**Parent Lines add 16.2% more words** for Jev to read per Rule: 1,269 of the 3,246 Clauses carry one,
72,545 words over 447,653 words of Clause text. Over those 1,269 Clauses the median Parent Line is 6
words, but 259 are over 60 words, the 99th percentile is 578 and the largest is **801**, because
where a page is one line the first line of an item is that page. Ticket 06 turns this into tokens;
there is no tokenizer in the code.

An earlier version of this section said 9.6%, from 985 Clauses. A review found the splitter read an
indented lettered marker (`"  (a)"`) as a numbered one, so indented lettered items got no Parent Line;
fixing it added 284 Clauses with one. Everything above is re-measured after that fix.

**The depth rule alone gives wrong Parent Lines.** For 362 of 750 numbered items beneath a numbered
ancestor, the nearest shallower item has a different leading number (`7.2` with no `7.` above it
lands under `6. Term and Termination.`). The splitter requires the numbering to agree for a numbered
item and gives it no Parent Line otherwise, on the ground that a wrong section label is worse than an
empty one. Lettered items use the depth rule alone, which cannot be checked this way. These two
figures count numbered markers before the heading merge and the oversized split, so they are not
comparable with the Clause counts above.

## Highlights sit inside one clause 98.8% of the time

Measured on the final partition: **424 of 429 Highlights** overlap exactly one Clause. The other 5 are
held by several. By raw marker count the figure was lower: of the 429 spans, 418 contain no item
marker, 5 contain one, 1 contains two, and 5 contain four or more. The earlier "97%" came from that
count, and the spec's "about 97%" expectation is that raw figure rounded. The measured share on the
real partition is 98.8%, so the expectation was slightly pessimistic. Neither is a build gate
(ADR-0004), and the report prints the share per document so a bad split shows. The gap between the
two was not chased.

## Run size

| | |
| --- | --- |
| Clauses (final partition) | 3,246 |
| Rules | 7 |
| Jev calls | 22,722 |
| Wall clock at ~1,200 req/min | ~20 minutes |
| Jev cost at $0.042 per million input tokens | ~$0.20 (not recomputed) |

The 22,708 recorded earlier was 3,244 clauses times 7, so it moves with the partition: the final
partition gives 3,246 times 7. The cost figure was not re-derived, and the 16.2% extra words from
Parent Lines are not in it; ticket 06 counts tokens properly. The price is from one unverified
third-party blog and must be confirmed when the key arrives.

## Reproducing these numbers

The probe scripts were throwaway. Anything here should be re-asserted as a test in the corpus loader
(see `.scratch/jev-cascade/issues/02-corpus-loader.md`) rather than kept as a script.
