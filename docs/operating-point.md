# Operating Point: the Cutoff a legal reader would accept

53 documents, 3,246 Clauses, 429 lawyer-marked Provisions, seven Rules, `jev-1.14.0`. Read from the stored answers; nothing is asked of Jev.

## Why this exists

The main report reads the cascade at a fixed Cutoff of 0.5. There Jev skips 77.3% of Clauses and loses 44 of 429 marked Provisions (10.3%). That is too many for a legal team. So: state a loss we can live with, choose the Cutoff for it, and say how much Jev still skips. Choosing a Cutoff is tuning, so it is done on one half of the documents and reported on the other (ADR-0007).

## Procedure

1. Split the documents in two by a hash of the document id. No random generator, so the split is the same every time.
2. On the **Selection Half**, take the highest Cutoff, **one shared by all seven Rules**, at which the Provisions Lost stay within the **Loss Budget**, a share of that half's Provisions.
3. Apply that Cutoff to the **Report Half** and read the skip, the loss and the cost there.
4. Do it both ways round, so every document is reported on exactly once, and pool the two readings.

## Loss Budget 1.0% of marked Provisions

| Chosen on | Cutoff | Skipped there | Lost there | Reported on | Skipped | Lost |
| --- | --- | --- | --- | --- | --- | --- |
| half 1 (30 docs) | 0.07 | 12.1% | 0/239 (0.0%) | half 2 (23 docs) | 249/1736 (14.3%) | 5/190 (2.6%) |
| half 2 (23 docs) | 0.03 | 0.1% | 0/190 (0.0%) | half 1 (30 docs) | 1/1510 (0.1%) | 0/239 (0.0%) |
| **Both, each document reported once** | | | | all 3,246 Clauses | **250/3,246 (7.7%)** | **5/429 (1.2%)** |

The pooled loss of 1.2% is **above** the 1.0% budget. The worse half lost 2.6%. Claude calls: 3,246 if everything is sent, 2,996 in the cascade (7.7% fewer). The two halves disagree, and the gap is the point: read the pooled row as the answer and the two rows above it as how far it can move.

## Loss Budget 2.0% of marked Provisions

| Chosen on | Cutoff | Skipped there | Lost there | Reported on | Skipped | Lost |
| --- | --- | --- | --- | --- | --- | --- |
| half 1 (30 docs) | 0.12 | 35.2% | 4/239 (1.7%) | half 2 (23 docs) | 646/1736 (37.2%) | 7/190 (3.7%) |
| half 2 (23 docs) | 0.04 | 1.2% | 3/190 (1.6%) | half 1 (30 docs) | 18/1510 (1.2%) | 0/239 (0.0%) |
| **Both, each document reported once** | | | | all 3,246 Clauses | **664/3,246 (20.5%)** | **7/429 (1.6%)** |

The pooled loss of 1.6% is within the 2.0% budget. The worse half lost 3.7%. Claude calls: 3,246 if everything is sent, 2,582 in the cascade (20.5% fewer). The two halves disagree, and the gap is the point: read the pooled row as the answer and the two rows above it as how far it can move.

## What it saves, per 1,000 Clauses

Against sending every Clause to Claude Sonnet 5.5, at list price, priced over the Report Halves and scaled to 1,000 Clauses. The Claude run was never made, so this is an estimate from token counts.

| Loss Budget | Skipped | Lost | Claude alone | Cascade (Claude + Jev) | Saved | Saved, share | Saved, reading only |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1.0% | 7.7% | 1.2% | $8.15 | $5.14 | **$3.00** | 36.9% | $0.05 (4.6%) |
| 2.0% | 20.5% | 1.6% | $8.15 | $3.92 | **$4.23** | 51.9% | $0.18 (15.7%) |

The saving is larger than the skipped share because a Clause that is sent on carries only the questions Jev said yes to, and the expensive model's answer length (100 tokens per question) is an assumption. The last column sets that answer length to zero, which is the saving from reading alone and does not depend on the guess.

## Where the 1.0%-budget losses sit

5 of the 5 Provisions Lost on the Report Halves are in one document, `SUMMAFOURINC_06_19_1998-EX-10.3-SOFTWARE LICE...`. By document:

| Document | Provisions Lost |
| --- | --- |
| SUMMAFOURINC_06_19_1998-EX-10.3-SOFTWARE LICE... | 5 |

## Where the 2.0%-budget losses sit

5 of the 7 Provisions Lost on the Report Halves are in one document, `SUMMAFOURINC_06_19_1998-EX-10.3-SOFTWARE LICE...`. By document:

| Document | Provisions Lost |
| --- | --- |
| SUMMAFOURINC_06_19_1998-EX-10.3-SOFTWARE LICE... | 5 |
| CoherusBiosciencesInc_20200227_10-K_EX-10.29_... | 1 |
| CytodynInc_20200109_10-Q_EX-10.5_11941634_EX-... | 1 |

## Read this before quoting a number

- **The budget is met on average, not on every half.** A Cutoff chosen to fit one half's budget exactly sits at the edge of that half's data, so on the other half it can lose more or less. The two directions above show by how much.
- **One document decides it, and its labels look wrong.** The lowest safe Cutoff is set by the weakest Rules, Minimum Commitment above all. The Minimum Commitment losses at Cutoffs of 0.05 and below are five Clauses of the SUMMAFOUR software licence, which are technical performance requirements (for example "fewer than 1 talkoff in 5 hours of voice"), not purchase or payment commitments. Read by hand on 14 Nov 2026. If those highlights are label noise, the losses here are overstated and the safe Cutoff is higher.
- **One shared Cutoff.** Per-Rule Cutoffs were tried while designing this and are not used: see ADR-0007.
- **The procedure was chosen after the full-data curve was seen.** The 1% and 2% budgets and the shared Cutoff were picked knowing roughly where the curve sits, and a prototype on a different split was looked at while designing this. The split used here (`halves-1`) was the first one written into the code and was not picked for its result, but the pooled figure is not a perfectly blind test. The choice of the Cutoff itself is held out.
- **Cost is an estimate.** The expensive model was never run. Tokens are characters divided by 4 and its answer length is assumed. See `report.md`, Cost and time.
- **53 license agreements only.** Nothing here says how it does on other contract types.
