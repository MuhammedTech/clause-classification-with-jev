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
2. **Its labels could not be checked** (this was the reason as given at the time; see "Checked
   afterwards" below, which shows it was only partly true). Some of the Highlights Jev missed read as
   technical performance requirements ("fewer than 1 talkoff in 5 hours of voice", in the SUMMAFOUR
   licence) rather than purchase or payment commitments, so they look like label noise. There is no
   lawyer to say, and no more data to set against them.

The user decided this with that information in hand: there is no lawyer and no more data, and this
was the Rule causing the trouble.

## Checked afterwards (2026-11-14): the reason above was incomplete

The decision was made after looking closely at one document (SUMMAFOUR). Every one of the 51 Highlights
was read afterwards, against CUAD's own text and the cached answers in `out/real/pyes.jsonl`. A
Highlight counts as lost when the highest P(yes) over the Clauses holding it is 0.5 or below, which
reproduces the 18 of 51. These are full-data readings at the fixed 0.5 Cutoff, not held out.

Of the 18 lost Highlights:

- **5 are labels that are wrong on any reading.** All five are in SUMMAFOUR, a phone-tone-detector
  licence: technical tables (columns headed "Minimum Maximum Unit"), a "Minimum response time" table
  and "fewer than 1 talkoff in 5 hours of voice (minimum tone duration 400 ms)". Jev scored them 0.04
  to 0.05. None is a commitment to buy, pay or deliver anything. This needed reading, not a lawyer.
- **13 are minimum targets or obligations that the question did not ask about.** Coherus 3, CytoDyn 3,
  Ehave 2, Glu Mobile 2, and one each in MusclePharm, Euromedia and SUMMAFOUR (a minimum of five years of
  support). Examples: annual revenue of $500,000 below which exclusivity ends, market-penetration
  targets, "at least fifty (50) signed items for each Contract Year", "not less than ten (10) Licensed
  Programs". CUAD's lawyers marked these. The Detection Question was "Does this clause commit a party to
  a minimum purchase, payment or volume?", narrower than what was marked. CUAD's own question for the
  category is narrower still ("minimum order size or minimum amount or units per-time period that one
  party must buy"), and the lawyers' marks are broader than that too, so the label itself is loose.
  Several are fragments ("Licensee commits to:", "CytoDyn shall have the right to terminate ... on the
  occurrence of any of the following:") whose figures sit in the next Clause, which Jev never saw.
- **Jev did well on what the question did ask about.** 33 of the 51 Highlights score above 0.5, mostly
  minimum royalties and guaranteed payments (0.59 to 0.92).

What this changes about the reasons above:

- **Reason 2 stands only for 5 of the 18.** Those are label noise. The other 13 are a mismatch between a
  narrow question and loosely drawn labels, which is a Rulebook problem, not a ground-truth problem.
- **Label noise does not explain the result.** With the 5 wrong labels set aside, R6 still loses 13 of
  46 Highlights at 0.5 (28%), still more than any other Rule (R7 loses 8, R8 6).
- **Reason 1 is mostly the question's wording.** "Jev could not separate it" is true of this question,
  not shown for the category.
- **Rewording was not tried.** ADR-0005 said that if R2 or R6 trailed, splitting or rewording them was
  the first thing to try. That was not done before R6 was dropped, and re-asking one Rule would cost
  cents (the whole seven-question run cost $0.085). R6 was dropped, not fixed.

The decision stands as made and the figures over six Rules stay post-hoc and more favourable than a
Rule set fixed in advance. Whether to reword R6 and bring it back is open and is the user's call.

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
- **R7 (Change Of Control) leads the six-Rule losses.** On the report halves, at the 1% budget it lost
  3 of the 4 (R8 lost the other 1), which at the headline budget is most of them. At the 2% budget R7
  lost 5 of the 16, ahead of R1 4, R2 3, R8 3 and R5 1. R7 was **kept deliberately**: dropping it too
  would be a second removal made after seeing results, and would make the six-Rule figures harder to
  defend, not easier. Whether to drop it is the user's decision, not settled here.
- **The losses sit in few documents.** PACIRA holds 2 of the 4 losses at 1% and 5 of the 16 at 2%. Its
  labels were not read to explain them away.

## Costs and what the cost figures mean

- **The baseline falls from $8.15 to $7.11 per 1,000 Clauses** only because Claude would be asked six
  questions, not seven. That is not a saving, and the two baselines must not be set against each other.
- **What Jev actually billed is for seven questions.** The real run asked all seven in each of 3,246
  fan-out calls; its measured 2,019,752 input tokens, 179 s and $0.085 are for those calls and are
  reported as measured, so they slightly overstate a six-question run. The *estimated* Jev part in the
  cost tables is recomputed for six questions per Clause ($0.231 over the run, against $0.27 for seven).
- **The six-Rule P(yes) came from seven-question calls.** ADR-0006 notes a probability can move when
  other questions ride in the same call. A fresh six-question run could give slightly different
  numbers. It was not made.
- **The cache is untouched.** It still holds all 22,722 Pairs; the six-Rule reading uses 19,476 of them
  and ignores R6's rows. Nothing was deleted, and nothing was asked of Jev again.

## Considered and rejected

- **Keeping R6 and declaring the SUMMAFOUR highlights label noise.** At the time this was judged to need
  a lawyer. Reading them later shows 5 of them are not commitments on any reading (see "Checked
  afterwards"), but setting them aside would still be an after-the-fact rescue of the result, and R6
  would still lose 13 of 46.
- **Rewording or splitting R6's question.** Not considered when R6 was dropped; ADR-0005 named it as the
  first remedy. See "Checked afterwards".
- **Dropping R7 as well.** See above: it leads the losses and is the user's call, not made here, and a
  second removal after seeing results would weaken the figures further.
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
