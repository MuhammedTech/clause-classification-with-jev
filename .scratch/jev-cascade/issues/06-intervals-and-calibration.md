# 06: Confidence intervals and calibration

**What to build:** uncertainty and calibration in the report.

- **Intervals:** every rate gets a 95% interval from a bootstrap over documents (about 1,000 resamples). A contract, not a clause, is the unit of luck.
- **Calibration:** each rule gets a calibration chart and an expected calibration error (ECE), using "the clause touches a highlight of that rule" as the outcome. This independently checks TypeSafe's calibration claim.

**Blocked by:** 05.

**Status:** ready-for-agent

- [ ] Every rate in the per-rule tables shows a 95% document-bootstrap interval next to its counts.
- [ ] An Evaluator test shows the bootstrap resamples documents, not clauses: a document's clauses always move together.
- [ ] A calibration chart per rule is written as a PNG and referenced from the report, with the ECE number beside it.
- [ ] An Evaluator test shows ECE is 0 for perfectly calibrated synthetic P(yes) and positive for miscalibrated ones.
