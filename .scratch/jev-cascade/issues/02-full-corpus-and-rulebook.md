# 02: Full corpus and full Rulebook

**What to build:** the report covers the whole License Agreement Set and all eight Rules.

- **Corpus:** the 53 documents whose CSV `Document Name` contains "licen", with Pacira matched despite "A&R" (CSV) vs "A_R" (JSON).
- **Rulebook:** eight positively phrased Detection Questions:
  - R1 Cap On Liability
  - R2 Post-Termination Services
  - R3 Termination For Convenience
  - R4 Uncapped Liability (carve-outs from a cap, or unlimited liability)
  - R5 Exclusivity
  - R6 Minimum Commitment
  - R7 Change Of Control
  - R8 Anti-Assignment
- **Sub-questions:** R2, R4 and R6 are asked as sub-questions, and the rule's P(yes) is the highest of its sub-questions.
- **Gate:** the report shows each rule's gate check: ≥ 15 documents with a highlight and ≥ 25 highlights. A rule that fails is swapped for the next backup (Audit Rights, then IP Ownership Assignment), and the swap is reported.

**Blocked by:** 01.

**Status:** ready-for-agent

- [ ] The corpus loads exactly 53 documents, including Pacira, and the report states the filter and the Pacira fix.
- [ ] All eight Rules appear in the report with counts.
- [ ] The Rulebook holds drafted wording for every Detection Question and sub-question, ready for the user's review in ticket 11.
- [ ] An Evaluator test shows a compound rule's P(yes) is the maximum of its sub-questions.
- [ ] The gate check is computed and shown per rule. A test shows a rule below the gate is replaced by the backup.
- [ ] Highlight totals per rule match the design facts: 455 across the eight rules; R4 has 17 documents and 26 highlights.
