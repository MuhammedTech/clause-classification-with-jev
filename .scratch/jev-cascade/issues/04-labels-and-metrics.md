# 04: Overlap labels and the metrics

**What to build:** the pure Evaluator from ADR-0003.

**Labels.** A Clause *holds* a Highlight when their character ranges overlap by one character or more.
No threshold. A Clause holding nothing is a **Certified Negative** if its document is `is_impossible`
for that Rule, otherwise an **Inferred Negative**.

**At one Cutoff**, a Pair at or below it is **Binned** and above it is **Escalated**. Then:

- **Clause Recall** — of Clauses holding a Highlight, the share Escalated.
- **Provision Recall** — of Highlights, the share with at least one holding Clause Escalated.
- **Precision** — of Escalated Clauses, the share holding a Highlight.
- **Lost Provisions** — Highlights whose every holding Clause was Binned.
- **Binned Share** — the share of contract **words** Binned.
- **Fully Binned Clause share** — Clauses Binned for all seven Rules.
- **False-alarm rate on Certified Negative documents**, reported separately from Precision.

Every figure carries its counts. The Evaluator takes Clauses, Highlights, the P(yes) table and a
Cutoff, and returns these. It is pure: no folds, no tuning, no randomness.

**Blocked by:** 03.

**Status:** ready-for-agent

- [ ] Evaluator tests (Seam A) cover:
  - a one-character overlap counts as holding
  - a Highlight across three Clauses with one Escalated is not Lost
  - the same Highlight with all three Binned is Lost, counted once
  - Provision Recall exceeds Clause Recall on that case
  - Precision counts Escalated Clauses, not Highlights
  - Binned Share counts words, not Clauses
  - a Fully Binned Clause needs every Rule Binned
  - Certified Negative and Inferred Negative Clauses are counted separately
- [ ] The report shows all of the above per Rule, each beside its counts.
- [ ] No Cutoff tuning, fold assignment or overlap threshold exists anywhere in the code.
- [ ] The report states that Precision reads in single digits by arithmetic at a ~1% base rate, and
      prints each Rule's base rate beside it.
