# 11: Wording review and question-type pilot

**What to build:** choose how to ask Jev, using evidence.

1. **Wording review (human checkpoint):** present the drafted wording of all eight Detection Questions and the R2/R4/R6 sub-questions to the user. Stop until they approve or edit it.
2. **Pilot:** take about 300 Pairs, deliberately including clauses that touch highlights for every rule. Ask each as:
   - Jev yes/no
   - a 2-level score
   - a yes/no choice

   For R2, R4 and R6, also compare compound versus split questions.
3. **Pilot report:** for each type, how well P(yes) separates touching from non-touching clauses, and Keep Share at the 5% missed-highlight budget. Pick **one** question type for all rules, and record whether splitting helped.

**Blocked by:** 02, 10.

**Status:** ready-for-agent (contains a human checkpoint: the user approves the question wording before the pilot runs)

- [ ] The user has approved the final wording, and the Rulebook holds it.
- [ ] Pilot results are cached like any other run.
- [ ] A short pilot report compares the three types (and compound vs split) with counts, and states the chosen type.
- [ ] The pipeline's question type is set from the pilot's choice.
- [ ] The final report will disclose that the type was chosen on pilot Pairs that are later scored (a small selection leak).
