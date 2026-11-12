# CUAD as ground truth: what was measured

Everything here was measured directly from the CUAD v1 files on 2026-11-11. Do not re-derive it;
correct it if a later run disagrees.

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

Corpus size: 2,845,654 characters, roughly 474,000 words. Median contract 35,703 characters, largest
272,018.

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
boundaries, not item boundaries: 21,172 newlines across 2,990,822 characters, so a "line" averages
about a page. Most documents still carry their item markers at the start of a line, which is why the
naive partition works at all. But some do not. In
`HertzGroupRealtyTrustInc_..._Trademark License Agreement` an entire page is one line —
`ARTICLE 1. BACKGROUND AND DEFINITIONS 1.1 Licensor has adopted ... 1.2 Licensee is ...` — and the
whole 14,313-character contract yields **4 clauses**.

This matters for the oversized split in ADR-0004: **a document like that has no paragraph breaks to
split at either**, so cutting oversized clauses at paragraph breaks cannot bring it under the word
ceiling. Ticket 03 needs a fallback that does not depend on finding a newline. The ticket 01 tracer
documents were therefore chosen from documents the line-start splitter does partition sensibly, so
the tracer exercises the pipeline rather than this weak spot.

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

## Spans sit inside one clause 97% of the time

Of the 429 spans, 418 contain no item marker, 5 contain one, 1 contains two, and 5 contain four or
more. So provisions spanning several clauses affect about 3% of cases. The old spec's "97% of
highlights inside exactly one clause" target was not arbitrary; it is what the data gives.

## Run size

| | |
| --- | --- |
| Clauses (naive partition) | 3,244 |
| Rules | 7 |
| Jev calls | 22,708 |
| Wall clock at ~1,200 req/min | ~20 minutes |
| Jev cost at $0.042 per million input tokens | ~$0.20 |

The price is from one unverified third-party blog and must be confirmed when the key arrives.

## Reproducing these numbers

The probe scripts were throwaway. Anything here should be re-asserted as a test in the corpus loader
(see `.scratch/jev-cascade/issues/02-corpus-loader.md`) rather than kept as a script.
