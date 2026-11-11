# 04: Complete grading

**What to build:** the full two-question grading from ADR-0002.

- **Touch:** a clause touches a highlight when they share any text, or when the clause sits directly under a Lead-in that is itself the whole highlight.
- **Found Highlight:** any touching clause is kept as "yes".
- **Pending Highlight:** no touching clause is kept as "yes", but at least one is Escalated.
- **Missed Highlight:** every touching clause is kept as "no".
- **False Alarm:** a clause kept as "yes" that touches no highlight of that rule.

The report adds precision on kept "yes" answers, the labelled upper-bound line (the expensive model gets every escalated pair right), and a list of every Lead-in case.

**Blocked by:** 03.

**Status:** ready-for-agent

- [ ] Evaluator tests (Seam A) cover:
  - one highlight across three clauses with one kept "yes" → found once
  - all touching clauses kept "no" → missed
  - one touching clause escalated and none kept "yes" → pending
  - a one-character overlap counts as touching
  - a highlighted Lead-in makes its direct sub-items touch
  - a kept "yes" on a sub-item under a highlighted Lead-in is not a False Alarm
  - a kept "yes" touching no highlight is a False Alarm
- [ ] The report shows found/pending/missed counts and the Miss Rate per rule, False Alarms, kept-"yes" precision, and the upper-bound line labelled as an upper bound.
- [ ] The report lists every Lead-in case (document, rule, highlight text).
- [ ] No per-clause gold label or overlap threshold exists anywhere in the code.
