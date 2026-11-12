# Jev-only evaluation, no strong-LLM run

The original plan ran a strong LLM on a sample of clauses to build a cascade and an LLM-alone baseline. We dropped it: the question is how much work Jev takes off the expensive model and how accurate Jev is against the lawyer labels, so only Jev is run. Savings are estimated from token counts at list prices (Claude Sonnet 5.5, with Opus 5.5 as a second row) rather than measured, and a line that assumes the expensive model resolves every Escalated clause correctly is shown only as a labelled upper bound.

This decision stands. The grading it feeds has since changed; see ADR-0003 for how Jev is scored.

## Consequences

Nothing about Jev's cutoff can be calibrated against what a strong LLM would have found, so the report shows the whole cutoff curve and lets the reader pick a point (ADR-0003). Adding an LLM later is possible but changes the headline, so do it as a separate comparison, not a silent replacement.

Because no expensive model is ever run, two things are assumptions rather than measurements, and the report must say so: that the expensive model would in fact find a provision once its Clause is Escalated, and that the estimated token prices are current.
