# 05: Two cutoffs with cross-fitting

**What to build:** honest per-rule results.

- **Folds:** documents go into five Folds, stratified so every Fold holds a fair share of each rule's highlighted documents, with a fixed seed.
- **Cutoffs:** for each Fold and rule, tune on the other four Folds:
  - **Lower Cutoff:** the highest value whose missed highlights are ≤ 5% of highlights.
  - **Upper Cutoff:** the lowest value whose False Alarms are ≤ 20% of kept "yes" answers.

  Ties go toward keeping less work.
- **Scoring:** apply each Fold's cutoffs to that Fold, then pool the five reported Folds.
- **Report:** Keep Share in tokens (with unit counts alongside), Fully Cleared Clauses, the five per-fold cutoffs per rule, and the keep-share-versus-miss-rate curve per rule.

**Blocked by:** 04.

**Status:** ready-for-agent

- [ ] Evaluator tests (Seam A) cover:
  - the Lower Cutoff respects the 5% missed-highlight budget on tuning data
  - the Upper Cutoff respects the 20% False Alarm budget
  - a Fold is never scored with cutoffs tuned on any of its own documents
  - stratification gives every Fold at least one highlighted document per rule when the data allows
  - Keep Share counts tokens, not units
  - a Fully Cleared Clause needs every rule kept
- [ ] The fold seed and the per-fold cutoffs appear in the report.
- [ ] A keep-share-versus-miss-rate chart per rule is written as a PNG and referenced from the report.
- [ ] All headline numbers come from pooled held-out Folds only.
