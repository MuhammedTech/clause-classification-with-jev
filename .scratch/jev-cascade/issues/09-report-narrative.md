# 09: Report narrative

**What to build:** the finished report a reader can follow without the design conversation. It adds:

- a "How grading works" section: highlights as ground truth, the touch rule, Found/Pending/Missed Highlights, False Alarms, Lead-in cases, and the fact that labels are derived from offsets
- the corpus section: the filter, the Pacira fix, and how it relates to the 44- and 33-document subsets
- a note that R5 and R8 replaced Non-Compete and Volume Restriction, and why (the gate)
- R1/R4 co-occurrence: documents and clauses with both, and highlights sharing text
- vendor caveats: TypeSafe's calibration evaluations were self-run, and its documented prompt-injection limitation
- a short "What Jev took off the expensive model" summary at the top, leading with counts

**Blocked by:** 06, 07, 08.

**Status:** ready-for-agent

- [ ] The report opens with a per-rule summary: Keep Share (tokens), missed highlights (count of total), and False Alarms, each with intervals.
- [ ] Every section above is present and uses `GLOSSARY.md` vocabulary.
- [ ] Every rate in the report has its count next to it.
- [ ] The end-to-end test (Seam C) checks the report contains each section heading.
- [ ] Rebuilding the report from the cache needs no network access.
