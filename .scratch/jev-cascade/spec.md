Status: ready-for-agent

# Spec: Jev cascade on CUAD license agreements

## Problem Statement

Reviewing contracts clause by clause with a strong LLM is expensive. Jev is a cheap decision model that answers a typed question about a clause with a probability. I want to know, per rule, how much of the clause-review work Jev could take off the expensive model by answering on its own when it is sure, and what that costs in missed provisions and false alarms, judged against lawyer highlights rather than against another model. Today I have only notes, a dataset, and claims from TypeSafe and third-party write-ups that disagree with each other; I have no reproducible measurement on contracts.

## Solution

A reproducible pipeline over the 53-document License Agreement Set from CUAD v1 that:

- splits each contract into Clauses,
- asks Jev one Detection Question per (clause, rule) Pair and caches every P(yes),
- grades Jev against the lawyers' highlights with two questions — was each highlight found, and was each confident "yes" justified — never against a per-clause gold label,
- tunes a Lower Cutoff and an Upper Cutoff per rule with 5-fold document cross-fitting, so every number is reported on documents its cutoffs never saw,
- and produces one Markdown report with per-rule counts, Keep Share in tokens, estimated savings versus a named expensive model, calibration, and timing.

The headline per rule: what share of the text Jev handles alone, how many highlights it misses doing so, and how many false alarms it raises.

## User Stories

1. As the researcher, I want the License Agreement Set defined as the 53 documents whose CSV `Document Name` contains "licen", so that the corpus matches my notes and is reproducible.
2. As the researcher, I want Pacira matched despite its name differing between the CSV ("A&R") and the JSON ("A_R"), so that a naming artifact does not silently drop a 22k-word document with 35 relevant highlights.
3. As the researcher, I want the corpus filter and the Pacira fix stated in the report, so that a reader can reconcile it with other subsets (44 by filename, 33 by CUAD's official type).
4. As the researcher, I want each contract split into Clauses at numbered and lettered items (`1.`, `1.1`, `(a)`, `(iv)`), so that Jev judges units a lawyer would recognise.
5. As the researcher, I want the splitter to recognise numbering that appears mid-line, so that contracts whose text extraction ran items together (Eton) are not left as one giant unit.
6. As the researcher, I want the splitter to recognise spaced dotted numbering such as `2. 3. 1.`, so that contracts like Telkom split correctly.
7. As the researcher, I want table rows and numbers that are not item markers (prices, quantities, years) not to start Clauses, so that pricing tables (Glu Mobile) do not become fake Clauses.
8. As the researcher, I want short list items such as "(1) United Kingdom;" kept as Clauses, so that list structure survives.
9. As the researcher, I want the build to fail if any Clause exceeds 600 words, so that giant units are fixed in the splitter rather than tolerated.
10. As the researcher, I want the share of highlights that sit inside exactly one Clause reported and checked to be about 97% or more, so that I know the splitter respects the lawyers' spans.
11. As the researcher, I want every sub-item to carry its parent's Lead-in, so that Jev judging "(a) for fraud" sees what it is an exception to.
12. As the researcher, I want the prepended Lead-in to be shown to Jev but never used in grading, so that context cannot make a Clause count as touching a highlight it does not touch.
13. As the researcher, I want the token growth from prepending Lead-ins reported, so that the cost of context is visible.
14. As the researcher, I want the Rulebook fixed at eight Rules, each a positively phrased yes/no Detection Question mapped to one CUAD category, so that results compare across rules.
15. As the researcher, I want R1 to ask whether a clause caps or limits a party's liability (Cap On Liability).
16. As the researcher, I want R2 to ask whether a clause requires help or obligations after termination (Post-Termination Services).
17. As the researcher, I want R3 to ask whether a clause lets a party terminate without cause (Termination For Convenience).
18. As the researcher, I want R4 to ask whether a clause carves exceptions out of a liability cap or makes liability unlimited (Uncapped Liability), so that the rule measures carve-outs, which is how uncapped liability actually appears in these contracts.
19. As the researcher, I want R5 to ask whether a clause grants or requires exclusivity (Exclusivity), replacing Non-Compete, which has too few documents.
20. As the researcher, I want R6 to ask whether a clause commits a party to a minimum purchase, payment or volume (Minimum Commitment).
21. As the researcher, I want R7 to ask whether a clause gives a right or trigger on change of control (Change Of Control).
22. As the researcher, I want R8 to ask whether a clause restricts assigning or transferring the agreement (Anti-Assignment), replacing Volume Restriction, which has too few documents.
23. As the researcher, I want the report to say that R5 and R8 changed meaning from my notes, so that nobody compares them to the old rules.
24. As the researcher, I want each Rule gated at ≥ 15 documents with a highlight and ≥ 25 highlights, and a failing Rule replaced by a backup (Audit Rights, then IP Ownership Assignment), so that no reported number rests on a handful of contracts.
25. As the researcher, I want to review the drafted wording of every Detection Question before the real Jev run, so that the questions say what I mean.
26. As the researcher, I want compound Rules (R2, R4, R6) asked as separate sub-questions and combined by taking the highest P(yes), so that Jev answers simple questions, which third-party tests show it does much better on.
27. As the researcher, I want a pilot of about 300 Pairs, deliberately including highlighted clauses for every rule, that compares Jev's yes/no type, a two-level score, and a yes/no choice, and compares compound versus split questions, so that the question format is chosen by evidence.
28. As the researcher, I want one question type chosen for all rules from the pilot, and the small selection leak disclosed, so that the design stays simple and honest.
29. As the researcher, I want Jev called through a client interface with a stub implementation, so that the whole pipeline can be built and tested before my Jev key arrives.
30. As the researcher, I want the real Jev client added as its own piece of work once I provide the key, so that the stub-to-real swap touches nothing else.
31. As the researcher, I want every P(yes) cached to disk with its clause, rule, sub-question, question type and model version, so that re-running the evaluation never calls Jev again.
32. As the researcher, I want an interrupted Jev run to resume from the cache, so that a rate-limit failure does not cost a full rerun.
33. As the researcher, I want wall-clock time recorded for the Jev run, so that I can report time per 1,000 clauses.
34. As the researcher, I want a highlight counted as a Found Highlight when any clause it touches is kept as "yes", so that one provision spanning several clauses counts once.
35. As the researcher, I want a highlight counted as a Pending Highlight when none of its touching clauses is kept as "yes" but at least one is Escalated, so that work handed to the expensive model is not counted as a miss.
36. As the researcher, I want a highlight counted as a Missed Highlight only when every clause it touches is kept as "no", so that a miss means nobody would ever look at that provision.
37. As the researcher, I want a clause kept as "yes" counted as a False Alarm only when it touches no highlight of that rule, so that no overlap threshold is needed.
38. As the researcher, I want clauses directly under a highlighted Lead-in to count as touching that highlight, so that Jev is not penalised when a lawyer highlighted only "Licensee commits to:".
39. As the researcher, I want every Lead-in case listed in the report, so that a reader can check them by eye.
40. As the researcher, I want two cutoffs per rule on P(yes): pairs at or below the Lower Cutoff are kept as "no", at or above the Upper Cutoff kept as "yes", and anything between Escalated, so that I can be strict on "no" and relaxed on "yes".
41. As the researcher, I want the Lower Cutoff tuned as the highest value whose Miss Rate on the tuning folds is ≤ 5% of highlights, so that missing provisions is tightly bounded.
42. As the researcher, I want the Upper Cutoff tuned as the lowest value whose False Alarms on the tuning folds are ≤ 20% of kept "yes" answers, so that weak "yes" answers are not all kept.
43. As the researcher, I want documents assigned to five Folds stratified so each Fold holds a fair share of every rule's highlighted documents, with a fixed seed, so that no Fold has zero cases of any rule.
44. As the researcher, I want each Fold reported with cutoffs tuned on the other four, and the five reported Folds pooled, so that every document is reported once and never with cutoffs tuned on itself.
45. As the researcher, I want the five per-fold cutoffs for each rule reported, so that I can see whether a rule's cutoff is stable.
46. As the researcher, I want confidence intervals from a bootstrap over documents, so that intervals treat a contract, not a clause, as the unit of luck.
47. As the researcher, I want Keep Share measured as the share of contract tokens Jev handles alone, with unit counts alongside, so that the headline does not depend on how the text was cut.
48. As the researcher, I want the share of Fully Cleared Clauses reported, so that I can see how often the expensive model would not be called at all.
49. As the researcher, I want every rate accompanied by its counts, such as "4 of 82 highlights missed", so that small numbers are never hidden behind percentages.
50. As the researcher, I want precision on kept "yes" answers reported (kept "yes" clauses that touch a highlight ÷ all kept "yes"), so that I know how trustworthy a confident "yes" is.
51. As the researcher, I want an upper-bound line that assumes the expensive model gets every escalated pair right, clearly labelled as an upper bound, so that I can see the best the cascade could do.
52. As the researcher, I want estimated savings per 1,000 clauses priced as one expensive call per clause with at least one Escalated rule, asking only the escalated rules, at Claude Sonnet 5.5 list price with Opus 5.5 as a second row, batch and non-batch, minus Jev's cost, so that "how much we could have saved" is a defensible estimate.
53. As the researcher, I want the expensive-model cost estimated from token counts without calling any expensive model, so that the project stays Jev-only.
54. As the researcher, I want Jev's price treated as a configurable value and its source stated, so that the unverified $0.042 per million input tokens can be corrected later.
55. As the researcher, I want a calibration chart and expected calibration error per rule, using whether a clause touches a highlight as the outcome, so that TypeSafe's calibration claim gets an independent check.
56. As the researcher, I want the R1/R4 co-occurrence reported (documents and clauses with both, highlights sharing text), so that readers know the two rules are not independent.
57. As the researcher, I want the whole grading rerun on plain 120-word chunks and shown side by side with clauses, so that readers can see the conclusions do not depend on the splitter.
58. As the researcher, I want one command that rebuilds the full report from the cache, so that results are reproducible without network access.
59. As the researcher, I want the report to include a "How grading works" section covering highlights as ground truth, the touch rule, Lead-in cases and the derived nature of the labels, so that the method is transparent.
60. As the researcher, I want the report to note TypeSafe's documented prompt-injection limitation and that its calibration evaluations were self-run, so that readers weigh vendor claims correctly.
61. As the researcher, I want charts as PNG files referenced from the Markdown, so that the report renders anywhere.
62. As a reader of the report, I want per-rule tables that lead with counts, then rates with intervals, so that I can judge each rule quickly.
63. As a reader of the report, I want the keep-share-versus-miss-rate curve per rule, so that I can see the trade-off beyond the chosen cutoffs.

## Implementation Decisions

- **Language and tooling:** Python with uv and pytest, matching the playground's tooling.
- **Modules:**
  - **Corpus** loads the License Agreement Set from the CUAD JSON and CSV and returns documents (title, text) with highlights per rule (start, end, text). It owns the filter and the Pacira name normalisation.
  - **Splitter** turns one document's text into an ordered list of Clauses, each with its span, its token count, its parent Lead-in (if a sub-item) and whether it is itself a Lead-in. A second unit maker produces plain 120-word chunks for the sensitivity check, with the same output shape.
  - **Rulebook** holds the eight Rules: id, CUAD category, Detection Question wording, and sub-questions for R2, R4 and R6. The backup categories live alongside.
  - **Jev client** is an interface: given a clause text (with Lead-in context), a question and a question type, return P(yes). It has a stub implementation (deterministic, seeded fake P(yes)) and later a real one (HTTP to TypeSafe with a bearer token, `jev-latest` pinned to a recorded version, respecting about 1,200 requests per minute).
  - **Jev runner** asks every (unit, rule, sub-question) and appends results to a JSONL cache keyed by document, unit, rule, sub-question, question type and model version. It skips keys already cached and records wall-clock time.
  - **Evaluator** is pure: given units, highlights, the P(yes) table and fold assignments, it returns per-rule results. It covers touch computation (including the Lead-in rule), fold stratification, per-fold cutoff tuning, pooled outcome counts (found, pending and missed highlights; false alarms; kept "yes" precision), Keep Share in tokens and units, Fully Cleared Clauses, the oracle upper bound, the cost model, calibration and ECE, document-bootstrap intervals, and R1/R4 co-occurrence.
  - **Report** renders Evaluator results to Markdown plus PNG charts.
  - **Pilot** runs the question-type and compound-versus-split comparison on about 300 Pairs and writes a short pilot report, using the same client, cache and evaluator pieces.
- **Rule P(yes)** for a compound Rule is the maximum of its sub-questions' P(yes).
- **Jev is called once per (unit, rule or sub-question)**, never with several questions in one call; third-party docs describe its budget as "state plus one question".
- **The cutoff search** runs over the observed P(yes) values in the tuning folds. Ties are resolved toward keeping less work, the conservative side.
- **The Lower Cutoff** is the highest value with missed highlights ≤ 5% of highlights in the tuning folds. **The Upper Cutoff** is the lowest value with false alarms ≤ 20% of kept "yes" in the tuning folds. They are tuned independently: misses depend only on the Lower Cutoff.
- **Folds** are five, document-level, stratified across all eight rules' highlighted documents, with a fixed seed recorded in the report.
- **Bootstrap** resamples documents with replacement, about 1,000 times, and gives 95% percentile intervals.
- **The cost model** counts tokens per clause, including the Lead-in context and question text. It uses list prices for Claude Sonnet 5.5 and Opus 5.5 (batch and non-batch) and Jev's price as configuration, each with its source date.
- **Grading never uses a per-clause gold label;** see ADR-0002. Only Jev runs; see ADR-0001.
- **Terminology** follows `GLOSSARY.md`: Clause, Highlight, Rule, Detection Question, Touch, P(yes), Lower/Upper Cutoff, Kept, Escalated, Keep Share, Found/Pending/Missed Highlight, False Alarm, Miss Rate, Fold, Fully Cleared Clause, Lead-in.

## Testing Decisions

- **Good tests check behaviour at a seam,** with inputs and expected outputs a person can verify by hand. They do not check internal helpers or intermediate data structures.
- **Seam A, the Evaluator, is the main seam.** Tests build tiny hand-made documents (a few clauses, a few highlights, chosen P(yes) values) and assert the per-rule results. Required cases:
  - one highlight across several clauses with one kept "yes" is found once
  - all touching clauses kept "no" is missed
  - one touching clause escalated is pending
  - a kept "yes" touching no highlight is a false alarm
  - a highlighted Lead-in makes its sub-items touch
  - a one-character overlap counts as touching
  - the Lower Cutoff respects the 5% budget and the Upper Cutoff the 20% budget on tuning data
  - a fold is never scored with cutoffs tuned on itself
  - stratified folds give every fold at least one highlighted document per rule when the data allows
  - Keep Share counts tokens, not units
  - a Fully Cleared Clause needs all rules kept
  - compound rules take the maximum of their sub-questions
  - the cost model charges one call per clause with any escalated rule
- **Seam B, the Splitter.** Tests use short excerpts from the real problem documents: Telkom's spaced numbering, Eton's mid-line numbering, a Glu Mobile pricing table that must not split, the exclusivity territory list whose short items must survive, and a lettered list under a Lead-in. A corpus-wide check asserts no Clause over 600 words and about 97% or more of highlights inside exactly one Clause.
- **Seam C, end to end.** One test runs the command on two or three real documents with the stub Jev client and asserts that a report with the expected sections and per-rule tables is produced and that a second run makes no client calls (the cache is used).
- **No prior art exists;** this is a new repo. The tests set the pattern.

## Out of Scope

- Running any strong LLM (Sonnet, Opus or others). Savings are estimated from list prices, not measured.
- Compliance Readings, such as "this contract violates R5", and any licensee-facing verdict.
- Auditing or correcting the lawyers' highlights (missing highlights, CUAD-definition mismatch).
- Contract types other than the License Agreement Set, and CUAD categories outside the Rulebook (except the backups).
- Fine-tuning, prompt optimisation beyond the question-type pilot, or recalibrating Jev's probabilities.
- Any user interface or service; the output is a report.
- Updating the old playground notes file; this spec supersedes it.

## Further Notes

- The Jev key comes later from the user. Until then everything runs on the stub, and the real-client work is blocked on the key.
- Facts established during design:
  - The 53-document set has 455 highlights across the eight rules.
  - In a rough-splitter dry run, 91% of highlights touched one clause, 39 spanned several, and 12 are Lead-in-only.
  - R4 is the thinnest rule (17 documents, 26 highlights) and may fail the gate on the real splitter.
  - Plain chunks moved R8 by 11 highlights in a keyword dry run, which is why clauses stay the unit.
- Third-party findings to cite:
  - Arize: tuned cutoffs matter a lot.
  - wotai.co: 34.7% escalation for Jev vs 2.7% for Haiku.
  - Beri: splitting questions lifted accuracy from 62.6% to 95%, and probabilities needed recalibrating per question.
  - Same question across types gave very different probabilities.
  - A yes/no question whose "true" means "no" performs worse.
- Related decisions: ADR-0001 (Jev-only evaluation), ADR-0002 (cross-fitting and highlight-based grading).
