# Choose the Operating Point on one half of the documents, report it on the other

**Amends [ADR-0003](0003-recall-precision-on-one-cutoff.md)**, which said "No tuned operating point"
and removed all holding out because nothing was fitted. That stays true of the main report. This ADR
adds one thing that **is** chosen, and holds it out.

## The decision

The main report still reads the cascade at a fixed Cutoff of 0.5 and shows the whole curve. Next to it
sits one chosen reading, the **Operating Point**:

1. Split the 53 documents into two halves by a hash of the document id (`HALF_SALT = "halves-1"`).
   No random generator, so the split is the same every time.
2. On the **Selection Half**, take the **highest Cutoff, one shared by all seven Rules**, at which the
   Lost Provisions stay within the **Loss Budget**: a share of that half's Provisions, rounded down to
   a whole provision. Read at 1% and 2%.
3. Apply that Cutoff to the **Report Half** and read the Fully Binned share, the Lost Provisions and
   the cost there.
4. Do it both ways round, so every document is reported on exactly once, and pool the two readings.

It lives in `operating_point.py`, `operating_point_report.py` and `operating_point_cli.py`, and writes
`docs/operating-point.md`. Nothing that grades a run imports it (`tests/test_no_tuning.py`), so the 0.5
reading and the Cutoff Curve are untouched.

## Why

A legal team will not accept 10.3% of marked Provisions lost, which is what the 0.5 reading gives
(44 of 429). The reviewer's feedback was to state a tolerable loss (1 to 2%), choose the point for it,
and lead with how much Jev still skips there. Choosing a Cutoff from the curve is tuning, and a
headline tuned on the data it is reported on flatters itself, so it is chosen on one half and reported
on the other, as the reviewer asked. Both directions are used because with 53 documents either half
alone is a small sample and its answer depends on which documents it holds.

## What it found

At the 2% budget: 20.5% of Clauses skipped and 7 of 429 Provisions lost (1.6%). At the 1% budget:
7.7% skipped and 5 lost (1.2%), which is **above** the budget. The two directions disagree widely
(one skips 37% and loses 3.7%, the other skips 1% and loses nothing), and five of the seven Provisions
lost at the 2% budget are in one document whose Minimum Commitment highlights look like label noise.
`docs/operating-point.md` has the tables.

## Considered and rejected

- **Per-Rule Cutoffs**, each at its Free Saving point on the Selection Half (lose nothing there). Tried
  once while designing this, on a split with a different hash, from the same stored answers. Pooled
  over both directions it skipped about 41% of Clauses but lost about 5.4% of Provisions, over any
  budget, because each Rule's lowest safe point is decided by one Clause and does not hold on other
  documents. Not used, and not written into the code.
- **A hand-picked Cutoff** (say 0.1) read off the whole curve. That is the tuning this ADR avoids.
- **Many random splits, to show a spread.** The reviewer asked for one half against the other; two
  directions already show the instability, and a spread would add machinery to a result that is
  already unstable for a reason named above.
- **Dropping the Rule that decides the Cutoff** (Minimum Commitment). A Clause is skipped only when it
  is Binned for **every** Rule, so always escalating one Rule skips nothing.

## Consequences

- ADR-0003's "no tuned operating point" now reads: **the report's fixed-Cutoff reading and the Cutoff
  Curve tune nothing; the Operating Point does, and is held out.** `tests/test_no_tuning.py` keeps the
  grading modules from importing it and still forbids the words `fold`, `tune`, `threshold`, `random`
  and `shuffle` as identifiers in every module, this one included.
- The glossary term "operating point", previously on the avoid list, now means this and nothing else.
- The procedure was written after the full-data curve had been seen, so the pooled figure is not a
  fully blind test. The split in the code was the first one written and was not picked for its result.
- The saving in dollars is larger than the skipped share because a Clause sent on carries only the
  questions Jev said yes to, and the expensive model's answer length is assumed. The report gives the
  reading-only saving beside it, which does not depend on that assumption.
