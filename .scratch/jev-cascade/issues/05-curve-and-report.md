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

**Status:** ready-for-agent

- [ ] The curve has exactly one row per distinct observed P(yes) per Rule; a test asserts this on
      hand-made data.
- [ ] Each Rule's lowest-scoring held Clause and its achievable Binned Share appear in the report.
- [ ] The report opens with a per-Rule summary leading with counts, and separately shows the Fully
      Binned Clause share with a note that per-Rule Binned Share does not combine into it.
- [ ] Neither accuracy nor ROC AUC appears anywhere; the report says why.
- [ ] Every section above is present and uses `GLOSSARY.md` vocabulary. No retired term appears.
- [ ] A per-Rule curve chart is written as a PNG and referenced.
- [ ] Every stub-derived figure is labelled as stub, not only the timings.
- [ ] One command rebuilds the whole report from the cache with no network access, and the end-to-end
      test checks each section heading is present.
