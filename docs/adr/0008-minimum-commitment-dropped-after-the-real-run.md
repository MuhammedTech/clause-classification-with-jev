# Minimum Commitment is dropped after the real run, knowing how it performed

**Amends [ADR-0005](0005-seven-rules-one-question-each.md)**, which fixed seven Rules and had the user
approve their wording. **This departs from the Rule set agreed with the reviewer, and it was decided
after the results for that Rule set had been seen.** Read the figures over six Rules with that in mind.

## The decision

The Rulebook now holds **six** Rules: R1, R2, R3, R5, R7, R8. **R6, Minimum Commitment, is out.** It
moves to `DROPPED_RULES` beside R4, with its own reason in `DROPPED_REASONS`. The id gap stays so the
ids remain comparable with the earlier notes and with the real run's cache.

It is not out for the gate: at 17 documents and 51 Highlights it passes, with room. It is not out for
independence, which is R4's ground. It is out for two reasons that are both about this data:

1. **Jev could not separate it.** At the 0.5 Cutoff it loses 18 of its 51 Highlights, more than any
   other Rule. Alone, R1, R2, R3, R5 and R8 could each skip 87 to 98% of Clauses within 2% of their own
   marked provisions lost, and R7 81%; Minimum Commitment could skip only 50% (full-data readings, not
   held out, made while diagnosing).
2. **Its labels could not be checked.** Some of the Highlights Jev missed read as technical performance
   requirements ("fewer than 1 talkoff in 5 hours of voice", in the SUMMAFOUR licence) rather than
   purchase or payment commitments, so they look like label noise. There is no lawyer to say, and no
   more data to set against them.

The user decided this with that information in hand: there is no lawyer and no more data, and this
was the Rule causing the trouble.

## What this changes, said plainly

- **It breaks the agreement.** The Rule set was agreed with the reviewer before the run. Removing a Rule
  after seeing its results is a choice made on the test data, so every figure over six Rules is more
  favourable than one from a Rule set fixed in advance. The Cutoff is still chosen on one half and read
  on the other (ADR-0007); the Rule set is not held out.
- **The seven-Rule figures stay on record,** because they are the figures for the Rule set that was
  agreed. They are in the table below, in this ADR, and in the commit history before this change.
- **Always escalating one Rule skips nothing.** A Clause is skipped only when it is Binned for every
  Rule, which is why one weak Rule cost the whole cascade (ADR-0007 considered and rejected dropping
  it; this ADR reverses that, for the reasons above, after the user's decision).

## The two readings side by side

| | Seven Rules (agreed) | Six Rules (this ADR) |
| --- | --- | --- |
| Provisions marked | 429 | 378 |
| Fixed Cutoff of 0.5 | 77.3% skipped, 44 lost (10.3%) | 78.5% skipped, 26 lost (6.9%) |
| 1% budget, held out | 7.7% skipped, 5 lost (1.2%) | **31.5% skipped, 4 lost (1.1%)** |
| 2% budget, held out | 20.5% skipped, 7 lost (1.6%) | 64.6% skipped, **16 lost (4.2%)** |
| Saved per 1,000 Clauses | $4.23 of $8.15 at the 2% budget | $4.68 of $7.11 at the 1% budget |

Both budgets are chosen on one half of the documents and read on the other, both ways round, and pooled
(`docs/operating-point.md` for six Rules).

## What it found

- **The six-Rule 1% reading meets the reviewer's ask**: aim for 1%, got 1.1%, skipping 31.5% of Clauses.
  The seven-Rule 2% reading also met it, skipping 20.5% and losing 1.6%.
- **The six-Rule 2% reading did not hold.** The Cutoff chosen on one half lost 4.2% pooled and 6.4% on
  the worse half. Do not quote its 64.6% skipped without that loss beside it.
- **Dropping R6 did not make the answer stable.** Which half chooses the Cutoff moves the skip from
  14.6% to 51.0% at the 1% budget.
- **No single Rule dominates the six-Rule losses.** On the report halves, at the 1% budget R7 (Change Of
  Control) lost 3 of the 4 and R8 lost 1. At the 2% budget R7 lost 5 of the 16, R1 4, R2 3, R8 3 and R5
  1. R7 is the largest owner and is **not** dropped; that is a decision for the user, and a second
  Rule removed after seeing results would make the six-Rule figures harder to defend, not easier.
- **The losses sit in few documents.** PACIRA holds 2 of the 4 losses at 1% and 5 of the 16 at 2%. Its
  labels were not read to explain them away.

## Costs and what the cost figures mean

- **The baseline falls from $8.15 to $7.11 per 1,000 Clauses** only because Claude would be asked six
  questions, not seven. That is not a saving, and the two baselines must not be set against each other.
- **Jev's own cost still includes the R6 question.** The real run asked all seven questions in each of
  3,246 fan-out calls; its measured 2,019,752 input tokens, 179 s and $0.085 are for those calls. The
  six-Rule figures use it unchanged, which is conservative: asking six questions would cost slightly less.
- **The six-Rule P(yes) came from seven-question calls.** ADR-0006 notes a probability can move when
  other questions ride in the same call. A fresh six-question run could give slightly different
  numbers. It was not made.
- **The cache is untouched.** It still holds all 22,722 Pairs; the six-Rule reading uses 19,476 of them
  and ignores R6's rows. Nothing was deleted, and nothing was asked of Jev again.

## Considered and rejected

- **Keeping R6 and flagging the SUMMAFOUR highlights as noise.** That needs a lawyer to say they are
  noise. Without one it is a guess, and the first rescue of the result would be a second.
- **Dropping R7 as well.** See above: it leads the losses but does not dominate, and the user has not
  decided it.
- **Re-asking Jev with six questions.** Possible and cheap (the seven-question run cost $0.085), but it would add a third
  reading to explain, and the user decided on the cached run.

## Consequences

- `rulebook.py`, the corpus gate (now six rows, 378 Highlights), the report (it prints R6 under its
  dropped Rules, says it was dropped after the real run, and counts its Rules from the Rulebook), the
  Operating Point page and several tests now describe six Rules. The tests assert the new facts
  instead of the old; none was deleted to make the suite pass.
- `docs/operating-point.md` carries a bullet, generated from the Rulebook, saying the Rule set was
  changed after results were seen.
- ADR-0007 is not rewritten; it records the seven-Rule run it was written for, with a pointer here.
