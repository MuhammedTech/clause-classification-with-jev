# Question wording, type and heading: the ticket 08 sample

Model `jev-1.14.0`. 1357 Jev answers behind this report, all in the cache, so a rerun asks nothing and the report can be rebuilt with no network.

## Decision rules

Fixed before any real call. Both choices are made on **separation per Rule only**: the chance that a Clause holding a Highlight scores above one that does not, ties counting half. 1.0 is a perfect ranking, 0.5 is a coin.

- Compare the three types with the heading shown. Pick the highest mean separation across Rules, unless it beats `binary` by less than 0.02, in which case `binary` stands.
- Then ask the chosen type with the heading taken out. The heading comes out only if that beats heading-on by at least 0.02; otherwise it stays.
- A 95% paired bootstrap interval is printed beside each difference, so a reader can see whether it is inside the noise. It does not change the rule.
- **Binned Share and Precision are not read from this sample.** It is enriched with held Clauses and near misses, so its base rate is wrong and those figures do not transfer.

## The sample

Seed 20261113. Up to 20 held Clauses and 40 not-held Clauses per Rule, at most 4 from any one document, over all 53 documents. 50% of the not-held Clauses are near misses: they sit under the same section heading as a held Clause. Each Clause is asked only its own Rule's question, so one arm is 420 Pairs.

| Rule | Held | Not held | Near misses | Heading-affected Clauses |
| --- | --- | --- | --- | --- |
| R1 | 20 | 40 | 6 | 14 |
| R2 | 20 | 40 | 7 | 15 |
| R3 | 20 | 40 | 7 | 19 |
| R5 | 20 | 40 | 4 | 10 |
| R6 | 20 | 40 | 4 | 8 |
| R7 | 20 | 40 | 8 | 17 |
| R8 | 20 | 40 | 4 | 14 |

A heading-affected Clause is one whose Parent Line is a section heading. It is the only kind the heading setting can change; the others are the same prompt in both arms.

## Question type, heading shown

Separation, with held/not-held Clause counts in brackets.

| Rule | binary, heading on | score2, heading on | choice2, heading on |
| --- | --- | --- | --- |
| R1 | 0.979 (20/40) | 0.966 (20/40) | 0.971 (20/40) |
| R2 | 0.974 (20/40) | 0.977 (20/40) | 0.981 (20/40) |
| R3 | 0.998 (20/40) | 0.996 (20/40) | 0.998 (20/40) |
| R5 | 0.990 (20/40) | 0.976 (20/40) | 0.979 (20/40) |
| R6 | 0.949 (20/40) | 0.952 (20/40) | 0.938 (20/40) |
| R7 | 0.979 (20/40) | 0.964 (20/40) | 0.961 (20/40) |
| R8 | 0.993 (20/40) | 0.982 (20/40) | 0.982 (20/40) |
| **Mean** | **0.980** | **0.973** | **0.973** |

- `score2` minus `binary`, mean separation: -0.007 (95% interval -0.016 to +0.001): the interval spans zero, so the sample cannot tell the two apart.
- `choice2` minus `binary`, mean separation: -0.007 (95% interval -0.016 to -0.000): the interval is below zero.

**Chosen question type: binary**, for every Rule.

## Heading context

The chosen type, `binary`, with the section heading shown against taken out. A lead-in such as 'Licensee shall:' is shown in both.

| Rule | binary, heading on | binary, heading off |
| --- | --- | --- |
| R1 | 0.979 (20/40) | 0.976 (20/40) |
| R2 | 0.974 (20/40) | 0.979 (20/40) |
| R3 | 0.998 (20/40) | 0.997 (20/40) |
| R5 | 0.990 (20/40) | 0.990 (20/40) |
| R6 | 0.949 (20/40) | 0.949 (20/40) |
| R7 | 0.979 (20/40) | 0.978 (20/40) |
| R8 | 0.993 (20/40) | 0.993 (20/40) |
| **Mean** | **0.980** | **0.980** |

- Heading off minus heading on, mean separation: +0.000 (95% interval -0.002 to +0.002): the interval spans zero, so the sample cannot tell the two apart.

**Heading context: on**.

## What this does not show

- **Both choices were made on Pairs that the full run later scores.** That is a small selection leak: two settings, chosen on a sample of a few percent of the corpus. The final report says so.
- With 20 held and 40 not-held Clauses a Rule, one Rule's separation is uncertain by a few hundredths. The mean across Rules is steadier; the intervals above are the honest read.
- **Separation is near its ceiling here.** Every Rule scores at least 0.938 in every arm, so this sample has little room to tell the arms apart. Read 'no difference' as none detectable on this sample, not as none. In particular the harm a heading may do, stamping a section label on unrelated Clauses, would show over the corpus's many unrelated Clauses, and this sample holds only 40 near misses across all Rules.
- Held and not-held are CUAD's labels. A not-held Clause may hold a provision the lawyers did not mark, which depresses every arm's separation alike.
