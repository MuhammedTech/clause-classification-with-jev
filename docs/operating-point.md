# Operating Point: the Cutoff a legal reader would accept

53 documents, 3,246 Clauses, 378 lawyer-marked Provisions, six Rules, `jev-1.14.0`. Read from the stored answers; nothing is asked of Jev.

## Why this exists

The main report reads the cascade at a fixed Cutoff of 0.5. There Jev skips 78.5% of Clauses and loses 26 of 378 marked Provisions (6.9%). That is too many for a legal team. So: state a loss we can live with, choose the Cutoff for it, and say how much Jev still skips. Choosing a Cutoff is tuning, so it is done on one half of the documents and reported on the other (ADR-0007).

## Procedure

1. Split the documents in two by a hash of the document id. No random generator, so the split is the same every time.
2. On the **Selection Half**, take the highest Cutoff, **one shared by all {_rules_in_words()} Rules**, at which the Provisions Lost stay within the **Loss Budget**, a share of that half's Provisions.
3. Apply that Cutoff to the **Report Half** and read the skip, the loss and the cost there.
4. Do it both ways round, so every document is reported on exactly once, and pool the two readings.

## Loss Budget 1.0% of marked Provisions

| Chosen on | Cutoff | Skipped there | Lost there | Reported on | Skipped | Lost |
| --- | --- | --- | --- | --- | --- | --- |
| half 1 (30 docs) | 0.07 | 12.5% | 0/218 (0.0%) | half 2 (23 docs) | 253/1736 (14.6%) | 0/160 (0.0%) |
| half 2 (23 docs) | 0.17 | 55.0% | 1/160 (0.6%) | half 1 (30 docs) | 770/1510 (51.0%) | 4/218 (1.8%) |
| **Both, each document reported once** | | | | all 3,246 Clauses | **1,023/3,246 (31.5%)** | **4/378 (1.1%)** |

The pooled loss of 1.1% is **above** the 1.0% budget. The worse half lost 1.8%. Claude calls: 3,246 if everything is sent, 2,223 in the cascade (31.5% fewer). The two halves disagree, and the gap is the point: read the pooled row as the answer and the two rows above it as how far it can move.

## Loss Budget 2.0% of marked Provisions

| Chosen on | Cutoff | Skipped there | Lost there | Reported on | Skipped | Lost |
| --- | --- | --- | --- | --- | --- | --- |
| half 1 (30 docs) | 0.20 | 56.3% | 4/218 (1.8%) | half 2 (23 docs) | 1041/1736 (60.0%) | 2/160 (1.2%) |
| half 2 (23 docs) | 0.37 | 74.6% | 3/160 (1.9%) | half 1 (30 docs) | 1056/1510 (69.9%) | 14/218 (6.4%) |
| **Both, each document reported once** | | | | all 3,246 Clauses | **2,097/3,246 (64.6%)** | **16/378 (4.2%)** |

The pooled loss of 4.2% is **above** the 2.0% budget. The worse half lost 6.4%. Claude calls: 3,246 if everything is sent, 1,149 in the cascade (64.6% fewer). The two halves disagree, and the gap is the point: read the pooled row as the answer and the two rows above it as how far it can move.

## What it saves, per 1,000 Clauses

Against sending every Clause to Claude Sonnet 5.5, at list price, priced over the Report Halves and scaled to 1,000 Clauses. The Claude run was never made, so this is an estimate from token counts.

| Loss Budget | Skipped | Lost | Claude alone | Cascade (Claude + Jev) | Saved | Saved, share | Saved, reading only |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1.0% | 31.5% | 1.1% | $7.11 | $2.43 | **$4.68** | 65.8% | $0.28 (25.0%) |
| 2.0% | 64.6% | 4.2% | $7.11 | $1.04 | **$6.07** | 85.4% | $0.59 (53.5%) |

The saving is larger than the skipped share because a Clause that is sent on carries only the questions Jev said yes to, and the expensive model's answer length (100 tokens per question) is an assumption. The last column sets that answer length to zero, which is the saving from reading alone and does not depend on the guess.

## Where the 1.0%-budget losses sit

2 of the 4 Provisions Lost on the Report Halves are in one document, `PACIRA PHARMACEUTICALS, INC. - A_R STRATEGIC ...`. By document:

| Document | Provisions Lost |
| --- | --- |
| PACIRA PHARMACEUTICALS, INC. - A_R STRATEGIC ... | 2 |
| EhaveInc_20190515_20-F_EX-4.44_11678816_EX-4.... | 1 |
| MusclepharmCorp_20170208_10-KA_EX-10.38_98935... | 1 |

## Where the 2.0%-budget losses sit

5 of the 16 Provisions Lost on the Report Halves are in one document, `PACIRA PHARMACEUTICALS, INC. - A_R STRATEGIC ...`. By document:

| Document | Provisions Lost |
| --- | --- |
| PACIRA PHARMACEUTICALS, INC. - A_R STRATEGIC ... | 5 |
| CHANGEPOINTCORP_03_08_2000-EX-10.6-LICENSE AN... | 3 |
| GluMobileInc_20070319_S-1A_EX-10.09_436630_EX... | 3 |

## Read this before quoting a number

- **The budget is met on average, not on every half.** A Cutoff chosen to fit one half's budget exactly sits at the edge of that half's data, so on the other half it can lose more or less. The two directions above show by how much.
- **The Rule set was changed after the results were seen.** Minimum Commitment (R6) was removed after the real run, because Jev separated it worst and its marked Provisions could not be checked: there is no lawyer and there is no more data. This departs from the Rules agreed beforehand and makes every figure on this page more favourable than a Rule set fixed in advance. The Cutoff is still chosen on one half and read on the other, but the Rule set is not held out. See ADR-0008 for the same run over all seven Rules.
- **A few documents decide it.** Read the tables above: the losses sit in a handful of contracts, so another sample of contracts could move the figure a long way.
- **One shared Cutoff.** Per-Rule Cutoffs were tried while designing this and are not used: see ADR-0007.
- **The procedure was chosen after the full-data curve was seen.** The 1% and 2% budgets and the shared Cutoff were picked knowing roughly where the curve sits, and a prototype on a different split was looked at while designing this. The split used here (`halves-1`) was the first one written into the code and was not picked for its result, but the pooled figure is not a perfectly blind test. The choice of the Cutoff itself is held out.
- **Cost is an estimate.** The expensive model was never run. Tokens are characters divided by 4 and its answer length is assumed. See `report.md`, Cost and time.
- **53 license agreements only.** Nothing here says how it does on other contract types.
