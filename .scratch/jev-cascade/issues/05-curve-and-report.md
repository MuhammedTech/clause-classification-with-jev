# 05: The cutoff curve and the finished report

**What to build:** the sweep, and the report a reader can follow without the design conversation.

**The curve.** For each Rule, sweep the Cutoff across **every distinct observed P(yes)** for that Rule
and run ticket 04's metrics at each. The piles only change when the Cutoff crosses a score Jev
actually gave, so that is the complete set of rows. Nothing is tuned.

**The headline per Rule.** The lowest P(yes) Jev gave to a Clause holding a Highlight, and the Binned
Share achievable below it. That is the free saving, and it is the most useful number in the report.

**The report adds:**

- a "How this is measured" section: Highlights as the only ground truth, the one-character overlap
  rule, Clause against Provision Recall, Certified against Inferred Negatives
- the corpus section: the filter, the Pacira normalisation, and how 53 relates to the 44 and 33
- the Rulebook section: seven Rules, why Uncapped Liability was dropped, that R5 and R8 changed meaning
- **two readings of the curve, named as such**: around 0.5 the ordinary classifier reading, at the low
  end the cascade reading where Precision is low by design. State plainly that quoting Precision at a
  low Cutoff as Jev's accuracy would be wrong.
- the three things not measured: whether a confident yes is trustworthy, whether the expensive model
  would find an Escalated provision, whether the lawyers highlighted everything
- vendor caveats: TypeSafe's calibration evaluations were self-run, and its documented prompt-injection
  limitation
- that the surviving Rules were partly chosen for clean definitions, so results read optimistically

**Charts.** One PNG per Rule of the curve, referenced from the Markdown.

**Blocked by:** 04.

**Status:** resolved

- [x] The curve has exactly one row per distinct observed P(yes) per Rule; a test asserts this on
      hand-made data.
- [x] Each Rule's lowest-scoring held Clause and its achievable Binned Share appear in the report.
- [x] The report opens with a per-Rule summary leading with counts, and separately shows the Fully
      Binned Clause share with a note that per-Rule Binned Share does not combine into it.
- [x] Neither accuracy nor ROC AUC appears anywhere; the report says why.
- [x] Every section above is present and uses `GLOSSARY.md` vocabulary. No retired term appears.
- [x] A per-Rule curve chart is written as a PNG and referenced.
- [x] Every stub-derived figure is labelled as stub, not only the timings.
- [x] One command rebuilds the whole report from the cache with no network access, and the end-to-end
      test checks each section heading is present.

## Comments

**2026-11-12, resolved.** `evaluator.cutoff_curve` returns one `RuleMetrics` per distinct observed
P(yes), lowest first, and `evaluator.free_saving` returns the lowest P(yes) of a holding Clause with
the metrics at the Cutoff just under it (`math.nextafter`, so a Clause tying the lowest held score
stays Escalated). The report opens with a Summary, adds How this is measured, a per-Rule curve block
with the free saving, a curve excerpt and a chart, Reading the curve (the classifier reading and the
cascade reading, with Precision never presented as accuracy) and Vendor caveats. Every table of
scored figures carries a "Stub-derived" line, not only the timings.

Decisions worth knowing:

- **matplotlib is now a dependency**, for the PNGs. `charts.py` uses the Agg backend, so no display.
- **The Markdown prints at most 25 curve rows**, chosen by position and never by outcome; the
  complete curve, one row per distinct P(yes), is `curves/<Rule>.csv`. A real run has thousands of
  distinct scores per Rule and would bury the report otherwise.
- **`--from-cache`** rebuilds the report with a client that refuses every call, so it cannot reach
  the network; a Pair missing from the cache is an error, not a call.
- **The ticket says "how 53 relates to the 44 and 33".** The measured filters are 53, 44 and 44
  (`docs/cuad-ground-truth.md`); no filter measures 33. The report states 53 against the two 44s.
  The 33 looks like R1's document count without Pacira in the gate table, which is a different
  quantity, so it is not in the report.

**Code review (Standards and Spec).** No hard violations on either axis. Fixed: the free-saving
paragraph now names the Clause that set the lowest P(yes) and carries its own stub label; the
classifier-reading prose no longer hard-codes 0.5 beside a row read at the run's Cutoff; the chart
draws steps between observed P(yes) values, not slopes; "score" is P(yes) in code and tests;
`GLOSSARY.md` gained Free Saving and Classifier / Cascade Reading.

Left alone, as judgement calls: splitting `report.py` into section modules, a shared helper for the
four recall/precision cells, `FreeSaving`'s forwarding properties, and a `RuleInputs` type for the
Rule-evaluation parameters. Worth doing when ticket 06 touches the report again.
