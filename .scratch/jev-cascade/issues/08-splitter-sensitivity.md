# 08: Splitter sensitivity check

**What to build:** the same pipeline and grading run on plain 120-word chunks instead of Clauses, shown side by side. Readers can then see whether the conclusions depend on how the text was cut.

**Blocked by:** 05.

**Status:** ready-for-agent

- [ ] A second unit maker produces 120-word chunks with the same output shape as Clauses.
- [ ] Jev is run (stub for now) on the chunks and cached under their own unit keys.
- [ ] Chunks go through the same folds, cutoff tuning and grading as Clauses.
- [ ] The report has one side-by-side table per rule, Clauses vs chunks, showing:
  - Keep Share in tokens
  - found, pending and missed highlights
  - False Alarms
- [ ] The report notes the design dry-run finding: chunks cut sentences and moved R8 by 11 highlights.
